# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class ScheduleGate:
	NAME = 'EXEC-4-SCHEDULE-GATE'
	PRIORITY = 95
	TOOLS = frozenset({'schedule'})
	__BG_TASK_ENDED_RE = re.compile(r'Task\s+id\s+"([^"]+)"\s+(?:finished|canceled|cancelled|terminated|killed)\b', re.IGNORECASE)
	# @used-by :meth:`ScheduleGate.__schedule_block_reason()`
	@staticmethod
	def __active_turn_run_command_tasks(transcript_path: str) -> tuple[bool, set[str], set[str]]:
		rows = ScheduleGate.__read_transcript_rows(transcript_path)
		explicit, segment = ScheduleGate.__split_last_user_segment(rows)
		all_tids: set[str] = set()
		active_tids: set[str] = set()
		for pos, row in enumerate(segment):
			if isinstance(row, dict):
				ScheduleGate.__discard_ended_tasks(row, active_tids)
				ScheduleGate.__collect_started_tasks(segment, pos, row, all_tids, active_tids)
		return (explicit, all_tids, active_tids)
	# @used-by :meth:`ScheduleGate.__active_turn_run_command_tasks()`
	@staticmethod
	def __collect_started_tasks(segment: list, pos: int, row: dict, all_tids: set[str], active_tids: set[str]) -> None:
		calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
		if calls:
			outputs = ScheduleGate.__following_outputs(segment, pos)
			for c_idx, call in enumerate(calls):
				if 'run_command' == str(call.get('name') or ''):
					matched = [outputs[c_idx]] if c_idx < len(outputs) else outputs
					ScheduleGate.__record_output_task_ids(matched, all_tids, active_tids)
	# @used-by :meth:`ScheduleGate.__active_turn_run_command_tasks()`
	@staticmethod
	def __discard_ended_tasks(row: dict, active_tids: set[str]) -> None:
		if row.get('type') in ('SYSTEM_MESSAGE', 'EPHEMERAL_MESSAGE', 'GENERIC') and row.get('content'):
			from agent_tools.tdd_gate import _BG_TASK_FINISHED_RE
			c_str = str(row.get('content'))
			for m_end in ScheduleGate.__BG_TASK_ENDED_RE.finditer(c_str):
				active_tids.discard(m_end.group(1).strip())
			m_fin = _BG_TASK_FINISHED_RE.search(c_str)
			if m_fin:
				active_tids.discard(m_fin.group(1).strip())
	# @used-by :meth:`ScheduleGate.__collect_started_tasks()`
	@staticmethod
	def __following_outputs(segment: list, pos: int) -> list[str]:
		outputs: list[str] = []
		for nxt in segment[pos + 1:]:
			if not isinstance(nxt, dict):
				continue
			if nxt.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
				break
			if 'GENERIC' == nxt.get('type') and nxt.get('content'):
				outputs.append(str(nxt.get('content')))
		return outputs
	# @used-by :meth:`ScheduleGate.__active_turn_run_command_tasks()`
	@staticmethod
	def __read_transcript_rows(transcript_path: str) -> list:
		t_path = Path(transcript_path) if transcript_path else None
		if None is not t_path and 'transcript.jsonl' == t_path.name and (t_path.parent / 'transcript_full.jsonl').is_file():
			t_path = t_path.parent / 'transcript_full.jsonl'
		r: list = []
		if None is not t_path and t_path.is_file():
			try:
				r = [json.loads(line) for line in t_path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
			except (OSError, ValueError):
				r = []
		return r
	# @used-by :meth:`ScheduleGate.__collect_started_tasks()`
	@staticmethod
	def __record_output_task_ids(outputs: list[str], all_tids: set[str], active_tids: set[str]) -> None:
		from agent_tools.tdd_gate import _BG_TASK_ID_RE
		for out_s in outputs:
			for m_tid in _BG_TASK_ID_RE.finditer(out_s):
				tid = m_tid.group(1).strip().rstrip('.,')
				if tid:
					all_tids.add(tid)
					active_tids.add(tid)
	# @used-by :meth:`ScheduleGate.check()`
	@staticmethod
	def __schedule_block_reason(t_raw: str, args: dict, payload: dict) -> str | None:
		from agent_tools.stop_subagent_check import evaluate_schedule_subagent_block
		explicit_schedule, all_tids, active_tids = ScheduleGate.__active_turn_run_command_tasks(t_raw)
		r = None
		if not explicit_schedule:
			cond = str(args.get('TimerCondition') or '').strip()
			if cond and cond in all_tids:
				r = f'EXEC-4-SCHEDULE-GATE: Do not attach a schedule timer to run_command task "{cond}"; run_command already delivers reactive completion notifications. Use in-process timeouts such as harness.py run-tests --module-timeout instead.'
			elif active_tids:
				joined = ', '.join(sorted(active_tids))
				r = f'EXEC-4-SCHEDULE-GATE: Active background run_command task(s) ({joined}) already deliver reactive completion notifications; do not attach a one-shot schedule timer over active run_command tasks.'
			else:
				r = evaluate_schedule_subagent_block(t_raw, args, payload)
		return r
	# @used-by :meth:`ScheduleGate.__active_turn_run_command_tasks()`
	@staticmethod
	def __split_last_user_segment(rows: list) -> tuple[bool, list]:
		last_user = -1
		for idx, row in enumerate(rows):
			if isinstance(row, dict) and 'USER_INPUT' == row.get('type'):
				last_user = idx
		explicit = bool(re.search(r'(?i)(?:^|\s)/schedule(?:\s|$)', str(rows[last_user].get('content') or ''))) if 0 <= last_user else False
		return (explicit, rows[last_user + 1:] if 0 <= last_user else rows)
	# @used-by :func:`agent_tools.failfast_gate.evaluate_pre_tool_use_schedule()`
	# @used-by :func:`agent_tools.gates.schedule_gate.check()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		is_one_shot = 'schedule' == name and (not args.get('CronExpression')) and (True is not args.get('IsDaemon')) and (None is not args.get('DurationSeconds'))
		return ScheduleGate.__schedule_block_reason(str((payload or {}).get('transcriptPath') or '').strip(), args, payload or {}) if is_one_shot else None
