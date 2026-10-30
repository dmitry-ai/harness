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
from .request_binding import native_project_fields


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
        elif kind in ('compacted', 'context_compacted', 'checkpoint') or (kind == 'event_msg' and payload.get('type') in ('context_compacted', 'compacted', 'checkpoint')):
            rows.append((index, {'type': 'event_msg', 'payload': {'type': 'context_compacted', 'turn_id': payload.get('turn_id')}}))
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


def _request_scope(root, rows, *, until=None, identifier=None):
    from .request_binding import native_project_id, scoped_inputs
    job_id = identifier if identifier is not None else native_project_id(root)
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


def native_answers(root, conversation_id, *, backend=None):
    """Public turn boundaries and exact final messages; no reasoning is exported."""
    from .request_binding import completion_project_id
    home = _home(backend)
    _, path, _, rows = _trace(home, conversation_id)
    meta = rows[0][1]['payload']
    child = isinstance(meta.get('source'), dict) and bool(meta['source'].get('subagent'))
    selected, _, _ = _request_scope(root, rows, identifier=completion_project_id(root))
    requests = {index: {'id': f'codex:{conversation_id}:{index}', 'text': text,
                        'native_step': index, 'project_binding': binding}
                for index, text, binding in selected}
    from ..git_gate import unflagged_git_read_commands, unpersisted_http_fetch_commands
    turns, current = [], None
    for index, item in rows:
        payload = item.get('payload', {})
        kind = item.get('type')
        if kind == 'event_msg' and payload.get('type') == 'task_started':
            ident = payload.get('turn_id')
            if not isinstance(ident, str) or not ident:
                raise ValueError('Native Codex task_started has no turn ID')
            current = {'turn_id': ident, 'requests': [], 'completed': False,
                       'response': None, 'start_step': index, 'final_step': None,
                       'completion_step': None, 'aborted': False,
                       'exec5_violations': [], 'http_fetch_violations': [],
                       'checkpoint_steps': [], 'tool_steps': [],
                       'subagent_steps': [], 'kb_persistence_steps': [],
                       'transcript_read_steps': [], 'tool_records': [],
                       '_pending_calls': {}}
            turns.append(current)
        elif current is not None and (
                kind in ('compacted', 'context_compacted', 'checkpoint')
                or (kind in ('event_msg', 'response_item') and payload.get('type') in ('context_compacted', 'compacted', 'checkpoint'))):
            current['checkpoint_steps'].append(index)
        elif current is not None and kind == 'response_item' and payload.get('type') in ('function_call', 'custom_tool_call'):
            name = payload.get('name', '')
            raw_cmd = payload.get('input', payload.get('arguments', ''))
            if not isinstance(raw_cmd, str):
                raw_cmd = json.dumps(raw_cmd, ensure_ascii=False)
            current['tool_steps'].append(index)
            rec = {'step': index, 'tools': [name], 'outputs': []}
            current['tool_records'].append(rec)
            if payload.get('call_id'):
                current['_pending_calls'][payload['call_id']] = rec
            if name == 'exec' or name.endswith(('exec_command', 'run_command')):
                bad = unflagged_git_read_commands(raw_cmd)
                if bad:
                    current['exec5_violations'].append({'step': index, 'call_id': payload.get('call_id'), 'commands': bad})
                bad_http = unpersisted_http_fetch_commands(raw_cmd)
                if bad_http:
                    current['http_fetch_violations'].append({'step': index, 'call_id': payload.get('call_id'), 'commands': bad_http})
            if any(tok in raw_cmd for tok in ('recover-checkpoint', str(path.name), 'transcript_full.jsonl')):
                if index not in current['transcript_read_steps']:
                    current['transcript_read_steps'].append(index)
            if name.endswith(('spawn_agent', 'send_input')) or 'spawn_agent' in raw_cmd:
                if index not in current['subagent_steps']:
                    current['subagent_steps'].append(index)
            if (any(tok in raw_cmd for tok in ('ꘖ/KB', 'ꘖ\\KB', '\\ua616/KB', '\\ua616\\\\KB'))
                    or re.search(r'\b(?:save-analysis|collect|collect-http|extract|extract-file|capture-dom)\b', raw_cmd)):
                if index not in current['kb_persistence_steps']:
                    current['kb_persistence_steps'].append(index)
        elif current is not None and kind == 'response_item' and payload.get('type') in ('function_call_output', 'custom_tool_call_output'):
            rec = current['_pending_calls'].get(payload.get('call_id'))
            if rec is not None and payload.get('output') is not None:
                out = payload.get('output')
                rec['outputs'].append((out if isinstance(out, str) else json.dumps(out, ensure_ascii=False))[:4000])
        elif current is not None and kind == 'response_item' and payload.get('type') == 'message':
            if payload.get('role') == 'user':
                text = ''.join(p.get('text', '') for p in payload.get('content', [])
                               if p.get('type') in ('input_text', 'output_text'))
                if _actual_user_input(text, payload):
                    # A foreign user turn must never journal an earlier owned request.
                    current.setdefault('all_request_steps', []).append(index)
                    if index in requests:
                        current['requests'].append(requests[index])
            elif payload.get('role') == 'assistant' and (payload.get('phase') == 'final_answer' or payload.get('channel') == 'final'):
                if payload.get('status') not in (None, 'completed'):
                    continue
                text = ''.join(p.get('text', '') for p in payload.get('content', [])
                               if p.get('type') == 'output_text')
                if text.strip():
                    current['response'], current['final_step'] = text, index
        elif current is not None and kind == 'event_msg' and payload.get('type') in ('task_complete', 'turn_aborted'):
            if payload.get('turn_id') != current['turn_id']:
                continue
            current['completion_step'] = index
            current['aborted'] = payload['type'] == 'turn_aborted'
            if not current['aborted']:
                native_final = payload.get('last_agent_message')
                if current['response'] is not None and isinstance(native_final, str) and native_final != current['response']:
                    raise ValueError('Native Codex final message and completion event disagree')
                current['completed'] = bool(current['response'] and current['final_step'] is not None)
    for turn in turns:
        turn['owned'] = bool(turn['requests']) and len(turn['requests']) == len(turn.get('all_request_steps', []))
        turn.pop('all_request_steps', None)
        cp_steps = turn.pop('checkpoint_steps', [])
        t_steps = turn.pop('tool_steps', [])
        sub_steps = turn.pop('subagent_steps', [])
        kb_steps = turn.pop('kb_persistence_steps', [])
        tr_steps = turn.pop('transcript_read_steps', [])
        records = turn.pop('tool_records', [])
        turn.pop('_pending_calls', None)
        last_cp = max(cp_steps) if cp_steps else None
        pre_cp_steps = [s for s in t_steps if last_cp is not None and s < last_cp]
        post_cp_rec = [s for s in tr_steps if last_cp is not None and s > last_cp]
        pre_cp_records = [r for r in records if last_cp is not None and r['step'] < last_cp]
        turn['compaction'] = {
            'occurred': bool(cp_steps),
            'checkpoint_steps': cp_steps,
            'last_checkpoint_step': last_cp,
            'pre_checkpoint_tool_steps': pre_cp_steps,
            'post_checkpoint_recovery_steps': post_cp_rec,
            'recovered_in_trace': (not cp_steps or not pre_cp_steps or bool(post_cp_rec)),
            'pre_checkpoint_records': pre_cp_records,
        }
        turn['delegation'] = {
            'tool_step_count': len(t_steps),
            'subagent_step_count': len(sub_steps),
            'kb_persistence_step_count': len(kb_steps),
        }
    return {'platform': 'codex', 'conversation_id': conversation_id, 'native_backend': str(home),
            'source_file': str(path), 'primary': not child, 'turns': turns,
            'active_turn_id': current['turn_id'] if current and not current['completion_step'] else None}


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


