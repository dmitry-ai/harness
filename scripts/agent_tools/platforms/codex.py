# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate token/stage summarize, native_review_proof, read-only SQLite, file:// helpers, and ProjectCleanupScanner across trace_common.py, antigravity.py, codex.py, metrics.py, and cleanup.py":
# https://github.com/dmitry-ai/harness/issues/75
# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose git_gate.py into shell_audit.py, GitRepoGate, and single-pass pre-commit validation":
# https://github.com/dmitry-ai/harness/issues/67
# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose experiments.py into ExperimentPlanStore, BrowserTraceInspector, and ExperimentRunValidator classes and unify raw_decode JSON object scanning":
# https://github.com/dmitry-ai/harness/issues/72
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify cross-platform subagent BFS traversal, tool-call effect classifier, turn accumulator, and invoke_subagent parser in platforms/trace_common.py":
# https://github.com/dmitry-ai/harness/issues/64
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract CodexTurnScanner class from native_answers in platforms/codex.py with completion_service_steps parity and cached subagent indexing":
# https://github.com/dmitry-ai/harness/issues/61
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Deduplicate turn compaction/delegation reducers, shell/path tool normalization, and request/metadata wrappers across Antigravity and Codex adapters":
# https://github.com/dmitry-ai/harness/issues/58
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify A.A reviewer isolation, prompt-bias checks, and review-proof helpers across Antigravity and Codex adapters into platforms/trace_common.py":
# https://github.com/dmitry-ai/harness/issues/52
# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
# https://github.com/dmitry-ai/harness/issues/48
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
from ..runtime import platform_settings, profile_name
from ..research import json_data
from ..shell_audit import extract_issue_actions_from_outputs
from ..storage import iter_embedded_json_objects
from .trace_common import UUID_PATTERN, build_native_review_proof, collect_prompt_bias_issues, collect_subagent_bfs, current_turn_requests, finalize_executor_checks, init_turn_accumulator, local_uri_to_path, make_tool_trace_event, open_readonly_sqlite, parse_tool_args, partial_candidate_read_issues as _partial_candidate_read_issues, persist_review_proof, prompt_bias_issues, record_normalized_tool_effects, require_turn_binding, reviewer_isolation_issues, summarize_token_records, summarize_turn_activity, verify_review_proof_core
class CodexTurnScanner:
	def __init__(self, root, conversation_id, *, backend=None):
		self.root = root
		self.root_p = Path(root).resolve()
		self.conversation_id = conversation_id
		self.home = _home(backend)
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
	def _finalize_turn(self, t_idx, turn, acc):
		turn['owned'] = bool(turn['requests']) and len(turn['requests']) == len(acc['all_request_steps'])
		turn['issue_actions'] = extract_issue_actions_from_outputs([out for rec in acc['tool_records'] for out in rec.get('outputs', [])])
		self._collect_subagent_bfs(t_idx, turn, acc)
		for rec in acc['tool_records']:
			rec.pop('target_subagents', None)
		turn['compaction'], turn['delegation'] = summarize_turn_activity(acc['checkpoint_steps'], acc['tool_steps'], acc['subagent_steps'], acc['aa_subagent_steps'], acc['af_subagent_steps'], acc['kb_persistence_steps'], acc['transcript_read_steps'], acc['tool_records'], acc['file_reads'], acc['file_writes'], svc_steps=acc['completion_service_steps'], aa_part_errs=acc['aa_partial_read_violations'])
	def _index_profile_subagents(self):
		if not self.indexed_subagents:
			self.indexed_subagents = True
			if 4096 < len(_SUBAGENT_PARENT_CACHE):
				_SUBAGENT_PARENT_CACHE.clear()
			for db_file in sorted(self.home.glob('state_*.sqlite')):
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
	def _load_context(self):
		from .request_binding import completion_project_id
		_, self.path, _, self.rows = _trace(self.home, self.conversation_id)
		meta = self.rows[0][1]['payload']
		self.child = isinstance(meta.get('source'), dict) and bool(meta['source'].get('subagent'))
		selected, _, _ = _request_scope(self.root, self.rows, identifier=completion_project_id(self.root))
		self.requests = {index: {'id': f'codex:{self.conversation_id}:{index}', 'text': text, 'native_step': index, 'project_binding': binding} for index, text, binding in selected}
	def _resolve_subagent_child(self, sub_id, expected_parent, anchor, turn, acc):
		r = None
		if sub_id not in self.thread_parent_map or (self.thread_parent_map[sub_id] and self.thread_parent_map[sub_id] == expected_parent):
			pre_children = self.child_parent_map.get(sub_id, [])
			try:
				sub_db_row, _, _, sub_rows = _trace(self.home, sub_id)
				sub_agent_path = str((sub_db_row or {}).get('agent_path') or '')
				r = (sub_rows, not re.search('\\baf\\b', sub_agent_path, flags=re.I) and bool(acc['aa_subagent_steps'] or sub_agent_path), pre_children, lambda sid, rows: self._visit_subagent_rows(sid, rows, anchor, turn, acc))
			except (ValueError, OSError):
				r = ([], False, pre_children, None)
		return r
	def _scan_primary_turns(self):
		current, acc = (None, None)
		for index, item in self.rows:
			payload = item.get('payload', {})
			kind, ptype = (item.get('type'), payload.get('type'))
			if None is not current and (kind in ('compacted', 'context_compacted', 'checkpoint') or (kind in ('event_msg', 'response_item') and ptype in ('context_compacted', 'compacted', 'checkpoint'))):
				acc['checkpoint_steps'].append(index)
			elif None is not current and 'response_item' == kind and ptype in ('function_call_output', 'custom_tool_call_output'):
				rec = acc['pending_calls'].get(payload.get('call_id'))
				if None is not rec and None is not payload.get('output'):
					out = payload.get('output')
					rec['outputs'].append((out if isinstance(out, str) else json.dumps(out, ensure_ascii=False))[:4000])
			elif 'event_msg' == kind and 'task_started' == ptype:
				ident = payload.get('turn_id')
				if not isinstance(ident, str) or not ident:
					raise ValueError('Native Codex task_started has no turn ID')
				current = {'turn_id': ident, 'requests': [], 'completed': False, 'response': None, 'start_step': index, 'final_step': None, 'completion_step': None, 'aborted': False, 'exec5_violations': [], 'http_fetch_violations': [], 'touched_files': []}
				acc = init_turn_accumulator(extra={'all_request_steps': [], 'pending_calls': {}, 'exec5_violations': current['exec5_violations'], 'http_fetch_violations': current['http_fetch_violations'], 'touched_files': current['touched_files']})
				self.turn_entries.append((current, acc))
			elif None is not current and 'event_msg' == kind and ptype in ('task_complete', 'turn_aborted') and payload.get('turn_id') == current['turn_id']:
				current['completion_step'], current['aborted'] = (index, 'turn_aborted' == ptype)
				if not current['aborted']:
					native_final = payload.get('last_agent_message')
					if None is not current['response'] and isinstance(native_final, str) and (native_final != current['response']):
						raise ValueError('Native Codex final message and completion event disagree')
					current['completed'] = bool(current['response'] and None is not current['final_step'])
			elif None is not current and 'response_item' == kind and 'message' == ptype:
				if 'assistant' == payload.get('role') and ('final_answer' == payload.get('phase') or 'final' == payload.get('channel')) and payload.get('status') in (None, 'completed'):
					text = ''.join((p.get('text', '') for p in payload.get('content', []) if 'output_text' == p.get('type')))
					if text.strip():
						current['response'], current['final_step'] = (text, index)
				elif 'user' == payload.get('role'):
					text = ''.join((p.get('text', '') for p in payload.get('content', []) if p.get('type') in ('input_text', 'output_text')))
					if _actual_user_input(text, payload):
						acc['all_request_steps'].append(index)
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
				record_normalized_tool_effects(self.root_p, index, name, raw_args, raw_cmd, acc, extra_violation={'call_id': payload.get('call_id')}, track_turn_steps=True, transcript_tokens=(str(self.path.name),))
		self.current_turn = current
	def _visit_subagent_rows(self, sub_id, sub_rows, anchor, turn, acc):
		r, sub_outputs, sub_spawn_call_ids = ([], [], set())
		for _, s_item in sub_rows:
			s_kind, s_pay = (s_item.get('type'), s_item.get('payload', {}))
			if 'response_item' == s_kind and s_pay.get('type') in ('function_call_output', 'custom_tool_call_output') and None is not s_pay.get('output'):
				out = s_pay.get('output')
				out_s = (out if isinstance(out, str) else json.dumps(out, ensure_ascii=False))[:4000]
				sub_outputs.append(out_s)
				if s_pay.get('call_id') in sub_spawn_call_ids:
					r.extend(_extract_codex_spawn_output_uuids(out_s))
			elif 'response_item' == s_kind and s_pay.get('type') in ('function_call', 'custom_tool_call'):
				s_name = s_pay.get('name', '')
				s_args_in = s_pay.get('arguments', s_pay.get('input', {}))
				s_raw_in = s_pay.get('input', s_pay.get('arguments', ''))
				s_raw = s_raw_in if isinstance(s_raw_in, str) else json.dumps(s_raw_in, ensure_ascii=False)
				if s_name.endswith(('spawn_agent', 'invoke_subagent')) and s_pay.get('call_id'):
					sub_spawn_call_ids.add(s_pay['call_id'])
				elif s_name.endswith(('send_input', 'send_message', 'wait', 'wait_agent')):
					r.extend(_extract_codex_target_subagents(s_args_in))
				record_normalized_tool_effects(self.root_p, anchor, s_name, s_args_in, s_raw, acc, extra_violation={'subagent_id': sub_id})
		for act in extract_issue_actions_from_outputs(sub_outputs):
			act_with_sub = {**act, 'subagent_id': sub_id}
			if act_with_sub not in turn['issue_actions']:
				turn['issue_actions'].append(act_with_sub)
		return r
	def scan(self):
		self._load_context()
		self._scan_primary_turns()
		for t_idx, (turn, acc) in enumerate(self.turn_entries):
			self._finalize_turn(t_idx, turn, acc)
		return {'platform': 'codex', 'conversation_id': self.conversation_id, 'native_backend': str(self.home), 'source_file': str(self.path), 'primary': not self.child, 'turns': [turn for turn, _ in self.turn_entries], 'active_turn_id': self.current_turn['turn_id'] if self.current_turn and (not self.current_turn['completion_step']) else None}
