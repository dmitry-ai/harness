# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from collections import Counter
import glob
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
from ..runtime import extract_platform_homes, platform_settings, profile_name, resolve_codex_home, resolve_codex_paths
from ..research import json_data
from ..shell_audit import extract_issue_actions_from_outputs
from ..storage import iter_embedded_json_objects
from .trace_common import UUID_PATTERN, build_native_review_proof, collect_prompt_bias_issues, collect_subagent_bfs, current_turn_requests, finalize_executor_checks, init_turn_accumulator, local_uri_to_path, make_tool_trace_event, open_readonly_sqlite, parse_tool_args, partial_candidate_read_issues as _partial_candidate_read_issues, persist_review_proof, prompt_bias_issues, record_normalized_tool_effects, require_turn_binding, reviewer_isolation_issues, summarize_token_records, summarize_turn_activity, verify_review_proof_core
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
# 2026-11-18
# "Fix runtime instance path derivation and store validation":
# https://github.com/dmitry-ai/harness/issues/89
# @used-by :func:`_trace()`
# @used-by :meth:`CodexTurnScanner._index_profile_subagents()`
def _state_db_files(paths_or_home):
	if isinstance(paths_or_home, dict):
		home = _local_path(paths_or_home['home']) if paths_or_home.get('home') else None
		glob_raw = paths_or_home.get('state_db_glob') or 'state_*.sqlite'
		if Path(glob_raw).is_absolute():
			return sorted((Path(p) for p in glob.glob(glob_raw, recursive=True) if Path(p).is_file()))
		if None is home:
			return []
		return sorted((Path(p) for p in glob.glob((home / glob_raw).as_posix(), recursive=True) if Path(p).is_file()))
	return sorted(_local_path(paths_or_home).glob('state_*.sqlite'))
