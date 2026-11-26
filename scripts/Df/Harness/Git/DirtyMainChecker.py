# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.RepoGate import RepoGate
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DirtyMainChecker:
	# @used-by :func:`agent_tools.polyglot_land.dirty_blocking_main_files()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__land_under_lease()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__phase2_commit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def __init__(self, main_repo: Path, branch: str) -> None:
		self.__main_repo = main_repo
		self.__branch = branch
	# @used-by :meth:`DirtyMainChecker.find_blocking()`
	def __branch_touched(self) -> set[str]:
		proc = RepoGate(self.__main_repo).run_read(['diff', '--name-only', f'HEAD..{self.__branch}'], check=False)
		raw = proc.stdout.decode('utf-8', errors='replace') if 0 == proc.returncode else ''
		return {ln.strip().replace('\\', '/').lstrip('./').casefold() for ln in raw.splitlines() if ln.strip()}
	# @used-by :meth:`DirtyMainChecker.find_blocking()`
	@staticmethod
	def __porcelain_paths(raw: str) -> list[str]:
		paths: list[str] = []
		for line in (raw or '').splitlines():
			if 4 <= len(line):
				entry = line[3:].strip()
				if ' -> ' in entry:
					entry = entry.split(' -> ', 1)[1].strip()
				clean = entry.strip('"').replace('\\', '/').lstrip('./')
				if clean:
					paths.append(clean)
		return paths
	# @used-by :func:`agent_tools.polyglot_land.dirty_blocking_main_files()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__land_under_lease()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__phase2_commit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def find_blocking(self) -> list[str]:
		from agent_tools.addon_observability import is_live_runtime_data_file
		raw = RepoGate(self.__main_repo).git('status', '--porcelain').decode('utf-8', errors='replace')
		dirty = self.__porcelain_paths(raw)
		if not dirty:
			r: list[str] = []
		else:
			touched = self.__branch_touched()
			r = [rel for rel in dirty if rel.casefold() in touched or (not is_live_runtime_data_file(self.__main_repo, rel))]
		return r