_SUBAGENT_PARENT_CACHE: dict[str, tuple[int, int, str]] = {}
def _local_path(value):
	return local_uri_to_path(value)
def _home(backend=None, profile=None):
	if None is not backend:
		r = Path(backend).resolve()
	else:
		values = platform_settings('codex')['homes']
		name = profile_name(profile)
		if name not in values:
			raise ValueError('Unknown Codex profile')
		r = Path(values[name]).resolve()
	return r
def _trace(home, conversation_id):
	home = _local_path(home)
	if not re.fullmatch('[a-f0-9-]{36}', conversation_id):
		raise ValueError('Exact native Codex thread UUID required')
	found = []
	for database in sorted(home.glob('state_*.sqlite')):
		with open_readonly_sqlite(database, row_factory=sqlite3.Row) as connection:
			row = connection.execute('SELECT * FROM threads WHERE id=?', (conversation_id,)).fetchone()
			if row:
				found.append(dict(row))
	if 1 != len(found):
		raise ValueError('Native Codex thread is missing or ambiguous in this profile')
	row = found[0]
	path = _local_path(row['rollout_path'])
	if not path.is_relative_to(home / 'sessions'):
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
		elif kind in ('compacted', 'context_compacted', 'checkpoint') or ('event_msg' == kind and payload.get('type') in ('context_compacted', 'compacted', 'checkpoint')):
			rows.append((index, {'type': 'event_msg', 'payload': {'type': 'context_compacted', 'turn_id': payload.get('turn_id')}}))
	if not rows or 'session_meta' != rows[0][1].get('type') or rows[0][1]['payload'].get('id') != conversation_id:
		raise ValueError('Codex trace identity differs from native database')
	return (row, path, raw, rows)
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
def native_requests(root, conversation_id, *, backend=None):
	home = _home(backend)
	selected, _, _ = _request_scope(root, _trace(home, conversation_id)[3])
	return current_turn_requests(selected, conversation_id, 'codex-ui', 'Native Codex requests do not identify this project; use its exact project root or /upwork-init URL', id_fmt='codex:{cid}:{idx}', extra={'native_profile_home': str(home)})
