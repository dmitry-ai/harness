# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.Issue.Linter import Linter
from Df.Harness.lib.shell import _GITHUB_ISSUE_URL_RE, dfh_parse_issue_url
import json
import re
_HASH_ISSUE_REF_RE = re.compile(r'(?<![A-Za-z0-9_/])#(\d+)\b')
_USER_REQUEST_BLOCK_RE = re.compile(r'<USER_REQUEST>\r?\n([\s\S]*?)\r?\n</USER_REQUEST>')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IssueFirstEvaluator:
	# @used-by :func:`agent_tools.issue_first_gate.evaluate_issue_first_events()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.__check_pending_target()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.evaluate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_b.DfHarnessS11Wave2CCovIssuesBTests.test_issue_first_pretool_evaluator_bg_scanner_and_var_match()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_first_evaluator_inheritor_and_pretool()`
	def __init__(self, events: list[dict] | tuple[dict, ...] | None, *, requests: list | tuple | None=None, project_root: Path | None=None) -> None:
		self.__events = events or ()
		self.__requests = requests
		self.__project_root = project_root
		self.__known_repos: dict[str, tuple[str, list[Path]]] = {}
		self.__seeded_parents: dict[str, dict[int, tuple[int, int | None]]] = {}
		self.__seeded_children: dict[str, dict[int, int]] = {}
		self.__repos: dict[str, dict] = {}
		self.__violations: list[str] = []
	# @used-by :meth:`IssueFirstEvaluator.__handle_create_action()`
	# @used-by :meth:`IssueFirstEvaluator.__handle_open_action()`
	def __activate_child_parent(self, st: dict, num: int, parent_num: int, step: int, sub_step: int | None, cand_repos: list[Path], *, report_closed: bool) -> None:
		st['child_to_parent'][num] = parent_num
		if parent_num not in st['active_parents']:
			pinfo = self.__load_evidence_info(st['repo_slug'], parent_num, cand_repos)
			if None is not pinfo and 'open' == pinfo.get('state') and parent_num not in st['closed_parents']:
				st['active_parents'][parent_num] = (step, sub_step)
				if parent_num not in st['established_parents']:
					st['established_parents'].append(parent_num)
			elif report_closed and None is not pinfo and 'closed' == pinfo.get('state'):
				slug = st['repo_slug']
				self.__violations.append(f'EXEC-5 ISSUE-FIRST-GATE: Child issue https://github.com/{slug}/issues/{num} links to closed parent issue #{parent_num}; open a new parent problem issue before working on new changes.')
	# @used-by :meth:`IssueFirstEvaluator.evaluate()`
	def __collect_known_repos(self) -> None:
		for ev in self.__events:
			if isinstance(ev, dict):
				self.__register_known_repo(ev)
	# @used-by :meth:`IssueFirstEvaluator.__handle_code_write()`
	# @used-by :meth:`IssueFirstEvaluator.__handle_issue_action()`
	def __ensure_repo(self, slug: str, repo_root: str | None=None) -> dict:
		key = slug.lower()
		st = self.__repos.get(key)
		if None is st:
			canon_slug = self.__known_repos.get(key, (slug, []))[0]
			st = {'repo_slug': canon_slug, 'repo_root': repo_root or '', 'active_parents': dict(self.__seeded_parents.get(key) or {}), 'closed_parents': set(), 'established_parents': sorted(self.__seeded_parents.get(key) or ()), 'child_to_parent': dict(self.__seeded_children.get(key) or {}), 'unauthorized_write_steps': [], 'code_write_count': 0, 'issue_action_count': 0}
			self.__repos[key] = st
		elif repo_root and (not st['repo_root']):
			st['repo_root'] = repo_root
		return st
	# @used-by :meth:`IssueFirstEvaluator.__parse_evidence_file()`
	@staticmethod
	def __extract_evidence_parent(data: dict, iss_obj: dict, slug: str, number: int) -> int | None:
		raw_p = data.get('parent_number')
		if not isinstance(raw_p, int) or isinstance(raw_p, bool):
			raw_p = iss_obj.get('parent_number')
		if not isinstance(raw_p, int) or isinstance(raw_p, bool):
			raw_p = Linter.extract_parent_number(str(iss_obj.get('body') or ''), slug)
		return int(raw_p) if isinstance(raw_p, int) and (not isinstance(raw_p, bool)) and int(raw_p) != int(number) else None
	# @used-by :meth:`IssueFirstEvaluator.__seed_from_requests()`
	def __extract_request_refs(self, combined: str) -> dict[str, set[int]]:
		refs: dict[str, set[int]] = {}
		for url in _GITHUB_ISSUE_URL_RE.findall(combined):
			parsed = dfh_parse_issue_url(url)
			if None is not parsed:
				slug_u, num_u = parsed
				if slug_u.lower() in self.__known_repos:
					refs.setdefault(slug_u.lower(), set()).add(int(num_u))
		hash_nums = {int(m.group(1)) for m in _HASH_ISSUE_REF_RE.finditer(combined)}
		if hash_nums:
			for slug_key in self.__known_repos:
				refs.setdefault(slug_key, set()).update(hash_nums)
		return refs
	# @used-by :meth:`IssueFirstEvaluator.__seed_from_requests()`
	@staticmethod
	def __extract_request_text(req) -> str:
		raw = req if isinstance(req, str) else str(req.get('text') or req.get('content') or '') if isinstance(req, dict) else ''
		m = _USER_REQUEST_BLOCK_RE.search(raw)
		return m.group(1) if m else raw
	# @used-by :meth:`IssueFirstEvaluator.__handle_code_write()`
	@staticmethod
	def __format_write_violation(cls_name: str, rel_path: str, slug: str, step: int) -> str:
		if 'test' == cls_name:
			r = f'EXEC-5 ISSUE-FIRST-GATE: Test file "{rel_path}" in {slug} edited at step {step} before establishing an open parent GitHub issue. State the problem as a parent GitHub issue via df_github_issue.py create --repo {slug} (or fetch an existing open issue via df_github_issue.py fetch --repo {slug} --issue <N>) BEFORE developing tests or code.'
		elif 'production' == cls_name:
			r = f'EXEC-5 ISSUE-FIRST-GATE: Production code "{rel_path}" in {slug} edited at step {step} before establishing an open parent GitHub issue. State the problem as a parent GitHub issue via df_github_issue.py create --repo {slug} BEFORE writing tests or production code.'
		else:
			r = f'EXEC-5 ISSUE-FIRST-GATE: Repository file "{rel_path}" in {slug} edited at step {step} before establishing an open parent GitHub issue. State the problem as a parent GitHub issue via df_github_issue.py create --repo {slug} BEFORE editing repository files.'
		return r
	# @used-by :meth:`IssueFirstEvaluator.__handle_issue_action()`
	@staticmethod
	def __handle_close_action(st: dict, num: int, parent_num: int | None) -> None:
		if num in st['active_parents']:
			st['active_parents'].pop(num, None)
			st['closed_parents'].add(num)
		elif None is parent_num:
			st['closed_parents'].add(num)
	# @used-by :meth:`IssueFirstEvaluator.evaluate()`
	def __handle_code_write(self, ev: dict, step: int, sub_step: int | None) -> None:
		slug = str(ev.get('repo_slug') or '').strip()
		if slug:
			st = self.__ensure_repo(slug, str(ev.get('repo_root') or ''))
			st['code_write_count'] += 1
			rel_path = str(ev.get('rel_path') or Path(str(ev.get('path') or '')).name)
			cls_name = str(ev.get('classification') or 'production')
			if not any((self.__is_established_before(est, step, sub_step) for est in st['active_parents'].values())):
				st['unauthorized_write_steps'].append(step)
				self.__violations.append(self.__format_write_violation(cls_name, rel_path, st['repo_slug'], step))
	# @used-by :meth:`IssueFirstEvaluator.__handle_issue_action()`
	def __handle_create_action(self, st: dict, num: int, parent_num: int | None, step: int, sub_step: int | None, cand_repos: list[Path]) -> None:
		if None is parent_num:
			if st['unauthorized_write_steps'] and (not st['active_parents']):
				first_bad = st['unauthorized_write_steps'][0]
				slug = st['repo_slug']
				self.__violations.append(f'EXEC-5 ISSUE-FIRST-GATE: Parent issue https://github.com/{slug}/issues/{num} was created at step {step} AFTER code/test edits already occurred at step {first_bad}. State the problem as a parent GitHub issue BEFORE writing tests or code.')
			st['active_parents'][num] = (step, sub_step)
			if num not in st['established_parents']:
				st['established_parents'].append(num)
		else:
			self.__activate_child_parent(st, num, parent_num, step, sub_step, cand_repos, report_closed=True)
	# @used-by :meth:`IssueFirstEvaluator.evaluate()`
	def __handle_issue_action(self, ev: dict, step: int, sub_step: int | None) -> None:
		slug, num, action = (str(ev.get('repo') or '').strip(), ev.get('number'), str(ev.get('action') or '').strip().lower())
		if slug and isinstance(num, int) and (not isinstance(num, bool)) and action:
			st = self.__ensure_repo(slug)
			st['issue_action_count'] += 1
			cand_repos = self.__known_repos.get(slug.lower(), (slug, []))[1]
			ev_info = self.__load_evidence_info(st['repo_slug'], num, cand_repos)
			parent_num = self.__resolve_action_parent(ev, st, num, ev_info)
			raw_state = self.__resolve_action_state(ev, action, ev_info)
			if 'create' == action:
				self.__handle_create_action(st, num, parent_num, step, sub_step, cand_repos)
			elif action in ('fetch', 'edit', 'comment'):
				self.__handle_open_action(st, num, parent_num, raw_state, step, sub_step, cand_repos)
			elif 'close' == action:
				self.__handle_close_action(st, num, parent_num)
	# @used-by :meth:`IssueFirstEvaluator.__handle_issue_action()`
	def __handle_open_action(self, st: dict, num: int, parent_num: int | None, raw_state: str, step: int, sub_step: int | None, cand_repos: list[Path]) -> None:
		if 'open' == raw_state:
			if None is parent_num:
				if num not in st['active_parents']:
					st['active_parents'][num] = (step, sub_step)
				if num not in st['established_parents']:
					st['established_parents'].append(num)
			else:
				self.__activate_child_parent(st, num, parent_num, step, sub_step, cand_repos, report_closed=False)
	# @used-by :meth:`IssueFirstEvaluator.__handle_code_write()`
	@staticmethod
	def __is_established_before(est: tuple[int, int | None], step: int, sub_step: int | None) -> bool:
		est_step, est_sub = est
		return est_step < step or (est_step == step and None is not est_sub and None is not sub_step and est_sub < sub_step)
	# @used-by :meth:`IssueFirstEvaluator.__activate_child_parent()`
	# @used-by :meth:`IssueFirstEvaluator.__handle_issue_action()`
	# @used-by :meth:`IssueFirstEvaluator.__seed_single_ref()`
	def __load_evidence_info(self, slug: str, number: int, candidate_repos: list[Path]) -> dict | None:
		base = Path(self.__project_root).resolve() if None is not self.__project_root else candidate_repos[0] if candidate_repos else Path.cwd().resolve()
		r: dict | None = None
		for ev_path in EvidenceWorkspace.evidence_issue_files(base, slug, f'issue-{int(number)}.json', candidate_repos=candidate_repos):
			info = self.__parse_evidence_file(ev_path, slug, number)
			if None is not info:
				r = info
				break
		return r
	# @used-by :meth:`IssueFirstEvaluator.__load_evidence_info()`
	@classmethod
	def __parse_evidence_file(cls, ev_path: Path, slug: str, number: int) -> dict | None:
		r: dict | None = None
		try:
			data = json.loads(ev_path.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			data = None
		if isinstance(data, dict):
			iss_obj = data.get('issue') if isinstance(data.get('issue'), dict) else data
			if isinstance(iss_obj, dict):
				state = str(iss_obj.get('state') or data.get('state') or '').strip().lower()
				pnum = cls.__extract_evidence_parent(data, iss_obj, slug, number)
				r = {'number': int(number), 'state': state or None, 'parent_number': pnum, 'path': str(ev_path)}
		return r
	# @used-by :meth:`IssueFirstEvaluator.__collect_known_repos()`
	def __register_known_repo(self, ev: dict) -> None:
		kind = ev.get('kind')
		if 'code_write' == kind:
			slug = str(ev.get('repo_slug') or '').strip()
			rroot_raw = str(ev.get('repo_root') or '').strip()
			if slug:
				entry = self.__known_repos.setdefault(slug.lower(), (slug, []))
				if rroot_raw:
					rp = Path(rroot_raw).resolve()
					if rp not in entry[1]:
						entry[1].append(rp)
		elif 'issue_action' == kind:
			slug = str(ev.get('repo') or '').strip()
			if slug:
				self.__known_repos.setdefault(slug.lower(), (slug, []))
	# @used-by :meth:`IssueFirstEvaluator.__handle_issue_action()`
	@staticmethod
	def __resolve_action_parent(ev: dict, st: dict, num: int, ev_info: dict | None) -> int | None:
		raw_p = ev.get('parent_number')
		if isinstance(raw_p, int) and (not isinstance(raw_p, bool)) and int(raw_p) != num:
			r: int | None = int(raw_p)
		else:
			r = ev_info.get('parent_number') if None is not ev_info else st['child_to_parent'].get(num)
		return r
	# @used-by :meth:`IssueFirstEvaluator.__handle_issue_action()`
	@staticmethod
	def __resolve_action_state(ev: dict, action: str, ev_info: dict | None) -> str:
		raw_state = str(ev.get('state') or '').strip().lower()
		if not raw_state:
			if 'create' == action:
				raw_state = 'open'
			elif 'close' == action:
				raw_state = 'closed'
			elif None is not ev_info and ev_info.get('state'):
				raw_state = str(ev_info['state']).lower()
		return raw_state
	# @used-by :meth:`IssueFirstEvaluator.evaluate()`
	def __seed_from_requests(self) -> None:
		if self.__requests and self.__known_repos:
			combined = '\n'.join((self.__extract_request_text(req) for req in self.__requests if req))
			if combined.strip():
				for slug_key, nums in self.__extract_request_refs(combined).items():
					canon_slug, cand_repos = self.__known_repos[slug_key]
					for num in sorted(nums):
						self.__seed_single_ref(slug_key, canon_slug, cand_repos, num)
	# @used-by :meth:`IssueFirstEvaluator.__seed_from_requests()`
	def __seed_single_ref(self, slug_key: str, canon_slug: str, cand_repos: list[Path], num: int) -> None:
		info = self.__load_evidence_info(canon_slug, num, cand_repos)
		if None is not info and 'open' == info.get('state'):
			pnum = info.get('parent_number')
			if None is pnum:
				self.__seeded_parents.setdefault(slug_key, {})[num] = (-1, None)
			else:
				pinfo = self.__load_evidence_info(canon_slug, pnum, cand_repos)
				if None is not pinfo and 'open' == pinfo.get('state'):
					self.__seeded_parents.setdefault(slug_key, {})[pnum] = (-1, None)
					self.__seeded_children.setdefault(slug_key, {})[num] = pnum
	# @used-by :meth:`IssueFirstEvaluator.evaluate()`
	def __serialize_repos(self) -> dict[str, dict]:
		return {key: {'repo_slug': st['repo_slug'], 'repo_root': st['repo_root'], 'active_parents': sorted(st['active_parents'].keys()), 'established_parents': list(st['established_parents']), 'closed_parents': sorted(st['closed_parents']), 'code_write_count': st['code_write_count'], 'issue_action_count': st['issue_action_count']} for key, st in sorted(self.__repos.items())}
	# @used-by :func:`agent_tools.issue_first_gate.evaluate_issue_first_events()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.__check_pending_target()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.evaluate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_b.DfHarnessS11Wave2CCovIssuesBTests.test_issue_first_pretool_evaluator_bg_scanner_and_var_match()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_issue_first_evaluator_inheritor_and_pretool()`
	def evaluate(self) -> dict:
		self.__collect_known_repos()
		self.__seed_from_requests()
		for ev in self.__events:
			if not isinstance(ev, dict):
				continue
			kind = ev.get('kind')
			step = int(ev.get('step', 0))
			raw_sub = ev.get('sub_step')
			sub_step = int(raw_sub) if None is not raw_sub else None
			if 'code_write' == kind:
				self.__handle_code_write(ev, step, sub_step)
			elif 'issue_action' == kind:
				self.__handle_issue_action(ev, step, sub_step)
		return {'verified': not self.__violations, 'repos': self.__serialize_repos(), 'violations': self.__violations}
