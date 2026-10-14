"""Assemble complete sources using a project-owned JSON manifest."""

from datetime import datetime, timezone
import json
from pathlib import Path
import re

from .storage import data_dir_for, locked, replace_bytes
from .journal import get_existing_step_ids, step_errors


def inside(root: Path, path: str | Path) -> Path:
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes project root: {path}')
    return target


def resolve_letter_file(path: Path, languages=('EN', 'RU')) -> Path | None:
    path = Path(path)
    if path.is_file():
        chosen = path.with_name('final.md') if path.name == 'draft.md' and path.with_name('final.md').exists() else path
    elif path.is_dir():
        chosen = None
        for directory in [*(path / 'result' / language for language in languages), path]:
            for name in ('final.md', 'draft.md', '.md'):
                candidate = directory / name
                if candidate.exists():
                    chosen = candidate
                    break
            if chosen is not None:
                break
        if chosen is None:
            return None
    else:
        return None
    if not chosen.is_file() or not chosen.read_text(encoding='utf-8').strip():
        raise ValueError(f'Chosen letter is empty or not a file: {chosen}')
    return chosen


def discover_letters(root: Path, languages=('EN', 'RU')) -> list[Path]:
    if not root.is_dir():
        raise FileNotFoundError(root)
    groups = set()
    for path in root.rglob('*.md'):
        if path.name not in ('final.md', 'draft.md', '.md'):
            continue
        parent = path.parent
        if parent.name in languages and parent.parent.name == 'result':
            parent = parent.parent.parent
        elif parent.parent.name == 'result':
            continue
        groups.add(parent)
    return [chosen for group in sorted(groups)
            if (chosen := resolve_letter_file(group, languages)) is not None]


def _fence(text: str) -> str:
    return '`' * max(3, max((len(m.group()) + 1 for m in re.finditer(r'`+', text)), default=3))


def assemble(root: Path, manifest: dict, now: datetime | None = None) -> tuple[str, list[Path]]:
    root = Path(root).resolve()
    if manifest.get('version') != 1 or not manifest.get('sections'):
        raise ValueError('Context manifest requires version=1 and nonempty sections')
    timestamp = (now or datetime.now(timezone.utc)).isoformat(timespec='seconds')
    blocks = [f'# Context\n\nGenerated: {timestamp}\n']
    selected = []
    seen = set()
    for section in manifest['sections']:
        items = [(inside(root, path), None) for path in section.get('files', [])]
        for pattern in section.get('globs', []):
            if Path(pattern).is_absolute() or '..' in Path(pattern).parts:
                raise ValueError(f'Invalid glob: {pattern}')
            matches = sorted(p for p in root.glob(pattern) if p.is_file())
            if not matches and not section.get('optional', False):
                raise FileNotFoundError(f'No sources match {pattern}')
            items.extend((inside(root, p), None) for p in matches)
        for journal_rel in section.get('journals', []):
            jdir = inside(root, journal_rel)
            if not jdir.is_dir():
                if section.get('optional', False):
                    continue
                raise FileNotFoundError(f'Missing journal directory: {journal_rel}')
            step_ids = sorted(get_existing_step_ids(jdir))
            for step_id in step_ids:
                errors = step_errors(jdir, step_id)
                if errors:
                    raise ValueError('Incomplete journal; context preserved: ' + '; '.join(errors))
                for sub, role in (('req', 'User (req)'), ('res', 'Agent (res)')):
                    candidate = jdir / sub / f'{step_id}.md'
                    if candidate.is_file() and candidate.read_text(encoding='utf-8').strip():
                        items.append((inside(root, candidate), role))
        for group in section.get('letters', []):
            directory = inside(root, group['root'])
            if not directory.is_dir() and section.get('optional', False):
                continue
            items.extend((inside(root, p), group['author']) for p in discover_letters(
                directory, group.get('languages', ['EN', 'RU'])))
        items = [(p, author) for p, author in items if not any(
            p.relative_to(root).match(pattern) for pattern in section.get('exclude', []))]
        if not items:
            if not section.get('optional', False):
                raise ValueError(f'Empty source section: {section["title"]}')
            continue
        blocks.append(f'\n# {section["title"]}\n')
        for source, author in items:
            if source in seen:
                continue
            seen.add(source)
            content = source.read_bytes().decode('utf-8')
            if not content.strip():
                raise ValueError(f'Empty source: {source}')
            selected.append(source)
            fence = _fence(content)
            label = source.relative_to(root).as_posix()
            blocks.append(f'\n## {label}\n')
            if author:
                blocks.append(f'\nAuthor: {author}\n')
            # Keep source text intact, including headings and code fences.
            blocks.append(f'\n{fence}markdown\n{content}')
            blocks.append(('' if content.endswith('\n') else '\n') + f'{fence}\n')
    if not selected:
        raise ValueError('No sources selected')
    return ''.join(blocks), selected


def generate(root: Path, config: Path, output: Path | None = None, dry_run=False):
    root = Path(root).resolve()
    manifest = json.loads(Path(config).read_text(encoding='utf-8-sig'))
    def build():
        content, sources = assemble(root, manifest)
        target = inside(root, output if output is not None else manifest['output'])
        if target in sources or target == Path(config).resolve():
            raise ValueError('Context output would overwrite an input')
        if not dry_run:
            replace_bytes(target, content.encode('utf-8'))
        return target, content, sources
    if dry_run:
        return build()
    with locked(data_dir_for(root) / 'context.lock'):
        return build()
