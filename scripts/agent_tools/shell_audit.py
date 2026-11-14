# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose git_gate.py into shell_audit.py, GitRepoGate, and single-pass pre-commit validation":
# https://github.com/dmitry-ai/harness/issues/67
from pathlib import Path
import re
from .storage import iter_embedded_json_objects
READ_SUBCOMMANDS = ('status', 'diff', 'log', 'rev-parse', 'show', 'ls-files')
_ADHOC_HTTP_CLIENT_RE = re.compile('(?:\\burllib\\.request\\b|\\burlopen\\s*\\(|\\brequests\\.(?:get|post|head|request|Session)\\b|\\bhttpx\\.(?:get|post|Client)\\b|\\bInvoke-(?:WebRequest|RestMethod)\\b|\\b(?:iwr|irm|curl(?:\\.exe)?|wget(?:\\.exe)?)\\s+)', re.I)
_COMMIT_MESSAGE_ISSUE_URL_RE = re.compile('^https://github\\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\\d+)$')
_CYGDRIVE_RE = re.compile('^/(?:cygdrive|mnt)/([a-zA-Z])(?:/(.*))?$')
_EXTERNAL_URL_RE = re.compile('https?://(?!(?:localhost|127\\.0\\.0\\.1|\\[::1\\])\\b)[A-Za-z0-9.-]+', re.I)
_GITHUB_ISSUE_URL_RE = re.compile('https://github\\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\\d+\\b')
_ISSUE_LINKED_CODE_SUFFIXES = ('.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.cs', '.ps1', '.sh', '.bash', '.cmd', '.bat', '.vbs')
_SANCTIONED_HTTP_RUNNER_RE = re.compile('(?:harness\\.py|upwork_project\\.py|validate_links\\.py|df_github_issue\\.py|\\bunittest\\b|\\bpytest\\b)', re.I)
_VALUE_GLOBAL_OPTS = ('-C', '--git-dir', '--work-tree', '-c', '--exec-path', '--namespace', '--super-prefix', '--config-env')
class ShellCommandInspector:
	def _iter_git_segments(self, candidate: str) -> list[tuple[str, list[str]]]:
		cleaned = re.sub('@\'[\\s\\S]*?\'@|@"[\\s\\S]*?"@', '""', candidate)
		cleaned = re.sub('(\\bpython(?:3)?(?:\\.exe)?\\s+(?:-[A-Za-z]+\\s+)*-c\\s+)(?:"(?:\\\\.|[^"\\\\])*"|\'(?:\'\'|[^\'])*\')', '\\1""', cleaned)
		r: list[tuple[str, list[str]]] = []
		for segment in self._split_segments(cleaned):
			m = re.match('^\\s*(?:&\\s*)?(?:["\']?[A-Za-z]:[\\\\/][^"\'\\s]*[\\\\/])?git(?:\\.exe)?(?:\\s+|$)(?P<rest>.*)$', segment)
			if m:
				raw_tokens = re.findall('"(?:\\\\.|[^"])*"|\'(?:\\\\.|[^\'])*\'|\\S+', m.group('rest'))
				r.append((segment, [self._unquote(tok) for tok in raw_tokens]))
		return r
	def _parse_commit_flag_bundle(self, flags: str, rest: list[str], idx: int, msg_parts: list[str]) -> tuple[int, bool, bool]:
		no_verify = 'n' in flags
		all_flag = 'a' in flags
		if 'm' not in flags:
			next_idx = idx + 1
		else:
			rem = flags[flags.index('m') + 1:]
			if not rem and idx + 1 >= len(rest):
				next_idx = idx + 1
			elif rem:
				msg_parts.append(rem)
				next_idx = idx + 1
			else:
				msg_parts.append(rest[idx + 1])
				next_idx = idx + 2
		return (next_idx, no_verify, all_flag)
	def _split_segments(self, cmd: str) -> list[str]:
		r: list[str] = []
		curr: list[str] = []
		for m in re.finditer('("(?:\\\\.|[^"\\\\])*"|\'(?:\\\\.|[^\'\\\\])*\'|&&|\\|\\||[;\\|\\r\\n]|[^"\'\\s;\\|\\&]+|\\s+)', cmd):
			tok = m.group(0)
			if tok not in (';', '\r', '\n', '&&', '||', '|'):
				curr.append(tok)
			else:
				seg = ''.join(curr).strip()
				if seg:
					r.append(seg)
				curr = []
		seg = ''.join(curr).strip()
		if seg:
			r.append(seg)
		return r
	def _unquote(self, token: str) -> str:
		if not (2 <= len(token) and token[0] == token[-1] and (token[0] in ('"', "'"))):
			r = token
		else:
			inner = token[1:-1]
			r = inner.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
		return r
	def classify_git_argv(self, argv: list[str] | tuple[str, ...]) -> tuple[str | None, bool]:
		tokens = list(argv)
		sub_idx, has_flag, _ = self.scan_git_global_opts(tokens)
		return (tokens[sub_idx] if None is not sub_idx else None, has_flag)
	def extract_issue_actions(self, outputs: list[str] | tuple[str, ...]) -> list[dict]:
		r: list[dict] = []
		for text in outputs or ():
			if isinstance(text, str) and '"action"' in text and ('"repo"' in text) and (not re.search('(?m)^Ran \\d+ tests? in \\d', text)) and (not re.search('(?i)"consumed_files"\\s*:\\s*\\[\\s*"[^"]*(?:[/\\\\\\\\]temp[/\\\\\\\\]|[/\\\\\\\\]tmp[/\\\\\\\\])', text)):
				for obj in iter_embedded_json_objects(text, parse_root=False, recursive=False):
					consumed = obj.get('consumed_files') if isinstance(obj, dict) else None
					act = obj.get('action') if isinstance(obj, dict) else None
					repo = obj.get('repo') if isinstance(obj, dict) else None
					if isinstance(obj, dict) and obj.get('ok', True) and (not (isinstance(consumed, list) and any((re.search('(?i)(?:[/\\\\]temp[/\\\\]|[/\\\\]tmp[/\\\\])', str(cf)) for cf in consumed)))) and (act in ('create', 'edit', 'comment', 'close')) and isinstance(repo, str) and ('/' in repo):
						num = obj.get('number')
						if None is num:
							m = re.search('/issues/(\\d+)\\b', str(obj.get('html_url') or ''))
							if m:
								num = int(m.group(1))
						if isinstance(num, int):
							r.append({'action': act, 'repo': repo, 'number': num, 'url': f'https://github.com/{repo}/issues/{num}', 'ok': bool(obj.get('ok', True)), 'state': obj.get('state')})
		return r
	def parse_commit_subcommand_args(self, argv: list[str] | tuple[str, ...]) -> tuple[list[str], str | None, str | None, bool, bool, list[str]]:
		tokens = list(argv)
		sub_idx, _, _ = self.scan_git_global_opts(tokens)
		if None is sub_idx or 'commit' != tokens[sub_idx]:
			r = ([], None, None, False, False, [])
		else:
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
				elif '--' == t:
					after_dd = True
					i += 1
				elif '--no-verify' == t:
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
				elif t.startswith('-m') and 2 < len(t):
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
				elif t.startswith('--'):
					i += 1
				elif not t.startswith('-'):
					pathspecs.append(t)
					i += 1
				else:
					i, bundle_nv, bundle_all = self._parse_commit_flag_bundle(t[1:], rest, i, msg_parts)
					no_verify = no_verify or bundle_nv
					all_flag = all_flag or bundle_all
			r = (rest, '\n\n'.join(msg_parts) if msg_parts else None, msg_file, no_verify, all_flag, pathspecs)
		return r
	def prohibited_git_write_commands(self, text: str) -> list[str]:
		if not isinstance(text, str) or 'git' not in text:
			r = []
		else:
			r = []
			for segment, tokens in self._iter_git_segments(text):
				subcommand, _ = self.classify_git_argv(tokens)
				if 'filter-branch' == subcommand:
					r.append(f'git filter-branch is prohibited ({segment.strip()})')
				elif 'commit' == subcommand:
					_, msg, _, no_verify, all_flag, _ = self.parse_commit_subcommand_args(tokens)
					if no_verify:
						r.append(f'git commit --no-verify/-n is prohibited ({segment.strip()})')
					if all_flag:
						r.append(f'git commit -a/--all is prohibited ({segment.strip()})')
					if None is not msg and None is parse_issue_url(normalize_commit_message(msg)) and ('$' not in msg):
						r.append(f'git commit message must contain only the GitHub Issue URL ({segment.strip()})')
		return r
	def scan_git_global_opts(self, argv: list[str] | tuple[str, ...], *, base_dir: Path | None=None) -> tuple[int | None, bool, Path | None]:
		has_flag = False
		sub_idx = None
		target_dir = base_dir
		tokens = list(argv)
		idx = 0
		while idx < len(tokens):
			tok = tokens[idx]
			if '--' == tok:
				break
			if '--no-optional-locks' == tok:
				has_flag = True
				idx += 1
			elif tok in _VALUE_GLOBAL_OPTS and (tok not in ('-C', '--work-tree') or idx + 1 >= len(tokens)):
				idx += 2
			elif tok.startswith('-') and (tok not in ('-C', '--work-tree')):
				idx += 1
			elif tok not in ('-C', '--work-tree'):
				sub_idx = idx
				break
			else:
				if None is not target_dir:
					cand = normalize_host_path(tokens[idx + 1])
					target_dir = cand.resolve() if cand.is_absolute() else (target_dir / cand).resolve()
				idx += 2
		return (sub_idx, has_flag, target_dir)
	def unflagged_git_read_commands(self, text: str) -> list[str]:
		if not isinstance(text, str) or 'git' not in text or re.search('[\\\\/]\\.gemini[\\\\/]antigravity[\\\\/]brain[\\\\/][^\\\\/]+[\\\\/]scratch[\\\\/]', text, re.I):
			r = []
		else:
			r = []
			for match in re.finditer('[\\[\\(]\\s*([\\\'"](?:[^\\\'"]*?[\\\\/])?git(?:\\.exe)?[\\\'"](?:\\s*,\\s*[^\\]\\)]+)+)[\\]\\)]', text):
				raw_items = [part.strip() for part in match.group(1).split(',')]
				parsed = [lit.group(1) if (lit := re.fullmatch('[\\\'"]([^\\\'"]*)[\\\'"]', item)) else '<expr>' for item in raw_items[1:]]
				subcommand, has_flag = self.classify_git_argv(parsed)
				if subcommand in READ_SUBCOMMANDS and (not has_flag):
					snippet = ' '.join(match.group(0).split())
					if snippet not in r:
						r.append(snippet)
			exec_cmds = [raw_lit[1:-1] if raw_lit.startswith('`') else self._unquote(raw_lit) for cm in re.finditer('\\bcmd\\s*:\\s*("(?:\\\\.|[^"\\\\])*"|\\\'(?:\\\\.|[^\\\'\\\\])*\\\'|`(?:\\\\.|[^`\\\\])*`)', text) for raw_lit in (cm.group(1),)] if 'exec_command' in text else []
			for candidate in exec_cmds or [text]:
				if not re.search('(?:\\$env:)?GIT_OPTIONAL_LOCKS\\s*=\\s*["\']?0["\']?', candidate):
					for segment, tokens in self._iter_git_segments(candidate):
						subcommand, has_flag = self.classify_git_argv(tokens)
						if subcommand in READ_SUBCOMMANDS and (not has_flag):
							normalized = ' '.join(segment.strip().split())
							if normalized not in r:
								r.append(normalized)
		return r
	def unpersisted_http_fetch_commands(self, text: str) -> list[str]:
		if not isinstance(text, str) or not text.strip() or _SANCTIONED_HTTP_RUNNER_RE.search(text) or (not (_EXTERNAL_URL_RE.search(text) and _ADHOC_HTTP_CLIENT_RE.search(text))):
			r = []
		else:
			r = [' '.join(text.strip().split())[:240]]
		return r
