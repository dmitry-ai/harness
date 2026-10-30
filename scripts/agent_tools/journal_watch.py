"""A cooperative local native-journal reconciler, independent of model turns.

Only explicitly registered native conversations are read. Stop requests address
our ownership token; no application or arbitrary PID is ever terminated.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import sys
from threading import Thread
import time
import uuid

from .runtime import PRIMARY
from .storage import locked, replace_bytes


INTEGRITY_INTERVAL_SECONDS = 60


def _folder(state_dir=None):
    return Path(state_dir).resolve() if state_dir is not None else PRIMARY.parent.parent / 'ꘖ/data/journal-watch'


def _read(path, default=None):
    for attempt in range(10):
        try:
            return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.025)


def _save(path, value):
    replace_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def register(root, native, from_step, *, state_dir=None, journal_directory=None):
    directory = _folder(state_dir)
    identity = [str(Path(root).resolve()), native['platform'], native['native_backend'], native['conversation_id']]
    key = hashlib.sha256(json.dumps(identity).encode('utf-8')).hexdigest()
    path = directory / 'bindings' / (key + '.json')
    with locked(directory / 'bindings.lock'):
        previous = _read(path, {})
        value = {**previous, 'schema_version': 1, 'project_root': identity[0],
                 'platform': native['platform'], 'native_backend': native['native_backend'],
                 'conversation_id': native['conversation_id'], 'source_file': native['source_file'],
                 'from_step': min(from_step, previous.get('from_step', from_step)), 'registered_at': _now()}
        if journal_directory is not None:
            value['journal_directory'] = str((Path(root).resolve() / journal_directory).resolve())
        if any(value.get(name) != previous.get(name) for name in ('from_step', 'source_file', 'journal_directory')):
            value.pop('last_signature', None)
        _save(path, value)
    return {'binding': str(path), 'from_step': value['from_step']}


def unregister(root, native, *, state_dir=None):
    """Honor an explicit user exception without stopping other conversations."""
    directory = _folder(state_dir)
    identity = [str(Path(root).resolve()), native['platform'], native['native_backend'], native['conversation_id']]
    key = hashlib.sha256(json.dumps(identity).encode('utf-8')).hexdigest()
    path = directory / 'bindings' / (key + '.json')
    with locked(directory / 'scan.lock'), locked(directory / 'bindings.lock'):
        existed = path.exists()
        if existed:
            path.unlink()
    return {'conversation_id': native['conversation_id'], 'watching': False, 'binding_removed': existed}


def _held(path):
    if not path.exists():
        return False
    try:
        with locked(path, timeout=0):
            return False
    except TimeoutError:
        return True


def status(*, state_dir=None):
    directory = _folder(state_dir)
    running = _held(directory / 'daemon.lock')
    value = _read(directory / 'daemon.json', {})
    return {**value, 'status': 'running' if running else 'stopped', 'state_dir': str(directory),
            'registered_conversations': len(list((directory / 'bindings').glob('*.json')))}


def start(*, state_dir=None):
    directory = _folder(state_dir)
    with locked(directory / 'launch.lock'):
        current = status(state_dir=directory)
        if current['status'] == 'running':
            return current
        token = uuid.uuid4().hex
        args = [sys.executable, str(PRIMARY / 'scripts/upwork_project.py'), 'journal-watch',
                '--action', 'run', '--state-dir', str(directory), '--token', token]
        options = {'cwd': str(PRIMARY.parent.parent), 'stdin': subprocess.DEVNULL}
        if os.name == 'nt':
            base_flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            options['creationflags'] = base_flags | getattr(subprocess, 'CREATE_BREAKAWAY_FROM_JOB', 0)
        else:
            options['start_new_session'] = True
        with (directory / 'daemon.log').open('ab') as output:
            try:
                process = subprocess.Popen(args, stdout=output, stderr=output, **options)
            except OSError:
                if os.name != 'nt':
                    raise
                options['creationflags'] = base_flags
                process = subprocess.Popen(args, stdout=output, stderr=output, **options)
        # Reap owned helpers when this caller stays alive (tests/library users).
        # The CLI may exit immediately; the daemon does not depend on this thread.
        Thread(target=process.wait, daemon=True).start()
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            current = status(state_dir=directory)
            if current['status'] == 'running' and current.get('token') == token:
                return current
            if process.poll() is not None:
                raise RuntimeError('Journal watcher exited before readiness; inspect ' + str(directory / 'daemon.log'))
            time.sleep(0.05)
        raise RuntimeError('Journal watcher readiness is unverified; preserve its log and check status')


def stop(*, state_dir=None):
    directory = _folder(state_dir)
    current = status(state_dir=directory)
    if current['status'] == 'running' and current.get('token'):
        _save(directory / 'stop.json', {'token': current['token'], 'requested_at': _now()})
        return {**current, 'stop_requested': True}
    return {**current, 'stop_requested': False}


def _signature(binding):
    files = [Path(binding['source_file'])]
    if binding['platform'] == 'antigravity':
        backend = Path(binding['native_backend'])
        databases = [backend / 'conversation_summaries.db',
                     backend / 'conversations' / (binding['conversation_id'] + '.db')]
        for database in databases:
            files += [database, Path(str(database) + '-wal')]
    result = []
    for path in files:
        try:
            state = path.stat()
            result.append([str(path), state.st_mtime_ns, state.st_size])
        except FileNotFoundError:
            result.append([str(path), None, None])
    return result


def _validate_binding(value):
    if not isinstance(value, dict):
        raise ValueError('Watcher binding must be a JSON object')
    for name in ('project_root', 'platform', 'native_backend', 'conversation_id', 'source_file'):
        if not isinstance(value.get(name), str) or not value[name].strip():
            raise ValueError('Watcher binding needs a nonempty string: ' + name)
    if value['platform'] not in ('codex', 'antigravity'):
        raise ValueError('Watcher binding has an unknown platform')
    if str(uuid.UUID(value['conversation_id'])) != value['conversation_id'].lower():
        raise ValueError('Watcher binding needs a native conversation UUID')
    if type(value.get('from_step')) is not int or value['from_step'] < 0:
        raise ValueError('Watcher binding needs a nonnegative integer from_step')
    for name in ('project_root', 'native_backend', 'source_file', 'journal_directory'):
        if name in value and (not isinstance(value[name], str) or not value[name].strip()
                              or not Path(value[name]).is_absolute()):
            raise ValueError('Watcher binding needs an absolute path: ' + name)
    if 'last_result' in value and not isinstance(value['last_result'], dict):
        raise ValueError('Watcher binding last_result must be a JSON object')


def _integrity_due(binding):
    """Native idleness must not indefinitely cache a once-correct journal."""
    try:
        elapsed = (datetime.fromisoformat(_now()) - datetime.fromisoformat(binding['last_checked_at'])).total_seconds()
        return elapsed < 0 or elapsed >= INTEGRITY_INTERVAL_SECONDS
    except (KeyError, TypeError, ValueError):
        return True


def once(*, state_dir=None):
    from .completion import sync
    directory = _folder(state_dir)
    results = []
    with locked(directory / 'scan.lock', timeout=0):
        for path in sorted((directory / 'bindings').glob('*.json')):
            try:
                value = _read(path)
                _validate_binding(value)
                signature = _signature(value)
            except (OSError, ValueError, TypeError) as exc:
                # A corrupt binding remains evidence; it must not disable the
                # other conversations or be silently rewritten as valid.
                results.append({'binding': str(path), 'valid': False, 'error': str(exc)})
                continue
            if value.get('last_signature') == signature and not _integrity_due(value):
                if value.get('last_result', {}).get('valid') is False:
                    results.append({'conversation_id': value['conversation_id'], **value['last_result'], 'unchanged': True})
                continue
            try:
                result = sync(value['project_root'], value['conversation_id'], platform=value['platform'],
                              backend=value['native_backend'], from_step=value['from_step'],
                              journal_directory=value.get('journal_directory'))
                update = {'last_result': result, 'last_error': None, 'last_checked_at': _now(),
                          'last_signature': None if result.get('retryable') else signature}
            except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, TimeoutError, sqlite3.Error) as exc:
                # A partial native line/temporary SQLite lock is retried, not called success.
                result = {'valid': False, 'error': str(exc)}
                update = {'last_result': result, 'last_error': str(exc), 'last_checked_at': _now(),
                          'last_signature': None}
            try:
                with locked(directory / 'bindings.lock'):
                    latest = _read(path)
                    _validate_binding(latest)
                    if any(latest[name] != value[name] for name in ('project_root', 'platform', 'native_backend', 'conversation_id')):
                        raise ValueError('Watcher binding owner changed during reconciliation; preserved')
                    if any(latest.get(name) != value.get(name) for name in ('from_step', 'source_file', 'journal_directory')):
                        update['last_signature'] = None
                    _save(path, {**latest, **update})
            except (OSError, ValueError, TypeError, KeyError, TimeoutError) as exc:
                # Re-registration or external damage after the first read must
                # not overwrite another owner or stop the remaining bindings.
                result = {'valid': False, 'error': str(exc), 'binding': str(path)}
            results.append({'conversation_id': value['conversation_id'], **result})
    return {'valid': all(r.get('valid') is not False for r in results),
            'bindings_checked': len(results), 'results': results}


def run(*, state_dir=None, token=None, interval=5):
    if not isinstance(interval, (int, float)) or not 0.1 <= interval <= 60:
        raise ValueError('Watcher interval must be between 0.1 and 60 seconds')
    if not isinstance(token, str) or len(token) != 32 or any(c not in '0123456789abcdef' for c in token):
        raise ValueError('Watcher needs its explicit launch ownership token')
    directory = _folder(state_dir)
    with locked(directory / 'daemon.lock', timeout=0):
        marker = {'schema_version': 1, 'pid': os.getpid(), 'token': token, 'started_at': _now(),
                  'status': 'running', 'script': str(PRIMARY / 'scripts/upwork_project.py')}
        _save(directory / 'daemon.json', marker)
        try:
            while _read(directory / 'stop.json', {}).get('token') != token:
                try:
                    result = once(state_dir=directory)
                    marker.update(last_scan_at=_now(), bindings_checked=result['bindings_checked'],
                                  last_scan_valid=result['valid'])
                    marker.pop('last_error', None)
                except (OSError, ValueError, TimeoutError, sqlite3.Error) as exc:
                    marker.update(last_scan_at=_now(), last_error=str(exc))
                _save(directory / 'daemon.json', marker)
                # Cooperative stop checks remain responsive, including during idle periods.
                deadline = time.monotonic() + interval
                while time.monotonic() < deadline:
                    if _read(directory / 'stop.json', {}).get('token') == token:
                        break
                    time.sleep(min(0.1, max(0, deadline - time.monotonic())))
        finally:
            _save(directory / 'daemon.json', {**marker, 'status': 'stopped', 'stopped_at': _now()})
    return {'status': 'stopped', 'token': token}
