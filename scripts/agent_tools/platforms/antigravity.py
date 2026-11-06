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
ANTIGRAVITY_PROJECTS_DIR = Path.home() / '.gemini/config/projects'
ANTIGRAVITY_FOLDERS_JSON = Path(platform_settings('antigravity')['folders_json'])
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
	observed = {'model': generation, 'effort': configured['effort'], 'configuration': config, 'model_ids': sorted({item['value'] for item in history['model_ids']})}
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
			if 'invoke_subagent' != call.get('name'):
				continue
			args = call.get('args', {})
			if isinstance(args, str):
				try:
					args = json.loads(args)
				except ValueError:
					continue
			subs = args.get('Subagents', []) if isinstance(args, dict) else []
			if isinstance(subs, str):
				try:
					subs = json.loads(subs)
				except ValueError:
					continue
			if not subs and isinstance(args, dict):
				subs = [args]
			for sub in subs if isinstance(subs, list) else []:
				if isinstance(sub, dict) and sub.get('TypeName') == row[1] and sub.get('Prompt') and (sub['Prompt'] in initial):
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
	requested = {'model': None, 'effort': None, 'selection': 'unavailable', 'source': None}
	if 'primary' == role and observed['configuration']:
		requested.update(_configuration(observed['configuration']), selection='native-executor-configuration', source=next((item for item in reversed(sources) if 'executor_metadata' == item.get('table')), None))
	elif 'primary' != role:
		if not parent_id or parent_id == conversation_id:
			raise ValueError('Exact parent required for AA/AF metadata')
		invocation, source = _native_invocation(backend, parent_id, conversation_id, role)
		selection = invocation.get('Model')
		if 'inherit' != selection:
			requested.update(_configuration(selection), selection='explicit-parent-invocation', source=source)
		else:
			parent_observed, parent_history, _ = _model_metadata(backend, parent_id)
			if 1 == len({item['value'] for item in parent_history['generations']}):
				requested['model'] = parent_observed['model']
			if 1 == len({item['value'] for item in parent_history['configurations']}):
				requested['effort'] = parent_observed['effort']
			requested.update(selection='inherit', source=source)
	checks = {}
	for key in ('model', 'effort'):
		checks[key] = 'unverified' if not requested.get(key) or not observed.get(key) else 'verified' if requested[key] == observed[key] else 'mismatch'
	if observed['configuration'] and observed['model'] and (_configuration(observed['configuration'])['model'] != observed['model']):
		checks['model'] = 'mismatch'
	status = 'mismatch' if 'mismatch' in checks.values() else 'verified' if set(checks.values()) == {'verified'} else 'unverified'
	r = {'schema_version': 1, 'surface': 'antigravity-ui', 'role': role, 'conversation_id': conversation_id, 'parent_id': parent_id, 'requested': requested, 'observed': observed, 'observation_history': history, 'metadata_sources': sources, 'verification': {'status': status, **checks, 'detail': 'Native generation model and executor configuration fields; exact API execution internals and missing modes are not inferred from runtime'}}
	return r
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
def prompt_bias_issues(prompt_text):
	if not isinstance(prompt_text, str) or not prompt_text.strip():
		r = []
	else:
		issues = []
		if re.search('["\\\']approved["\\\']|\\bresult["\\\']?\\s*:\\s*["\\\']?approved\\b', prompt_text, re.I) and (not re.search('\\bneeds_changes\\b', prompt_text, re.I)):
			issues.append('prompt specifies result="approved" without "needs_changes"')
		if re.search('["\\\']supported["\\\']|\\boutcome["\\\']?\\s*:\\s*["\\\']?supported\\b', prompt_text, re.I) and (not (re.search('\\bqualified\\b', prompt_text, re.I) and re.search('\\bunsupported\\b', prompt_text, re.I))):
			issues.append('prompt specifies outcome="supported" without "qualified" and "unsupported"')
		if re.search('["\\\']direct["\\\']|\\brelationship["\\\']?\\s*:\\s*["\\\']?direct\\b', prompt_text, re.I) and (not (re.search('\\bproxy\\b', prompt_text, re.I) and re.search('\\birrelevant\\b', prompt_text, re.I))):
			issues.append('prompt specifies relationship="direct" without "proxy" and "irrelevant"')
		if re.search('["\\\']findings["\\\']\\s*:\\s*\\[\\s*\\]', prompt_text) and (not (re.search('\\bseverity\\b', prompt_text, re.I) and re.search('\\bremediation\\b', prompt_text, re.I))):
			issues.append('prompt hardcodes empty findings=[] without specifying finding object fields')
		r = issues
	return r
