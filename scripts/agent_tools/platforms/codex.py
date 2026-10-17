"""Codex native session evidence and the installed Shared-Projects boundary."""

import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess

from ..runtime import platform_settings, profile_name
from ..research import json_data
from ..storage import create_bytes


def _local_path(value):
    path = str(Path(value).resolve())
    # SQLite can store Windows extended-length paths after an app update.
    # Resolve links first, then compare the same filesystem spelling on both sides.
    if path.startswith('\\\\?\\UNC\\'):
        path = '\\\\' + path[8:]
    elif path.startswith('\\\\?\\') and re.match(r'^[A-Za-z]:\\', path[4:]):
        path = path[4:]
    return Path(path)


def _home(backend=None, profile=None):
    if backend is not None:
        return Path(backend).resolve()
    values = platform_settings('codex')['homes']
    name = profile_name(profile)
    if name not in values:
        raise ValueError('Unknown Codex profile')
    return Path(values[name]).resolve()


def _trace(home, conversation_id):
    home = _local_path(home)
    if not re.fullmatch(r'[a-f0-9-]{36}', conversation_id):
        raise ValueError('Exact native Codex thread UUID required')
    databases = sorted(home.glob('state_*.sqlite'))
    found = []
    for database in databases:
        connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
        connection.row_factory = sqlite3.Row
        try:
            row = connection.execute('SELECT * FROM threads WHERE id=?', (conversation_id,)).fetchone()
            if row:
                found.append(dict(row))
        finally:
            connection.close()
    if len(found) != 1:
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
        # Never retain private reasoning or compaction summaries as evidence.
        kind = value.get('type')
        payload = value.get('payload', {})
        if kind in ('session_meta', 'turn_context') or kind == 'response_item' and payload.get('type') != 'reasoning' or kind == 'event_msg' and payload.get('type') in ('task_started', 'task_complete', 'turn_aborted'):
            rows.append((index, value))
    if not rows or rows[0][1].get('type') != 'session_meta' or rows[0][1]['payload'].get('id') != conversation_id:
        raise ValueError('Codex trace identity differs from native database')
    return row, path, raw, rows


def _messages(rows, role):
    for index, item in rows:
        payload = item.get('payload', {})
        if item.get('type') != 'response_item' or payload.get('type') != 'message' or payload.get('role') != role:
            continue
        content = payload.get('content', [])
        if not isinstance(content, list):
            raise ValueError('Unsupported native Codex message content')
        texts = [part['text'] for part in content if part.get('type') in ('input_text', 'output_text') and isinstance(part.get('text'), str)]
        if texts:
            yield index, ''.join(texts), payload


def _actual_user_input(text, payload):
    kinds = payload.get('internal_chat_message_metadata_passthrough', {}).get('content_item_kinds', [])
    if 'user.text' in kinds:
        return True
    if any(kind in ('agents_md.instructions', 'environments.environment_context') for kind in kinds):
        return False
    if kinds:
        return not text.lstrip().startswith('<external_codex_apps_open_page>')
    return (not text.lstrip().startswith(('<environment_context>', '<external_codex_apps_open_page>'))
            and not (text.lstrip().startswith('# AGENTS.md instructions') and '<INSTRUCTIONS>' in text))


def _request_scope(root, rows, *, until=None):
    from .request_binding import scoped_inputs
    job_id = json.loads((Path(root) / 'ꘖ/project.json').read_text(encoding='utf-8'))['job_id']
    visible = [(index, item) for index, item in rows if until is None or index <= until]
    contexts = [(index, item['payload']) for index, item in visible if item.get('type') == 'turn_context' and item['payload'].get('cwd')]
    roots = []
    meta = visible[0][1]['payload'] if visible else {}
    if meta.get('cwd'):
        roots.append((visible[0][0], str(_local_path(meta['cwd'])), 'codex-session-cwd'))
    roots.extend((index, str(_local_path(value['cwd'])), 'codex-turn-cwd') for index, value in contexts)
    inputs = []
    for index, text, payload in _messages(visible, 'user'):
        if not _actual_user_input(text, payload):
            continue
        turn = payload.get('internal_chat_message_metadata_passthrough', {}).get('turn_id')
        # A native turn_context may be emitted just after that turn's user input.
        matching = [(step, value) for step, value in contexts if turn and value.get('turn_id') == turn]
        if matching and not any(step <= index for step, _ in matching):
            roots.append((index, str(_local_path(matching[0][1]['cwd'])), 'codex-turn-cwd'))
        inputs.append((index, text))
    return scoped_inputs(root, job_id, inputs, roots, until=until)


