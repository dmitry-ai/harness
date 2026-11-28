# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.Issue.ParityAuditor import ParityAuditor
from Df.Harness.Issue.TurnAuditor import TurnAuditor
from Df.Harness.lib.issue_turn import dfh_extract_implemented_m_roots
from .issues import IssueEvidenceWorkspace, TurnIssueLifecycleAuditor
from .issues.parity import check_similar_project_parity, extract_implemented_m_roots, similar_project_repo_slugs
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_check_similar_project_parity = check_similar_project_parity
_extract_implemented_m_roots_from_response = dfh_extract_implemented_m_roots
# @used-by :meth:`test_issue_decomposition.IssueDecompositionTests.test_issue_lifecycle_exports_multi_subtask_decomposition_helper()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_multi_subtask_decomposition_aggregates_across_repositories()`
# @used-by :mod:`agent_tools.issue_lifecycle`
# @uses :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__getattr__()`
def _check_multi_subtask_decomposition(root: Path, response, repo_touched: dict, committed_by_repo: dict[Path, set[str]], turn_issues: dict, required_issues_by_repo: dict[Path, set[str]], candidate_repos: list[Path], violations: list[str]) -> None:
	auditor = TurnAuditor(Path(root), {}, None, response)
	auditor.repo_touched = repo_touched
	auditor.turn_issues = turn_issues
	auditor.candidate_repos = candidate_repos
	auditor.violations = violations
	auditor._check_multi_subtask_decomposition(committed_by_repo, required_issues_by_repo)
# @used-by :mod:`agent_tools.issue_lifecycle`
def _collect_turn_issues(turn: dict, turn_state: dict | None) -> dict[str, dict]:
	return TurnAuditor.collect_turn_issues(turn, turn_state)
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :func:`Df.Harness.lib.completion_state._initial_lifecycle_checks()`
# @used-by :func:`Df.Harness.lib.completion_state._refresh_active_turn_checks()`
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__check_turn_hygiene()`
# @used-by :meth:`test_clarification_stop_consent.ClarificationStopConsentTests.test_explicit_user_stop_consent_in_clarifications_unblocks_deferral()`
# @used-by :meth:`test_clarification_stop_consent.ClarificationStopConsentTests.test_step_100_102_real_clarifications_rejected_with_open_deferred_children()`
# @used-by :meth:`test_git_lifecycle_memoization.GitLifecycleMemoizationTests.test_audit_memoizes_readonly_git_commands_across_multiple_issues()`
# @used-by :meth:`test_incomplete_scope_regression_matrix.IncompleteScopeRegressionMatrixTests.test_step_281_scope_deferral_matrix_blocks_open_children_allows_unrelated_bugs_and_consent()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_post_checkpoint_evicted_citation_gate_and_issue48_defect_filing_gate()`
# @used-by :meth:`test_issue_conversation_isolation.IssueConversationIsolationTests.test_analytical_turn_ignores_foreign_and_legacy_broadcast_issues_with_dirty_repo()`
# @used-by :meth:`test_issue_decomposition.IssueDecompositionTests.test_issue_markdown_linter_and_service_classes_exist()`
# @used-by :meth:`test_open_child_deferral_gate.OpenChildDeferralGateTests.test_open_deferred_child_blocks_lifecycle_and_answer_gates()`
# @used-by :meth:`test_open_child_deferral_gate.OpenChildDeferralGateTests.test_unparented_open_bug_and_prior_turn_open_child_remain_allowed()`
# @used-by :meth:`test_repo_tag_close_gate.RepoTagCloseGateTests.test_issue_lifecycle_auditor_requires_pushed_tag_on_closing_commit()`
# @used-by :meth:`test_turn_completion.IssueLifecycleTests.test_mixed_multi_commit_closed_issues_and_open_backlog_issue()`
# @used-by :meth:`test_turn_completion.IssueLifecycleTests.test_multi_subtask_parent_and_child_commits_enforced_in_lifecycle()`
# @used-by :meth:`test_turn_completion.IssueLifecycleTests.test_post_audit_turn_isolation_diagnostic_parent_and_unclosed_parent_checks()`
# @used-by :mod:`agent_tools.issue_lifecycle`
def code_and_issue_lifecycle_status(root, turn, turn_state=None, response=None) -> dict:
	return TurnAuditor(Path(root), turn, turn_state, response).audit()
# @used-by :meth:`Df.Harness.Tdd.RatchetGuard.RatchetGuard.__find_issue_approval()`
# @used-by :mod:`agent_tools.issue_lifecycle`
def evidence_issue_files(root: Path, repo_slug: str, fname: str, candidate_repos=()) -> list[Path]:
	return EvidenceWorkspace.evidence_issue_files(root, repo_slug, fname, candidate_repos)
# @used-by :mod:`agent_tools.issue_lifecycle`
def evidence_issue_state(root: Path, repo_slug: str, number: int, candidate_repos=()) -> str | None:
	return EvidenceWorkspace.evidence_issue_state(root, repo_slug, number, candidate_repos)
# @used-by :meth:`Df.Harness.Tdd.Exemption.Exemption.verify_staged_issue_urls()`
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.__resolve_existing_repo()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_origin_repo_slug_and_linked_worktree_detection()`
# @used-by :mod:`agent_tools.issue_lifecycle`
def origin_repo_slug(code_repo: Path) -> str | None:
	return EvidenceWorkspace.origin_repo_slug(code_repo)
__all__ = ('IssueEvidenceWorkspace', 'ParityAuditor', 'TurnIssueLifecycleAuditor', '_check_multi_subtask_decomposition', '_check_similar_project_parity', '_collect_turn_issues', '_extract_implemented_m_roots_from_response', 'check_similar_project_parity', 'code_and_issue_lifecycle_status', 'evidence_issue_files', 'evidence_issue_state', 'extract_implemented_m_roots', 'origin_repo_slug', 'similar_project_repo_slugs')
