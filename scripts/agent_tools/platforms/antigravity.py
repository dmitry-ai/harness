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
from urllib.parse import unquote
import hashlib
import json
import re
import sqlite3
import uuid
from ..runtime import platform_settings, request_day
from ..research import json_data
from ..knowledge import json_bytes
from ..storage import create_bytes, replace_bytes, locked
from .request_binding import native_project_fields
from .trace_common import collect_prompt_bias_issues, collect_subagent_bfs, current_turn_requests, finalize_executor_checks, init_turn_accumulator, iter_antigravity_subagents, merge_turn_accumulators, parse_tool_args, partial_candidate_read_issues as _partial_candidate_read_issues, persist_review_proof, prompt_bias_issues, record_normalized_tool_effects, require_turn_binding, reviewer_isolation_issues, verify_review_proof_core
ANTIGRAVITY_PROJECTS_DIR = Path.home() / '.gemini/config/projects'
ANTIGRAVITY_FOLDERS_JSON = Path(platform_settings('antigravity')['folders_json'])
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
					p_conn = sqlite3.connect((self.backend / 'conversation_summaries.db').as_uri() + '?mode=ro', uri=True)
					try:
						for p_row in p_conn.execute('SELECT conversation_id FROM conversation_summaries WHERE parent_conversation_id=?', (self.conversation_id,)).fetchall():
							if p_row and p_row[0] and p_row[0] not in self.completed_turn_cids:
								seeds.append((p_row[0], bool(seg['aa_subagent_steps']), self.conversation_id))
					finally:
						p_conn.close()
				except Exception:
					pass
			anchor = seg['subagent_steps'][-1]
			r = collect_subagent_bfs(self.conversation_id, self.root_p, seeds, lambda cid, depth, hint, parent: self._resolve_subagent_child(cid, hint, parent, anchor, seg), seg['aa_partial_read_violations'])
		return r
	def _finalize_segment(self, start, end, segment, seg, visited_cids):
		last = segment[-1] if segment else {}
		final_step = last.get('step_index')
		final = 'PLANNER_RESPONSE' == last.get('type') and (not last.get('tool_calls')) and bool(last.get('content', '').strip()) and ((15, 3) == self.statuses.get(final_step))
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
		return {'turn_id': f'ag-{self.conversation_id}-{start}', 'requests': [self.requests[start]] if start in self.requests else [], 'owned': start in self.requests, 'completed': completed, 'aborted': False, 'response': resp_text, 'start_step': start, 'final_step': final_step if completed else None, 'completion_step': final_step if completed else None, 'exec5_violations': seg['exec5_violations'], 'http_fetch_violations': seg['http_fetch_violations'], 'checkpoint_steps': seg['checkpoint_steps'], 'tool_steps': seg['tool_steps'], 'subagent_steps': seg['subagent_steps'], 'aa_subagent_steps': seg['aa_subagent_steps'], 'aa_partial_read_violations': seg['aa_partial_read_violations'], 'af_subagent_steps': seg['af_subagent_steps'], 'kb_persistence_steps': seg['kb_persistence_steps'], 'completion_service_steps': seg['completion_service_steps'], 'transcript_read_steps': seg['transcript_read_steps'], 'tool_records': seg['tool_records'], 'touched_files': seg['touched_files'], 'file_reads': seg['file_reads'], 'file_writes': seg['file_writes'], 'issue_actions': seg['issue_actions']}
	def _load_context(self):
		from .request_binding import completion_project_id
		from ..journal import resolve_journal_dir, state_dir
		if not re.fullmatch('[a-f0-9-]{36}', self.conversation_id):
			raise ValueError('Exact native Antigravity conversation UUID required')
		connection = sqlite3.connect((self.backend / 'conversation_summaries.db').as_uri() + '?mode=ro', uri=True)
		connection.row_factory = sqlite3.Row
		try:
			summary = connection.execute('SELECT * FROM conversation_summaries WHERE conversation_id=?', (self.conversation_id,)).fetchone()
			self.summary = dict(summary) if None is not summary else None
		finally:
			connection.close()
		if None is self.summary or 'parent_conversation_id' not in self.summary:
			raise ValueError('Native Antigravity primary/child identity is unavailable')
		self.path = self.backend / 'brain' / self.conversation_id / '.system_generated/logs/transcript_full.jsonl'
		try:
			self.rows = [json.loads(line) for line in self.path.read_text(encoding='utf-8').split('\n') if line.strip()]
		except ValueError as exc:
			raise ValueError('Native Antigravity trace has a partial record; retry after flush') from exc
		self.inputs = _native_inputs(self.backend, self.conversation_id)
		selected, _, _ = _request_scope(self.root, self.conversation_id, self.backend, inputs=self.inputs, identifier=completion_project_id(self.root))
		self.requests = {index: {'id': f'{self.conversation_id}-{index}', 'text': text, 'native_step': index, 'project_binding': binding} for index, text, binding in selected}
		connection = sqlite3.connect((self.backend / 'conversations' / (self.conversation_id + '.db')).as_uri() + '?mode=ro', uri=True)
		try:
			self.statuses = {index: (kind, status) for index, kind, status in connection.execute('SELECT idx,step_type,status FROM steps')}
		finally:
			connection.close()
		self.jdir = resolve_journal_dir(self.root_p)
		sdir = state_dir(self.jdir)
		if (sdir / 'answer-groups').is_dir():
			for gpath in (sdir / 'answer-groups').glob('*.json'):
				try:
					g = json.loads(gpath.read_text(encoding='utf-8'))
					if 'complete' == g.get('status') and g.get('request_ids'):
						for rid, st in zip(g['request_ids'], g.get('steps', [])):
							self.journal_groups[rid] = (g, st)
				except Exception:
					pass
		self.boundaries = sorted((index for index, _ in self.inputs))
	def _merge_pending(self, items):
		return merge_turn_accumulators(items, allow_step_output_recovery=True)
	def _query_child_summary(self, child_cid, expected_parent):
		child_agent_name = None
		db_grandchildren = []
		parent_mismatch = False
		try:
			c_conn = sqlite3.connect((self.backend / 'conversation_summaries.db').as_uri() + '?mode=ro', uri=True)
			try:
				c_row = c_conn.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (child_cid,)).fetchone()
				if None is not c_row:
					if not c_row[0] or c_row[0] != expected_parent:
						parent_mismatch = True
					else:
						child_agent_name = c_row[1]
				if not parent_mismatch:
					db_grandchildren = [row[0] for row in c_conn.execute('SELECT conversation_id FROM conversation_summaries WHERE parent_conversation_id=?', (child_cid,)).fetchall() if row and row[0]]
			finally:
				c_conn.close()
		except Exception:
			pass
		return (parent_mismatch, child_agent_name, db_grandchildren)
	def _record_subagent_calls(self, child_cid, c_rows, anchor_step, seg):
		from ..git_gate import extract_issue_actions_from_outputs
		for c_pos, c_ev in enumerate(c_rows):
			if isinstance(c_ev, dict):
				c_calls = [c for c in c_ev.get('tool_calls') or [] if isinstance(c, dict)]
				if c_calls:
					c_outputs = self._collect_outputs(c_rows, c_pos)
					for act_item in extract_issue_actions_from_outputs(c_outputs):
						seg['issue_actions'].append({**act_item, 'step': anchor_step, 'subagent_id': child_cid})
					for c_call in c_calls:
						record_normalized_tool_effects(self.root_p, anchor_step, c_call.get('name', ''), c_call.get('args', {}), '', seg, extra_violation={'subagent_id': child_cid})
		return ()
	def _record_tool_calls(self, step_idx, calls, outputs, seg):
		from ..git_gate import extract_issue_actions_from_outputs
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
					c_rows = [json.loads(line) for line in child_log.read_text(encoding='utf-8').split('\n') if line.strip()]
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
			if not isinstance(row, dict):
				continue
			step_idx = row.get('step_index')
			if 'CHECKPOINT' == row.get('type') and isinstance(step_idx, int):
				seg['checkpoint_steps'].append(step_idx)
			if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and re.search('<SYSTEM_MESSAGE>.*(?:\\bSubagent\\b.*\\bcompleted\\b|\\[Message\\]\\s+timestamp=[^\\n]+\\bsender=[0-9a-f]{8}-[0-9a-f]{4}-)', str(row.get('content') or ''), re.S | re.I):
				seg['completed_subagents'] += 1
			calls = [c for c in row.get('tool_calls') or [] if isinstance(c, dict)]
			if calls and isinstance(step_idx, int):
				outputs = self._collect_outputs(segment, pos, step_idx=step_idx, file_reads=seg['file_reads'])
				self._record_tool_calls(step_idx, calls, outputs, seg)
		visited_cids = self._collect_subagent_bfs(position, segment, seg)
		return self._finalize_segment(start, end, segment, seg, visited_cids)
	def scan(self):
		self._load_context()
		raw_turns = [self._scan_segment(position, start) for position, start in enumerate(self.boundaries)]
		grouped, pending = ([], [])
		for turn in raw_turns:
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
	if not isinstance(res, dict):
		return None
	r = res.get('folderUri') or (res.get('gitFolder') or {}).get('folderUri') or (res.get('folder') or {}).get('folderUri')
	return r if isinstance(r, str) and r.strip() else None
