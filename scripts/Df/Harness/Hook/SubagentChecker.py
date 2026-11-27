# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.hook_subagent_ops import dfh_filter_turn_db_rows, dfh_is_row_running, dfh_query_summary_children
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class SubagentChecker:
	# @used-by :func:`Df.Harness.lib.hook_subagent_ops.dfh_evaluate_schedule_subagent_block()`
	# @used-by :func:`agent_tools.stop_subagent_check.has_running_subagents()`
	# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__load_state_context()`
	# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_subagent_checker_and_schedule_block()`
	def __init__(self, state: dict, session_id: str, conversations_db: Path | None=None) -> None:
		self.__state = state
		self.__session_id = session_id
		self.__conversations_db = conversations_db
	# @used-by :func:`Df.Harness.lib.hook_subagent_ops.dfh_evaluate_schedule_subagent_block()`
	# @used-by :func:`agent_tools.stop_subagent_check.has_running_subagents()`
	# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__load_state_context()`
	# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_subagent_checker_and_schedule_block()`
	def run(self) -> bool:
		if 0 >= int(self.__state.get('spawned') or 0) or self.__state.get('killed_all'):
			r = False
		else:
			db_rows = dfh_query_summary_children(self.__conversations_db, self.__session_id)
			matched = dfh_filter_turn_db_rows(db_rows, self.__state) if db_rows else []
			active_rows = [row for row in matched if row['conversation_id'] not in self.__state['killed_uuids']]
			if any((dfh_is_row_running(row) for row in active_rows)):
				r = True
			elif len(matched) >= int(self.__state['spawned']):
				r = False
			else:
				done_total = len(self.__state['completed_uuids'] | self.__state['killed_uuids']) + int(self.__state.get('legacy_completed') or 0)
				r = done_total < int(self.__state['spawned'])
		return r