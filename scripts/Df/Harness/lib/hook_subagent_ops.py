# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import re
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_CHILD_MSG_RE = re.compile(r'\[Message\]\s+timestamp=[^\n]*?\bsender=([a-f0-9-]{36})(?!/)\b', re.I)
_INVOKE_UUID_RE = re.compile(r'"(?:conversationId|agent_id|subagent_id)"\s*:\s*"([a-f0-9-]{36})"', re.I)
_LEGACY_DONE_RE = re.compile(r'<SYSTEM_MESSAGE>.*\bSubagent\b.*\bcompleted\b', re.S)
_OPTIONAL_COLS = (('status', "''"), ('not_fully_idle', '0'), ('killed', '0'), ('last_modified_time', "''"))
_TERMINAL_STATUSES = frozenset({'CASCADE_RUN_STATUS_IDLE', 'IDLE', 'COMPLETED', 'FAILED', 'ERROR', 'CANCELED', 'CANCELLED', 'KILLED'})
_UUID_RE = re.compile(r'^[a-f0-9-]{36}$', re.I)
# @used-by :func:`_process_row_calls()`
def _apply_call(segment: list[dict], pos: int, row: dict, call: dict, state: dict) -> None:
	cname = str(call.get('name') or '')
	args = _parse_args(call.get('args'))
	if 'invoke_subagent' == cname:
		_record_invoke(segment, pos, row, args, state)
	elif 'manage_subagents' == cname:
		_process_manage_subagents(args, state)
	elif 'send_message' == cname:
		recip = str(args.get('Recipient') or '').strip().lower()
		if _UUID_RE.fullmatch(recip):
			state['spawned_uuids'].add(recip)
			state['completed_uuids'].discard(recip)
			state['killed_all'] = False
			state['spawned'] += 1
# @used-by :func:`_record_invoke()`
def _collect_invoke_outputs(segment: list[dict], pos: int) -> set[str]:
	found: set[str] = set()
	for nxt in segment[pos + 1:]:
		if not isinstance(nxt, dict):
			continue
		if nxt.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
			break
		if 'GENERIC' == nxt.get('type') and nxt.get('content'):
			found.update((u.lower() for u in _INVOKE_UUID_RE.findall(str(nxt.get('content')))))
	return found
# @used-by :func:`dfh_query_summary_children()`
def _fetch_summary_rows(conn: sqlite3.Connection, session_id: str) -> list[dict] | None:
	cols = {row[1] for row in conn.execute('PRAGMA table_info(conversation_summaries)')}
	r: list[dict] | None = None
	if {'conversation_id', 'parent_conversation_id'}.issubset(cols):
		sel = ['conversation_id', *(c if c in cols else d for c, d in _OPTIONAL_COLS)]
		cols_sql = ','.join(sel)
		raw = conn.execute(f'SELECT {cols_sql} FROM conversation_summaries WHERE lower(parent_conversation_id)=?', (session_id.strip().lower(),)).fetchall()
		r = [{'conversation_id': str(x[0] or '').strip().lower(), 'killed': x[3], 'last_modified_time': x[4], 'not_fully_idle': x[2], 'status': x[1]} for x in raw if x[0]]
	return r
# @used-by :func:`dfh_evaluate_schedule_subagent_block()`
def _find_summary_db(t_path: Path) -> Path | None:
	r: Path | None = None
	for parent in t_path.parents:
		if 'brain' == parent.name.lower():
			cand = parent.parent / 'conversation_summaries.db'
			if cand.is_file():
				r = cand
			break
	return r
# @used-by :func:`dfh_evaluate_schedule_subagent_block()`
def _live_running_db_children(conversations_db: Path | None, session_id: str, killed_uuids: set[str]) -> list[str]:
	db_rows = dfh_query_summary_children(conversations_db, session_id) if session_id else None
	return sorted({row['conversation_id'] for row in (db_rows or ()) if row['conversation_id'] not in killed_uuids and dfh_is_row_running(row)})
