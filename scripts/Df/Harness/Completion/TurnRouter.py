# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.turn_routing_ops import dfh_resolve_active_turn_state, dfh_resolve_handoff_target_root
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class TurnRouter:
	# @used-by :func:`agent_tools.turn_routing.resolve_active_turn_state()`
	# @used-by :func:`agent_tools.turn_routing.resolve_handoff_target_root()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_completion_subsystem_classes()`
	def __init__(self, t_dir: Path, session_id: str, last_user_step: int, *, rows: list[dict] | None=None, user_text: str | None=None, mode: str='active', brain_dir: Path | None=None, conversations_dir: Path | None=None, t_path: Path | None=None) -> None:
		self.__t_dir = t_dir
		self.__session_id = session_id
		self.__last_user_step = last_user_step
		self.__rows = rows
		self.__user_text = user_text
		self.__mode = mode
		self.__brain_dir = brain_dir
		self.__conversations_dir = conversations_dir
		self.__t_path = t_path
	# @used-by :func:`agent_tools.turn_routing.resolve_active_turn_state()`
	# @used-by :func:`agent_tools.turn_routing.resolve_handoff_target_root()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_completion_subsystem_classes()`
	def run(self) -> Any:
		if 'handoff' == self.__mode:
			r: Any = dfh_resolve_handoff_target_root(self.__t_dir, self.__session_id, self.__last_user_step, brain_dir=self.__brain_dir, conversations_dir=self.__conversations_dir, t_path=self.__t_path, rows=self.__rows, user_text=self.__user_text)
		else:
			r = dfh_resolve_active_turn_state(self.__t_dir, self.__session_id, self.__last_user_step, rows=self.__rows, user_text=self.__user_text)
		return r
