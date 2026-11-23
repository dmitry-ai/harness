# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/77
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add isolated git worktree task workflow and worktree-scoped issue gates":
# https://github.com/dmitry-ai/harness/issues/165
from pathlib import Path
from .issues import IssueEvidenceWorkspace, TurnIssueLifecycleAuditor
from .issues.parity import check_similar_project_parity, extract_implemented_m_roots, similar_project_repo_slugs
_check_similar_project_parity = check_similar_project_parity
_extract_implemented_m_roots_from_response = extract_implemented_m_roots
def _collect_turn_issues(turn: dict, turn_state: dict | None) -> dict[str, dict]:
	return TurnIssueLifecycleAuditor.collect_turn_issues(turn, turn_state)
def code_and_issue_lifecycle_status(root, turn, turn_state=None, response=None) -> dict:
	return TurnIssueLifecycleAuditor(Path(root), turn, turn_state, response).audit()
def evidence_issue_files(root: Path, repo_slug: str, fname: str, candidate_repos=()) -> list[Path]:
	return IssueEvidenceWorkspace.evidence_issue_files(root, repo_slug, fname, candidate_repos)
def evidence_issue_state(root: Path, repo_slug: str, number: int, candidate_repos=()) -> str | None:
	return IssueEvidenceWorkspace.evidence_issue_state(root, repo_slug, number, candidate_repos)
def origin_repo_slug(code_repo: Path) -> str | None:
	return IssueEvidenceWorkspace.origin_repo_slug(code_repo)