# 2026-11-13
# "Extract CodexTurnScanner class from native_answers in platforms/codex.py with completion_service_steps parity and cached subagent indexing":
# https://github.com/dmitry-ai/harness/issues/61
class CodexTurnScanner:
	# @used-by :func:`native_answers()`
	def __init__(self, root, conversation_id, *, backend=None, instance=None):
		self.root = root
		self.root_p = Path(root).resolve()
		self.conversation_id = conversation_id
		self._instance = instance
		self.paths = _paths(backend, profile=instance, conversation_id=conversation_id)
		self.home = self.paths['home']
		self.path = None
		self.rows = []
		self.child = False
		self.requests = {}
		self.turn_entries = []
		self.current_turn = None
		self.child_parent_map: dict[str, list[str]] = {}
		self.thread_parent_map: dict[str, str] = {}
		self.indexed_subagents = False
		self.completed_turn_sub_ids: set[str] = set()
		# 2026-11-23
		# "Use native workspace priority and AST command parsing in request binding":
		# https://github.com/dmitry-ai/harness/issues/129
		self.scope_active = False
		self.scope_binding = None
		self.expected_job_id = None
	# 2026-11-13
	# "Unify cross-platform subagent BFS traversal, tool-call effect classifier, turn accumulator, and invoke_subagent parser in platforms/trace_common.py":
	# https://github.com/dmitry-ai/harness/issues/64
	# @used-by :meth:`CodexTurnScanner._finalize_turn()`
	def _collect_subagent_bfs(self, t_idx, turn, acc):
		visited_sub_ids = {self.conversation_id}
		is_last_turn = t_idx == len(self.turn_entries) - 1
		if not self.child and (acc['subagent_steps'] or is_last_turn):
			self._index_profile_subagents()
			unclaimed = [cid for cid in self.child_parent_map.get(self.conversation_id, []) if cid not in self.completed_turn_sub_ids]
			if acc['subagent_steps'] or (is_last_turn and unclaimed):
				seeds = [(cid, False, self.conversation_id) for cid in unclaimed] if is_last_turn else []
				for rec in acc['tool_records']:
					seeds.extend(((t_uid, False, self.conversation_id) for t_uid in rec.get('target_subagents', []) if t_uid != self.conversation_id))
					if any((str(t).endswith(('spawn_agent', 'invoke_subagent')) for t in rec.get('tools', []))):
						seeds.extend(((m_uuid, False, self.conversation_id) for out in rec.get('outputs', []) for m_uuid in _extract_codex_spawn_output_uuids(str(out)) if m_uuid != self.conversation_id))
				anchor = acc['subagent_steps'][-1] if acc['subagent_steps'] else (acc['tool_steps'][-1] if acc['tool_steps'] else turn['start_step'])
				visited_sub_ids = collect_subagent_bfs(self.conversation_id, self.root_p, seeds, lambda sid, depth, hint, parent: self._resolve_subagent_child(sid, parent, anchor, turn, acc), acc['aa_partial_read_violations'])
		self.completed_turn_sub_ids.update(visited_sub_ids - {self.conversation_id})
	# 2026-11-01
	# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
	# https://github.com/dmitry-ai/harness/issues/34
	# @used-by :meth:`CodexTurnScanner.scan()`
	def _finalize_turn(self, t_idx, turn, acc):
		turn['owned'] = bool(turn['requests']) and len(turn['requests']) == len(acc['all_request_steps'])
		# 2026-10-31
		# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
		# https://github.com/dmitry-ai/harness/issues/31
		# 2026-11-14
		# "Decompose git_gate.py into shell_audit.py, GitRepoGate, and single-pass pre-commit validation":
		# https://github.com/dmitry-ai/harness/issues/67
		# 2026-11-23
		# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
		# https://github.com/dmitry-ai/harness/issues/146
		turn['issue_actions'] = [{**act, 'step': rec['step']} for rec in acc['tool_records'] for act in extract_issue_actions_from_outputs(rec.get('outputs', []))]
		self._collect_subagent_bfs(t_idx, turn, acc)
		for rec in acc['tool_records']:
			rec.pop('target_subagents', None)
		turn['compaction'], turn['delegation'] = summarize_turn_activity(acc['checkpoint_steps'], acc['tool_steps'], acc['subagent_steps'], acc['aa_subagent_steps'], acc['af_subagent_steps'], acc['kb_persistence_steps'], acc['transcript_read_steps'], acc['tool_records'], acc['file_reads'], acc['file_writes'], svc_steps=acc['completion_service_steps'], aa_part_errs=acc['aa_partial_read_violations'])
	# 2026-11-07
	# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
	# https://github.com/dmitry-ai/harness/issues/48
	# @used-by :meth:`CodexTurnScanner._collect_subagent_bfs()`
	def _index_profile_subagents(self):
		if not self.indexed_subagents:
			self.indexed_subagents = True
			if 4096 < len(_SUBAGENT_PARENT_CACHE):
				_SUBAGENT_PARENT_CACHE.clear()
			for db_file in _state_db_files(self.paths):
				try:
					with open_readonly_sqlite(db_file, row_factory=sqlite3.Row) as conn:
						t_rows = conn.execute('SELECT id, rollout_path FROM threads').fetchall()
				except sqlite3.Error:
					continue
				for tr in t_rows:
					tid, r_path = (tr['id'], tr['rollout_path'])
					if not tid or tid == self.conversation_id or not r_path:
						continue
					try:
						rp = _local_path(r_path)
						st = rp.stat()
						cache_key = str(rp)
						cached = _SUBAGENT_PARENT_CACHE.get(cache_key)
						if None is not cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
							p_tid = cached[2]
						else:
							with rp.open('r', encoding='utf-8', errors='replace') as fh:
								first_ln = fh.readline().strip()
							if not first_ln:
								continue
							first_obj = json.loads(first_ln)
							src_meta = (first_obj.get('payload') or {}).get('source') if isinstance(first_obj, dict) and isinstance(first_obj.get('payload'), dict) else None
							raw_parent = ((src_meta.get('subagent') if isinstance(src_meta, dict) else None) or {}).get('thread_spawn', {}).get('parent_thread_id') if isinstance(src_meta, dict) and isinstance(src_meta.get('subagent'), dict) and isinstance(src_meta['subagent'].get('thread_spawn'), dict) else None
							p_tid = raw_parent if isinstance(raw_parent, str) and raw_parent else ''
							_SUBAGENT_PARENT_CACHE[cache_key] = (st.st_mtime_ns, st.st_size, p_tid)
						self.thread_parent_map[tid] = p_tid
						if p_tid:
							parent_children = self.child_parent_map.setdefault(p_tid, [])
							if tid not in parent_children:
								parent_children.append(tid)
					except (OSError, ValueError, KeyError, TypeError, AttributeError):
						continue
	# @used-by :meth:`CodexTurnScanner.scan()`
	def _load_context(self):
		from .request_binding import completion_project_id
		_, self.path, _, self.rows = _trace(self.home, self.conversation_id, paths=self.paths)
		meta = self.rows[0][1]['payload']
		self.child = isinstance(meta.get('source'), dict) and bool(meta['source'].get('subagent'))
		self.expected_job_id = completion_project_id(self.root)
		selected, self.scope_active, self.scope_binding = _request_scope(self.root, self.rows, identifier=self.expected_job_id)
		self.requests = {index: {'id': f'codex:{self.conversation_id}:{index}', 'text': text, 'native_step': index, 'project_binding': binding} for index, text, binding in selected}
	# @used-by :meth:`CodexTurnScanner._collect_subagent_bfs()`
	def _resolve_subagent_child(self, sub_id, expected_parent, anchor, turn, acc):
		r = None
		if sub_id not in self.thread_parent_map or (self.thread_parent_map[sub_id] and self.thread_parent_map[sub_id] == expected_parent):
			pre_children = self.child_parent_map.get(sub_id, [])
			try:
				sub_db_row, _, _, sub_rows = _trace(self.home, sub_id, paths=self.paths)
				sub_agent_path = str((sub_db_row or {}).get('agent_path') or '')
				r = (sub_rows, not re.search('\\baf\\b', sub_agent_path, flags=re.I) and bool(acc['aa_subagent_steps'] or sub_agent_path), pre_children, lambda sid, rows: self._visit_subagent_rows(sid, rows, anchor, turn, acc))
			except (ValueError, OSError):
				r = ([], False, pre_children, None)
		return r
	# 2026-11-23
	# "Prepend JSON metadata headers to new journal responses":
	# https://github.com/dmitry-ai/harness/issues/151
	# @used-by :meth:`CodexTurnScanner.scan()`
	def _scan_primary_turns(self):
		current, acc = (None, None)
		last_ctx_model, last_ctx_effort = (None, None)
		for index, item in self.rows:
			payload = item.get('payload', {})
			kind, ptype = (item.get('type'), payload.get('type'))
			ts = item.get('timestamp') if isinstance(item.get('timestamp'), str) and item['timestamp'].strip() else None
			if 'turn_context' == kind and isinstance(payload, dict):
				m_val = payload.get('model') if isinstance(payload.get('model'), str) and payload['model'].strip() else None
				e_val = payload.get('effort') if isinstance(payload.get('effort'), str) and payload['effort'].strip() else None
				if m_val:
					last_ctx_model = m_val
				if e_val:
					last_ctx_effort = e_val
				if None is not current and payload.get('turn_id') in (None, current['turn_id']):
					if m_val:
						current['model'] = m_val
					if e_val:
						current['effort'] = e_val
				continue
			# 2026-10-30
			# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
			# https://github.com/dmitry-ai/harness/issues/21
			if None is not current and (kind in ('compacted', 'context_compacted', 'checkpoint') or (kind in ('event_msg', 'response_item') and ptype in ('context_compacted', 'compacted', 'checkpoint'))):
				acc['checkpoint_steps'].append(index)
			elif None is not current and 'response_item' == kind and ptype in ('function_call_output', 'custom_tool_call_output'):
				call_id = payload.get('call_id')
				rec = acc['pending_calls'].get(call_id)
				if None is not payload.get('output'):
					out = payload.get('output')
					out_full = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
					if None is not rec:
						rec['outputs'].append(out_full[:4000])
					# 2026-11-23
					# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
					# https://github.com/dmitry-ai/harness/issues/138
					if call_id in acc['pending_tdd_cmds']:
						from ..tdd_gate import parse_command_outcome
						acc['pending_tdd_cmds'][call_id]['outcome'] = parse_command_outcome(out_full)
					# 2026-11-23
					# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
					# https://github.com/dmitry-ai/harness/issues/146
					if call_id in acc['pending_issue_cmds']:
						from ..issue_first_gate import build_issue_action_events
						c_step, c_cmd = acc['pending_issue_cmds'].pop(call_id)
						acc['issue_first_events'].extend(build_issue_action_events(c_step, c_cmd, [out_full]))
			elif 'event_msg' == kind and 'task_started' == ptype:
				ident = payload.get('turn_id')
				if not isinstance(ident, str) or not ident:
					raise ValueError('Native Codex task_started has no turn ID')
				current = {'turn_id': ident, 'requests': [], 'completed': False, 'response': None, 'start_step': index, 'final_step': None, 'completion_step': None, 'aborted': False, 'request_timestamp': ts, 'response_timestamp': None, 'model': last_ctx_model, 'effort': last_ctx_effort, 'exec5_violations': [], 'http_fetch_violations': [], 'touched_files': [], 'issue_first_events': [], 'tdd_events': []}
				acc = init_turn_accumulator(extra={'all_request_steps': [], 'pending_calls': {}, 'pending_tdd_cmds': {}, 'pending_issue_cmds': {}, 'exec5_violations': current['exec5_violations'], 'http_fetch_violations': current['http_fetch_violations'], 'touched_files': current['touched_files'], 'issue_first_events': current['issue_first_events'], 'tdd_events': current['tdd_events']})
				self.turn_entries.append((current, acc))
			elif None is not current and 'event_msg' == kind and ptype in ('task_complete', 'turn_aborted') and payload.get('turn_id') == current['turn_id']:
				current['completion_step'], current['aborted'] = (index, 'turn_aborted' == ptype)
				if not current['aborted']:
					native_final = payload.get('last_agent_message')
					if None is not current['response'] and isinstance(native_final, str) and (native_final != current['response']):
						raise ValueError('Native Codex final message and completion event disagree')
					current['completed'] = bool(current['response'] and None is not current['final_step'])
					if current['completed'] and None is current['response_timestamp'] and ts:
						current['response_timestamp'] = ts
			elif None is not current and 'response_item' == kind and 'message' == ptype:
				if 'assistant' == payload.get('role') and ('final_answer' == payload.get('phase') or 'final' == payload.get('channel')) and payload.get('status') in (None, 'completed'):
					text = ''.join((p.get('text', '') for p in payload.get('content', []) if 'output_text' == p.get('type')))
					if text.strip():
						current['response'], current['final_step'] = (text, index)
						if ts:
							current['response_timestamp'] = ts
				elif 'user' == payload.get('role'):
					text = ''.join((p.get('text', '') for p in payload.get('content', []) if p.get('type') in ('input_text', 'output_text')))
					if _actual_user_input(text, payload):
						acc['all_request_steps'].append(index)
						if None is current['request_timestamp'] and ts:
							current['request_timestamp'] = ts
						if index in self.requests:
							current['requests'].append(self.requests[index])
			elif None is not current and 'response_item' == kind and ptype in ('function_call', 'custom_tool_call'):
				name = payload.get('name', '')
				raw_args = payload.get('arguments', payload.get('input', {}))
				raw_in = payload.get('input', payload.get('arguments', ''))
				raw_cmd = raw_in if isinstance(raw_in, str) else json.dumps(raw_in, ensure_ascii=False)
				acc['tool_steps'].append(index)
				rec = {'step': index, 'tools': [name], 'outputs': [], 'target_subagents': _extract_codex_target_subagents(raw_args) if name.endswith(('send_input', 'send_message', 'wait', 'wait_agent')) else []}
				acc['tool_records'].append(rec)
				if payload.get('call_id'):
					acc['pending_calls'][payload['call_id']] = rec
				cev = record_normalized_tool_effects(self.root_p, index, name, raw_args, raw_cmd, acc, extra_violation={'call_id': payload.get('call_id')}, track_turn_steps=True, transcript_tokens=(str(self.path.name),))
				if cev and payload.get('call_id'):
					acc['pending_tdd_cmds'][payload['call_id']] = cev
				if payload.get('call_id') and ('exec' == name or name.endswith(('exec_command', 'run_command'))):
					from ..issue_first_gate import is_df_github_issue_command
					p_args = parse_tool_args(raw_args)
					eff_cmd = str(p_args.get('CommandLine') or p_args.get('cmd') or p_args.get('command') or raw_cmd)
					if is_df_github_issue_command(eff_cmd):
						acc['pending_issue_cmds'][payload['call_id']] = (index, eff_cmd)
		self.current_turn = current
	# @used-by :meth:`CodexTurnScanner._resolve_subagent_child()`
	def _visit_subagent_rows(self, sub_id, sub_rows, anchor, turn, acc):
		r, sub_outputs, sub_spawn_call_ids = ([], [], set())
		sub_pending_tdd: dict[str, dict] = {}
		sub_pending_issue: dict[str, tuple[int, str]] = {}
		for s_pos, (_, s_item) in enumerate(sub_rows):
			s_kind, s_pay = (s_item.get('type'), s_item.get('payload', {}))
			if 'response_item' == s_kind and s_pay.get('type') in ('function_call_output', 'custom_tool_call_output') and None is not s_pay.get('output'):
				out = s_pay.get('output')
				out_full = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
				out_s = out_full[:4000]
				sub_outputs.append(out_s)
				s_cid = s_pay.get('call_id')
				if s_cid in sub_spawn_call_ids:
					r.extend(_extract_codex_spawn_output_uuids(out_s))
				# 2026-11-23
				# "Enforce cross-platform TDD lifecycle gate across turn completion and CLI":
				# https://github.com/dmitry-ai/harness/issues/138
				if s_cid in sub_pending_tdd:
					from ..tdd_gate import parse_command_outcome
					sub_pending_tdd[s_cid]['outcome'] = parse_command_outcome(out_full)
				# 2026-11-23
				# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
				# https://github.com/dmitry-ai/harness/issues/146
				if s_cid in sub_pending_issue:
					from ..issue_first_gate import build_issue_action_events
					c_sub, c_cmd = sub_pending_issue.pop(s_cid)
					acc['issue_first_events'].extend(build_issue_action_events(anchor, c_cmd, [out_full], sub_step=c_sub))
			elif 'response_item' == s_kind and s_pay.get('type') in ('function_call', 'custom_tool_call'):
				s_name = s_pay.get('name', '')
				s_args_in = s_pay.get('arguments', s_pay.get('input', {}))
				s_raw_in = s_pay.get('input', s_pay.get('arguments', ''))
				s_raw = s_raw_in if isinstance(s_raw_in, str) else json.dumps(s_raw_in, ensure_ascii=False)
				if s_name.endswith(('spawn_agent', 'invoke_subagent')) and s_pay.get('call_id'):
					sub_spawn_call_ids.add(s_pay['call_id'])
				elif s_name.endswith(('send_input', 'send_message', 'wait', 'wait_agent')):
					r.extend(_extract_codex_target_subagents(s_args_in))
				cev = record_normalized_tool_effects(self.root_p, anchor, s_name, s_args_in, s_raw, acc, extra_violation={'subagent_id': sub_id}, sub_step=s_pos)
				if cev and s_pay.get('call_id'):
					sub_pending_tdd[s_pay['call_id']] = cev
				if s_pay.get('call_id') and ('exec' == s_name or s_name.endswith(('exec_command', 'run_command'))):
					from ..issue_first_gate import is_df_github_issue_command
					sp_args = parse_tool_args(s_args_in)
					seff_cmd = str(sp_args.get('CommandLine') or sp_args.get('cmd') or sp_args.get('command') or s_raw)
					if is_df_github_issue_command(seff_cmd):
						sub_pending_issue[s_pay['call_id']] = (s_pos, seff_cmd)
		for act in extract_issue_actions_from_outputs(sub_outputs):
			act_with_sub = {**act, 'step': anchor, 'subagent_id': sub_id}
			if act_with_sub not in turn['issue_actions']:
				turn['issue_actions'].append(act_with_sub)
		return r
	# 2026-11-23
	# "Prepend JSON metadata headers to new journal responses":
	# https://github.com/dmitry-ai/harness/issues/151
	# @used-by :func:`native_answers()`
	def scan(self):
		self._load_context()
		self._scan_primary_turns()
		for t_idx, (turn, acc) in enumerate(self.turn_entries):
			turn['turn_index'] = t_idx + 1
			self._finalize_turn(t_idx, turn, acc)
		out = {'platform': 'codex', 'conversation_id': self.conversation_id, 'native_backend': str(self.home or (self.paths.get('sessions_dir') or '')), 'source_file': str(self.path), 'primary': not self.child, 'turns': [turn for turn, _ in self.turn_entries], 'active_turn_id': self.current_turn['turn_id'] if self.current_turn and (not self.current_turn['completion_step']) else None, 'binding_diagnostic': {'active': self.scope_active, 'binding': self.scope_binding, 'expected_root': str(self.root_p), 'expected_job_id': self.expected_job_id}}
		if self.paths.get('instance'):
			out['instance'] = self.paths['instance']
		return out
