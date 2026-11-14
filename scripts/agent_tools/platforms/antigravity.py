# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate token/stage summarize, native_review_proof, read-only SQLite, file:// helpers, and ProjectCleanupScanner across trace_common.py, antigravity.py, codex.py, metrics.py, and cleanup.py":
# https://github.com/dmitry-ai/harness/issues/75
# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose git_gate.py into shell_audit.py, GitRepoGate, and single-pass pre-commit validation":
# https://github.com/dmitry-ai/harness/issues/67
# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose completion.py into declarative turn-hygiene gates, TurnJournalReconciler, and unified answer-groups/authorize flow across completion.py, workflow.py, journal.py, text_workflow.py, and antigravity.py":
# https://github.com/dmitry-ai/harness/issues/60
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify cross-platform subagent BFS traversal, tool-call effect classifier, turn accumulator, and invoke_subagent parser in platforms/trace_common.py":
# https://github.com/dmitry-ai/harness/issues/64
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract AnswerPreparationRunner class from prepare in completion.py, add typed gate_id readiness tracking, deduplicate native trace loading, and unify resolve_journal_dir":
# https://github.com/dmitry-ai/harness/issues/57
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Deduplicate turn compaction/delegation reducers, shell/path tool normalization, and request/metadata wrappers across Antigravity and Codex adapters":
# https://github.com/dmitry-ai/harness/issues/58
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract AntigravityTurnScanner class from native_answers in platforms/antigravity.py":
# https://github.com/dmitry-ai/harness/issues/55
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify A.A reviewer isolation, prompt-bias checks, and review-proof helpers across Antigravity and Codex adapters into platforms/trace_common.py":
# https://github.com/dmitry-ai/harness/issues/52
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix Antigravity executor/generation model mismatch in native-review-proof, decouple post-finalize deliverable reviews from initial Analysis.json, cache source grounding, and preserve journal recording on gate failure":
# https://github.com/dmitry-ai/harness/issues/51
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce local_source_grounding_issues across touched client deliverables, require post-compaction re-read of evicted tool outputs, and close A.A review bypass":
# https://github.com/dmitry-ai/harness/issues/50
# 2026-10-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify Antigravity and OpenAI Codex adapters with build-native projections, parent-driven model selection, and cross-system continuation":
# https://github.com/dmitry-ai/harness/issues/6
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent intermediate subagent status replies from polluting the journal, enforce TEXT-1 language gate in completion, and codify background task timeouts":
# https://github.com/dmitry-ai/harness/issues/30
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement claim-level Merkle cache, blind entailment predicates, single adversarial falsifier, and full-read reviewer verification":
# https://github.com/dmitry-ai/harness/issues/47
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
# https://github.com/dmitry-ai/harness/issues/48
from pathlib import Path
from datetime import date
import hashlib
import json
import re
import sqlite3
import uuid
from ..runtime import platform_settings, request_day
from ..knowledge import json_bytes
from ..shell_audit import extract_issue_actions_from_outputs
from ..storage import create_bytes, replace_bytes, locked
from .trace_common import UUID_PATTERN, build_native_review_proof, collect_prompt_bias_issues, collect_subagent_bfs, current_turn_requests, extract_resource_uri, finalize_executor_checks, init_turn_accumulator, iter_antigravity_subagents, local_uri_to_path, make_tool_trace_event, merge_turn_accumulators, open_readonly_sqlite, parse_tool_args, partial_candidate_read_issues as _partial_candidate_read_issues, persist_review_proof, prompt_bias_issues, read_jsonl_objects, record_normalized_tool_effects, require_turn_binding, reviewer_isolation_issues, verify_review_proof_core
ANTIGRAVITY_PROJECTS_DIR = Path.home() / '.gemini/config/projects'
ANTIGRAVITY_FOLDERS_JSON = Path(platform_settings('antigravity')['folders_json'])
COMPLETED_STEP_STATUSES = (3, 5)
_SEGMENT_TRANSIENT_KEYS = {'spawned_subagents', 'completed_subagents', 'answer_prepared_in_segment'}
class AntigravityTurnScanner:
	def __init__(self, root, conversation_id, *, backend=None):
		self.root = root
		self.root_p = Path(root).resolve()
		self.conversation_id = conversation_id
		self.backend = Path(backend).resolve() if backend else Path.home() / '.gemini/antigravity'
		self.summary = None
		self.path = None
		self.rows = []
		self.inputs = []
		self.requests = {}
		self.statuses = {}
		self.jdir = None
		self.journal_groups = {}
		self.boundaries = []
		self.completed_turn_cids: set[str] = set()
	def _collect_outputs(self, rows_slice, start_pos, *, step_idx=None, file_reads=None):
		r = []
		for cand in rows_slice[start_pos + 1:]:
			if not isinstance(cand, dict):
				continue
			if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
				break
			if 'GENERIC' == cand.get('type') and cand.get('content'):
				c_str = str(cand.get('content'))
				r.append(c_str[:4000])
				if None is not file_reads and None is not step_idx:
					for m_step_out in re.finditer('file:///+([A-Za-z]:/[^\\s"\\\'<>`]+?/\\.system_generated/steps/\\d+/output\\.txt)', c_str):
						file_reads.append((step_idx, m_step_out.group(1).replace('\\', '/')))
		return r
	def _collect_subagent_bfs(self, position, segment, seg):
		r = {self.conversation_id}
		if seg['subagent_steps']:
			seeds = [(m_uuid, bool(seg['aa_subagent_steps']), self.conversation_id) for m_uuid in _extract_subagent_uuids(segment)]
			if 1 == len(self.boundaries) - position:
				try:
					with open_readonly_sqlite(self.backend / 'conversation_summaries.db') as p_conn:
						seeds.extend(((p_row[0], bool(seg['aa_subagent_steps']), self.conversation_id) for p_row in p_conn.execute('SELECT conversation_id FROM conversation_summaries WHERE parent_conversation_id=?', (self.conversation_id,)).fetchall() if p_row and p_row[0] and p_row[0] not in self.completed_turn_cids))
				except Exception:
					pass
			anchor = seg['subagent_steps'][-1]
			r = collect_subagent_bfs(self.conversation_id, self.root_p, seeds, lambda cid, depth, hint, parent: self._resolve_subagent_child(cid, hint, parent, anchor, seg), seg['aa_partial_read_violations'])
		return r
	def _finalize_segment(self, start, end, segment, seg, visited_cids):
		last = segment[-1] if segment else {}
		final_step = last.get('step_index')
		final = 'PLANNER_RESPONSE' == last.get('type') and (not last.get('tool_calls')) and bool(last.get('content', '').strip()) and (self.statuses.get(final_step) in ((15, 3), (15, 5)))
		last_user_idx = self.summary.get('last_user_input_step_index')
		last_db_user = max((idx for idx, (stype, _) in self.statuses.items() if 14 == stype), default=start)
		idle = 'CASCADE_RUN_STATUS_IDLE' == self.summary.get('status') and 0 == self.summary.get('not_fully_idle') and (not self.summary.get('killed')) and (last_user_idx == start or (0 == start and -1 == last_user_idx)) and (last_db_user == start) and (final_step == max(self.statuses, default=-1))
		req_id = f'{self.conversation_id}-{start}'
		j_entry = self.journal_groups.get(req_id)
		has_single_journal_group = None is not j_entry and 1 == len(j_entry[0].get('request_ids', []))
		last_text = str(last.get('content') or '')
		intermediate_wait = None is not end and (not seg['answer_prepared_in_segment']) and (not has_single_journal_group) and (seg['completed_subagents'] < seg['spawned_subagents'] or bool(re.search('(?i)(?:^|\\n)\\s*waiting\\s+for\\s+(?:the\\s+)?(?:remaining\\s+)?(?:\\d+\\s+)?(?:subagents?|background\\s+tasks?|tasks?|commands?)\\b[^\\n]{0,120}\\bto\\s+(?:complete|finish)\\b', last_text)))
		if intermediate_wait:
			completed, resp_text = (False, None)
		elif None is not j_entry and (not final or 1 < len(j_entry[0].get('request_ids', []))):
			completed = req_id == j_entry[0]['request_ids'][-1] and (None is not end or idle)
			resp_text = (self.jdir / 'res' / f'{j_entry[1]}.md').read_bytes().decode('utf-8') if completed else None
		else:
			completed = bool(final and (None is not end or idle))
			resp_text = last.get('content') if completed else None
		self.completed_turn_cids.update(visited_cids - {self.conversation_id})
		return {'turn_id': f'ag-{self.conversation_id}-{start}', 'requests': [self.requests[start]] if start in self.requests else [], 'owned': start in self.requests, 'completed': completed, 'aborted': False, 'response': resp_text, 'start_step': start, 'final_step': final_step if completed else None, 'completion_step': final_step if completed else None, **{k: v for k, v in seg.items() if k not in _SEGMENT_TRANSIENT_KEYS}}
	def _load_context(self):
		from .request_binding import completion_project_id
		from ..journal import completed_request_group_index, resolve_journal_dir
		if not re.fullmatch('[a-f0-9-]{36}', self.conversation_id):
			raise ValueError('Exact native Antigravity conversation UUID required')
		with open_readonly_sqlite(self.backend / 'conversation_summaries.db', row_factory=sqlite3.Row) as conn:
			summary = conn.execute('SELECT * FROM conversation_summaries WHERE conversation_id=?', (self.conversation_id,)).fetchone()
			self.summary = dict(summary) if None is not summary else None
		if None is self.summary or 'parent_conversation_id' not in self.summary:
			raise ValueError('Native Antigravity primary/child identity is unavailable')
		self.path = self.backend / 'brain' / self.conversation_id / '.system_generated/logs/transcript_full.jsonl'
		self.rows = read_jsonl_objects(self.path, partial_error='Native Antigravity trace has a partial record; retry after flush')
		self.inputs = _native_inputs(self.backend, self.conversation_id)
		selected, _, _ = _request_scope(self.root, self.conversation_id, self.backend, inputs=self.inputs, identifier=completion_project_id(self.root))
		self.requests = {index: {'id': f'{self.conversation_id}-{index}', 'text': text, 'native_step': index, 'project_binding': binding} for index, text, binding in selected}
		with open_readonly_sqlite(self.backend / 'conversations' / (self.conversation_id + '.db')) as conn:
			self.statuses = {index: (kind, status) for index, kind, status in conn.execute('SELECT idx,step_type,status FROM steps')}
		self.jdir = resolve_journal_dir(self.root_p)
		self.journal_groups = completed_request_group_index(self.jdir)
		self.boundaries = sorted((index for index, _ in self.inputs))
	def _merge_pending(self, items):
		return merge_turn_accumulators(items, allow_step_output_recovery=True)
	def _query_child_summary(self, child_cid, expected_parent):
		child_agent_name, db_grandchildren, parent_mismatch = (None, [], False)
		try:
			with open_readonly_sqlite(self.backend / 'conversation_summaries.db') as c_conn:
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
	def _record_subagent_calls(self, child_cid, c_rows, anchor_step, seg):
		for c_pos, c_ev in enumerate(c_rows):
			if isinstance(c_ev, dict):
				c_calls = [c for c in c_ev.get('tool_calls') or [] if isinstance(c, dict)]
				if c_calls:
					for act_item in extract_issue_actions_from_outputs(self._collect_outputs(c_rows, c_pos)):
						seg['issue_actions'].append({**act_item, 'step': anchor_step, 'subagent_id': child_cid})
					for c_call in c_calls:
						record_normalized_tool_effects(self.root_p, anchor_step, c_call.get('name', ''), c_call.get('args', {}), '', seg, extra_violation={'subagent_id': child_cid})
		return ()
	def _record_tool_calls(self, step_idx, calls, outputs, seg):
		seg['tool_steps'].append(step_idx)
		seg['tool_records'].append({'step': step_idx, 'tools': [c.get('name', '') for c in calls], 'outputs': outputs})
		for act_item in extract_issue_actions_from_outputs(outputs):
			seg['issue_actions'].append({**act_item, 'step': step_idx})
		for call in calls:
			raw_args = call.get('args', {})
			args = parse_tool_args(raw_args)
			args_text = json.dumps(args, ensure_ascii=False) if args or isinstance(raw_args, dict) else str(raw_args)
			record_normalized_tool_effects(self.root_p, step_idx, call.get('name', ''), raw_args, args_text, seg, track_turn_steps=True)
	def _resolve_subagent_child(self, child_cid, is_aa_hint, expected_parent, anchor_step, seg):
		r = None
		child_log = self.backend / 'brain' / child_cid / '.system_generated/logs/transcript_full.jsonl'
		if child_log.is_file():
			parent_mismatch, child_agent_name, db_grandchildren = self._query_child_summary(child_cid, expected_parent)
			if not parent_mismatch:
				try:
					c_rows = read_jsonl_objects(child_log)
					is_aa = 'self' == child_agent_name or (None is child_agent_name and bool(is_aa_hint))
					r = (c_rows, is_aa, db_grandchildren + _extract_subagent_uuids(c_rows), lambda cid, rows: self._record_subagent_calls(cid, rows, anchor_step, seg))
				except Exception:
					r = ([], False, (), None)
		return r
	def _scan_segment(self, position, start):
		end = self.boundaries[position + 1] if position + 1 < len(self.boundaries) else None
		segment = [row for row in self.rows if row.get('step_index', -1) > start and (None is end or row.get('step_index', -1) < end)]
		seg = init_turn_accumulator(extra={'issue_actions': [], 'spawned_subagents': 0, 'completed_subagents': 0, 'answer_prepared_in_segment': False})
		for pos, row in enumerate(segment):
			if isinstance(row, dict):
				step_idx = row.get('step_index')
				if 'CHECKPOINT' == row.get('type') and isinstance(step_idx, int):
					seg['checkpoint_steps'].append(step_idx)
				if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and re.search('<SYSTEM_MESSAGE>.*(?:\\bSubagent\\b.*\\bcompleted\\b|\\[Message\\]\\s+timestamp=[^\\n]+\\bsender=[0-9a-f]{8}-[0-9a-f]{4}-)', str(row.get('content') or ''), re.S | re.I):
					seg['completed_subagents'] += 1
				calls = [c for c in row.get('tool_calls') or [] if isinstance(c, dict)]
				if calls and isinstance(step_idx, int):
					self._record_tool_calls(step_idx, calls, self._collect_outputs(segment, pos, step_idx=step_idx, file_reads=seg['file_reads']), seg)
		return self._finalize_segment(start, end, segment, seg, self._collect_subagent_bfs(position, segment, seg))
	def scan(self):
		self._load_context()
		grouped, pending = ([], [])
		for turn in (self._scan_segment(position, start) for position, start in enumerate(self.boundaries)):
			if pending and pending[-1]['owned'] != turn['owned']:
				pending = []
			pending.append(turn)
			if turn['completed']:
				grouped.append(self._merge_pending(pending))
				pending = []
		if pending:
			grouped.append(self._merge_pending(pending))
		active = grouped[-1] if grouped and (not grouped[-1]['completed']) else None
		return {'platform': 'antigravity', 'conversation_id': self.conversation_id, 'native_backend': str(self.backend), 'source_file': str(self.path), 'primary': not bool(self.summary['parent_conversation_id']), 'turns': grouped, 'active_turn_id': active['turn_id'] if active else None}
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Canonicalize relocated Codex, Antigravity, and Harness project roots and support v2Migrated gitFolder project resources":
# https://github.com/dmitry-ai/harness/issues/29
def resource_uri(res):
	return extract_resource_uri(res)
