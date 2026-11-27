# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Runtime.LauncherRenderer import LauncherRenderer
from Df.Harness.lib.runtime_launcher_templates import GIT_HOOK_LAUNCHER_HEADER, GIT_MAIN as _GIT_MAIN, HOOK_DISCOVERY as _HOOK_DISCOVERY, HOOK_MAIN as _HOOK_MAIN, HOOK_RUNNER_HEADER, RUNNER_COMMON as _RUNNER_COMMON, dfh_git_hook_shell_wrapper as git_hook_shell_wrapper
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :mod:`agent_tools.runtime_snapshot`
def git_hook_launcher_source(primary: str | Path, *, store_dir: str | Path | None=None) -> str:
	return LauncherRenderer(primary, store_dir=store_dir, kind='git_hook').run()
# @used-by :func:`agent_tools.upwork_project.harness_hook_runner_source()`
# @used-by :func:`test_hook_runner_e2e_budget._stage_snapshot_runner()`
# @used-by :func:`test_hook_runner_watchdog._seed_two_releases()`
# @used-by :meth:`test_hook_runner_watchdog.HookRunnerWatchdogTests.test_watchdog_env_override_terminates_hung_child_process_and_keeps_ascii_header()`
# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_lkg_fallback_runs_previous_release_when_current_crashes()`
# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_promote_exports_snapshot_surviving_live_tree_corruption_and_preserving_anchor()`
# @used-by :mod:`agent_tools.runtime_snapshot`
def harness_hook_runner_source(primary: str | Path, *, store_dir: str | Path | None=None) -> str:
	return LauncherRenderer(primary, store_dir=store_dir, kind='hook_runner').run()
