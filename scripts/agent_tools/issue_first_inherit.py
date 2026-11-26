# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Support parent-issue inheritance and worktree-scoped TDD keys for coding fan-out":
# https://github.com/dmitry-ai/harness/issues/351
from __future__ import annotations
from pathlib import Path
from .github_issue import extract_parent_issue_number
from .hook_runtime import iter_turn_state_files
from .issues.workspace import IssueEvidenceWorkspace
import json
import re
import sqlite3
_SENDER_UUID_RE = re.compile(r'\bsender=([a-f0-9-]{36})\b', re.I)
# @used-by :func:`_find_parent_from_summary_db()`
# @used-by :func:`_resolve_parent_context()`
def _brain_dir_and_cid(t_path: Path | None) -> tuple[Path | None, str | None]:
	r: tuple[Path | None, str | None] = (None, None)
	if None is not t_path:
		parts = t_path.parts
		for idx, part in enumerate(parts):
			if 'brain' == part.lower() and idx + 1 < len(parts):
				r = (Path(*parts[:idx + 1]), parts[idx + 1])
				break
	return r
# @used-by :func:`has_inherited_open_parent_issue()`
def _candidate_project_roots(repo_root: Path, cwd: Path | None) -> list[Path]:
	from .path_registry import project_paths
	seeds: list[Path] = []
	for raw in (cwd, repo_root, repo_root.parent):
		if None is not raw:
			rp = Path(raw).resolve()
			seeds.append(rp)
			wt_proj = _worktree_project_root(rp)
			if None is not wt_proj:
				seeds.append(wt_proj)
			try:
				seeds.append(project_paths(rp).root)
			except (OSError, ValueError):
				pass
	return list(dict.fromkeys(seeds))
# @used-by :func:`_is_verified_open_parent()`
def _evidence_issue_data(ev_dirs: list[Path], slug: str, number: int) -> dict | None:
	safe = slug.replace('/', '__')
	r: dict | None = None
	for base in ev_dirs:
		cand = base / safe / f'issue-{int(number)}.json'
		if cand.is_file():
			try:
				loaded = json.loads(cand.read_text(encoding='utf-8'))
				if isinstance(loaded, dict):
					r = loaded
					break
			except (OSError, ValueError):
				continue
	return r
# @used-by :func:`_is_verified_open_parent()`
def _evidence_parent_number(data: dict, iss: dict, slug: str, number: int) -> int | None:
	raw = _int_or_none(data.get('parent_number'))
	if None is raw:
		raw = _int_or_none(iss.get('parent_number'))
	if None is raw:
		raw = _int_or_none(extract_parent_issue_number(str(iss.get('body') or ''), slug))
	return raw if None is not raw and raw != int(number) else None
# @used-by :func:`_iter_candidate_issue_nums()`
def _extract_issue_nums_from_turn(tdata: dict, slug_key: str) -> list[int]:
	ifc_repo = ((tdata.get('issue_first_check') or {}).get('repos') or {}).get(slug_key)
	active = ifc_repo.get('active_parents') or () if isinstance(ifc_repo, dict) else ()
	nums = {n for n in (_int_or_none(x) for x in active) if None is not n}
	nums.update(_extract_turn_gh_nums(tdata.get('github_issues'), slug_key))
	return sorted(nums)
# @used-by :func:`_extract_issue_nums_from_turn()`
def _extract_turn_gh_nums(gh_raw, slug_key: str) -> set[int]:
	items = gh_raw.values() if isinstance(gh_raw, dict) else (gh_raw if isinstance(gh_raw, list) else ())
	nums: set[int] = set()
	for item in items:
		if isinstance(item, dict) and str(item.get('repo') or '').strip().lower() == slug_key and 'open' == str(item.get('state') or '').strip().lower():
			cand = _int_or_none(item.get('parent_number'))
			if None is cand:
				cand = _int_or_none(item.get('number'))
			if None is not cand:
				nums.add(cand)
	return nums