def folder_path(uri):
	return local_uri_to_path(uri)
# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
def register_antigravity_project(project_dir, domain_or_topic, date_str=None, projects_dir=ANTIGRAVITY_PROJECTS_DIR, folders_json_path=ANTIGRAVITY_FOLDERS_JSON):
	root, projects = (Path(project_dir).resolve(), Path(projects_dir))
	day = request_day(date_str) if date_str else date(int(root.parents[2].name), int(root.parents[1].name), int(root.parent.name))
	name = f'{domain_or_topic} - U.P.{day:%Y.%m.%d}'
	with locked(projects / 'ꘖ' / 'data' / 'registration.lock'):
		folders = Path(folders_json_path)
		before = folders.read_bytes()
		listing = json.loads(before.decode('utf-8-sig'))
		nodes, assignments = (listing.get('folders'), listing.get('projectFolderMap'))
		if not isinstance(nodes, list) or not isinstance(assignments, dict):
			raise ValueError('Folders requires folders[] and projectFolderMap{}')
		branch = ('Upwork', 'Proposals', f'{day.year:04d}', f'{day.month:02d}', f'{day.day:02d}')
		parent = None
		for part in branch:
			node = next((x for x in nodes if x['name'].casefold() == part.casefold() and x.get('parentId') == parent), None)
			if None is node:
				node = {'id': f'folder-{uuid.uuid4().hex[:16]}', 'name': part, 'parentId': parent, 'color': '#10b981', 'isExpanded': True}
				nodes.append(node)
			parent = node['id']
		ident, payload, destination = (None, None, None)
		for path in projects.glob('*.json'):
			item = json.loads(path.read_text(encoding='utf-8-sig'))
			if any((resource_uri(res) and folder_path(resource_uri(res)) == root for res in (item.get('projectResources') or {}).get('resources') or [])):
				ident, payload, destination = (item.get('id') or path.stem, item, path)
				break
		if None is ident:
			ident = str(uuid.uuid4())
			destination = projects / f'{ident}.json'
			payload = {'id': ident, 'name': name, 'projectResources': {'resources': [{'folderUri': root.as_uri()}]}, 'settings': {}, 'isWorkspaceOnly': False}
			create_bytes(destination, json_bytes(payload))
		assignments[ident] = parent
		if folders.read_bytes() != before:
			raise RuntimeError('Folders changed concurrently; retry registration')
		if json_bytes(listing) != before:
			replace_bytes(folders, json_bytes(listing))
		if json.loads(folders.read_text(encoding='utf-8-sig'))['projectFolderMap'].get(ident) != parent:
			raise RuntimeError('Project folder assignment did not persist; retry registration')
		r = {'project_id': ident, 'project_name': payload['name'], 'project_file': str(destination), 'folder_id': parent, 'folder_path': ' / '.join(branch), 'folders_file': str(folders)}
	return r
