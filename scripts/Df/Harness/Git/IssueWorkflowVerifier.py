# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.shell import dfh_normalize_commit_message, dfh_parse_issue_url
import json
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IssueWorkflowVerifier:
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_issue_workflow()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	def __init__(self, gate) -> None:
		self.__gate = gate
	# @used-by :meth:`IssueWorkflowVerifier.__verify_single_url()`
	@staticmethod
	def __extract_parent(ev_data: dict, u_slug: str) -> int | None:
		from agent_tools.github_issue import extract_parent_issue_number
		iss_obj = ev_data.get('issue') if isinstance(ev_data.get('issue'), dict) else ev_data
		raw_p = ev_data.get('parent_number')
		if not isinstance(raw_p, int) or isinstance(raw_p, bool):
			raw_p = iss_obj.get('parent_number') if isinstance(iss_obj, dict) else None
		if not isinstance(raw_p, int) or isinstance(raw_p, bool):
			raw_p = extract_parent_issue_number(str((iss_obj or {}).get('body') or ''), u_slug)
		return raw_p if isinstance(raw_p, int) and (not isinstance(raw_p, bool)) else None
	# @used-by :meth:`IssueWorkflowVerifier.__verify_tracked_evidence()`
	def __verify_single_url(self, proj_root: Path, repo_slug: str, url: str) -> None:
		from agent_tools.issue_lifecycle import evidence_issue_files
		parsed = dfh_parse_issue_url(url)
		if None is not parsed:
			u_slug, u_num = parsed
			if u_slug.lower() != repo_slug.lower():
				raise ValueError(f'EXEC-5 ISSUE-FIRST-GATE: Referenced issue {url} does not match repository {repo_slug}')
			ev_files = evidence_issue_files(proj_root, u_slug, f'issue-{u_num}.json', candidate_repos=[self.__gate.root])
			if not ev_files:
				raise ValueError(f'EXEC-5 ISSUE-FIRST-GATE: Referenced issue {url} has no saved API read-back Evidence JSON (issue-{u_num}.json); create or fetch the parent issue via df_github_issue.py before writing tests or code')
			try:
				ev_data = json.loads(ev_files[0].read_text(encoding='utf-8'))
			except (OSError, ValueError):
				ev_data = None
			if isinstance(ev_data, dict):
				parent_num = self.__extract_parent(ev_data, u_slug)
				if None is not parent_num and parent_num != u_num and (not evidence_issue_files(proj_root, u_slug, f'issue-{parent_num}.json', candidate_repos=[self.__gate.root])):
					raise ValueError(f'EXEC-5 ISSUE-FIRST-GATE: Child issue {url} references parent #{parent_num}, which has no saved API read-back Evidence JSON (issue-{parent_num}.json)')
	# @used-by :meth:`IssueWorkflowVerifier.verify()`
	def __verify_tracked_evidence(self, stripped_msg: str | None, all_new_diff_urls: set[str]) -> None:
		from agent_tools.issue_lifecycle import origin_repo_slug
		repo_slug = origin_repo_slug(self.__gate.root)
		if repo_slug:
			urls: list[str] = [stripped_msg] if None is not stripped_msg else []
			urls.extend((u for u in sorted(all_new_diff_urls) if u not in urls))
			proj_root = self.__gate.tdd_project_root()
			for url in urls:
				self.__verify_single_url(proj_root, repo_slug, url)
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_issue_workflow()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	# @uses :meth:`Df.Harness.Git.RepoGate.RepoGate.__getattr__()`
	def verify(self, relative: list[str], message: str | None=None, *, agent_context: bool=True) -> None:
		if agent_context:
			stripped_msg = None
			if None is not message:
				stripped_msg = dfh_normalize_commit_message(message)
				if None is dfh_parse_issue_url(stripped_msg):
					raise ValueError('Commit message for an agent commit must contain only the GitHub Issue URL (https://github.com/<owner>/<repo>/issues/<N>)')
			from agent_tools.tdd.exemption import verify_staged_issue_urls
			all_new = verify_staged_issue_urls(self.__gate, relative, stripped_msg, project_root=self.__gate.tdd_project_root())
			if self.__gate.is_issue_tracked():
				self.__verify_tracked_evidence(stripped_msg, all_new)