_SUBAGENT_PARENT_CACHE: dict[str, tuple[int, int, str]] = {}
# 2026-10-16
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-11-14
# "Consolidate token/stage summarize, native_review_proof, read-only SQLite, file:// helpers, and ProjectCleanupScanner across trace_common.py, antigravity.py, codex.py, metrics.py, and cleanup.py":
# https://github.com/dmitry-ai/harness/issues/75
# @used-by :func:`_request_scope()`
# @used-by :func:`_state_db_files()`
# @used-by :func:`_trace()`
# @used-by :meth:`CodexTurnScanner._index_profile_subagents()`
def _local_path(value):
	return local_uri_to_path(value)
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
# @used-by :func:`_home()`
# @used-by :func:`_trace()`
# @used-by :func:`native_executor_metadata()`
# @used-by :func:`native_requests()`
# @used-by :func:`native_review_proof()`
# @used-by :func:`native_tool_trace()`
# @used-by :func:`require_current_binding()`
# @used-by :meth:`CodexTurnScanner.__init__()`
def _paths(backend=None, profile=None, *, conversation_id=None):
	return resolve_codex_paths(backend, instance=profile, conversation_id=conversation_id, codex_cfg=platform_settings('codex'))
# @used-by unused
def _home(backend=None, profile=None, *, conversation_id=None):
	return _paths(backend, profile=profile, conversation_id=conversation_id)['home']