def _apply_requested_config(requested, observed, raw_config, selection_kind, source):
	cfg = _configuration(raw_config)
	gen_match = _generation_matches_executor(observed['generation_model'], cfg['model'])
	requested.update(cfg, executor_model=cfg['model'], generation_model=observed['generation_model'] if gen_match else None, selection=selection_kind, source=source)
	if gen_match and observed['generation_model']:
		requested['model'] = observed['generation_model']
def _conversation_db_path(backend, conversation_id, *, error_msg='Exact native conversation UUID required'):
	if not re.fullmatch('[a-f0-9-]{36}', conversation_id):
		raise ValueError(error_msg)
	return backend / 'conversations' / (conversation_id + '.db')
def _wire_path(blob, path):
	values = [blob]
	for field in path:
		found = []
		for value in values:
			try:
				found.extend((part for number, kind, part in wire_fields(value or b'') if number == field and 2 == kind))
			except (ValueError, IndexError, TypeError):
				continue
		values = found
	r = []
	for value in values:
		try:
			text = value.decode('utf-8')
			if text.strip():
				r.append(text)
		except UnicodeError:
			pass
	return r
def _configuration(value):
	if not isinstance(value, str) or not value.strip():
		r = {'model': None, 'effort': None}
	else:
		match = re.fullmatch('(.+)-(minimal|low|medium|high|xhigh|max|ultra)', value)
		r = {'model': match[1], 'effort': match[2]} if match else {'model': value, 'effort': None}
	return r