def require_current_binding(root, conversation_id, *, backend=None, rows=None, until=None):
	selected, active, binding = _request_scope(root, _trace(_home(backend), conversation_id)[3] if None is rows else rows, until=until)
	return require_turn_binding(selected, active, binding, 'Native Codex conversation is currently bound to another project or no exact project root')
def _extract_codex_target_subagents(raw_args) -> list[str]:
	parsed_args = parse_tool_args(raw_args)
	candidates = [val.strip().lower() for key in ('id', 'Recipient', 'agent_id', 'subagent_id') for val in [parsed_args.get(key)] if isinstance(val, str)]
	ids_val = parsed_args.get('ids')
	if isinstance(ids_val, list):
		candidates.extend((item.strip().lower() for item in ids_val if isinstance(item, str)))
	return [u for u in dict.fromkeys(candidates) if re.fullmatch(UUID_PATTERN, u)]
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
def native_answers(root, conversation_id, *, backend=None):
	return CodexTurnScanner(root, conversation_id, backend=backend).scan()
def _model(rows, before=None):
	contexts = [item['payload'] for index, item in rows if 'turn_context' == item.get('type') and (None is before or index <= before)]
	if not contexts or not contexts[-1].get('model') or (not contexts[-1].get('effort')):
		raise ValueError('Actual Codex model/effort is unavailable in native turn context')
	return {key: contexts[-1][key] for key in ('model', 'effort')}
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
def _selection(parent_rows, child_meta, invocation=None):
	index, call_id, arguments = invocation or _spawn(parent_rows, child_meta)
	parent = _model(parent_rows, before=index)
	model = arguments.get('model') or parent['model']
	effort = arguments.get('reasoning_effort') or arguments.get('model_reasoning_effort')
	if None is effort and model == parent['model']:
		effort = parent['effort']
	return {'model': model, 'effort': effort, 'invocation_call_id': call_id, 'task_name': arguments['task_name'], 'selection': 'explicit-parent-spawn' if arguments.get('model') or arguments.get('reasoning_effort') else 'inherit'}