# 2026-10-15
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-18
# "Fix runtime instance path derivation and store validation":
# https://github.com/dmitry-ai/harness/issues/89
# @used-by :func:`native_executor_metadata()`
# @used-by :func:`native_requests()`
# @used-by :func:`native_review_proof()`
# @used-by :func:`native_tool_trace()`
# @used-by :func:`require_current_binding()`
# @used-by :meth:`CodexTurnScanner._load_context()`
# @used-by :meth:`CodexTurnScanner._resolve_subagent_child()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_existing_codex_review_model_gate_still_rejects_missing_actual_context()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_dynamic_folders_json_and_cleanup_without_homes()`
def _trace(home, conversation_id, *, paths=None):
	resolved = paths or _paths(home, conversation_id=conversation_id)
	home = _local_path(resolved['home']) if resolved.get('home') else None
	sessions_dir = _local_path(resolved['sessions_dir']) if resolved.get('sessions_dir') else None
	if not re.fullmatch('[a-f0-9-]{36}', conversation_id):
		raise ValueError('Exact native Codex thread UUID required')
	found = []
	for database in _state_db_files(resolved):
		with open_readonly_sqlite(database, row_factory=sqlite3.Row) as connection:
			row = connection.execute('SELECT * FROM threads WHERE id=?', (conversation_id,)).fetchone()
			if row:
				found.append(dict(row))
	if 1 != len(found):
		raise ValueError('Native Codex thread is missing or ambiguous in this profile')
	row = found[0]
	path = _local_path(row['rollout_path'])
	if sessions_dir and (not path.is_relative_to(sessions_dir)):
		raise ValueError('Codex trace is outside the selected profile sessions')
	raw = path.read_bytes()
	rows = []
	for index, line in enumerate(raw.splitlines()):
		if not line.strip():
			continue
		try:
			value = json.loads(line)
		except ValueError as exc:
			raise ValueError('Native Codex trace has a partial record; retry after it is flushed') from exc
		kind, payload = (value.get('type'), value.get('payload', {}))
		if kind in ('session_meta', 'turn_context') or ('response_item' == kind and 'reasoning' != payload.get('type')) or ('event_msg' == kind and payload.get('type') in ('task_started', 'task_complete', 'turn_aborted')):
			rows.append((index, value))
		# 2026-10-30
		# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
		# https://github.com/dmitry-ai/harness/issues/21
		elif kind in ('compacted', 'context_compacted', 'checkpoint') or ('event_msg' == kind and payload.get('type') in ('context_compacted', 'compacted', 'checkpoint')):
			rows.append((index, {'type': 'event_msg', 'payload': {'type': 'context_compacted', 'turn_id': payload.get('turn_id')}}))
	if not rows or 'session_meta' != rows[0][1].get('type') or rows[0][1]['payload'].get('id') != conversation_id:
		raise ValueError('Codex trace identity differs from native database')
	return (row, path, raw, rows)
# @used-by :func:`_request_scope()`
def _messages(rows, role):
	for index, item in rows:
		payload = item.get('payload', {})
		if 'response_item' == item.get('type') and 'message' == payload.get('type') and payload.get('role') == role:
			content = payload.get('content', [])
			if not isinstance(content, list):
				raise ValueError('Unsupported native Codex message content')
			texts = [part['text'] for part in content if part.get('type') in ('input_text', 'output_text') and isinstance(part.get('text'), str)]
			if texts:
				yield (index, ''.join(texts), payload)
# @used-by :func:`_request_scope()`
# @used-by :meth:`CodexTurnScanner._scan_primary_turns()`
def _actual_user_input(text, payload):
	kinds = payload.get('internal_chat_message_metadata_passthrough', {}).get('content_item_kinds', [])
	if 'user.text' in kinds:
		r = True
	elif any((kind in ('agents_md.instructions', 'environments.environment_context') for kind in kinds)):
		r = False
	elif kinds:
		r = not text.lstrip().startswith('<external_codex_apps_open_page>')
	else:
		r = not text.lstrip().startswith(('<environment_context>', '<external_codex_apps_open_page>')) and (not (text.lstrip().startswith('# AGENTS.md instructions') and '<INSTRUCTIONS>' in text))
	return r
# 2026-10-16
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# @used-by :func:`native_requests()`
# @used-by :func:`require_current_binding()`
# @used-by :meth:`CodexTurnScanner._load_context()`
def _request_scope(root, rows, *, until=None, identifier=None):
	from .request_binding import native_project_id, scoped_inputs
	job_id = identifier if None is not identifier else native_project_id(root)
	visible = [(index, item) for index, item in rows if None is until or index <= until]
	contexts = [(index, item['payload']) for index, item in visible if 'turn_context' == item.get('type') and item['payload'].get('cwd')]
	roots = []
	meta = visible[0][1]['payload'] if visible else {}
	if meta.get('cwd'):
		roots.append((visible[0][0], str(_local_path(meta['cwd'])), 'codex-session-cwd'))
	roots.extend(((index, str(_local_path(value['cwd'])), 'codex-turn-cwd') for index, value in contexts))
	inputs = []
	for index, text, payload in _messages(visible, 'user'):
		if _actual_user_input(text, payload):
			turn = payload.get('internal_chat_message_metadata_passthrough', {}).get('turn_id')
			matching = [(step, value) for step, value in contexts if turn and value.get('turn_id') == turn]
			if matching and (not any((step <= index for step, _ in matching))):
				roots.append((index, str(_local_path(matching[0][1]['cwd'])), 'codex-turn-cwd'))
			inputs.append((index, text))
	return scoped_inputs(root, job_id, inputs, roots, until=until)