def folder_path(uri):
	path = unquote(uri[7:]) if uri.startswith('file://') else uri
	if re.match('^/[A-Za-z]:/', path):
		path = path[1:]
	r = Path(path).resolve()
	return r
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
			resources = (item.get('projectResources') or {}).get('resources') or []
			if any((resource_uri(res) and folder_path(resource_uri(res)) == root for res in resources)):
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
		effective = json.loads(folders.read_text(encoding='utf-8-sig'))
		if effective['projectFolderMap'].get(ident) != parent:
			raise RuntimeError('Project folder assignment did not persist; retry registration')
		r = {'project_id': ident, 'project_name': payload['name'], 'project_file': str(destination), 'folder_id': parent, 'folder_path': ' / '.join(branch), 'folders_file': str(folders)}
	return r
def _native_database(backend, conversation_id):
	if not re.fullmatch('[a-f0-9-]{36}', conversation_id):
		raise ValueError('Exact native conversation UUID required')
	path = backend / 'conversations' / (conversation_id + '.db')
	r = (path, sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True))
	return r
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
	result = []
	for value in values:
		try:
			text = value.decode('utf-8')
			if text.strip():
				result.append(text)
		except UnicodeError:
			pass
	r = result
	return r
def _configuration(value):
	if not isinstance(value, str) or not value.strip():
		r = {'model': None, 'effort': None}
	else:
		match = re.fullmatch('(.+)-(minimal|low|medium|high|xhigh|max|ultra)', value)
		r = {'model': match[1], 'effort': match[2]} if match else {'model': value, 'effort': None}
	return r
