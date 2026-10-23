"""A format-independent turn contract and exact native delivery reconciliation.

Rule applicability is recorded, not presented as proof of model comprehension.
Prepared bytes and observed delivery are deliberately different states.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

from . import journal
from .platforms import adapter
from .runtime import PRIMARY, platform_name
from .storage import create_bytes, locked, replace_bytes


COMMANDS = ('turn-begin', 'answer-prepare', 'journal-sync', 'journal-watch', 'journal-unwatch')
RULES = {'FILE-3': ('rules/01-file-boundaries.md', 'file-3'),
         'EXEC-5': ('rules/08-execution-and-tools.md', 'exec-5'),
         'DOC-2': ('rules/04-statement-structure.md', 'doc-2')}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def _read(path):
    return json.loads(path.read_bytes().decode('utf-8'))


def _folder(root):
    return Path(root).resolve() / 'ꘖ/data/turns'


def _directory(root, selected=None):
    return (Path(root).resolve() / (selected or 'ꙮ/1 - Анализ')).resolve()


def _key(native, turn):
    identity = [native['platform'], native['native_backend'], native['conversation_id'], turn['turn_id']]
    return _hash(_json(identity))[:40]


def _native(root, conversation=None, *, platform=None, backend=None):
    platform = platform_name(platform)
    conversation = conversation or (os.environ.get('CODEX_THREAD_ID') if platform == 'codex' else None)
    if not conversation:
        raise ValueError('Select the actual current native conversation; no summary or neighbouring chat fallback')
    return adapter(platform).native_answers(Path(root).resolve(), conversation, backend=backend)


def _policy():
    return {ident: {'source': relative, 'anchor': anchor,
                    'sha256': _hash((PRIMARY / relative).read_bytes())}
            for ident, (relative, anchor) in RULES.items()}


def _new(root, native, turn, *, recovered=False, journal_directory=None):
    return {'schema_version': 1, 'key': _key(native, turn), 'project_root': str(Path(root).resolve()),
            'platform': native['platform'], 'native_backend': native['native_backend'],
            'conversation_id': native['conversation_id'], 'native_turn_id': turn['turn_id'],
            'native_start_step': turn['start_step'], 'requests': turn['requests'], 'role': 'primary',
            'journal_required': True, 'journal': str(_directory(root, journal_directory)), 'applicable_rules': _policy(),
            'format_independent': True, 'rule_comprehension_verified': False,
            'required_completion': ['answer-prepare', 'native-delivery-check'],
            'status': 'open', 'prepared': None, 'delivery': None,
            'recovered_after_delivery': recovered, 'created_at': _now()}


def _state(root, native, turn, *, recovered=False, allow_extended=False, journal_directory=None, strict_journal=False):
    path = _folder(root) / (_key(native, turn) + '.json')
    value = _read(path) if path.exists() else _new(root, native, turn, recovered=recovered, journal_directory=journal_directory)
    saved_directory = _directory(root, value['journal'])
    if strict_journal and journal_directory is not None and saved_directory != _directory(root, journal_directory):
        raise ValueError('The native turn already has a different journal; preserve its original binding')
    value['journal'] = str(saved_directory)
    for name, expected in [('project_root', str(Path(root).resolve())), ('platform', native['platform']),
                           ('native_backend', native['native_backend']), ('conversation_id', native['conversation_id']),
                           ('native_turn_id', turn['turn_id'])]:
        if value.get(name) != expected:
            raise ValueError('Completion state has a different native owner; preserved')
    old, current = value['requests'], turn['requests']
    if current[:len(old)] != old:
        raise ValueError('Native requests changed before the saved boundary; preserved')
    if value['prepared'] and current != old:
        if not allow_extended:
            raise ValueError('A prepared answer does not cover the new native request; preserve it and reconcile the turn')
        value['uncovered_requests'] = current[len(old):]
        return path, value
    value['requests'] = current
    return path, value


def _persist(path, value):
    value['updated_at'] = _now()
    replace_bytes(path, _json(value))


def _active(native):
    if not native['primary']:
        return None
    turn = next((turn for turn in native['turns'] if turn['turn_id'] == native['active_turn_id']), None)
    if turn is None or not turn['owned'] or turn['aborted']:
        raise ValueError('No active native user turn belonging entirely to this project')
    return turn


def begin(root, conversation=None, *, platform=None, backend=None, watch=True, watch_dir=None, journal_directory=None):
    root = Path(root).resolve()
    native = _native(root, conversation, platform=platform, backend=backend)
    turn = _active(native)
    if turn is None:
        return {'role': 'child', 'journal_required': False, 'reason': 'The primary conversation owns the user journal'}
    with locked(_folder(root) / 'writer.lock'):
        path, value = _state(root, native, turn, journal_directory=journal_directory, strict_journal=True)
        _persist(path, value)
    result = {'turn_key': value['key'], 'state': path.relative_to(root).as_posix(),
              'role': 'primary', 'journal_required': True, 'status': value['status'],
              'applicable_rules': value['applicable_rules'], 'rule_comprehension_verified': False,
              'required_completion': value['required_completion']}
    if watch:
        from .journal_watch import register, start
        register(root, native, turn['start_step'], state_dir=watch_dir, journal_directory=value['journal'])
        result['watcher'] = start(state_dir=watch_dir)
    return result


def _group(root, native, turn, response, directory):
    """Recognize our previous exact native-turn receipts, never deduplicate by text."""
    key = 'native-' + _key(native, turn)
    legacy = turn['turn_id']
    groups = journal.state_dir(directory) / 'answer-groups'
    native_ids = [r['id'] for r in turn['requests']]
    matches = []
    for file in groups.glob('*.json'):
        old = _read(file)
        if old.get('request_ids') == native_ids:
            if old.get('requests') != [r['text'] for r in turn['requests']] or old.get('response_sha256') != _hash(response.encode('utf-8')):
                raise ValueError('A journal for these exact native request IDs has different bytes; preserve the conflict')
            matches.append(old)
    if len(matches) > 1:
        raise ValueError('More than one journal group claims these native request IDs; preserve the ambiguity')
    if matches:
        return matches[0]['turn'], native_ids
    if re.fullmatch(r'[A-Za-z0-9_-]{1,100}', legacy) and (groups / (legacy + '.json')).exists():
        old = _read(groups / (legacy + '.json'))
        if old.get('requests') != [r['text'] for r in turn['requests']] or old.get('response_sha256') != _hash(response.encode('utf-8')):
            raise ValueError('Existing native-turn journal has different bytes; preserve the conflict')
        # Old record-answer callers did not always retain native request IDs.
        return legacy, old.get('request_ids')
    return key, native_ids


def _record(root, native, turn, response, directory):
    directory = _directory(root, directory)
    from .text_workflow import gate_requests
    gate_requests([root, directory], [r['text'] for r in turn['requests']], response)
    token, request_ids = _group(root, native, turn, response, directory)
    group_file = journal.state_dir(directory) / 'answer-groups' / (token + '.json')
    already_complete = group_file.exists() and _read(group_file).get('status') == 'complete'
    steps = journal.record_answer(directory, [r['text'] for r in turn['requests']],
                                  response, token, request_ids)
    for step, request in zip(steps, turn['requests']):
        if (directory / 'req' / f'{step}.md').read_bytes() != request['text'].encode('utf-8'):
            raise ValueError('Recorded request read-back differs from native text')
        if (directory / 'res' / f'{step}.md').read_bytes() != response.encode('utf-8'):
            raise ValueError('Recorded response read-back differs from prepared text')
    return {'journal_steps': steps, 'response_sha256': _hash(response.encode('utf-8')),
            'response_file': str(directory / 'res' / f'{steps[0]}.md'), 'recorded_at': _now(),
            'reused_complete_journal_group': already_complete}


def prepare(root, response, conversation=None, *, platform=None, backend=None, watch=True, watch_dir=None, journal_directory=None):
    """One pre-publication operation for articles and ordinary analytical replies."""
    if not isinstance(response, str) or not response.strip():
        raise ValueError('An exact nonempty UTF-8 final response is required')
    from .causal_checks import unsupported_probability_claims
    issues = unsupported_probability_claims(response)
    if issues:
        raise ValueError('Unsupported causal probability basis: ' + '; '.join(issues))
    result = begin(root, conversation, platform=platform, backend=backend, watch=watch, watch_dir=watch_dir,
                   journal_directory=journal_directory)
    if not result['journal_required']:
        raise ValueError('A child executor cannot prepare the primary user journal')
    root = Path(root).resolve()
    native = _native(root, conversation, platform=platform, backend=backend)
    turn = _active(native)
    if turn is None or _key(native, turn) != result['turn_key']:
        raise ValueError('The active native turn changed during preparation; no answer was recorded')
    with locked(_folder(root) / 'writer.lock'):
        path, value = _state(root, native, turn)
        sha = _hash(response.encode('utf-8'))
        if value['prepared'] and value['prepared']['response_sha256'] != sha:
            raise ValueError('Prepared response bytes are immutable; preserve the earlier version and reconcile before a corrective turn')
        if value['status'] == 'conflict':
            raise ValueError('Resolve the native delivery conflict without overwriting journal history')
        workflow = root / 'ꘖ/data/workflow.json'
        if workflow.exists():
            from .workflow import load
            state = load(root)
            identifiers = {r['id'] for r in turn['requests']}
            covered = {r['id'] for r in state['requests']} & identifiers
            if covered:
                if covered != identifiers:
                    raise ValueError('Adopt all exact current requests before preparing a tracked analysis response')
                from .review import authorize
                authorize(root, state, response=response)
                pending = {r['id'] for r in state['requests'] if not r.get('response_prepared')}
                if pending:
                    if pending != identifiers:
                        raise ValueError('Align unanswered tracked requests with the exact current native turn before preparation')
                    # Keep the analysis finalizer's answer-bound approval and
                    # response_prepared receipts; _record reuses this ID group.
                    from .workflow import record_current_answer
                    record_current_answer(root, response, journal_directory=value['journal'])
                elif any(r['response_prepared']['sha256'] != sha for r in state['requests'] if r['id'] in identifiers):
                    raise ValueError('Tracked analysis requests already have different prepared response bytes')
        value['prepared'] = _record(root, native, turn, response, value['journal'])
        value['status'] = 'prepared'
        _persist(path, value)
    return {**result, **value['prepared'], 'ready': True, 'status': 'prepared', 'delivery_verified': False}


def _conflict(root, path, value, native, turn, response, detail):
    payload = response.encode('utf-8')
    evidence = _folder(root) / 'conflicts' / (value['key'] + '-' + _hash(payload) + '.txt')
    evidence.parent.mkdir(parents=True, exist_ok=True)
    if evidence.exists() and evidence.read_bytes() != payload:
        raise ValueError('Immutable native conflict evidence changed')
    if not evidence.exists():
        create_bytes(evidence, payload)
    value['status'] = 'conflict'
    value['delivery'] = {'verified': False, 'native_response_sha256': _hash(payload),
                         'source_file': native['source_file'], 'final_step': turn['final_step'],
                         'native_requests': turn['requests'],
                         'conflict_evidence': evidence.relative_to(root).as_posix(), 'detail': detail}
    _persist(path, value)
    return {'turn_key': value['key'], 'status': 'conflict', 'detail': detail,
            'evidence': evidence.relative_to(root).as_posix()}


def sync(root, conversation=None, *, platform=None, backend=None, from_step=0, journal_directory=None):
    """Import only observed completed public answers, or verify prepared ones."""
    if type(from_step) is not int or from_step < 0:
        raise ValueError('Native from-step must be a nonnegative integer')
    root = Path(root).resolve()
    native = _native(root, conversation, platform=platform, backend=backend)
    if not native['primary']:
        raise ValueError('A child executor has no primary user journal to synchronize')
    if not any(turn['owned'] for turn in native['turns']):
        raise ValueError('Native conversation has no user turns owned by this project')
    eligible = [turn for turn in native['turns']
                if turn['owned'] and turn['completed'] and not turn['aborted'] and turn['start_step'] >= from_step]
    if not eligible:
        return {'valid': True, 'conversation_id': native['conversation_id'], 'source_file': native['source_file'],
                'turns': [], 'pending_native_turn': native['active_turn_id'], 'private_reasoning_retained': False}
    results = []
    with locked(_folder(root) / 'writer.lock'):
        for turn in eligible:
            path, value = _state(root, native, turn, recovered=True, allow_extended=True, journal_directory=journal_directory)
            response = turn['response']
            sha = _hash(response.encode('utf-8'))
            if value.get('uncovered_requests'):
                results.append(_conflict(root, path, value, native, turn, response, 'Prepared answer does not cover newly received native requests'))
                continue
            if value['prepared'] and value['prepared']['response_sha256'] != sha:
                results.append(_conflict(root, path, value, native, turn, response, 'Prepared and delivered response bytes differ'))
                continue
            try:
                recorded = _record(root, native, turn, response, value['journal'])
            except (OSError, ValueError) as exc:
                results.append(_conflict(root, path, value, native, turn, response, str(exc)))
                continue
            previous = value.get('delivery') or {}
            if not previous.get('completion_provenance'):
                value['recovered_after_delivery'] = not bool(value['prepared']) and not recorded['reused_complete_journal_group']
            provenance = ('prepared' if value['prepared'] else
                          'recovered_native' if value['recovered_after_delivery'] else 'existing_journal')
            value['delivery'] = {**recorded, 'verified': True, 'source_file': native['source_file'],
                                 'final_step': turn['final_step'], 'completion_step': turn['completion_step'],
                                 'native_response_sha256': sha, 'verified_at': _now(),
                                 'completion_provenance': provenance, 'preparation_verified': bool(value['prepared'])}
            value['status'] = 'delivered'
            _persist(path, value)
            results.append({'turn_key': value['key'], 'status': 'delivered', 'delivery_verified': True,
                            'journal_steps': recorded['journal_steps'],
                            'completion_provenance': provenance, 'preparation_verified': bool(value['prepared']),
                            'recovered_after_delivery': value['recovered_after_delivery']})
    return {'valid': not any(r['status'] == 'conflict' for r in results), 'conversation_id': native['conversation_id'],
            'source_file': native['source_file'], 'turns': results,
            'pending_native_turn': native['active_turn_id'], 'private_reasoning_retained': False}


def add_parser_arguments(parser, command):
    if command == 'journal-watch':
        parser.add_argument('--action', choices=('start', 'status', 'stop', 'once', 'run'), default='status')
        parser.add_argument('--state-dir', type=Path)
        parser.add_argument('--interval', type=float, default=5)
        parser.add_argument('--token', help='Internal watcher ownership token')
        return
    parser.add_argument('project', type=Path)
    parser.add_argument('--conversation', help='Actual current native conversation UUID; Codex can use CODEX_THREAD_ID')
    if command != 'journal-unwatch':
        parser.add_argument('--journal', type=Path, help='User-selected journal; otherwise preserve the turn binding or use ꙮ/1 - Анализ')
    if command in ('turn-begin', 'answer-prepare'):
        parser.add_argument('--no-watch', action='store_true', help='Explicit foreground-only mode; no independent recovery')
    if command == 'answer-prepare':
        parser.add_argument('--response-file', type=Path, required=True, help='Exact UTF-8 final response, or - for stdin')
        parser.add_argument('--consume-input', action='store_true')
    if command == 'journal-sync':
        parser.add_argument('--from-step', type=int, default=0)


def execute(args):
    if args.command == 'turn-begin':
        return begin(args.project, args.conversation, watch=not args.no_watch, journal_directory=args.journal)
    if args.command == 'answer-prepare':
        from .operations import _operation_input, _consumed
        payload = _operation_input(args, args.response_file)
        result = prepare(args.project, payload.decode('utf-8'), args.conversation, watch=not args.no_watch, journal_directory=args.journal)
        return _consumed(args, args.response_file, payload, result)
    if args.command == 'journal-sync':
        return sync(args.project, args.conversation, from_step=args.from_step, journal_directory=args.journal)
    if args.command == 'journal-unwatch':
        from .journal_watch import unregister
        native = _native(args.project, args.conversation)
        if not native['primary'] or not any(turn['owned'] for turn in native['turns']):
            raise ValueError('Only the owned primary conversation can remove its watcher binding')
        return unregister(args.project, native)
    if args.command == 'journal-watch':
        from . import journal_watch
        if args.action == 'run':
            return journal_watch.run(state_dir=args.state_dir, token=args.token, interval=args.interval)
        return getattr(journal_watch, args.action)(state_dir=args.state_dir)
    raise ValueError('Unknown completion operation')
