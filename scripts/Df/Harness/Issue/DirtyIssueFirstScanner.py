# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.RepoGate import RepoGate
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace
from Df.Harness.lib.issue import dfh_is_excluded_meta_rel
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DirtyIssueFirstScanner:
	# @used-by :func:`agent_tools.github_issue._dirty_issue_first_files()`
	# @used-by :func:`agent_tools.issues.service_helpers.dirty_issue_first_files()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_create()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_dirty_scanner_read_cache_and_locator()`
	def __init__(self, workspace: EvidenceWorkspace, repo: str, *, project_root: str | Path | None=None, source_files: list[tuple[Path, bytes]] | None=None, repo_root: str | Path | None=None) -> None:
		self.__workspace = workspace
		self.__repo = repo
		self.__project_root = project_root
		self.__source_files = source_files
		self.__repo_root = repo_root
	# @used-by :meth:`DirtyIssueFirstScanner.scan()`
	@staticmethod
	def __is_isolated_temp_root(code_repo: Path, project_root: str | Path | None) -> bool:
		r = False
		if None is not project_root and str(project_root).strip():
			pr = Path(project_root).resolve()
			pr_low = pr.as_posix().lower()
			if ('/temp/' in pr_low or '/tmp/' in pr_low) and (not code_repo.is_relative_to(pr)) and (not pr.is_relative_to(code_repo)):
				r = True
		return r
	# @used-by :meth:`DirtyIssueFirstScanner.scan()`
	@staticmethod
	def __parse_dirty_porcelain(code_repo: Path, stdout: bytes) -> list[str]:
		from agent_tools.addon_observability import is_live_runtime_data_file
		from agent_tools.tdd_gate import classify_code_path
		tracked = RepoGate(code_repo).is_issue_tracked()
		entries = [e for e in stdout.decode('utf-8', errors='replace').split('\x00') if e]
		dirty: list[str] = []
		idx = 0
		while idx < len(entries):
			entry = entries[idx]
			rel_path = entry[3:].replace('\\', '/')
			idx += 2 if entry[:2].startswith(('R', 'C')) and idx + 1 < len(entries) else 1
			if rel_path and (not dfh_is_excluded_meta_rel(rel_path)) and (not is_live_runtime_data_file(code_repo, rel_path)) and (tracked or 'non_code' != classify_code_path(code_repo / rel_path)):
				if rel_path not in dirty:
					dirty.append(rel_path)
		return sorted(dirty)
	# @used-by :func:`agent_tools.github_issue._dirty_issue_first_files()`
	# @used-by :func:`agent_tools.issues.service_helpers.dirty_issue_first_files()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.cmd_create()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_dirty_scanner_read_cache_and_locator()`
	def scan(self) -> list[str]:
		code_repo = self.__workspace.find_local_code_repo(self.__repo, project_root=self.__project_root, source_files=self.__source_files, repo_root=self.__repo_root)
		r: list[str] = []
		if None is not code_repo and (code_repo / '.git').exists() and (not self.__is_isolated_temp_root(code_repo, self.__project_root)):
			proc = RepoGate(code_repo).run_read(['status', '--porcelain', '-z', '--untracked-files=all'], check=False)
			if 0 == proc.returncode and proc.stdout:
				r = self.__parse_dirty_porcelain(code_repo, proc.stdout)
		return r
