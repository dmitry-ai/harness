"""Commit only an exact staged file set, with explicit repository and paths."""

import os
from pathlib import Path
import re
import subprocess

from .links import validate_file

READ_SUBCOMMANDS = ('status', 'diff', 'log', 'rev-parse', 'show', 'ls-files')
_VALUE_GLOBAL_OPTS = ('-C', '--git-dir', '--work-tree', '-c', '--exec-path', '--namespace', '--super-prefix', '--config-env')


def git(root: Path, *args) -> bytes:
    env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
    result = subprocess.run(['git', '--no-optional-locks', '-C', str(root), *args], capture_output=True, env=env)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace').strip())
    return result.stdout


def read_git(root: Path, subcommand: str = 'status', args: tuple[str, ...] | list[str] = ()) -> dict:
    if subcommand not in READ_SUBCOMMANDS:
        raise ValueError(f'Unsupported read-only Git subcommand: {subcommand}')
    resolved = Path(root).resolve(strict=True)
    extra = [str(a) for a in args]
    output = git(resolved, subcommand, *extra)
    return {'valid': True, 'repo': str(resolved), 'subcommand': subcommand, 'args': extra,
            'command': ['git', '--no-optional-locks', '-C', str(resolved), subcommand, *extra],
            'git_optional_locks': '0', 'stdout': output.decode('utf-8', errors='replace')}


def classify_git_argv(argv: list[str] | tuple[str, ...]) -> tuple[str | None, bool]:
    """Return (subcommand, has_no_optional_locks) for a tokenized git argument list."""
    has_flag = False
    index = 0
    tokens = list(argv)
    while index < len(tokens):
        token = tokens[index]
        if token == '--':
            break
        if token == '--no-optional-locks':
            has_flag = True
            index += 1
        elif token in _VALUE_GLOBAL_OPTS:
            index += 2
        elif token.startswith('-'):
            index += 1
        else:
            return token, has_flag
    return None, has_flag


def _unquote(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
        inner = token[1:-1]
        return inner.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
    return token


def _split_shell_segments(cmd: str) -> list[str]:
    segments = []
    curr = []
    for m in re.finditer(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|&&|\|\||[;\|\r\n]|[^"\'\s;\|\&]+|\s+)', cmd):
        tok = m.group(0)
        if tok in (';', '\r', '\n', '&&', '||', '|'):
            seg = ''.join(curr).strip()
            if seg:
                segments.append(seg)
            curr = []
        else:
            curr.append(tok)
    seg = ''.join(curr).strip()
    if seg:
        segments.append(seg)
    return segments


def unflagged_git_read_commands(text: str) -> list[str]:
    """Detect shell or Python subprocess git read commands missing --no-optional-locks."""
    if not isinstance(text, str) or 'git' not in text:
        return []
    violations = []
    # 1. Check Python subprocess list/tuple invocations: ['git', ...] or ('git', ...)
    for match in re.finditer(r'[\[\(]\s*([\'"](?:[^\'"]*?[\\/])?git(?:\.exe)?[\'"](?:\s*,\s*[^\]\)]+)+)[\]\)]', text):
        raw_items = [part.strip() for part in match.group(1).split(',')]
        parsed = []
        for item in raw_items[1:]:
            lit = re.fullmatch(r'[\'"]([^\'"]*)[\'"]', item)
            parsed.append(lit.group(1) if lit else '<expr>')
        subcommand, has_flag = classify_git_argv(parsed)
        if subcommand in READ_SUBCOMMANDS and not has_flag:
            snippet = ' '.join( match.group(0).split() )
            if snippet not in violations:
                violations.append(snippet)
    # 2. If text is a Codex JS REPL script with exec_command({ cmd: ... }), extract each cmd string
    exec_cmds = []
    if 'exec_command' in text:
        for cm in re.finditer(r'\bcmd\s*:\s*("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`)', text):
            raw_lit = cm.group(1)
            if raw_lit.startswith('`'):
                exec_cmds.append(raw_lit[1:-1])
            else:
                exec_cmds.append(_unquote(raw_lit))
    candidates = exec_cmds if exec_cmds else [text]
    for candidate in candidates:
        # Strip PowerShell here-strings and inline python -c "..." / '...' code payloads
        cleaned = re.sub(r"@'[\s\S]*?'@|@\"[\s\S]*?\"@", '""', candidate)
        cleaned = re.sub(r'(\bpython(?:3)?(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*-c\s+)(?:"(?:\\.|[^"\\])*"|\'(?:\'\'|[^\'])*\')', r'\1""', cleaned)
        for segment in _split_shell_segments(cleaned):
            m = re.match(r'^\s*(?:&\s*)?(?:["\']?[A-Za-z]:[\\/][^"\'\s]*[\\/])?git(?:\.exe)?(?:\s+|$)(?P<rest>.*)$', segment)
            if not m:
                continue
            raw_tokens = re.findall(r'"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\'|\S+', m.group('rest'))
            tokens = [_unquote(tok) for tok in raw_tokens]
            subcommand, has_flag = classify_git_argv(tokens)
            if subcommand in READ_SUBCOMMANDS and not has_flag:
                normalized = ' '.join(segment.strip().split())
                if normalized not in violations:
                    violations.append(normalized)
    return violations


_EXTERNAL_URL_RE = re.compile(
    r'https?://(?!(?:localhost|127\.0\.0\.1|\[::1\])\b)[A-Za-z0-9.-]+',
    re.I,
)
_ADHOC_HTTP_CLIENT_RE = re.compile(
    r'(?:\burllib\.request\b|\burlopen\s*\(|\brequests\.(?:get|post|head|request|Session)\b'
    r'|\bhttpx\.(?:get|post|Client)\b|\bInvoke-(?:WebRequest|RestMethod)\b'
    r'|\b(?:iwr|irm|curl(?:\.exe)?|wget(?:\.exe)?)\s+)',
    re.I,
)
_SANCTIONED_HTTP_RUNNER_RE = re.compile(
    r'(?:upwork_project\.py|validate_links\.py|df_github_issue\.py|\bunittest\b|\bpytest\b)',
    re.I,
)


def unpersisted_http_fetch_commands(text: str) -> list[str]:
    """Detect ad-hoc external HTTP(S) fetches in shell/Python one-liners that bypass Evidence storage."""
    if not isinstance(text, str) or not text.strip():
        return []
    if _SANCTIONED_HTTP_RUNNER_RE.search(text):
        return []
    if _EXTERNAL_URL_RE.search(text) and _ADHOC_HTTP_CLIENT_RE.search(text):
        return [' '.join(text.strip().split())[:240]]
    return []



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
