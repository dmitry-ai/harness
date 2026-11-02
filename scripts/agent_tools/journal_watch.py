# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate flashing Git console windows on Windows via CREATE_NO_WINDOW and journal-watch lifecycle skip":
# https://github.com/dmitry-ai/harness/issues/40
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
from .runtime import HARNESS_META, HARNESS_ROOT, PRIMARY
from .storage import locked, replace_bytes
INTEGRITY_INTERVAL_SECONDS = 60
def _folder(state_dir=None):
	return Path(state_dir).resolve() if None is not state_dir else HARNESS_META / 'ꘖ/data/journal-watch'
def _read(path, default=None):
	for attempt in range(10):
		try:
			return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
		except PermissionError:
			if 9 == attempt:
				raise
			time.sleep(0.025)
def _save(path, value):
	replace_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
def _now():
	return datetime.now(timezone.utc).isoformat()
def _log(directory, event, **fields):
	try:
		path = Path(directory) / 'daemon.log'
		path.parent.mkdir(parents=True, exist_ok=True)
		entry = {'ts': _now(), 'event': event, **fields}
		with path.open('ab') as stream:
			stream.write((json.dumps(entry, ensure_ascii=False) + '\n').encode('utf-8'))
	except OSError:
		pass
def _code_digest():
	digest = hashlib.sha256()
	for path in sorted((PRIMARY / 'scripts/agent_tools').rglob('*.py')):
		try:
			digest.update(path.relative_to(PRIMARY).as_posix().encode('utf-8') + b'\x00' + path.read_bytes() + b'\x00')
		except OSError:
			pass
	return digest.hexdigest()
def register(root, native, from_step, *, state_dir=None, journal_directory=None):
	directory = _folder(state_dir)
	identity = [str(Path(root).resolve()), native['platform'], native['native_backend'], native['conversation_id']]
	key = hashlib.sha256(json.dumps(identity).encode('utf-8')).hexdigest()
	path = directory / 'bindings' / (key + '.json')
	with locked(directory / 'bindings.lock'):
		previous = _read(path, {})
		value = {**previous, 'schema_version': 1, 'project_root': identity[0], 'platform': native['platform'], 'native_backend': native['native_backend'], 'conversation_id': native['conversation_id'], 'source_file': native['source_file'], 'from_step': min(from_step, previous.get('from_step', from_step)), 'registered_at': _now()}
		if None is not journal_directory:
			value['journal_directory'] = str((Path(root).resolve() / journal_directory).resolve())
		if any((value.get(name) != previous.get(name) for name in ('from_step', 'source_file', 'journal_directory'))):
			value.pop('last_signature', None)
		_save(path, value)
	r = {'binding': str(path), 'from_step': value['from_step']}
	return r
def unregister(root, native, *, state_dir=None):
	directory = _folder(state_dir)
	identity = [str(Path(root).resolve()), native['platform'], native['native_backend'], native['conversation_id']]
	key = hashlib.sha256(json.dumps(identity).encode('utf-8')).hexdigest()
	path = directory / 'bindings' / (key + '.json')
	with locked(directory / 'scan.lock'), locked(directory / 'bindings.lock'):
		existed = path.exists()
		if existed:
			path.unlink()
	r = {'conversation_id': native['conversation_id'], 'watching': False, 'binding_removed': existed}
	return r
def _held(path):
	if not path.exists():
		r = False
	else:
		try:
			with locked(path, timeout=0):
				r = False
		except TimeoutError:
			r = True
	return r
def status(*, state_dir=None):
	directory = _folder(state_dir)
	running = _held(directory / 'daemon.lock')
	value = _read(directory / 'daemon.json', {})
	r = {**value, 'status': 'running' if running else 'stopped', 'state_dir': str(directory), 'registered_conversations': len(list((directory / 'bindings').glob('*.json')))}
	return r