def _generation_matches_executor(generation_model, executor_model):
	if not isinstance(generation_model, str) or not generation_model.strip() or (not isinstance(executor_model, str)) or (not executor_model.strip()):
		return False
	g_val = generation_model.strip()
	e_val = executor_model.strip()
	return g_val == e_val or g_val.startswith(e_val + '-')
def _model_metadata(backend, conversation_id):
	path, connection = _native_database(backend, conversation_id)
	history, sources = ({'generations': [], 'configurations': [], 'model_ids': []}, [])
	try:
		tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
		for table, field_path, key in (('gen_metadata', (1, 19), 'generations'), ('executor_metadata', (10, 1, 28), 'configurations')):
			if table not in tables:
				continue
			columns = {row[1] for row in connection.execute('PRAGMA table_info(' + table + ')')}
			if not {'idx', 'data'}.issubset(columns):
				continue
			for index, blob in connection.execute('SELECT idx,data FROM ' + table + ' ORDER BY idx'):
				values = _wire_path(blob, field_path)
				for value in values:
					history[key].append({'index': index, 'value': value})
				if values:
					sources.append({'native_file': str(path), 'table': table, 'row': index, 'protobuf_path': list(field_path), 'sha256': hashlib.sha256(blob or b'').hexdigest()})
		columns = {row[1] for row in connection.execute('PRAGMA table_info(steps)')}
		if 'metadata' in columns:
			for index, blob in connection.execute('SELECT idx,metadata FROM steps WHERE step_type=15 AND status=3 ORDER BY idx'):
				try:
					history['model_ids'].extend(({'step': index, 'value': value} for field, kind, value in wire_fields(blob or b'') if 11 == field and 0 == kind and value))
				except (ValueError, IndexError):
					pass
	finally:
		connection.close()
	generation = history['generations'][-1]['value'] if history['generations'] else None
	config = history['configurations'][-1]['value'] if history['configurations'] else None
	configured = _configuration(config)
	observed = {'model': generation, 'generation_model': generation, 'executor_model': configured['model'], 'effort': configured['effort'], 'configuration': config, 'model_ids': sorted({item['value'] for item in history['model_ids']})}
	r = (observed, history, sources)
	return r