# 2026-11-13
# "Deduplicate turn compaction/delegation reducers, shell/path tool normalization, and request/metadata wrappers across Antigravity and Codex adapters":
# https://github.com/dmitry-ai/harness/issues/58
# 2026-11-21
# "Remove text-based explicit-project-root override from request binding":
# https://github.com/dmitry-ai/harness/issues/112
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_changed_cwd_before_and_after_user_input_does_not_import_foreign_turn()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_injected_rules_and_environment_are_excluded_but_user_text_is_unchanged()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_missing_native_root_keeps_legacy_job_id_but_foreign_root_does_not()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_same_words_in_another_native_root_do_not_establish_ownership()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_codex_custom_system_paths_trace_requests_metadata_and_answers()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_exact_user_text_job_scope_and_cross_platform_request_merge()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_codex_requests_preserve_exact_text_without_analysis_project()`
def native_requests(root, conversation_id, *, backend=None, instance=None):
	paths = _paths(backend, profile=instance, conversation_id=conversation_id)
	home = paths['home']
	selected, _, _ = _request_scope(root, _trace(home, conversation_id, paths=paths)[3])
	return current_turn_requests(selected, conversation_id, 'codex-ui', 'Native Codex requests do not identify this project; open the session in the exact project directory or pass its /upwork-init URL', id_fmt='codex:{cid}:{idx}', extra={'native_profile_home': str(home)})
# 2026-11-13
# "Deduplicate turn compaction/delegation reducers, shell/path tool normalization, and request/metadata wrappers across Antigravity and Codex adapters":
# https://github.com/dmitry-ai/harness/issues/58
# 2026-11-23
# "Use native workspace priority and AST command parsing in request binding":
# https://github.com/dmitry-ai/harness/issues/129
# 2026-11-27 "Pass ARCH role through Codex native_review_proof binding": https://github.com/dmitry-ai/harness/issues/394
# @used-by :func:`native_review_proof()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_missing_native_root_keeps_legacy_job_id_but_foreign_root_does_not()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_same_words_in_another_native_root_do_not_establish_ownership()`
def require_current_binding(root, conversation_id, *, backend=None, instance=None, rows=None, until=None, role='AA'):
	from .request_binding import format_binding_diagnostic, review_project_id
	if None is rows:
		paths = _paths(backend, profile=instance, conversation_id=conversation_id)
		rows_val = _trace(paths['home'], conversation_id, paths=paths)[3]
	else:
		rows_val = rows
	job_id = review_project_id(root, role=role)
	selected, active, binding = _request_scope(root, rows_val, until=until, identifier=job_id)
	diag = format_binding_diagnostic(str(Path(root).resolve()), binding, expected_job_id=job_id)
	return require_turn_binding(selected, active, binding, f'Native Codex conversation is currently bound to another project or no exact project root ({diag})')
# 2026-11-07
# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
# https://github.com/dmitry-ai/harness/issues/48
# @used-by :func:`native_review_proof()`
# @used-by :meth:`CodexTurnScanner._scan_primary_turns()`
# @used-by :meth:`CodexTurnScanner._visit_subagent_rows()`
def _extract_codex_target_subagents(raw_args) -> list[str]:
	parsed_args = parse_tool_args(raw_args)
	candidates = [val.strip().lower() for key in ('id', 'Recipient', 'agent_id', 'subagent_id') for val in [parsed_args.get(key)] if isinstance(val, str)]
	ids_val = parsed_args.get('ids')
	if isinstance(ids_val, list):
		candidates.extend((item.strip().lower() for item in ids_val if isinstance(item, str)))
	return [u for u in dict.fromkeys(candidates) if re.fullmatch(UUID_PATTERN, u)]
# 2026-11-07
# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
# https://github.com/dmitry-ai/harness/issues/48
# @used-by :meth:`CodexTurnScanner._collect_subagent_bfs()`
# @used-by :meth:`CodexTurnScanner._visit_subagent_rows()`
def _extract_codex_spawn_output_uuids(out_text: str) -> list[str]:
	r = []
	if isinstance(out_text, str) and out_text.strip():
		try:
			parsed = json.loads(out_text)
		except ValueError:
			parsed = None
		if not isinstance(parsed, dict):
			r = [m.lower() for m in re.findall(f'\\b({UUID_PATTERN})\\b', out_text, flags=re.I)]
		else:
			matched = [u for u in dict.fromkeys((str(parsed[k]).strip().lower() for k in ('agent_id', 'conversationId', 'subagent_id', 'id', 'thread_id') if isinstance(parsed.get(k), str))) if re.fullmatch(UUID_PATTERN, u)]
			if matched or any((k in parsed for k in ('output', 'message', 'response', 'content'))):
				r = matched
			else:
				r = [m.lower() for m in re.findall(f'\\b({UUID_PATTERN})\\b', out_text, flags=re.I)]
	return r
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-11-13
# "Extract CodexTurnScanner class from native_answers in platforms/codex.py with completion_service_steps parity and cached subagent indexing":
# https://github.com/dmitry-ai/harness/issues/61
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_codex_custom_system_paths_trace_requests_metadata_and_answers()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_instance_flag_and_codex_auto_lookup_for_handoff_and_audit()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue48_codex_subagent_aggregation_ignores_read_output_uuids()`
# @used-by :meth:`test_turn_completion.CodexTurnScannerTests.test_service_steps_parity_subagent_cache_and_bfs_depth_cap()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_external_journal_cannot_bypass_the_current_client_document_gate()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_matching_native_request_ids_reuse_an_existing_record_answer_group()`
# @used-by :meth:`test_turn_completion.CompletionCase.tracked()`
def native_answers(root, conversation_id, *, backend=None, instance=None):
	return CodexTurnScanner(root, conversation_id, backend=backend, instance=instance).scan()
# @used-by :func:`_selection()`
# @used-by :func:`native_review_proof()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_existing_codex_review_model_gate_still_rejects_missing_actual_context()`
def _model(rows, before=None):
	contexts = [item['payload'] for index, item in rows if 'turn_context' == item.get('type') and (None is before or index <= before)]
	if not contexts or not contexts[-1].get('model') or (not contexts[-1].get('effort')):
		raise ValueError('Actual Codex model/effort is unavailable in native turn context')
	return {key: contexts[-1][key] for key in ('model', 'effort')}
