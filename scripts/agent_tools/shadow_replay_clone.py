# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import json
import os
import re
import shutil
from .journal import resolve_journal_dir, state_dir
from .path_cache import clear_path_cache
from .path_registry import _path_key, load_registry
# 2026-11-25
# "Add workspace-local shadow-replay CLI command and EXEC-2 acceptance gate":
# https://github.com/dmitry-ai/harness/issues/237
def _copy_file(src: Path, dst: Path, *, hardlink: bool) -> None:
	dst.parent.mkdir(parents=True, exist_ok=True)
	linked = False
	if hardlink:
		try:
			os.link(src, dst)
			linked = True
		except OSError:
			linked = False
	if not linked:
		shutil.copy2(src, dst)
def _is_evidence_file(rel: Path) -> bool:
	parts = rel.parts
	return 3 <= len(parts) and '\ua616' == parts[0] and 'KB' == parts[1] and 'Evidence' == parts[2]
def _is_skipped_rel(rel: Path) -> bool:
	parts = rel.parts
	if any((p.endswith('.lock') for p in parts)):
		r = True
	elif 3 <= len(parts) and '\ua616' == parts[0] and 'data' == parts[1] and parts[2] in ('scratch', '.journal'):
		r = True
	else:
		r = False
	return r
def _path_pairs(raw_pairs: tuple[tuple[Path, Path], ...]) -> list[tuple[str, str]]:
	pairs: list[tuple[str, str]] = []
	for old_p, new_p in raw_pairs:
		old_r = Path(old_p).resolve()
		new_r = Path(new_p).resolve()
		pairs.append((str(old_r), str(new_r)))
		old_posix, new_posix = (old_r.as_posix(), new_r.as_posix())
		if old_posix != str(old_r):
			pairs.append((old_posix, new_posix))
	return pairs
def _remap_journal_data(old_state: Path, new_state: Path, pairs: list[tuple[str, str]]) -> None:
	if old_state.is_dir():
		for item in sorted(old_state.rglob('*')):
			if item.is_file() and (not item.name.endswith('.lock')):
				target = new_state / item.relative_to(old_state)
				_copy_file(item, target, hardlink=False)
				if '.json' == target.suffix.lower() and 'answer-groups' not in target.parts:
					_rewrite_json_file(target, pairs)
def _rewrite_json_file(path: Path, pairs: list[tuple[str, str]], *, preserve_keys: tuple[str, ...]=()) -> None:
	if path.is_file():
		data = json.loads(path.read_text(encoding='utf-8-sig'))
		updated = _rewrite_value(data, pairs, preserve_keys=preserve_keys)
		path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def _rewrite_path_text(text: str, pairs: list[tuple[str, str]]) -> str:
	out = text
	for old_s, new_s in pairs:
		out = re.sub(re.escape(old_s), lambda _m, rep=new_s: rep, out, flags=re.IGNORECASE)
	return out
def _rewrite_value(value, pairs: list[tuple[str, str]], *, preserve_keys: tuple[str, ...]=()):
	if isinstance(value, str):
		r = _rewrite_path_text(value, pairs)
	elif isinstance(value, list):
		r = [_rewrite_value(v, pairs, preserve_keys=preserve_keys) for v in value]
	elif isinstance(value, dict):
		r = {(_rewrite_path_text(k, pairs) if isinstance(k, str) else k): (v if k in preserve_keys else _rewrite_value(v, pairs, preserve_keys=preserve_keys)) for k, v in value.items()}
	else:
		r = value
	return r
