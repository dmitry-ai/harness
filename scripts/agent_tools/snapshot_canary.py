# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Runtime.CanaryProbe import CanaryProbe
from Df.Harness.lib.snapshot_canary_ops import CANARY_COMMITTED_FILES, CANARY_MAX_SECONDS, CANARY_MAX_SUBPROCESSES, CANARY_PROBE as _CANARY_PROBE, NO_WINDOW as _NO_WINDOW
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`run_pre_tool_use_canary()`
def _large_canary_via_facade(staging: Path) -> tuple[bool, str]:
	from .snapshot_latency_canary import run_large_transcript_latency_canary
	return run_large_transcript_latency_canary(staging)
# @used-by :func:`agent_tools.runtime_snapshot._canary_via_facade()`
# @used-by :meth:`test_snapshot_canary_and_hook_crash_audit.SnapshotCanaryAndHookCrashAuditTests.test_live_worktree_passes_pre_tool_use_canary()`
# @used-by :mod:`agent_tools.snapshot_canary`
def run_pre_tool_use_canary(staging: Path, *, max_seconds: float=CANARY_MAX_SECONDS, max_subprocesses: int=CANARY_MAX_SUBPROCESSES, committed_files: int=CANARY_COMMITTED_FILES) -> tuple[bool, str]:
	return CanaryProbe(staging, max_seconds=max_seconds, max_subprocesses=max_subprocesses, committed_files=committed_files, large_canary_fn=_large_canary_via_facade).run()
__all__ = ['CANARY_COMMITTED_FILES', 'CANARY_MAX_SECONDS', 'CANARY_MAX_SUBPROCESSES', 'run_pre_tool_use_canary']
