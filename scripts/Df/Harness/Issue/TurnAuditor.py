# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.Git.WorktreePathResolver import WorktreePathResolver
from Df.Harness.Issue.CompetingTurnChecker import CompetingTurnChecker
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.Issue.Linter import Linter
from Df.Harness.Issue.ParityAuditor import ParityAuditor
from Df.Harness.Issue.ReadCache import ReadCache
from Df.Harness.Issue.RepoLocator import V2_CODE_RELS
from Df.Harness.Issue.ScopeCompletenessChecker import ScopeCompletenessChecker
from Df.Harness.lib.issue_turn import dfh_extract_implemented_m_roots, dfh_filter_turn_state_items, dfh_merge_turn_issue_item, dfh_verify_multi_subtask_counts
from Df.Harness.lib.shell import ISSUE_LINKED_CODE_SUFFIXES, dfh_extract_comment_issue_urls, dfh_extract_issue_urls, dfh_parse_issue_url
from agent_tools.source_grounding import local_source_grounding_issues
import json
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class TurnAuditor:
	# @used-by :func:`agent_tools.issue_lifecycle._check_multi_subtask_decomposition()`
	# @used-by :func:`agent_tools.issue_lifecycle.code_and_issue_lifecycle_status()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_parity_and_scope_completeness()`
	def __init__(self, root: Path, turn: dict, turn_state: dict | None=None, response=None, *, workspace: EvidenceWorkspace | None=None, linter: Linter | None=None) -> None:
		self.root, self.turn, self.turn_state, self.response = (Path(root).resolve(), turn, turn_state, response)
		self.workspace = workspace if None is not workspace else EvidenceWorkspace()
		self.linter = linter if None is not linter else Linter()
		self.violations: list[str] = []
		self.warnings: list[str] = []
		self.checked_issues: list[dict] = []
		self.checked_urls: set[str] = set()
		self.repo_touched: dict[Path, set[str]] = {}
		self.candidate_repos: list[Path] = []
		self.workspace_code_repos: set[Path] = set()
		self.turn_issues: dict[str, dict] = {}
		self.git_cache = ReadCache()
	# @used-by :func:`agent_tools.issue_lifecycle._check_multi_subtask_decomposition()`
	def __getattr__(self, name: str):
		aliases = {'_check_multi_subtask_decomposition': self.check_multi_subtask_decomposition, '_inspect_touched_code_file': self.inspect_touched_code_file, '_resolve_parent_number': self.resolve_parent_number}
		if name in aliases:
			r = aliases[name]
		else:
			raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
		return r
	# @used-by :meth:`TurnAuditor.__collect_repos_and_issues()`
	def __bind_issue_repos(self) -> tuple[dict[Path, set[str]], dict[str, Path]]:
		for info in self.turn_issues.values():
			found = self.workspace.find_local_code_repo(info['repo'], project_root=self.root)
			if None is not found and RepoGate(found.resolve()).is_issue_tracked() and found.resolve() not in self.candidate_repos:
				self.candidate_repos.append(found.resolve())
		required_by_repo: dict[Path, set[str]] = {rep: set() for rep in self.candidate_repos}
		repo_by_url: dict[str, Path] = {}
		for url, info in self.turn_issues.items():
			for cand in self.candidate_repos:
				slug = self.workspace.origin_repo_slug(cand)
				if slug and slug.lower() == info['repo'].lower():
					repo_by_url[url] = cand
					if 'close' == info.get('last_action'):
						required_by_repo.setdefault(cand, set()).add(url)
						self.repo_touched.setdefault(cand, set())
		return (required_by_repo, repo_by_url)
	# @used-by :meth:`TurnAuditor.__check_turn_issue_evidence()`
	def __check_comments_evidence(self, issue_url: str, slug: str, cids: list, container_text: str | None) -> None:
		for cid in cids:
			for cp in self.workspace.evidence_issue_files(self.root, slug, f'comment-{cid}.json', self.candidate_repos)[:1]:
				try:
					c_body = str((json.loads(cp.read_text(encoding='utf-8')) or {}).get('body') or '')
				except (OSError, ValueError):
					continue
				if c_body:
					for err in self.linter.lint(c_body, is_title=False, container_text=container_text, check_structure_policy=False):
						code, msg = (err.get('code'), err.get('message'))
						self.violations.append(f'GitHub comment {issue_url}#issuecomment-{cid} lint error ({code}): {msg}')
					for g_err in local_source_grounding_issues(self.root, c_body, doc_path=cp):
						self.violations.append(f'GitHub comment {issue_url}#issuecomment-{cid} grounding error: {g_err}')
	# @used-by :meth:`TurnAuditor.audit()`
	def __check_diagnostic_audit_filing(self) -> None:
		resp = self.response
		if isinstance(resp, str) and resp.strip() and self.workspace_code_repos and (not self.repo_touched):
			has_diag = bool(re.search('(?m)(?:^|\\s|`|\\*\\*)(?:C|H)-[1-9]\\d*\\b', resp)) and bool(re.search('(?m)(?:^|\\s|`|\\*\\*)M-[1-9]\\d*\\b', resp)) and bool(re.search('\\b[A-Za-z0-9_/-]+\\.py\\b', resp))
			if has_diag:
				for ws_repo in sorted(self.workspace_code_repos, key=str):
					ws_slug = self.workspace.origin_repo_slug(ws_repo)
					if ws_slug and (not self.__has_workspace_parent_issue(ws_slug, resp)):
						self.violations.append(f'EXEC-5 / SCOPE-2: Diagnostic audit of {ws_slug} identifies repository defects (C-/H-) and remediation methods (M-) without recording a corresponding parent problem GitHub Issue via df_github_issue.py')
	# @used-by :meth:`TurnAuditor.__check_turn_issue_evidence()`
	def __check_issue_file_evidence(self, issue_url: str, slug: str, num: int, info: dict, mutated: bool) -> str | None:
		iss_files = self.workspace.evidence_issue_files(self.root, slug, f'issue-{num}.json', self.candidate_repos)
		if not iss_files and mutated:
			self.violations.append(f'GitHub issue {issue_url} is missing saved API read-back Evidence JSON (issue-{num}.json)')
		container_text = None
		for p in iss_files[:1]:
			try:
				data = json.loads(p.read_text(encoding='utf-8'))
				iss_obj = data.get('issue') if isinstance(data.get('issue'), dict) else data
				t_txt, b_txt = (str(iss_obj.get('title') or ''), str(iss_obj.get('body') or ''))
				container_text = f'{t_txt}\n{b_txt}'.strip()
				self.__lint_saved_issue_obj(issue_url, slug, num, info, iss_obj, t_txt, b_txt, p, mutated)
			except (OSError, ValueError):
				continue
		return container_text
	# @used-by :meth:`TurnAuditor.audit()`
	def __check_repo_commits_and_files(self, code_repo: Path, rel_paths: list[str], required_issues: set[str]) -> set[str]:
		from agent_tools.python_integrity import verify_touched_python_files
		from agent_tools.tdd.diff_executability import check_touched_mixed_commit_warning
		committed_urls: set[str] = set()
		if rel_paths:
			if self.git_cache.has_dirty_for_paths(code_repo, rel_paths):
				joined_r = ', '.join(rel_paths)
				self.violations.append(f'Modified files in {code_repo} are not committed: {joined_r}')
			self.violations.extend(verify_touched_python_files(code_repo, rel_paths))
			for rel in rel_paths:
				self.inspect_touched_code_file(code_repo, rel, required_issues, committed_urls)
			existing_rels = [rel for rel in rel_paths if (code_repo / rel).exists()]
			if existing_rels:
				self.__inspect_latest_commits(code_repo, existing_rels, required_issues, committed_urls)
			mixed_warn = check_touched_mixed_commit_warning(code_repo, rel_paths, project_root=self.root)
			if None is not mixed_warn:
				self.warnings.append(str(mixed_warn['message']))
		return committed_urls
	# @used-by :meth:`TurnAuditor.audit()`
	def __check_turn_issue_evidence(self, repo_by_issue_url: dict[str, Path]) -> None:
		for issue_url, info in sorted(self.turn_issues.items()):
			slug, num = (info['repo'], int(info['number']))
			mutated = info.get('last_action') in ('create', 'edit') or bool(set(info.get('actions') or ()) & {'create', 'edit'})
			eff_state = self.workspace.evidence_issue_state(self.root, slug, num, self.candidate_repos) or info.get('state') or 'open'
			if issue_url not in self.checked_urls:
				mapped = repo_by_issue_url.get(issue_url)
				self.checked_issues.append({'url': issue_url, 'repo': slug, 'number': num, 'state': eff_state, 'code_repo': str(mapped) if mapped else None, 'commit_and_push_verified': False})
				self.checked_urls.add(issue_url)
			container_text = self.__check_issue_file_evidence(issue_url, slug, num, info, mutated)
			self.__check_comments_evidence(issue_url, slug, info.get('comment_ids') or [], container_text)
	# @used-by :meth:`TurnAuditor.audit()`
	def __collect_repos_and_issues(self) -> tuple[dict[Path, set[str]], dict[str, Path]]:
		from agent_tools.path_registry import project_paths
		self.__collect_touched_repos()
		pp_root = project_paths(self.root)
		ts_cid = str((self.turn_state or {}).get('conversation_id') or '').strip()
		self.turn_issues = self.collect_turn_issues(self.turn, self.turn_state, has_competing_open_turns=CompetingTurnChecker(self.root, ts_cid).has_competing())
		self.candidate_repos = list(self.repo_touched.keys())
		ws_cands = (*pp_root.code_repos, self.root, self.root / 'code', *(self.root / rel for rel in V2_CODE_RELS), self.root.parent / 'code', *(self.root.parent / rel for rel in V2_CODE_RELS))
		self.workspace_code_repos = {c.resolve() for c in ws_cands if RepoGate(c.resolve()).is_issue_tracked()}
		for cand in self.workspace_code_repos:
			if cand not in self.candidate_repos:
				self.candidate_repos.append(cand)
		return self.__bind_issue_repos()
	# @used-by :meth:`TurnAuditor.__collect_repos_and_issues()`
	def __collect_touched_repos(self) -> None:
		for raw_p in self.turn.get('touched_files') or []:
			if isinstance(raw_p, str) and raw_p.strip():
				try:
					p = Path(raw_p.strip())
					resolved = WorktreePathResolver(p.resolve() if p.is_absolute() else (self.root / p).resolve(), lambda r: RepoGate(r).is_issue_tracked()).resolve()
					if None is not resolved:
						self.repo_touched.setdefault(resolved[0], set()).add(resolved[1])
				except OSError:
					continue
	# @used-by :meth:`TurnAuditor.check_multi_subtask_decomposition()`
	def __committed_parent_numbers(self, slug: str, committed_urls: set[str]) -> set[int]:
		parents: set[int] = set()
		for c_url in sorted(committed_urls):
			parsed = dfh_parse_issue_url(c_url)
			if None is not parsed and parsed[0].lower() == slug.lower():
				pnum = self.resolve_parent_number(parsed[0], parsed[1])
				if None is not pnum:
					parents.add(pnum)
		return parents
	# @used-by :meth:`TurnAuditor.__lint_saved_issue_obj()`
	# @used-by :meth:`TurnAuditor.resolve_parent_number()`
	def __extract_saved_parent(self, info: dict, iss_obj: dict, b_txt: str, slug: str) -> int | None:
		pnum = info.get('parent_number')
		if not isinstance(pnum, int) or isinstance(pnum, bool):
			raw_p = iss_obj.get('parent_number')
			pnum = raw_p if isinstance(raw_p, int) and (not isinstance(raw_p, bool)) else self.linter.extract_parent_number(b_txt, slug)
		return pnum
	# @used-by :meth:`TurnAuditor.check_multi_subtask_decomposition()`
	def __flag_unparented_multi_commits(self, slug: str, committed_urls: set[str]) -> None:
		for c_url in sorted(committed_urls):
			c_info = self.turn_issues.get(c_url) or {}
			if 'create' in set(c_info.get('actions') or ()) and c_info.get('repo', '').lower() == slug.lower():
				if None is self.resolve_parent_number(c_info['repo'], int(c_info['number'])):
					self.violations.append(f'EXEC-5 violation: multi-commit subtask issue {c_url} created in {slug} lacks a --parent link to a parent problem issue')
	# @used-by :meth:`TurnAuditor.__check_diagnostic_audit_filing()`
	def __has_workspace_parent_issue(self, ws_slug: str, resp: str) -> bool:
		r = any((info['repo'].lower() == ws_slug.lower() and (None is self.resolve_parent_number(info['repo'], int(info['number']), require_parent_evidence=False)) for info in self.turn_issues.values()))
		if not r:
			for resp_url in dfh_extract_issue_urls(resp):
				parsed = dfh_parse_issue_url(resp_url)
				if None is not parsed and parsed[0].lower() == ws_slug.lower() and self.workspace.evidence_issue_files(self.root, parsed[0], f'issue-{parsed[1]}.json', self.candidate_repos) and (None is self.resolve_parent_number(parsed[0], parsed[1], require_parent_evidence=False)):
					r = True
					break
		return r
	# @used-by :meth:`TurnAuditor.__check_repo_commits_and_files()`
	def __inspect_latest_commits(self, code_repo: Path, existing_rels: list[str], required_issues: set[str], committed_urls: set[str]) -> None:
		commit_urls = self.git_cache.latest_commit_urls_for_files(code_repo, existing_rels, dfh_extract_issue_urls)
		if not commit_urls:
			joined_r = ', '.join(existing_rels)
			self.violations.append(f'Latest commit for {joined_r} in {code_repo} does not reference a GitHub Issue URL')
		required_issues.update(commit_urls)
		committed_urls.update(commit_urls)
	# @used-by :meth:`TurnAuditor.__check_issue_file_evidence()`
	def __lint_saved_issue_obj(self, issue_url: str, slug: str, num: int, info: dict, iss_obj: dict, t_txt: str, b_txt: str, p: Path, mutated: bool) -> None:
		pnum = self.__extract_saved_parent(info, iss_obj, b_txt, slug)
		if isinstance(pnum, int) and pnum != num and (not self.workspace.evidence_issue_files(self.root, slug, f'issue-{pnum}.json', self.candidate_repos)):
			self.violations.append(f'GitHub child issue {issue_url} references parent #{pnum}, which is missing saved API read-back Evidence JSON (issue-{pnum}.json)')
		if mutated and t_txt:
			for err in self.linter.lint(t_txt, is_title=True):
				code, msg = (err.get('code'), err.get('message'))
				self.violations.append(f'GitHub issue {issue_url} title lint error ({code}): {msg}')
		if mutated and b_txt:
			eff_p = pnum if isinstance(pnum, int) and pnum != num else None
			for err in self.linter.lint(b_txt, is_title=False, parent_number=eff_p, repo=slug, self_number=num):
				code, msg = (err.get('code'), err.get('message'))
				self.violations.append(f'GitHub issue {issue_url} body lint error ({code}): {msg}')
			self.violations.extend((f'GitHub issue {issue_url} body grounding error: {g_err}' for g_err in local_source_grounding_issues(self.root, b_txt, doc_path=p)))
	# @used-by :meth:`TurnAuditor.check_multi_subtask_decomposition()`
	def __parent_linked_committed_urls(self, slug: str, req_urls: list[str], committed_urls: set[str]) -> list[str]:
		return [c_url for c_url in req_urls if c_url in committed_urls and (parsed := dfh_parse_issue_url(c_url)) and parsed[0].lower() == slug.lower() and (None is not self.resolve_parent_number(parsed[0], parsed[1]))]
	# @used-by :meth:`TurnAuditor.audit()`
	def __verify_required_repo_issues(self, code_repo: Path, req_set: set[str]) -> None:
		for issue_url in sorted(req_set):
			parsed = dfh_parse_issue_url(issue_url)
			if None is not parsed:
				slug, num = parsed
				try:
					ready = RepoGate(code_repo, strict=True).verify_issue_ready_for_close(slug, num, project_root=self.root, git_cache=self.git_cache)
				except (ValueError, RuntimeError) as exc:
					ready = {'verified': False, 'violations': [str(exc)]}
				for v in ready.get('violations') or []:
					if v not in self.violations:
						self.violations.append(v)
				eff_state = self.workspace.evidence_issue_state(self.root, slug, num, self.candidate_repos) or self.turn_issues.get(issue_url, {}).get('state') or 'open'
				self.checked_issues.append({'url': issue_url, 'repo': slug, 'number': num, 'state': eff_state, 'code_repo': str(code_repo), 'commit_and_push_verified': bool(ready.get('verified'))})
				self.checked_urls.add(issue_url)
				if 'closed' != eff_state:
					self.violations.append(f'GitHub issue {issue_url} remains {eff_state}; close it via df_github_issue.py close after git push before answer-prepare')
	# @used-by :func:`agent_tools.issue_lifecycle.code_and_issue_lifecycle_status()`
	def audit(self) -> dict:
		required_by_repo, repo_by_url = self.__collect_repos_and_issues()
		committed_by_repo: dict[Path, set[str]] = {}
		self.__check_diagnostic_audit_filing()
		for code_repo, rel_set in sorted(self.repo_touched.items(), key=lambda x: str(x[0])):
			req_set = required_by_repo.setdefault(code_repo, set())
			committed_by_repo[code_repo] = self.__check_repo_commits_and_files(code_repo, sorted(rel_set), req_set)
			self.__verify_required_repo_issues(code_repo, req_set)
		sim_status = ParityAuditor(self.root, self.repo_touched, self.turn_issues, self.turn_state, self.candidate_repos, self.violations).audit()
		self.__check_turn_issue_evidence(repo_by_url)
		self.check_multi_subtask_decomposition(committed_by_repo, required_by_repo)
		return {'verified': not self.violations, 'touched_repos': {str(k): sorted(v) for k, v in self.repo_touched.items()}, 'issues': self.checked_issues, 'similar_projects': sim_status, 'violations': self.violations, 'warnings': self.warnings, **({'deferred_children': getattr(self, 'deferred_children', [])} if getattr(self, 'deferred_children', None) else {})}
	# @used-by :meth:`TurnAuditor.__getattr__()`
	# @used-by :meth:`TurnAuditor.audit()`
	def check_multi_subtask_decomposition(self, committed_by_repo: dict[Path, set[str]], required_by_repo: dict[Path, set[str]]) -> None:
		active_repos = [cr for cr, rels in sorted(self.repo_touched.items(), key=lambda x: str(x[0])) if rels or committed_by_repo.get(cr)]
		if active_repos:
			impl_m_roots = dfh_extract_implemented_m_roots(self.response or '')
			total_child_urls, per_repo = (0, [])
			for code_repo in active_repos:
				slug = self.workspace.origin_repo_slug(code_repo)
				if not slug:
					continue
				committed_urls = committed_by_repo.get(code_repo) or set()
				parent_nums = self.__committed_parent_numbers(slug, committed_urls)
				if 2 <= len(impl_m_roots):
					c_urls = self.__parent_linked_committed_urls(slug, sorted(required_by_repo.get(code_repo) or ()), committed_urls)
					total_child_urls += len(c_urls)
					per_repo.append((code_repo, slug, c_urls))
				elif 2 <= len(committed_urls):
					self.__flag_unparented_multi_commits(slug, committed_urls)
				ScopeCompletenessChecker(self, slug).check(code_repo, parent_nums)
			dfh_verify_multi_subtask_counts(impl_m_roots, per_repo, total_child_urls, self.violations)
	# @used-by :func:`agent_tools.issue_lifecycle._collect_turn_issues()`
	# @used-by :meth:`TurnAuditor.__collect_repos_and_issues()`
	@staticmethod
	def collect_turn_issues(turn: dict, turn_state: dict | None, *, has_competing_open_turns: bool=False) -> dict[str, dict]:
		turn_issues: dict[str, dict] = {}
		ts_cid, ts_plat = (str((turn_state or {}).get('conversation_id') or '').strip(), str((turn_state or {}).get('platform') or '').strip().lower())
		gh_raw = (turn_state or {}).get('github_issues') or []
		gh_items = list(gh_raw.values()) if isinstance(gh_raw, dict) else list(gh_raw)
		native_items = [it for it in (turn.get('issue_actions') or []) if isinstance(it, dict)]
		native_urls = {(it.get('url') or '').strip() for it in native_items if (it.get('url') or '').strip()}
		for item in dfh_filter_turn_state_items(gh_items, ts_cid, ts_plat, native_urls, has_competing_open_turns=has_competing_open_turns) + native_items:
			if isinstance(item, dict):
				dfh_merge_turn_issue_item(turn_issues, item)
		return turn_issues
	# @used-by :meth:`TurnAuditor.__check_repo_commits_and_files()`
	# @used-by :meth:`TurnAuditor.__getattr__()`
	def inspect_touched_code_file(self, code_repo: Path, rel: str, required_issues: set[str], committed_urls: set[str]) -> None:
		from agent_tools.tdd.exemption import filter_repo_turn_issue_urls, is_git_path_exempt
		fpath = code_repo / rel
		is_code = (Path(rel).suffix.lower() or (Path(rel).name.lower() if Path(rel).name.startswith('.') else '')) in ISSUE_LINKED_CODE_SUFFIXES
		if fpath.is_file() and is_code:
			try:
				file_text = fpath.read_text(encoding='utf-8', errors='replace')
				urls_in_file, comment_urls = (dfh_extract_issue_urls(file_text), dfh_extract_comment_issue_urls(file_text))
			except OSError:
				urls_in_file, comment_urls = ([], set())
			if (not urls_in_file) and (not is_git_path_exempt(code_repo, rel, project_root=self.root)):
				self.violations.append(f'Modified code file {fpath} does not reference a GitHub Issue URL')
			for cu in filter_repo_turn_issue_urls(comment_urls, self.turn_issues, self.workspace.origin_repo_slug(code_repo)):
				required_issues.add(cu)
				committed_urls.add(cu)
	# @used-by :meth:`TurnAuditor.__committed_parent_numbers()`
	# @used-by :meth:`TurnAuditor.__flag_unparented_multi_commits()`
	# @used-by :meth:`TurnAuditor.__getattr__()`
	# @used-by :meth:`TurnAuditor.__has_workspace_parent_issue()`
	# @used-by :meth:`TurnAuditor.__parent_linked_committed_urls()`
	def resolve_parent_number(self, slug: str, num: int, *, require_parent_evidence: bool=True) -> int | None:
		pnum = self.turn_issues.get(f'https://github.com/{slug}/issues/{int(num)}', {}).get('parent_number')
		if not isinstance(pnum, int) or isinstance(pnum, bool):
			pnum = None
			for p in self.workspace.evidence_issue_files(self.root, slug, f'issue-{int(num)}.json', self.candidate_repos)[:1]:
				try:
					data = json.loads(p.read_text(encoding='utf-8'))
				except (OSError, ValueError):
					continue
				iss_obj = data.get('issue') if isinstance(data, dict) and isinstance(data.get('issue'), dict) else data
				if isinstance(iss_obj, dict):
					pnum = self.__extract_saved_parent({}, iss_obj, str(iss_obj.get('body') or ''), slug)
					break
		return pnum if isinstance(pnum, int) and pnum != int(num) and (not require_parent_evidence or self.workspace.evidence_issue_files(self.root, slug, f'issue-{pnum}.json', self.candidate_repos)) else None
