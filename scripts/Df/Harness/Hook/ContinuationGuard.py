# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.hook_stop_ops import dfh_evaluate_continuation_reentry, dfh_failure_fingerprint, dfh_guard_file_path, dfh_is_continuation_reentry, dfh_load_guard, dfh_max_segment_step, dfh_save_guard, dfh_unlink_guard
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ContinuationGuard:
	# @used-by :func:`agent_tools.stop_hook_guard.apply_continuation_guard()`
	# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__evaluate_handoff()`
	# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__evaluate_matched_state()`
	def __init__(self, t_dir: Path, session_id: str, last_user_step: int, matched_state: dict | None, decision: dict, payload: dict, *, segment: list[dict] | None=None, emergency_ctx: dict[str, Any] | None=None) -> None:
		self.__t_dir = t_dir
		self.__session_id = session_id
		self.__last_user_step = last_user_step
		self.__matched_state = matched_state
		self.__decision = decision
		self.__payload = payload
		self.__segment = segment
		self.__emergency_ctx = emergency_ctx
	# @used-by :func:`agent_tools.stop_hook_guard.apply_continuation_guard()`
	# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__evaluate_handoff()`
	# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__evaluate_matched_state()`
	def run(self) -> dict:
		gfile = dfh_guard_file_path(self.__t_dir, self.__session_id, self.__last_user_step, self.__matched_state)
		if 'continue' != self.__decision.get('decision'):
			dfh_unlink_guard(gfile)
			r = self.__decision
		else:
			prev = dfh_load_guard(gfile)
			fp = dfh_failure_fingerprint(self.__matched_state, self.__decision, self.__last_user_step)
			last_step = dfh_max_segment_step(self.__segment, self.__last_user_step)
			if not dfh_is_continuation_reentry(self.__payload, prev, self.__last_user_step, last_step):
				dfh_save_guard(gfile, {'fingerprint': fp, 'last_step': last_step, 'last_user_step': self.__last_user_step, 'total_count': 1, 'unchanged_count': 1})
				r = self.__decision
			else:
				r = dfh_evaluate_continuation_reentry(gfile, fp, self.__last_user_step, last_step, prev, self.__decision, self.__payload, session_id=self.__session_id, matched_state=self.__matched_state, emergency_ctx=self.__emergency_ctx)
		return r