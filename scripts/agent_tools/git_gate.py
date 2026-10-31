# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent rogue ꘖ directory outside harness meta repo, remove mirror logic, and recognize GIT_OPTIONAL_LOCKS in git gate":
# https://github.com/dmitry-ai/harness/issues/28
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from .links import validate_file
READ_SUBCOMMANDS = ('status', 'diff', 'log', 'rev-parse', 'show', 'ls-files')
_VALUE_GLOBAL_OPTS = ('-C', '--git-dir', '--work-tree', '-c', '--exec-path', '--namespace', '--super-prefix', '--config-env')
HOOKS_DIR = Path(__file__).resolve().parents[1] / 'git_hooks'
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
			if re.search('(?:\\$env:)?GIT_OPTIONAL_LOCKS\\s*=\\s*["\']?0["\']?', candidate):
				continue
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
_COMMIT_MESSAGE_ISSUE_URL_RE = re.compile('^https://github\\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\\d+$')
_ISSUE_LINKED_CODE_SUFFIXES = ('.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.cs', '.ps1', '.sh', '.bash', '.cmd', '.bat', '.vbs')
def extract_issue_urls(text: str) -> list[str]:
	return list(dict.fromkeys(_GITHUB_ISSUE_URL_RE.findall(text or '')))
def is_code_file(rel_path: str | Path) -> bool:
	return Path(rel_path).suffix.lower() in _ISSUE_LINKED_CODE_SUFFIXES
def run_git_read(root: Path, args: list[str] | tuple[str, ...], *, check: bool=True):
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
	return subprocess.run(['git', '--no-optional-locks', '-C', str(root), *args], capture_output=True, env=env, check=check)
def _main_repo_for_worktree(root: Path) -> Path:
	resolved = Path(root).resolve()
	dot_git = resolved / '.git'
	if dot_git.is_file():
		try:
			txt = dot_git.read_text(encoding='utf-8', errors='replace').strip()
			if txt.lower().startswith('gitdir:'):
				gitdir = Path(txt.split(':', 1)[1].strip())
				if not gitdir.is_absolute():
					gitdir = (resolved / gitdir).resolve()
				if 'worktrees' == gitdir.parent.name and '.git' == gitdir.parent.parent.name:
					return gitdir.parent.parent.parent.resolve()
		except OSError:
			pass
	return resolved
def is_issue_tracked_code_repo(root: Path) -> bool:
	resolved = _main_repo_for_worktree(Path(root).resolve())
	r = 'code' == resolved.name and (resolved / '.git').exists() and ((resolved.parent / '_').is_dir() or (resolved.parent / '.agents').is_dir())
	return r
def ensure_repo_hooks(root: Path) -> Path | None:
	resolved = Path(root).resolve()
	if not is_issue_tracked_code_repo(resolved) or not (resolved / '.git').exists() or (not HOOKS_DIR.is_dir()):
		return None
	main_repo = _main_repo_for_worktree(resolved)
	try:
		for hname in ('pre-commit', 'commit-msg'):
			hp = HOOKS_DIR / hname
			if hp.is_file():
				hp.chmod(hp.stat().st_mode | 0o755)
		proc = subprocess.run(['git', '--no-optional-locks', '-C', str(main_repo), 'config', '--local', '--get', 'core.hooksPath'], capture_output=True, text=True, check=False)
		current = (proc.stdout or '').strip()
		if Path(current).resolve() != HOOKS_DIR.resolve() if current else True:
			subprocess.run(['git', '-C', str(main_repo), 'config', '--local', 'core.hooksPath', str(HOOKS_DIR)], capture_output=True, check=False)
	except OSError:
		return None
	return HOOKS_DIR
