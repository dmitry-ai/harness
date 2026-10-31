# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
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
	r = result.stdout
	return r
def read_git(root: Path, subcommand: str='status', args: tuple[str, ...] | list[str]=()) -> dict:
	if subcommand not in READ_SUBCOMMANDS:
		raise ValueError(f'Unsupported read-only Git subcommand: {subcommand}')
	resolved = Path(root).resolve(strict=True)
	extra = [str(a) for a in args]
	output = git(resolved, subcommand, *extra)
	r = {'valid': True, 'repo': str(resolved), 'subcommand': subcommand, 'args': extra, 'command': ['git', '--no-optional-locks', '-C', str(resolved), subcommand, *extra], 'git_optional_locks': '0', 'stdout': output.decode('utf-8', errors='replace')}
	return r
def classify_git_argv(argv: list[str] | tuple[str, ...]) -> tuple[str | None, bool]:
	has_flag = False
	index = 0
	tokens = list(argv)
	while index < len(tokens):
		token = tokens[index]
		if '--' == token:
			break
		if '--no-optional-locks' == token:
			has_flag = True
			index += 1
		elif token in _VALUE_GLOBAL_OPTS:
			index += 2
		elif token.startswith('-'):
			index += 1
		else:
			return (token, has_flag)
	return (None, has_flag)
def _unquote(token: str) -> str:
	if not (len(token) >= 2 and token[0] == token[-1] and (token[0] in ('"', "'"))):
		r = token
	else:
		inner = token[1:-1]
		r = inner.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
	return r
def _split_shell_segments(cmd: str) -> list[str]:
	segments = []
	curr = []
	for m in re.finditer('("(?:\\\\.|[^"\\\\])*"|\\\'(?:\\\\.|[^\\\'\\\\])*\\\'|&&|\\|\\||[;\\|\\r\\n]|[^"\\\'\\s;\\|\\&]+|\\s+)', cmd):
		tok = m.group(0)
		if tok not in (';', '\r', '\n', '&&', '||', '|'):
			curr.append(tok)
		else:
			seg = ''.join(curr).strip()
			if seg:
				segments.append(seg)
			curr = []
	seg = ''.join(curr).strip()
	if seg:
		segments.append(seg)
	r = segments
	return r
def unflagged_git_read_commands(text: str) -> list[str]:
	if not isinstance(text, str) or 'git' not in text:
		r = []
	elif re.search('[\\\\/]\\.gemini[\\\\/]antigravity[\\\\/]brain[\\\\/][^\\\\/]+[\\\\/]scratch[\\\\/]', text, re.I):
		r = []
	else:
		violations = []
		for match in re.finditer('[\\[\\(]\\s*([\\\'"](?:[^\\\'"]*?[\\\\/])?git(?:\\.exe)?[\\\'"](?:\\s*,\\s*[^\\]\\)]+)+)[\\]\\)]', text):
			raw_items = [part.strip() for part in match.group(1).split(',')]
			parsed = []
			for item in raw_items[1:]:
				lit = re.fullmatch('[\\\'"]([^\\\'"]*)[\\\'"]', item)
				parsed.append(lit.group(1) if lit else '<expr>')
			subcommand, has_flag = classify_git_argv(parsed)
			if subcommand in READ_SUBCOMMANDS and (not has_flag):
				snippet = ' '.join(match.group(0).split())
				if snippet not in violations:
					violations.append(snippet)
		exec_cmds = []
		if 'exec_command' in text:
			for cm in re.finditer('\\bcmd\\s*:\\s*("(?:\\\\.|[^"\\\\])*"|\\\'(?:\\\\.|[^\\\'\\\\])*\\\'|`(?:\\\\.|[^`\\\\])*`)', text):
				raw_lit = cm.group(1)
				if raw_lit.startswith('`'):
					exec_cmds.append(raw_lit[1:-1])
				else:
					exec_cmds.append(_unquote(raw_lit))
		candidates = exec_cmds if exec_cmds else [text]
		for candidate in candidates:
			cleaned = re.sub('@\'[\\s\\S]*?\'@|@\\"[\\s\\S]*?\\"@', '""', candidate)
			cleaned = re.sub('(\\bpython(?:3)?(?:\\.exe)?\\s+(?:-[A-Za-z]+\\s+)*-c\\s+)(?:"(?:\\\\.|[^"\\\\])*"|\\\'(?:\\\'\\\'|[^\\\'])*\\\')', '\\1""', cleaned)
			for segment in _split_shell_segments(cleaned):
				m = re.match('^\\s*(?:&\\s*)?(?:["\\\']?[A-Za-z]:[\\\\/][^"\\\'\\s]*[\\\\/])?git(?:\\.exe)?(?:\\s+|$)(?P<rest>.*)$', segment)
				if not m:
					continue
				raw_tokens = re.findall('"(?:\\\\.|[^"])*"|\\\'(?:\\\\.|[^\\\'])*\\\'|\\S+', m.group('rest'))
				tokens = [_unquote(tok) for tok in raw_tokens]
				subcommand, has_flag = classify_git_argv(tokens)
				if subcommand in READ_SUBCOMMANDS and (not has_flag):
					normalized = ' '.join(segment.strip().split())
					if normalized not in violations:
						violations.append(normalized)
		r = violations
	return r
