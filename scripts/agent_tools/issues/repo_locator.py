# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Issue.RepoLocator import RepoLocator, V2_CODE_RELS
from ..git_gate import run_git_read
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_V2_CODE_RELS = V2_CODE_RELS
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.find_matching_recipes()`
def _extract_config_slugs(code_repo: Path) -> list[str]:
	return RepoLocator.extract_config_slugs(code_repo)
# @used-by :func:`find_local_code_repo()`
def _search_registry_and_roots(repo: str, seen: set[Path] | None=None) -> Path | None:
	return RepoLocator.search_registry_and_roots(repo, seen if None is not seen else set())
# @used-by :func:`Df.Harness.lib.path_state.dfh_clear_registry_cache()`
def clear_repo_locator_cache() -> None:
	RepoLocator.clear_cache()
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.resolve_blob()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.validate_github_url()`
# @used-by :meth:`test_repo_locator_perf.RepoLocatorPerformanceTests.test_find_local_code_repo_discovers_direct_similar_project_peer_locally()`
# @used-by :meth:`test_repo_locator_perf.RepoLocatorPerformanceTests.test_find_local_code_repo_isolates_temp_project_from_host_search_roots()`
# @used-by :meth:`test_repo_locator_perf.RepoLocatorPerformanceTests.test_pruned_walk_skips_heavy_dirs_and_respects_ttl_cache_and_reset()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_isolated_temp_project_ignores_unrelated_host_worktree_cwd()`
def find_local_code_repo(repo: str, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, *, repo_root: str | Path | None=None) -> Path | None:
	return RepoLocator(search_fn=_search_registry_and_roots, git_read_fn=run_git_read).find_local_code_repo(repo, project_root=project_root, source_files=source_files, repo_root=repo_root)
# @used-by :func:`agent_tools.doc5_context._workspace_repo_slugs()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.enclosing_github_repo()`
# @used-by :meth:`test_hook_trace_cache_and_watchdog.HookTraceCacheAndWatchdogTests.test_origin_repo_slug_skips_git_subprocess_for_local_repo_without_origin()`
def origin_repo_slug(code_repo: Path) -> str | None:
	return RepoLocator(git_read_fn=run_git_read).origin_repo_slug(code_repo)
# @used-by unused
def repo_matches_slug(code_repo: Path, repo: str) -> bool:
	return RepoLocator(git_read_fn=run_git_read).repo_matches_slug(code_repo, repo)