def _extract_added_diff_urls(root: Path, rel_name: str) -> tuple[set[str], set[str]]:
	added_urls: set[str] = set()
	head_urls: set[str] = set()
	if not (Path(root) / '.git').exists():
		return (added_urls, head_urls)
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
	diff_proc = subprocess.run(['git', '--no-optional-locks', '-C', str(root), 'diff', '--cached', '-U0', '--', f':(literal){rel_name}'], capture_output=True, env=env, check=False)
	if 0 == diff_proc.returncode and diff_proc.stdout:
		diff_text = diff_proc.stdout.decode('utf-8', errors='replace')
		for line in diff_text.splitlines():
			if line.startswith('+') and (not line.startswith('+++')):
				body = line[1:]
				if re.match('^\\s*(?:#|//|REM\\b|/\\*|\\*)', body, re.I):
					added_urls.update(_GITHUB_ISSUE_URL_RE.findall(body))
	if added_urls:
		show_proc = subprocess.run(['git', '--no-optional-locks', '-C', str(root), 'show', f'HEAD:{rel_name}'], capture_output=True, env=env, check=False)
		if 0 == show_proc.returncode and show_proc.stdout:
			head_text = show_proc.stdout.decode('utf-8', errors='replace')
			for hline in head_text.splitlines():
				if re.match('^\\s*(?:#|//|REM\\b|/\\*|\\*)', hline, re.I):
					head_urls.update(_GITHUB_ISSUE_URL_RE.findall(hline))
	return (added_urls, head_urls)
def verify_issue_workflow(root: Path, relative: list[str], message: str | None=None) -> None:
	if not is_issue_tracked_code_repo(root):
		return
	stripped_msg = None
	if None is not message:
		stripped_msg = message.strip()
		if not _COMMIT_MESSAGE_ISSUE_URL_RE.fullmatch(stripped_msg):
			raise ValueError('Commit message in an issue-tracked code repository must contain only the GitHub Issue URL (https://github.com/<owner>/<repo>/issues/<N>)')
	all_new_diff_urls: set[str] = set()
	for name in relative:
		path = root / name
		if not path.is_file() or path.suffix.lower() not in _ISSUE_LINKED_CODE_SUFFIXES:
			continue
		content = path.read_text(encoding='utf-8', errors='replace')
		if not content.strip():
			continue
		file_urls = set(_GITHUB_ISSUE_URL_RE.findall(content))
		if not file_urls:
			raise ValueError(f'Issue-tracked code file lacks a GitHub Issue URL reference: {name}')
		if None is not stripped_msg and stripped_msg not in file_urls:
			raise ValueError(f'Issue-tracked code file {name} does not reference the commit GitHub Issue URL {stripped_msg}')
		added_urls, head_urls = _extract_added_diff_urls(root, name)
		new_diff_urls = added_urls - head_urls
		if len(new_diff_urls) > 1:
			raise ValueError(f'Staged diff in {name} introduces multiple distinct GitHub Issue URLs: {sorted(new_diff_urls)}')
		if None is not stripped_msg and new_diff_urls and (new_diff_urls != {stripped_msg}):
			raise ValueError(f'Staged diff in {name} introduces GitHub Issue URL(s) {sorted(new_diff_urls)} not matching commit message {stripped_msg}')
		all_new_diff_urls.update(new_diff_urls)
	if len(all_new_diff_urls) > 1:
		raise ValueError(f'Staged files mix changes from multiple GitHub Issues: {sorted(all_new_diff_urls)}')
def resolve_git_repo_from_argv(argv: list[str] | tuple[str, ...], cwd: Path | None=None) -> Path | None:
	target_dir = Path(cwd).resolve() if None is not cwd else Path.cwd().resolve()
	tokens = list(argv)
	idx = 0
	while idx < len(tokens):
		tok = tokens[idx]
		if '--' == tok:
			break
		if tok in ('-C', '--work-tree') and idx + 1 < len(tokens):
			cand = Path(tokens[idx + 1])
			target_dir = cand.resolve() if cand.is_absolute() else (target_dir / cand).resolve()
			idx += 2
		elif tok in _VALUE_GLOBAL_OPTS:
			idx += 2
		elif tok.startswith('-'):
			idx += 1
		else:
			break
	for anc in (target_dir, *target_dir.parents):
		if (anc / '.git').exists():
			return anc
	return None