def _native_invocation(backend, parent_id, conversation_id, role):
	child_log = backend / 'brain' / conversation_id / '.system_generated/logs/transcript_full.jsonl'
	parent_log = backend / 'brain' / parent_id / '.system_generated/logs/transcript_full.jsonl'
	initial = next((json.loads(line).get('content', '') for line in child_log.read_text(encoding='utf-8').splitlines() if line.strip()), '')
	connection = sqlite3.connect((backend / 'conversation_summaries.db').resolve().as_uri() + '?mode=ro', uri=True)
	try:
		row = connection.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
	finally:
		connection.close()
	expected_agent = platform_settings('antigravity')['roles'][role]['agent']
	if None is row or row[0] != parent_id or row[1] != expected_agent:
		raise ValueError('Native child relationship/role is not established')
	matches = []
	lines = [json.loads(line) for line in parent_log.read_text(encoding='utf-8').splitlines() if line.strip()]
	for i, event in enumerate(lines):
		for call in event.get('tool_calls', []):
			for sub in iter_antigravity_subagents(call):
				if sub.get('TypeName') == row[1] and sub.get('Prompt') and (sub['Prompt'] in initial):
					exact = i + 1 < len(lines) and conversation_id in lines[i + 1].get('content', '')
					matches.append((event.get('step_index'), sub, exact))
	if not matches:
		raise ValueError('Matching native child invocation not established')
	exact_matches = [m for m in matches if m[2]]
	index, invocation = exact_matches[-1][:2] if exact_matches else matches[-1][:2]
	r = (invocation, {'native_file': str(parent_log), 'step': index, 'kind': 'invoke_subagent'})
	return r
def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, backend=None):
	if role not in ('primary', 'AA', 'AF'):
		raise ValueError('Unknown executor role')
	backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
	observed, history, sources = _model_metadata(backend, conversation_id)
	requested = {'model': None, 'generation_model': None, 'executor_model': None, 'effort': None, 'selection': 'unavailable', 'source': None}
	if 'primary' == role and observed['configuration']:
		cfg = _configuration(observed['configuration'])
		gen_match = _generation_matches_executor(observed['generation_model'], cfg['model'])
		requested.update(cfg, executor_model=cfg['model'], generation_model=observed['generation_model'] if gen_match else None, selection='native-executor-configuration', source=next((item for item in reversed(sources) if 'executor_metadata' == item.get('table')), None))
		if gen_match and observed['generation_model']:
			requested['model'] = observed['generation_model']
	elif 'primary' != role:
		if not parent_id or parent_id == conversation_id:
			raise ValueError('Exact parent required for AA/AF metadata')
		invocation, source = _native_invocation(backend, parent_id, conversation_id, role)
		selection = invocation.get('Model')
		if 'inherit' != selection:
			cfg = _configuration(selection)
			gen_match = _generation_matches_executor(observed['generation_model'], cfg['model'])
			requested.update(cfg, executor_model=cfg['model'], generation_model=observed['generation_model'] if gen_match else None, selection='explicit-parent-invocation', source=source)
			if gen_match and observed['generation_model']:
				requested['model'] = observed['generation_model']
		else:
			parent_observed, parent_history, _ = _model_metadata(backend, parent_id)
			if 1 == len({item['value'] for item in parent_history['generations']}):
				requested['model'] = parent_observed['model']
				requested['generation_model'] = parent_observed['generation_model']
			if 1 == len({item['value'] for item in parent_history['configurations']}):
				requested['effort'] = parent_observed['effort']
				requested['executor_model'] = parent_observed['executor_model']
			requested.update(selection='inherit', source=source)
	force_mismatch = ('inherit' == requested.get('selection') and bool(requested.get('executor_model') and observed.get('executor_model') and (requested['executor_model'] != observed['executor_model']))) or bool(observed['configuration'] and observed['model'] and (not _generation_matches_executor(observed['model'], _configuration(observed['configuration'])['model'])))
	return finalize_executor_checks('antigravity-ui', role, conversation_id, parent_id, requested, observed, history, sources, 'Native generation model and executor configuration fields; exact API execution internals and missing modes are not inferred from runtime', force_model_mismatch=force_mismatch)