def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, backend=None):
    """Native model/effort observations for every role, with explicit unknowns."""
    if role not in ('primary', 'AA', 'AF'): raise ValueError('Unknown executor role')
    home = _home(backend)
    _, path, _, rows = _trace(home, conversation_id)
    contexts = [(index, item['payload']) for index, item in rows if item.get('type') == 'turn_context']
    history = [{'step': index, 'model': context.get('model'), 'effort': context.get('effort')}
               for index, context in contexts]
    observed = {key: (history[-1].get(key) if history else None) for key in ('model', 'effort')}
    sources = [{'native_file': str(path), 'kind': 'turn_context', 'step': index,
                'sha256': hashlib.sha256(json_data(context)).hexdigest()} for index, context in contexts]
    requested = {'model': None, 'effort': None, 'selection': 'unavailable', 'source': None}
    meta = rows[0][1]['payload']
    source = meta.get('source')
    spawn = source.get('subagent', {}).get('thread_spawn', {}) if isinstance(source, dict) else {}
    if role != 'primary':
        if not parent_id or spawn.get('parent_thread_id') != parent_id or parent_id == conversation_id:
            raise ValueError('Native parent/child relationship required for AA/AF metadata')
        _, parent_path, _, parent_rows = _trace(home, parent_id)
        invocation = _spawn(parent_rows, meta)
        try:
            selection = _selection(parent_rows, meta, invocation)
            requested = {key: selection.get(key) for key in ('model', 'effort', 'selection')}
        except ValueError:
            arguments = invocation[2]
            requested.update(model=arguments.get('model'),
                             effort=arguments.get('reasoning_effort') or arguments.get('model_reasoning_effort'),
                             selection='explicit-parent-spawn' if arguments.get('model') else 'inherit')
        requested['source'] = {'native_file': str(parent_path), 'kind': 'spawn_agent',
                               'step': invocation[0], 'call_id': invocation[1]}
    else:
        # Session metadata sometimes carries an explicit requested model. Do not
        # copy a runtime default or the observed context into a missing request.
        if meta.get('model'):
            requested.update(model=meta['model'], effort=meta.get('reasoning_effort'), selection='native-session-selection',
                             source={'native_file': str(path), 'kind': 'session_meta', 'step': rows[0][0]})
    checks = {}
    for key in ('model', 'effort'):
        checks[key] = ('unverified' if not requested.get(key) or not observed.get(key) else
                       'verified' if requested[key] == observed[key] else 'mismatch')
    status = 'mismatch' if 'mismatch' in checks.values() else 'verified' if set(checks.values()) == {'verified'} else 'unverified'
    return {'schema_version': 1, 'surface': 'codex-ui', 'role': role, 'conversation_id': conversation_id,
            'parent_id': parent_id, 'requested': requested, 'observed': observed, 'observation_history': history,
            'metadata_sources': sources, 'verification': {'status': status, **checks,
                'detail': 'Native turn_context reports selected model/effort; missing fields remain unknown; server execution internals are not inferred'}}


