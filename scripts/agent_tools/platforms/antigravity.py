"""Antigravity-specific manifests, registrations and verified native traces."""
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

def folder_path(uri):
    path = unquote(uri[7:]) if uri.startswith('file://') else uri
    if re.match(r'^/[A-Za-z]:/', path):
        path = path[1:]
    return Path(path).resolve()


def register_antigravity_project(project_dir, domain_or_topic, date_str=None,
                                projects_dir=ANTIGRAVITY_PROJECTS_DIR,
                                folders_json_path=ANTIGRAVITY_FOLDERS_JSON):
    root, projects = Path(project_dir).resolve(), Path(projects_dir)
    day = request_day(date_str) if date_str else date(int(root.parents[2].name), int(root.parents[1].name), int(root.parent.name))
    name = f'{domain_or_topic} - U.P.{day:%Y.%m.%d}'
    with locked(projects / 'ꘖ' / 'data' / 'registration.lock'):
        folders = Path(folders_json_path)
        # Folders is our installed add-on, not a native Antigravity field.
        # Reject a missing/broken store before publishing an ungrouped project.
        before = folders.read_bytes()
        listing = json.loads(before.decode('utf-8-sig'))
        nodes, assignments = listing.get('folders'), listing.get('projectFolderMap')
        if not isinstance(nodes, list) or not isinstance(assignments, dict):
            raise ValueError('Folders requires folders[] and projectFolderMap{}')
        branch = ('Upwork', 'Proposals', f'{day.year:04d}', f'{day.month:02d}', f'{day.day:02d}')
        parent = None
        for part in branch:
            node = next((x for x in nodes if x['name'].casefold() == part.casefold()
                         and x.get('parentId') == parent), None)
            if node is None:
                node = {'id': f'folder-{uuid.uuid4().hex[:16]}', 'name': part,
                        'parentId': parent, 'color': '#10b981', 'isExpanded': True}
                nodes.append(node)
            parent = node['id']
        ident, payload, destination = None, None, None
        for path in projects.glob('*.json'):
            item = json.loads(path.read_text(encoding='utf-8-sig'))
            resources = (item.get('projectResources') or {}).get('resources') or []
            if any(res.get('folderUri') and folder_path(res['folderUri']) == root for res in resources):
                ident, payload, destination = item.get('id') or path.stem, item, path
                break
        if ident is None:
            ident = str(uuid.uuid4())
            destination = projects / f'{ident}.json'
            payload = {'id': ident, 'name': name,
                       'projectResources': {'resources': [{'folderUri': root.as_uri()}]},
                       'settings': {}, 'isWorkspaceOnly': False}
            create_bytes(destination, json_bytes(payload))
        assignments[ident] = parent
        if folders.read_bytes() != before:
            raise RuntimeError('Folders changed concurrently; retry registration')
        if json_bytes(listing) != before:
            replace_bytes(folders, json_bytes(listing))
        effective = json.loads(folders.read_text(encoding='utf-8-sig'))
        if effective['projectFolderMap'].get(ident) != parent:
            raise RuntimeError('Project folder assignment did not persist; retry registration')
        return {'project_id': ident, 'project_name': payload['name'], 'project_file': str(destination),
                'folder_id': parent, 'folder_path': ' / '.join(branch), 'folders_file': str(folders)}


def _native_database(backend, conversation_id):
    if not re.fullmatch(r'[a-f0-9-]{36}', conversation_id):
        raise ValueError('Exact native conversation UUID required')
    path = backend / 'conversations' / (conversation_id + '.db')
    return path, sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)


def _wire_path(blob, path):
    values = [blob]
    for field in path:
        found = []
        for value in values:
            try: found.extend(part for number, kind, part in wire_fields(value or b'') if number == field and kind == 2)
            except (ValueError, IndexError, TypeError): continue
        values = found
    result = []
    for value in values:
        try:
            text = value.decode('utf-8')
            if text.strip(): result.append(text)
        except UnicodeError: pass
    return result