# @used-by :func:`_selection()`
# @used-by :func:`native_executor_metadata()`
# @used-by :func:`native_review_proof()`
def _spawn(parent_rows, child_meta):
	path, created, matches = (child_meta['source']['subagent']['thread_spawn'].get('agent_path', ''), child_meta.get('timestamp'), [])
	for index, item in parent_rows:
		payload = item.get('payload', {})
		if 'response_item' == item.get('type') and payload.get('name', '').endswith('spawn_agent') and (not (created and item.get('timestamp') and (item['timestamp'] > created))):
			value = parse_tool_args(payload.get('arguments', payload.get('input', '{}')))
			if value.get('task_name') and path.endswith('/' + value['task_name']):
				matches.append((index, payload.get('call_id'), value))
	if not matches:
		raise ValueError('Native parent spawn call and its model selection are not established')
	return matches[-1]
# @used-by :func:`native_executor_metadata()`
# @used-by :func:`native_review_proof()`
def _selection(parent_rows, child_meta, invocation=None):
	index, call_id, arguments = invocation or _spawn(parent_rows, child_meta)
	parent = _model(parent_rows, before=index)
	model = arguments.get('model') or parent['model']
	effort = arguments.get('reasoning_effort') or arguments.get('model_reasoning_effort')
	if None is effort and model == parent['model']:
		effort = parent['effort']
	return {'model': model, 'effort': effort, 'invocation_call_id': call_id, 'task_name': arguments['task_name'], 'selection': 'explicit-parent-spawn' if arguments.get('model') or arguments.get('reasoning_effort') else 'inherit'}
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# 2026-11-13
# "Deduplicate turn compaction/delegation reducers, shell/path tool normalization, and request/metadata wrappers across Antigravity and Codex adapters":
# https://github.com/dmitry-ai/harness/issues/58
# @used-by :func:`native_review_proof()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_codex_aa_and_af_use_actual_spawn_selection()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_codex_explicit_requested_actual_model_mismatch_is_reported()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_codex_missing_native_context_is_explicitly_unverified()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_codex_primary_distinguishes_requested_unknown_from_observed()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_codex_custom_system_paths_trace_requests_metadata_and_answers()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_instance_flag_and_codex_auto_lookup_for_handoff_and_audit()`
def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, backend=None, instance=None):
	if role not in ('primary', 'AA', 'AF', 'ARCH'):
		raise ValueError('Unknown executor role')
	paths = _paths(backend, profile=instance, conversation_id=conversation_id)
	home = paths['home']
	_, path, _, rows = _trace(home, conversation_id, paths=paths)
	contexts = [(index, item['payload']) for index, item in rows if 'turn_context' == item.get('type')]
	history = [{'step': index, 'model': context.get('model'), 'effort': context.get('effort')} for index, context in contexts]
	observed = {key: history[-1].get(key) if history else None for key in ('model', 'effort')}
	sources = [{'native_file': str(path), 'kind': 'turn_context', 'step': index, 'sha256': hashlib.sha256(json_data(context)).hexdigest()} for index, context in contexts]
	requested = {'model': None, 'effort': None, 'selection': 'unavailable', 'source': None}
	meta = rows[0][1]['payload']
	source = meta.get('source')
	spawn = source.get('subagent', {}).get('thread_spawn', {}) if isinstance(source, dict) else {}
	if 'primary' == role:
		if meta.get('model'):
			requested.update(model=meta['model'], effort=meta.get('reasoning_effort'), selection='native-session-selection', source={'native_file': str(path), 'kind': 'session_meta', 'step': rows[0][0]})
	else:
		if not parent_id or spawn.get('parent_thread_id') != parent_id or parent_id == conversation_id:
			raise ValueError('Native parent/child relationship required for AA/AF metadata')
		_, parent_path, _, parent_rows = _trace(home, parent_id, paths=paths)
		invocation = _spawn(parent_rows, meta)
		try:
			selection = _selection(parent_rows, meta, invocation)
			requested = {key: selection.get(key) for key in ('model', 'effort', 'selection')}
		except ValueError:
			arguments = invocation[2]
			requested.update(model=arguments.get('model'), effort=arguments.get('reasoning_effort') or arguments.get('model_reasoning_effort'), selection='explicit-parent-spawn' if arguments.get('model') else 'inherit')
		requested['source'] = {'native_file': str(parent_path), 'kind': 'spawn_agent', 'step': invocation[0], 'call_id': invocation[1]}
	return finalize_executor_checks('codex-ui', role, conversation_id, parent_id, requested, observed, history, sources, 'Native turn_context reports selected model/effort; missing fields remain unknown; server execution internals are not inferred')
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_codex_custom_system_paths_trace_requests_metadata_and_answers()`
def native_tool_trace(root, request):
	conversation_id = request.get('conversation_id', '')
	paths = _paths(request.get('native_profile_home'), profile=request.get('instance'), conversation_id=conversation_id)
	home = paths['home']
	allowed_homes = [Path(value).resolve() for value in extract_platform_homes(platform_settings('codex'), platform='codex', include_disabled=True).values()]
	if request.get('native_profile_home') and home not in allowed_homes:
		raise ValueError('Native tool trace names an unconfigured Codex profile')
	_, path, raw, rows = _trace(home, conversation_id, paths=paths)
	ids = request.get('call_ids')
	if not isinstance(ids, list) or not ids or (not all((isinstance(x, str) and x.strip() for x in ids))) or (len(set(ids)) != len(ids)):
		raise ValueError('Exact unique Codex native tool call IDs required')
	calls, outputs = ({}, {})
	for index, item in rows:
		payload = item.get('payload', {})
		if 'response_item' == item.get('type') and payload.get('call_id') in ids:
			call_id, kind = (payload['call_id'], payload.get('type'))
			if kind in ('function_call', 'custom_tool_call'):
				if call_id in calls:
					raise ValueError('Ambiguous native tool invocation')
				calls[call_id] = (index, payload, item.get('timestamp'))
			elif kind in ('function_call_output', 'custom_tool_call_output'):
				if call_id in outputs:
					raise ValueError('Ambiguous native tool output')
				outputs[call_id] = (index, payload, item.get('timestamp'))
	events = []
	for call_id in ids:
		if call_id not in calls or call_id not in outputs or outputs[call_id][0] <= calls[call_id][0]:
			raise ValueError('Native tool call has no matched completed output')
		index, call, created_at = calls[call_id]
		output_index, output, completed_at = outputs[call_id]
		arguments = call.get('arguments', call.get('input', {}))
		if isinstance(arguments, str):
			try:
				arguments = json.loads(arguments)
			except ValueError:
				arguments = {'code': arguments} if 'custom_tool_call' == call.get('type') else {}
		result = output.get('output')
		error = True is output.get('isError') or (isinstance(result, dict) and True is result.get('isError'))
		if isinstance(result, str):
			try:
				error |= True is json.loads(result).get('isError')
			except (ValueError, AttributeError):
				pass
		events.append(make_tool_trace_event(call_id, index, output_index, call.get('name', ''), arguments, result, not error, created_at, completed_at, [call, output], namespace=call.get('namespace')))
	return {'surface': 'codex-ui', 'conversation_id': conversation_id, 'native_profile_home': str(home), 'call_ids': ids, 'native_log': str(path), 'native_log_sha256': hashlib.sha256(raw).hexdigest(), 'events': events}
# @used-by :func:`native_review_proof()`
def _assignment_source(rows, meta, assignment):
	r = None
	path = meta['source']['subagent']['thread_spawn']['agent_path']
	for _, item in rows:
		payload = item.get('payload', {})
		if 'response_item' == item.get('type') and 'agent_message' == payload.get('type') and payload.get('recipient') == path:
			parts = payload.get('content', [])
			if any((part.get('text', '').startswith('Message Type: NEW_TASK') for part in parts)) and any((part.get('encrypted_content') == assignment for part in parts if 'encrypted_content' == part.get('type'))):
				r = 'matching-native-spawn-and-child-ciphertext'
				break
	if None is r:
		if assignment.startswith('gAAAAA'):
			raise ValueError('Encrypted native spawn does not match the child assignment')
		r = 'native-parent-spawn.message'
	return r
# 2026-11-14
# "Decompose experiments.py into ExperimentPlanStore, BrowserTraceInspector, and ExperimentRunValidator classes and unify raw_decode JSON object scanning":
# https://github.com/dmitry-ai/harness/issues/72
# @used-by :func:`_review_inputs()`
def _json_objects(value):
	return iter_embedded_json_objects(value, parse_root=False)
# 2026-11-21
# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
# https://github.com/dmitry-ai/harness/issues/113
# @used-by :func:`native_review_proof()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
def _review_inputs(root, rows, parent_id, reviewer_id, *, role='AA'):
	from ..path_registry import canonicalize_root_dir, same_project_root
	from ..research import inside
	calls, r, root_p = ({}, [], canonicalize_root_dir(root))
	for index, item in rows:
		payload = item.get('payload', {})
		if 'response_item' == item.get('type'):
			call_id, kind = (payload.get('call_id'), payload.get('type'))
			if kind in ('function_call', 'custom_tool_call'):
				arguments = payload.get('input', payload.get('arguments', ''))
				if isinstance(arguments, str) and 'review-input' in arguments:
					calls[call_id] = arguments
			elif kind in ('function_call_output', 'custom_tool_call_output') and call_id in calls:
				for receipt in _json_objects(payload.get('output')):
					if 1 == receipt.get({'ARCH': 'arch_review_input'}.get(role, 'upwork_review_input')) and True is receipt.get('verified') and (receipt.get('reviewer_id') == reviewer_id) and (receipt.get('parent_id') == parent_id) and same_project_root(receipt.get('project_root'), root_p):
						try:
							package = inside(root_p, receipt.get('package', ''))
						except ValueError:
							continue
						if package.is_file() and (package.name in calls[call_id]) and (hashlib.sha256(package.read_bytes()).hexdigest() == receipt.get('package_sha256')):
							r.append({'package': receipt['package'], 'package_sha256': receipt['package_sha256'], 'call_id': call_id, 'output_step': index})
	if not r:
		raise ValueError('Native reviewer has no successful review-input execution for this immutable package')
	return r
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# 2026-11-13
# "Unify A.A reviewer isolation, prompt-bias checks, and review-proof helpers across Antigravity and Codex adapters into platforms/trace_common.py":
# https://github.com/dmitry-ai/harness/issues/52
# 2026-11-14
# "Consolidate token/stage summarize, native_review_proof, read-only SQLite, file:// helpers, and ProjectCleanupScanner across trace_common.py, antigravity.py, codex.py, metrics.py, and cleanup.py":
# https://github.com/dmitry-ai/harness/issues/75
# 2026-11-24
# "Clarify verbatim target_claim contract and add native-review-proof wait timeout":
# https://github.com/dmitry-ai/harness/issues/212
# 2026-11-26
# "Add arch-auditor subagent role and content-addressed review CLI":
# https://github.com/dmitry-ai/harness/issues/361
# @used-by :func:`verify_native_proof()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_arch_native_review_proof_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_native_review_proof_and_verify_support_arch_role()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_encrypted_assignment_or_missing_native_package_execution_cannot_prove_a_review()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_native_windows_extended_path_keeps_the_profile_boundary()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_review_provenance_checks_parent_completion_model_and_assignment()`
# @used-by :meth:`test_text_native_binding.TextNativeBindingTests.test_codex_native_review_for_text_has_no_fabricated_upwork_job()`
def native_review_proof(root, parent_id, reviewer_id, *, backend=None, instance=None, write=True, wait_timeout=0.0, role='AA'):
	paths = _paths(backend, profile=instance, conversation_id=reviewer_id or parent_id)
	home = paths['home']
	_, parent_path, _, parent_rows = _trace(home, parent_id, paths=paths)
	child_row, path, raw, rows = _trace(home, reviewer_id, paths=paths)
	meta = rows[0][1]['payload']
	source = meta.get('source')
	if not isinstance(source, dict):
		raise ValueError('Native Codex reviewer is not a spawned child')
	spawn = source.get('subagent', {}).get('thread_spawn', {})
	if parent_id == reviewer_id or spawn.get('parent_thread_id') != parent_id:
		raise ValueError('Codex source does not establish this parent/child relationship')
	if child_row.get('agent_path') and child_row['agent_path'] != spawn.get('agent_path'):
		raise ValueError('Codex child database and session source disagree')
	events = [(i, item['payload']) for i, item in rows if 'event_msg' == item.get('type')]
	if not events or 'task_complete' != events[-1][1].get('type') or (not events[-1][1].get('last_agent_message', '').strip()):
		raise ValueError('Codex reviewer has no completed final native turn')
	final_index, final = events[-1]
	invocation = _spawn(parent_rows, meta)
	# 2026-11-27 "Pass ARCH role through Codex native_review_proof binding": https://github.com/dmitry-ai/harness/issues/394
	require_current_binding(root, parent_id, backend=home, rows=parent_rows, until=invocation[0], role=role)
	selection, child_model = (_selection(parent_rows, meta, invocation), _model(rows))
	if child_model['model'] != selection['model'] or (None is not selection['effort'] and child_model['effort'] != selection['effort']):
		raise ValueError('Observed reviewer model/effort differs from the native parent spawn selection')
	assignment = invocation[2].get('message')
	if not isinstance(assignment, str) or not assignment.strip():
		raise ValueError('Native parent reviewer assignment is unavailable')
	matched_prompts = [assignment]
	for _, p_item in parent_rows:
		p_pay = p_item.get('payload', {}) if isinstance(p_item, dict) else {}
		if 'response_item' == p_item.get('type') and p_pay.get('type') in ('function_call', 'custom_tool_call') and str(p_pay.get('name') or '').endswith(('send_input', 'send_message')):
			p_args = p_pay.get('arguments', p_pay.get('input', {}))
			if reviewer_id.lower() in _extract_codex_target_subagents(p_args):
				parsed = parse_tool_args(p_args)
				msg_txt = parsed.get('message') or parsed.get('Message') or parsed.get('input')
				if isinstance(msg_txt, str) and msg_txt.strip():
					matched_prompts.append(msg_txt)
	resolved_inst = paths['instance'] or instance
	# 2026-11-27 "Pass ARCH role through Codex native_review_proof binding": https://github.com/dmitry-ai/harness/issues/394
	return build_native_review_proof(root, 'codex-ui', parent_id, reviewer_id, spawn.get('agent_path'), path, parent_path, raw, final_index, final['last_agent_message'], matched_prompts, rows, diff_error='Existing Codex proof differs; preserve both versions', extra_fields_fn=lambda: {'native_profile_home': str(home), 'assignment_sha256': hashlib.sha256(assignment.encode('utf-8')).hexdigest(), 'assignment_source': _assignment_source(rows, meta, assignment), 'review_inputs': _review_inputs(root, rows, parent_id, reviewer_id, role=role), 'observed_model': child_model, 'model_selection': selection, 'executor_metadata': native_executor_metadata(root, reviewer_id, role=role, parent_id=parent_id, backend=home, instance=resolved_inst), 'model_verification': 'native child model/effort checked against actual parent spawn parameters'}, write=write, role=role)
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# 2026-11-13
# "Unify A.A reviewer isolation, prompt-bias checks, and review-proof helpers across Antigravity and Codex adapters into platforms/trace_common.py":
# https://github.com/dmitry-ai/harness/issues/52
# @used-by :func:`agent_tools.platforms.adapter()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_arch_native_review_proof_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_native_review_proof_and_verify_support_arch_role()`
def verify_native_proof(root, native, package=None):
	# 2026-11-26
	# "Add arch-auditor subagent role and content-addressed review CLI":
	# https://github.com/dmitry-ai/harness/issues/361
	home, role = (Path(native.get('native_profile_home', '')).resolve(), (native.get('executor_metadata') or {}).get('role') or 'AA')
	allowed_homes = [Path(value).resolve() for value in extract_platform_homes(platform_settings('codex'), platform='codex', include_disabled=True).values()]
	if home not in allowed_homes:
		raise ValueError('Saved Codex proof names an unconfigured profile')
	r = verify_review_proof_core(root, native, native_review_proof(root, native.get('parent_id', ''), native.get('reviewer_id', ''), backend=home, instance=native.get('instance'), write=False, role=role), ('native_log_sha256', 'final_response_sha256', 'assignment_sha256', 'assignment_source', 'review_inputs', 'final_step', 'job_id', 'observed_model', 'model_selection'), trace_error='Codex review proof differs from the actual native trace', identity_error='Codex review proof has a different explicit project identity')
	if package and (not any((Path(item['package']).name == package for item in r['review_inputs']))):
		raise ValueError('Codex reviewer did not verify this immutable KB review package')
	return r