# @used-by :func:`dfh_filter_turn_db_rows()`
def _norm_ts(value) -> str:
	raw = str(value or '').strip()
	return raw.replace('T', ' ').rstrip('Z')[:19] if 19 <= len(raw) else ''
# @used-by :func:`_apply_call()`
def _parse_args(raw) -> dict:
	r: dict = {}
	if isinstance(raw, dict):
		r = raw
	elif isinstance(raw, str) and raw.strip():
		try:
			parsed = json.loads(raw)
			if isinstance(parsed, dict):
				r = parsed
		except ValueError:
			r = {}
	return r
# @used-by :func:`_apply_call()`
def _process_manage_subagents(args: dict, state: dict) -> None:
	action = str(args.get('Action') or '').strip().lower()
	if 'kill_all' == action:
		state['killed_all'] = True
	elif 'kill' == action:
		for raw_id in args.get('ConversationIds') or ():
			cid = str(raw_id or '').strip().lower()
			if _UUID_RE.fullmatch(cid):
				state['killed_uuids'].add(cid)
# @used-by :func:`dfh_extract_segment_subagent_state()`
def _process_row_calls(segment: list[dict], pos: int, row: dict, state: dict) -> None:
	calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
	for call in calls:
		_apply_call(segment, pos, row, call, state)
	if 'PLANNER_RESPONSE' == row.get('type') and (not calls) and str(row.get('content') or '').strip():
		state['last_planner_text'] = str(row.get('content'))
# @used-by :func:`dfh_extract_segment_subagent_state()`
def _process_row_message(row: dict, state: dict) -> None:
	rtype = row.get('type')
	if rtype in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE'):
		content = str(row.get('content') or '')
		header = re.split(r'\bcontent=', content, maxsplit=1)[0]
		senders = [u.lower() for u in _CHILD_MSG_RE.findall(header)]
		if senders:
			state['completed_uuids'].update(senders)
			state['spawned_uuids'].update(senders)
		elif 'EPHEMERAL_MESSAGE' == rtype and _LEGACY_DONE_RE.search(content):
			state['legacy_completed'] += 1