def _configuration(value):
    """Split native configuration syntax, without a model-name lookup table."""
    if not isinstance(value, str) or not value.strip(): return {'model': None, 'effort': None}
    match = re.fullmatch(r'(.+)-(minimal|low|medium|high|xhigh|max|ultra)', value)
    return {'model': match[1], 'effort': match[2]} if match else {'model': value, 'effort': None}


def _model_metadata(backend, conversation_id):
    path, connection = _native_database(backend, conversation_id)
    history, sources = {'generations': [], 'configurations': [], 'model_ids': []}, []
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, field_path, key in (('gen_metadata', (1, 19), 'generations'), ('executor_metadata', (10, 1, 28), 'configurations')):
            if table not in tables: continue
            columns = {row[1] for row in connection.execute('PRAGMA table_info(' + table + ')')}
            if not {'idx', 'data'}.issubset(columns): continue
            for index, blob in connection.execute('SELECT idx,data FROM ' + table + ' ORDER BY idx'):
                values = _wire_path(blob, field_path)
                for value in values: history[key].append({'index': index, 'value': value})
                if values:
                    sources.append({'native_file': str(path), 'table': table, 'row': index,
                                    'protobuf_path': list(field_path), 'sha256': hashlib.sha256(blob or b'').hexdigest()})
        columns = {row[1] for row in connection.execute('PRAGMA table_info(steps)')}
        if 'metadata' in columns:
            for index, blob in connection.execute('SELECT idx,metadata FROM steps WHERE step_type=15 AND status=3 ORDER BY idx'):
                try:
                    history['model_ids'].extend({'step': index, 'value': value} for field, kind, value in wire_fields(blob or b'') if field == 11 and kind == 0 and value)
                except (ValueError, IndexError): pass
    finally: connection.close()
    generation = history['generations'][-1]['value'] if history['generations'] else None
    config = history['configurations'][-1]['value'] if history['configurations'] else None
    configured = _configuration(config)
    observed = {'model': generation, 'effort': configured['effort'], 'configuration': config,
                'model_ids': sorted({item['value'] for item in history['model_ids']})}
    return observed, history, sources


def _native_invocation(backend, parent_id, conversation_id, role):
    child_log = backend / 'brain' / conversation_id / '.system_generated/logs/transcript_full.jsonl'
    parent_log = backend / 'brain' / parent_id / '.system_generated/logs/transcript_full.jsonl'
    initial = next((json.loads(line).get('content', '') for line in child_log.read_text(encoding='utf-8').splitlines() if line.strip()), '')
    connection = sqlite3.connect((backend / 'conversation_summaries.db').resolve().as_uri() + '?mode=ro', uri=True)
    try:
        row = connection.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
    finally: connection.close()
    expected_agent = platform_settings('antigravity')['roles'][role]['agent']
    if row is None or row[0] != parent_id or row[1] != expected_agent:
        raise ValueError('Native child relationship/role is not established')
    matches = []
    lines = [json.loads(line) for line in parent_log.read_text(encoding='utf-8').splitlines() if line.strip()]
    for i, event in enumerate(lines):
        for call in event.get('tool_calls', []):
            if call.get('name') != 'invoke_subagent': continue
            args = call.get('args', {})
            if isinstance(args, str):
                try: args = json.loads(args)
                except ValueError: continue
            subs = args.get('Subagents', []) if isinstance(args, dict) else []
            if isinstance(subs, str):
                try: subs = json.loads(subs)
                except ValueError: continue
            if not subs and isinstance(args, dict):
                subs = [args]
            for sub in subs if isinstance(subs, list) else []:
                if isinstance(sub, dict) and sub.get('TypeName') == row[1] and sub.get('Prompt') and sub['Prompt'] in initial:
                    exact = i + 1 < len(lines) and conversation_id in lines[i + 1].get('content', '')
                    matches.append((event.get('step_index'), sub, exact))
    if not matches: raise ValueError('Matching native child invocation not established')
    exact_matches = [m for m in matches if m[2]]
    index, invocation = (exact_matches[-1][:2] if exact_matches else matches[-1][:2])
    return invocation, {'native_file': str(parent_log), 'step': index, 'kind': 'invoke_subagent'}