# @used-by :func:`_resolve_parent_context()`
def _find_parent_from_summary_db(t_path: Path | None, child_cid: str) -> str | None:
	r: str | None = None
	brain_dir, _ = _brain_dir_and_cid(t_path)
	db_path = brain_dir.parent / 'conversation_summaries.db' if None is not brain_dir else None
	if None is not db_path and db_path.is_file() and child_cid:
		conn = None
		try:
			conn = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)
			cols = {row[1] for row in conn.execute('PRAGMA table_info(conversation_summaries)')}
			if {'conversation_id', 'parent_conversation_id'}.issubset(cols):
				row = conn.execute('SELECT parent_conversation_id FROM conversation_summaries WHERE lower(conversation_id)=?', (child_cid.lower(),)).fetchone()
				if row and row[0]:
					r = str(row[0]).strip() or None
		except sqlite3.Error:
			r = None
		finally:
			if None is not conn:
				conn.close()
	return r
# @used-by :func:`_resolve_parent_context()`
def _find_parent_from_transcript(t_path: Path | None) -> tuple[bool, str | None]:
	rows = _read_transcript_rows(t_path)
	if not rows or any(('USER_INPUT' == row.get('type') for row in rows)):
		r: tuple[bool, str | None] = (False, None)
	else:
		sender: str | None = None
		saw_sys = False
		for row in rows:
			if row.get('type') in ('SYSTEM_MESSAGE', 'EPHEMERAL_MESSAGE'):
				saw_sys = True
				m = _SENDER_UUID_RE.search(str(row.get('content') or ''))
				if None is not m:
					sender = m.group(1)
					break
		r = (saw_sys, sender)
	return r
# @used-by :func:`_evidence_parent_number()`
# @used-by :func:`_extract_issue_nums_from_turn()`
# @used-by :func:`_extract_turn_gh_nums()`
def _int_or_none(val) -> int | None:
	return int(val) if isinstance(val, int) and (not isinstance(val, bool)) else None
# @used-by :func:`has_inherited_open_parent_issue()`
def _is_verified_open_parent(ev_dirs: list[Path], slug: str, number: int, depth: int=0) -> bool:
	data = _evidence_issue_data(ev_dirs, slug, number)
	r = False
	if None is not data:
		iss = data.get('issue') if isinstance(data.get('issue'), dict) else data
		if isinstance(iss, dict) and 'open' == str(iss.get('state') or data.get('state') or '').strip().lower():
			pnum = _evidence_parent_number(data, iss, slug, number)
			r = True if None is pnum else (0 == depth and _is_verified_open_parent(ev_dirs, slug, pnum, depth=1))
	return r
# @used-by :func:`has_inherited_open_parent_issue()`
def _iter_candidate_issue_nums(turn_dirs: list[Path], slug_key: str, parent_cid: str | None, child_cid: str) -> list[int]:
	nums: set[int] = set()
	for tdir in turn_dirs:
		for _, tdata in iter_turn_state_files(tdir, exclude_hyphen=True):
			if 'open' != str(tdata.get('status') or '').strip().lower() or 'primary' != str(tdata.get('role') or 'primary').strip().lower():
				continue
			tcid = str(tdata.get('conversation_id') or '').strip().lower()
			if None is not parent_cid and tcid != parent_cid.lower():
				continue
			if None is parent_cid and child_cid and tcid == child_cid.lower():
				continue
			nums.update(_extract_issue_nums_from_turn(tdata, slug_key))
	return sorted(nums)
# @used-by :func:`_find_parent_from_transcript()`
def _read_transcript_rows(t_path: Path | None) -> list[dict]:
	r: list[dict] = []
	if None is not t_path:
		eff = t_path.parent / 'transcript_full.jsonl' if 'transcript.jsonl' == t_path.name and (t_path.parent / 'transcript_full.jsonl').is_file() else t_path
		if eff.is_file():
			try:
				r = [obj for ln in eff.read_text(encoding='utf-8', errors='replace').splitlines() if ln.strip() for obj in (json.loads(ln),) if isinstance(obj, dict)]
			except (OSError, ValueError):
				r = []
	return r
