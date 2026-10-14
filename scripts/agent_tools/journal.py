"""Exact req/res pairs with reservations, recovery, and no overwrite mode."""

import hashlib
import json
from pathlib import Path
import uuid

from .storage import create_bytes, data_dir_for, locked


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def state_dir(directory: Path) -> Path:
    identity = str(Path(directory).resolve()).casefold()
    return data_dir_for(directory) / '.journal' / digest(identity.encode('utf-8'))[:24]


def get_existing_step_ids(directory: Path) -> set[int]:
    directory = Path(directory)
    sources = [(directory / 'req', '.md'), (directory / 'res', '.md'),
               (state_dir(directory), '.json')]
    return {int(p.stem) for folder, suffix in sources if folder.exists()
            for p in folder.glob(f'*{suffix}')
            if p.stem.isascii() and p.stem.isdigit()}


def _payload(request: str, response: str):
    for label, text in [('request', request), ('response', response)]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f'Empty {label}')
        text.encode('utf-8')


def _publish(directory: Path, step: int, state: dict, *, recovering=False):
    # A pending receipt exists only during publication or after a crash before completion.
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
    (state_dir(directory) / f'{step}.json').unlink(missing_ok=True)


def record_step(journal_dir: Path, req_content: str, res_content: str,
                target_step: int | None = None, allow_overwrite: bool = False) -> int:
    """Reserve and publish a pair; a token in the receipt permits explicit crash recovery."""
    _payload(req_content, res_content)
    if allow_overwrite:
        raise ValueError('Journal overwrite is unsupported; create a new corrective step')
    if target_step is not None and (type(target_step) is not int or target_step < 1):
        raise ValueError('Step must be a positive integer')
    directory = Path(journal_dir).resolve()
    journal_state = state_dir(directory)
    for folder in (directory / 'req', directory / 'res', journal_state):
        folder.mkdir(parents=True, exist_ok=True)
    with locked(journal_state / 'writer.lock'):
        used = get_existing_step_ids(directory)
        step = target_step if target_step is not None else max(used, default=0) + 1
        if step in used:
            raise FileExistsError(f'Step {step} is occupied or reserved')
        state = {'version': 2, 'journal': str(directory), 'step': step, 'token': uuid.uuid4().hex,
                 'status': 'pending', 'request': req_content, 'response': res_content,
                 'request_sha256': digest(req_content.encode('utf-8')),
                 'response_sha256': digest(res_content.encode('utf-8'))}
        receipt = journal_state / f'{step}.json'
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
    journal_state = state_dir(directory)
    with locked(journal_state / 'writer.lock'):
        receipt = journal_state / f'{step}.json'
        state = json.loads(receipt.read_text(encoding='utf-8'))
        if (state.get('journal') != str(directory) or state['token'] != token
                or state['step'] != step):
            raise ValueError('Reservation journal, token or step mismatch')
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
    for folder in ('req', 'res'):
        path = directory / folder / f'{step}.md'
        try:
            data = path.read_bytes()
            if not data.decode('utf-8').strip():
                errors.append(f'Empty file: {path}')
        except (OSError, UnicodeError) as exc:
            errors.append(f'{path}: {exc}')
    receipt = state_dir(directory) / f'{step}.json'
    if receipt.exists():
        errors.append(f'Incomplete reservation: {receipt}')
    return errors


def validate_step(journal_dir, step_num) -> bool:
    errors = step_errors(Path(journal_dir), step_num)
    for error in errors:
        print(error)
    return not errors
