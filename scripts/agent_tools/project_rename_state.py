# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
import hashlib
import json
import os
import re
from Df.Core.lib.text.source import df_text_rewrite_pairs
from .journal import _raw_state_dir, resolve_journal_dir
from .path_registry import project_paths
from .storage import replace_bytes
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
_FOLDER_RULE_RE = re.compile(r'(?m)^Folder name:\s*`[^`]+`;')
# @used-by :func:`same_journal_identity_with_rename()`
def _is_under_journal_root(path: Path) -> Path | None:
	r = None
	if '\ua66e' == path.name:
		r = path.parent
	elif '\ua66e' == path.parent.name and path.name in ('1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437'):
		r = path.parent.parent
	return r
# @used-by :func:`agent_tools.project_rename_verify._launcher_stale_files()`
# @used-by :func:`agent_tools.project_rename_verify._verify_journal_regression()`
# @used-by :func:`migrate_journal_state()`
# @used-by :func:`rewrite_launcher_handoffs()`
# @used-by :func:`rewrite_project_internal_state()`
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
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
# @used-by :func:`_rewrite_json_file()`
# @used-by :func:`_update_folder_rule()`
# @used-by :func:`_update_project_json()`
# @used-by :func:`rewrite_launcher_handoffs()`
# @used-by :func:`rewrite_project_internal_state()`
def _record_backup(path: Path, backups: list[tuple[Path, bytes | None]] | None) -> None:
	if None is not backups and (not any((p == path for p, _ in backups))):
		backups.append((path, path.read_bytes() if path.is_file() else None))