def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, backend=None):
    if role not in ('primary', 'AA', 'AF'): raise ValueError('Unknown executor role')
    backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
    observed, history, sources = _model_metadata(backend, conversation_id)
    requested = {'model': None, 'effort': None, 'selection': 'unavailable', 'source': None}
    if role == 'primary' and observed['configuration']:
        requested.update(_configuration(observed['configuration']), selection='native-executor-configuration',
                         source=next((item for item in reversed(sources) if item.get('table') == 'executor_metadata'), None))
    elif role != 'primary':
        if not parent_id or parent_id == conversation_id: raise ValueError('Exact parent required for AA/AF metadata')
        invocation, source = _native_invocation(backend, parent_id, conversation_id, role)
        selection = invocation.get('Model')
        if selection == 'inherit':
            parent_observed, parent_history, _ = _model_metadata(backend, parent_id)
            # Generation/config rows are not a per-step selection history. Only
            # a single observed parent configuration establishes inheritance;
            # mixed sessions retain their histories and remain unverified.
            if len({item['value'] for item in parent_history['generations']}) == 1:
                requested['model'] = parent_observed['model']
            if len({item['value'] for item in parent_history['configurations']}) == 1:
                requested['effort'] = parent_observed['effort']
            requested.update(selection='inherit', source=source)
        else:
            requested.update(_configuration(selection), selection='explicit-parent-invocation', source=source)
    checks = {}
    for key in ('model', 'effort'):
        checks[key] = ('unverified' if not requested.get(key) or not observed.get(key) else
                       'verified' if requested[key] == observed[key] else 'mismatch')
    if observed['configuration'] and observed['model'] and _configuration(observed['configuration'])['model'] != observed['model']:
        checks['model'] = 'mismatch'
    status = 'mismatch' if 'mismatch' in checks.values() else 'verified' if set(checks.values()) == {'verified'} else 'unverified'
    return {'schema_version': 1, 'surface': 'antigravity-ui', 'role': role, 'conversation_id': conversation_id,
            'parent_id': parent_id, 'requested': requested, 'observed': observed, 'observation_history': history,
            'metadata_sources': sources, 'verification': {'status': status, **checks,
                'detail': 'Native generation model and executor configuration fields; exact API execution internals and missing modes are not inferred from runtime'}}


def native_tool_trace(root, request):
    backend = Path.home() / '.gemini/antigravity'
    conversation_id = request.get('conversation_id', '')
    database, connection = _native_database(backend, conversation_id)
    try:
        statuses = {index: status for index, status in connection.execute('SELECT idx,status FROM steps')}
    finally: connection.close()
    path = backend / 'brain' / conversation_id / '.system_generated/logs/transcript_full.jsonl'
    raw = path.read_bytes()
    # Only explicit tool calls and tool-result fields are retained; thinking and
    # planner prose do not enter the evidence artifact.
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    selected = request.get('step_indices')
    if not isinstance(selected, list) or not selected or any(type(x) is not int for x in selected) or len(set(selected)) != len(selected):
        raise ValueError('Exact unique Antigravity native invocation step indices required')
    events = []
    for index in selected:
        matches = [position for position, row in enumerate(rows) if row.get('step_index') == index]
        if len(matches) != 1: raise ValueError('Native invocation step is missing/ambiguous')
        position = matches[0]; row = rows[position]; calls = row.get('tool_calls', [])
        if len(calls) != 1: raise ValueError('Select a native step containing exactly one tool call; multi-call results cannot be safely attributed')
        following = []
        for candidate in rows[position + 1:]:
            if candidate.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT'): break
            if candidate.get('type') == 'GENERIC': following.append(candidate)
        # Native step status 3 establishes completion. The last successful
        # GENERIC result in this tool interval is retained, without reasoning.
        if not following or any(candidate.get('error') for candidate in following):
            raise ValueError('Native tool has no attributable successful result')
        output = following[-1]
        if statuses.get(output.get('step_index')) != 3:
            raise ValueError('Native database does not confirm successful tool completion')
        call = calls[0]; arguments = call.get('args', {})
        if isinstance(arguments, str):
            try: arguments = json.loads(arguments)
            except ValueError: arguments = {}
        selected_data = {'call': call, 'output': {'step_index': output.get('step_index'), 'content': output.get('content'), 'created_at': output.get('created_at')}}
        events.append({'id': str(index), 'step': index, 'output_step': output['step_index'], 'name': call.get('name', ''),
                       'arguments': arguments, 'result': output.get('content', ''), 'successful': True,
                       'created_at': row.get('created_at'), 'completed_at': output.get('created_at'),
                       'native_event_sha256': hashlib.sha256(json_data(selected_data)).hexdigest()})
    return {'surface': 'antigravity-ui', 'conversation_id': conversation_id, 'step_indices': selected,
            'native_database': str(database), 'native_log': str(path),
            'native_log_sha256': hashlib.sha256(raw).hexdigest(), 'events': events}


