# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
import subprocess
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :func:`agent_tools.worktree_flow._attach_land_telemetry()`
# @used-by :func:`dfh_fail_land()`
# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__fifo_fallback()`
# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__push_and_finish()`
def dfh_attach_land_telemetry(result: dict, plan: dict | None) -> dict:
	if None is not plan:
		from agent_tools.tdd.diff_executability import format_land_diff_telemetry
		result.update(format_land_diff_telemetry(plan))
	return result
# @used-by :func:`agent_tools.worktree_flow._fail_land()`
# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__fifo_fallback()`
# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__land_under_lease()`
# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__phase2_commit()`
# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.land()`
# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__push_and_finish()`
# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.merge()`
# @used-by :meth:`Df.Harness.Git.WorktreeRebaseVerifier.WorktreeRebaseVerifier.__fail_land()`
# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
def dfh_fail_land(main_repo: Path, wt_path: Path, branch: str, stage: str, error: str, *, test_runs: int=0, test_result: dict | None=None, plan: dict | None=None) -> dict:
	return dfh_attach_land_telemetry({'valid': False, 'landed': False, 'stage': stage, 'error': error, 'main_repo': main_repo.as_posix(), 'worktree': wt_path.as_posix(), 'branch': branch, 'test_runs': test_runs, 'test_result': test_result}, plan)
# @used-by :func:`agent_tools.worktree_flow.git_config_file()`
# @used-by :func:`dfh_has_origin_remote()`
# @used-by :meth:`Df.Harness.Arch.RepoReceiptSpecification.RepoReceiptSpecification.repo_slug()`
# @used-by :meth:`Df.Harness.Issue.RepoLocator.RepoLocator.__config_may_have_origin()`
# @used-by :meth:`Df.Harness.Issue.RepoLocator.RepoLocator.extract_config_slugs()`
# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
def dfh_git_config_file(code_repo: Path) -> Path:
	from Df.Harness.Git.RepoGate import RepoGate
	resolved = Path(code_repo).resolve()
	dot_git = resolved / '.git'
	return (RepoGate(resolved).main_repo() / '.git/config') if dot_git.is_file() else (dot_git / 'config')
# @used-by :func:`agent_tools.worktree_flow._git_exec()`
# @used-by :meth:`Df.Harness.Git.WorktreeCleaner.WorktreeCleaner.__init__()`
# @used-by :meth:`Df.Harness.Git.WorktreeCreator.WorktreeCreator.__init__()`
# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__init__()`
# @used-by :meth:`Df.Harness.Git.WorktreeRebaseVerifier.WorktreeRebaseVerifier.__init__()`
# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
def dfh_git_exec(repo: Path, *args: str, timeout: int=300) -> subprocess.CompletedProcess:
	return subprocess.run(['git', '-C', str(Path(repo).resolve()), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False, timeout=timeout, creationflags=_NO_WINDOW)
# @used-by :func:`agent_tools.repo_tags.has_origin_remote()`
# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.ensure()`
# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.run()`
# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
def dfh_has_origin_remote(repo: Path, *, remote: str='origin') -> bool:
	cfg = dfh_git_config_file(repo)
	if cfg.is_file():
		r = f'[remote "{remote}"]' in cfg.read_text(encoding='utf-8', errors='replace')
	else:
		from Df.Harness.Git.RepoGate import RepoGate
		r = 0 == RepoGate(repo).run_read(['remote', 'get-url', remote], check=False).returncode
	return r
# @used-by :func:`agent_tools.git_ignore.prepare_worktrees_base_dir()`
# @used-by :meth:`Df.Harness.Git.WorktreeCreator.WorktreeCreator.begin()`
# @used-by :meth:`Df.Harness.Git.WorktreeTransaction.WorktreeTransaction.create()`
def dfh_prepare_worktrees_base_dir(repo: Path | str, *, worktrees_dir: Path | str | None=None) -> tuple[Path, dict]:
	from Df.Harness.Git.WorktreeExcludeManager import WorktreeExcludeManager
	if None is not worktrees_dir:
		base = HostPathNormalizer(str(worktrees_dir)).normalize().resolve()
	else:
		from agent_tools.path_registry import project_paths
		base = project_paths(Path(repo).resolve()).worktrees_dir.resolve()
	return (base, WorktreeExcludeManager(base).ensure())