def _parse_commit_subcommand_args(argv: list[str] | tuple[str, ...]) -> tuple[list[str], str | None, str | None, bool, bool, list[str]]:
	tokens = list(argv)
	idx = 0
	sub_idx = None
	while idx < len(tokens):
		tok = tokens[idx]
		if '--' == tok:
			break
		if tok in _VALUE_GLOBAL_OPTS:
			idx += 2
		elif tok.startswith('-'):
			idx += 1
		else:
			sub_idx = idx
			break
	if None is sub_idx or 'commit' != tokens[sub_idx]:
		return ([], None, None, False, False, [])
	rest = tokens[sub_idx + 1:]
	msg_parts: list[str] = []
	msg_file: str | None = None
	no_verify = False
	all_flag = False
	pathspecs: list[str] = []
	i = 0
	after_dd = False
	while i < len(rest):
		t = rest[i]
		if after_dd:
			pathspecs.append(t)
			i += 1
			continue
		if '--' == t:
			after_dd = True
			i += 1
			continue
		if '--no-verify' == t:
			no_verify = True
			i += 1
		elif '--all' == t:
			all_flag = True
			i += 1
		elif t in ('-m', '--message') and i + 1 < len(rest):
			msg_parts.append(rest[i + 1])
			i += 2
		elif t.startswith('--message='):
			msg_parts.append(t.split('=', 1)[1])
			i += 1
		elif t.startswith('-m') and len(t) > 2:
			msg_parts.append(t[2:])
			i += 1
		elif t in ('-F', '--file') and i + 1 < len(rest):
			msg_file = rest[i + 1]
			i += 2
		elif t.startswith('--file='):
			msg_file = t.split('=', 1)[1]
			i += 1
		elif t in ('-c', '-C', '--reuse-message', '--reedit-message', '--fixup', '--squash', '--author', '--date', '--cleanup', '-u', '--untracked-files', '-S', '--gpg-sign'):
			i += 2
		elif t.startswith('-') and (not t.startswith('--')):
			flags = t[1:]
			if 'n' in flags:
				no_verify = True
			if 'a' in flags:
				all_flag = True
			if 'm' in flags:
				m_pos = flags.index('m')
				rem = flags[m_pos + 1:]
				if rem:
					msg_parts.append(rem)
					i += 1
				elif i + 1 < len(rest):
					msg_parts.append(rest[i + 1])
					i += 2
				else:
					i += 1
			else:
				i += 1
		elif t.startswith('--'):
			i += 1
		else:
			pathspecs.append(t)
			i += 1
	msg = '\n\n'.join(msg_parts) if msg_parts else None
	return (rest, msg, msg_file, no_verify, all_flag, pathspecs)