def _partial_candidate_read_issues(project_root: Path, rows: list) -> list[str]:
	issues = []
	candidate_reads: dict[str, dict] = {}
	rows_list = rows if isinstance(rows, list) else []
	root_resolved = Path(project_root).resolve()
	for pos, row in enumerate(rows_list):
		if not isinstance(row, dict):
			continue
		for call in row.get('tool_calls', []) if isinstance(row.get('tool_calls'), list) else []:
			if not isinstance(call, dict):
				continue
			name = call.get('name', '')
			if name not in ('view_file', 'read_file'):
				continue
			args = call.get('args', {})
			if isinstance(args, str):
				try:
					args = json.loads(args)
				except ValueError:
					args = {}
			if not isinstance(args, dict):
				continue
			raw_path = str(args.get('AbsolutePath') or args.get('Path') or args.get('TargetFile') or '').strip()
			if not raw_path:
				continue
			norm_p = raw_path.replace('\\', '/').lower()
			is_cand = (
				norm_p.endswith(('/answer.md', '/candidate.md'))
				or '/reviews/candidates/' in norm_p
				or ('/data/scratch/' in norm_p and ('answer' in Path(norm_p).name or 'candidate' in Path(norm_p).name))
			)
			if not is_cand:
				continue
			try:
				p_obj = Path(raw_path)
				rp = p_obj.resolve() if p_obj.is_absolute() else (root_resolved / p_obj).resolve()
			except OSError:
				rp = Path(raw_path)
			key = rp.as_posix().lower()
			entry = candidate_reads.setdefault(key, {'path': rp, 'intervals': [], 'full_read': False, 'total_lines': 0})
			if rp.is_file():
				try:
					entry['total_lines'] = max(entry['total_lines'], len(rp.read_text(encoding='utf-8', errors='replace').splitlines()))
				except OSError:
					pass
			for nxt in rows_list[pos + 1:pos + 4]:
				if isinstance(nxt, dict) and 'GENERIC' == nxt.get('type'):
					m_tl = re.search('Total Lines:\\s*(\\d+)', str(nxt.get('content') or ''))
					if m_tl:
						entry['total_lines'] = max(entry['total_lines'], int(m_tl.group(1)))
			start_ln = args.get('StartLine')
			end_ln = args.get('EndLine')
			if None is start_ln and None is end_ln:
				entry['full_read'] = True
			else:
				s_val = int(start_ln) if isinstance(start_ln, int) or (isinstance(start_ln, str) and start_ln.isdigit()) else 1
				e_val = int(end_ln) if isinstance(end_ln, int) or (isinstance(end_ln, str) and end_ln.isdigit()) else max(entry['total_lines'], 800)
				entry['intervals'].append((s_val, e_val))
	for info in candidate_reads.values():
		if info['full_read']:
			continue
		total = info['total_lines']
		intervals = sorted(info['intervals'])
		if not intervals:
			continue
		merged = []
		for s_val, e_val in intervals:
			if not merged or s_val > merged[-1][1] + 1:
				merged.append([s_val, e_val])
			else:
				merged[-1][1] = max(merged[-1][1], e_val)
		min_s = merged[0][0]
		max_e = merged[-1][1]
		if total > 0 and (len(merged) > 1 or min_s > 1 or max_e < total):
			if len(merged) > 1:
				issues.append(f'reviewer performed a partial/truncated read of candidate response {info["path"].name} (non-contiguous intervals {merged} of {total})')
			else:
				issues.append(f'reviewer performed a partial/truncated read of candidate response {info["path"].name} (lines {min_s}-{max_e} of {total})')
		elif 0 == total and (len(merged) > 1 or (max_e <= 100 and min_s == 1)):
			issues.append(f'reviewer performed a partial/truncated read of candidate response {info["path"].name} (lines {min_s}-{max_e})')
	return issues