def _decode_user_step(payload, status, index, load_transcript):
	r = None
	try:
		messages = [val for field, kind, val in wire_fields(payload or b'') if 19 == field and 2 == kind]
		if messages:
			msg_fields = list(wire_fields(messages[0]))
			texts = [val.decode('utf-8') for field, kind, val in msg_fields if 2 == field and 2 == kind and val.decode('utf-8').strip()]
			if not texts and 5 == status:
				texts = _wire_path(messages[0], (3, 1))
			if texts:
				r = texts[0]
			else:
				medias = []
				for field, kind, val in msg_fields:
					if 9 == field and 2 == kind:
						m_fields = {mf: mv.decode('utf-8', 'replace') for mf, mk, mv in wire_fields(val) if 2 == mk and mf in (1, 4, 5)}
						uri = m_fields.get(5) or m_fields.get(4) or m_fields.get(1)
						if uri:
							medias.append(f'[Image: {uri}]')
				if medias:
					r = '\n'.join(medias)
	except (IndexError, UnicodeError):
		if 5 != status:
			raise ValueError('Exact native user text is unavailable; do not reconstruct it from summaries')
	if None is r and 5 == status:
		r = _extract_transcript_user_input(load_transcript().get(index))
	if None is r:
		raise ValueError('Exact native user text is unavailable; do not reconstruct it from summaries')
	return r
