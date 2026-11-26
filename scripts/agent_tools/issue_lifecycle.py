# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
from .issues import IssueEvidenceWorkspace, TurnIssueLifecycleAuditor
from .issues.parity import check_similar_project_parity, extract_implemented_m_roots, similar_project_repo_slugs
# 2026-11-22
# "Enforce similar-project parity in turn lifecycle gates and Antigravity hooks":
# https://github.com/dmitry-ai/harness/issues/123
_check_similar_project_parity = check_similar_project_parity
# 2026-11-18
# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/84
_extract_implemented_m_roots_from_response = extract_implemented_m_roots
# 2026-11-24
# "Decompose github_issue.py and issue_lifecycle.py into IssueMarkdownLinter, IssueEvidenceWorkspace, GitHubIssueService, and TurnIssueLifecycleAuditor with locked turn updates":
# https://github.com/dmitry-ai/harness/issues/77
def _check_multi_subtask_decomposition(root: Path, response, repo_touched: dict, committed_by_repo: dict[Path, set[str]], turn_issues: dict, required_issues_by_repo: dict[Path, set[str]], candidate_repos: list[Path], violations: list[str]) -> None:
	auditor = TurnIssueLifecycleAuditor(Path(root), {}, None, response)
	auditor.repo_touched = repo_touched
	auditor.turn_issues = turn_issues
	auditor.candidate_repos = candidate_repos
	auditor.violations = violations
	auditor._check_multi_subtask_decomposition(committed_by_repo, required_issues_by_repo)
def _collect_turn_issues(turn: dict, turn_state: dict | None) -> dict[str, dict]:
	return TurnIssueLifecycleAuditor.collect_turn_issues(turn, turn_state)
# 2026-11-13
# "Extract issue_lifecycle.py from completion.py, fix open backlog-issue lifecycle gating, and consolidate Git/issue helpers in git_gate.py":
# https://github.com/dmitry-ai/harness/issues/53
def code_and_issue_lifecycle_status(root, turn, turn_state=None, response=None) -> dict:
	return TurnIssueLifecycleAuditor(Path(root), turn, turn_state, response).audit()
def evidence_issue_files(root: Path, repo_slug: str, fname: str, candidate_repos=()) -> list[Path]:
	return IssueEvidenceWorkspace.evidence_issue_files(root, repo_slug, fname, candidate_repos)
def evidence_issue_state(root: Path, repo_slug: str, number: int, candidate_repos=()) -> str | None:
	return IssueEvidenceWorkspace.evidence_issue_state(root, repo_slug, number, candidate_repos)
def origin_repo_slug(code_repo: Path) -> str | None:
	return IssueEvidenceWorkspace.origin_repo_slug(code_repo)