def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, backend=None):
	if role not in ('primary', 'AA', 'AF'):
		raise ValueError('Unknown executor role')
	home = _home(backend)
	_, path, _, rows = _trace(home, conversation_id)
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
		_, parent_path, _, parent_rows = _trace(home, parent_id)
		invocation = _spawn(parent_rows, meta)
		try:
			selection = _selection(parent_rows, meta, invocation)
			requested = {key: selection.get(key) for key in ('model', 'effort', 'selection')}
		except ValueError:
			arguments = invocation[2]
			requested.update(model=arguments.get('model'), effort=arguments.get('reasoning_effort') or arguments.get('model_reasoning_effort'), selection='explicit-parent-spawn' if arguments.get('model') else 'inherit')
		requested['source'] = {'native_file': str(parent_path), 'kind': 'spawn_agent', 'step': invocation[0], 'call_id': invocation[1]}
	return finalize_executor_checks('codex-ui', role, conversation_id, parent_id, requested, observed, history, sources, 'Native turn_context reports selected model/effort; missing fields remain unknown; server execution internals are not inferred')
def native_tool_trace(root, request):
	home = _home(request.get('native_profile_home'))
	if request.get('native_profile_home') and home not in [Path(value).resolve() for value in platform_settings('codex')['homes'].values()]:
		raise ValueError('Native tool trace names an unconfigured Codex profile')
	conversation_id = request.get('conversation_id', '')
	_, path, raw, rows = _trace(home, conversation_id)
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
def _json_objects(value):
	return iter_embedded_json_objects(value, parse_root=False)