def _extract_transcript_user_input(t_row):
	r = None
	if isinstance(t_row, dict):
		raw = t_row.get('content')
		if isinstance(raw, str):
			m = re.search('<USER_REQUEST>\\r?\\n([\\s\\S]*?)\\r?\\n</USER_REQUEST>', raw)
			if m and m.group(1).strip():
				r = m.group(1)
			elif raw.strip() and '<USER_REQUEST>' not in raw:
				r = raw
		if None is r and isinstance(t_row.get('media'), list):
			uris = [f"[Image: {item['uri']}]" for item in t_row['media'] if isinstance(item, dict) and item.get('uri')]
			if uris:
				r = '\n'.join(uris)
	return r
def _find_subagent_invocations(parent_rows, child_id, agent_name, initial_prompt, *, require_inherit_error=None):
	matches, extra_messages = ([], [])
	for i, event in enumerate(parent_rows):
		for call in event.get('tool_calls', []):
			if 'send_message' == call.get('name'):
				args = parse_tool_args(call.get('args', {}))
				if args.get('Recipient') == child_id and isinstance(args.get('Message'), str):
					extra_messages.append(args['Message'])
			for sub in iter_antigravity_subagents(call):
				if sub.get('TypeName') == agent_name and sub.get('Prompt') and (sub['Prompt'] in initial_prompt):
					if None is not require_inherit_error and 'inherit' != sub.get('Model'):
						raise ValueError(require_inherit_error)
					matches.append((event.get('step_index'), sub, i + 1 < len(parent_rows) and child_id in parent_rows[i + 1].get('content', '')))
	return (matches, extra_messages)
def _generation_matches_executor(generation_model, executor_model):
	r = False
	if isinstance(generation_model, str) and generation_model.strip() and isinstance(executor_model, str) and executor_model.strip():
		g_val, e_val = (generation_model.strip(), executor_model.strip())
		r = g_val == e_val or g_val.startswith(e_val + '-')
	return r
def _load_transcript_inputs(backend, conversation_id):
	t_path = backend / 'brain' / conversation_id / '.system_generated/logs/transcript_full.jsonl'
	r = {}
	if t_path.is_file():
		try:
			r = {obj.get('step_index'): obj for obj in read_jsonl_objects(t_path) if isinstance(obj, dict) and 'USER_INPUT' == obj.get('type')}
		except (OSError, ValueError):
			r = {}
	return r
def _query_step_model_ids(backend, cid, *, step=None):
	r = set()
	with open_readonly_sqlite(_conversation_db_path(backend, cid)) as connection:
		if 'metadata' in {row[1] for row in connection.execute('PRAGMA table_info(steps)')}:
			for blob, in connection.execute('SELECT metadata FROM steps WHERE step_type=15 AND status IN (3,5)' + (' AND idx=?' if None is not step else ''), (step,) if None is not step else ()).fetchall():
				try:
					r.update((value for field, kind, value in wire_fields(blob or b'') if 11 == field and 0 == kind and value))
				except (ValueError, IndexError):
					r = set()
					break
	return r
def _model_metadata(backend, conversation_id):
	path = _conversation_db_path(backend, conversation_id)
	history, sources = ({'generations': [], 'configurations': [], 'model_ids': []}, [])
	with open_readonly_sqlite(path) as connection:
		tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
		for table, field_path, key in (('gen_metadata', (1, 19), 'generations'), ('executor_metadata', (10, 1, 28), 'configurations')):
			if table in tables and {'idx', 'data'}.issubset({row[1] for row in connection.execute('PRAGMA table_info(' + table + ')')}):
				for index, blob in connection.execute('SELECT idx,data FROM ' + table + ' ORDER BY idx'):
					values = _wire_path(blob, field_path)
					history[key].extend(({'index': index, 'value': v} for v in values))
					if values:
						sources.append({'native_file': str(path), 'table': table, 'row': index, 'protobuf_path': list(field_path), 'sha256': hashlib.sha256(blob or b'').hexdigest()})
		if 'metadata' in {row[1] for row in connection.execute('PRAGMA table_info(steps)')}:
			for index, blob in connection.execute('SELECT idx,metadata FROM steps WHERE step_type=15 AND status IN (3,5) ORDER BY idx'):
				try:
					history['model_ids'].extend(({'step': index, 'value': value} for field, kind, value in wire_fields(blob or b'') if 11 == field and 0 == kind and value))
				except (ValueError, IndexError):
					pass
	generation = history['generations'][-1]['value'] if history['generations'] else None
	config = history['configurations'][-1]['value'] if history['configurations'] else None
	configured = _configuration(config)
	return ({'model': generation, 'generation_model': generation, 'executor_model': configured['model'], 'effort': configured['effort'], 'configuration': config, 'model_ids': sorted({item['value'] for item in history['model_ids']})}, history, sources)
def _native_invocation(backend, parent_id, conversation_id, role):
	child_log = backend / 'brain' / conversation_id / '.system_generated/logs/transcript_full.jsonl'
	parent_log = backend / 'brain' / parent_id / '.system_generated/logs/transcript_full.jsonl'
	initial = next((item.get('content', '') for item in read_jsonl_objects(child_log)), '')
	with open_readonly_sqlite(backend / 'conversation_summaries.db') as connection:
		row = connection.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
	if None is row or row[0] != parent_id or row[1] != platform_settings('antigravity')['roles'][role]['agent']:
		raise ValueError('Native child relationship/role is not established')
	matches, _ = _find_subagent_invocations(read_jsonl_objects(parent_log), conversation_id, row[1], initial)
	if not matches:
		raise ValueError('Matching native child invocation not established')
	exact_matches = [m for m in matches if m[2]]
	index, invocation = exact_matches[-1][:2] if exact_matches else matches[-1][:2]
	return (invocation, {'native_file': str(parent_log), 'step': index, 'kind': 'invoke_subagent'})
