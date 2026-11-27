# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.Issue.Linter import Linter
from agent_tools.hook_runtime import iter_turn_state_files
import json
import re
import sqlite3
_SENDER_UUID_RE = re.compile(r'\bsender=([a-f0-9-]{36})\b', re.I)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IssueFirstInheritor:
	# @used-by :func:`agent_tools.issue_first_inherit.has_inherited_open_parent_issue()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.__check_pending_target()`
	# @used-by :meth:`IssueFirstInheritor.missing_transcript_error()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_first_evaluator_inheritor_and_pretool()`
	def __init__(self, payload: dict, info: dict, cwd: Path | None, t_path: Path | None) -> None:
		self.__payload = payload
		self.__info = info
		self.__cwd = cwd
		self.__t_path = t_path
	# @used-by :meth:`IssueFirstInheritor.__find_parent_from_db()`
	# @used-by :meth:`IssueFirstInheritor.__resolve_parent_context()`
	@staticmethod
	def __brain_dir_and_cid(t_path: Path | None) -> tuple[Path | None, str | None]:
		r: tuple[Path | None, str | None] = (None, None)
		if None is not t_path:
			parts = t_path.parts
			for idx, part in enumerate(parts):
				if 'brain' == part.lower() and idx + 1 < len(parts):
					r = (Path(*parts[:idx + 1]), parts[idx + 1])
					break
		return r
	# @used-by :meth:`IssueFirstInheritor.has_inherited_open_parent()`
	@classmethod
	def __candidate_project_roots(cls, repo_root: Path, cwd: Path | None) -> list[Path]:
		from agent_tools.path_registry import project_paths
		seeds: list[Path] = []
		for raw in (cwd, repo_root, repo_root.parent):
			if None is not raw:
				rp = Path(raw).resolve()
				seeds.append(rp)
				wt_proj = cls.__worktree_project_root(rp)
				if None is not wt_proj:
					seeds.append(wt_proj)
				try:
					seeds.append(project_paths(rp).root)
				except (OSError, ValueError):
					pass
		return list(dict.fromkeys(seeds))
	# @used-by :meth:`IssueFirstInheritor.__is_verified_open_parent()`
	@staticmethod
	def __evidence_issue_data(ev_dirs: list[Path], slug: str, number: int) -> dict | None:
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
	# @used-by :meth:`IssueFirstInheritor.__is_verified_open_parent()`
	@classmethod
	def __evidence_parent_number(cls, data: dict, iss: dict, slug: str, number: int) -> int | None:
		raw = cls.__int_or_none(data.get('parent_number'))
		if None is raw:
			raw = cls.__int_or_none(iss.get('parent_number'))
		if None is raw:
			raw = cls.__int_or_none(Linter.extract_parent_number(str(iss.get('body') or ''), slug))
		return raw if None is not raw and raw != int(number) else None
	# @used-by :meth:`IssueFirstInheritor.__iter_candidate_issue_nums()`
	@classmethod
	def __extract_issue_nums_from_turn(cls, tdata: dict, slug_key: str) -> list[int]:
		ifc_repo = ((tdata.get('issue_first_check') or {}).get('repos') or {}).get(slug_key)
		active = ifc_repo.get('active_parents') or () if isinstance(ifc_repo, dict) else ()
		nums = {n for n in (cls.__int_or_none(x) for x in active) if None is not n}
		nums.update(cls.__extract_turn_gh_nums(tdata.get('github_issues'), slug_key))
		return sorted(nums)
	# @used-by :meth:`IssueFirstInheritor.__extract_issue_nums_from_turn()`
	@classmethod
	def __extract_turn_gh_nums(cls, gh_raw, slug_key: str) -> set[int]:
		items = gh_raw.values() if isinstance(gh_raw, dict) else gh_raw if isinstance(gh_raw, list) else ()
		nums: set[int] = set()
		for item in items:
			if isinstance(item, dict) and str(item.get('repo') or '').strip().lower() == slug_key and 'open' == str(item.get('state') or '').strip().lower():
				cand = cls.__int_or_none(item.get('parent_number'))
				if None is cand:
					cand = cls.__int_or_none(item.get('number'))
				if None is not cand:
					nums.add(cand)
		return nums
	# @used-by :meth:`IssueFirstInheritor.__resolve_from_db_or_tx()`
	@classmethod
	def __find_parent_from_db(cls, t_path: Path | None, child_cid: str) -> str | None:
		r: str | None = None
		brain_dir, _ = cls.__brain_dir_and_cid(t_path)
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
	# @used-by :meth:`IssueFirstInheritor.__resolve_from_db_or_tx()`
	@classmethod
	def __find_parent_from_tx(cls, t_path: Path | None) -> tuple[bool, str | None]:
		rows = cls.__read_transcript_rows(t_path)
		if not rows or any(('USER_INPUT' == row.get('type') for row in rows)):
			r: tuple[bool, str | None] = (False, None)
		else:
			sender, saw_sys = (None, False)
			for row in rows:
				if row.get('type') in ('SYSTEM_MESSAGE', 'EPHEMERAL_MESSAGE'):
					saw_sys = True
					m = _SENDER_UUID_RE.search(str(row.get('content') or ''))
					if None is not m:
						sender = m.group(1)
						break
			r = (saw_sys, sender)
		return r
	# @used-by :meth:`IssueFirstInheritor.__evidence_parent_number()`
	# @used-by :meth:`IssueFirstInheritor.__extract_issue_nums_from_turn()`
	# @used-by :meth:`IssueFirstInheritor.__extract_turn_gh_nums()`
	@staticmethod
	def __int_or_none(val) -> int | None:
		return int(val) if isinstance(val, int) and (not isinstance(val, bool)) else None
	# @used-by :meth:`IssueFirstInheritor.has_inherited_open_parent()`
	@classmethod
	def __is_verified_open_parent(cls, ev_dirs: list[Path], slug: str, number: int, depth: int=0) -> bool:
		data = cls.__evidence_issue_data(ev_dirs, slug, number)
		r = False
		if None is not data:
			iss = data.get('issue') if isinstance(data.get('issue'), dict) else data
			if isinstance(iss, dict) and 'open' == str(iss.get('state') or data.get('state') or '').strip().lower():
				pnum = cls.__evidence_parent_number(data, iss, slug, number)
				r = True if None is pnum else 0 == depth and cls.__is_verified_open_parent(ev_dirs, slug, pnum, depth=1)
		return r
	# @used-by :meth:`IssueFirstInheritor.has_inherited_open_parent()`
	@classmethod
	def __iter_candidate_issue_nums(cls, turn_dirs: list[Path], slug_key: str, parent_cid: str | None, child_cid: str) -> list[int]:
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
				nums.update(cls.__extract_issue_nums_from_turn(tdata, slug_key))
		return sorted(nums)
	# @used-by :meth:`IssueFirstInheritor.__find_parent_from_tx()`
	@staticmethod
	def __read_transcript_rows(t_path: Path | None) -> list[dict]:
		r: list[dict] = []
		if None is not t_path:
			eff = t_path.parent / 'transcript_full.jsonl' if 'transcript.jsonl' == t_path.name and (t_path.parent / 'transcript_full.jsonl').is_file() else t_path
			if eff.is_file():
				try:
					r = [obj for ln in eff.read_text(encoding='utf-8', errors='replace').splitlines() if ln.strip() for obj in (json.loads(ln),) if isinstance(obj, dict)]
				except (OSError, ValueError):
					r = []
		return r
	# @used-by :meth:`IssueFirstInheritor.__resolve_parent_context()`
	def __resolve_from_db_or_tx(self, child_cid: str) -> tuple[bool, str | None, str]:
		db_parent = self.__find_parent_from_db(self.__t_path, child_cid) if child_cid else None
		if None is not db_parent:
			r: tuple[bool, str | None, str] = (True, db_parent, child_cid)
		else:
			tx_sub, tx_parent = self.__find_parent_from_tx(self.__t_path)
			if tx_sub:
				r = (True, tx_parent, child_cid)
			elif bool(self.__payload.get('isSubagent')) or 'subagent' == str(self.__payload.get('role') or '').strip().lower():
				r = (True, None, child_cid)
			else:
				r = (False, None, child_cid)
		return r
	# @used-by :meth:`IssueFirstInheritor.has_inherited_open_parent()`
	def __resolve_parent_context(self) -> tuple[bool, str | None, str]:
		_, path_cid = self.__brain_dir_and_cid(self.__t_path)
		child_cid = str(self.__payload.get('conversationId') or self.__payload.get('conversation_id') or path_cid or '').strip()
		explicit_p = str(self.__payload.get('parentConversationId') or self.__payload.get('parent_conversation_id') or '').strip()
		return (True, explicit_p, child_cid) if explicit_p else self.__resolve_from_db_or_tx(child_cid)
	# @used-by :meth:`IssueFirstInheritor.has_inherited_open_parent()`
	@staticmethod
	def __turns_and_evidence_dirs(roots: list[Path]) -> tuple[list[Path], list[Path]]:
		ev_dirs: list[Path] = []
		turn_dirs: list[Path] = []
		for rt in roots:
			tgt = EvidenceWorkspace.issue_target_for_path(rt)
			if None is not tgt:
				ev_dirs.append(tgt[0])
				turn_dirs.append(tgt[1])
			ev_dirs.extend((rt / '\ua616/KB/Evidence/GitHub', rt / '_/\ua616/KB/Evidence/GitHub'))
			turn_dirs.extend((rt / '\ua616/data/turns', rt / '_/\ua616/data/turns'))
		return (list(dict.fromkeys((p.resolve() for p in ev_dirs if p.is_dir()))), list(dict.fromkeys((p.resolve() for p in turn_dirs if p.is_dir()))))
	# @used-by :meth:`IssueFirstInheritor.__candidate_project_roots()`
	@staticmethod
	def __worktree_project_root(path: Path) -> Path | None:
		parts = path.parts
		r: Path | None = None
		for idx in range(len(parts) - 2):
			if ('\ua616', 'data', 'worktrees') == (parts[idx], parts[idx + 1].lower(), parts[idx + 2].lower()):
				base_idx = idx - 1 if 0 < idx and '_' == parts[idx - 1] else idx
				r = Path(*parts[:base_idx]).resolve() if 0 < base_idx else None
				break
		return r
	# @used-by :func:`agent_tools.issue_first_inherit.has_inherited_open_parent_issue()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.__check_pending_target()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_first_evaluator_inheritor_and_pretool()`
	def has_inherited_open_parent(self) -> bool:
		is_sub, parent_cid, child_cid = self.__resolve_parent_context()
		if not is_sub:
			r = False
		else:
			slug = str(self.__info.get('repo_slug') or '').strip()
			roots = self.__candidate_project_roots(Path(self.__info['repo_root']), self.__cwd)
			ev_dirs, turn_dirs = self.__turns_and_evidence_dirs(roots)
			cands = self.__iter_candidate_issue_nums(turn_dirs, slug.lower(), parent_cid, child_cid)
			r = any((self.__is_verified_open_parent(ev_dirs, slug, num) for num in cands))
		return r
	# @used-by :func:`agent_tools.issue_first_inherit.missing_transcript_issue_first_error()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.evaluate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_first_evaluator_inheritor_and_pretool()`
	@classmethod
	def missing_transcript_error(cls, pending_targets: list[tuple[Path, dict]], payload: dict, cwd: Path | None) -> str | None:
		r: str | None = None
		for _, info in pending_targets:
			if not cls(payload, info, cwd, None).has_inherited_open_parent():
				rel, slug = (info['rel_path'], info['repo_slug'])
				r = f'EXEC-5 ISSUE-FIRST-GATE: Cannot edit "{rel}" in {slug} without an established open parent GitHub issue (transcript unavailable). State the problem as a parent GitHub issue via df_github_issue.py create --repo {slug} BEFORE developing tests or code.'
				break
		return r