def native_tool_trace(root, request):
	backend = Path.home() / '.gemini/antigravity'
	conversation_id = request.get('conversation_id', '')
	database, connection = _native_database(backend, conversation_id)
	try:
		statuses = {index: status for index, status in connection.execute('SELECT idx,status FROM steps')}
	finally:
		connection.close()
	path = backend / 'brain' / conversation_id / '.system_generated/logs/transcript_full.jsonl'
	raw = path.read_bytes()
	rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
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
		arguments = call.get('args', {})
		if isinstance(arguments, str):
			try:
				arguments = json.loads(arguments)
			except ValueError:
				arguments = {}
		selected_data = {'call': call, 'output': {'step_index': output.get('step_index'), 'content': output.get('content'), 'created_at': output.get('created_at')}}
		events.append({'id': str(index), 'step': index, 'output_step': output['step_index'], 'name': call.get('name', ''), 'arguments': arguments, 'result': output.get('content', ''), 'successful': True, 'created_at': row.get('created_at'), 'completed_at': output.get('created_at'), 'native_event_sha256': hashlib.sha256(json_data(selected_data)).hexdigest()})
	r = {'surface': 'antigravity-ui', 'conversation_id': conversation_id, 'step_indices': selected, 'native_database': str(database), 'native_log': str(path), 'native_log_sha256': hashlib.sha256(raw).hexdigest(), 'events': events}
	return r
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def native_review_proof(root, parent_id, reviewer_id, *, backend=None, write=True):
	root = Path(root).resolve()
	backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
	if not all((re.fullmatch('[a-f0-9-]{36}', x) for x in (parent_id, reviewer_id))):
		raise ValueError('Native parent/reviewer UUIDs required')
	conn = sqlite3.connect((backend / 'conversation_summaries.db').resolve().as_uri() + '?mode=ro', uri=True)
	conn.row_factory = sqlite3.Row
	try:
		child = conn.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (reviewer_id,)).fetchone()
	finally:
		conn.close()
	if None is child or child['parent_conversation_id'] != parent_id or 'self' != child['agent_name']:
		raise ValueError('Native trace does not establish an independent self/A.A child of this parent')
	log = backend / 'brain' / reviewer_id / '.system_generated/logs/transcript_full.jsonl'
	rows = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines() if line.strip()]
	last = rows[-1] if rows else {}
	if 'PLANNER_RESPONSE' != last.get('type') or last.get('tool_calls') or (not last.get('content', '').strip()):
		raise ValueError('Reviewer has no successful final response in the native trace')
	conn = sqlite3.connect((backend / 'conversations' / (reviewer_id + '.db')).resolve().as_uri() + '?mode=ro', uri=True)
	try:
		final = conn.execute('SELECT idx,step_type,status FROM steps ORDER BY idx DESC LIMIT 1').fetchone()
	finally:
		conn.close()
	if not final or final[0] != last['step_index'] or 15 != final[1] or (3 != final[2]):
		raise ValueError('Native database reports an unfinished/failed later reviewer step')
	parent_log = backend / 'brain' / parent_id / '.system_generated/logs/transcript_full.jsonl'
	parent_inputs = [json.loads(line) for line in parent_log.read_text(encoding='utf-8').splitlines() if line.strip()]
	initial_prompt = rows[0].get('content', '')
	invocation = None
	exact_invocation = None
	matched_prompts = [initial_prompt]
	for p_idx, row in enumerate(parent_inputs):
		for call in row.get('tool_calls', []):
			if 'send_message' == call.get('name'):
				args = parse_tool_args(call.get('args', {}))
				if args.get('Recipient') == reviewer_id and isinstance(args.get('Message'), str):
					matched_prompts.append(args['Message'])
			for sub in iter_antigravity_subagents(call):
				if 'self' == sub.get('TypeName') and sub.get('Prompt') and (sub['Prompt'] in initial_prompt):
					if 'inherit' != sub.get('Model'):
						raise ValueError('Native A.A reviewer was not requested with the inherited parent model')
					if p_idx + 1 < len(parent_inputs) and reviewer_id in parent_inputs[p_idx + 1].get('content', ''):
						exact_invocation = row['step_index']
					elif None is invocation:
						invocation = row['step_index']
					matched_prompts.append(sub['Prompt'])
	if None is not exact_invocation:
		invocation = exact_invocation
	if None is invocation:
		raise ValueError('Matching native self/inherit invocation is not established')
	bias_issues = collect_prompt_bias_issues(matched_prompts)
	if bias_issues:
		raise ValueError('Reviewer prompt biases verdict or omits negative schema outcomes: ' + '; '.join(bias_issues))
	isolation_issues = reviewer_isolation_issues(root, rows)
	if isolation_issues:
		raise ValueError('Independent reviewer isolation violated: ' + '; '.join(isolation_issues))
	require_current_binding(root, parent_id, backend=backend, inputs=[(item.get('step_index', index), item['content']) for index, item in enumerate(parent_inputs) if 'USER_INPUT' == item.get('type') and isinstance(item.get('content'), str)], until=invocation)
	def observed_models(cid, step=None):
		database = backend / 'conversations' / (cid + '.db')
		connection = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
		try:
			columns = {r[1] for r in connection.execute('PRAGMA table_info(steps)')}
			if 'metadata' not in columns:
				ids = set()
			else:
				metadata = connection.execute('SELECT metadata FROM steps WHERE step_type=15 AND status=3' + (' AND idx=?' if None is not step else ''), (step,) if None is not step else ()).fetchall()
				ids = set()
				for blob, in metadata:
					try:
						ids.update((value for field, kind, value in wire_fields(blob or b'') if 11 == field and 0 == kind and value))
					except (ValueError, IndexError):
						ids = set()
						break
		finally:
			connection.close()
		return ids
	parent_models, child_models = (observed_models(parent_id, invocation), observed_models(reviewer_id))
	if parent_models and child_models and (not child_models.issubset(parent_models)):
		raise ValueError('Observed reviewer model differs from the inherited A.A model')
	executor_metadata = native_executor_metadata(root, reviewer_id, role='AA', parent_id=parent_id, backend=backend)
	if 'mismatch' == executor_metadata['verification']['status']:
		raise ValueError('Native reviewer generation/configuration differs from requested inherited model/effort')
	digest = hashlib.sha256(log.read_bytes()).hexdigest()
	proof = {'surface': 'antigravity-ui', 'parent_id': parent_id, 'reviewer_id': reviewer_id, 'agent_name': 'self', 'status': 'completed', 'model_verification': executor_metadata['verification']['status'] + ': native generation/executor fields', 'executor_metadata': executor_metadata, 'observed_model_ids': sorted(child_models), 'invocation_step': invocation, 'native_log': str(log), 'native_log_sha256': digest, 'final_step': last['step_index'], 'final_response_sha256': hashlib.sha256(last['content'].encode()).hexdigest(), 'final_response': last['content'], 'parent_log': str(parent_log), **native_project_fields(root)}
	return persist_review_proof(root, reviewer_id, digest, last['content'], proof, write=write)
