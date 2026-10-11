"""Check statement artifacts without pretending to verify factual evidence."""

from pathlib import Path


def validate_statements(directory: Path) -> list[str]:
    directory = Path(directory)
    if not directory.is_dir():
        return [f'Missing statement directory: {directory}']
    entries = sorted(p for p in directory.iterdir() if p.is_dir() and p.name.isdigit())
    if not entries:
        return [f'No statement directories: {directory}']
    errors = []
    for entry in entries:
        for name in ('.md', 'Test.md'):
            path = entry / name
            try:
                if not path.read_text(encoding='utf-8').strip():
                    errors.append(f'Empty file: {path}')
            except (OSError, UnicodeError) as exc:
                errors.append(f'{path}: {exc}')
    return errors