def native_requests(root, conversation_id, *, backend=None):
    home = _home(backend)
    _, _, _, rows = _trace(home, conversation_id)
    selected, _, _ = _request_scope(root, rows)
    if not selected:
        raise ValueError('Native Codex requests do not identify this project; use its exact project root or /upwork-init URL')
    return [{'id': f'codex:{conversation_id}:{index}', 'text': text,
             'native_conversation_id': conversation_id, 'native_step': index,
             'surface': 'codex-ui', 'native_profile_home': str(home), 'project_binding': binding}
            for index, text, binding in selected]


def require_current_binding(root, conversation_id, *, backend=None, rows=None, until=None):
    if rows is None:
        rows = _trace(_home(backend), conversation_id)[3]
    selected, active, binding = _request_scope(root, rows, until=until)
    if not selected or not active:
        raise ValueError('Native Codex conversation is currently bound to another project or no exact project root')
    return binding


def _model(rows, before=None):
    contexts = [item['payload'] for index, item in rows if item.get('type') == 'turn_context' and (before is None or index <= before)]
    if not contexts or not contexts[-1].get('model') or not contexts[-1].get('effort'):
        raise ValueError('Actual Codex model/effort is unavailable in native turn context')
    return {key: contexts[-1][key] for key in ('model', 'effort')}


def _spawn(parent_rows, child_meta):
    path = child_meta['source']['subagent']['thread_spawn'].get('agent_path', '')
    matches = []
    created = child_meta.get('timestamp')
    for index, item in parent_rows:
        payload = item.get('payload', {})
        if item.get('type') != 'response_item' or not payload.get('name', '').endswith('spawn_agent'):
            continue
        if created and item.get('timestamp') and item['timestamp'] > created:
            continue
        value = payload.get('arguments', payload.get('input', '{}'))
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                continue
        if isinstance(value, dict) and value.get('task_name') and path.endswith('/' + value['task_name']):
            matches.append((index, payload.get('call_id'), value))
    if not matches:
        raise ValueError('Native parent spawn call and its model selection are not established')
    return matches[-1]


def _selection(parent_rows, child_meta, invocation=None):
    index, call_id, arguments = invocation or _spawn(parent_rows, child_meta)
    parent = _model(parent_rows, before=index)
    model = arguments.get('model') or parent['model']
    effort = arguments.get('reasoning_effort') or arguments.get('model_reasoning_effort')
    if effort is None and model == parent['model']:
        effort = parent['effort']
    return {'model': model, 'effort': effort, 'invocation_call_id': call_id,
            'task_name': arguments['task_name'],
            'selection': 'explicit-parent-spawn' if arguments.get('model') or arguments.get('reasoning_effort') else 'inherit'}


def _assignment_source(rows, meta, assignment):
    spawn = meta['source']['subagent']['thread_spawn']
    path = spawn['agent_path']
    for _, item in rows:
        payload = item.get('payload', {})
        if item.get('type') != 'response_item' or payload.get('type') != 'agent_message' or payload.get('recipient') != path:
            continue
        parts = payload.get('content', [])
        if not any(part.get('text', '').startswith('Message Type: NEW_TASK') for part in parts):
            continue
        if any(part.get('encrypted_content') == assignment for part in parts if part.get('type') == 'encrypted_content'):
            return 'matching-native-spawn-and-child-ciphertext'
    if assignment.startswith('gAAAAA'):
        raise ValueError('Encrypted native spawn does not match the child assignment')
    return 'native-parent-spawn.message'


def _json_objects(value):
    if isinstance(value, dict):
        yield value
        for part in value.values():
            yield from _json_objects(part)
    elif isinstance(value, list):
        for part in value:
            yield from _json_objects(part)
    elif isinstance(value, str):
        decoder, start = json.JSONDecoder(), 0
        while (start := value.find('{', start)) >= 0:
            try:
                parsed, size = decoder.raw_decode(value[start:])
            except ValueError:
                start += 1
                continue
            yield from _json_objects(parsed)
            start += size