def wire_fields(data):
	def number(offset):
		value, shift = (0, 0)
		while True:
			byte = data[offset]
			offset += 1
			value |= (byte & 127) << shift
			if byte < 128:
				return (value, offset)
			shift += 7
			if shift > 70:
				raise ValueError('Unsupported native protobuf varint')
	offset, result = (0, [])
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
		result.append((field, kind, value))
	return result
def _native_inputs(backend, conversation_id):
	if not re.fullmatch('[a-f0-9-]{36}', conversation_id):
		raise ValueError('Exact current native conversation UUID required')
	conn = sqlite3.connect((backend / 'conversations' / (conversation_id + '.db')).resolve().as_uri() + '?mode=ro', uri=True)
	try:
		rows = conn.execute('SELECT idx,step_format,step_payload FROM steps WHERE step_type=14 AND status=3 ORDER BY idx').fetchall()
	finally:
		conn.close()
	inputs = []
	for index, format_id, payload in rows:
		if 0 != format_id:
			raise ValueError('Native request format is unsupported; save exact requests from the current chat, without reconstruction')
		try:
			message = next((value for field, kind, value in wire_fields(payload) if 19 == field and 2 == kind))
			msg_fields = list(wire_fields(message))
			texts = [value.decode('utf-8') for field, kind, value in msg_fields if 2 == field and 2 == kind and value.decode('utf-8').strip()]
			if texts:
				text = texts[0]
			else:
				medias = []
				for field, kind, value in msg_fields:
					if 9 == field and 2 == kind:
						m_fields = {mf: mv.decode('utf-8', 'replace') for mf, mk, mv in wire_fields(value) if 2 == mk and mf in (1, 4, 5)}
						uri = m_fields.get(5) or m_fields.get(4) or m_fields.get(1)
						if uri:
							medias.append(f'[Image: {uri}]')
				if not medias:
					raise StopIteration('No text or media in user message')
				text = '\n'.join(medias)
		except (IndexError, StopIteration, UnicodeError) as exc:
			raise ValueError('Exact native user text is unavailable; do not reconstruct it from summaries') from exc
		inputs.append((index, text))
	r = inputs
	return r