_INSPECTOR = ShellCommandInspector()
def _iter_shell_git_segments(candidate: str) -> list[tuple[str, list[str]]]:
	return _INSPECTOR._iter_git_segments(candidate)
def _parse_commit_subcommand_args(argv: list[str] | tuple[str, ...]) -> tuple[list[str], str | None, str | None, bool, bool, list[str]]:
	return _INSPECTOR.parse_commit_subcommand_args(argv)
def _scan_git_global_opts(argv: list[str] | tuple[str, ...], *, base_dir: Path | None=None) -> tuple[int | None, bool, Path | None]:
	return _INSPECTOR.scan_git_global_opts(argv, base_dir=base_dir)
def _split_shell_segments(cmd: str) -> list[str]:
	return _INSPECTOR._split_segments(cmd)
def _unquote(token: str) -> str:
	return _INSPECTOR._unquote(token)
def classify_git_argv(argv: list[str] | tuple[str, ...]) -> tuple[str | None, bool]:
	return _INSPECTOR.classify_git_argv(argv)
def extract_comment_issue_urls(text: str) -> set[str]:
	r: set[str] = set()
	for line in (text or '').splitlines():
		if re.match('^\\s*(?:#|//|REM\\b|/\\*|\\*)', line, re.I):
			r.update(_GITHUB_ISSUE_URL_RE.findall(line))
	return r