def _review_inputs(root, rows, parent_id, reviewer_id):
    calls, receipts = {}, []
    for index, item in rows:
        payload = item.get('payload', {})
        if item.get('type') != 'response_item':
            continue
        call_id, kind = payload.get('call_id'), payload.get('type')
        if kind in ('function_call', 'custom_tool_call'):
            arguments = payload.get('input', payload.get('arguments', ''))
            if isinstance(arguments, str) and 'review-input' in arguments:
                calls[call_id] = arguments
        elif kind in ('function_call_output', 'custom_tool_call_output') and call_id in calls:
            for receipt in _json_objects(payload.get('output')):
                if receipt.get('upwork_review_input') != 1 or receipt.get('verified') is not True:
                    continue
                if (receipt.get('reviewer_id') != reviewer_id or receipt.get('parent_id') != parent_id or
                        receipt.get('project_root') != str(Path(root).resolve())):
                    continue
                package = Path(root).resolve() / receipt.get('package', '')
                if (not package.resolve().is_relative_to(Path(root).resolve()) or not package.is_file() or
                        package.name not in calls[call_id] or hashlib.sha256(package.read_bytes()).hexdigest() != receipt.get('package_sha256')):
                    continue
                receipts.append({'package': receipt['package'], 'package_sha256': receipt['package_sha256'],
                                 'call_id': call_id, 'output_step': index})
    if not receipts:
        raise ValueError('Native reviewer has no successful review-input execution for this immutable package')
    return receipts


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
    events = [(i, item['payload']) for i, item in rows if item.get('type') == 'event_msg']
    if not events or events[-1][1].get('type') != 'task_complete' or not events[-1][1].get('last_agent_message', '').strip():
        raise ValueError('Codex reviewer has no completed final native turn')
    final_index, final = events[-1]
    invocation = _spawn(parent_rows, meta)
    require_current_binding(root, parent_id, backend=home, rows=parent_rows, until=invocation[0])
    selection, child_model = _selection(parent_rows, meta, invocation), _model(rows)
    if child_model['model'] != selection['model'] or selection['effort'] is not None and child_model['effort'] != selection['effort']:
        raise ValueError('Observed reviewer model/effort differs from the native parent spawn selection')
    # collaboration can encrypt both spawn.message and the child NEW_TASK body.
    # Bind that ciphertext, and verify package use via the child's actual tool result.
    assignment = invocation[2].get('message')
    if not isinstance(assignment, str) or not assignment.strip():
        raise ValueError('Native parent reviewer assignment is unavailable')
    assignment_source = _assignment_source(rows, meta, assignment)
    review_inputs = _review_inputs(root, rows, parent_id, reviewer_id)
    digest = hashlib.sha256(raw).hexdigest()
    proof = {'surface': 'codex-ui', 'parent_id': parent_id, 'reviewer_id': reviewer_id,
             'status': 'completed', 'agent_name': spawn.get('agent_path'),
             'native_profile_home': str(home), 'native_log': str(path), 'parent_log': str(parent_path),
             'native_log_sha256': digest, 'final_step': final_index,
             'final_response_sha256': hashlib.sha256(final['last_agent_message'].encode()).hexdigest(),
             'assignment_sha256': hashlib.sha256(assignment.encode()).hexdigest(),
             'assignment_source': assignment_source, 'review_inputs': review_inputs,
             'job_id': json.loads((Path(root) / 'ꘖ/project.json').read_text(encoding='utf-8'))['job_id'],
             'observed_model': child_model, 'model_selection': selection,
             'model_verification': 'native child model/effort checked against actual parent spawn parameters'}
    target = Path(root).resolve() / 'ꘖ/KB/Evidence/Reviews' / f'{reviewer_id}-{digest[:16]}-native.json'
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json_data(proof)
        if target.exists() and target.read_bytes() != payload:
            raise ValueError('Existing Codex proof differs; preserve both versions')
        if not target.exists():
            create_bytes(target, payload)
    return {'proof': target.relative_to(Path(root).resolve()).as_posix(), **proof}


