# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Hook.SubagentChecker import SubagentChecker
from Df.Harness.lib.hook_subagent_ops import dfh_evaluate_schedule_subagent_block as evaluate_schedule_subagent_block, dfh_extract_segment_subagent_state as extract_segment_subagent_state, dfh_filter_turn_db_rows as _filter_turn_db_rows, dfh_is_row_running as _is_row_running, dfh_query_summary_children as _query_summary_children
# @used-by :mod:`agent_tools.stop_subagent_check`
def has_running_subagents(state: dict, session_id: str, conversations_db: Path | None=None) -> bool:
	return SubagentChecker(state, session_id, conversations_db).run()
__all__ = ['_filter_turn_db_rows', '_is_row_running', '_query_summary_children', 'evaluate_schedule_subagent_block', 'extract_segment_subagent_state', 'has_running_subagents']