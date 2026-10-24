#!/usr/bin/env python3
"""Priority Git wrapper enforcing EXEC-5 (--no-optional-locks and GIT_OPTIONAL_LOCKS=0) on read commands."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.git_gate import READ_SUBCOMMANDS, classify_git_argv


def resolve_system_git() -> str:
    explicit = os.environ.get('UPWORK_REAL_GIT')
    if explicit and Path(explicit).is_file():
        return str(Path(explicit).resolve())
    shim_dir = (Path(__file__).resolve().parent / 'shim').resolve()
    script_dir = Path(__file__).resolve().parent.resolve()
    filtered_paths = []
    for entry in os.environ.get('PATH', '').split(os.pathsep):
        if not entry.strip():
            continue
        try:
            resolved = Path(entry).resolve()
        except OSError:
            continue
        if resolved in (shim_dir, script_dir):
            continue
        filtered_paths.append(entry)
    found = shutil.which('git', path=os.pathsep.join(filtered_paths))
    if found:
        return found
    for candidate in (Path('C:/tools/git/cmd/git.exe'), Path('C:/Program Files/Git/cmd/git.exe')):
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError('System git executable not found outside .agents shim directory')


def prepare_git_invocation(argv: list[str], *, mode: str | None = None) -> tuple[list[str], dict[str, str]]:
    mode = (mode or os.environ.get('GIT_SHIM_MODE') or os.environ.get('UPWORK_GIT_SHIM_MODE') or 'inject').strip().lower()
    subcommand, has_flag = classify_git_argv(argv)
    effective = list(argv)
    if subcommand in READ_SUBCOMMANDS and not has_flag:
        if mode == 'reject':
            raise ValueError(f'EXEC-5 violation: git {subcommand} requires --no-optional-locks')
        effective = ['--no-optional-locks', *effective]
    env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
    return effective, env


normalize_argv = prepare_git_invocation


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        effective, env = prepare_git_invocation(args)
        binary = resolve_system_git()
    except (ValueError, FileNotFoundError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    completed = subprocess.run([binary, *effective], env=env)
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