def _project_roots(backend, project_id):
	if not isinstance(project_id, str) or not project_id.strip() or project_id in ('outside-of-project', 'default-cli-project'):
		return []
	from .request_binding import canonical_path
	candidate = Path(backend).resolve().parent / 'config/projects' / f'{project_id}.json'
	if not candidate.is_file():
		return []
	try:
		data = json.loads(candidate.read_text(encoding='utf-8-sig'))
		resources = (data.get('projectResources') or {}).get('resources') or []
		r = [canonical_path(folder_path(resource_uri(res))) for res in resources if resource_uri(res)]
	except Exception:
		r = []
	return r
def _workspace_context(backend, conversation_id):
	file = backend / 'conversation_summaries.db'
	if not file.is_file():
		return []
	conn = sqlite3.connect(file.resolve().as_uri() + '?mode=ro', uri=True)
	try:
		columns = {row[1] for row in conn.execute('PRAGMA table_info(conversation_summaries)')}
		if 'workspace_uris' not in columns:
			return []
		sel = 'SELECT workspace_uris, project_id FROM conversation_summaries WHERE conversation_id=?' if 'project_id' in columns else 'SELECT workspace_uris, NULL FROM conversation_summaries WHERE conversation_id=?'
		row = conn.execute(sel, (conversation_id,)).fetchone()
	finally:
		conn.close()
	roots = json.loads(row[0]) if row and row[0] else []
	project_id = row[1] if row and len(row) > 1 else None
	if not isinstance(roots, list) or any((not isinstance(root, str) or not root.startswith('file://') for root in roots)):
		raise ValueError('Native Antigravity workspace_uris format is unsupported')
	from .request_binding import canonical_path
	p_roots = _project_roots(backend, project_id)
	if not roots:
		return [(-1, str(p_roots[0]), 'antigravity-project-id')] if 1 == len(p_roots) else []
	if 1 == len(roots):
		w_path = canonical_path(folder_path(roots[0]))
		if not w_path.exists() and 1 == len(p_roots) and p_roots[0].exists():
			return [(-1, str(p_roots[0]), 'antigravity-project-id')]
		return [(-1, str(w_path), 'antigravity-workspace-uris')]
	return [(-1, None, 'antigravity-workspace-uris')]
def _request_scope(root, conversation_id, backend, *, inputs=None, until=None, identifier=None):
	from .request_binding import native_project_id, scoped_inputs
	job_id = identifier if None is not identifier else native_project_id(root)
	inputs = _native_inputs(backend, conversation_id) if None is inputs else inputs
	r = scoped_inputs(root, job_id, inputs, _workspace_context(backend, conversation_id), until=until)
	return r
