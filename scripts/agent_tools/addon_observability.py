# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Hook.AddonObserver import AddonObserver
from Df.Harness.lib.hook_addon_ops import dfh_check_close_companion_health as check_close_companion_health, dfh_check_runner_addon_observability as check_runner_addon_observability, dfh_default_companion_runtime_path as default_companion_runtime_path, dfh_detect_suppressed_worktree_errors as detect_suppressed_worktree_errors, dfh_evaluate_worktree_removal_audit as evaluate_worktree_removal_audit, dfh_format_pre_invocation_companion_warning as format_pre_invocation_companion_warning, dfh_inspect_companion_runtime_health as inspect_companion_runtime_health, dfh_is_live_runtime_data_file as is_live_runtime_data_file, dfh_is_pid_alive as _is_pid_alive, dfh_touches_antigravity_addons as _touches_antigravity_addons
# @used-by :meth:`Df.Harness.Gate.AnswerChecksGate.AnswerChecksGate.__addon_observability_messages()`
# @used-by :mod:`agent_tools.addon_observability`
def evaluate_addon_observability(root: Path, native: dict[str, Any] | None, turn: dict[str, Any] | None, value: dict[str, Any] | None, response: str | None) -> dict[str, Any]:
	return AddonObserver(root, native, turn, value, response).run()
__all__ = ['_is_pid_alive', '_touches_antigravity_addons', 'check_close_companion_health', 'check_runner_addon_observability', 'default_companion_runtime_path', 'detect_suppressed_worktree_errors', 'evaluate_addon_observability', 'evaluate_worktree_removal_audit', 'format_pre_invocation_companion_warning', 'inspect_companion_runtime_health', 'is_live_runtime_data_file']