# 2026-10-17
# "Add /upwork-cleanup skill and cross-platform empty project pruner with timestamped audit logs":
# https://github.com/dmitry-ai/harness/issues/8
# @used-by :func:`register()`
# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
def shared_control(request):
	config = platform_settings('codex')
	script = 'import {controlWithHelper as control} from ' + json.dumps(Path(config['ui_manage']).as_uri()) + ";let input='';for await(const part of process.stdin)input+=part;console.log(JSON.stringify(await control(JSON.parse(input))));"
	try:
		result = subprocess.run([config['node'], '--input-type=module', '-e', script], input=json.dumps(request), text=True, capture_output=True, timeout=55, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
	except subprocess.TimeoutExpired as exc:
		raise RuntimeError('Shared-Projects timed out; the request may have been accepted. Repeat the same idempotent command to recover.') from exc
	if result.returncode:
		raise RuntimeError('Shared-Projects request failed: ' + (result.stderr.strip() or result.stdout.strip()))
	return json.loads(result.stdout)
# 2026-10-16
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# @used-by :meth:`test_registration_portability.RegistrationProfileTests.test_codex_adapter_uses_fallback_and_rejects_wrong_native_name_without_rename()`
def register(project_dir, domain_or_topic, date_str=None):
	from ..runtime import request_day, registration_profile_name
	from ..registration import validate_registration
	profile, day = (registration_profile_name(), request_day(date_str))
	receipt = shared_control({'command': 'shared-ensure-project', 'profile': profile, 'project': {'name': f'{domain_or_topic} - U.P.{day:%Y.%m.%d}', 'trustPolicy': 'upwork-daily', 'rootPaths': [str(Path(project_dir).resolve())], 'folderPath': ['Upwork', 'Proposals', f'{day.year:04d}', f'{day.month:02d}', f'{day.day:02d}']}})
	# 2026-10-25
	# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
	# https://github.com/dmitry-ai/harness/issues/17
	if not receipt.get('complete') and receipt.get('shared_id') and any((isinstance(info, dict) and info.get('state') in ('connected', 'initializing') for info in (receipt.get('accounts') or {}).values())):
		import time
		for _ in range(8):
			time.sleep(0.4)
			receipt = shared_control({'command': 'shared-registration', 'sharedId': receipt['shared_id'], 'profile': profile})
			if receipt.get('complete') or not any((isinstance(info, dict) and info.get('state') in ('connected', 'initializing') for info in (receipt.get('accounts') or {}).values())):
				break
	return validate_registration(project_dir, domain_or_topic, day.isoformat(), 'codex', {**receipt, 'surface': 'codex-ui', 'profile': profile})
# 2026-11-14
# "Consolidate token/stage summarize, native_review_proof, read-only SQLite, file:// helpers, and ProjectCleanupScanner across trace_common.py, antigravity.py, codex.py, metrics.py, and cleanup.py":
# https://github.com/dmitry-ai/harness/issues/75
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.summarize()`
def summarize(paths, bindings=None):
	tools, events, seen = (Counter(), [], set())
	for path in paths:
		cid = None
		for index, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines()):
			item = json.loads(line)
			payload = item.get('payload', {})
			if 'session_meta' == item.get('type') and None is cid:
				cid = payload['id']
			if 'response_item' == item.get('type') and payload.get('type') in ('custom_tool_call', 'function_call'):
				tools[payload.get('name', 'unknown')] += 1
			if 'token_usage_record' == item.get('type'):
				owner = payload.get('thread_id') or cid
				key = (owner, payload.get('turn_id'), payload.get('response_id', index))
				if key in seen:
					events.append(('duplicate',))
				else:
					seen.add(key)
					events.append(('generation', owner, index, payload.get('usage') or {}))
	return summarize_token_records(events, bindings, prefix={'surface': 'codex-ui'}, field_map={'input_tokens': 'input_tokens', 'cache_read_tokens': 'cached_input_tokens', 'output_tokens': 'output_tokens'}, tools=tools, extra={'interpretation': 'Observed native token_usage_record counters; not quota percentage, currency or proof of quality'})
