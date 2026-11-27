# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Hook.ContinuationGuard import ContinuationGuard
from Df.Harness.lib.hook_stop_ops import MAX_TOTAL_CONTINUATIONS, dfh_evaluate_continuation_reentry as _evaluate_continuation_reentry, dfh_extract_stop_context as extract_stop_context, dfh_failure_fingerprint as _failure_fingerprint, dfh_guard_file_path as _guard_file_path, dfh_handoff_matches_user_step as handoff_matches_user_step, dfh_is_continuation_reentry as _is_continuation_reentry, dfh_is_journal_opt_out as is_journal_opt_out, dfh_load_guard as _load_guard, dfh_max_segment_step as _max_segment_step, dfh_save_guard as _save_guard, dfh_unlink_guard as _unlink_guard
# @used-by :mod:`agent_tools.stop_hook_guard`
def apply_continuation_guard(t_dir: Path, session_id: str, last_user_step: int, matched_state: dict | None, decision: dict, payload: dict, *, segment: list[dict] | None=None, emergency_ctx: dict[str, Any] | None=None) -> dict:
	return ContinuationGuard(t_dir, session_id, last_user_step, matched_state, decision, payload, segment=segment, emergency_ctx=emergency_ctx).run()
__all__ = ['MAX_TOTAL_CONTINUATIONS', '_evaluate_continuation_reentry', '_failure_fingerprint', '_guard_file_path', '_is_continuation_reentry', '_load_guard', '_max_segment_step', '_save_guard', '_unlink_guard', 'apply_continuation_guard', 'extract_stop_context', 'handoff_matches_user_step', 'is_journal_opt_out']