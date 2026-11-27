# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Issue.ParityAuditor import ParityAuditor
from Df.Harness.lib.issue_turn import dfh_extract_implemented_m_roots, dfh_filter_turn_state_items, dfh_merge_turn_issue_item, dfh_verify_multi_subtask_counts
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :mod:`agent_tools.issue_lifecycle`
def check_similar_project_parity(root: Path, repo_touched: dict[Path, set[str]], turn_issues: dict[str, dict], turn_state: dict | None, candidate_repos: list[Path], violations: list[str]) -> list[dict]:
	return ParityAuditor(root, repo_touched, turn_issues, turn_state, candidate_repos, violations).audit()
# @used-by :mod:`agent_tools.issue_lifecycle`
def extract_implemented_m_roots(response) -> list[str]:
	return dfh_extract_implemented_m_roots(response)
# @used-by :meth:`test_issue_conversation_isolation.IssueConversationIsolationTests.test_filter_rejects_legacy_non_codex_broadcast_and_competing_untagged_entries()`
def filter_turn_state_items(gh_items: list, ts_cid: str, ts_plat: str, native_urls: set[str], *, has_competing_open_turns: bool=False) -> list[dict]:
	return dfh_filter_turn_state_items(gh_items, ts_cid, ts_plat, native_urls, has_competing_open_turns=has_competing_open_turns)
# @used-by unused
def merge_turn_issue_item(turn_issues: dict[str, dict], item: dict) -> None:
	dfh_merge_turn_issue_item(turn_issues, item)
# @used-by :func:`Df.Harness.lib.completion_checks._collect_peer_repo_slugs()`
# @used-by :func:`Df.Harness.lib.completion_recovery._match_similar_peer()`
# @used-by :mod:`agent_tools.issue_lifecycle`
def similar_project_repo_slugs(peer_root: Path, *, registry=None) -> list[str]:
	return ParityAuditor.similar_project_repo_slugs(peer_root, registry=registry)
# @used-by unused
def verify_multi_subtask_counts(impl_m_roots: list[str], per_repo: list[tuple[Path, str, list[str]]], total_child_urls: int, violations: list[str]) -> None:
	dfh_verify_multi_subtask_counts(impl_m_roots, per_repo, total_child_urls, violations)