# @used-by :func:`migrate_journal_state()`
# @used-by :func:`refresh_workflow_file_hash()`
# @used-by :func:`rewrite_project_internal_state()`
def _rewrite_json_file(path: Path, pairs: list[tuple[str, str]], backups: list[tuple[Path, bytes | None]] | None=None) -> None:
	if path.is_file():
		_record_backup(path, backups)
		data = json.loads(path.read_text(encoding='utf-8-sig'))
		updated = _rewrite_value(data, pairs)
		replace_bytes(path, (json.dumps(updated, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`_rewrite_value()`
# @used-by :func:`rewrite_project_internal_state()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
def _rewrite_text(text: str, pairs: list[tuple[str, str]]) -> str:
	return df_text_rewrite_pairs(text, pairs)
# @used-by :func:`_rewrite_json_file()`
# @used-by :func:`rewrite_launcher_handoffs()`
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
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
# @used-by :func:`rewrite_project_internal_state()`
def _update_folder_rule(new_root: Path, new_label: str, backups: list[tuple[Path, bytes | None]] | None=None) -> None:
	rule_f = new_root / '.agents/rules/90-project.md'
	if rule_f.is_file():
		orig = rule_f.read_text(encoding='utf-8')
		updated = _FOLDER_RULE_RE.sub(lambda _m: f'Folder name: `{new_label}`;', orig)
		if updated != orig:
			_record_backup(rule_f, backups)
			replace_bytes(rule_f, updated.encode('utf-8'))
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
# @used-by :func:`rewrite_project_internal_state()`
def _update_project_json(old_root: Path, new_root: Path, new_label: str, new_label_kind: str, backups: list[tuple[Path, bytes | None]] | None=None) -> tuple[dict, str, str]:
	pj_path = project_paths(new_root, exact_root=True).project_json
	_record_backup(pj_path, backups)
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
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
# @used-by :func:`rewrite_project_internal_state()`
def migrate_journal_state(old_root: Path, new_root: Path, *, backups: list[tuple[Path, bytes | None]] | None=None, state_moves: list[tuple[Path, Path]] | None=None) -> tuple[Path, Path]:
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
			if None is not state_moves:
				state_moves.append((old_state, new_state))
	pairs = _path_pairs(old_root, new_root, old_state, new_state)
	if new_state.is_dir():
		for item in sorted(new_state.rglob('*.json')):
			_rewrite_json_file(item, pairs, backups)
	return (old_state, new_state)
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
# 2026-11-26 "Preserve finalized workflow and review lineage across rename-project": https://github.com/dmitry-ai/harness/issues/277
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
# @used-by :func:`agent_tools.project_rename._apply_rename_mutations()`
def rewrite_launcher_handoffs(launcher_root: Path, old_root: Path, new_root: Path, *, backups: list[tuple[Path, bytes | None]] | None=None) -> int:
	turns_dir = project_paths(Path(launcher_root).resolve(), exact_root=True).turns_dir
	pairs = _path_pairs(old_root, new_root, None, None)
	count = 0
	if turns_dir.is_dir():
		for sf in sorted(turns_dir.glob('*.json')):
			try:
				data = json.loads(sf.read_text(encoding='utf-8-sig'))
			except (OSError, ValueError):
				continue
			updated = _rewrite_value(data, pairs)
			if updated != data:
				_record_backup(sf, backups)
				replace_bytes(sf, (json.dumps(updated, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
				count += 1
	return count
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
# @used-by :func:`agent_tools.project_rename._apply_rename_mutations()`
def rewrite_project_internal_state(old_root: Path, new_root: Path, new_label: str, new_label_kind: str, *, backups: list[tuple[Path, bytes | None]] | None=None, state_moves: list[tuple[Path, Path]] | None=None) -> dict:
	old_state, new_state = migrate_journal_state(old_root, new_root, backups=backups, state_moves=state_moves)
	pairs = _path_pairs(old_root, new_root, old_state, new_state)
	# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
	state, old_pj_sha, new_pj_sha = _update_project_json(old_root, new_root, new_label, new_label_kind, backups)
	_update_folder_rule(new_root, new_label, backups)
	pp = project_paths(new_root, exact_root=True)
	# 2026-11-26 "Enforce project.domain_drift invariant in check-project and finalize": https://github.com/dmitry-ai/harness/issues/268
	_rewrite_json_file(pp.data_dir / 'workflow.json', [*pairs, (old_pj_sha, new_pj_sha)], backups)
	_rewrite_json_file(pp.data_dir / 'rendered.json', pairs, backups)
	if pp.turns_dir.is_dir():
		for tf in sorted(pp.turns_dir.glob('*.json')):
			_rewrite_json_file(tf, pairs, backups)
	if pp.scratch_dir.is_dir():
		for df in sorted(pp.scratch_dir.glob('answer-*.md')):
			orig = df.read_text(encoding='utf-8-sig')
			updated = _rewrite_text(orig, pairs)
			if updated != orig:
				_record_backup(df, backups)
				replace_bytes(df, updated.encode('utf-8'))
	return state
# 2026-11-26 "Preserve finalized workflow and review lineage across rename-project": https://github.com/dmitry-ai/harness/issues/277
# @used-by :func:`_has_rename_lineage()`
# @used-by :func:`find_sibling_project_path()`
def _rename_lineage_roots(existing_root: Path) -> tuple[Path, ...]:
	pj_path = existing_root / '\ua616/project.json'
	r: list[Path] = []
	if pj_path.is_file():
		try:
			history = json.loads(pj_path.read_text(encoding='utf-8-sig')).get('renamed_from') or []
		except (OSError, ValueError):
			history = []
		for item in history:
			if isinstance(item, dict) and item.get('from'):
				cand = Path(str(item['from'])).resolve()
				if not cand.is_dir():
					r.append(cand)
	return tuple(r)
# @used-by :func:`same_journal_identity_with_rename()`
# @used-by :func:`same_project_root_check()`
def _has_rename_lineage(existing_root: Path, missing_root: Path) -> bool:
	target_key = missing_root.as_posix().casefold()
	return any((cand.as_posix().casefold() == target_key for cand in _rename_lineage_roots(existing_root)))
# @used-by :func:`agent_tools.project_rename._sync_registrations()`
# @used-by :func:`refresh_workflow_file_hash()`
def capture_file_sha(path: Path) -> str | None:
	return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
# @used-by :func:`agent_tools.platforms.trace_common.reviewer_isolation_issues()`
def find_sibling_project_path(raw_val: str, project_root: Path, daily_root: Path) -> Path | None:
	r: Path | None = None
	try:
		candidate = Path(raw_val).resolve()
	except OSError:
		candidate = None
	if None is not candidate and candidate.is_relative_to(daily_root):
		allowed = (project_root, *_rename_lineage_roots(project_root))
		if not any((candidate.is_relative_to(root_p) or root_p.is_relative_to(candidate) for root_p in allowed)):
			r = candidate
	return r
# @used-by :func:`agent_tools.project_rename._sync_registrations()`
def refresh_workflow_file_hash(new_root: Path, target_file: Path, old_sha: str | None) -> None:
	new_sha = capture_file_sha(target_file)
	if old_sha and new_sha and old_sha != new_sha:
		wf_path = project_paths(new_root, exact_root=True).data_dir / 'workflow.json'
		_rewrite_json_file(wf_path, [(old_sha, new_sha)])
# @used-by :func:`agent_tools.path_registry.same_project_root()`
def same_project_root_check(first: str | Path | None, second: str | Path | None, canon_fn, key_fn) -> bool:
	r = False
	if None is not first and None is not second:
		s1, s2 = (str(first).strip(), str(second).strip())
		if s1 and s2 and (not (isinstance(first, str) and (not Path(s1).is_absolute()))) and (not (isinstance(second, str) and (not Path(s2).is_absolute()))):
			try:
				c1, c2 = (canon_fn(s1), canon_fn(s2))
				if key_fn(c1) == key_fn(c2):
					r = True
				else:
					r = (c1.is_dir() and (not c2.is_dir()) and _has_rename_lineage(c1, c2)) or (c2.is_dir() and (not c1.is_dir()) and _has_rename_lineage(c2, c1))
			except (OSError, ValueError):
				r = False
	return r
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
# @used-by :func:`agent_tools.journal.same_journal_identity()`
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
