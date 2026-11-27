# 2026-10-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Cli.GitShim import GitShim, _NET_SUBCOMMANDS
# @used-by :mod:`git_shim`
def main(argv: list[str] | None=None) -> int:
	return GitShim(argv, mode='main', script_dir=Path(__file__).resolve().parent).run()
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_read_git_and_git_shim_and_unflagged_detector()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
# @used-by :mod:`git_shim`
def prepare_git_invocation(argv: list[str], *, mode: str | None=None, cwd: Path | None=None) -> tuple[list[str], dict[str, str]]:
	return GitShim(argv, mode='prepare', shim_mode=mode, cwd=cwd, script_dir=Path(__file__).resolve().parent).run()
# @used-by unused
def resolve_system_git() -> str:
	return GitShim([], mode='resolve_git', script_dir=Path(__file__).resolve().parent).run()
normalize_argv = prepare_git_invocation
if '__main__' == __name__:
	raise SystemExit(main())