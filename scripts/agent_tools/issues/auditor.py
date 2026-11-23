# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate per-conversation github_issues recording and turn-state filtering":
# https://github.com/dmitry-ai/harness/issues/195
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/175
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/77
from __future__ import annotations
import json
from pathlib import Path
import re
from ..git_gate import extract_comment_issue_urls, extract_issue_urls, is_code_file, is_issue_tracked_code_repo, parse_issue_url, run_git_read, verify_repo_issue_ready_for_close
from ..source_grounding import local_source_grounding_issues
from ..worktree_flow import resolve_touched_repo_file
from .git_read_cache import RepoReadCache
from .linter import IssueMarkdownLinter
from .parity import check_similar_project_parity, extract_implemented_m_roots, filter_turn_state_items, merge_turn_issue_item, verify_multi_subtask_counts
from .turn_scope import has_competing_open_turns
from .workspace import IssueEvidenceWorkspace, _V2_CODE_RELS
class TurnIssueLifecycleAuditor:
	def __init__(self, root: Path, turn: dict, turn_state: dict | None=None, response=None, *, workspace: IssueEvidenceWorkspace | None=None, linter: IssueMarkdownLinter | None=None) -> None:
		self.root, self.turn, self.turn_state, self.response = (Path(root).resolve(), turn, turn_state, response)
		self.workspace = workspace if None is not workspace else IssueEvidenceWorkspace()
		self.linter = linter if None is not linter else IssueMarkdownLinter()
		self.violations: list[str] = []
		self.checked_issues: list[dict] = []
		self.checked_urls: set[str] = set()
		self.repo_touched: dict[Path, set[str]] = {}
		self.candidate_repos: list[Path] = []
		self.workspace_code_repos: set[Path] = set()
		self.turn_issues: dict[str, dict] = {}
		self.git_cache = RepoReadCache()
	def _bind_issue_repos(self) -> tuple[dict[Path, set[str]], dict[str, Path]]:
		for info in self.turn_issues.values():
			found = self.workspace.find_local_code_repo(info['repo'], project_root=self.root)
			if None is not found and is_issue_tracked_code_repo(found.resolve()) and found.resolve() not in self.candidate_repos:
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
	def _check_comments_evidence(self, issue_url: str, slug: str, cids: list, container_text: str | None) -> None:
		for cid in cids:
			for cp in self.workspace.evidence_issue_files(self.root, slug, f'comment-{cid}.json', self.candidate_repos)[:1]:
				try:
					c_body = str((json.loads(cp.read_text(encoding='utf-8')) or {}).get('body') or '')
				except (OSError, ValueError):
					continue
				if c_body:
					for err in self.linter.lint(c_body, is_title=False, container_text=container_text, check_structure_policy=False):
						self.violations.append(f'GitHub comment {issue_url}#issuecomment-{cid} lint error ({err.get("code")}): {err.get("message")}')
					for g_err in local_source_grounding_issues(self.root, c_body, doc_path=cp):
						self.violations.append(f'GitHub comment {issue_url}#issuecomment-{cid} grounding error: {g_err}')
	def _check_diagnostic_audit_filing(self) -> None:
		resp = self.response
		if isinstance(resp, str) and resp.strip() and self.workspace_code_repos and (not self.repo_touched):
			has_diag = bool(re.search('(?m)(?:^|\\s|`|\\*\\*)(?:C|H)-[1-9]\\d*\\b', resp)) and bool(re.search('(?m)(?:^|\\s|`|\\*\\*)M-[1-9]\\d*\\b', resp)) and bool(re.search('\\b[A-Za-z0-9_/-]+\\.py\\b', resp))
			if has_diag:
				for ws_repo in sorted(self.workspace_code_repos, key=str):
					ws_slug = self.workspace.origin_repo_slug(ws_repo)
					if ws_slug and (not self._has_workspace_parent_issue(ws_slug, resp)):
						self.violations.append(f'EXEC-5 / SCOPE-2: Diagnostic audit of {ws_slug} identifies repository defects (C-/H-) and remediation methods (M-) without recording a corresponding parent problem GitHub Issue via df_github_issue.py')
	def _check_issue_file_evidence(self, issue_url: str, slug: str, num: int, info: dict, mutated: bool) -> str | None:
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
				self._lint_saved_issue_obj(issue_url, slug, num, info, iss_obj, t_txt, b_txt, p, mutated)
			except (OSError, ValueError):
				continue
		return container_text
	def _check_multi_subtask_decomposition(self, committed_by_repo: dict[Path, set[str]], required_by_repo: dict[Path, set[str]]) -> None:
		active_repos = [cr for cr, rels in sorted(self.repo_touched.items(), key=lambda x: str(x[0])) if rels or committed_by_repo.get(cr)]
		if active_repos:
			impl_m_roots = extract_implemented_m_roots(self.response or '')
			total_child_urls, per_repo = (0, [])
			for code_repo in active_repos:
				slug = self.workspace.origin_repo_slug(code_repo)
				if not slug:
					continue
				committed_urls = committed_by_repo.get(code_repo) or set()
				parent_nums = self._committed_parent_numbers(slug, committed_urls)
				if 2 <= len(impl_m_roots):
					c_urls = self._parent_linked_committed_urls(slug, sorted(required_by_repo.get(code_repo) or ()), committed_urls)
					total_child_urls += len(c_urls)
					per_repo.append((code_repo, slug, c_urls))
				elif 2 <= len(committed_urls):
					self._flag_unparented_multi_commits(slug, committed_urls)
				self._flag_unclosed_completed_parents(code_repo, slug, parent_nums)
			verify_multi_subtask_counts(impl_m_roots, per_repo, total_child_urls, self.violations)
	def _check_repo_commits_and_files(self, code_repo: Path, rel_paths: list[str], required_issues: set[str]) -> set[str]:
		committed_urls: set[str] = set()
		if rel_paths:
			if self.git_cache.has_dirty_for_paths(code_repo, rel_paths):
				self.violations.append(f'Modified files in {code_repo} are not committed: {", ".join(rel_paths)}')
			for rel in rel_paths:
				self._inspect_touched_code_file(code_repo, rel, required_issues, committed_urls)
			existing_rels = [rel for rel in rel_paths if (code_repo / rel).exists()]
			if existing_rels:
				self._inspect_latest_commits(code_repo, existing_rels, required_issues, committed_urls)
		return committed_urls
	def _check_turn_issue_evidence(self, repo_by_issue_url: dict[str, Path]) -> None:
		for issue_url, info in sorted(self.turn_issues.items()):
			slug, num = (info['repo'], int(info['number']))
			mutated = info.get('last_action') in ('create', 'edit') or bool(set(info.get('actions') or ()) & {'create', 'edit'})
			eff_state = self.workspace.evidence_issue_state(self.root, slug, num, self.candidate_repos) or info.get('state') or 'open'
			if issue_url not in self.checked_urls:
				mapped = repo_by_issue_url.get(issue_url)
				self.checked_issues.append({'url': issue_url, 'repo': slug, 'number': num, 'state': eff_state, 'code_repo': str(mapped) if mapped else None, 'commit_and_push_verified': False})
				self.checked_urls.add(issue_url)
			container_text = self._check_issue_file_evidence(issue_url, slug, num, info, mutated)
			self._check_comments_evidence(issue_url, slug, info.get('comment_ids') or [], container_text)
	def _collect_repos_and_issues(self) -> tuple[dict[Path, set[str]], dict[str, Path]]:
		from ..path_registry import project_paths
		self._collect_touched_repos()
		pp_root = project_paths(self.root)
		ts_cid = str((self.turn_state or {}).get('conversation_id') or '').strip()
		self.turn_issues = self.collect_turn_issues(self.turn, self.turn_state, has_competing_open_turns=has_competing_open_turns(self.root, ts_cid))
		self.candidate_repos = list(self.repo_touched.keys())
		ws_cands = (*pp_root.code_repos, self.root, self.root / 'code', *(self.root / rel for rel in _V2_CODE_RELS), self.root.parent / 'code', *(self.root.parent / rel for rel in _V2_CODE_RELS))
		self.workspace_code_repos = {c.resolve() for c in ws_cands if is_issue_tracked_code_repo(c.resolve())}
		for cand in self.workspace_code_repos:
			if cand not in self.candidate_repos:
				self.candidate_repos.append(cand)
		return self._bind_issue_repos()
	def _collect_touched_repos(self) -> None:
		for raw_p in self.turn.get('touched_files') or []:
			if isinstance(raw_p, str) and raw_p.strip():
				try:
					p = Path(raw_p.strip())
					resolved = resolve_touched_repo_file(p.resolve() if p.is_absolute() else (self.root / p).resolve(), is_issue_tracked_code_repo)
					if None is not resolved:
						self.repo_touched.setdefault(resolved[0], set()).add(resolved[1])
				except OSError:
					continue
	def _committed_parent_numbers(self, slug: str, committed_urls: set[str]) -> set[int]:
		parents: set[int] = set()
		for c_url in sorted(committed_urls):
			parsed = parse_issue_url(c_url)
			if None is not parsed and parsed[0].lower() == slug.lower():
				pnum = self._resolve_parent_number(parsed[0], parsed[1])
				if None is not pnum:
					parents.add(pnum)
		return parents
	def _extract_saved_parent(self, info: dict, iss_obj: dict, b_txt: str, slug: str) -> int | None:
		pnum = info.get('parent_number')
		if not isinstance(pnum, int) or isinstance(pnum, bool):
			raw_p = iss_obj.get('parent_number')
			pnum = raw_p if isinstance(raw_p, int) and (not isinstance(raw_p, bool)) else self.linter.extract_parent_number(b_txt, slug)
		return pnum
	def _flag_unclosed_completed_parents(self, code_repo: Path, slug: str, parent_nums: set[int]) -> None:
		for pnum in sorted(parent_nums):
			children = self.workspace.find_tracked_child_issues(slug, pnum, project_root=self.root, code_repo=code_repo)
			if children and all(('closed' == c.get('state') for c in children)):
				p_url = f'https://github.com/{slug}/issues/{pnum}'
				p_state = self.workspace.evidence_issue_state(self.root, slug, pnum, self.candidate_repos) or (self.turn_issues.get(p_url) or {}).get('state') or 'open'
				if 'closed' != p_state:
					self.violations.append(f'EXEC-5 violation: parent issue {p_url} in {slug} remains {p_state} after all tracked child subtask issues are closed; close it via df_github_issue.py close')
	def _flag_unparented_multi_commits(self, slug: str, committed_urls: set[str]) -> None:
		for c_url in sorted(committed_urls):
			c_info = self.turn_issues.get(c_url) or {}
			if 'create' in set(c_info.get('actions') or ()) and c_info.get('repo', '').lower() == slug.lower():
				if None is self._resolve_parent_number(c_info['repo'], int(c_info['number'])):
					self.violations.append(f'EXEC-5 violation: multi-commit subtask issue {c_url} created in {slug} lacks a --parent link to a parent problem issue')
	def _has_workspace_parent_issue(self, ws_slug: str, resp: str) -> bool:
		r = any((info['repo'].lower() == ws_slug.lower() and (None is self._resolve_parent_number(info['repo'], int(info['number']), require_parent_evidence=False)) for info in self.turn_issues.values()))
		if not r:
			for resp_url in extract_issue_urls(resp):
				parsed = parse_issue_url(resp_url)
				if None is not parsed and parsed[0].lower() == ws_slug.lower() and self.workspace.evidence_issue_files(self.root, parsed[0], f'issue-{parsed[1]}.json', self.candidate_repos) and (None is self._resolve_parent_number(parsed[0], parsed[1], require_parent_evidence=False)):
					r = True
					break
		return r
	def _inspect_latest_commits(self, code_repo: Path, existing_rels: list[str], required_issues: set[str], committed_urls: set[str]) -> None:
		commit_urls = self.git_cache.latest_commit_urls_for_files(code_repo, existing_rels, extract_issue_urls)
		if not commit_urls:
			self.violations.append(f'Latest commit for {", ".join(existing_rels)} in {code_repo} does not reference a GitHub Issue URL')
		required_issues.update(commit_urls)
		committed_urls.update(commit_urls)
	def _inspect_touched_code_file(self, code_repo: Path, rel: str, required_issues: set[str], committed_urls: set[str]) -> None:
		fpath = code_repo / rel
		if fpath.is_file() and is_code_file(rel):
			try:
				file_text = fpath.read_text(encoding='utf-8', errors='replace')
				urls_in_file, comment_urls = (extract_issue_urls(file_text), extract_comment_issue_urls(file_text))
			except OSError:
				urls_in_file, comment_urls = ([], set())
			if not urls_in_file:
				self.violations.append(f'Modified code file {fpath} does not reference a GitHub Issue URL')
			for cu in comment_urls:
				if cu in self.turn_issues:
					required_issues.add(cu)
					committed_urls.add(cu)
	def _lint_saved_issue_obj(self, issue_url: str, slug: str, num: int, info: dict, iss_obj: dict, t_txt: str, b_txt: str, p: Path, mutated: bool) -> None:
		pnum = self._extract_saved_parent(info, iss_obj, b_txt, slug)
		if isinstance(pnum, int) and pnum != num and (not self.workspace.evidence_issue_files(self.root, slug, f'issue-{pnum}.json', self.candidate_repos)):
			self.violations.append(f'GitHub child issue {issue_url} references parent #{pnum}, which is missing saved API read-back Evidence JSON (issue-{pnum}.json)')
		if mutated and t_txt:
			self.violations.extend((f'GitHub issue {issue_url} title lint error ({err.get("code")}): {err.get("message")}' for err in self.linter.lint(t_txt, is_title=True)))
		if mutated and b_txt:
			eff_p = pnum if isinstance(pnum, int) and pnum != num else None
			self.violations.extend((f'GitHub issue {issue_url} body lint error ({err.get("code")}): {err.get("message")}' for err in self.linter.lint(b_txt, is_title=False, parent_number=eff_p, repo=slug, self_number=num)))
			self.violations.extend((f'GitHub issue {issue_url} body grounding error: {g_err}' for g_err in local_source_grounding_issues(self.root, b_txt, doc_path=p)))
	def _parent_linked_committed_urls(self, slug: str, req_urls: list[str], committed_urls: set[str]) -> list[str]:
		return [c_url for c_url in req_urls if c_url in committed_urls and (parsed := parse_issue_url(c_url)) and parsed[0].lower() == slug.lower() and (None is not self._resolve_parent_number(parsed[0], parsed[1]))]
	def _resolve_parent_number(self, slug: str, num: int, *, require_parent_evidence: bool=True) -> int | None:
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
					pnum = self._extract_saved_parent({}, iss_obj, str(iss_obj.get('body') or ''), slug)
					break
		return pnum if isinstance(pnum, int) and pnum != int(num) and (not require_parent_evidence or self.workspace.evidence_issue_files(self.root, slug, f'issue-{pnum}.json', self.candidate_repos)) else None
	def _verify_required_repo_issues(self, code_repo: Path, req_set: set[str]) -> None:
		for issue_url in sorted(req_set):
			parsed = parse_issue_url(issue_url)
			if None is not parsed:
				slug, num = parsed
				try:
					ready = verify_repo_issue_ready_for_close(code_repo, slug, num, project_root=self.root, git_cache=self.git_cache)
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
	def audit(self) -> dict:
		required_by_repo, repo_by_url = self._collect_repos_and_issues()
		committed_by_repo: dict[Path, set[str]] = {}
		self._check_diagnostic_audit_filing()
		for code_repo, rel_set in sorted(self.repo_touched.items(), key=lambda x: str(x[0])):
			req_set = required_by_repo.setdefault(code_repo, set())
			committed_by_repo[code_repo] = self._check_repo_commits_and_files(code_repo, sorted(rel_set), req_set)
			self._verify_required_repo_issues(code_repo, req_set)
		sim_status = check_similar_project_parity(self.root, self.repo_touched, self.turn_issues, self.turn_state, self.candidate_repos, self.violations)
		self._check_turn_issue_evidence(repo_by_url)
		self._check_multi_subtask_decomposition(committed_by_repo, required_by_repo)
		return {'verified': not self.violations, 'touched_repos': {str(k): sorted(v) for k, v in self.repo_touched.items()}, 'issues': self.checked_issues, 'similar_projects': sim_status, 'violations': self.violations}
	@staticmethod
	def collect_turn_issues(turn: dict, turn_state: dict | None, *, has_competing_open_turns: bool=False) -> dict[str, dict]:
		turn_issues: dict[str, dict] = {}
		ts_cid, ts_plat = (str((turn_state or {}).get('conversation_id') or '').strip(), str((turn_state or {}).get('platform') or '').strip().lower())
		gh_raw = (turn_state or {}).get('github_issues') or []
		gh_items = list(gh_raw.values()) if isinstance(gh_raw, dict) else list(gh_raw)
		native_items = [it for it in (turn.get('issue_actions') or []) if isinstance(it, dict)]
		native_urls = {(it.get('url') or '').strip() for it in native_items if (it.get('url') or '').strip()}
		for item in filter_turn_state_items(gh_items, ts_cid, ts_plat, native_urls, has_competing_open_turns=has_competing_open_turns) + native_items:
			if isinstance(item, dict):
				merge_turn_issue_item(turn_issues, item)
		return turn_issues
