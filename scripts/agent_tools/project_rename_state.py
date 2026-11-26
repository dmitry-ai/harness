# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
import hashlib
import json
import os
import re
from .journal import _raw_state_dir, resolve_journal_dir
from .path_registry import project_paths
from .storage import replace_bytes
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
_FOLDER_RULE_RE = re.compile(r'(?m)^Folder name:\s*`[^`]+`;')
def _is_under_journal_root(path: Path) -> Path | None:
	r = None
	if '\ua66e' == path.name:
		r = path.parent
	elif '\ua66e' == path.parent.name and path.name in ('1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437'):
		r = path.parent.parent
	return r
def _path_pairs(old_root: Path, new_root: Path, old_state: Path | None, new_state: Path | None) -> list[tuple[str, str]]:
	raw: list[tuple[Path, Path]] = []
	if None is not old_state and None is not new_state:
		raw.append((old_state, new_state))
	raw.append((old_root, new_root))
	pairs: list[tuple[str, str]] = []
	for src, dst in raw:
		s_uri, d_uri = (src.as_uri(), dst.as_uri())
		pairs.append((s_uri, d_uri))
		s_str, d_str = (str(src), str(dst))
		pairs.append((s_str, d_str))
		s_pos, d_pos = (src.as_posix(), dst.as_posix())
		if s_pos != s_str:
			pairs.append((s_pos, d_pos))
	return pairs
def _rewrite_json_file(path: Path, pairs: list[tuple[str, str]]) -> None:
	if path.is_file():
		data = json.loads(path.read_text(encoding='utf-8-sig'))
		updated = _rewrite_value(data, pairs)
		replace_bytes(path, (json.dumps(updated, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
def _rewrite_text(text: str, pairs: list[tuple[str, str]]) -> str:
	out = text
	for old_s, new_s in pairs:
		out = re.sub(re.escape(old_s), lambda _m, rep=new_s: rep, out, flags=re.IGNORECASE)
	return out
def _rewrite_value(value, pairs: list[tuple[str, str]]):
	if isinstance(value, str):
		r = _rewrite_text(value, pairs)
	elif isinstance(value, list):
		r = [_rewrite_value(v, pairs) for v in value]
	elif isinstance(value, dict):
		r = {(_rewrite_text(k, pairs) if isinstance(k, str) else k): _rewrite_value(v, pairs) for k, v in value.items()}
	else:
		r = value
	return r
def _update_folder_rule(new_root: Path, new_label: str) -> None:
	rule_f = new_root / '.agents/rules/90-project.md'
	if rule_f.is_file():
		orig = rule_f.read_text(encoding='utf-8')
		updated = _FOLDER_RULE_RE.sub(lambda _m: f'Folder name: `{new_label}`;', orig)
		if updated != orig:
			replace_bytes(rule_f, updated.encode('utf-8'))
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
def _update_project_json(old_root: Path, new_root: Path, new_label: str, new_label_kind: str) -> tuple[dict, str, str]:
	pj_path = project_paths(new_root, exact_root=True).project_json
	old_raw = pj_path.read_bytes()
	state = json.loads(old_raw.decode('utf-8-sig'))
	history = list(state.get('renamed_from') or [])
	history.append({'from': str(old_root), 'to': str(new_root), 'from_name': old_root.name, 'to_name': new_root.name, 'at': datetime.now(timezone.utc).isoformat()})
	state['label'] = new_label
	state['label_kind'] = new_label_kind
	state['renamed_from'] = history
	new_raw = (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
	replace_bytes(pj_path, new_raw)
	return (state, hashlib.sha256(old_raw).hexdigest(), hashlib.sha256(new_raw).hexdigest())
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
def migrate_journal_state(old_root: Path, new_root: Path) -> tuple[Path, Path]:
	new_pp = project_paths(new_root, exact_root=True)
	new_jdir = resolve_journal_dir(new_root)
	rel_j = new_jdir.relative_to(new_root)
	old_jdir = old_root / rel_j
	old_state = _raw_state_dir(old_jdir, data_root=new_pp.data_dir)
	new_state = _raw_state_dir(new_jdir, data_root=new_pp.data_dir)
	if old_state.is_dir() and old_state.resolve() != new_state.resolve():
		(old_state / 'writer.lock').unlink(missing_ok=True)
		if not new_state.exists():
			new_state.parent.mkdir(parents=True, exist_ok=True)
			os.replace(old_state, new_state)
	pairs = _path_pairs(old_root, new_root, old_state, new_state)
	if new_state.is_dir():
		for item in sorted(new_state.rglob('*.json')):
			_rewrite_json_file(item, pairs)
	return (old_state, new_state)
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
def rewrite_launcher_handoffs(launcher_root: Path, old_root: Path, new_root: Path) -> int:
	turns_dir = project_paths(Path(launcher_root).resolve(), exact_root=True).turns_dir
	pairs = _path_pairs(old_root, new_root, None, None)
	count = 0
	if turns_dir.is_dir():
		for sf in sorted(turns_dir.glob('*.json')):
			raw = sf.read_text(encoding='utf-8-sig')
			updated = _rewrite_text(raw, pairs)
			if updated != raw:
				replace_bytes(sf, updated.encode('utf-8'))
				count += 1
	return count
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
def rewrite_project_internal_state(old_root: Path, new_root: Path, new_label: str, new_label_kind: str) -> dict:
	old_state, new_state = migrate_journal_state(old_root, new_root)
	pairs = _path_pairs(old_root, new_root, old_state, new_state)
	# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
	state, old_pj_sha, new_pj_sha = _update_project_json(old_root, new_root, new_label, new_label_kind)
	_update_folder_rule(new_root, new_label)
	pp = project_paths(new_root, exact_root=True)
	# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
	_rewrite_json_file(pp.data_dir / 'workflow.json', [*pairs, (old_pj_sha, new_pj_sha)])
	_rewrite_json_file(pp.data_dir / 'rendered.json', pairs)
	if pp.turns_dir.is_dir():
		for tf in sorted(pp.turns_dir.glob('*.json')):
			_rewrite_json_file(tf, pairs)
	if pp.scratch_dir.is_dir():
		for df in sorted(pp.scratch_dir.glob('answer-*.md')):
			orig = df.read_text(encoding='utf-8-sig')
			updated = _rewrite_text(orig, pairs)
			if updated != orig:
				replace_bytes(df, updated.encode('utf-8'))
	return state
def _has_rename_lineage(existing_root: Path, missing_root: Path) -> bool:
	r = False
	pj_path = existing_root / '\ua616/project.json'
	if pj_path.is_file():
		try:
			history = json.loads(pj_path.read_text(encoding='utf-8-sig')).get('renamed_from') or []
		except (OSError, ValueError):
			history = []
		target_key = missing_root.as_posix().casefold()
		r = any((isinstance(h, dict) and Path(str(h.get('from') or '')).resolve().as_posix().casefold() == target_key for h in history if h.get('from')))
	return r
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
def same_journal_identity_with_rename(first: str | Path | None, second: str | Path | None, canon_fn) -> bool:
	r = False
	if isinstance(first, (str, Path)) and isinstance(second, (str, Path)) and str(first).strip() and str(second).strip():
		c1, c2 = (canon_fn(first), canon_fn(second))
		if c1 == c2:
			r = True
		else:
			r1, r2 = (_is_under_journal_root(c1), _is_under_journal_root(c2))
			if None is not r1 and None is not r2:
				r = (r1.is_dir() and (not r2.is_dir()) and _has_rename_lineage(r1, r2)) or (r2.is_dir() and (not r1.is_dir()) and _has_rename_lineage(r2, r1))
	return r