def verify_native_proof(root, native, package=None):
    home = Path(native.get('native_profile_home', '')).resolve()
    allowed = [Path(value).resolve() for value in platform_settings('codex')['homes'].values()]
    if home not in allowed:
        raise ValueError('Saved Codex proof names an unconfigured profile')
    result = native_review_proof(root, native.get('parent_id', ''), native.get('reviewer_id', ''), backend=home, write=False)
    for key in ('native_log_sha256', 'final_response_sha256', 'assignment_sha256', 'assignment_source', 'review_inputs', 'final_step', 'job_id', 'observed_model', 'model_selection'):
        if result.get(key) != native.get(key):
            raise ValueError('Codex review proof differs from the actual native trace')
    if package:
        if not any(Path(item['package']).name == package for item in result['review_inputs']):
            raise ValueError('Codex reviewer did not verify this immutable KB review package')
    return result


def shared_control(request):
    """Use the installed helper; never write native registration stores here."""
    config = platform_settings('codex')
    script = "import {controlWithHelper as control} from " + json.dumps(Path(config['ui_manage']).as_uri()) + ";let input='';for await(const part of process.stdin)input+=part;console.log(JSON.stringify(await control(JSON.parse(input))));"
    result = subprocess.run([config['node'], '--input-type=module', '-e', script],
                            input=json.dumps(request), text=True, capture_output=True, timeout=55,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('Shared-Projects request failed: ' + (result.stderr.strip() or result.stdout.strip()))
    return json.loads(result.stdout)


def register(project_dir, domain_or_topic, date_str=None):
    from ..runtime import request_day, registration_profile_name
    from ..registration import validate_registration
    profile = registration_profile_name()
    day = request_day(date_str)
    request = {'command': 'shared-ensure-project', 'profile': profile,
               'project': {'name': f'{domain_or_topic} - U.P.{day:%Y.%m.%d}',
                           'trustPolicy': 'upwork-daily',
                           'rootPaths': [str(Path(project_dir).resolve())],
                           'folderPath': ['Upwork', 'Proposals', f'{day.year:04d}', f'{day.month:02d}', f'{day.day:02d}']}}
    receipt = shared_control(request)
    return validate_registration(project_dir, domain_or_topic, day.isoformat(), 'codex',
                                 {**receipt, 'surface': 'codex-ui', 'profile': profile})


def summarize(paths, bindings=None):
    from collections import Counter
    tools, totals, missing = Counter(), Counter(), Counter()
    generations, duplicates, seen, phases = 0, 0, set(), {}
    fields = {'input_tokens': 'input_tokens', 'cache_read_tokens': 'cached_input_tokens', 'output_tokens': 'output_tokens'}
    for path in paths:
        cid = None
        for index, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines()):
            item = json.loads(line); payload = item.get('payload', {})
            if item.get('type') == 'session_meta' and cid is None:
                cid = payload['id']
            if item.get('type') == 'response_item' and payload.get('type') in ('custom_tool_call', 'function_call'):
                tools[payload.get('name', 'unknown')] += 1
            if item.get('type') != 'token_usage_record':
                continue
            owner = payload.get('thread_id') or cid
            key = (owner, payload.get('turn_id'), payload.get('response_id', index))
            if key in seen:
                duplicates += 1; continue
            seen.add(key); generations += 1
            phase = next((part['stage'] for part in (bindings or {}).get(owner, [])
                          if part['first_step'] <= index <= part['last_step']), 'unassigned')
            group = phases.setdefault(phase, {'known': Counter(), 'missing': Counter(), 'generations': 0})
            group['generations'] += 1
            for field, native in fields.items():
                value = payload.get('usage', {}).get(native)
                if type(value) is int and value >= 0:
                    totals[field] += value; group['known'][field] += value
                else:
                    missing[field] += 1; group['missing'][field] += 1
    def counts(known, unavailable):
        return {key: {'known_sum': known[key], 'unreported_records': unavailable[key],
                      'complete_total': None if unavailable[key] else known[key]} for key in fields}
    return {'surface': 'codex-ui', 'generations': generations, 'duplicate_records_ignored': duplicates,
            'tokens': counts(totals, missing), 'tools': dict(tools),
            'phases': {name: {'generations': value['generations'], 'tokens': counts(value['known'], value['missing'])}
                       for name, value in phases.items()},
            'interpretation': 'Observed native token_usage_record counters; not quota percentage, currency or proof of quality'}
