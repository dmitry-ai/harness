# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ScopeCompletenessChecker:
	# @used-by :func:`agent_tools.issues.scope_completeness.find_open_deferred_children()`
	# @used-by :func:`agent_tools.issues.scope_completeness.flag_parent_and_deferred_children()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.check_multi_subtask_decomposition()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_parity_and_scope_completeness()`
	def __init__(self, auditor, slug: str) -> None:
		self.__auditor = auditor
		self.__slug = slug
	# @used-by :meth:`ScopeCompletenessChecker.check()`
	def __flag_unclosed_parent(self, code_repo: Path, pnum: int) -> None:
		children = self.__auditor.workspace.find_tracked_child_issues(self.__slug, pnum, project_root=self.__auditor.root, code_repo=code_repo)
		if children and all(('closed' == c.get('state') for c in children)):
			p_url = f'https://github.com/{self.__slug}/issues/{pnum}'
			p_state = self.__auditor.workspace.evidence_issue_state(self.__auditor.root, self.__slug, pnum, self.__auditor.candidate_repos) or (self.__auditor.turn_issues.get(p_url) or {}).get('state') or 'open'
			if 'closed' != p_state:
				self.__auditor.violations.append(f'EXEC-5 violation: parent issue {p_url} in {self.__slug} remains {p_state} after all tracked child subtask issues are closed; close it via df_github_issue.py close')
	# @used-by :meth:`ScopeCompletenessChecker.find_open_deferred_children()`
	@staticmethod
	def __issue_created_in_turn(info: dict) -> bool:
		return 'create' == info.get('last_action') or 'create' in set(info.get('actions') or ())
	# @used-by :func:`agent_tools.issues.scope_completeness.flag_parent_and_deferred_children()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.check_multi_subtask_decomposition()`
	def check(self, code_repo: Path, parent_nums: set[int]) -> None:
		from agent_tools.scope_deferral import find_explicit_stop_consent
		for pnum in sorted(parent_nums):
			self.__flag_unclosed_parent(code_repo, pnum)
		deferred = self.find_open_deferred_children()
		if deferred:
			recorded = list(getattr(self.__auditor, 'deferred_children', ()))
			has_consent = None is not find_explicit_stop_consent(self.__auditor.turn, self.__auditor.turn_state)
			for pnum, child_urls in sorted(deferred.items()):
				p_url = f'https://github.com/{self.__slug}/issues/{pnum}'
				recorded.append({'repo': self.__slug, 'parent_number': pnum, 'parent_url': p_url, 'children': child_urls})
				if not has_consent:
					joined = ', '.join(child_urls)
					self.__auditor.violations.append(f'SCOPE-2 / EXEC-5 violation: active turn created open deferred child issue(s) under parent {p_url} in {self.__slug} ({joined}) without completing them; finish all requested subtasks, pass --blocked-report for a documented blocker, or obtain explicit user authorization to stop the turn early')
			self.__auditor.deferred_children = recorded
	# @used-by :func:`agent_tools.issues.scope_completeness.find_open_deferred_children()`
	# @used-by :meth:`ScopeCompletenessChecker.check()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_parity_and_scope_completeness()`
	def find_open_deferred_children(self) -> dict[int, list[str]]:
		grouped: dict[int, list[str]] = {}
		slug_low = self.__slug.lower()
		for issue_url, info in sorted(self.__auditor.turn_issues.items()):
			if info.get('repo', '').lower() != slug_low or (not self.__issue_created_in_turn(info)):
				continue
			num = int(info['number'])
			pnum = self.__auditor.resolve_parent_number(info['repo'], num, require_parent_evidence=False)
			if None is pnum:
				continue
			eff_state = self.__auditor.workspace.evidence_issue_state(self.__auditor.root, self.__slug, num, self.__auditor.candidate_repos) or info.get('state') or 'open'
			if 'closed' != eff_state:
				grouped.setdefault(pnum, []).append(issue_url)
		return grouped
