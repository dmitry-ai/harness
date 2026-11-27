# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.hook_stop_ops import dfh_find_target_turn, dfh_record_emergency_locked
from Df.Harness.lib.storage import dfh_locked
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class EmergencyCapturer:
	# @used-by :func:`Df.Harness.lib.hook_stop_ops.dfh_evaluate_continuation_reentry()`
	# @used-by :func:`agent_tools.stop_emergency_capture.maybe_emergency_capture_journal()`
	def __init__(self, root_or_data: Path, session_id: str, last_user_step: int, matched_state: dict | None, decision: dict, emergency_ctx: dict[str, Any] | None) -> None:
		self.__root_or_data = root_or_data
		self.__session_id = session_id
		self.__last_user_step = last_user_step
		self.__matched_state = matched_state
		self.__decision = decision
		self.__emergency_ctx = emergency_ctx
	# @used-by :func:`Df.Harness.lib.hook_stop_ops.dfh_evaluate_continuation_reentry()`
	# @used-by :func:`agent_tools.stop_emergency_capture.maybe_emergency_capture_journal()`
	def run(self) -> dict[str, Any] | None:
		from Df.Harness.lib.completion_core import dfh_native_scan, dfh_turn_key, dfh_turn_lock
		r: dict[str, Any] | None = None
		raw_text = str((self.__emergency_ctx or {}).get('last_planner_text') or '')
		if None is not self.__emergency_ctx and raw_text.strip() and self.__session_id:
			try:
				root = Path(self.__emergency_ctx['root']).resolve()
				native = dfh_native_scan(root, self.__session_id, platform='antigravity', backend=self.__emergency_ctx.get('backend'))
				turn = dfh_find_target_turn(native, self.__last_user_step)
				if None is not turn and turn.get('requests'):
					key = dfh_turn_key(native, turn)
					reason = str(self.__decision.get('reason') or 'Stop Gate fail-open')
					with dfh_locked(dfh_turn_lock(root, key)):
						r = dfh_record_emergency_locked(root, native, turn, raw_text, reason)
			except Exception:
				r = None
		return r