def verify_git_write_invocation(argv: list[str] | tuple[str, ...], cwd: Path | None=None) -> None:
	subcommand, _ = classify_git_argv(argv)
	if subcommand not in ('commit', 'filter-branch', 'merge', 'rebase', 'cherry-pick'):
		return
	repo_root = resolve_git_repo_from_argv(argv, cwd=cwd)
	if None is repo_root or not is_issue_tracked_code_repo(repo_root):
		return
	ensure_repo_hooks(repo_root)
	if 'filter-branch' == subcommand:
		raise ValueError('EXEC-5 violation: git filter-branch is prohibited in issue-tracked code repositories')
	if 'commit' == subcommand:
		_, msg, msg_file, no_verify, all_flag, pathspecs = _parse_commit_subcommand_args(argv)
		if no_verify:
			raise ValueError('EXEC-5 violation: git commit --no-verify/-n is prohibited in issue-tracked code repositories')
		if all_flag:
			raise ValueError('EXEC-5 violation: git commit -a/--all is prohibited in issue-tracked code repositories; stage and commit only an explicit file list')
		if None is msg and msg_file and ('-' != msg_file):
			mf = Path(msg_file)
			if not mf.is_absolute():
				mf = (Path(cwd or Path.cwd()) / mf).resolve()
			if mf.is_file():
				msg = mf.read_text(encoding='utf-8', errors='replace')
		if None is not msg:
			stripped = '\n'.join((line for line in msg.splitlines() if not line.startswith('#'))).strip()
			if not _COMMIT_MESSAGE_ISSUE_URL_RE.fullmatch(stripped):
				raise ValueError('EXEC-5 violation: commit message in an issue-tracked code repository must contain only the GitHub Issue URL (https://github.com/<owner>/<repo>/issues/<N>)')
		if (repo_root / '.git').exists():
			clean_specs = []
			for sp in pathspecs:
				s = sp[len(':(literal)'):] if sp.startswith(':(literal)') else sp
				p = (repo_root / s).resolve()
				if p.is_relative_to(repo_root):
					clean_specs.append(p.relative_to(repo_root).as_posix())
			if not clean_specs:
				try:
					clean_specs = [x.decode('utf-8') for x in git(repo_root, 'diff', '--cached', '--name-only', '--no-renames', '-z').split(b'\x00') if x]
				except RuntimeError:
					clean_specs = []
			if clean_specs:
				verify_issue_workflow(repo_root, clean_specs, message=msg)
def prohibited_git_write_commands(text: str) -> list[str]:
	if not isinstance(text, str) or 'git' not in text:
		return []
	violations: list[str] = []
	cleaned = re.sub('@\'[\\s\\S]*?\'@|@\\"[\\s\\S]*?\\"@', '""', text)
	cleaned = re.sub('(\\bpython(?:3)?(?:\\.exe)?\\s+(?:-[A-Za-z]+\\s+)*-c\\s+)(?:"(?:\\\\.|[^"\\\\])*"|\\\'(?:\\\'\\\'|[^\\\'])*\\\')', '\\1""', cleaned)
	for segment in _split_shell_segments(cleaned):
		m = re.match('^\\s*(?:&\\s*)?(?:["\\\']?[A-Za-z]:[\\\\/][^"\\\'\\s]*[\\\\/])?git(?:\\.exe)?(?:\\s+|$)(?P<rest>.*)$', segment)
		if not m:
			continue
		raw_tokens = re.findall('"(?:\\\\.|[^"])*"|\\\'(?:\\\\.|[^\\\'])*\\\'|\\S+', m.group('rest'))
		tokens = [_unquote(tok) for tok in raw_tokens]
		subcommand, _ = classify_git_argv(tokens)
		if 'filter-branch' == subcommand:
			violations.append(f'git filter-branch is prohibited ({segment.strip()})')
		elif 'commit' == subcommand:
			_, msg, _, no_verify, all_flag, _ = _parse_commit_subcommand_args(tokens)
			if no_verify:
				violations.append(f'git commit --no-verify/-n is prohibited ({segment.strip()})')
			if all_flag:
				violations.append(f'git commit -a/--all is prohibited ({segment.strip()})')
			if None is not msg and (not _COMMIT_MESSAGE_ISSUE_URL_RE.fullmatch(msg.strip())) and ('$' not in msg):
				repo_root = resolve_git_repo_from_argv(tokens)
				if None is repo_root or is_issue_tracked_code_repo(repo_root):
					violations.append(f'git commit message must contain only the GitHub Issue URL ({segment.strip()})')
	return violations
