"""Exact req/res pairs with reservations, recovery, and no overwrite mode."""

import hashlib
import json
from pathlib import Path
import uuid

from .storage import create_bytes, data_dir_for, locked, replace_bytes


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def state_dir(directory: Path) -> Path:
    identity = str(Path(directory).resolve()).casefold()
    return data_dir_for(directory) / '.journal' / digest(identity.encode('utf-8'))[:24]


def get_existing_step_ids(directory: Path) -> set[int]:
    directory = Path(directory)
    sources = [(directory / 'req', '.md'), (directory / 'res', '.md'),
               (state_dir(directory), '.json')]
    ids = {int(p.stem) for folder, suffix in sources if folder.exists()
            for p in folder.glob(f'*{suffix}')
            if p.stem.isascii() and p.stem.isdigit()}
    for file in (state_dir(directory) / 'answer-groups').glob('*.json'):
        group = json.loads(file.read_text(encoding='utf-8'))
        if group.get('journal') != str(directory.resolve()) or not isinstance(group.get('steps'), list) or any(type(x) is not int or x < 1 for x in group['steps']):
            raise ValueError('Damaged answer-group reservation')
        ids.update(group['steps'])
    return ids


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


def record_answer(directory, requests, response, turn, request_ids=None):
    """Explicitly link several exact requests to one real final answer; crash-recoverable."""
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', turn) or not isinstance(requests, list) or not requests:
        raise ValueError('Stable turn ID and nonempty exact request list required')
    for request in requests:
        _payload(request, response)
    if request_ids is not None and (len(request_ids) != len(requests) or any(not isinstance(x, str) or not x for x in request_ids)):
        raise ValueError('Request IDs must match the exact request list')
    directory = Path(directory).resolve()
    journal_state = state_dir(directory)
    groups = journal_state / 'answer-groups'
    for path in (directory / 'req', directory / 'res', groups):
        path.mkdir(parents=True, exist_ok=True)
    file = groups / (turn + '.json')
    with locked(journal_state / 'writer.lock'):
        if file.exists():
            group = json.loads(file.read_text(encoding='utf-8'))
            if group.get('journal') != str(directory) or group.get('requests') != requests or group.get('request_ids') != request_ids or group.get('response_sha256') != digest(response.encode()):
                raise ValueError('Answer group differs from its original journal/requests/response; preserve it')
        else:
            start = max(get_existing_step_ids(directory), default=0) + 1
            group = {'version': 1, 'journal': str(directory), 'turn': turn, 'status': 'pending',
                     'steps': list(range(start, start + len(requests))), 'requests': requests,
                     'response_sha256': digest(response.encode()), 'tokens': [uuid.uuid4().hex for _ in requests], 'request_ids': request_ids}
            create_bytes(file, json.dumps(group, ensure_ascii=False, indent=2).encode())
        for step, request, token in zip(group['steps'], requests, group['tokens']):
            receipt = journal_state / f'{step}.json'
            state = {'version': 2, 'journal': str(directory), 'step': step, 'token': token,
                     'status': 'pending', 'request': request, 'response': response,
                     'request_sha256': digest(request.encode()), 'response_sha256': digest(response.encode())}
            if group['status'] == 'complete':
                for sub, text in [('req', request), ('res', response)]:
                    if (directory / sub / f'{step}.md').read_bytes() != text.encode():
                        raise ValueError('Completed answer group changed; journal is preserved')
                continue
            if receipt.exists():
                saved = json.loads(receipt.read_text(encoding='utf-8'))
                if saved != state:
                    raise ValueError('Reserved answer step belongs to another payload; preserved')
            else:
                # A successful earlier member may already have removed its reservation.
                req, res = directory / 'req' / f'{step}.md', directory / 'res' / f'{step}.md'
                if req.exists() and res.exists():
                    if req.read_bytes() == request.encode() and res.read_bytes() == response.encode():
                        continue
                    raise ValueError('Answer-group step is occupied; preserved')
                create_bytes(receipt, json.dumps(state, ensure_ascii=False, indent=2).encode())
            _publish(directory, step, state, recovering=True)
        group['status'] = 'complete'
        replace_bytes(file, json.dumps(group, ensure_ascii=False, indent=2).encode())
    return group['steps']


def answer_groups(directory):
    """Read grouped-answer provenance; pending groups block external export."""
    directory = Path(directory).resolve()
    groups = []
    for path in sorted((state_dir(directory) / 'answer-groups').glob('*.json')):
        group = json.loads(path.read_text(encoding='utf-8'))
        if group.get('journal') != str(directory) or group.get('status') != 'complete':
            raise ValueError('Incomplete or mismatched answer group; recover it before context export')
        for step, request in zip(group['steps'], group['requests']):
            if (directory / 'req' / f'{step}.md').read_bytes() != request.encode() or digest((directory / 'res' / f'{step}.md').read_bytes()) != group['response_sha256']:
                raise ValueError('Answer group source bytes changed; preserve context')
        groups.append(group)
    return groups