def native_tool_trace(root, request):
    home = _home(request.get('native_profile_home'))
    if request.get('native_profile_home') and home not in [Path(value).resolve() for value in platform_settings('codex')['homes'].values()]:
        raise ValueError('Native tool trace names an unconfigured Codex profile')
    conversation_id = request.get('conversation_id', '')
    _, path, raw, rows = _trace(home, conversation_id)
    ids = request.get('call_ids')
    if not isinstance(ids, list) or not ids or not all(isinstance(x, str) and x.strip() for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('Exact unique Codex native tool call IDs required')
    calls, outputs = {}, {}
    for index, item in rows:
        payload = item.get('payload', {})
        if item.get('type') != 'response_item' or payload.get('call_id') not in ids: continue
        call_id, kind = payload['call_id'], payload.get('type')
        if kind in ('function_call', 'custom_tool_call'):
            if call_id in calls: raise ValueError('Ambiguous native tool invocation')
            calls[call_id] = (index, payload, item.get('timestamp'))
        elif kind in ('function_call_output', 'custom_tool_call_output'):
            if call_id in outputs: raise ValueError('Ambiguous native tool output')
            outputs[call_id] = (index, payload, item.get('timestamp'))
    events = []
    for call_id in ids:
        if call_id not in calls or call_id not in outputs or outputs[call_id][0] <= calls[call_id][0]:
            raise ValueError('Native tool call has no matched completed output')
        index, call, created_at = calls[call_id]
        output_index, output, completed_at = outputs[call_id]
        arguments = call.get('arguments', call.get('input', {}))
        if isinstance(arguments, str):
            try: arguments = json.loads(arguments)
            except ValueError: arguments = {'code': arguments} if call.get('type') == 'custom_tool_call' else {}
        result = output.get('output')
        error = output.get('isError') is True
        if isinstance(result, dict): error |= result.get('isError') is True
        elif isinstance(result, str):
            try: error |= json.loads(result).get('isError') is True
            except (ValueError, AttributeError): pass
        events.append({'id': call_id, 'step': index, 'output_step': output_index, 'name': call.get('name', ''),
                       'arguments': arguments, 'result': result, 'successful': not error,
                       'created_at': created_at, 'completed_at': completed_at,
                       'native_event_sha256': hashlib.sha256(json_data([call, output])).hexdigest()})
        if call.get('namespace') is not None:
            events[-1]['namespace'] = call['namespace']
    return {'surface': 'codex-ui', 'conversation_id': conversation_id, 'native_profile_home': str(home),
            'call_ids': ids, 'native_log': str(path), 'native_log_sha256': hashlib.sha256(raw).hexdigest(), 'events': events}


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
             'final_response': final['last_agent_message'],
             'assignment_sha256': hashlib.sha256(assignment.encode()).hexdigest(),
             'assignment_source': assignment_source, 'review_inputs': review_inputs,
             **native_project_fields(root),
             'observed_model': child_model, 'model_selection': selection,
             'executor_metadata': native_executor_metadata(root, reviewer_id, role='AA', parent_id=parent_id, backend=home),
             'model_verification': 'native child model/effort checked against actual parent spawn parameters'}
    target = Path(root).resolve() / 'ꘖ/KB/Evidence/Reviews' / f'{reviewer_id}-{digest[:16]}-native.json'
    authored = target.with_name(target.stem + '-authored.txt')
    proof['authored_response'] = authored.relative_to(Path(root).resolve()).as_posix()
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        authored_bytes = final['last_agent_message'].encode('utf-8')
        if authored.exists() and authored.read_bytes() != authored_bytes:
            raise ValueError('Immutable native authored response differs')
        if not authored.exists(): create_bytes(authored, authored_bytes)
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
    if result['project_kind'] == 'client_text_workspace' or any(key in native for key in ('project_id', 'project_kind')):
        for key in ('project_id', 'project_kind'):
            if result.get(key) != native.get(key):
                raise ValueError('Codex review proof has a different explicit project identity')
    authored = Path(root) / result['authored_response']
    if authored.exists() and hashlib.sha256(authored.read_bytes()).hexdigest() != result['final_response_sha256']:
        raise ValueError('Immutable native authored reviewer response changed')
    if 'executor_metadata' in native and native['executor_metadata'] != result['executor_metadata']:
        raise ValueError('Native executor metadata differs from saved reviewer proof')
    if package:
        if not any(Path(item['package']).name == package for item in result['review_inputs']):
            raise ValueError('Codex reviewer did not verify this immutable KB review package')
    return result


def shared_control(request):
    """Use the installed helper; never write native registration stores here."""
    config = platform_settings('codex')
    script = "import {controlWithHelper as control} from " + json.dumps(Path(config['ui_manage']).as_uri()) + ";let input='';for await(const part of process.stdin)input+=part;console.log(JSON.stringify(await control(JSON.parse(input))));"
    try:
        result = subprocess.run([config['node'], '--input-type=module', '-e', script],
                                input=json.dumps(request), text=True, capture_output=True, timeout=55,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Shared-Projects timed out; the request may have been accepted. Repeat the same idempotent command to recover.') from exc
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
    if not receipt.get('complete') and receipt.get('shared_id'):
        accounts = receipt.get('accounts') or {}
        if any(isinstance(info, dict) and info.get('state') in ('connected', 'initializing') for info in accounts.values()):
            import time
            for _ in range(8):
                time.sleep(0.4)
                receipt = shared_control({'command': 'shared-registration', 'sharedId': receipt['shared_id'], 'profile': profile})
                if receipt.get('complete'):
                    break
                accounts = receipt.get('accounts') or {}
                if not any(isinstance(info, dict) and info.get('state') in ('connected', 'initializing') for info in accounts.values()):
                    break
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