def run_git_hook(hook_name: str, argv: list[str] | tuple[str, ...]=(), cwd: Path | None=None) -> int:
	repo_root = resolve_git_repo_from_argv((), cwd=cwd)
	if None is repo_root or not is_issue_tracked_code_repo(repo_root):
		return 0
	try:
		staged = [x.decode('utf-8') for x in git(repo_root, 'diff', '--cached', '--name-only', '--no-renames', '-z').split(b'\x00') if x]
		if 'pre-commit' == hook_name:
			if staged:
				verify_issue_workflow(repo_root, staged)
		elif 'commit-msg' == hook_name:
			if not argv:
				raise ValueError('commit-msg hook requires message file path argument')
			msg_path = Path(argv[0])
			if not msg_path.is_absolute():
				msg_path = (repo_root / msg_path).resolve()
			raw_msg = msg_path.read_text(encoding='utf-8', errors='replace')
			cleaned_msg = '\n'.join((line for line in raw_msg.splitlines() if not line.startswith('#'))).strip()
			verify_issue_workflow(repo_root, staged, message=cleaned_msg)
	except (OSError, ValueError, RuntimeError) as exc:
		print(f'ERROR (Git hook {hook_name}): {exc}', file=sys.stderr)
		return 2
	return 0
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
def extract_issue_actions_from_outputs(outputs: list[str] | tuple[str, ...]) -> list[dict]:
	import json as _json
	actions: list[dict] = []
	decoder = _json.JSONDecoder()
	for text in outputs or []:
		if not isinstance(text, str) or '"action"' not in text or '"repo"' not in text:
			continue
		pos = 0
		while (pos := text.find('{', pos)) >= 0:
			try:
				obj, size = decoder.raw_decode(text[pos:])
			except ValueError:
				pos += 1
				continue
			pos += size
			if not isinstance(obj, dict):
				continue
			act = obj.get('action')
			repo = obj.get('repo')
			if act not in ('create', 'edit', 'comment', 'close') or not isinstance(repo, str) or '/' not in repo:
				continue
			num = obj.get('number')
			if None is num:
				m = re.search('/issues/(\\d+)\\b', str(obj.get('html_url') or ''))
				if m:
					num = int(m.group(1))
			if isinstance(num, int):
				actions.append({'action': act, 'repo': repo, 'number': num, 'url': f'https://github.com/{repo}/issues/{num}', 'ok': bool(obj.get('ok')), 'state': obj.get('state')})
	return actions
def _normalize_repo_paths(root: Path, paths: list[str]) -> list[str]:
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
	return relative
# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
def check_commit(root: Path, paths: list[str]) -> list[str]:
	root = Path(root).resolve(strict=True)
	actual = Path(git(root, 'rev-parse', '--show-toplevel').decode('utf-8').strip()).resolve()
	if actual != root:
		raise ValueError(f'Expected repository root {root}, found {actual}')
	ensure_repo_hooks(root)
	relative = _normalize_repo_paths(root, paths)
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
def create_isolated_worktree(root: Path, label: str='isolated') -> Path:
	root = Path(root).resolve(strict=True)
	base = (root.parent / '_/ꘖ/data/worktrees') if (root.parent / '_').is_dir() else (root.parent / 'ꘖ/data/worktrees')
	base.mkdir(parents=True, exist_ok=True)
	wt_dir = base / f'{label}-{uuid.uuid4().hex[:10]}'
	git(root, 'worktree', 'add', '--detach', str(wt_dir), 'HEAD')
	return wt_dir
def remove_isolated_worktree(root: Path, wt_dir: Path) -> None:
	root = Path(root).resolve(strict=True)
	wt_dir = Path(wt_dir).resolve()
	try:
		git(root, 'worktree', 'remove', '--force', str(wt_dir))
	finally:
		if wt_dir.exists():
			shutil.rmtree(wt_dir, ignore_errors=True)
		subprocess.run(['git', '-C', str(root), 'worktree', 'prune'], capture_output=True, check=False)