# @used-by :func:`has_inherited_open_parent_issue()`
def _resolve_parent_context(payload: dict, t_path: Path | None) -> tuple[bool, str | None, str]:
	_, path_cid = _brain_dir_and_cid(t_path)
	child_cid = str(payload.get('conversationId') or payload.get('conversation_id') or path_cid or '').strip()
	explicit_p = str(payload.get('parentConversationId') or payload.get('parent_conversation_id') or '').strip()
	if explicit_p:
		r: tuple[bool, str | None, str] = (True, explicit_p, child_cid)
	else:
		db_parent = _find_parent_from_summary_db(t_path, child_cid) if child_cid else None
		if None is not db_parent:
			r = (True, db_parent, child_cid)
		else:
			tx_sub, tx_parent = _find_parent_from_transcript(t_path)
			if tx_sub:
				r = (True, tx_parent, child_cid)
			elif bool(payload.get('isSubagent')) or 'subagent' == str(payload.get('role') or '').strip().lower():
				r = (True, None, child_cid)
			else:
				r = (False, None, child_cid)
	return r
# @used-by :func:`has_inherited_open_parent_issue()`
def _turns_and_evidence_dirs(roots: list[Path]) -> tuple[list[Path], list[Path]]:
	ev_dirs: list[Path] = []
	turn_dirs: list[Path] = []
	for rt in roots:
		tgt = IssueEvidenceWorkspace.issue_target_for_path(rt)
		if None is not tgt:
			ev_dirs.append(tgt[0])
			turn_dirs.append(tgt[1])
		ev_dirs.extend((rt / '\ua616/KB/Evidence/GitHub', rt / '_/\ua616/KB/Evidence/GitHub'))
		turn_dirs.extend((rt / '\ua616/data/turns', rt / '_/\ua616/data/turns'))
	return (list(dict.fromkeys((p.resolve() for p in ev_dirs if p.is_dir()))), list(dict.fromkeys((p.resolve() for p in turn_dirs if p.is_dir()))))
# @used-by :func:`_candidate_project_roots()`
def _worktree_project_root(path: Path) -> Path | None:
	parts = path.parts
	r: Path | None = None
	for idx in range(len(parts) - 2):
		if ('\ua616', 'data', 'worktrees') == (parts[idx], parts[idx + 1].lower(), parts[idx + 2].lower()):
			base_idx = idx - 1 if 0 < idx and '_' == parts[idx - 1] else idx
			r = Path(*parts[:base_idx]).resolve() if 0 < base_idx else None
			break
	return r
# @used-by :func:`agent_tools.issue_first_gate.evaluate_pre_tool_use_issue_first()`
# @used-by :func:`missing_transcript_issue_first_error()`
def has_inherited_open_parent_issue(payload: dict, info: dict, cwd: Path | None, t_path: Path | None) -> bool:
	is_sub, parent_cid, child_cid = _resolve_parent_context(payload, t_path)
	if not is_sub:
		r = False
	else:
		slug = str(info.get('repo_slug') or '').strip()
		roots = _candidate_project_roots(Path(info['repo_root']), cwd)
		ev_dirs, turn_dirs = _turns_and_evidence_dirs(roots)
		cands = _iter_candidate_issue_nums(turn_dirs, slug.lower(), parent_cid, child_cid)
		r = any((_is_verified_open_parent(ev_dirs, slug, num) for num in cands))
	return r
# @used-by :func:`agent_tools.issue_first_gate.evaluate_pre_tool_use_issue_first()`
def missing_transcript_issue_first_error(pending_targets: list[tuple[Path, dict]], payload: dict, cwd: Path | None) -> str | None:
	r: str | None = None
	for _, info in pending_targets:
		if not has_inherited_open_parent_issue(payload, info, cwd, None):
			rel, slug = (info['rel_path'], info['repo_slug'])
			r = f'EXEC-5 ISSUE-FIRST-GATE: Cannot edit "{rel}" in {slug} without an established open parent GitHub issue (transcript unavailable). State the problem as a parent GitHub issue via df_github_issue.py create --repo {slug} BEFORE developing tests or code.'
			break
	return r