def start(*, state_dir=None):
	directory = _folder(state_dir)
	with locked(directory / 'launch.lock'):
		current = status(state_dir=directory)
		if 'running' == current['status']:
			return current
		token = uuid.uuid4().hex
		args = [sys.executable, str(PRIMARY / 'scripts/harness.py'), 'journal-watch', '--action', 'run', '--state-dir', str(directory), '--token', token]
		options = {'cwd': str(HARNESS_ROOT), 'stdin': subprocess.DEVNULL}
		if 'nt' != os.name:
			options['start_new_session'] = True
		else:
			base_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
			options['creationflags'] = base_flags | getattr(subprocess, 'CREATE_BREAKAWAY_FROM_JOB', 0)
		breakaway_fallback = False
		with (directory / 'daemon.log').open('ab') as output:
			try:
				process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=output, **options)
			except OSError:
				if 'nt' != os.name:
					raise
				breakaway_fallback = True
				options['creationflags'] = base_flags
				process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=output, **options)
		_log(directory, 'start_spawn', pid=process.pid, token=token, breakaway_fallback=breakaway_fallback)
		Thread(target=process.wait, daemon=True).start()
		deadline = time.monotonic() + 8
		while time.monotonic() < deadline:
			current = status(state_dir=directory)
			if 'running' == current['status'] and current.get('token') == token:
				return current
			if None is not process.poll():
				raise RuntimeError('Journal watcher exited before readiness; inspect ' + str(directory / 'daemon.log'))
			time.sleep(0.05)
		raise RuntimeError('Journal watcher readiness is unverified; preserve its log and check status')
def stop(*, state_dir=None):
	directory = _folder(state_dir)
	current = status(state_dir=directory)
	if not ('running' == current['status'] and current.get('token')):
		r = {**current, 'stop_requested': False}
	else:
		_save(directory / 'stop.json', {'token': current['token'], 'requested_at': _now()})
		_log(directory, 'stop_requested', token=current['token'], pid=current.get('pid'))
		r = {**current, 'stop_requested': True}
	return r
def _signature(binding):
	files = [Path(binding['source_file'])]
	if 'antigravity' == binding['platform']:
		backend = Path(binding['native_backend'])
		databases = [backend / 'conversation_summaries.db', backend / 'conversations' / (binding['conversation_id'] + '.db')]
		for database in databases:
			files += [database, Path(str(database) + '-wal')]
	result = []
	for path in files:
		try:
			state = path.stat()
			result.append([str(path), state.st_mtime_ns, state.st_size])
		except FileNotFoundError:
			result.append([str(path), None, None])
	r = result
	return r
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
		if name in value and (not isinstance(value[name], str) or not value[name].strip() or (not Path(value[name]).is_absolute())):
			raise ValueError('Watcher binding needs an absolute path: ' + name)
	if 'last_result' in value and (not isinstance(value['last_result'], dict)):
		raise ValueError('Watcher binding last_result must be a JSON object')
def _integrity_due(binding):
	try:
		elapsed = (datetime.fromisoformat(_now()) - datetime.fromisoformat(binding['last_checked_at'])).total_seconds()
		r = elapsed < 0 or elapsed >= INTEGRITY_INTERVAL_SECONDS
	except (KeyError, TypeError, ValueError):
		r = True
	return r