def commit_in_worktree(root: Path, paths: list[str], message: str) -> list[str]:
	root = Path(root).resolve(strict=True)
	actual = Path(git(root, 'rev-parse', '--show-toplevel').decode('utf-8').strip()).resolve()
	if actual != root:
		raise ValueError(f'Expected repository root {root}, found {actual}')
	if not message.strip():
		raise ValueError('Empty commit message')
	ensure_repo_hooks(root)
	relative = _normalize_repo_paths(root, paths)
	has_head = 0 == run_git_read(root, ['rev-parse', '--verify', 'HEAD'], check=False).returncode
	wt_dir = create_isolated_worktree(root, label='commit')
	try:
		for rel in relative:
			src = root / rel
			dst = wt_dir / rel
			if src.exists():
				dst.parent.mkdir(parents=True, exist_ok=True)
				shutil.copy2(src, dst)
			elif dst.exists():
				dst.unlink()
		specs = [f':(literal){p}' for p in relative]
		git(wt_dir, 'add', '-A', '--', *specs)
		check_commit(wt_dir, relative)
		verify_issue_workflow(wt_dir, relative, message=message)
		old_head = git(root, 'rev-parse', 'HEAD').decode('utf-8').strip() if has_head else None
		git(wt_dir, 'commit', '--only', '-m', message, '--', *specs)
		new_head = git(wt_dir, 'rev-parse', 'HEAD').decode('utf-8').strip()
		if old_head:
			git(root, 'update-ref', '-m', f'commit (worktree): {message.strip()}', 'HEAD', new_head, old_head)
		else:
			git(root, 'update-ref', '-m', f'commit (worktree): {message.strip()}', 'HEAD', new_head)
		git(root, 'reset', '-q', 'HEAD', '--', *specs)
	finally:
		remove_isolated_worktree(root, wt_dir)
	return relative
# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
def commit(root: Path, paths: list[str], message: str, execute=False, *, worktree: bool=False):
	if worktree and execute:
		return commit_in_worktree(root, paths, message)
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
def verify_repo_issue_ready_for_close(code_repo: Path, repo: str, number: int) -> dict:
	code_repo = Path(code_repo).resolve(strict=True)
	issue_url = f'https://github.com/{repo}/issues/{number}'
	status_out = git(code_repo, 'status', '--porcelain', '-z').decode('utf-8', errors='replace')
	dirty_referencing = []
	entries = [e for e in status_out.split('\x00') if e]
	idx = 0
	while idx < len(entries):
		entry = entries[idx]
		status_code = entry[:2]
		rel_path = entry[3:]
		if status_code.startswith(('R', 'C')) and idx + 1 < len(entries):
			idx += 1
		fpath = code_repo / rel_path
		if fpath.is_file() and fpath.suffix.lower() in _ISSUE_LINKED_CODE_SUFFIXES:
			try:
				if issue_url in fpath.read_text(encoding='utf-8', errors='replace'):
					dirty_referencing.append(rel_path)
			except OSError:
				pass
		idx += 1
	if dirty_referencing:
		raise ValueError(f'EXEC-5 violation: uncommitted file(s) in {code_repo} still reference {issue_url}: {", ".join(dirty_referencing)}; commit and push before closing the issue')
	commit_sha = git(code_repo, 'log', f'--grep={issue_url}', '--fixed-strings', '-n', '1', '--format=%H').decode('utf-8', errors='replace').strip()
	if not commit_sha:
		raise ValueError(f'EXEC-5 violation: no commit in {code_repo} references {issue_url}; commit and push changes before closing the issue as completed')
	env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
	up_proc = subprocess.run(['git', '--no-optional-locks', '-C', str(code_repo), 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'], capture_output=True, env=env, check=False)
	pushed = True
	if 0 == up_proc.returncode:
		anc_proc = subprocess.run(['git', '--no-optional-locks', '-C', str(code_repo), 'merge-base', '--is-ancestor', commit_sha, '@{u}'], capture_output=True, env=env, check=False)
		unpushed_str = git(code_repo, 'rev-list', '--count', '@{u}..HEAD').decode('utf-8', errors='replace').strip()
		unpushed = int(unpushed_str) if unpushed_str.isdigit() else 0
		if 0 != anc_proc.returncode or unpushed > 0:
			pushed = False
			raise ValueError(f'EXEC-5 violation: commit {commit_sha[:12]} referencing {issue_url} in {code_repo} has not been pushed to upstream (run git push before df_github_issue.py close)')
	return {'verified': True, 'repo': str(code_repo), 'issue_url': issue_url, 'commit_sha': commit_sha, 'pushed': pushed}
