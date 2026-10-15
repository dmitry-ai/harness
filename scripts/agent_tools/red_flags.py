"""Explicit, evidence-linked project screening; never infer flags from keywords."""

from pathlib import Path
import json

from .diagnostics import problem
from .storage import create_bytes, locked, replace_bytes

FLAGS = {
    'RF-CLIENT-INTERMEDIARY': ('Клиент — посредник', ('confirmed', 'suspected')),
    'RF-WEBSITE-UNIDENTIFIED': ('Сайт, над которым предстоит работать, не установлен', ('unresolved',)),
}
STATUSES = {'confirmed': 'подтверждено', 'suspected': 'гипотеза', 'unresolved': 'не установлен по доступным данным'}
START = b'<!-- upwork-init:red-flags:start -->'
END = b'<!-- upwork-init:red-flags:end -->'


def red_flag_issues(value, claims):
    if 'red_flags' not in value:
        return []  # Legacy analyses are unassessed, not evidence of no flags.
    flags = value['red_flags']
    if not isinstance(flags, list):
        return [problem('red_flags.list', '/red_flags', 'red_flags must be a list')]
    issues, seen = [], set()
    for index, flag in enumerate(flags):
        field = f'/red_flags/{index}'
        if not isinstance(flag, dict):
            issues.append(problem('red_flags.object', field, 'A red flag must be an object'))
            continue
        ident = flag.get('id')
        if not isinstance(ident, str) or ident not in FLAGS or ident in seen:
            issues.append(problem('red_flags.id', field + '/id', 'Unknown or duplicate red flag ID'))
        else:
            seen.add(ident)
            if flag.get('status') not in FLAGS[ident][1]:
                issues.append(problem('red_flags.status', field + '/status', 'Use the status allowed for this flag'))
        if not isinstance(flag.get('summary'), str) or not flag['summary'].strip():
            issues.append(problem('red_flags.summary', field + '/summary', 'Explain this project-specific risk'))
        refs = flag.get('basis_ids')
        if (not isinstance(refs, list) or not refs
                or any(not isinstance(ref, str) or claims.get(ref) != 'identity' for ref in refs)):
            issues.append(problem('red_flags.basis', field + '/basis_ids', 'Reference existing identity claims with evidence'))
    return issues


def render_red_flags(value, *, project_card=False):
    flags = value.get('red_flags', [])
    if not flags:
        return ''
    by_id = {flag['id']: flag for flag in flags}
    lines = [f'{"##" if project_card else "#"} Red Flags — {len(flags)}', '']
    if len(by_id) == 2:
        qualifier = ' (посредничество пока является гипотезой)' if by_id['RF-CLIENT-INTERMEDIARY']['status'] == 'suspected' else ''
        lines += [f'**Оба Red Flags одновременно{qualifier}: высокая вероятность отказа от проекта.**', '']
    pointers = {claim['id']: f'ꘖ/KB/Analysis.json#/identity/{index}' for index, claim in enumerate(value['identity'])}
    for ident in FLAGS:
        if ident not in by_id:
            continue
        flag = by_id[ident]
        lines += [f'- **{FLAGS[ident][0]}.** Статус: {STATUSES[flag["status"]]}.',
                  '  ' + flag['summary'].strip().replace('\n', '\n  '),
                  '  Основания: ' + ', '.join(f'[{ref}](<{pointers[ref] if project_card else "#" + ref.lower()}>)' for ref in flag['basis_ids']) + '.', '']
    return '\n'.join(lines) + '\n'


def sync_project_red_flags(root, value):
    """Own only a marked block; preserve all other card bytes, including user edits."""
    from .analysis import digest, validate_analysis
    validate_analysis(value)
    root = Path(root).resolve()
    target = root / '.md'
    if 'red_flags' not in value:
        return {'status': 'unassessed', 'target': str(target)}
    state_dir = root / 'ꘖ/data'
    state_file = state_dir / 'red-flags.json'
    with locked(state_dir / 'red-flags.lock'):
        original = target.read_bytes()
        original.decode('utf-8-sig')  # Do not replace a card with an unknown encoding.
        newline = b'\r\n' if b'\r\n' in original else b'\n'
        content = render_red_flags(value, project_card=True).encode('utf-8').replace(b'\n', newline)
        block = START + newline + newline + content + END + newline + newline if content else b''
        current, body = b'', original
        if START in original or END in original:
            if original.count(START) != 1 or original.count(END) != 1 or original.index(START) > original.index(END):
                return {'status': 'conflict', 'target': str(target), 'detail': 'Malformed Red Flags block; card preserved'}
            start, end = original.index(START), original.index(END) + len(END)
            if original[end:end + len(newline) * 2] == newline * 2:
                end += len(newline) * 2
            current = original[start:end]
            body = original[:start] + original[end:]
            receipt = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
            if current != block and digest(current) != receipt.get('block_sha256'):
                return {'status': 'conflict', 'target': str(target), 'detail': 'Red Flags block was manually edited; reconcile it explicitly'}
        offset = 3 if body.startswith(b'\xef\xbb\xbf') else 0
        if body[offset:].startswith(b'# ') and b'\n' in body[offset:]:
            offset = body.index(b'\n', offset) + 1
        payload = body[:offset] + block + body[offset:]
        if payload != original:
            archive = state_dir / 'red-flags-history' / (digest(original) + '.md')
            archive.parent.mkdir(parents=True, exist_ok=True)
            if not archive.exists():
                create_bytes(archive, original)
            if target.read_bytes() != original:
                raise ValueError('Project card changed during publication; reread and reconcile')
            replace_bytes(target, payload)
        if target.read_bytes() != payload:
            raise OSError('Project card failed read-back verification')
        replace_bytes(state_file, (json.dumps({'block_sha256': digest(block)}, indent=2) + '\n').encode())
    return {'status': 'unchanged' if payload == original else 'published', 'target': str(target), 'sha256': digest(payload)}