def prompt_bias_issues(prompt_text):
    """Detect reviewer prompt poisoning where positive verdicts are specified without negative alternatives."""
    if not isinstance(prompt_text, str) or not prompt_text.strip():
        return []
    issues = []
    if re.search(r'["\']approved["\']|\bresult["\']?\s*:\s*["\']?approved\b', prompt_text, re.I) and not re.search(r'\bneeds_changes\b', prompt_text, re.I):
        issues.append('prompt specifies result="approved" without "needs_changes"')
    if re.search(r'["\']supported["\']|\boutcome["\']?\s*:\s*["\']?supported\b', prompt_text, re.I) and not (
            re.search(r'\bqualified\b', prompt_text, re.I) and re.search(r'\bunsupported\b', prompt_text, re.I)):
        issues.append('prompt specifies outcome="supported" without "qualified" and "unsupported"')
    if re.search(r'["\']direct["\']|\brelationship["\']?\s*:\s*["\']?direct\b', prompt_text, re.I) and not (
            re.search(r'\bproxy\b', prompt_text, re.I) and re.search(r'\birrelevant\b', prompt_text, re.I)):
        issues.append('prompt specifies relationship="direct" without "proxy" and "irrelevant"')
    if re.search(r'["\']findings["\']\s*:\s*\[\s*\]', prompt_text) and not (
            re.search(r'\bseverity\b', prompt_text, re.I) and re.search(r'\bremediation\b', prompt_text, re.I)):
        issues.append('prompt hardcodes empty findings=[] without specifying finding object fields')
    return issues


def reviewer_isolation_issues(root, rows):
    """Verify that an independent reviewer does not mutate files, run ad-hoc scripts, or inspect sibling projects."""
    project_root = Path(root).resolve()
    daily_root = next((p for p in project_root.parents if p.name == 'daily'), project_root.parent)
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
            if name == 'run_command':
                cmd = str(args.get('CommandLine', ''))
                if re.search(r'(?i)\b(?:Set-Content|Out-File|Add-Content)\b|\.(?:write_text|write_bytes)\b|\bgen_review', cmd):
                    issues.append('reviewer executed a file-writing command or ad-hoc generator script')
            for key in ('AbsolutePath', 'TargetFile', 'DirectoryPath', 'SearchPath', 'Cwd'):
                val = args.get(key)
                if not isinstance(val, str) or not val.strip():
                    continue
                try:
                    candidate = Path(val).resolve()
                except OSError:
                    continue
                if (candidate.is_relative_to(daily_root) and
                        not candidate.is_relative_to(project_root) and
                        not project_root.is_relative_to(candidate)):
                    issues.append(f'reviewer accessed sibling project path {candidate}')
    return issues


