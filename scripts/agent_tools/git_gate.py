"""Commit only an exact staged file set, with explicit repository and paths."""

from pathlib import Path
import subprocess

from .links import validate_file


def git(root: Path, *args) -> bytes:
    result = subprocess.run(['git', '--no-optional-locks', '-C', str(root), *args], capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace').strip())
    return result.stdout


def check_commit(root: Path, paths: list[str]) -> list[str]:
    root = Path(root).resolve(strict=True)
    actual = Path(git(root, 'rev-parse', '--show-toplevel').decode('utf-8').strip()).resolve()
    if actual != root:
        raise ValueError(f'Expected repository root {root}, found {actual}')
    if not paths:
        raise ValueError('An explicit file list is required')
    relative = []
    for name in paths:
        path = (root / name).resolve()
        if not path.is_relative_to(root) or path == root or path.is_dir():
            raise ValueError(f'Not a repository file: {name}')
        relative.append(path.relative_to(root).as_posix())
    if len(relative) != len(set(relative)):
        raise ValueError('Duplicate file paths')
    staged = {x.decode('utf-8') for x in git(root, 'diff', '--cached', '--name-only',
                                          '--no-renames', '-z').split(b'\0') if x}
    if staged != set(relative):
        raise ValueError(f'Staged paths differ from explicit paths: {sorted(staged ^ set(relative))}')
    specs = [f':(literal){p}' for p in relative]
    if git(root, 'diff', '--name-only', '-z', '--', *specs):
        raise ValueError('Selected files have unstaged changes; review and stage the intended version')
    if git(root, 'diff', '--cached', '--name-only', '--diff-filter=U'):
        raise ValueError('Unresolved merge conflicts')
    for name in relative:
        path = root / name
        if path.is_file() and path.suffix.lower() == '.md':
            errors = validate_file(path, readable_links=True)
            if errors:
                raise ValueError('\n'.join(errors))
    git(root, 'diff', '--cached', '--check')
    from .text_workflow import gate_paths
    gate_paths([root / name for name in relative])
    return relative


def commit(root: Path, paths: list[str], message: str, execute=False):
    relative = check_commit(root, paths)
    if not message.strip():
        raise ValueError('Empty commit message')
    if not execute:
        return relative
    # --only excludes concurrently staged unrelated files; recheck selected content.
    check_commit(root, relative)
    git(root, 'commit', '--only', '-m', message, '--', *[f':(literal){p}' for p in relative])
    return relative
