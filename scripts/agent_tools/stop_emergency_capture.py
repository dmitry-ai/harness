# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Hook.EmergencyCapturer import EmergencyCapturer
from Df.Harness.lib.hook_stop_ops import dfh_find_target_turn as _find_target_turn, dfh_record_emergency_locked as _record_emergency_locked
# @used-by :mod:`agent_tools.stop_emergency_capture`
def maybe_emergency_capture_journal(root_or_data: Path, session_id: str, last_user_step: int, matched_state: dict | None, decision: dict, emergency_ctx: dict[str, Any] | None) -> dict[str, Any] | None:
	return EmergencyCapturer(root_or_data, session_id, last_user_step, matched_state, decision, emergency_ctx).run()
__all__ = ['_find_target_turn', '_record_emergency_locked', 'maybe_emergency_capture_journal']