def reviewer_isolation_issues(root, rows):
	project_root = Path(root).resolve()
	daily_root = next((p for p in project_root.parents if 'daily' == p.name), project_root.parent)
	issues = []
	for row in rows if isinstance(rows, list) else []:
		for call in row.get('tool_calls', []) if isinstance(row, dict) else []:
			if not isinstance(call, dict):
				continue
			name = call.get('name', '')
			args = call.get('args', {})
			if isinstance(args, str):
				try:
					args = json.loads(args)
				except ValueError:
					args = {}
			if not isinstance(args, dict):
				args = {}
			if name in ('write_to_file', 'replace_file_content', 'multi_replace_file_content'):
				issues.append(f'reviewer called mutating tool {name}')
			if 'run_command' == name:
				cmd = str(args.get('CommandLine', ''))
				if re.search('(?i)\\b(?:Set-Content|Out-File|Add-Content)\\b|\\.(?:write_text|write_bytes)\\b|\\bgen_review', cmd):
					issues.append('reviewer executed a file-writing command or ad-hoc generator script')
			for key in ('AbsolutePath', 'TargetFile', 'DirectoryPath', 'SearchPath', 'Cwd'):
				val = args.get(key)
				if not isinstance(val, str) or not val.strip():
					continue
				try:
					candidate = Path(val).resolve()
				except OSError:
					continue
				if candidate.is_relative_to(daily_root) and (not candidate.is_relative_to(project_root)) and (not project_root.is_relative_to(candidate)):
					issues.append(f'reviewer accessed sibling project path {candidate}')
	issues.extend(_partial_candidate_read_issues(project_root, rows))
	r = issues
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
				args = call.get('args', {})
				if isinstance(args, dict) and args.get('Recipient') == reviewer_id and isinstance(args.get('Message'), str):
					matched_prompts.append(args['Message'])
			if 'invoke_subagent' != call.get('name'):
				continue
			subs = call.get('args', {}).get('Subagents', [])
			if isinstance(subs, str):
				try:
					subs = json.loads(subs)
				except ValueError:
					subs = []
			if not subs and isinstance(call.get('args'), dict):
				subs = [call['args']]
			for sub in subs if isinstance(subs, list) else []:
				if isinstance(sub, dict) and 'self' == sub.get('TypeName') and sub.get('Prompt') and (sub['Prompt'] in initial_prompt):
					if 'inherit' != sub.get('Model'):
						raise ValueError('Native A.A reviewer was not requested with the inherited parent model')
					is_exact = p_idx + 1 < len(parent_inputs) and reviewer_id in parent_inputs[p_idx + 1].get('content', '')
					if is_exact:
						exact_invocation = row['step_index']
					elif None is invocation:
						invocation = row['step_index']
					matched_prompts.append(sub['Prompt'])
	if None is not exact_invocation:
		invocation = exact_invocation
	if None is invocation:
		raise ValueError('Matching native self/inherit invocation is not established')
	bias_issues = []
	for prompt_text in matched_prompts:
		for issue in prompt_bias_issues(prompt_text):
			if issue not in bias_issues:
				bias_issues.append(issue)
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
				return set()
			metadata = connection.execute('SELECT metadata FROM steps WHERE step_type=15 AND status=3' + (' AND idx=?' if None is not step else ''), (step,) if None is not step else ()).fetchall()
			ids = set()
			for blob, in metadata:
				try:
					ids.update((value for field, kind, value in wire_fields(blob or b'') if 11 == field and 0 == kind and value))
				except (ValueError, IndexError):
					return set()
			return ids
		finally:
			connection.close()
	parent_models, child_models = (observed_models(parent_id, invocation), observed_models(reviewer_id))
	if parent_models and child_models and (not child_models.issubset(parent_models)):
		raise ValueError('Observed reviewer model differs from the inherited A.A model')
	executor_metadata = native_executor_metadata(root, reviewer_id, role='AA', parent_id=parent_id, backend=backend)
	if 'mismatch' == executor_metadata['verification']['status']:
		raise ValueError('Native reviewer generation/configuration differs from requested inherited model/effort')
	proof = {'surface': 'antigravity-ui', 'parent_id': parent_id, 'reviewer_id': reviewer_id, 'agent_name': 'self', 'status': 'completed', 'model_verification': executor_metadata['verification']['status'] + ': native generation/executor fields', 'executor_metadata': executor_metadata, 'observed_model_ids': sorted(child_models), 'invocation_step': invocation, 'native_log': str(log), 'native_log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(), 'final_step': last['step_index'], 'final_response_sha256': hashlib.sha256(last['content'].encode()).hexdigest(), 'final_response': last['content'], 'parent_log': str(parent_log), **native_project_fields(root)}
	target = Path(root) / 'ꘖ/KB/Evidence/Reviews' / (reviewer_id + '-' + proof['native_log_sha256'][:16] + '-native.json')
	authored = target.with_name(target.stem + '-authored.txt')
	proof['authored_response'] = authored.relative_to(Path(root).resolve()).as_posix()
	payload = json_data(proof)
	if not write:
		return {'proof': target.relative_to(Path(root).resolve()).as_posix(), **proof}
	target.parent.mkdir(parents=True, exist_ok=True)
	authored_bytes = last['content'].encode('utf-8')
	if authored.exists() and authored.read_bytes() != authored_bytes:
		raise ValueError('Immutable native authored response differs')
	if not authored.exists():
		create_bytes(authored, authored_bytes)
	if target.exists():
		if target.read_bytes() != payload:
			raise ValueError('Existing reviewer proof changed; preserve both and recheck native progress')
	else:
		create_bytes(target, payload)
	return {'proof': target.relative_to(Path(root).resolve()).as_posix(), **proof}
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
	if not selected:
		raise ValueError('Native requests do not identify this project; say "Continue analysis. Project root: `<absolute path>`"')
	r = [{'id': f'{conversation_id}-{index}', 'text': text, 'native_conversation_id': conversation_id, 'native_step': index, 'surface': 'antigravity-ui', 'project_binding': binding} for index, text, binding in selected]
	return r
def require_current_binding(root, conversation_id, *, backend=None, inputs=None, until=None):
	backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
	selected, active, binding = _request_scope(root, conversation_id, backend, inputs=inputs, until=until)
	if not selected or not active:
		raise ValueError('Native Antigravity conversation is currently bound to another project or no exact project root')
	r = binding
	return r
def native_answers(root, conversation_id, *, backend=None):
	from .request_binding import completion_project_id
	backend = Path(backend).resolve() if backend else Path.home() / '.gemini/antigravity'
	if not re.fullmatch('[a-f0-9-]{36}', conversation_id):
		raise ValueError('Exact native Antigravity conversation UUID required')
	connection = sqlite3.connect((backend / 'conversation_summaries.db').as_uri() + '?mode=ro', uri=True)
	connection.row_factory = sqlite3.Row
	try:
		summary = connection.execute('SELECT * FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
		summary = dict(summary) if None is not summary else None
	finally:
		connection.close()
	if None is summary or 'parent_conversation_id' not in summary:
		raise ValueError('Native Antigravity primary/child identity is unavailable')
	path = backend / 'brain' / conversation_id / '.system_generated/logs/transcript_full.jsonl'
	try:
		rows = [json.loads(line) for line in path.read_text(encoding='utf-8').split('\n') if line.strip()]
	except ValueError as exc:
		raise ValueError('Native Antigravity trace has a partial record; retry after flush') from exc
	inputs = _native_inputs(backend, conversation_id)
	selected, _, _ = _request_scope(root, conversation_id, backend, inputs=inputs, identifier=completion_project_id(root))
	requests = {index: {'id': f'{conversation_id}-{index}', 'text': text, 'native_step': index, 'project_binding': binding} for index, text, binding in selected}
	connection = sqlite3.connect((backend / 'conversations' / (conversation_id + '.db')).as_uri() + '?mode=ro', uri=True)
	try:
		statuses = {index: (kind, status) for index, kind, status in connection.execute('SELECT idx,step_type,status FROM steps')}
	finally:
		connection.close()
	from ..git_gate import extract_issue_actions_from_outputs, unflagged_git_read_commands, unpersisted_http_fetch_commands
	from ..journal import state_dir
	root_p = Path(root).resolve()
	jdir = (root_p / '_/ꙮ').resolve() if (root_p / '_/ꙮ').is_dir() else (root_p / 'ꙮ/1 - \u0410\u043d\u0430\u043b\u0438\u0437').resolve() if (root_p / 'ꙮ/1 - \u0410\u043d\u0430\u043b\u0438\u0437').is_dir() and (not (root_p / 'ꙮ/1 - Analysis').is_dir()) else (root_p / 'ꙮ').resolve() if (root_p / 'ꙮ/README.md').is_file() and (not (root_p / 'ꙮ/1 - Analysis').is_dir()) else (root_p / 'ꙮ/1 - Analysis').resolve()
	sdir = state_dir(jdir)
	journal_groups = {}
	if (sdir / 'answer-groups').is_dir():
		for gpath in (sdir / 'answer-groups').glob('*.json'):
			try:
				g = json.loads(gpath.read_text(encoding='utf-8'))
				if 'complete' == g.get('status') and g.get('request_ids'):
					for rid, st in zip(g['request_ids'], g.get('steps', [])):
						journal_groups[rid] = (g, st)
			except Exception:
				pass
	boundaries = sorted((index for index, _ in inputs))
	turns = []
	for position, start in enumerate(boundaries):
		end = boundaries[position + 1] if position + 1 < len(boundaries) else None
		segment = [row for row in rows if row.get('step_index', -1) > start and (None is end or row.get('step_index', -1) < end)]
		violations = []
		http_violations = []
		checkpoint_steps = []
		tool_steps = []
		subagent_steps = []
		aa_subagent_steps = []
		af_subagent_steps = []
		kb_persistence_steps = []
		transcript_read_steps = []
		tool_records = []
		touched_files = []
		file_reads = []
		file_writes = []
		issue_actions = []
		spawned_subagents = 0
		completed_subagents = 0
		answer_prepared_in_segment = False
		for pos, row in enumerate(segment):
			if not isinstance(row, dict):
				continue
			step_idx = row.get('step_index')
			if 'CHECKPOINT' == row.get('type') and isinstance(step_idx, int):
				checkpoint_steps.append(step_idx)
			if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and re.search('<SYSTEM_MESSAGE>.*(?:\\bSubagent\\b.*\\bcompleted\\b|\\[Message\\]\\s+timestamp=[^\\n]+\\bsender=[0-9a-f]{8}-[0-9a-f]{4}-)', str(row.get('content') or ''), re.S | re.I):
				completed_subagents += 1
			calls = [c for c in row.get('tool_calls') or [] if isinstance(c, dict)]
			if calls and isinstance(step_idx, int):
				tool_steps.append(step_idx)
				outputs = []
				for cand in segment[pos + 1:]:
					if not isinstance(cand, dict):
						continue
					if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
						break
					if 'GENERIC' == cand.get('type') and cand.get('content'):
						outputs.append(str(cand.get('content'))[:4000])
				tool_records.append({'step': step_idx, 'tools': [c.get('name', '') for c in calls], 'outputs': outputs})
				for act_item in extract_issue_actions_from_outputs(outputs):
					issue_actions.append({**act_item, 'step': step_idx})
				for call in calls:
					name = call.get('name', '')
					args = call.get('args', {})
					if isinstance(args, str):
						try:
							args = json.loads(args)
						except ValueError:
							args = {}
					args_text = json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else str(args)
					if 'run_command' == name:
						cmd = args.get('CommandLine', '') if isinstance(args, dict) else ''
						bad = unflagged_git_read_commands(cmd)
						if bad:
							violations.append({'step': step_idx, 'commands': bad})
						bad_http = unpersisted_http_fetch_commands(cmd)
						if bad_http:
							http_violations.append({'step': step_idx, 'commands': bad_http})
						if re.search('\\banswer-prepare\\b', cmd):
							answer_prepared_in_segment = True
					if any((tok in args_text for tok in ('transcript_full.jsonl', 'transcript.jsonl', 'recover-checkpoint'))):
						if step_idx not in transcript_read_steps:
							transcript_read_steps.append(step_idx)
					if 'invoke_subagent' == name:
						spawned_subagents += 1
						subs = args.get('Subagents', []) if isinstance(args, dict) else []
						if isinstance(subs, str):
							try:
								subs = json.loads(subs)
							except ValueError:
								subs = []
						if not subs and isinstance(args, dict):
							subs = [args]
						for sub in subs if isinstance(subs, list) else []:
							if isinstance(sub, dict):
								tname = str(sub.get('TypeName') or '').strip().lower()
								if 'self' == tname:
									if step_idx not in aa_subagent_steps:
										aa_subagent_steps.append(step_idx)
								elif tname:
									if step_idx not in af_subagent_steps:
										af_subagent_steps.append(step_idx)
					if name in ('invoke_subagent', 'send_message'):
						if step_idx not in subagent_steps:
							subagent_steps.append(step_idx)
					target_path = str(args.get('Path') or args.get('TargetFile') or args.get('AbsolutePath') or args.get('path') or '' if isinstance(args, dict) else '').strip()
					if name in ('read_file', 'view_file') and target_path:
						try:
							rp = Path(target_path)
							norm_rp = (rp.resolve() if rp.is_absolute() else (root_p / rp).resolve()).as_posix()
						except OSError:
							norm_rp = target_path.replace('\\', '/')
						file_reads.append((step_idx, norm_rp))
					if name in ('write_file', 'edit_file', 'write_to_file', 'replace_file_content', 'multi_replace_file_content') and target_path:
						if target_path not in touched_files:
							touched_files.append(target_path)
						try:
							wp = Path(target_path)
							norm_wp = (wp.resolve() if wp.is_absolute() else (root_p / wp).resolve()).as_posix()
						except OSError:
							norm_wp = target_path.replace('\\', '/')
						file_writes.append((step_idx, norm_wp))
					if name in ('write_file', 'edit_file', 'write_to_file', 'replace_file_content', 'multi_replace_file_content') and (any((tok in target_path for tok in ('\ua616/KB', '\ua616\\KB', '\\ua616/KB', '\\ua616\\\\KB'))) or target_path.replace('\\', '/').lower().endswith('/kb/analysis.md')) or ('run_command' == name and re.search('\\b(?:save-analysis|collect|collect-http|extract|extract-file|capture-dom)\\b', args_text)):
						if step_idx not in kb_persistence_steps:
							kb_persistence_steps.append(step_idx)
		aa_partial_read_violations = []
		if subagent_steps:
			visited_cids = {conversation_id}
			queued_set = set()
			queue_cids = []
			for s_row in segment:
				if isinstance(s_row, dict):
					for m_uuid in re.findall('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(s_row.get('content') or '')):
						if m_uuid not in visited_cids and m_uuid not in queued_set:
							queued_set.add(m_uuid)
							queue_cids.append((m_uuid, 1, bool(aa_subagent_steps)))
			while queue_cids:
				child_cid, depth, is_aa_hint = queue_cids.pop(0)
				if child_cid in visited_cids or depth > 4:
					continue
				child_log = backend / 'brain' / child_cid / '.system_generated/logs/transcript_full.jsonl'
				if not child_log.is_file():
					continue
				visited_cids.add(child_cid)
				child_agent_name = None
				try:
					c_conn = sqlite3.connect((backend / 'conversation_summaries.db').as_uri() + '?mode=ro', uri=True)
					try:
						c_row = c_conn.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (child_cid,)).fetchone()
						if None is not c_row:
							if c_row[0] and c_row[0] not in visited_cids:
								continue
							child_agent_name = c_row[1]
					finally:
						c_conn.close()
				except Exception:
					pass
				try:
					c_rows = [json.loads(line) for line in child_log.read_text(encoding='utf-8').split('\n') if line.strip()]
				except Exception:
					continue
				if 'self' == child_agent_name or (None is child_agent_name and is_aa_hint):
					for p_err in _partial_candidate_read_issues(root_p, c_rows):
						if p_err not in aa_partial_read_violations:
							aa_partial_read_violations.append(p_err)
				anchor_step = subagent_steps[-1]
				for c_pos, c_ev in enumerate(c_rows):
					if not isinstance(c_ev, dict):
						continue
					for m_sub_uuid in re.findall('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', str(c_ev.get('content') or '')):
						if m_sub_uuid not in visited_cids:
							queue_cids.append((m_sub_uuid, depth + 1, False))
					c_calls = [c for c in c_ev.get('tool_calls') or [] if isinstance(c, dict)]
					if not c_calls:
						continue
					c_outputs = []
					for c_cand in c_rows[c_pos + 1:]:
						if not isinstance(c_cand, dict):
							continue
						if c_cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
							break
						if 'GENERIC' == c_cand.get('type') and c_cand.get('content'):
							c_outputs.append(str(c_cand.get('content'))[:4000])
					for act_item in extract_issue_actions_from_outputs(c_outputs):
						issue_actions.append({**act_item, 'step': anchor_step, 'subagent_id': child_cid})
					for c_call in c_calls:
						c_name = c_call.get('name', '')
						c_args = c_call.get('args', {})
						if isinstance(c_args, str):
							try:
								c_args = json.loads(c_args)
							except ValueError:
								c_args = {}
						if 'run_command' == c_name and isinstance(c_args, dict):
							c_cmd = c_args.get('CommandLine', '')
							bad_g = unflagged_git_read_commands(c_cmd)
							if bad_g:
								violations.append({'step': anchor_step, 'subagent_id': child_cid, 'commands': bad_g})
							bad_h = unpersisted_http_fetch_commands(c_cmd)
							if bad_h:
								http_violations.append({'step': anchor_step, 'subagent_id': child_cid, 'commands': bad_h})
						c_target = str(c_args.get('Path') or c_args.get('TargetFile') or c_args.get('AbsolutePath') or c_args.get('path') or '' if isinstance(c_args, dict) else '').strip()
						if c_name in ('read_file', 'view_file') and c_target:
							try:
								crp = Path(c_target)
								norm_crp = (crp.resolve() if crp.is_absolute() else (root_p / crp).resolve()).as_posix()
							except OSError:
								norm_crp = c_target.replace('\\', '/')
							file_reads.append((anchor_step, norm_crp))
						if c_name in ('write_file', 'edit_file', 'write_to_file', 'replace_file_content', 'multi_replace_file_content') and c_target:
							if c_target not in touched_files:
								touched_files.append(c_target)
							try:
								cwp = Path(c_target)
								norm_cwp = (cwp.resolve() if cwp.is_absolute() else (root_p / cwp).resolve()).as_posix()
							except OSError:
								norm_cwp = c_target.replace('\\', '/')
							file_writes.append((anchor_step, norm_cwp))
		last = segment[-1] if segment else {}
		final_step = last.get('step_index')
		final = 'PLANNER_RESPONSE' == last.get('type') and (not last.get('tool_calls')) and bool(last.get('content', '').strip())
		final = final and statuses.get(final_step) == (15, 3)
		last_user_idx = summary.get('last_user_input_step_index')
		last_db_user = max((idx for idx, (stype, _) in statuses.items() if 14 == stype), default=start)
		idle = 'CASCADE_RUN_STATUS_IDLE' == summary.get('status') and 0 == summary.get('not_fully_idle') and (not summary.get('killed')) and (last_user_idx == start or (0 == start and last_user_idx == -1)) and (last_db_user == start) and (final_step == max(statuses, default=-1))
		req_id = f'{conversation_id}-{start}'
		j_entry = journal_groups.get(req_id)
		has_single_journal_group = None is not j_entry and 1 == len(j_entry[0].get('request_ids', []))
		last_text = str(last.get('content') or '')
		intermediate_wait = None is not end and (not answer_prepared_in_segment) and (not has_single_journal_group) and (completed_subagents < spawned_subagents or bool(re.search('(?i)(?:^|\\n)\\s*waiting\\s+for\\s+(?:the\\s+)?(?:remaining\\s+)?(?:\\d+\\s+)?(?:subagents?|background\\s+tasks?|tasks?|commands?)\\b[^\\n]{0,120}\\bto\\s+(?:complete|finish)\\b', last_text)))
		if intermediate_wait:
			completed = False
			resp_text = None
		elif None is not j_entry and (not final or 1 < len(j_entry[0].get('request_ids', []))):
			completed = req_id == j_entry[0]['request_ids'][-1] and (None is not end or idle)
			resp_text = (jdir / 'res' / f'{j_entry[1]}.md').read_bytes().decode('utf-8') if completed else None
		else:
			completed = bool(final and (None is not end or idle))
			resp_text = last.get('content') if completed else None
		turns.append({'turn_id': f'ag-{conversation_id}-{start}', 'requests': [requests[start]] if start in requests else [], 'owned': start in requests, 'completed': completed, 'aborted': False, 'response': resp_text, 'start_step': start, 'final_step': final_step if completed else None, 'completion_step': final_step if completed else None, 'exec5_violations': violations, 'http_fetch_violations': http_violations, 'checkpoint_steps': checkpoint_steps, 'tool_steps': tool_steps, 'subagent_steps': subagent_steps, 'aa_subagent_steps': aa_subagent_steps, 'aa_partial_read_violations': aa_partial_read_violations, 'af_subagent_steps': af_subagent_steps, 'kb_persistence_steps': kb_persistence_steps, 'transcript_read_steps': transcript_read_steps, 'tool_records': tool_records, 'touched_files': touched_files, 'file_reads': file_reads, 'file_writes': file_writes, 'issue_actions': issue_actions})
	def _merge_pending(items):
		first, last = (items[0], items[-1])
		cp_steps = [s for item in items for s in item.get('checkpoint_steps', [])]
		t_steps = [s for item in items for s in item.get('tool_steps', [])]
		sub_steps = [s for item in items for s in item.get('subagent_steps', [])]
		aa_steps = [s for item in items for s in item.get('aa_subagent_steps', [])]
		aa_part_errs = list(dict.fromkeys((e for item in items for e in item.get('aa_partial_read_violations', []))))
		af_steps = [s for item in items for s in item.get('af_subagent_steps', [])]
		kb_steps = [s for item in items for s in item.get('kb_persistence_steps', [])]
		tr_steps = [s for item in items for s in item.get('transcript_read_steps', [])]
		records = [r for item in items for r in item.get('tool_records', [])]
		t_files = list(dict.fromkeys((f for item in items for f in item.get('touched_files', []))))
		f_reads = [fr for item in items for fr in item.get('file_reads', [])]
		f_writes = [fw for item in items for fw in item.get('file_writes', [])]
		i_actions = [a for item in items for a in item.get('issue_actions', [])]
		last_cp = max(cp_steps) if cp_steps else None
		pre_cp_steps = [s for s in t_steps if None is not last_cp and s < last_cp]
		post_cp_rec = [s for s in tr_steps if None is not last_cp and s > last_cp]
		pre_cp_records = [r for r in records if None is not last_cp and r['step'] < last_cp]
		pre_cp_reads = list(dict.fromkeys((p for st, p in f_reads if None is not last_cp and st < last_cp)))
		post_cp_reads = list(dict.fromkeys((p for st, p in f_reads if None is not last_cp and st > last_cp)))
		post_cp_writes = list(dict.fromkeys((p for st, p in f_writes if None is not last_cp and st > last_cp)))
		post_cp_lower = {p.lower() for p in post_cp_reads}
		evicted_unreread = [p for p in pre_cp_reads if p.lower() not in post_cp_lower]
		reads_by_step = {}
		for st, p in f_reads:
			reads_by_step.setdefault(st, []).append(p)
		cur_streak = 0
		max_streak = 0
		cur_src_reads = set()
		max_src_reads = 0
		persist_or_sub = set(sub_steps) | set(kb_steps)
		for st in t_steps:
			if st in persist_or_sub:
				cur_streak = 0
				cur_src_reads.clear()
			else:
				cur_streak += 1
				if cur_streak > max_streak:
					max_streak = cur_streak
				for rp in reads_by_step.get(st, ()):
					if rp.lower().endswith('/kb/source.md'):
						cur_src_reads.add(rp.lower())
				if len(cur_src_reads) > max_src_reads:
					max_src_reads = len(cur_src_reads)
		merged = {**last, 'turn_id': first['turn_id'], 'start_step': first['start_step'], 'requests': [r for item in items for r in item['requests']], 'owned': all((item['owned'] for item in items)), 'exec5_violations': [v for item in items for v in item.get('exec5_violations', [])], 'http_fetch_violations': [v for item in items for v in item.get('http_fetch_violations', [])], 'touched_files': t_files, 'issue_actions': i_actions, 'compaction': {'occurred': bool(cp_steps), 'checkpoint_steps': cp_steps, 'last_checkpoint_step': last_cp, 'pre_checkpoint_tool_steps': pre_cp_steps, 'post_checkpoint_recovery_steps': post_cp_rec, 'recovered_in_trace': not cp_steps or not pre_cp_steps or bool(post_cp_rec), 'pre_checkpoint_records': pre_cp_records, 'pre_checkpoint_read_files': pre_cp_reads, 'post_checkpoint_read_files': post_cp_reads, 'post_checkpoint_written_files': post_cp_writes, 'evicted_unreread_files': evicted_unreread}, 'delegation': {'tool_step_count': len(t_steps), 'subagent_step_count': len(sub_steps), 'aa_subagent_step_count': len(aa_steps), 'aa_partial_read_violations': aa_part_errs, 'af_subagent_step_count': len(af_steps), 'kb_persistence_step_count': len(kb_steps), 'unpersisted_step_streak': cur_streak, 'max_unpersisted_step_streak': max_streak, 'max_unpersisted_source_reads': max_src_reads}}
		for k in ('checkpoint_steps', 'tool_steps', 'subagent_steps', 'aa_subagent_steps', 'aa_partial_read_violations', 'af_subagent_steps', 'kb_persistence_steps', 'transcript_read_steps', 'tool_records', 'file_reads', 'file_writes'):
			merged.pop(k, None)
		return merged
	grouped, pending = ([], [])
	for turn in turns:
		if pending and pending[-1]['owned'] != turn['owned']:
			pending = []
		pending.append(turn)
		if turn['completed']:
			grouped.append(_merge_pending(pending))
			pending = []
	if pending:
		grouped.append(_merge_pending(pending))
	turns = grouped
	active = turns[-1] if turns and (not turns[-1]['completed']) else None
	return {'platform': 'antigravity', 'conversation_id': conversation_id, 'native_backend': str(backend), 'source_file': str(path), 'primary': not bool(summary['parent_conversation_id']), 'turns': turns, 'active_turn_id': active['turn_id'] if active else None}
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
def verify_native_proof(root, native, package=None):
	result = native_review_proof(root, native.get('parent_id', ''), native.get('reviewer_id', ''), write=False)
	for field in ('native_log_sha256', 'final_response_sha256', 'final_step', 'job_id'):
		if native.get(field) != result.get(field):
			raise ValueError('Review proof differs from the current native trace')
	if 'client_text_workspace' == result['project_kind'] or any((key in native for key in ('project_id', 'project_kind'))):
		for key in ('project_id', 'project_kind'):
			if native.get(key) != result.get(key):
				raise ValueError('Review proof has a different explicit project identity')
	authored = Path(root) / result['authored_response']
	if authored.exists() and hashlib.sha256(authored.read_bytes()).hexdigest() != result['final_response_sha256']:
		raise ValueError('Immutable native authored reviewer response changed')
	if 'executor_metadata' in native and native['executor_metadata'] != result['executor_metadata']:
		raise ValueError('Native executor metadata differs from saved reviewer proof')
	if package:
		with Path(result['native_log']).open(encoding='utf-8') as stream:
			prompt = json.loads(stream.readline()).get('content', '')
		if package not in prompt:
			raise ValueError('Native reviewer was not assigned this immutable KB review package')
	r = result
	return r
def register(project_dir, domain_or_topic, date_str=None):
	return register_antigravity_project(project_dir, domain_or_topic, date_str)