def once(*, state_dir=None, dry_run=False, stop_token=None):
	from .completion import sync
	directory = _folder(state_dir)
	results = []
	with locked(directory / 'scan.lock', timeout=0):
		for path in sorted((directory / 'bindings').glob('*.json')):
			if stop_token and _read(directory / 'stop.json', {}).get('token') == stop_token:
				break
			try:
				value = _read(path)
				_validate_binding(value)
				signature = _signature(value)
			except (OSError, ValueError, TypeError) as exc:
				results.append({'binding': str(path), 'valid': False, 'error': str(exc)})
				continue
			if value.get('last_signature') == signature and (not _integrity_due(value)):
				if False is value.get('last_result', {}).get('valid'):
					results.append({'conversation_id': value['conversation_id'], **value['last_result'], 'unchanged': True})
				continue
			if dry_run:
				results.append({'conversation_id': value['conversation_id'], 'project_root': value['project_root'], 'platform': value['platform'], 'valid': True, 'dry_run': True, 'would_sync': True})
				continue
			try:
				result = sync(value['project_root'], value['conversation_id'], platform=value['platform'], backend=value['native_backend'], from_step=value['from_step'], journal_directory=value.get('journal_directory'))
				update = {'last_result': result, 'last_error': None, 'last_checked_at': _now(), 'last_signature': None if result.get('retryable') else signature}
				for t_rec in result.get('turns') or []:
					if t_rec.get('recovered_after_delivery') or 'conflict' == t_rec.get('status'):
						_log(directory, 'turn_reconciled', conversation_id=value['conversation_id'], project_root=value['project_root'], turn_key=t_rec.get('turn_key'), status=t_rec.get('status'), journal_steps=t_rec.get('journal_steps'), completion_provenance=t_rec.get('completion_provenance'), detail=t_rec.get('detail'))
			except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, TimeoutError, sqlite3.Error) as exc:
				retryable_exc = isinstance(exc, (OSError, TimeoutError, sqlite3.Error)) and (not isinstance(exc, FileNotFoundError))
				result = {'valid': False, 'error': str(exc), 'retryable': retryable_exc}
				update = {'last_result': result, 'last_error': str(exc), 'last_checked_at': _now(), 'last_signature': None if retryable_exc else signature}
				_log(directory, 'binding_sync_error', conversation_id=value['conversation_id'], project_root=value['project_root'], error=str(exc))
			try:
				with locked(directory / 'bindings.lock'):
					latest = _read(path)
					_validate_binding(latest)
					if any((latest[name] != value[name] for name in ('project_root', 'platform', 'native_backend', 'conversation_id'))):
						raise ValueError('Watcher binding owner changed during reconciliation; preserved')
					if any((latest.get(name) != value.get(name) for name in ('from_step', 'source_file', 'journal_directory'))):
						update['last_signature'] = None
					_save(path, {**latest, **update})
			except (OSError, ValueError, TypeError, KeyError, TimeoutError) as exc:
				result = {'valid': False, 'error': str(exc), 'binding': str(path)}
			results.append({'conversation_id': value['conversation_id'], **result})
	return {'valid': all((False is not r.get('valid') for r in results)), 'bindings_checked': len(results), 'dry_run': bool(dry_run), 'results': results}
def run(*, state_dir=None, token=None, interval=5):
	if not isinstance(interval, (int, float)) or not 0.1 <= interval <= 60:
		raise ValueError('Watcher interval must be between 0.1 and 60 seconds')
	if not isinstance(token, str) or 32 != len(token) or any((c not in '0123456789abcdef' for c in token)):
		raise ValueError('Watcher needs its explicit launch ownership token')
	directory = _folder(state_dir)
	with locked(directory / 'daemon.lock', timeout=0):
		initial_code = _code_digest()
		marker = {'schema_version': 1, 'pid': os.getpid(), 'token': token, 'started_at': _now(), 'status': 'running', 'script': str(PRIMARY / 'scripts/harness.py'), 'code_sha256': initial_code}
		_save(directory / 'daemon.json', marker)
		_log(directory, 'daemon_started', pid=os.getpid(), token=token, code_sha256=initial_code)
		try:
			while _read(directory / 'stop.json', {}).get('token') != token:
				current_code = _code_digest()
				if current_code != initial_code:
					_log(directory, 'code_digest_changed', pid=os.getpid(), token=token, old_sha256=initial_code, new_sha256=current_code)
					break
				try:
					result = once(state_dir=directory, stop_token=token)
					marker.update(last_scan_at=_now(), bindings_checked=result['bindings_checked'], last_scan_valid=result['valid'])
					marker.pop('last_error', None)
				except (OSError, ValueError, TimeoutError, sqlite3.Error) as exc:
					marker.update(last_scan_at=_now(), last_error=str(exc))
					_log(directory, 'daemon_error', pid=os.getpid(), token=token, error=str(exc))
				_save(directory / 'daemon.json', marker)
				deadline = time.monotonic() + interval
				while time.monotonic() < deadline:
					if _read(directory / 'stop.json', {}).get('token') == token:
						break
					time.sleep(min(0.1, max(0, deadline - time.monotonic())))
		finally:
			_save(directory / 'daemon.json', {**marker, 'status': 'stopped', 'stopped_at': _now()})
			_log(directory, 'daemon_stopped', pid=os.getpid(), token=token)
	r = {'status': 'stopped', 'token': token}
	return r
