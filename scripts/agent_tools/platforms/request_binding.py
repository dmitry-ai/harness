"""Select exact native user inputs by observed roots and explicit project changes."""

import hashlib
import json
from pathlib import Path
import re


def text_project_id(root):
    """A stable internal workspace ID, deliberately not an Upwork job ID."""
    root = Path(root).resolve()
    return 'text-' + hashlib.sha256(str(root).encode('utf-8')).hexdigest()


def native_project_id(root):
    """Read an existing job identity or an explicitly initialized text workspace.

    Never creates project.json or guesses an Upwork identity for client prose.
    Native cwd/explicit user roots still establish the request's actual scope.
    """
    root = Path(root).resolve()
    job = root / 'ꘖ/project.json'
    if job.is_file():
        project = json.loads(job.read_text(encoding='utf-8-sig'))
        identifier = project.get('job_id') if isinstance(project, dict) else None
        if not isinstance(identifier, str) or not identifier.strip() or identifier.startswith('text-'):
            raise ValueError('Existing project.json needs its real Upwork job_id')
        return identifier
    marker = root / 'ꘖ/data/text-project.json'
    if not marker.is_file():
        raise ValueError('No native project identity; initialize an explicit text workspace first')
    value = json.loads(marker.read_text(encoding='utf-8-sig'))
    if (not isinstance(value, dict) or type(value.get('schema_version')) is not int or value['schema_version'] != 1 or
            value.get('kind') != 'client_text_workspace' or
            not _same_root(value.get('project_root'), root) or value.get('id') != text_project_id(root)):
        raise ValueError('Text workspace marker has the wrong root, kind, schema or internal ID')
    return value['id']


def native_project_fields(root):
    """Keep the legacy job_id field honest while recording both project kinds."""
    identifier = native_project_id(root)
    is_text = identifier.startswith('text-')
    return {'project_id': identifier,
            'project_kind': 'client_text_workspace' if is_text else 'upwork_job',
            'job_id': None if is_text else identifier}


def _same_root(value, root):
    if not isinstance(value, str) or not value.strip() or not Path(value).is_absolute():
        return False
    return Path(value).resolve() == Path(root).resolve()


def _explicit(text, root, job_id):
    commands = re.findall(r'(?:/|\$)upwork-init\s+https?://[^\s]*?~(\d+)', text)
    if commands:
        return all('~' + ident == job_id for ident in commands), 'explicit-upwork-init'
    declarations = re.findall(r'(?im)(?:корень проекта|project root|проект)\s*:\s*([^\r\n]+)', text)
    if declarations:
        paths = [value.strip().strip('`"<>«»') for value in declarations]
        return all(_same_root(value, root) for value in paths), 'explicit-project-root'
    return None, None


def scoped_inputs(root, job_id, inputs, contexts=(), *, until=None):
    """A repeated native cwd never cancels a user's explicit selection of another job."""
    events = [(step, 1, text, None) for step, text in inputs if until is None or step <= until]
    events += [(step, 0, path, source) for step, path, source in contexts if until is None or step <= until]
    events.sort(key=lambda item: (item[0], item[1]))
    legacy = not any(kind == 0 for _, kind, _, _ in events)
    selected, active, previous_root, binding = [], False, object(), None
    for step, kind, value, source in events:
        if kind == 0:
            normalized = str(Path(value).resolve()) if value else None
            if normalized != previous_root:
                previous_root, active = normalized, _same_root(normalized, root)
                binding = {'kind': source, 'native_step': step, 'root': normalized}
            continue
        choice, source = _explicit(value, root, job_id)
        if choice is not None:
            active, legacy = choice, False
            binding = {'kind': source, 'native_step': step, 'root': str(Path(root).resolve())}
        elif legacy and not active and not job_id.startswith('text-') and job_id in value:
            active = True
            binding = {'kind': 'legacy-native-job-id', 'native_step': step, 'job_id': job_id}
        if active and value.strip():
            selected.append((step, value, dict(binding)))
    return selected, active, binding