def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, backend=None):
	if role not in ('primary', 'AA', 'AF'):
		raise ValueError('Unknown executor role')
	backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
	observed, history, sources = _model_metadata(backend, conversation_id)
	requested = {'model': None, 'generation_model': None, 'executor_model': None, 'effort': None, 'selection': 'unavailable', 'source': None}
	if 'primary' == role and observed['configuration']:
		_apply_requested_config(requested, observed, observed['configuration'], 'native-executor-configuration', next((item for item in reversed(sources) if 'executor_metadata' == item.get('table')), None))
	elif 'primary' != role:
		if not parent_id or parent_id == conversation_id:
			raise ValueError('Exact parent required for AA/AF metadata')
		invocation, source = _native_invocation(backend, parent_id, conversation_id, role)
		selection = invocation.get('Model')
		if 'inherit' != selection:
			_apply_requested_config(requested, observed, selection, 'explicit-parent-invocation', source)
		else:
			parent_observed, parent_history, _ = _model_metadata(backend, parent_id)
			if 1 == len({item['value'] for item in parent_history['generations']}):
				requested['model'], requested['generation_model'] = (parent_observed['model'], parent_observed['generation_model'])
			if 1 == len({item['value'] for item in parent_history['configurations']}):
				requested['effort'], requested['executor_model'] = (parent_observed['effort'], parent_observed['executor_model'])
			requested.update(selection='inherit', source=source)
	force_mismatch = ('inherit' == requested.get('selection') and bool(requested.get('executor_model') and observed.get('executor_model') and (requested['executor_model'] != observed['executor_model']))) or bool(observed['configuration'] and observed['model'] and (not _generation_matches_executor(observed['model'], _configuration(observed['configuration'])['model'])))
	return finalize_executor_checks('antigravity-ui', role, conversation_id, parent_id, requested, observed, history, sources, 'Native generation model and executor configuration fields; exact API execution internals and missing modes are not inferred from runtime', force_model_mismatch=force_mismatch)
def native_tool_trace(root, request):
	backend = Path.home() / '.gemini/antigravity'
	conversation_id = request.get('conversation_id', '')
	database = _conversation_db_path(backend, conversation_id)
	with open_readonly_sqlite(database) as connection:
		statuses = {index: status for index, status in connection.execute('SELECT idx,status FROM steps')}
	path = backend / 'brain' / conversation_id / '.system_generated/logs/transcript_full.jsonl'
	raw = path.read_bytes()
	rows = read_jsonl_objects(raw)
	selected = request.get('step_indices')
	if not isinstance(selected, list) or not selected or any((type(x) is not int for x in selected)) or (len(set(selected)) != len(selected)):
		raise ValueError('Exact unique Antigravity native invocation step indices required')
	events = []
	for index in selected:
		matches = [position for position, row in enumerate(rows) if row.get('step_index') == index]
		if 1 != len(matches):
			raise ValueError('Native invocation step is missing/ambiguous')
		position = matches[0]
		row = rows[position]
		calls = row.get('tool_calls', [])
		if 1 != len(calls):
			raise ValueError('Select a native step containing exactly one tool call; multi-call results cannot be safely attributed')
		following = []
		for candidate in rows[position + 1:]:
			if candidate.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT'):
				break
			if 'GENERIC' == candidate.get('type'):
				following.append(candidate)
		if not following or any((candidate.get('error') for candidate in following)):
			raise ValueError('Native tool has no attributable successful result')
		output = following[-1]
		if 3 != statuses.get(output.get('step_index')):
			raise ValueError('Native database does not confirm successful tool completion')
		call = calls[0]
		arguments = parse_tool_args(call.get('args', {})) if isinstance(call.get('args', {}), (dict, str)) else {}
		events.append(make_tool_trace_event(str(index), index, output['step_index'], call.get('name', ''), arguments, output.get('content', ''), True, row.get('created_at'), output.get('created_at'), {'call': call, 'output': {'step_index': output.get('step_index'), 'content': output.get('content'), 'created_at': output.get('created_at')}}))
	return {'surface': 'antigravity-ui', 'conversation_id': conversation_id, 'step_indices': selected, 'native_database': str(database), 'native_log': str(path), 'native_log_sha256': hashlib.sha256(raw).hexdigest(), 'events': events}
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def native_review_proof(root, parent_id, reviewer_id, *, backend=None, write=True):
	root = Path(root).resolve()
	backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
	if not all((re.fullmatch('[a-f0-9-]{36}', x) for x in (parent_id, reviewer_id))):
		raise ValueError('Native parent/reviewer UUIDs required')
	with open_readonly_sqlite(backend / 'conversation_summaries.db', row_factory=sqlite3.Row) as conn:
		child = conn.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (reviewer_id,)).fetchone()
	if None is child or child['parent_conversation_id'] != parent_id or 'self' != child['agent_name']:
		raise ValueError('Native trace does not establish an independent self/A.A child of this parent')
	log = backend / 'brain' / reviewer_id / '.system_generated/logs/transcript_full.jsonl'
	raw = log.read_bytes()
	rows = read_jsonl_objects(raw)
	last = rows[-1] if rows else {}
	if 'PLANNER_RESPONSE' != last.get('type') or last.get('tool_calls') or (not last.get('content', '').strip()):
		raise ValueError('Reviewer has no successful final response in the native trace')
	with open_readonly_sqlite(_conversation_db_path(backend, reviewer_id)) as conn:
		final = conn.execute('SELECT idx,step_type,status FROM steps ORDER BY idx DESC LIMIT 1').fetchone()
	if not final or final[0] != last['step_index'] or 15 != final[1] or (final[2] not in COMPLETED_STEP_STATUSES):
		raise ValueError('Native database reports an unfinished/failed later reviewer step')
	parent_log = backend / 'brain' / parent_id / '.system_generated/logs/transcript_full.jsonl'
	parent_inputs = read_jsonl_objects(parent_log)
	initial_prompt = rows[0].get('content', '')
	matches, extra_msgs = _find_subagent_invocations(parent_inputs, reviewer_id, 'self', initial_prompt, require_inherit_error='Native A.A reviewer was not requested with the inherited parent model')
	if not matches:
		raise ValueError('Matching native self/inherit invocation is not established')
	exact_matches = [m for m in matches if m[2]]
	invocation = exact_matches[-1][0] if exact_matches else matches[0][0]
	def _extra():
		require_current_binding(root, parent_id, backend=backend, inputs=[(item.get('step_index', index), item['content']) for index, item in enumerate(parent_inputs) if 'USER_INPUT' == item.get('type') and isinstance(item.get('content'), str)], until=invocation)
		parent_models, child_models = (_query_step_model_ids(backend, parent_id, step=invocation), _query_step_model_ids(backend, reviewer_id))
		if parent_models and child_models and (not child_models.issubset(parent_models)):
			raise ValueError('Observed reviewer model differs from the inherited A.A model')
		executor_metadata = native_executor_metadata(root, reviewer_id, role='AA', parent_id=parent_id, backend=backend)
		if 'mismatch' == executor_metadata['verification']['status']:
			raise ValueError('Native reviewer generation/configuration differs from requested inherited model/effort')
		return {'model_verification': executor_metadata['verification']['status'] + ': native generation/executor fields', 'executor_metadata': executor_metadata, 'observed_model_ids': sorted(child_models), 'invocation_step': invocation}
	return build_native_review_proof(root, 'antigravity-ui', parent_id, reviewer_id, 'self', log, parent_log, raw, last['step_index'], last['content'], [initial_prompt, *extra_msgs, *(m[1]['Prompt'] for m in matches)], rows, extra_fields_fn=_extra, write=write)