def native_review_proof(root, parent_id, reviewer_id, *, backend=None, write=True):
    """Require an actual child self conversation and its successful final native step."""
    root = Path(root).resolve()
    backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
    if not all(re.fullmatch(r'[a-f0-9-]{36}', x) for x in (parent_id, reviewer_id)):
        raise ValueError('Native parent/reviewer UUIDs required')
    conn = sqlite3.connect((backend / 'conversation_summaries.db').resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    try:
        child = conn.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (reviewer_id,)).fetchone()
    finally:
        conn.close()
    if child is None or child['parent_conversation_id'] != parent_id or child['agent_name'] != 'self':
        raise ValueError('Native trace does not establish an independent self/A.A child of this parent')
    log = backend / 'brain' / reviewer_id / '.system_generated/logs/transcript_full.jsonl'
    rows = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines() if line.strip()]
    last = rows[-1] if rows else {}
    if last.get('type') != 'PLANNER_RESPONSE' or last.get('tool_calls') or not last.get('content', '').strip():
        raise ValueError('Reviewer has no successful final response in the native trace')
    conn = sqlite3.connect((backend / 'conversations' / (reviewer_id + '.db')).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        final = conn.execute('SELECT idx,step_type,status FROM steps ORDER BY idx DESC LIMIT 1').fetchone()
    finally:
        conn.close()
    if not final or final[0] != last['step_index'] or final[1] != 15 or final[2] != 3:
        raise ValueError('Native database reports an unfinished/failed later reviewer step')
    parent_log = backend / 'brain' / parent_id / '.system_generated/logs/transcript_full.jsonl'
    parent_inputs = [json.loads(line) for line in parent_log.read_text(encoding='utf-8').splitlines() if line.strip()]
    initial_prompt = rows[0].get('content', '')
    invocation = None
    exact_invocation = None
    matched_prompts = [initial_prompt]
    for p_idx, row in enumerate(parent_inputs):
        for call in row.get('tool_calls', []):
            if call.get('name') == 'send_message':
                args = call.get('args', {})
                if isinstance(args, dict) and args.get('Recipient') == reviewer_id and isinstance(args.get('Message'), str):
                    matched_prompts.append(args['Message'])
            if call.get('name') != 'invoke_subagent':
                continue
            subs = call.get('args', {}).get('Subagents', [])
            if isinstance(subs, str):
                try: subs = json.loads(subs)
                except ValueError: subs = []
            if not subs and isinstance(call.get('args'), dict):
                subs = [call['args']]
            for sub in subs if isinstance(subs, list) else []:
                if isinstance(sub, dict) and sub.get('TypeName') == 'self' and sub.get('Prompt') and sub['Prompt'] in initial_prompt:
                    if sub.get('Model') != 'inherit':
                        raise ValueError('Native A.A reviewer was not requested with the inherited parent model')
                    is_exact = p_idx + 1 < len(parent_inputs) and reviewer_id in parent_inputs[p_idx + 1].get('content', '')
                    if is_exact:
                        exact_invocation = row['step_index']
                    elif invocation is None:
                        invocation = row['step_index']
                    matched_prompts.append(sub['Prompt'])
    if exact_invocation is not None:
        invocation = exact_invocation
    if invocation is None:
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
    require_current_binding(root, parent_id, backend=backend,
        inputs=[(item.get('step_index', index), item['content']) for index, item in enumerate(parent_inputs)
                if item.get('type') == 'USER_INPUT' and isinstance(item.get('content'), str)],
        until=invocation)
    def observed_models(cid, step=None):
        database = backend / 'conversations' / (cid + '.db')
        connection = sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            columns = {r[1] for r in connection.execute('PRAGMA table_info(steps)')}
            if 'metadata' not in columns:
                return set()
            metadata = connection.execute('SELECT metadata FROM steps WHERE step_type=15 AND status=3' + (' AND idx=?' if step is not None else ''), (step,) if step is not None else ()).fetchall()
            ids = set()
            for (blob,) in metadata:
                try:
                    ids.update(value for field, kind, value in wire_fields(blob or b'') if field == 11 and kind == 0 and value)
                except (ValueError, IndexError):
                    return set()
            return ids
        finally:
            connection.close()
    parent_models, child_models = observed_models(parent_id, invocation), observed_models(reviewer_id)
    if parent_models and child_models and not child_models.issubset(parent_models):
        raise ValueError('Observed reviewer model differs from the inherited A.A model')
    executor_metadata = native_executor_metadata(root, reviewer_id, role='AA', parent_id=parent_id, backend=backend)
    if executor_metadata['verification']['status'] == 'mismatch':
        raise ValueError('Native reviewer generation/configuration differs from requested inherited model/effort')
    proof = {'surface': 'antigravity-ui', 'parent_id': parent_id, 'reviewer_id': reviewer_id, 'agent_name': 'self',
             'status': 'completed', 'model_verification': executor_metadata['verification']['status'] + ': native generation/executor fields',
             'executor_metadata': executor_metadata,
             'observed_model_ids': sorted(child_models), 'invocation_step': invocation,
             'native_log': str(log), 'native_log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
             'final_step': last['step_index'], 'final_response_sha256': hashlib.sha256(last['content'].encode()).hexdigest(),
             'final_response': last['content'],
             'parent_log': str(parent_log), **native_project_fields(root)}
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
    if not authored.exists(): create_bytes(authored, authored_bytes)
    if target.exists():
        if target.read_bytes() != payload:
            raise ValueError('Existing reviewer proof changed; preserve both and recheck native progress')
    else:
        create_bytes(target, payload)
    return {'proof': target.relative_to(Path(root).resolve()).as_posix(), **proof}


def wire_fields(data):
    def number(offset):
        value, shift = 0, 0
        while True:
            byte = data[offset]; offset += 1; value |= (byte & 127) << shift
            if byte < 128: return value, offset
            shift += 7
            if shift > 70: raise ValueError('Unsupported native protobuf varint')
    offset, result = 0, []
    while offset < len(data):
        tag, offset = number(offset); field, kind = tag >> 3, tag & 7
        if not field: raise ValueError('Unsupported native protobuf field')
        if kind == 0: value, offset = number(offset)
        elif kind == 2:
            size, offset = number(offset); value = data[offset:offset + size]; offset += size
            if len(value) != size: raise ValueError('Native protobuf field is truncated')
        elif kind in (1, 5):
            size = 8 if kind == 1 else 4; value = data[offset:offset + size]; offset += size
        else: raise ValueError('Unsupported native protobuf encoding')
        result.append((field, kind, value))
    return result


def _native_inputs(backend, conversation_id):
    if not re.fullmatch(r'[a-f0-9-]{36}', conversation_id):
        raise ValueError('Exact current native conversation UUID required')
    conn = sqlite3.connect((backend / 'conversations' / (conversation_id + '.db')).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        rows = conn.execute('SELECT idx,step_format,step_payload FROM steps WHERE step_type=14 AND status=3 ORDER BY idx').fetchall()
    finally: conn.close()
    inputs = []
    for index, format_id, payload in rows:
        if format_id != 0:
            raise ValueError('Native request format is unsupported; save exact requests from the current chat, without reconstruction')
        try:
            message = next(value for field, kind, value in wire_fields(payload) if field == 19 and kind == 2)
            msg_fields = list(wire_fields(message))
            texts = [value.decode('utf-8') for field, kind, value in msg_fields if field == 2 and kind == 2 and value.decode('utf-8').strip()]
            if texts:
                text = texts[0]
            else:
                medias = []
                for field, kind, value in msg_fields:
                    if field == 9 and kind == 2:
                        m_fields = {mf: mv.decode('utf-8', 'replace') for mf, mk, mv in wire_fields(value) if mk == 2 and mf in (1, 4, 5)}
                        uri = m_fields.get(5) or m_fields.get(4) or m_fields.get(1)
                        if uri:
                            medias.append(f'[Image: {uri}]')
                if not medias:
                    raise StopIteration('No text or media in user message')
                text = '\n'.join(medias)
        except (IndexError, StopIteration, UnicodeError) as exc:
            raise ValueError('Exact native user text is unavailable; do not reconstruct it from summaries') from exc
        inputs.append((index, text))
    return inputs


def _workspace_context(backend, conversation_id):
    file = backend / 'conversation_summaries.db'
    if not file.is_file():
        return []
    conn = sqlite3.connect(file.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        columns = {row[1] for row in conn.execute('PRAGMA table_info(conversation_summaries)')}
        if 'workspace_uris' not in columns:
            return []
        row = conn.execute('SELECT workspace_uris FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
    finally:
        conn.close()
    roots = json.loads(row[0]) if row and row[0] else []
    if not isinstance(roots, list) or any(not isinstance(root, str) or not root.startswith('file://') for root in roots):
        raise ValueError('Native Antigravity workspace_uris format is unsupported')
    if not roots:
        return []
    # This native conversation field is not a per-step cwd history; multiple roots
    # cannot establish which particular project owns an otherwise unbound request.
    root = str(folder_path(roots[0])) if len(roots) == 1 else None
    return [(-1, root, 'antigravity-workspace-uris')]


def _request_scope(root, conversation_id, backend, *, inputs=None, until=None, identifier=None):
    from .request_binding import native_project_id, scoped_inputs
    job_id = identifier if identifier is not None else native_project_id(root)
    inputs = _native_inputs(backend, conversation_id) if inputs is None else inputs
    return scoped_inputs(root, job_id, inputs, _workspace_context(backend, conversation_id), until=until)


def native_requests(root, conversation_id, *, backend=None):
    """Exact USER_INPUT bytes, scoped by a native workspace or explicit user choice."""
    backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
    selected, _, _ = _request_scope(root, conversation_id, backend)
    if not selected:
        raise ValueError('Native requests do not identify this project; say "Продолжай анализ. Корень проекта: `<absolute path>`"')
    return [{'id': f'{conversation_id}-{index}', 'text': text,
             'native_conversation_id': conversation_id, 'native_step': index,
             'surface': 'antigravity-ui', 'project_binding': binding}
            for index, text, binding in selected]


def require_current_binding(root, conversation_id, *, backend=None, inputs=None, until=None):
    backend = Path(backend) if backend else Path.home() / '.gemini/antigravity'
    selected, active, binding = _request_scope(root, conversation_id, backend, inputs=inputs, until=until)
    if not selected or not active:
        raise ValueError('Native Antigravity conversation is currently bound to another project or no exact project root')
    return binding


def native_answers(root, conversation_id, *, backend=None):
    """Read public final planner steps, checking idle state for the live tail."""
    from .request_binding import completion_project_id
    backend = Path(backend).resolve() if backend else Path.home() / '.gemini/antigravity'
    if not re.fullmatch(r'[a-f0-9-]{36}', conversation_id):
        raise ValueError('Exact native Antigravity conversation UUID required')
    connection = sqlite3.connect((backend / 'conversation_summaries.db').as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        summary = connection.execute('SELECT * FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
        summary = dict(summary) if summary is not None else None
    finally:
        connection.close()
    if summary is None or 'parent_conversation_id' not in summary:
        raise ValueError('Native Antigravity primary/child identity is unavailable')
    path = backend / 'brain' / conversation_id / '.system_generated/logs/transcript_full.jsonl'
    try:
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').split('\n') if line.strip()]
    except ValueError as exc:
        raise ValueError('Native Antigravity trace has a partial record; retry after flush') from exc
    inputs = _native_inputs(backend, conversation_id)
    selected, _, _ = _request_scope(root, conversation_id, backend, inputs=inputs,
                                    identifier=completion_project_id(root))
    requests = {index: {'id': f'{conversation_id}-{index}', 'text': text,
                        'native_step': index, 'project_binding': binding}
                for index, text, binding in selected}
    connection = sqlite3.connect((backend / 'conversations' / (conversation_id + '.db')).as_uri() + '?mode=ro', uri=True)
    try:
        statuses = {index: (kind, status) for index, kind, status in connection.execute('SELECT idx,step_type,status FROM steps')}
    finally:
        connection.close()
    from ..git_gate import unflagged_git_read_commands
    from ..journal import state_dir
    jdir = (Path(root).resolve() / 'ꙮ/1 - Анализ').resolve()
    sdir = state_dir(jdir)
    journal_groups = {}
    if (sdir / 'answer-groups').is_dir():
        for gpath in (sdir / 'answer-groups').glob('*.json'):
            try:
                g = json.loads(gpath.read_text(encoding='utf-8'))
                if g.get('status') == 'complete' and g.get('request_ids'):
                    for rid, st in zip(g['request_ids'], g.get('steps', [])):
                        journal_groups[rid] = (g, st)
            except Exception:
                pass
    boundaries = sorted(index for index, _ in inputs)
    turns = []
    for position, start in enumerate(boundaries):
        end = boundaries[position + 1] if position + 1 < len(boundaries) else None
        segment = [row for row in rows if row.get('step_index', -1) > start and (end is None or row.get('step_index', -1) < end)]
        violations = []
        for row in segment:
            for call in row.get('tool_calls', []) if isinstance(row, dict) else []:
                if isinstance(call, dict) and call.get('name') == 'run_command':
                    args = call.get('args', {})
                    if isinstance(args, str):
                        try: args = json.loads(args)
                        except ValueError: args = {}
                    cmd = args.get('CommandLine', '') if isinstance(args, dict) else ''
                    bad = unflagged_git_read_commands(cmd)
                    if bad:
                        violations.append({'step': row.get('step_index'), 'commands': bad})
        last = segment[-1] if segment else {}
        final_step = last.get('step_index')
        final = last.get('type') == 'PLANNER_RESPONSE' and not last.get('tool_calls') and bool(last.get('content', '').strip())
        final = final and statuses.get(final_step) == (15, 3)
        idle = (summary.get('status') == 'CASCADE_RUN_STATUS_IDLE' and summary.get('not_fully_idle') == 0
                and not summary.get('killed') and summary.get('last_user_input_step_index') == start
                and final_step == max(statuses, default=-1))
        req_id = f'{conversation_id}-{start}'
        j_entry = journal_groups.get(req_id)
        if not final and end is not None and j_entry is not None:
            completed = (req_id == j_entry[0]['request_ids'][-1])
            resp_text = (jdir / 'res' / f'{j_entry[1]}.md').read_text(encoding='utf-8') if completed else None
        else:
            completed = bool(final and (end is not None or idle))
            resp_text = last.get('content') if completed else None
        turns.append({'turn_id': f'ag-{conversation_id}-{start}', 'requests': [requests[start]] if start in requests else [],
                      'owned': start in requests, 'completed': completed, 'aborted': False,
                      'response': resp_text, 'start_step': start,
                      'final_step': final_step if completed else None, 'completion_step': final_step if completed else None,
                      'exec5_violations': violations})
    # Several human messages can steer one running answer. Do not manufacture
    # empty intermediate answers or lose the earlier unanswered native inputs.
    grouped, pending = [], []
    for turn in turns:
        if pending and pending[-1]['owned'] != turn['owned']:
            pending = []  # A different explicit project cannot inherit these inputs.
        pending.append(turn)
        if turn['completed']:
            first = pending[0]
            grouped.append({**turn, 'turn_id': first['turn_id'], 'start_step': first['start_step'],
                            'requests': [r for item in pending for r in item['requests']],
                            'owned': all(item['owned'] for item in pending),
                            'exec5_violations': [v for item in pending for v in item.get('exec5_violations', [])]})
            pending = []
    if pending:
        first, last = pending[0], pending[-1]
        grouped.append({**last, 'turn_id': first['turn_id'], 'start_step': first['start_step'],
                        'requests': [r for item in pending for r in item['requests']],
                        'owned': all(item['owned'] for item in pending),
                        'exec5_violations': [v for item in pending for v in item.get('exec5_violations', [])]})
    turns = grouped
    active = turns[-1] if turns and not turns[-1]['completed'] else None
    return {'platform': 'antigravity', 'conversation_id': conversation_id, 'native_backend': str(backend),
            'source_file': str(path), 'primary': not bool(summary['parent_conversation_id']), 'turns': turns,
            'active_turn_id': active['turn_id'] if active else None}


def verify_native_proof(root, native, package=None):
    result = native_review_proof(root, native.get('parent_id', ''), native.get('reviewer_id', ''), write=False)
    for field in ('native_log_sha256', 'final_response_sha256', 'final_step', 'job_id'):
        if native.get(field) != result.get(field):
            raise ValueError('Review proof differs from the current native trace')
    if result['project_kind'] == 'client_text_workspace' or any(key in native for key in ('project_id', 'project_kind')):
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
    return result


def register(project_dir, domain_or_topic, date_str=None):
    return register_antigravity_project(project_dir, domain_or_topic, date_str)