def build_stop_transcript(native_tx: Path, prepared_body: str, out_dir: Path) -> Path:
	out_dir.mkdir(parents=True, exist_ok=True)
	rows = [json.loads(line) for line in native_tx.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
	max_step = max((int(row.get('step_index', -1)) for row in rows if isinstance(row.get('step_index'), int)), default=0)
	rows.append({'step_index': max_step + 1, 'type': 'PLANNER_RESPONSE', 'content': prepared_body, 'tool_calls': []})
	dest = out_dir / 'transcript_full.jsonl'
	dest.write_text('\n'.join((json.dumps(row, ensure_ascii=False) for row in rows)) + '\n', encoding='utf-8')
	return dest
def cleanup_shadow_root(shadow_root: Path) -> bool:
	if shadow_root.exists():
		shutil.rmtree(shadow_root, ignore_errors=False)
	parent = shadow_root.parent
	if parent.is_dir() and (not any(parent.iterdir())):
		parent.rmdir()
	return not shadow_root.exists()
def clone_project_tree(src_root: Path, dst_root: Path, *, hardlink_evidence: bool=True) -> None:
	src_r = Path(src_root).resolve()
	dst_r = Path(dst_root).resolve()
	dst_r.mkdir(parents=True, exist_ok=True)
	for item in sorted(src_r.rglob('*')):
		rel = item.relative_to(src_r)
		if _is_skipped_rel(rel):
			continue
		target = dst_r / rel
		if item.is_dir():
			target.mkdir(parents=True, exist_ok=True)
		elif item.is_file():
			_copy_file(item, target, hardlink=hardlink_evidence and _is_evidence_file(rel))
	(dst_r / '\ua616/data/scratch').mkdir(parents=True, exist_ok=True)
def _journal_identity_matcher(orig_fn, relocations: dict[Path, Path]):
	mapped = {(_path_key(Path(src).resolve() / '\ua66e'), _path_key(Path(dst).resolve() / '\ua66e')) for src, dst in relocations.items()}
	def _match(first, second) -> bool:
		r = orig_fn(first, second)
		if not r and first and second:
			k1, k2 = (_path_key(Path(first).resolve()), _path_key(Path(second).resolve()))
			r = (k1, k2) in mapped or (k2, k1) in mapped
		return r
	return _match
# 2026-11-26 "Add reusable finalized Upwork project fixture and lifecycle contract tests": https://github.com/dmitry-ai/harness/issues/293
# @used-by :func:`shadow_isolation_context()`
def _wrapped_shadow_registry(orig_load, relocations: dict[Path, Path]):
	mapped = [(_path_key(Path(src).resolve()), Path(dst).resolve()) for src, dst in relocations.items()]
	def _load(*args, **kwargs):
		reg = orig_load(*args, **kwargs)
		for src_k, dst_r in mapped:
			reg.relocations[src_k] = str(dst_r)
			reg.workspace_overrides[_path_key(dst_r)] = {}
		return reg
	return _load
def _restore_shadow_registry(pr_mod, orig_load, ag_mod, orig_title, journal_mod, orig_same_j) -> None:
	pr_mod.load_registry = orig_load
	pr_mod.clear_registry_cache()
	ag_mod.update_conversation_title = orig_title
	journal_mod.same_journal_identity = orig_same_j
	clear_path_cache()
def remap_shadow_state(src_root: Path, dst_root: Path, extra_pairs: tuple[tuple[Path, Path], ...]=(), *, old_state: Path | None=None) -> None:
	src_state = old_state if None is not old_state else state_dir(resolve_journal_dir(src_root))
	new_state = state_dir(resolve_journal_dir(dst_root))
	pairs = _path_pairs(((src_state, new_state), (src_root, dst_root), *extra_pairs))
	_remap_journal_data(src_state, new_state, pairs)
	data_dir = dst_root / '\ua616/data'
	for name in ('workflow.json', 'rendered.json'):
		_rewrite_json_file(data_dir / name, pairs)
	turns_dir = data_dir / 'turns'
	if turns_dir.is_dir():
		for item in sorted(turns_dir.glob('*.json')):
			_rewrite_json_file(item, pairs, preserve_keys=('admission',))
@contextmanager
def shadow_isolation_context(relocations: dict[Path, Path]):
	from . import journal as journal_mod, path_registry as pr_mod
	from .platforms import antigravity as ag_mod
	orig_load = pr_mod.load_registry
	orig_title, orig_same_j = (ag_mod.update_conversation_title, journal_mod.same_journal_identity)
	pr_mod.load_registry = _wrapped_shadow_registry(orig_load, relocations)
	pr_mod.load_registry()
	ag_mod.update_conversation_title = lambda cid, title, **_kw: {'synced': False, 'changed': False, 'title': title, 'conversation_id': cid, 'reason': 'shadow_replay_disabled'}
	journal_mod.same_journal_identity = _journal_identity_matcher(orig_same_j, relocations)
	clear_path_cache()
	try:
		yield
	finally:
		_restore_shadow_registry(pr_mod, orig_load, ag_mod, orig_title, journal_mod, orig_same_j)