def _review_inputs(root, rows, parent_id, reviewer_id):
	calls, r, root_p = ({}, [], Path(root).resolve())
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
					if 1 == receipt.get('upwork_review_input') and True is receipt.get('verified') and (receipt.get('reviewer_id') == reviewer_id) and (receipt.get('parent_id') == parent_id) and (receipt.get('project_root') == str(root_p)):
						package = root_p / receipt.get('package', '')
						if package.resolve().is_relative_to(root_p) and package.is_file() and (package.name in calls[call_id]) and (hashlib.sha256(package.read_bytes()).hexdigest() == receipt.get('package_sha256')):
							r.append({'package': receipt['package'], 'package_sha256': receipt['package_sha256'], 'call_id': call_id, 'output_step': index})
	if not r:
		raise ValueError('Native reviewer has no successful review-input execution for this immutable package')
	return r
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def native_review_proof(root, parent_id, reviewer_id, *, backend=None, write=True):
	home = _home(backend)
	_, parent_path, _, parent_rows = _trace(home, parent_id)
	child_row, path, raw, rows = _trace(home, reviewer_id)
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
	require_current_binding(root, parent_id, backend=home, rows=parent_rows, until=invocation[0])
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
	return build_native_review_proof(root, 'codex-ui', parent_id, reviewer_id, spawn.get('agent_path'), path, parent_path, raw, final_index, final['last_agent_message'], matched_prompts, rows, diff_error='Existing Codex proof differs; preserve both versions', extra_fields_fn=lambda: {'native_profile_home': str(home), 'assignment_sha256': hashlib.sha256(assignment.encode('utf-8')).hexdigest(), 'assignment_source': _assignment_source(rows, meta, assignment), 'review_inputs': _review_inputs(root, rows, parent_id, reviewer_id), 'observed_model': child_model, 'model_selection': selection, 'executor_metadata': native_executor_metadata(root, reviewer_id, role='AA', parent_id=parent_id, backend=home), 'model_verification': 'native child model/effort checked against actual parent spawn parameters'}, write=write)
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def verify_native_proof(root, native, package=None):
	home = Path(native.get('native_profile_home', '')).resolve()
	if home not in [Path(value).resolve() for value in platform_settings('codex')['homes'].values()]:
		raise ValueError('Saved Codex proof names an unconfigured profile')
	r = verify_review_proof_core(root, native, native_review_proof(root, native.get('parent_id', ''), native.get('reviewer_id', ''), backend=home, write=False), ('native_log_sha256', 'final_response_sha256', 'assignment_sha256', 'assignment_source', 'review_inputs', 'final_step', 'job_id', 'observed_model', 'model_selection'), trace_error='Codex review proof differs from the actual native trace', identity_error='Codex review proof has a different explicit project identity')
	if package and (not any((Path(item['package']).name == package for item in r['review_inputs']))):
		raise ValueError('Codex reviewer did not verify this immutable KB review package')
	return r
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
def register(project_dir, domain_or_topic, date_str=None):
	from ..runtime import request_day, registration_profile_name
	from ..registration import validate_registration
	profile, day = (registration_profile_name(), request_day(date_str))
	receipt = shared_control({'command': 'shared-ensure-project', 'profile': profile, 'project': {'name': f'{domain_or_topic} - U.P.{day:%Y.%m.%d}', 'trustPolicy': 'upwork-daily', 'rootPaths': [str(Path(project_dir).resolve())], 'folderPath': ['Upwork', 'Proposals', f'{day.year:04d}', f'{day.month:02d}', f'{day.day:02d}']}})
	if not receipt.get('complete') and receipt.get('shared_id') and any((isinstance(info, dict) and info.get('state') in ('connected', 'initializing') for info in (receipt.get('accounts') or {}).values())):
		import time
		for _ in range(8):
			time.sleep(0.4)
			receipt = shared_control({'command': 'shared-registration', 'sharedId': receipt['shared_id'], 'profile': profile})
			if receipt.get('complete') or not any((isinstance(info, dict) and info.get('state') in ('connected', 'initializing') for info in (receipt.get('accounts') or {}).values())):
				break
	return validate_registration(project_dir, domain_or_topic, day.isoformat(), 'codex', {**receipt, 'surface': 'codex-ui', 'profile': profile})
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
