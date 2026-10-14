"""Preserve the actual draft bytes once per explicitly named turn."""

import hashlib
import json
from pathlib import Path
import re

from .storage import create_bytes, data_dir_for, locked, replace_bytes


def snapshot_draft(source: Path, turn: str) -> Path:
    source = Path(source).resolve(strict=True)
    if source.name != 'draft.md':
        raise ValueError('Expected an explicit draft.md path')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', turn):
        raise ValueError('Turn ID must contain 1..80 ASCII letters, digits, _ or -')
    snapshots = data_dir_for(source) / '.draft-snapshots'
    archive = snapshots / turn
    archive.mkdir(parents=True, exist_ok=True)
    saved = archive / 'draft.md'
    previous = source.with_name('draft.prev.md')
    with locked(snapshots / 'writer.lock'):
        if saved.exists():
            receipt = json.loads((archive / 'snapshot.json').read_text(encoding='utf-8'))
            if hashlib.sha256(saved.read_bytes()).hexdigest() != receipt['sha256']:
                raise ValueError('Snapshot changed after capture')
            if previous.read_bytes() != saved.read_bytes():
                raise ValueError('draft.prev.md changed; preserve both versions before continuing')
            return saved
        data = source.read_bytes()
        create_bytes(saved, data)
        create_bytes(archive / 'snapshot.json', json.dumps({
            'source': str(source), 'turn': turn,
            'sha256': hashlib.sha256(data).hexdigest()
        }, ensure_ascii=False, indent=2).encode('utf-8'))
        if source.read_bytes() != data:
            raise ValueError('Source changed during capture; snapshot retained for inspection')
        replace_bytes(previous, data)
        if previous.read_bytes() != data or saved.read_bytes() != data:
            raise OSError('Snapshot read-back failed')
        return saved
