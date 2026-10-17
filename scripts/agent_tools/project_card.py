"""Publish owned blocks without replacing surrounding manual text."""

from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import re

from .storage import locked, replace_bytes


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def sync_block(root, target, key, content, position='after-title', *, check=False, source=None, attributes=None):
    """Own only a delimited block. A check never writes files, receipts or lock files."""
    root = Path(root).resolve()
    target = (root / target).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Managed KB block must stay inside the project')
    if position not in ('start', 'after-title', 'append') or not re.fullmatch(r'[a-z][a-z0-9-]*', key):
        raise ValueError('Known block position and a lowercase block key required')
    if not isinstance(content, str) or '<!-- upwork-init:' in content:
        raise ValueError('Managed block content must be text without reserved markers')
    directory = root / 'ꘖ/data'
    receipt_path = directory / 'rendered.json'
    result = {'target': str(target), 'block': key}

    def conflict(detail):
        return {**result, 'status': 'conflict', 'detail': detail}

    with (nullcontext() if check else locked(directory / 'render.lock')):
        try:
            receipts = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
            if not isinstance(receipts, dict):
                return conflict('Malformed publication receipt; preserved')
            entry = receipts.get(str(target), {})
            if not isinstance(entry, dict) or not isinstance(entry.get('managed_blocks', {}), dict):
                return conflict('Malformed block ownership receipt; preserved')
            blocks = entry.get('managed_blocks', {})
            owned = blocks.get(key)
            if owned is not None and (not isinstance(owned, dict) or not re.fullmatch(r'[a-f0-9]{64}', str(owned.get('sha256', '')))):
                return conflict('Malformed block ownership hash; preserved')
            previous = target.read_bytes() if target.exists() else b''
            previous.decode('utf-8-sig')
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            return conflict(f'Cannot read existing publication safely: {type(error).__name__}')

        newline = b'\r\n' if b'\r\n' in previous else b'\n'
        start = f'<!-- upwork-init:{key}:start -->'.encode()
        end = f'<!-- upwork-init:{key}:end -->'.encode()
        body = content.replace('\r\n', '\n').rstrip('\n').encode().replace(b'\n', newline)
        block = start + newline + newline + body + newline + end + newline
        if previous.count(start) or previous.count(end):
            if previous.count(start) != 1 or previous.count(end) != 1 or previous.index(start) > previous.index(end):
                return conflict('Malformed or repeated managed markers; surrounding text preserved')
            first, last = previous.index(start), previous.index(end) + len(end)
            if previous[last:last + len(newline)] == newline:
                last += len(newline)
            current = previous[first:last]
            if current != block and (not owned or _digest(current) != owned['sha256']):
                return conflict('Managed block was manually changed or is unowned; reconcile explicitly')
            payload = previous[:first] + block + previous[last:]
        else:
            if owned and previous:
                return conflict('Previously published block was removed; manual text preserved')
            offset = 3 if previous.startswith(b'\xef\xbb\xbf') else 0
            if position == 'append':
                offset = len(previous)
            elif position == 'after-title' and previous[offset:].startswith(b'# '):
                end_of_title = previous.find(b'\n', offset)
                offset = end_of_title + 1 if end_of_title >= 0 else len(previous)
            prefix, suffix = previous[:offset], previous[offset:]
            before = newline if prefix and not prefix.endswith(newline * 2) else b''
            # A last title without a newline needs its own line terminator, too.
            if prefix and not prefix.endswith(newline):
                before = newline * 2
            after = newline if suffix and not suffix.startswith(newline) else b''
            payload = prefix + before + block + after + suffix

        metadata = {'sha256': _digest(block), 'source': str(source) if source is not None else None}
        if attributes is not None:
            metadata['data'] = attributes
        changed = payload != previous
        receipt_changed = owned != metadata
        if check:
            return {**result, 'status': 'stale' if changed or receipt_changed else 'unchanged',
                    'sha256': _digest(block), 'detail': 'Read-only comparison; no files written'}
        if (target.read_bytes() if target.exists() else b'') != previous:
            return conflict('Target changed during publication; external edit preserved')
        if changed:
            replace_bytes(target, payload)
        if target.read_bytes() != payload:
            return conflict('Publication read-back differs; inspect the target before retrying')
        if receipt_changed:
            entry.setdefault('managed_blocks', {})[key] = metadata
            receipts[str(target)] = entry
            replace_bytes(receipt_path, (json.dumps(receipts, ensure_ascii=False, indent=2) + '\n').encode())
        return {**result, 'status': 'published' if changed else 'unchanged', 'sha256': _digest(block)}