def wire_fields(data):
	def number(offset):
		value, shift = (0, 0)
		while True:
			byte = data[offset]
			offset += 1
			value |= (byte & 127) << shift
			if 128 > byte:
				return (value, offset)
			shift += 7
			if 70 < shift:
				raise ValueError('Unsupported native protobuf varint')
	offset, r = (0, [])
	while offset < len(data):
		tag, offset = number(offset)
		field, kind = (tag >> 3, tag & 7)
		if not field:
			raise ValueError('Unsupported native protobuf field')
		if 0 == kind:
			value, offset = number(offset)
		elif 2 == kind:
			size, offset = number(offset)
			value = data[offset:offset + size]
			offset += size
			if len(value) != size:
				raise ValueError('Native protobuf field is truncated')
		elif kind not in (1, 5):
			raise ValueError('Unsupported native protobuf encoding')
		else:
			size = 8 if 1 == kind else 4
			value = data[offset:offset + size]
			offset += size
		r.append((field, kind, value))
	return r
def _native_inputs(backend, conversation_id):
	db_path = _conversation_db_path(backend, conversation_id, error_msg='Exact current native conversation UUID required')
	with open_readonly_sqlite(db_path) as conn:
		rows = conn.execute('SELECT idx,status,step_format,step_payload FROM steps WHERE step_type=14 AND status IN (3,5) ORDER BY idx').fetchall()
	cache = {}
	r = []
	for index, status, format_id, payload in rows:
		if 0 != format_id:
			raise ValueError('Native request format is unsupported; save exact requests from the current chat, without reconstruction')
		r.append((index, _decode_user_step(payload, status, index, lambda: cache.setdefault('rows', _load_transcript_inputs(backend, conversation_id)))))
	return r
def _project_roots(backend, project_id):
	r = []
	if isinstance(project_id, str) and project_id.strip() and project_id not in ('outside-of-project', 'default-cli-project'):
		from .request_binding import canonical_path
		candidate = Path(backend).resolve().parent / 'config/projects' / f'{project_id}.json'
		if candidate.is_file():
			try:
				data = json.loads(candidate.read_text(encoding='utf-8-sig'))
				r = [canonical_path(folder_path(resource_uri(res))) for res in (data.get('projectResources') or {}).get('resources') or [] if resource_uri(res)]
			except Exception:
				r = []
	return r