def native_requests(root, conversation_id, *, backend=None):
	backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
	selected, _, _ = _request_scope(root, conversation_id, backend)
	return current_turn_requests(selected, conversation_id, 'antigravity-ui', 'Native requests do not identify this project; say "Continue analysis. Project root: `<absolute path>`"')
def require_current_binding(root, conversation_id, *, backend=None, inputs=None, until=None):
	backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
	selected, active, binding = _request_scope(root, conversation_id, backend, inputs=inputs, until=until)
	return require_turn_binding(selected, active, binding, 'Native Antigravity conversation is currently bound to another project or no exact project root')
def _extract_subagent_uuids(rows_slice: list) -> list[str]:
	found: list[str] = []
	rows_list = rows_slice if isinstance(rows_slice, list) else []
	uuid_re = re.compile('\\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\b', re.I)
	for pos, ev in enumerate(rows_list):
		if not isinstance(ev, dict):
			continue
		ev_type = ev.get('type')
		content = str(ev.get('content') or '')
		if ev_type in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and re.match('^\\s*(?:The following is a <SYSTEM_MESSAGE>[^\\n]*\\n+\\s*)?<SYSTEM_MESSAGE>', content):
			sys_header = re.split('\\bcontent=', content, maxsplit=1)[0]
			for m_u in re.findall('\\[Message\\]\\s+timestamp=[^\\n]*?\\bsender=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\b', sys_header, flags=re.I):
				u_low = m_u.lower()
				if u_low not in found:
					found.append(u_low)
			for m_u in re.findall('\\bSubagent\\b[^\\n]{0,80}?\\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\b', sys_header, flags=re.I):
				u_low = m_u.lower()
				if u_low not in found:
					found.append(u_low)
		calls = [c for c in ev.get('tool_calls') or [] if isinstance(c, dict)]
		if not calls:
			continue
		has_invoke = False
		for call in calls:
			c_name = call.get('name', '')
			if 'invoke_subagent' == c_name:
				has_invoke = True
			elif 'send_message' == c_name:
				c_args = parse_tool_args(call.get('args', {}))
				recip = str(c_args.get('Recipient') or '').strip().lower()
				if re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', recip) and recip not in found:
					found.append(recip)
		if has_invoke:
			for cand in rows_list[pos + 1:]:
				if not isinstance(cand, dict):
					continue
				if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
					break
				if 'GENERIC' == cand.get('type') and cand.get('content'):
					cand_text = str(cand.get('content'))
					if re.search('(?:^|\\n)(?:File Path:\\s*`?file://|Showing lines \\d+-\\d+ of \\d+|Partial read \\(lines \\d+-\\d+ of \\d+\\)|Command exited with code \\d+\\.|Tool is running as a background task)', cand_text):
						continue
					invoke_matches = (
						re.findall('"(?:conversationId|agent_id|subagent_id)"\\s*:\\s*"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"', cand_text, flags=re.I)
						+ re.findall('\\b(?:Subagents?|subagents?|workers?|coordinators?)\\b[^\\n]{0,80}?\\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\b', cand_text, flags=re.I)
					)
					if not invoke_matches and re.fullmatch('\\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\s*', cand_text, flags=re.I):
						invoke_matches = uuid_re.findall(cand_text)
					for m_u in invoke_matches:
						u_low = m_u.lower()
						if u_low not in found:
							found.append(u_low)
	return found
def native_answers(root, conversation_id, *, backend=None):
	return AntigravityTurnScanner(root, conversation_id, backend=backend).scan()
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def verify_native_proof(root, native, package=None):
	result = verify_review_proof_core(root, native, native_review_proof(root, native.get('parent_id', ''), native.get('reviewer_id', ''), write=False), ('native_log_sha256', 'final_response_sha256', 'final_step', 'job_id'), allow_legacy_generation_model=True)
	if package:
		with Path(result['native_log']).open(encoding='utf-8') as stream:
			prompt = json.loads(stream.readline()).get('content', '')
		if package not in prompt:
			raise ValueError('Native reviewer was not assigned this immutable KB review package')
	return result
def register(project_dir, domain_or_topic, date_str=None):
	return register_antigravity_project(project_dir, domain_or_topic, date_str)
