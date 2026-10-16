"""Select exact native user inputs by observed roots and explicit project changes."""

from pathlib import Path
import re


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
        elif legacy and not active and job_id in value:
            active = True
            binding = {'kind': 'legacy-native-job-id', 'native_step': step, 'job_id': job_id}
        if active and value.strip():
            selected.append((step, value, dict(binding)))
    return selected, active, binding