def _workspace_context(backend, conversation_id):
	file = backend / 'conversation_summaries.db'
	r = []
	if file.is_file():
		with open_readonly_sqlite(file) as conn:
			columns = {row[1] for row in conn.execute('PRAGMA table_info(conversation_summaries)')}
			has_ws = 'workspace_uris' in columns
			row = conn.execute('SELECT workspace_uris, project_id FROM conversation_summaries WHERE conversation_id=?' if 'project_id' in columns else 'SELECT workspace_uris, NULL FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone() if has_ws else None
		if has_ws:
			roots = json.loads(row[0]) if row and row[0] else []
			project_id = row[1] if row and 1 < len(row) else None
			if not isinstance(roots, list) or any((not isinstance(root, str) or not root.startswith('file://') for root in roots)):
				raise ValueError('Native Antigravity workspace_uris format is unsupported')
			from .request_binding import canonical_path
			p_roots = _project_roots(backend, project_id)
			if not roots:
				r = [(-1, str(p_roots[0]), 'antigravity-project-id')] if 1 == len(p_roots) else []
			elif 1 < len(roots):
				r = [(-1, None, 'antigravity-workspace-uris')]
			else:
				w_path = canonical_path(folder_path(roots[0]))
				target = p_roots[0] if not w_path.exists() and 1 == len(p_roots) and p_roots[0].exists() else w_path
				r = [(-1, str(target), 'antigravity-project-id' if target != w_path else 'antigravity-workspace-uris')]
	return r
def _request_scope(root, conversation_id, backend, *, inputs=None, until=None, identifier=None):
	from .request_binding import native_project_id, scoped_inputs
	job_id = identifier if None is not identifier else native_project_id(root)
	return scoped_inputs(root, job_id, _native_inputs(backend, conversation_id) if None is inputs else inputs, _workspace_context(backend, conversation_id), until=until)
def native_requests(root, conversation_id, *, backend=None):
	backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
	selected, _, _ = _request_scope(root, conversation_id, backend)
	return current_turn_requests(selected, conversation_id, 'antigravity-ui', 'Native requests do not identify this project; say "Continue analysis. Project root: `<absolute path>`"')
def require_current_binding(root, conversation_id, *, backend=None, inputs=None, until=None):
	backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
	selected, active, binding = _request_scope(root, conversation_id, backend, inputs=inputs, until=until)
	return require_turn_binding(selected, active, binding, 'Native Antigravity conversation is currently bound to another project or no exact project root')
def _extract_subagent_uuids(rows_slice: list) -> list[str]:
	r: list[str] = []
	rows_list = rows_slice if isinstance(rows_slice, list) else []
	uuid_re = re.compile(f'\\b({UUID_PATTERN})\\b', re.I)
	for pos, ev in enumerate(rows_list):
		if not isinstance(ev, dict):
			continue
		content = str(ev.get('content') or '')
		if ev.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and re.match('^\\s*(?:The following is a <SYSTEM_MESSAGE>[^\\n]*\\n+\\s*)?<SYSTEM_MESSAGE>', content):
			sys_header = re.split('\\bcontent=', content, maxsplit=1)[0]
			for m_u in re.findall(f'\\[Message\\]\\s+timestamp=[^\\n]*?\\bsender=({UUID_PATTERN})\\b', sys_header, flags=re.I) + re.findall(f'\\bSubagent\\b[^\\n]{{0,80}}?\\b({UUID_PATTERN})\\b', sys_header, flags=re.I):
				if m_u.lower() not in r:
					r.append(m_u.lower())
		calls = [c for c in ev.get('tool_calls') or [] if isinstance(c, dict)]
		has_invoke = any(('invoke_subagent' == c.get('name') for c in calls))
		for call in calls:
			if 'send_message' == call.get('name'):
				recip = str(parse_tool_args(call.get('args', {})).get('Recipient') or '').strip().lower()
				if re.fullmatch(UUID_PATTERN, recip) and recip not in r:
					r.append(recip)
		if has_invoke:
			for cand in rows_list[pos + 1:]:
				if not isinstance(cand, dict):
					continue
				if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
					break
				if 'GENERIC' == cand.get('type') and cand.get('content'):
					cand_text = str(cand.get('content'))
					if not re.search('(?:^|\\n)(?:File Path:\\s*`?file://|Showing lines \\d+-\\d+ of \\d+|Partial read \\(lines \\d+-\\d+ of \\d+\\)|Command exited with code \\d+\\.|Tool is running as a background task)', cand_text):
						invoke_matches = re.findall(f'"(?:conversationId|agent_id|subagent_id)"\\s*:\\s*"({UUID_PATTERN})"', cand_text, flags=re.I) + re.findall(f'\\b(?:Subagents?|subagents?|workers?|coordinators?)\\b[^\\n]{{0,80}}?\\b({UUID_PATTERN})\\b', cand_text, flags=re.I)
						if not invoke_matches and re.fullmatch(f'\\s*({UUID_PATTERN})\\s*', cand_text, flags=re.I):
							invoke_matches = uuid_re.findall(cand_text)
						for m_u in invoke_matches:
							if m_u.lower() not in r:
								r.append(m_u.lower())
	return r
def native_answers(root, conversation_id, *, backend=None):
	return AntigravityTurnScanner(root, conversation_id, backend=backend).scan()
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def verify_native_proof(root, native, package=None):
	r = verify_review_proof_core(root, native, native_review_proof(root, native.get('parent_id', ''), native.get('reviewer_id', ''), write=False), ('native_log_sha256', 'final_response_sha256', 'final_step', 'job_id'), allow_legacy_generation_model=True)
	if package:
		with Path(r['native_log']).open(encoding='utf-8') as stream:
			prompt = json.loads(stream.readline()).get('content', '')
		if package not in prompt:
			raise ValueError('Native reviewer was not assigned this immutable KB review package')
	return r
def register(project_dir, domain_or_topic, date_str=None):
	return register_antigravity_project(project_dir, domain_or_topic, date_str)