# @used-by :func:`dfh_evaluate_schedule_subagent_block()`
def _read_turn_segment(t_path: Path) -> list[dict]:
	try:
		rows = [json.loads(line) for line in t_path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
	except (OSError, ValueError):
		rows = []
	last_user = -1
	for idx, row in enumerate(rows):
		if isinstance(row, dict) and 'USER_INPUT' == row.get('type'):
			last_user = idx
	return rows[last_user + 1:] if 0 <= last_user else rows
# @used-by :func:`_apply_call()`
def _record_invoke(segment: list[dict], pos: int, row: dict, args: dict, state: dict) -> None:
	sub_list = args.get('Subagents')
	state['spawned'] += len(sub_list) if isinstance(sub_list, list) and sub_list else 1
	state['killed_all'] = False
	if not state['first_spawn_ts'] and row.get('created_at'):
		state['first_spawn_ts'] = str(row.get('created_at'))
	state['spawned_uuids'].update(_collect_invoke_outputs(segment, pos))
# @used-by :func:`dfh_evaluate_schedule_subagent_block()`
def _resolve_transcript_file(transcript_path: str) -> Path | None:
	r = Path(transcript_path) if transcript_path else None
	if None is not r and 'transcript.jsonl' == r.name:
		full = r.parent / 'transcript_full.jsonl'
		if full.is_file():
			r = full
	return r if None is not r and r.is_file() else None
# @used-by :func:`agent_tools.failfast_gate._schedule_block_reason()`
# @used-by :mod:`agent_tools.stop_subagent_check`
def dfh_evaluate_schedule_subagent_block(transcript_path: str, args: dict, payload: dict) -> str | None:
	from Df.Harness.Hook.SubagentChecker import SubagentChecker
	t_path = _resolve_transcript_file(transcript_path)
	r: str | None = None
	if None is not t_path:
		state = dfh_extract_segment_subagent_state(_read_turn_segment(t_path))
		cond = str(args.get('TimerCondition') or '').strip().lower()
		sid = str(payload.get('conversationId') or payload.get('conversation_id') or '').strip()
		db_path = _find_summary_db(t_path)
		live_running = _live_running_db_children(db_path, sid, state['killed_uuids'])
		if cond and cond in state['spawned_uuids']:
			r = f'EXEC-4-SCHEDULE-GATE: Do not attach a schedule timer to invoke_subagent worker "{cond}"; invoke_subagent already delivers reactive completion notifications.'
		elif live_running or SubagentChecker(state, sid, db_path).run():
			pending = live_running or sorted(state['spawned_uuids'] - state['completed_uuids'] - state['killed_uuids'])
			spawned = state['spawned']
			label = ', '.join(pending) if pending else f'{spawned} active'
			r = f'EXEC-4-SCHEDULE-GATE: Active invoke_subagent worker(s) ({label}) already deliver reactive completion notifications; do not attach a one-shot schedule timer over active subagents.'
	return r
# @used-by :func:`dfh_evaluate_schedule_subagent_block()`
# @used-by :meth:`Df.Harness.Hook.StopGate.StopGate.__load_state_context()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.test_schedule_gate_blocks_after_send_message_and_ignores_task_sender()`
# @used-by :mod:`agent_tools.stop_subagent_check`
def dfh_extract_segment_subagent_state(segment: list[dict]) -> dict:
	state = {'completed_uuids': set(), 'first_spawn_ts': '', 'killed_all': False, 'killed_uuids': set(), 'last_planner_text': '', 'legacy_completed': 0, 'spawned': 0, 'spawned_uuids': set()}
	for pos, row in enumerate(segment or ()):
		if isinstance(row, dict):
			_process_row_message(row, state)
			_process_row_calls(segment, pos, row, state)
	return state
# @used-by :meth:`Df.Harness.Hook.SubagentChecker.SubagentChecker.run()`
# @used-by :mod:`agent_tools.stop_subagent_check`
def dfh_filter_turn_db_rows(db_rows: list[dict], state: dict) -> list[dict]:
	spawned_ids = state['spawned_uuids']
	first_ts = _norm_ts(state.get('first_spawn_ts'))
	if spawned_ids:
		r = [row for row in db_rows if row['conversation_id'] in spawned_ids]
	elif first_ts:
		r = [row for row in db_rows if (not _norm_ts(row.get('last_modified_time'))) or _norm_ts(row.get('last_modified_time')) >= first_ts]
	else:
		r = list(db_rows)
	return r
# @used-by :func:`_live_running_db_children()`
# @used-by :meth:`Df.Harness.Hook.SubagentChecker.SubagentChecker.run()`
# @used-by :mod:`agent_tools.stop_subagent_check`
def dfh_is_row_running(row: dict) -> bool:
	if 0 != int(row.get('killed') or 0):
		r = False
	else:
		status = str(row.get('status') or '').strip().upper()
		not_idle = 0 != int(row.get('not_fully_idle') or 0)
		r = not_idle or (bool(status) and status not in _TERMINAL_STATUSES)
	return r
# @used-by :func:`_live_running_db_children()`
# @used-by :meth:`Df.Harness.Hook.SubagentChecker.SubagentChecker.run()`
# @used-by :mod:`agent_tools.stop_subagent_check`
def dfh_query_summary_children(conversations_db: Path | None, session_id: str) -> list[dict] | None:
	db_path = Path(conversations_db) if None is not conversations_db else None
	r: list[dict] | None = None
	if None is not db_path and db_path.is_file():
		conn = None
		try:
			conn = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)
			r = _fetch_summary_rows(conn, session_id)
		except sqlite3.Error:
			r = None
		finally:
			if None is not conn:
				conn.close()
	return r