def extract_issue_actions_from_outputs(outputs: list[str] | tuple[str, ...]) -> list[dict]:
	return _INSPECTOR.extract_issue_actions(outputs)
def extract_issue_urls(text: str) -> list[str]:
	return list(dict.fromkeys(_GITHUB_ISSUE_URL_RE.findall(text or '')))
def is_code_file(rel_path: str | Path) -> bool:
	return Path(rel_path).suffix.lower() in _ISSUE_LINKED_CODE_SUFFIXES
def normalize_commit_message(message: str | None) -> str:
	return '\n'.join((line for line in (message or '').splitlines() if not line.startswith('#'))).strip()
def normalize_host_path(value: str | Path) -> Path:
	raw = str(value).strip()
	m = _CYGDRIVE_RE.match(raw.replace('\\', '/'))
	if not m:
		r = Path(raw)
	else:
		drive = m.group(1).upper()
		rest = m.group(2) or ''
		r = Path(f'{drive}:/{rest}')
	return r
def parse_issue_url(url: str) -> tuple[str, int] | None:
	m = _COMMIT_MESSAGE_ISSUE_URL_RE.fullmatch((url or '').strip())
	return (m.group(1), int(m.group(2))) if m else None
def prohibited_git_write_commands(text: str) -> list[str]:
	return _INSPECTOR.prohibited_git_write_commands(text)
def unflagged_git_read_commands(text: str) -> list[str]:
	return _INSPECTOR.unflagged_git_read_commands(text)
def unpersisted_http_fetch_commands(text: str) -> list[str]:
	return _INSPECTOR.unpersisted_http_fetch_commands(text)
