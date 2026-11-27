# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.ag_inputs import dfh_antigravity_paths, dfh_conversation_db_path, dfh_extract_subagent_uuids, dfh_native_inputs, dfh_request_scope, dfh_transcript_path, dfh_workspace_context
from Df.Harness.lib.ag_wire import dfh_configuration
from Df.Harness.lib.clarifications_ops import dfh_build_segment_metadata, dfh_merge_segment_metadata
from Df.Harness.lib.journal_core import dfh_journal_pair_dirs, dfh_resolve_journal_dir, dfh_step_file
from Df.Harness.lib.journal_records import dfh_completed_request_group_index
from Df.Harness.lib.request_binding import dfh_completion_project_id
from Df.Harness.lib.trace_common import dfh_is_waiting_status_stub, dfh_open_readonly_sqlite, dfh_parse_tool_args, dfh_read_jsonl_objects
from Df.Harness.lib.trace_effects import dfh_collect_subagent_bfs, dfh_init_turn_accumulator, dfh_merge_turn_accumulators, dfh_record_normalized_tool_effects
from agent_tools.shell_audit import extract_issue_actions_from_outputs
import json
import re
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_BG_TASK_ENDED_RE = re.compile(r'Task\s+id\s+"([^"]+)"\s+(?:finished|canceled|cancelled|terminated|killed)\b', re.IGNORECASE)
_BG_TASK_SENDER_RE = re.compile(r'\bsender=([A-Za-z0-9_./:-]+/task-\d+)\b', re.IGNORECASE)
_SEGMENT_TRANSIENT_KEYS = {'spawned_subagents', 'completed_subagents', 'answer_prepared_in_segment', 'bg_tdd_index', 'active_bg_tasks'}
class TurnScanner:
	# @used-by :func:`Df.Harness.lib.completion_core._scan_native_for_platform()`
	# @used-by :func:`Df.Harness.lib.hook_pre_invocation_ops._diagnose_no_active_turn()`
	# @used-by :func:`agent_tools.platforms.antigravity.native_answers()`
	# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_platform_turn_scanner_and_ag_tail()`
	# @used-by :meth:`test_tdd_worktree_land_green.TddWorktreeLandGreenTests.test_antigravity_scanners_forward_untruncated_output_to_tdd_while_capping_tool_records()`
	def __init__(self, root, conversation_id: str, *, backend=None, instance=None, _ops: dict[str, Any] | None=None) -> None:
		self.__ops = _ops or {}
		self.__root = root
		self.__root_p = Path(root).resolve()
		self.__conversation_id = conversation_id
		self.__paths = dfh_antigravity_paths(backend=backend, instance=instance, conversation_id=conversation_id, settings_fn=self.__ops.get('settings'))
		self.__backend = Path(self.__paths['backend_dir']).resolve()
		self.__init_scan_state()
	# @used-by :meth:`TurnScanner.__record_subagent_tool_calls()`
	# @used-by :meth:`TurnScanner.__scan_segment_row()`
	def __collect_outputs(self, rows_slice: list, start_pos: int, *, step_idx=None, file_reads=None) -> list[str]:
		r: list[str] = []
		for cand in rows_slice[start_pos + 1:]:
			if not isinstance(cand, dict):
				continue
			if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
				break
			if 'GENERIC' == cand.get('type') and cand.get('content'):
				c_str = str(cand.get('content'))
				# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
				r.append(c_str)
				self.__record_step_output_reads(c_str, step_idx, file_reads)
		return r
	# @used-by :meth:`TurnScanner.__scan_segment()`
	def __collect_subagent_bfs(self, position: int, segment: list, seg: dict) -> set[str]:
		r = {self.__conversation_id}
		if seg['subagent_steps']:
			seeds = [(m_uuid, bool(seg['aa_subagent_steps']), self.__conversation_id) for m_uuid in dfh_extract_subagent_uuids(segment)]
			if 1 == len(self.__boundaries) - position:
				seeds.extend(self.__db_child_seeds(seg))
			anchor = seg['subagent_steps'][-1]
			r = dfh_collect_subagent_bfs(self.__conversation_id, self.__root_p, seeds, lambda cid, depth, hint, parent: self.__resolve_subagent_child(cid, hint, parent, anchor, seg), seg['aa_partial_read_violations'])
		return r
	# @used-by :meth:`TurnScanner.__collect_subagent_bfs()`
	def __db_child_seeds(self, seg: dict) -> list[tuple]:
		r: list[tuple] = []
		try:
			with dfh_open_readonly_sqlite(self.__paths['conversations_db']) as p_conn:
				rows = p_conn.execute('SELECT conversation_id FROM conversation_summaries WHERE parent_conversation_id=?', (self.__conversation_id,)).fetchall()
				r = [(p_row[0], bool(seg['aa_subagent_steps']), self.__conversation_id) for p_row in rows if p_row and p_row[0] and p_row[0] not in self.__completed_turn_cids]
		except Exception:
			r = []
		return r
	# @used-by :meth:`TurnScanner.__scan_segment()`
	def __finalize_segment(self, start: int, end, segment: list, seg: dict, visited_cids: set, seg_models=()) -> dict[str, Any]:
		last = segment[-1] if segment else {}
		final_step = last.get('step_index')
		completed, resp_text = self.__resolve_segment_completion(start, end, last, seg)
		start_row = self.__row_by_step.get(start)
		req_ts = start_row.get('created_at') if isinstance(start_row, dict) and isinstance(start_row.get('created_at'), str) and start_row['created_at'].strip() else None
		resp_ts = last.get('created_at') if completed and isinstance(last.get('created_at'), str) and last['created_at'].strip() else None
		seg_meta = dfh_build_segment_metadata(segment, seg_models, dfh_configuration)
		self.__completed_turn_cids.update(visited_cids - {self.__conversation_id})
		return {'turn_id': f'ag-{self.__conversation_id}-{start}', 'requests': [self.__requests[start]] if start in self.__requests else [], 'owned': start in self.__requests, 'completed': completed, 'aborted': False, 'response': resp_text, 'start_step': start, 'final_step': final_step if completed else None, 'completion_step': final_step if completed else None, 'request_timestamp': req_ts, 'response_timestamp': resp_ts, **seg_meta, **{k: v for k, v in seg.items() if k not in _SEGMENT_TRANSIENT_KEYS}}
	# @used-by :meth:`TurnScanner.scan()`
	def __group_segments(self) -> list[dict[str, Any]]:
		grouped, pending = ([], [])
		for position, start in enumerate(self.__boundaries):
			turn = self.__scan_segment(position, start)
			if pending and pending[-1]['owned'] != turn['owned']:
				pending = []
			pending.append(turn)
			if turn['completed']:
				grouped.append(self.__merge_pending(pending))
				pending = []
		if pending:
			grouped.append(self.__merge_pending(pending))
		for idx, item in enumerate(grouped, 1):
			item['turn_index'] = idx
		return grouped
	# @used-by :meth:`TurnScanner.__scan_segment_row()`
	def __handle_system_message(self, c_str: str, step_idx, seg: dict) -> None:
		from agent_tools.issue_first_bg import handle_antigravity_bg_task_message
		from agent_tools.tdd_gate import parse_command_outcome
		if re.search('<SYSTEM_MESSAGE>.*(?:\\bSubagent\\b.*\\bcompleted\\b|\\[Message\\]\\s+timestamp=[^\\n]+\\bsender=[0-9a-f]{8}-[0-9a-f]{4}-)', c_str, re.S | re.I):
			seg['completed_subagents'] += 1
		for m_end in _BG_TASK_ENDED_RE.finditer(c_str):
			seg['active_bg_tasks'].discard(m_end.group(1).strip())
		for m_snd in _BG_TASK_SENDER_RE.finditer(c_str):
			seg['active_bg_tasks'].discard(m_snd.group(1).strip())
		handle_antigravity_bg_task_message(c_str, step_idx, seg, parse_command_outcome)
	# @used-by :meth:`TurnScanner.__init__()`
	def __init_scan_state(self) -> None:
		self.__summary: dict | None = None
		self.__path: Any = None
		self.__rows: list = []
		self.__inputs: list = []
		self.__requests: dict = {}
		self.__statuses: dict = {}
		self.__jdir: Any = None
		self.__journal_groups: dict = {}
		self.__boundaries: list[int] = []
		self.__completed_turn_cids: set[str] = set()
		self.__scope_active = False
		self.__scope_binding = None
		self.__expected_job_id: str | None = None
		self.__workspace_root: str | None = None
		self.__row_by_step: dict = {}
	# @used-by :meth:`TurnScanner.__resolve_segment_completion()`
	def __is_final_idle(self, start: int, last: dict) -> tuple[bool, bool]:
		final_step = last.get('step_index')
		final = 'PLANNER_RESPONSE' == last.get('type') and (not last.get('tool_calls')) and bool(last.get('content', '').strip()) and self.__statuses.get(final_step) in ((15, 3), (15, 5))
		last_user_idx = self.__summary.get('last_user_input_step_index')
		last_db_user = max((idx for idx, (stype, _) in self.__statuses.items() if 14 == stype), default=start)
		idle = 'CASCADE_RUN_STATUS_IDLE' == self.__summary.get('status') and 0 == self.__summary.get('not_fully_idle') and (not self.__summary.get('killed')) and (last_user_idx == start or (0 == start and -1 == last_user_idx)) and last_db_user == start and final_step == max(self.__statuses, default=-1)
		return (final, idle)
	# @used-by :meth:`TurnScanner.scan()`
	def __load_context(self) -> None:
		if not re.fullmatch('[a-f0-9-]{36}', self.__conversation_id):
			raise ValueError('Exact native Antigravity conversation UUID required')
		with dfh_open_readonly_sqlite(self.__paths['conversations_db'], row_factory=sqlite3.Row) as conn:
			summary = conn.execute('SELECT * FROM conversation_summaries WHERE conversation_id=?', (self.__conversation_id,)).fetchone()
			self.__summary = dict(summary) if None is not summary else None
		if None is self.__summary or 'parent_conversation_id' not in self.__summary:
			raise ValueError('Native Antigravity primary/child identity is unavailable')
		read_fn = self.__ops.get('read_jsonl_objects') or dfh_read_jsonl_objects
		self.__path = dfh_transcript_path(self.__paths['brain_dir'], self.__conversation_id)
		self.__rows = read_fn(self.__path, partial_error='Native Antigravity trace has a partial record; retry after flush')
		self.__row_by_step = {row.get('step_index'): row for row in self.__rows if isinstance(row, dict) and isinstance(row.get('step_index'), int)}
		raw_inputs = dfh_native_inputs(self.__backend, self.__conversation_id, paths=self.__paths, include_meta=True)
		self.__inputs = [(index, text) for index, text, _ in raw_inputs]
		self.__expected_job_id = dfh_completion_project_id(self.__root)
		ws_contexts = dfh_workspace_context(self.__backend, self.__conversation_id, paths=self.__paths, settings_fn=self.__ops.get('settings'))
		self.__workspace_root = ws_contexts[-1][1] if ws_contexts and ws_contexts[-1][1] else None
		selected, self.__scope_active, self.__scope_binding = dfh_request_scope(self.__root, self.__conversation_id, self.__backend, inputs=raw_inputs, identifier=self.__expected_job_id, paths=self.__paths, contexts=ws_contexts, settings_fn=self.__ops.get('settings'))
		self.__requests = {index: {'id': f'{self.__conversation_id}-{index}', 'text': text, 'native_step': index, 'project_binding': binding} for index, text, binding in selected}
		self.__load_statuses_and_journal()
	# @used-by :meth:`TurnScanner.__load_context()`
	def __load_statuses_and_journal(self) -> None:
		with dfh_open_readonly_sqlite(dfh_conversation_db_path(self.__backend, self.__conversation_id, paths=self.__paths)) as conn:
			self.__statuses = {index: (kind, status) for index, kind, status in conn.execute('SELECT idx,step_type,status FROM steps')}
		self.__jdir = dfh_resolve_journal_dir(self.__root_p)
		self.__journal_groups = dfh_completed_request_group_index(self.__jdir)
		self.__boundaries = sorted((index for index, _ in self.__inputs))
	# @used-by :meth:`TurnScanner.__group_segments()`
	def __merge_pending(self, items: list[dict]) -> dict[str, Any]:
		return dfh_merge_segment_metadata(dfh_merge_turn_accumulators(items, allow_step_output_recovery=True), items)
	# @used-by :meth:`TurnScanner.__resolve_subagent_child()`
	def __query_child_summary(self, child_cid: str, expected_parent: str) -> tuple[bool, str | None, list[str]]:
		child_agent_name, db_grandchildren, parent_mismatch = (None, [], False)
		try:
			with dfh_open_readonly_sqlite(self.__paths['conversations_db']) as c_conn:
				c_row = c_conn.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (child_cid,)).fetchone()
				if None is not c_row:
					if not c_row[0] or c_row[0] != expected_parent:
						parent_mismatch = True
					else:
						child_agent_name = c_row[1]
				if not parent_mismatch:
					db_grandchildren = [row[0] for row in c_conn.execute('SELECT conversation_id FROM conversation_summaries WHERE parent_conversation_id=?', (child_cid,)).fetchall() if row and row[0]]
		except Exception:
			pass
		return (parent_mismatch, child_agent_name, db_grandchildren)
	# @used-by :meth:`TurnScanner.__record_tool_calls()`
	def __record_one_tool_call(self, step_idx: int, call: dict, matched: list[str], seg: dict) -> None:
		cname = call.get('name', '')
		raw_args = call.get('args', {})
		args = dfh_parse_tool_args(raw_args)
		args_text = json.dumps(args, ensure_ascii=False) if args or isinstance(raw_args, dict) else str(raw_args)
		self.__update_bg_tasks(cname, args, matched, seg)
		cev = dfh_record_normalized_tool_effects(self.__root_p, step_idx, cname, raw_args, args_text, seg, track_turn_steps=True, cmd_outputs=matched, shell_violations_fn=self.__ops.get('shell_violations_fn'))
		if cev and cev.get('outcome', {}).get('background_task_id') and 'bg_tdd_index' in seg:
			seg['bg_tdd_index'][cev['outcome']['background_task_id']] = cev
	# @used-by :meth:`TurnScanner.__collect_outputs()`
	def __record_step_output_reads(self, c_str: str, step_idx, file_reads) -> None:
		if None is not file_reads and None is not step_idx:
			for m_step_out in re.finditer('file:///+([A-Za-z]:/[^\\s"\\\'<>`]+?/\\.system_generated/steps/\\d+/output\\.txt)', c_str):
				file_reads.append((step_idx, m_step_out.group(1).replace('\\', '/')))
	# @used-by :meth:`TurnScanner.__resolve_subagent_child()`
	def __record_subagent_calls(self, child_cid: str, c_rows: list, anchor_step: int, seg: dict) -> tuple:
		sub_bg: dict[str, dict] = {}
		for c_pos, c_ev in enumerate(c_rows):
			if isinstance(c_ev, dict):
				self.__visit_subagent_row(child_cid, c_rows, c_pos, c_ev, anchor_step, seg, sub_bg)
		return ()
	# @used-by :meth:`TurnScanner.__visit_subagent_row()`
	def __record_subagent_tool_calls(self, child_cid: str, c_rows: list, c_pos: int, c_calls: list[dict], anchor_step: int, seg: dict, sub_bg: dict[str, dict]) -> None:
		c_outs = self.__collect_outputs(c_rows, c_pos)
		for act_item in extract_issue_actions_from_outputs(c_outs):
			seg['issue_actions'].append({**act_item, 'step': anchor_step, 'subagent_id': child_cid})
		for c_idx, c_call in enumerate(c_calls):
			matched = [c_outs[c_idx]] if c_idx < len(c_outs) else c_outs
			cev = dfh_record_normalized_tool_effects(self.__root_p, anchor_step, c_call.get('name', ''), c_call.get('args', {}), '', seg, extra_violation={'subagent_id': child_cid}, cmd_outputs=matched, sub_step=c_pos, shell_violations_fn=self.__ops.get('shell_violations_fn'))
			if cev and cev.get('outcome', {}).get('background_task_id'):
				sub_bg[cev['outcome']['background_task_id']] = cev
	# @used-by :meth:`TurnScanner.__scan_segment_row()`
	def __record_tool_calls(self, step_idx: int, calls: list[dict], outputs: list[str], seg: dict) -> None:
		seg['tool_steps'].append(step_idx)
		# 2026-11-27 "Recognize passing worktree-land full test runs in TDD-FULL-GATE": https://github.com/dmitry-ai/harness/issues/398
		seg['tool_records'].append({'step': step_idx, 'tools': [c.get('name', '') for c in calls], 'outputs': [o[:4000] for o in outputs]})
		for act_item in extract_issue_actions_from_outputs(outputs):
			seg['issue_actions'].append({**act_item, 'step': step_idx})
		for c_idx, call in enumerate(calls):
			matched = [outputs[c_idx]] if c_idx < len(outputs) else outputs
			self.__record_one_tool_call(step_idx, call, matched, seg)
	# @used-by :meth:`TurnScanner.__finalize_segment()`
	def __resolve_segment_completion(self, start: int, end, last: dict, seg: dict) -> tuple[bool, str | None]:
		final, idle = self.__is_final_idle(start, last)
		req_id = f'{self.__conversation_id}-{start}'
		j_entry = self.__journal_groups.get(req_id)
		has_single = None is not j_entry and 1 == len(j_entry[0].get('request_ids', []))
		pending_work = seg['completed_subagents'] < seg['spawned_subagents'] or bool(seg.get('active_bg_tasks')) or dfh_is_waiting_status_stub(str(last.get('content') or ''))
		if None is not end and (not seg['answer_prepared_in_segment']) and (not has_single) and pending_work:
			r = (False, None)
		elif None is not j_entry and ((not final) or 1 < len(j_entry[0].get('request_ids', []))):
			completed = req_id == j_entry[0]['request_ids'][-1] and (None is not end or idle)
			_, res_dir = dfh_journal_pair_dirs(self.__jdir)
			res_p = dfh_step_file(res_dir, j_entry[1], directory=self.__jdir)
			r = (completed, res_p.read_bytes().decode('utf-8') if completed and res_p.is_file() else None)
		else:
			completed = bool(final and (None is not end or idle))
			r = (completed, last.get('content') if completed else None)
		return r
	# @used-by :meth:`TurnScanner.__collect_subagent_bfs()`
	def __resolve_subagent_child(self, child_cid: str, is_aa_hint: bool, expected_parent: str, anchor_step: int, seg: dict):
		r = None
		child_log = dfh_transcript_path(self.__paths['brain_dir'], child_cid)
		if child_log.is_file():
			parent_mismatch, child_agent_name, db_grandchildren = self.__query_child_summary(child_cid, expected_parent)
			if not parent_mismatch:
				read_fn = self.__ops.get('read_jsonl_objects') or dfh_read_jsonl_objects
				try:
					c_rows = read_fn(child_log)
					is_aa = 'self' == child_agent_name or (None is child_agent_name and bool(is_aa_hint))
					r = (c_rows, is_aa, db_grandchildren + dfh_extract_subagent_uuids(c_rows), lambda cid, rows: self.__record_subagent_calls(cid, rows, anchor_step, seg))
				except Exception:
					r = ([], False, (), None)
		return r
	# @used-by :meth:`TurnScanner.__group_segments()`
	def __scan_segment(self, position: int, start: int) -> dict[str, Any]:
		end = self.__boundaries[position + 1] if position + 1 < len(self.__boundaries) else None
		segment = [row for row in self.__rows if row.get('step_index', -1) > start and (None is end or row.get('step_index', -1) < end)]
		seg = dfh_init_turn_accumulator(extra={'issue_actions': [], 'spawned_subagents': 0, 'completed_subagents': 0, 'answer_prepared_in_segment': False, 'bg_tdd_index': {}, 'active_bg_tasks': set()})
		seg_models: list[str] = []
		for pos, row in enumerate(segment):
			if isinstance(row, dict):
				self.__scan_segment_row(segment, pos, row, seg, seg_models)
		return self.__finalize_segment(start, end, segment, seg, self.__collect_subagent_bfs(position, segment, seg), seg_models)
	# @used-by :meth:`TurnScanner.__scan_segment()`
	def __scan_segment_row(self, segment: list, pos: int, row: dict, seg: dict, seg_models: list[str]) -> None:
		step_idx = row.get('step_index')
		if 'PLANNER_RESPONSE' == row.get('type') and isinstance(row.get('model'), str) and row['model'].strip():
			seg_models.append(row['model'].strip())
		if 'CHECKPOINT' == row.get('type') and isinstance(step_idx, int):
			seg['checkpoint_steps'].append(step_idx)
		if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and row.get('content'):
			self.__handle_system_message(str(row.get('content')), step_idx, seg)
		calls = [c for c in row.get('tool_calls') or () if isinstance(c, dict)]
		if calls and isinstance(step_idx, int):
			self.__record_tool_calls(step_idx, calls, self.__collect_outputs(segment, pos, step_idx=step_idx, file_reads=seg['file_reads']), seg)
	# @used-by :meth:`TurnScanner.__record_one_tool_call()`
	def __update_bg_tasks(self, cname: str, args: dict, matched: list[str], seg: dict) -> None:
		from agent_tools.tdd.outcomes import extract_bg_task_ids
		if 'run_command' == cname and 'active_bg_tasks' in seg:
			for out_s in matched:
				seg['active_bg_tasks'].update(extract_bg_task_ids(out_s))
		elif 'manage_task' == cname and 'kill' == str(args.get('Action') or '').strip().lower() and 'active_bg_tasks' in seg:
			kill_tid = str(args.get('TaskId') or '').strip()
			if kill_tid:
				seg['active_bg_tasks'].discard(kill_tid)
	# @used-by :meth:`TurnScanner.__record_subagent_calls()`
	def __visit_subagent_row(self, child_cid: str, c_rows: list, c_pos: int, c_ev: dict, anchor_step: int, seg: dict, sub_bg: dict[str, dict]) -> None:
		from agent_tools.tdd_gate import _BG_TASK_FINISHED_RE, parse_command_outcome
		if c_ev.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and c_ev.get('content'):
			m_fin = _BG_TASK_FINISHED_RE.search(str(c_ev.get('content')))
			if m_fin and m_fin.group(1).strip() in sub_bg:
				sub_bg[m_fin.group(1).strip()]['outcome'] = parse_command_outcome(m_fin.group(2))
		c_calls = [c for c in c_ev.get('tool_calls') or () if isinstance(c, dict)]
		if c_calls:
			self.__record_subagent_tool_calls(child_cid, c_rows, c_pos, c_calls, anchor_step, seg, sub_bg)
	# @used-by :func:`Df.Harness.lib.completion_core._scan_native_for_platform()`
	# @used-by :func:`Df.Harness.lib.hook_pre_invocation_ops._diagnose_no_active_turn()`
	# @used-by :func:`agent_tools.platforms.antigravity.native_answers()`
	# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_platform_turn_scanner_and_ag_tail()`
	# @used-by :meth:`test_tdd_worktree_land_green.TddWorktreeLandGreenTests.test_antigravity_scanners_forward_untruncated_output_to_tdd_while_capping_tool_records()`
	def scan(self) -> dict[str, Any]:
		self.__load_context()
		grouped = self.__group_segments()
		active = grouped[-1] if grouped and (not grouped[-1]['completed']) else None
		out: dict[str, Any] = {'platform': 'antigravity', 'conversation_id': self.__conversation_id, 'native_backend': str(self.__backend), 'source_file': str(self.__path), 'primary': not bool(self.__summary['parent_conversation_id']), 'turns': grouped, 'active_turn_id': active['turn_id'] if active else None, 'binding_diagnostic': {'active': self.__scope_active, 'binding': self.__scope_binding, 'expected_root': str(self.__root_p), 'expected_job_id': self.__expected_job_id}}
		if self.__paths.get('instance'):
			out['instance'] = self.__paths['instance']
		if self.__workspace_root:
			out['workspace_root'] = self.__workspace_root
		return out
