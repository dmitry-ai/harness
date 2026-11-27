# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.shell import ISSUE_LINKED_CODE_SUFFIXES, dfh_extract_issue_urls
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IssueCloseVerifier:
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_issue_ready_for_close()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	def __init__(self, gate) -> None:
		self.__gate = gate
	# @used-by :meth:`IssueCloseVerifier.verify()`
	def __ensure_clean(self, cache, issue_url: str) -> None:
		dirty = cache.dirty_referencing_issue(self.__gate.root, issue_url, ISSUE_LINKED_CODE_SUFFIXES, dfh_extract_issue_urls)
		if dirty:
			joined = ', '.join(dirty)
			raise ValueError(f'EXEC-5 violation: uncommitted file(s) in {self.__gate.root} still reference {issue_url}: {joined}; commit and push before closing the issue')
	# @used-by :meth:`IssueCloseVerifier.verify()`
	def __verify_parent_children(self, repo: str, issue_url: str, commit_sha: str | None, children: list[dict], *, project_root: str | Path | None, visiting: set[int], cache) -> dict:
		if commit_sha:
			raise ValueError(f'EXEC-5 violation: parent issue {issue_url} has child subtask issues and must document the original problem without direct monolithic code commits ({commit_sha[:12]})')
		open_children = [c['url'] for c in children if 'closed' != c['state']]
		if open_children:
			joined_open = ', '.join(open_children)
			raise ValueError(f'EXEC-5 violation: parent issue {issue_url} cannot be closed as completed while child issue(s) remain open: {joined_open}')
		completed = [c for c in children if 'closed' == c['state'] and 'not_planned' != str(c.get('state_reason') or '').lower() and c['number'] not in visiting]
		if not completed:
			raise ValueError(f'EXEC-5 violation: parent issue {issue_url} has no completed child issues with verified commits')
		child_shas = [c_res['commit_sha'] for child in completed for c_res in (self.verify(repo, child['number'], project_root=project_root, visiting=visiting, git_cache=cache),) if c_res.get('commit_sha')]
		return {'verified': True, 'repo': str(self.__gate.root), 'issue_url': issue_url, 'commit_sha': child_shas[0] if child_shas else '', 'child_issues': [c['number'] for c in completed], 'pushed': True}
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_issue_ready_for_close()`
	# @used-by :meth:`IssueCloseVerifier.__verify_parent_children()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	def verify(self, repo: str, number: int, *, project_root: str | Path | None=None, visiting: set[int] | None=None, git_cache=None) -> dict:
		from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
		from Df.Harness.Issue.ReadCache import ReadCache
		from agent_tools.repo_tag_gate import finalize_commit_close_check
		cache = git_cache if None is not git_cache else ReadCache()
		issue_url = f'https://github.com/{repo}/issues/{number}'
		self.__ensure_clean(cache, issue_url)
		commit_sha = cache.find_commit_for_issue(self.__gate.root, issue_url, dfh_extract_issue_urls)
		children = EvidenceWorkspace().find_tracked_child_issues(repo, number, project_root=project_root, code_repo=self.__gate.root)
		seen = set(visiting or ())
		if children and int(number) not in seen:
			seen.add(int(number))
			r = self.__verify_parent_children(repo, issue_url, commit_sha, children, project_root=project_root, visiting=seen, cache=cache)
		elif not commit_sha:
			raise ValueError(f'EXEC-5 violation: no commit in {self.__gate.root} references {issue_url}; commit and push changes before closing the issue as completed')
		else:
			r = finalize_commit_close_check(self.__gate.root, commit_sha, issue_url, cache)
		return r
