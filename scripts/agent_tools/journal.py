"""Exact req/res pairs with reservations, recovery, and no overwrite mode."""

import hashlib
import json
from pathlib import Path
import uuid

from .storage import create_bytes, locked, replace_bytes


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_existing_step_ids(directory: Path) -> set[int]:
    return {int(p.stem) for folder, suffix in [('req', '.md'), ('res', '.md'),
                                              ('.journal', '.json')]
            for p in (Path(directory) / folder).glob(f'*{suffix}')
            if p.stem.isascii() and p.stem.isdigit()}


def _payload(request: str, response: str):
    for label, text in [('request', request), ('response', response)]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f'Empty {label}')
        text.encode('utf-8')


def _save_state(path: Path, state: dict):
    replace_bytes(path, json.dumps(state, ensure_ascii=False, indent=2).encode('utf-8'))


def _publish(directory: Path, step: int, state: dict, *, recovering=False):
    # A pending receipt is intentional: after a crash, recover using its token.
    for folder, key in [('req', 'request'), ('res', 'response')]:
        path = directory / folder / f'{step}.md'
        data = state[key].encode('utf-8')
        if path.exists():
            if not recovering or path.read_bytes() != data:
                raise FileExistsError(f'Conflicting file; preserved without changes: {path}')
        else:
            create_bytes(path, data)
        if path.read_bytes() != data:
            raise OSError(f'Read-back mismatch: {path}')
    state['status'] = 'complete'
    _save_state(directory / '.journal' / f'{step}.json', state)


def record_step(journal_dir: Path, req_content: str, res_content: str,
                target_step: int | None = None, allow_overwrite: bool = False) -> int:
    """Reserve and publish a pair; a token in the receipt permits explicit crash recovery."""
    _payload(req_content, res_content)
    if allow_overwrite:
        raise ValueError('Journal overwrite is unsupported; create a new corrective step')
    if target_step is not None and (type(target_step) is not int or target_step < 1):
        raise ValueError('Step must be a positive integer')
    directory = Path(journal_dir).resolve()
    for folder in ('req', 'res', '.journal'):
        (directory / folder).mkdir(parents=True, exist_ok=True)
    with locked(directory / '.journal' / 'writer.lock'):
        used = get_existing_step_ids(directory)
        step = target_step if target_step is not None else max(used, default=0) + 1
        if step in used:
            raise FileExistsError(f'Step {step} is occupied or reserved')
        state = {'version': 1, 'step': step, 'token': uuid.uuid4().hex,
                 'status': 'pending', 'request': req_content, 'response': res_content,
                 'request_sha256': digest(req_content.encode('utf-8')),
                 'response_sha256': digest(res_content.encode('utf-8'))}
        receipt = directory / '.journal' / f'{step}.json'
        create_bytes(receipt, json.dumps(state, ensure_ascii=False, indent=2).encode('utf-8'))
        try:
            _publish(directory, step, state)
        except Exception as exc:
            raise RuntimeError(f'Step {step} pending; recover with token {state["token"]}: {exc}') from exc
        return step


def recover_step(directory: Path, step: int, token: str):
    if step < 1:
        raise ValueError('Step must be positive')
    directory = Path(directory).resolve()
    with locked(directory / '.journal' / 'writer.lock'):
        state = json.loads((directory / '.journal' / f'{step}.json').read_text(encoding='utf-8'))
        if state['token'] != token or state['step'] != step:
            raise ValueError('Reservation token or step mismatch')
        _payload(state['request'], state['response'])
        for key in ('request', 'response'):
            if digest(state[key].encode('utf-8')) != state[key + '_sha256']:
                raise ValueError(f'Damaged reservation: {key}')
        _publish(directory, step, state, recovering=True)


def step_errors(directory: Path, step: int) -> list[str]:
    """Validate only this pair; never infer task authorization from its prose."""
    directory = Path(directory)
    if type(step) is not int or step < 1:
        return ['Step must be a positive integer']
    errors = []
    payloads = {}
    for folder, key in [('req', 'request'), ('res', 'response')]:
        path = directory / folder / f'{step}.md'
        try:
            data = path.read_bytes()
            if not data.decode('utf-8').strip():
                errors.append(f'Empty file: {path}')
            payloads[key] = data
        except (OSError, UnicodeError) as exc:
            errors.append(f'{path}: {exc}')
    receipt = directory / '.journal' / f'{step}.json'
    if receipt.exists():
        try:
            state = json.loads(receipt.read_text(encoding='utf-8'))
            if state['status'] != 'complete' or state['step'] != step:
                errors.append(f'Incomplete reservation: {receipt}')
            for key, data in payloads.items():
                if digest(data) != state[key + '_sha256']:
                    errors.append(f'Changed {key}: step {step}')
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
            errors.append(f'Invalid receipt {receipt}: {exc}')
    return errors


def validate_step(journal_dir, step_num) -> bool:
    errors = step_errors(Path(journal_dir), step_num)
    for error in errors:
        print(error)
    return not errors
