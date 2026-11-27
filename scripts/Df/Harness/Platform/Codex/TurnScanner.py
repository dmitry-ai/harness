# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.codex_trace import SUBAGENT_PARENT_CACHE, dfh_actual_user_input, dfh_codex_paths, dfh_codex_request_scope, dfh_codex_trace, dfh_extract_codex_spawn_output_uuids, dfh_extract_codex_target_subagents, dfh_state_db_files
from Df.Harness.lib.request_binding import dfh_completion_project_id
from Df.Harness.lib.trace_common import dfh_local_uri_to_path, dfh_open_readonly_sqlite, dfh_parse_tool_args
from Df.Harness.lib.trace_effects import dfh_collect_subagent_bfs, dfh_init_turn_accumulator, dfh_record_normalized_tool_effects, dfh_summarize_turn_activity
from agent_tools.shell_audit import extract_issue_actions_from_outputs
import json
import re
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class TurnScanner:
	# @used-by :func:`Df.Harness.lib.completion_core._scan_native_for_platform()`
	# @used-by :func:`agent_tools.platforms.codex.native_answers()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_codex_and_ag_scanners_and_tool_trace()`
	def __init__(self, root, conversation_id: str, *, backend=None, instance=None, _ops: dict[str, Any] | None=None) -> None:
		self.__ops = _ops or {}
		self.__root = root
		self.__root_p = Path(root).resolve()
		self.__conversation_id = conversation_id
		self.__paths = dfh_codex_paths(backend, profile=instance, conversation_id=conversation_id, platform_settings_fn=self.__ops.get('platform_settings'), settings_fn=self.__ops.get('settings'))
		self.__home = self.__paths['home']
		self.__init_scan_state()
	# @used-by :meth:`TurnScanner.__collect_subagent_bfs()`
	def __collect_bfs_seeds(self, is_last_turn: bool, unclaimed: list[str], acc: dict) -> list[tuple]:
		seeds = [(cid, False, self.__conversation_id) for cid in unclaimed] if is_last_turn else []
		for rec in acc['tool_records']:
			seeds.extend(((t_uid, False, self.__conversation_id) for t_uid in rec.get('target_subagents', []) if t_uid != self.__conversation_id))
			if any((str(t).endswith(('spawn_agent', 'invoke_subagent')) for t in rec.get('tools', []))):
				seeds.extend(((m_uuid, False, self.__conversation_id) for out in rec.get('outputs', []) for m_uuid in dfh_extract_codex_spawn_output_uuids(str(out)) if m_uuid != self.__conversation_id))
		return seeds
	# @used-by :meth:`TurnScanner.__finalize_turn()`
	def __collect_subagent_bfs(self, t_idx: int, turn: dict, acc: dict) -> None:
		visited_sub_ids = {self.__conversation_id}
		is_last_turn = t_idx == len(self.__turn_entries) - 1
		if not self.__child and (acc['subagent_steps'] or is_last_turn):
			self.__index_profile_subagents()
			unclaimed = [cid for cid in self.__child_parent_map.get(self.__conversation_id, []) if cid not in self.__completed_turn_sub_ids]
			if acc['subagent_steps'] or (is_last_turn and unclaimed):
				seeds = self.__collect_bfs_seeds(is_last_turn, unclaimed, acc)
				anchor = acc['subagent_steps'][-1] if acc['subagent_steps'] else (acc['tool_steps'][-1] if acc['tool_steps'] else turn['start_step'])
				visited_sub_ids = dfh_collect_subagent_bfs(self.__conversation_id, self.__root_p, seeds, lambda sid, depth, hint, parent: self.__resolve_subagent_child(sid, parent, anchor, turn, acc), acc['aa_partial_read_violations'])
		self.__completed_turn_sub_ids.update(visited_sub_ids - {self.__conversation_id})
	# @used-by :meth:`TurnScanner.__scan_active_row()`
	def __complete_turn(self, index: int, ptype: str, payload: dict, ts: str | None, current: dict) -> None:
		current['completion_step'], current['aborted'] = (index, 'turn_aborted' == ptype)
		if not current['aborted']:
			native_final = payload.get('last_agent_message')
			if None is not current['response'] and isinstance(native_final, str) and native_final != current['response']:
				raise ValueError('Native Codex final message and completion event disagree')
			current['completed'] = bool(current['response'] and None is not current['final_step'])
			if current['completed'] and None is current['response_timestamp'] and ts:
				current['response_timestamp'] = ts
	# @used-by :meth:`TurnScanner.scan()`
	def __finalize_turn(self, t_idx: int, turn: dict, acc: dict) -> None:
		turn['owned'] = bool(turn['requests']) and len(turn['requests']) == len(acc['all_request_steps'])
		turn['issue_actions'] = [{**act, 'step': rec['step']} for rec in acc['tool_records'] for act in extract_issue_actions_from_outputs(rec.get('outputs', []))]
		self.__collect_subagent_bfs(t_idx, turn, acc)
		for rec in acc['tool_records']:
			rec.pop('target_subagents', None)
		turn['compaction'], turn['delegation'] = dfh_summarize_turn_activity(acc['checkpoint_steps'], acc['tool_steps'], acc['subagent_steps'], acc['aa_subagent_steps'], acc['af_subagent_steps'], acc['kb_persistence_steps'], acc['transcript_read_steps'], acc['tool_records'], acc['file_reads'], acc['file_writes'], svc_steps=acc['completion_service_steps'], aa_part_errs=acc['aa_partial_read_violations'])
	# @used-by :meth:`TurnScanner.__handle_message_row()`
	def __handle_assistant_message(self, index: int, payload: dict, ts: str | None, current: dict) -> None:
		is_final = 'final_answer' == payload.get('phase') or 'final' == payload.get('channel')
		if is_final and payload.get('status') in (None, 'completed'):
			text = ''.join((p.get('text', '') for p in payload.get('content', []) if 'output_text' == p.get('type')))
			if text.strip():
				current['response'], current['final_step'] = (text, index)
				if ts:
					current['response_timestamp'] = ts
	# @used-by :meth:`TurnScanner.__scan_active_row()`
	def __handle_message_row(self, index: int, payload: dict, ts: str | None, current: dict, acc: dict) -> None:
		role = payload.get('role')
		if 'assistant' == role:
			self.__handle_assistant_message(index, payload, ts, current)
		elif 'user' == role:
			self.__handle_user_message(index, payload, ts, current, acc)
	# @used-by :meth:`TurnScanner.__scan_active_row()`
	def __handle_output_row(self, payload: dict, acc: dict) -> None:
		call_id = payload.get('call_id')
		rec = acc['pending_calls'].get(call_id)
		if None is not payload.get('output'):
			out = payload.get('output')
			out_full = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
			if None is not rec:
				rec['outputs'].append(out_full[:4000])
			if call_id in acc['pending_tdd_cmds']:
				from agent_tools.tdd_gate import parse_command_outcome
				acc['pending_tdd_cmds'][call_id]['outcome'] = parse_command_outcome(out_full)
			if call_id in acc['pending_issue_cmds']:
				from agent_tools.issue_first_gate import build_issue_action_events
				c_step, c_cmd = acc['pending_issue_cmds'].pop(call_id)
				acc['issue_first_events'].extend(build_issue_action_events(c_step, c_cmd, [out_full]))
	# @used-by :meth:`TurnScanner.__visit_subagent_rows()`
	def __handle_subagent_call(self, sub_id: str, anchor, s_pos: int, s_pay: dict, acc: dict, sub_spawn_ids: set, sub_pending_tdd: dict, sub_pending_issue: dict, r: list) -> None:
		s_name = s_pay.get('name', '')
		s_args_in = s_pay.get('arguments', s_pay.get('input', {}))
		s_raw_in = s_pay.get('input', s_pay.get('arguments', ''))
		s_raw = s_raw_in if isinstance(s_raw_in, str) else json.dumps(s_raw_in, ensure_ascii=False)
		if s_name.endswith(('spawn_agent', 'invoke_subagent')) and s_pay.get('call_id'):
			sub_spawn_ids.add(s_pay['call_id'])
		elif s_name.endswith(('send_input', 'send_message', 'wait', 'wait_agent')):
			r.extend(dfh_extract_codex_target_subagents(s_args_in))
		cev = dfh_record_normalized_tool_effects(self.__root_p, anchor, s_name, s_args_in, s_raw, acc, extra_violation={'subagent_id': sub_id}, sub_step=s_pos, shell_violations_fn=self.__ops.get('shell_violations_fn'))
		if cev and s_pay.get('call_id'):
			sub_pending_tdd[s_pay['call_id']] = cev
		if s_pay.get('call_id') and ('exec' == s_name or s_name.endswith(('exec_command', 'run_command'))):
			from agent_tools.issue_first_gate import is_df_github_issue_command
			sp_args = dfh_parse_tool_args(s_args_in)
			seff_cmd = str(sp_args.get('CommandLine') or sp_args.get('cmd') or sp_args.get('command') or s_raw)
			if is_df_github_issue_command(seff_cmd):
				sub_pending_issue[s_pay['call_id']] = (s_pos, seff_cmd)
	# @used-by :meth:`TurnScanner.__visit_subagent_rows()`
	def __handle_subagent_output(self, anchor, s_pay: dict, acc: dict, sub_outputs: list, sub_spawn_ids: set, sub_pending_tdd: dict, sub_pending_issue: dict, r: list) -> None:
		out = s_pay.get('output')
		out_full = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
		out_s = out_full[:4000]
		sub_outputs.append(out_s)
		s_cid = s_pay.get('call_id')
		if s_cid in sub_spawn_ids:
			r.extend(dfh_extract_codex_spawn_output_uuids(out_s))
		if s_cid in sub_pending_tdd:
			from agent_tools.tdd_gate import parse_command_outcome
			sub_pending_tdd[s_cid]['outcome'] = parse_command_outcome(out_full)
		if s_cid in sub_pending_issue:
			from agent_tools.issue_first_gate import build_issue_action_events
			c_sub, c_cmd = sub_pending_issue.pop(s_cid)
			acc['issue_first_events'].extend(build_issue_action_events(anchor, c_cmd, [out_full], sub_step=c_sub))
	# @used-by :meth:`TurnScanner.__scan_active_row()`
	def __handle_tool_call_row(self, index: int, payload: dict, acc: dict) -> None:
		name = payload.get('name', '')
		raw_args = payload.get('arguments', payload.get('input', {}))
		raw_in = payload.get('input', payload.get('arguments', ''))
		raw_cmd = raw_in if isinstance(raw_in, str) else json.dumps(raw_in, ensure_ascii=False)
		acc['tool_steps'].append(index)
		rec = {'step': index, 'tools': [name], 'outputs': [], 'target_subagents': dfh_extract_codex_target_subagents(raw_args) if name.endswith(('send_input', 'send_message', 'wait', 'wait_agent')) else []}
		acc['tool_records'].append(rec)
		if payload.get('call_id'):
			acc['pending_calls'][payload['call_id']] = rec
		cev = dfh_record_normalized_tool_effects(self.__root_p, index, name, raw_args, raw_cmd, acc, extra_violation={'call_id': payload.get('call_id')}, track_turn_steps=True, transcript_tokens=(str(self.__path.name),), shell_violations_fn=self.__ops.get('shell_violations_fn'))
		if cev and payload.get('call_id'):
			acc['pending_tdd_cmds'][payload['call_id']] = cev
		if payload.get('call_id') and ('exec' == name or name.endswith(('exec_command', 'run_command'))):
			from agent_tools.issue_first_gate import is_df_github_issue_command
			p_args = dfh_parse_tool_args(raw_args)
			eff_cmd = str(p_args.get('CommandLine') or p_args.get('cmd') or p_args.get('command') or raw_cmd)
			if is_df_github_issue_command(eff_cmd):
				acc['pending_issue_cmds'][payload['call_id']] = (index, eff_cmd)
	# @used-by :meth:`TurnScanner.__scan_primary_row()`
	def __handle_turn_context(self, payload: dict, state: dict) -> None:
		m_val = payload.get('model') if isinstance(payload.get('model'), str) and payload['model'].strip() else None
		e_val = payload.get('effort') if isinstance(payload.get('effort'), str) and payload['effort'].strip() else None
		if m_val:
			state['model'] = m_val
		if e_val:
			state['effort'] = e_val
		cur = state['current']
		if None is not cur and payload.get('turn_id') in (None, cur['turn_id']):
			if m_val:
				cur['model'] = m_val
			if e_val:
				cur['effort'] = e_val
	# @used-by :meth:`TurnScanner.__handle_message_row()`
	def __handle_user_message(self, index: int, payload: dict, ts: str | None, current: dict, acc: dict) -> None:
		text = ''.join((p.get('text', '') for p in payload.get('content', []) if p.get('type') in ('input_text', 'output_text')))
		if dfh_actual_user_input(text, payload):
			acc['all_request_steps'].append(index)
			if None is current['request_timestamp'] and ts:
				current['request_timestamp'] = ts
			if index in self.__requests:
				current['requests'].append(self.__requests[index])
	# @used-by :meth:`TurnScanner.__index_profile_subagents()`
	def __index_db_threads(self, db_file: Path) -> None:
		try:
			with dfh_open_readonly_sqlite(db_file, row_factory=sqlite3.Row) as conn:
				t_rows = conn.execute('SELECT id, rollout_path FROM threads').fetchall()
		except sqlite3.Error:
			t_rows = []
		for tr in t_rows:
			tid, r_path = (tr['id'], tr['rollout_path'])
			if not tid or tid == self.__conversation_id or (not r_path):
				continue
			p_tid = self.__read_rollout_parent(dfh_local_uri_to_path(r_path))
			if None is not p_tid:
				self.__thread_parent_map[tid] = p_tid
				if p_tid:
					parent_children = self.__child_parent_map.setdefault(p_tid, [])
					if tid not in parent_children:
						parent_children.append(tid)
	# @used-by :meth:`TurnScanner.__collect_subagent_bfs()`
	def __index_profile_subagents(self) -> None:
		if not self.__indexed_subagents:
			self.__indexed_subagents = True
			if 4096 < len(SUBAGENT_PARENT_CACHE):
				SUBAGENT_PARENT_CACHE.clear()
			for db_file in dfh_state_db_files(self.__paths):
				self.__index_db_threads(db_file)
	# @used-by :meth:`TurnScanner.__init__()`
	def __init_scan_state(self) -> None:
		self.__path: Any = None
		self.__rows: list = []
		self.__child = False
		self.__requests: dict = {}
		self.__turn_entries: list = []
		self.__current_turn: dict | None = None
		self.__child_parent_map: dict[str, list[str]] = {}
		self.__thread_parent_map: dict[str, str] = {}
		self.__indexed_subagents = False
		self.__completed_turn_sub_ids: set[str] = set()
		self.__scope_active = False
		self.__scope_binding = None
		self.__expected_job_id: str | None = None
	# @used-by :meth:`TurnScanner.scan()`
	def __load_context(self) -> None:
		_, self.__path, _, self.__rows = dfh_codex_trace(self.__home, self.__conversation_id, paths=self.__paths, platform_settings_fn=self.__ops.get('platform_settings'), settings_fn=self.__ops.get('settings'))
		meta = self.__rows[0][1]['payload']
		self.__child = isinstance(meta.get('source'), dict) and bool(meta['source'].get('subagent'))
		self.__expected_job_id = dfh_completion_project_id(self.__root)
		selected, self.__scope_active, self.__scope_binding = dfh_codex_request_scope(self.__root, self.__rows, identifier=self.__expected_job_id)
		self.__requests = {index: {'id': f'codex:{self.__conversation_id}:{index}', 'text': text, 'native_step': index, 'project_binding': binding} for index, text, binding in selected}
	# @used-by :meth:`TurnScanner.__index_db_threads()`
	def __read_rollout_parent(self, rp: Path) -> str | None:
		r: str | None = None
		try:
			st = rp.stat()
			cache_key = str(rp)
			cached = SUBAGENT_PARENT_CACHE.get(cache_key)
			if None is not cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
				r = cached[2]
			else:
				with rp.open('r', encoding='utf-8', errors='replace') as fh:
					first_ln = fh.readline().strip()
				if first_ln:
					first_obj = json.loads(first_ln)
					src_meta = (first_obj.get('payload') or {}).get('source') if isinstance(first_obj, dict) and isinstance(first_obj.get('payload'), dict) else None
					raw_parent = ((src_meta.get('subagent') if isinstance(src_meta, dict) else None) or {}).get('thread_spawn', {}).get('parent_thread_id') if isinstance(src_meta, dict) and isinstance(src_meta.get('subagent'), dict) and isinstance(src_meta['subagent'].get('thread_spawn'), dict) else None
					r = raw_parent if isinstance(raw_parent, str) and raw_parent else ''
					SUBAGENT_PARENT_CACHE[cache_key] = (st.st_mtime_ns, st.st_size, r)
		except (OSError, ValueError, KeyError, TypeError, AttributeError):
			r = None
		return r
	# @used-by :meth:`TurnScanner.__collect_subagent_bfs()`
	def __resolve_subagent_child(self, sub_id: str, expected_parent: str, anchor, turn: dict, acc: dict):
		r = None
		if sub_id not in self.__thread_parent_map or (self.__thread_parent_map[sub_id] and self.__thread_parent_map[sub_id] == expected_parent):
			pre_children = self.__child_parent_map.get(sub_id, [])
			try:
				sub_db_row, _, _, sub_rows = dfh_codex_trace(self.__home, sub_id, paths=self.__paths, platform_settings_fn=self.__ops.get('platform_settings'), settings_fn=self.__ops.get('settings'))
				sub_agent_path = str((sub_db_row or {}).get('agent_path') or '')
				r = (sub_rows, not re.search('\\baf\\b', sub_agent_path, flags=re.I) and bool(acc['aa_subagent_steps'] or sub_agent_path), pre_children, lambda sid, rows: self.__visit_subagent_rows(sid, rows, anchor, turn, acc))
			except (ValueError, OSError):
				r = ([], False, pre_children, None)
		return r
	# @used-by :meth:`TurnScanner.__scan_primary_row()`
	def __scan_active_row(self, index: int, kind, ptype, payload: dict, ts: str | None, cur: dict, acc: dict) -> None:
		is_cp = kind in ('compacted', 'context_compacted', 'checkpoint') or (kind in ('event_msg', 'response_item') and ptype in ('context_compacted', 'compacted', 'checkpoint'))
		if is_cp:
			acc['checkpoint_steps'].append(index)
		elif 'response_item' == kind and ptype in ('function_call_output', 'custom_tool_call_output'):
			self.__handle_output_row(payload, acc)
		elif 'event_msg' == kind and ptype in ('task_complete', 'turn_aborted') and payload.get('turn_id') == cur['turn_id']:
			self.__complete_turn(index, ptype, payload, ts, cur)
		elif 'response_item' == kind and 'message' == ptype:
			self.__handle_message_row(index, payload, ts, cur, acc)
		elif 'response_item' == kind and ptype in ('function_call', 'custom_tool_call'):
			self.__handle_tool_call_row(index, payload, acc)
	# @used-by :meth:`TurnScanner.__scan_primary_turns()`
	def __scan_primary_row(self, index: int, item: dict, state: dict) -> None:
		payload = item.get('payload', {})
		kind, ptype = (item.get('type'), payload.get('type'))
		ts = item.get('timestamp') if isinstance(item.get('timestamp'), str) and item['timestamp'].strip() else None
		if 'turn_context' == kind and isinstance(payload, dict):
			self.__handle_turn_context(payload, state)
		elif 'event_msg' == kind and 'task_started' == ptype:
			self.__start_turn(index, payload, ts, state)
		elif None is not state['current']:
			self.__scan_active_row(index, kind, ptype, payload, ts, state['current'], state['acc'])
	# @used-by :meth:`TurnScanner.scan()`
	def __scan_primary_turns(self) -> None:
		state: dict[str, Any] = {'current': None, 'acc': None, 'model': None, 'effort': None}
		for index, item in self.__rows:
			self.__scan_primary_row(index, item, state)
		self.__current_turn = state['current']
	# @used-by :meth:`TurnScanner.__scan_primary_row()`
	def __start_turn(self, index: int, payload: dict, ts: str | None, state: dict) -> None:
		ident = payload.get('turn_id')
		if not isinstance(ident, str) or (not ident):
			raise ValueError('Native Codex task_started has no turn ID')
		cur = {'turn_id': ident, 'requests': [], 'completed': False, 'response': None, 'start_step': index, 'final_step': None, 'completion_step': None, 'aborted': False, 'request_timestamp': ts, 'response_timestamp': None, 'model': state['model'], 'effort': state['effort'], 'exec5_violations': [], 'http_fetch_violations': [], 'touched_files': [], 'issue_first_events': [], 'tdd_events': []}
		acc = dfh_init_turn_accumulator(extra={'all_request_steps': [], 'pending_calls': {}, 'pending_tdd_cmds': {}, 'pending_issue_cmds': {}, 'exec5_violations': cur['exec5_violations'], 'http_fetch_violations': cur['http_fetch_violations'], 'touched_files': cur['touched_files'], 'issue_first_events': cur['issue_first_events'], 'tdd_events': cur['tdd_events']})
		state['current'], state['acc'] = (cur, acc)
		self.__turn_entries.append((cur, acc))
	# @used-by :meth:`TurnScanner.__resolve_subagent_child()`
	def __visit_subagent_rows(self, sub_id: str, sub_rows: list, anchor, turn: dict, acc: dict) -> list[str]:
		r, sub_outputs, sub_spawn_ids = ([], [], set())
		sub_pending_tdd: dict[str, dict] = {}
		sub_pending_issue: dict[str, tuple[int, str]] = {}
		for s_pos, (_, s_item) in enumerate(sub_rows):
			s_kind, s_pay = (s_item.get('type'), s_item.get('payload', {}))
			if 'response_item' == s_kind and s_pay.get('type') in ('function_call_output', 'custom_tool_call_output') and None is not s_pay.get('output'):
				self.__handle_subagent_output(anchor, s_pay, acc, sub_outputs, sub_spawn_ids, sub_pending_tdd, sub_pending_issue, r)
			elif 'response_item' == s_kind and s_pay.get('type') in ('function_call', 'custom_tool_call'):
				self.__handle_subagent_call(sub_id, anchor, s_pos, s_pay, acc, sub_spawn_ids, sub_pending_tdd, sub_pending_issue, r)
		for act in extract_issue_actions_from_outputs(sub_outputs):
			act_with_sub = {**act, 'step': anchor, 'subagent_id': sub_id}
			if act_with_sub not in turn['issue_actions']:
				turn['issue_actions'].append(act_with_sub)
		return r
	# @used-by :func:`Df.Harness.lib.completion_core._scan_native_for_platform()`
	# @used-by :func:`agent_tools.platforms.codex.native_answers()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_codex_and_ag_scanners_and_tool_trace()`
	def scan(self) -> dict[str, Any]:
		self.__load_context()
		self.__scan_primary_turns()
		for t_idx, (turn, acc) in enumerate(self.__turn_entries):
			turn['turn_index'] = t_idx + 1
			self.__finalize_turn(t_idx, turn, acc)
		out: dict[str, Any] = {'platform': 'codex', 'conversation_id': self.__conversation_id, 'native_backend': str(self.__home or (self.__paths.get('sessions_dir') or '')), 'source_file': str(self.__path), 'primary': not self.__child, 'turns': [turn for turn, _ in self.__turn_entries], 'active_turn_id': self.__current_turn['turn_id'] if self.__current_turn and (not self.__current_turn['completion_step']) else None, 'binding_diagnostic': {'active': self.__scope_active, 'binding': self.__scope_binding, 'expected_root': str(self.__root_p), 'expected_job_id': self.__expected_job_id}}
		if self.__paths.get('instance'):
			out['instance'] = self.__paths['instance']
		return out
