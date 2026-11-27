# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_resolve import dfh_load_registry
from Df.Harness.lib.path_state import SHADOW_LOAD_HOOK, dfh_clear_path_cache, dfh_clear_registry_cache
from Df.Harness.lib.path_template import dfh_path_key
from Df.Harness.lib.project import dfh_rewrite_json_file
from Df.Harness.lib.shadow_hooks import SHADOW_JOURNAL_IDENTITY_HOOK, SHADOW_TITLE_HOOK
import json
import os
import shutil
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_remap_journal_data()`
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
# @used-by :func:`dfh_shadow_isolation_context()`
def _journal_identity_hook(relocations: dict[Path, Path]):
	mapped = {(dfh_path_key(Path(src).resolve() / '\ua66e'), dfh_path_key(Path(dst).resolve() / '\ua66e')) for src, dst in relocations.items()}
	# @used-by :func:`_journal_identity_hook()`
	def _match(orig_fn, first, second) -> bool:
		r = orig_fn(first, second)
		if not r and first and second:
			k1, k2 = (dfh_path_key(Path(first).resolve()), dfh_path_key(Path(second).resolve()))
			r = (k1, k2) in mapped or (k2, k1) in mapped
		return r
	return _match
# @used-by :func:`dfh_remap_shadow_state()`
def _remap_journal_data(old_state: Path, new_state: Path, pairs: list[tuple[str, str]]) -> None:
	if old_state.is_dir():
		for item in sorted(old_state.rglob('*')):
			if item.is_file() and (not item.name.endswith('.lock')):
				target = new_state / item.relative_to(old_state)
				_copy_file(item, target, hardlink=False)
				if '.json' == target.suffix.lower() and 'answer-groups' not in target.parts:
					dfh_rewrite_json_file(target, pairs)
# @used-by :func:`dfh_shadow_isolation_context()`
def _shadow_registry_wrapper(relocations: dict[Path, Path]):
	mapped = [(dfh_path_key(Path(src).resolve()), Path(dst).resolve()) for src, dst in relocations.items()]
	# @used-by :func:`_shadow_registry_wrapper()`
	def _wrap(reg):
		for src_k, dst_r in mapped:
			reg.relocations[src_k] = str(dst_r)
			reg.workspace_overrides[dfh_path_key(dst_r)] = {}
		return reg
	return _wrap
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.run()`
def dfh_build_stop_transcript(native_tx: Path, prepared_body: str, out_dir: Path) -> Path:
	out_dir.mkdir(parents=True, exist_ok=True)
	rows = [json.loads(line) for line in native_tx.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
	max_step = max((int(row.get('step_index', -1)) for row in rows if isinstance(row.get('step_index'), int)), default=0)
	rows.append({'content': prepared_body, 'step_index': max_step + 1, 'tool_calls': [], 'type': 'PLANNER_RESPONSE'})
	dest = out_dir / 'transcript_full.jsonl'
	dest.write_text('\n'.join((json.dumps(row, ensure_ascii=False) for row in rows)) + '\n', encoding='utf-8')
	return dest
# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.run()`
def dfh_cleanup_shadow_root(shadow_root: Path) -> bool:
	if shadow_root.exists():
		shutil.rmtree(shadow_root, ignore_errors=False)
	parent = shadow_root.parent
	if parent.is_dir() and (not any(parent.iterdir())):
		parent.rmdir()
	return not shadow_root.exists()
# @used-by :func:`dfh_remap_shadow_state()`
# @used-by :meth:`Df.Harness.Shadow.CommandExecutor.CommandExecutor.run()`
def dfh_path_pairs(raw_pairs: tuple[tuple[Path, Path], ...]) -> list[tuple[str, str]]:
	pairs: list[tuple[str, str]] = []
	for old_p, new_p in raw_pairs:
		old_r, new_r = (Path(old_p).resolve(), Path(new_p).resolve())
		pairs.append((str(old_r), str(new_r)))
		old_posix, new_posix = (old_r.as_posix(), new_r.as_posix())
		if old_posix != str(old_r):
			pairs.append((old_posix, new_posix))
	return pairs
# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.__remap_copies()`
def dfh_remap_shadow_state(src_root: Path, dst_root: Path, extra_pairs: tuple[tuple[Path, Path], ...]=(), *, old_state: Path | None=None, resolve_state_fn: Any=None) -> None:
	if None is resolve_state_fn:
		from Df.Harness.lib.journal_core import dfh_resolve_journal_dir, dfh_state_dir
		resolve_state_fn = lambda r: dfh_state_dir(dfh_resolve_journal_dir(r))
	src_state = old_state if None is not old_state else resolve_state_fn(src_root)
	new_state = resolve_state_fn(dst_root)
	pairs = dfh_path_pairs(((src_state, new_state), (src_root, dst_root), *extra_pairs))
	_remap_journal_data(src_state, new_state, pairs)
	data_dir = dst_root / '\ua616/data'
	for name in ('workflow.json', 'rendered.json'):
		dfh_rewrite_json_file(data_dir / name, pairs)
	turns_dir = data_dir / 'turns'
	if turns_dir.is_dir():
		for item in sorted(turns_dir.glob('*.json')):
			dfh_rewrite_json_file(item, pairs, preserve_keys=('admission',))
# @used-by :func:`agent_tools.shadow_replay_clone.shadow_isolation_context()`
# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.run()`
@contextmanager
def dfh_shadow_isolation_context(relocations: dict[Path, Path], *, legacy_ctx: Any=None):
	prev_load, prev_title, prev_same = (SHADOW_LOAD_HOOK[0], SHADOW_TITLE_HOOK[0], SHADOW_JOURNAL_IDENTITY_HOOK[0])
	SHADOW_LOAD_HOOK[0] = _shadow_registry_wrapper(relocations)
	SHADOW_TITLE_HOOK[0] = lambda cid, title, **_kw: {'changed': False, 'conversation_id': cid, 'reason': 'shadow_replay_disabled', 'synced': False, 'title': title}
	SHADOW_JOURNAL_IDENTITY_HOOK[0] = _journal_identity_hook(relocations)
	dfh_clear_registry_cache()
	dfh_clear_path_cache()
	dfh_load_registry()
	try:
		if None is not legacy_ctx:
			with legacy_ctx(relocations):
				yield
		else:
			yield
	finally:
		SHADOW_LOAD_HOOK[0] = prev_load
		SHADOW_TITLE_HOOK[0] = prev_title
		SHADOW_JOURNAL_IDENTITY_HOOK[0] = prev_same
		dfh_clear_registry_cache()
		dfh_clear_path_cache()