_EXTERNAL_URL_RE = re.compile('https?://(?!(?:localhost|127\\.0\\.0\\.1|\\[::1\\])\\b)[A-Za-z0-9.-]+', re.I)
_ADHOC_HTTP_CLIENT_RE = re.compile('(?:\\burllib\\.request\\b|\\burlopen\\s*\\(|\\brequests\\.(?:get|post|head|request|Session)\\b|\\bhttpx\\.(?:get|post|Client)\\b|\\bInvoke-(?:WebRequest|RestMethod)\\b|\\b(?:iwr|irm|curl(?:\\.exe)?|wget(?:\\.exe)?)\\s+)', re.I)
_SANCTIONED_HTTP_RUNNER_RE = re.compile('(?:harness\\.py|upwork_project\\.py|validate_links\\.py|df_github_issue\\.py|\\bunittest\\b|\\bpytest\\b)', re.I)
_GITHUB_ISSUE_URL_RE = re.compile('https://github\\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\\d+\\b')
_ISSUE_LINKED_CODE_SUFFIXES = ('.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.cs', '.ps1', '.sh', '.bash', '.cmd', '.bat', '.vbs')
def is_issue_tracked_code_repo(root: Path) -> bool:
	resolved = Path(root).resolve()
	r = 'code' == resolved.name and (resolved.parent / '_').is_dir() and (resolved.parent / '.agents').is_dir()
	return r
def verify_issue_workflow(root: Path, relative: list[str], message: str | None=None) -> None:
	if not is_issue_tracked_code_repo(root):
		return
	for name in relative:
		path = root / name
		if not path.is_file() or path.suffix.lower() not in _ISSUE_LINKED_CODE_SUFFIXES:
			continue
		content = path.read_text(encoding='utf-8', errors='replace')
		if not content.strip():
			continue
		if not _GITHUB_ISSUE_URL_RE.search(content):
			raise ValueError(f'Issue-tracked code file lacks a GitHub Issue URL reference: {name}')
	if None is not message and (not _GITHUB_ISSUE_URL_RE.search(message)):
		raise ValueError('Commit message in an issue-tracked code repository must reference a GitHub Issue URL')
def unpersisted_http_fetch_commands(text: str) -> list[str]:
	if not isinstance(text, str) or not text.strip():
		r = []
	elif _SANCTIONED_HTTP_RUNNER_RE.search(text):
		r = []
	elif not (_EXTERNAL_URL_RE.search(text) and _ADHOC_HTTP_CLIENT_RE.search(text)):
		r = []
	else:
		r = [' '.join(text.strip().split())[:240]]
	return r
# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
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
	staged = {x.decode('utf-8') for x in git(root, 'diff', '--cached', '--name-only', '--no-renames', '-z').split(b'\x00') if x}
	if staged != set(relative):
		raise ValueError(f'Staged paths differ from explicit paths: {sorted(staged ^ set(relative))}')
	specs = [f':(literal){p}' for p in relative]
	if git(root, 'diff', '--name-only', '-z', '--', *specs):
		raise ValueError('Selected files have unstaged changes; review and stage the intended version')
	if git(root, 'diff', '--cached', '--name-only', '--diff-filter=U'):
		raise ValueError('Unresolved merge conflicts')
	for name in relative:
		path = root / name
		if path.is_file() and '.md' == path.suffix.lower():
			errors = validate_file(path, readable_links=True)
			if errors:
				raise ValueError('\n'.join(errors))
	git(root, 'diff', '--cached', '--check')
	from .text_workflow import gate_paths
	gate_paths([root / name for name in relative])
	verify_issue_workflow(root, relative)
	r = relative
	return r
# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
def commit(root: Path, paths: list[str], message: str, execute=False):
	relative = check_commit(root, paths)
	if not message.strip():
		raise ValueError('Empty commit message')
	verify_issue_workflow(root, relative, message=message)
	if not execute:
		r = relative
	else:
		check_commit(root, relative)
		git(root, 'commit', '--only', '-m', message, '--', *[f':(literal){p}' for p in relative])
		r = relative
	return r
