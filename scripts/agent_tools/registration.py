"""Durable registration of one workspace in each configured native application."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from .runtime import platform_name, request_day, settings
from .storage import locked, replace_bytes


class RegistrationConflict(ValueError):
    def __init__(self, message, *, expected, actual, issues):
        super().__init__(message)
        self.expected, self.actual, self.issues = expected, actual, issues


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def _expected(project, label=None, day=None):
    root = Path(project).resolve()
    if not root.is_dir():
        raise ValueError('Registration requires an existing project directory')
    if day is None:
        state = json.loads((root / 'ꘖ/project.json').read_text(encoding='utf-8'))
        day = state['request_date']
    day = request_day(day)
    label = label or root.name.split(' - ', 1)[-1]
    return root, label, day.isoformat(), {
        'project_name': f'{label} - U.P.{day:%Y.%m.%d}',
        'root_paths': [str(root)],
        'folder_path': f'Upwork / Proposals / {day:%Y / %m / %d}',
    }


def _complete(result):
    if result.get('complete') is False:
        return False
    if isinstance(result.get('profiles'), dict):
        profile = result.get('profile')
        return bool(profile and result['profiles'].get(profile, {}).get('ready'))
    return bool(result.get('complete', result.get('project_id') and result.get('folder_id')))


def validate_registration(project, label, day, platform, result):
    """Check what the adapter actually returned; never silently rename native projects."""
    root, _, _, expected = _expected(project, label, day)
    if not isinstance(result, dict):
        raise ValueError('Native registration receipt must be a JSON object')
    value, issues = deepcopy(result), []
    roots = value.get('root_paths')
    if platform == 'antigravity' and value.get('project_file'):
        native = json.loads(Path(value['project_file']).read_text(encoding='utf-8-sig'))
        from .platforms.antigravity import folder_path
        roots = [str(folder_path(item['folderUri'])) for item in
                 native.get('projectResources', {}).get('resources', []) if item.get('folderUri')]
        if native.get('name') != value.get('project_name'):
            issues.append('Native project name differs from the registration receipt')
        if native.get('id') and native['id'] != value.get('project_id'):
            issues.append('Native project ID differs from the registration receipt')
    value['root_paths'] = roots
    try:
        normalized_roots = [str(Path(path).resolve()) for path in roots] if isinstance(roots, list) else None
    except (TypeError, ValueError):
        normalized_roots = None
    if normalized_roots != expected['root_paths']:
        issues.append('Native project roots differ from the requested workspace')
    if value.get('project_name') != expected['project_name']:
        issues.append('Native project name differs from the requested name; manual name preserved')
    if value.get('folder_path') != expected['folder_path'] or not value.get('folder_id'):
        issues.append('Native folder assignment differs from the requested branch')
    identity = 'shared_id' if platform == 'codex' else 'project_id'
    if not value.get(identity):
        issues.append('Native registration did not confirm its project identity')
    if platform == 'codex':
        profiles = value.get('profiles')
        binding = profiles.get(value.get('profile')) if isinstance(profiles, dict) else None
        if not isinstance(binding, dict) or not binding.get('project_id'):
            issues.append('Shared-Projects did not confirm the selected profile native identity')
    if issues:
        raise RegistrationConflict('; '.join(issues), expected=expected, actual=value, issues=issues)
    value['root_paths'] = normalized_roots
    value['complete'] = _complete(value)
    value['status'] = 'registered' if value['complete'] else 'pending'
    return value


def _read(root):
    path = root / 'ꘖ/data/registrations.json'
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError('Registrations must be a map of platform receipts')
    return path, data


def _write(path, data):
    replace_bytes(path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def _success(previous):
    if previous.get('last_success'):
        return deepcopy(previous['last_success'])
    if _complete(previous):
        return {key: deepcopy(value) for key, value in previous.items()
                if key not in ('intent', 'attempt', 'attempts', 'attempt_history', 'last_success')}
    return None


def _begin(root, platform, intent):
    with locked(root / 'ꘖ/data/registration.lock'):
        path, data = _read(root)
        previous = data.get(platform, {})
        history = deepcopy(previous.get('attempt_history', []))
        prior_attempt = previous.get('attempt')
        if prior_attempt and not any(part.get('id') == prior_attempt['id'] for part in history):
            history.append(deepcopy(prior_attempt))
        attempt = {'id': str(uuid.uuid4()), 'started_at': _now(), 'status': 'attempting',
                   'intent': deepcopy(intent)}
        entry = {'platform': platform, 'intent': intent, 'attempt': attempt,
                 'attempts': previous.get('attempts', 0) + 1,
                 'attempt_history': history,
                 'status': 'attempting', 'complete': False}
        success = _success(previous)
        if success:
            entry['last_success'] = success
        data[platform] = entry
        _write(path, data)
        return deepcopy(entry)


def save_registration(root, platform, result):
    """Publish a flat receipt, preserving completed native identity after an error."""
    root = Path(root).resolve()
    platform = platform_name(platform)
    with locked(root / 'ꘖ/data/registration.lock'):
        path, data = _read(root)
        previous = data.get(platform, {})
        value = deepcopy(result)
        attempt = value.get('attempt') or {'id': str(uuid.uuid4()), 'started_at': _now()}
        value['complete'] = _complete(value)
        value.setdefault('status', 'registered' if value['complete'] else 'pending')
        attempt.update(finished_at=_now(), status=value['status'])
        if value.get('error'):
            attempt['error'] = value['error']
        value.update(platform=platform, attempt=attempt,
                     attempts=previous.get('attempts', 0) + (0 if result.get('attempt') else 1))
        value.setdefault('intent', previous.get('intent', {}))
        history = [part for part in previous.get('attempt_history', []) if part.get('id') != attempt['id']]
        value['attempt_history'] = [*history, deepcopy(attempt)]
        success = ({key: deepcopy(part) for key, part in value.items()
                    if key not in ('intent', 'attempt', 'attempts', 'attempt_history', 'last_success')}
                   if value['complete'] else _success(previous))
        if success:
            value['last_success'] = success
        # A slower older native call must not erase a later attempt's current state.
        current_id = previous.get('attempt', {}).get('id')
        if result.get('attempt') and current_id and current_id != attempt['id']:
            previous['attempt_history'] = value['attempt_history']
            if success:
                previous['last_success'] = success
            data[platform] = previous
        else:
            data[platform] = value
        _write(path, data)
        return deepcopy(value)


def _attempt(root, label, day, target, expected, registrar):
    started = _begin(root, target, deepcopy(expected))
    error = None
    try:
        if registrar is None:
            from .platforms import adapter
            registrar = adapter(target).register
        result = validate_registration(root, label, day, target, registrar(root, label, day))
    except Exception as exc:
        error = exc
        result = {'status': 'conflict' if isinstance(exc, RegistrationConflict) else 'error',
                  'complete': False, 'error': {'type': type(exc).__name__, 'message': str(exc)}}
        if isinstance(exc, RegistrationConflict):
            result.update(expected=exc.expected, actual=exc.actual, issues=exc.issues)
    result.update(intent=started['intent'], attempt=started['attempt'])
    return save_registration(root, target, result), error


def register_project(project, label=None, day=None, *, platform=None):
    """Compatibility entry point: one adapter; persist and re-raise native failures."""
    active = platform_name(platform)
    root, label, day, expected = _expected(project, label, day)
    result, error = _attempt(root, label, day, active, expected, None)
    if error:
        raise error
    return result


def register_projects(project, label=None, day=None, *, platform=None, targets=None, registrars=None):
    """Register all targets while only the active application's result gates work."""
    active, config = platform_name(platform), settings()
    chosen = list(dict.fromkeys(targets if targets is not None else config['registration']['targets']))
    if active not in chosen:
        raise ValueError('Registration targets must include the active application')
    if any(target not in config['platforms'] for target in chosen):
        raise ValueError('Unknown registration target')
    root, label, day, expected = _expected(project, label, day)
    results = {}
    # Complete the current application's attempt first, even if another UI is offline.
    for target in [active, *(name for name in chosen if name != active)]:
        results[target], _ = _attempt(root, label, day, target, expected, (registrars or {}).get(target))
    return {**results[active], 'platform': active, 'targets': chosen, 'registrations': results,
            'complete': results[active]['complete'],
            'all_registered': all(result['complete'] for result in results.values())}
