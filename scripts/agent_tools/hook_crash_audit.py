# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Hook.CrashAuditor import CrashAuditor
from Df.Harness.lib.hook_crash_ops import dfh_build_violation_recovery_receipt as build_violation_recovery_receipt, dfh_check_runner_hook_crashes as check_runner_hook_crashes, dfh_detect_hook_crashes as detect_hook_crashes, dfh_has_recorded_hook_issue as _has_recorded_hook_issue, dfh_load_turn_rows as _load_turn_rows, dfh_load_violation_receipt as _load_violation_receipt, dfh_text_documents_hook_crash as _text_documents_hook_crash
# @used-by :meth:`test_snapshot_canary_and_hook_crash_audit.SnapshotCanaryAndHookCrashAuditTests.test_hook_crash_audit_blocks_silent_omission_and_accepts_disclosed_issue_or_recovery()`
# @used-by :mod:`agent_tools.hook_crash_audit`
def evaluate_hook_crash_check(root: Path, native: dict[str, Any] | None, turn: dict[str, Any] | None, value: dict[str, Any] | None, response: str | None) -> dict[str, Any]:
	return CrashAuditor(root, native, turn, value, response).run()
__all__ = ['_has_recorded_hook_issue', '_load_turn_rows', '_load_violation_receipt', '_text_documents_hook_crash', 'build_violation_recovery_receipt', 'check_runner_hook_crashes', 'detect_hook_crashes', 'evaluate_hook_crash_check']