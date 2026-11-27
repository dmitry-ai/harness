# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from agent_tools.path_registry import project_paths
_SKIP_PREFIXES = ('.git/', '\ua616/', '\ua66e/', '_/', '\U0001f56e/', '\u2c0f/\u227a/', 'Artifacts/\u227a/')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreePathResolver:
	# @used-by :func:`agent_tools.worktree_flow.resolve_touched_repo_file()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__map_path_to_repo()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__collect_touched_repos()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	def __init__(self, path: Path, is_tracked_fn) -> None:
		self.__path = path
		self.__is_tracked = is_tracked_fn
	# @used-by :meth:`WorktreePathResolver.resolve()`
	def __resolve_deleted(self) -> tuple[Path, str] | None:
		r: tuple[Path, str] | None = None
		parts = self.__path.parts
		for idx in range(len(parts) - 3):
			if ('\ua616', 'data', 'worktrees') == parts[idx:idx + 3] and idx + 4 < len(parts):
				proj_root = Path(*parts[:idx]).resolve()
				rel = Path(*parts[idx + 4:]).as_posix()
				for cr in project_paths(proj_root).code_repos:
					if self.__is_tracked(cr) and (cr / rel).exists():
						r = (cr.resolve(), rel)
						break
				break
		return r
	# @used-by :func:`agent_tools.worktree_flow.resolve_touched_repo_file()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__map_path_to_repo()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__collect_touched_repos()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	def resolve(self) -> tuple[Path, str] | None:
		r: tuple[Path, str] | None = None
		for anc in (self.__path, *self.__path.parents):
			if self.__is_tracked(anc):
				try:
					rel = self.__path.relative_to(anc).as_posix()
				except ValueError:
					break
				if rel and '.' != rel and (not rel.startswith(_SKIP_PREFIXES)):
					r = (anc, rel)
				break
		return r if None is not r else self.__resolve_deleted()
