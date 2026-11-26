# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
# 2026-11-14
# "Decompose git_gate.py into shell_audit.py, GitRepoGate, and single-pass pre-commit validation":
# https://github.com/dmitry-ai/harness/issues/67
READ_SUBCOMMANDS = ('status', 'diff', 'log', 'rev-parse', 'show', 'ls-files')
_ADHOC_HTTP_CLIENT_RE = re.compile('(?:\\burllib\\.request\\b|\\burlopen\\s*\\(|\\brequests\\.(?:get|post|head|request|Session)\\b|\\bhttpx\\.(?:get|post|Client)\\b|\\bInvoke-(?:WebRequest|RestMethod)\\b|\\b(?:iwr|irm|curl(?:\\.exe)?|wget(?:\\.exe)?)\\s+)', re.I)
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
_CDP_PROTOCOL_RE = re.compile('(?:(?:https?|wss?)://(?:127\\.0\\.0\\.1|localhost|\\[::1\\])(?::\\d+)?(?:/json(?:/|$|["\'\\s?])|/devtools/(?:page|browser)(?:/|$|["\'\\s?]))|(?:/json/(?:list|version|new|activate|close|protocol)\\b|/devtools/(?:page|browser)/[A-Za-z0-9_-]*)|\\bDevToolsActivePort\\b|\\bchrome-remote-interface\\b|\\bchrome-devtools-mcp\\b[^\\r\\n]*(?:--browser-url|--browserUrl|--autoConnect)\\b)', re.I)
_COMMIT_MESSAGE_ISSUE_URL_RE = re.compile('^https://github\\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\\d+)$')
_CYGDRIVE_RE = re.compile('^/(?:cygdrive|mnt)/([a-zA-Z])(?:/(.*))?$')
_EXTERNAL_URL_RE = re.compile('https?://(?!(?:localhost|127\\.0\\.0\\.1|\\[::1\\])\\b)[A-Za-z0-9.-]+', re.I)
_GITHUB_ISSUE_URL_RE = re.compile('https://github\\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\\d+\\b')
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
_INLINE_EXEC_RE = re.compile('\\b(?:python(?:3)?(?:\\.exe)?\\s+(?:-[A-Za-z]+\\s+)*-c|node(?:\\.exe)?\\s+(?:--[A-Za-z-]+(?:=\\S+)?\\s+)*-e)\\b', re.I)
_ISSUE_LINKED_CODE_SUFFIXES = ('.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.cs', '.ps1', '.sh', '.bash', '.cmd', '.bat', '.vbs')
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
_SANCTIONED_CDP_RUNNER_RE = re.compile('(?:harness\\.py|upwork_project\\.py|df_text\\.py|df_article\\.py|df_proposal\\.py|df_github_issue\\.py|validate_links\\.py|safe_commit\\.py|\\bunittest\\b|\\bpytest\\b)', re.I)
_SANCTIONED_HTTP_RUNNER_RE = re.compile('(?:harness\\.py|upwork_project\\.py|validate_links\\.py|df_github_issue\\.py|\\bunittest\\b|\\bpytest\\b)', re.I)
_VALUE_GLOBAL_OPTS = ('-C', '--git-dir', '--work-tree', '-c', '--exec-path', '--namespace', '--super-prefix', '--config-env')
# 2026-11-19
# "Integrate declarative Antigravity addons health and sanctioning into Harness":
# https://github.com/dmitry-ai/harness/issues/92
# @used-by :meth:`ShellCommandInspector.prohibited_cdp_bypass_commands()`
def _is_sanctioned_addon_command(seg_norm: str, *, config=None) -> bool:
	try:
		from .runtime import sanctioned_addon_code_roots
		roots = sanctioned_addon_code_roots(config)
	except Exception:
		roots = []
	for root in roots:
		r_norm = root.as_posix().rstrip('/').casefold()
		if r_norm and (r_norm + '/' in seg_norm or seg_norm.endswith(r_norm)):
			return True
	return False
# 2026-11-24
# "Cache runtime settings and deduplicate evidence validation in hot paths":
# https://github.com/dmitry-ai/harness/issues/227
from .runtime_cache import run_shell_violation_scan
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# 2026-11-24
# "Cache runtime settings and deduplicate evidence validation in hot paths":
# https://github.com/dmitry-ai/harness/issues/227
# @used-by :func:`agent_tools.gates.cdp_bypass._check_read_perimeter()`
# @used-by :meth:`ShellCommandInspector.prohibited_cdp_bypass_commands()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_runtime_settings_cache_invalidates_on_file_or_env_change_and_isolates_mutations()`
def protected_browser_perimeter(config=None) -> dict:
	from . import runtime as _rt
	from .runtime_cache import cached_browser_perimeter
	return cached_browser_perimeter(config, _rt)
# 2026-11-14
# "Decompose git_gate.py into shell_audit.py, GitRepoGate, and single-pass pre-commit validation":
# https://github.com/dmitry-ai/harness/issues/67
class ShellCommandInspector:
	# @used-by :func:`_iter_shell_git_segments()`
	# @used-by :meth:`ShellCommandInspector.prohibited_git_write_commands()`
	# @used-by :meth:`ShellCommandInspector.unflagged_git_read_commands()`
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
	# @used-by :meth:`ShellCommandInspector.parse_commit_subcommand_args()`
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
	# @used-by :func:`_split_shell_segments()`
	# @used-by :meth:`ShellCommandInspector._iter_git_segments()`
	# @used-by :meth:`ShellCommandInspector.prohibited_cdp_bypass_commands()`
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
	# @used-by :func:`_unquote()`
	# @used-by :meth:`ShellCommandInspector._iter_git_segments()`
	# @used-by :meth:`ShellCommandInspector.unflagged_git_read_commands()`
	def _unquote(self, token: str) -> str:
		if not (2 <= len(token) and token[0] == token[-1] and (token[0] in ('"', "'"))):
			r = token
		else:
			inner = token[1:-1]
			r = inner.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
		return r
	# @used-by :func:`classify_git_argv()`
	# @used-by :meth:`ShellCommandInspector.prohibited_git_write_commands()`
	# @used-by :meth:`ShellCommandInspector.unflagged_git_read_commands()`
	def classify_git_argv(self, argv: list[str] | tuple[str, ...]) -> tuple[str | None, bool]:
		tokens = list(argv)
		sub_idx, has_flag, _ = self.scan_git_global_opts(tokens)
		return (tokens[sub_idx] if None is not sub_idx else None, has_flag)
	# @used-by :func:`extract_issue_actions_from_outputs()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	def extract_issue_actions(self, outputs: list[str] | tuple[str, ...]) -> list[dict]:
		r: list[dict] = []
		# 2026-11-18
		# "Ignore source-code search and file-viewer lines in ShellCommandInspector.extract_issue_actions":
		# https://github.com/dmitry-ai/harness/issues/88
		decoder = json.JSONDecoder()
		for text in outputs or ():
			if isinstance(text, str) and '"action"' in text and ('"repo"' in text) and (not re.search('(?m)^Ran \\d+ tests? in \\d', text)) and (not re.search('(?m)^Showing lines \\d+-\\d+ of \\d+\\b', text)) and (not re.search('(?i)"consumed_files"\\s*:\\s*\\[\\s*"[^"]*(?:[/\\\\\\\\]temp[/\\\\\\\\]|[/\\\\\\\\]tmp[/\\\\\\\\])', text)):
				pos = 0
				while True:
					m_brace = re.search('(?m)^[ \\t]*\\{', text[pos:])
					if not m_brace:
						break
					raw_start = text.find('{', pos + m_brace.start())
					try:
						obj, end_idx = decoder.raw_decode(text, raw_start)
					except ValueError:
						pos = raw_start + 1
						continue
					nl_idx = text.find('\n', end_idx)
					tail = text[end_idx:] if -1 == nl_idx else text[end_idx:nl_idx]
					pos = end_idx
					if tail.strip() or not isinstance(obj, dict):
						continue
					consumed = obj.get('consumed_files')
					act = obj.get('action')
					repo = obj.get('repo')
					# 2026-11-23
					# "Implement core Issue-First verification engine in agent_tools/issue_first_gate.py":
					# https://github.com/dmitry-ai/harness/issues/143
					if obj.get('ok', True) and (not (isinstance(consumed, list) and any((re.search('(?i)(?:[/\\\\]temp[/\\\\]|[/\\\\]tmp[/\\\\])', str(cf)) for cf in consumed)))) and (act in ('create', 'fetch', 'edit', 'comment', 'close')) and isinstance(repo, str) and ('/' in repo):
						num = obj.get('number')
						if None is num:
							m = re.search('/issues/(\\d+)\\b', str(obj.get('html_url') or ''))
							if m:
								num = int(m.group(1))
						if isinstance(num, int):
							# 2026-11-18
							# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
							# https://github.com/dmitry-ai/harness/issues/84
							entry = {'action': act, 'repo': repo, 'number': num, 'url': f'https://github.com/{repo}/issues/{num}', 'ok': bool(obj.get('ok', True)), 'state': obj.get('state')}
							if isinstance(obj.get('parent_number'), int) and (not isinstance(obj.get('parent_number'), bool)):
								entry['parent_number'] = obj['parent_number']
							r.append(entry)
		return r
	# @used-by :func:`_parse_commit_subcommand_args()`
	# @used-by :meth:`ShellCommandInspector.prohibited_git_write_commands()`
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
	# @used-by :func:`prohibited_git_write_commands()`
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
	# @used-by :func:`_scan_git_global_opts()`
	# @used-by :meth:`ShellCommandInspector.classify_git_argv()`
	# @used-by :meth:`ShellCommandInspector.parse_commit_subcommand_args()`
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
	# @used-by :func:`unflagged_git_read_commands()`
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
	# 2026-11-16
	# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
	# https://github.com/dmitry-ai/harness/issues/80
	# @used-by :func:`prohibited_cdp_bypass_commands()`
	# @used-by :meth:`ShellCommandInspector.unpersisted_http_fetch_commands()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_sanctioned_addon_roots_and_cdp_bypass_gate()`
	def prohibited_cdp_bypass_commands(self, text: str, *, config=None) -> list[str]:
		if not isinstance(text, str) or not text.strip():
			return []
		perim = protected_browser_perimeter(config)
		port_alt = '|'.join((str(p) for p in perim['ports']))
		port_re = re.compile(f'(?:(?:https?|wss?)://)?(?:127\\.0\\.0\\.1|localhost|\\[::1\\]):(?:{port_alt})\\b', re.I) if port_alt else None
		r: list[str] = []
		for seg in self._split_segments(text):
			# 2026-11-19
			# "Integrate declarative Antigravity addons health and sanctioning into Harness":
			# https://github.com/dmitry-ai/harness/issues/92
			seg_norm = seg.replace('\\\\', '/').replace('\\', '/').casefold()
			is_inline = bool(_INLINE_EXEC_RE.search(seg))
			is_sanctioned = (not is_inline) and (bool(_SANCTIONED_CDP_RUNNER_RE.search(seg)) or _is_sanctioned_addon_command(seg_norm, config=config))
			if is_sanctioned:
				continue
			hit = bool(_CDP_PROTOCOL_RE.search(seg))
			if not hit and None is not port_re and port_re.search(seg):
				if re.search('(?:\\b(?:urlopen|urllib|requests|httpx|websockets|WebSocket|curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod|TcpClient|netstat|Get-NetTCPConnection)\\b)', seg, re.I):
					hit = True
			if not hit:
				for apf in perim['active_port_files']:
					if apf and apf in seg_norm:
						hit = True
						break
			if not hit:
				for pdir in perim['profile_dirs']:
					if pdir and pdir in seg_norm and re.search('(?:devtoolsactiveport|local\\s+state|/cookies\\b|/login\\s+data\\b|/web\\s+data\\b)', seg_norm):
						hit = True
						break
			if hit:
				snippet = ' '.join(seg.strip().split())[:240]
				if snippet not in r:
					r.append(snippet)
		return r
	# @used-by :func:`unpersisted_http_fetch_commands()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	def unpersisted_http_fetch_commands(self, text: str) -> list[str]:
		# 2026-11-16
		# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
		# https://github.com/dmitry-ai/harness/issues/80
		r = list(self.prohibited_cdp_bypass_commands(text))
		if isinstance(text, str) and text.strip() and (not _SANCTIONED_HTTP_RUNNER_RE.search(text)) and _EXTERNAL_URL_RE.search(text) and _ADHOC_HTTP_CLIENT_RE.search(text):
			snippet = ' '.join(text.strip().split())[:240]
			if snippet not in r:
				r.append(snippet)
		return r
_INSPECTOR = ShellCommandInspector()
# @used-by :func:`agent_tools.tdd.events._is_git_commit_command()`
def _iter_shell_git_segments(candidate: str) -> list[tuple[str, list[str]]]:
	return _INSPECTOR._iter_git_segments(candidate)
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_write_invocation()`
def _parse_commit_subcommand_args(argv: list[str] | tuple[str, ...]) -> tuple[list[str], str | None, str | None, bool, bool, list[str]]:
	return _INSPECTOR.parse_commit_subcommand_args(argv)
# @used-by :func:`agent_tools.git_gate.resolve_git_repo_from_argv()`
def _scan_git_global_opts(argv: list[str] | tuple[str, ...], *, base_dir: Path | None=None) -> tuple[int | None, bool, Path | None]:
	return _INSPECTOR.scan_git_global_opts(argv, base_dir=base_dir)
# @used-by :func:`agent_tools.failfast_gate.evaluate_pre_tool_use_test_failfast()`
# @used-by :func:`agent_tools.issue_first_bg.is_df_issue_command_text()`
# @used-by :func:`agent_tools.tdd.commands._collect_write_matches()`
# @used-by :func:`agent_tools.tdd.commands.classify_test_command()`
# @used-by :func:`agent_tools.tdd.commands.shell_test_delete_targets()`
# @used-by :func:`agent_tools.tdd.evaluator._collect_failfast_warnings()`
# @used-by :func:`agent_tools.tdd.service_exempt._is_service_command()`
def _split_shell_segments(cmd: str) -> list[str]:
	return _INSPECTOR._split_segments(cmd)
# @used-by unused
def _unquote(token: str) -> str:
	return _INSPECTOR._unquote(token)
# @used-by :func:`agent_tools.git_gate.verify_git_write_invocation()`
# @used-by :func:`agent_tools.tdd.events._is_git_commit_command()`
# @used-by :func:`git_shim.prepare_git_invocation()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_write_invocation()`
def classify_git_argv(argv: list[str] | tuple[str, ...]) -> tuple[str | None, bool]:
	return _INSPECTOR.classify_git_argv(argv)
# @used-by :meth:`agent_tools.git_gate.GitRepoGate._extract_added_diff_urls()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_touched_code_file()`
def extract_comment_issue_urls(text: str) -> set[str]:
	r: set[str] = set()
	for line in (text or '').splitlines():
		if re.match('^\\s*(?:#|//|REM\\b|/\\*|\\*)', line, re.I):
			r.update(_GITHUB_ISSUE_URL_RE.findall(line))
	return r
# @used-by :func:`agent_tools.completion._scan_child_trace_turn()`
# @used-by :func:`agent_tools.issue_first_bg._record_bg_seg_issues()`
# @used-by :func:`agent_tools.issue_first_gate.build_issue_action_events()`
# @used-by :meth:`agent_tools.platforms.antigravity.AntigravityTurnScanner._record_subagent_calls()`
# @used-by :meth:`agent_tools.platforms.antigravity.AntigravityTurnScanner._record_tool_calls()`
# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._finalize_turn()`
# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._visit_subagent_rows()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_extract_issue_actions_recognizes_fetch_and_anti_spoofing_command_check()`
def extract_issue_actions_from_outputs(outputs: list[str] | tuple[str, ...]) -> list[dict]:
	return _INSPECTOR.extract_issue_actions(outputs)
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_ready_for_close()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._has_workspace_parent_issue()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_latest_commits()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_touched_code_file()`
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_git_read_cache_detects_issue_url_in_untracked_dotpy()`
# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_diff_cache_runs_once_for_dirty_repo_and_zero_times_for_clean_repo()`
# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_historical_header_ignored_while_added_removed_and_untracked_refs_caught()`
def extract_issue_urls(text: str) -> list[str]:
	return list(dict.fromkeys(_GITHUB_ISSUE_URL_RE.findall(text or '')))
# 2026-11-26 "Add Df package dot-py bootstrap and dot-py support across Harness gates": https://github.com/dmitry-ai/harness/issues/320
# @used-by :func:`agent_tools.gates.cdp_bypass._check_write_content()`
# @used-by :func:`agent_tools.tdd.exemption.verify_staged_issue_urls()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_touched_code_file()`
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_gates_and_classifiers_recognize_dotpy_files()`
def is_code_file(rel_path: str | Path) -> bool:
	return (Path(rel_path).suffix.lower() or (Path(rel_path).name.lower() if Path(rel_path).name.startswith('.') else '')) in _ISSUE_LINKED_CODE_SUFFIXES
# @used-by :func:`agent_tools.tdd.mechanical.find_matching_mechanical_recipes()`
# @used-by :meth:`ShellCommandInspector.prohibited_git_write_commands()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_workflow()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_write_invocation()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
def normalize_commit_message(message: str | None) -> str:
	return '\n'.join((line for line in (message or '').splitlines() if not line.startswith('#'))).strip()
# @used-by :func:`agent_tools.code_size_gate._resolve_python_target()`
# @used-by :func:`agent_tools.git_gate.cleanup_stale_credential_locks()`
# @used-by :func:`agent_tools.git_gate.resolve_git_repo_from_argv()`
# @used-by :func:`agent_tools.git_gate.run_git_read()`
# @used-by :func:`agent_tools.git_ignore._configured_excludes_file()`
# @used-by :func:`agent_tools.git_ignore._detect_enclosing_repo()`
# @used-by :func:`agent_tools.git_ignore.ensure_worktree_dir_ignored()`
# @used-by :func:`agent_tools.git_ignore.prepare_worktrees_base_dir()`
# @used-by :func:`agent_tools.git_ignore.resolve_global_git_ignore_path()`
# @used-by :func:`agent_tools.git_ignore.resolve_managed_git_ignore_target()`
# @used-by :func:`agent_tools.issue_comment_gate._resolve_comment_target()`
# @used-by :func:`agent_tools.issue_first_gate.build_code_write_issue_first_event()`
# @used-by :func:`agent_tools.issue_first_gate.evaluate_pre_tool_use_issue_first()`
# @used-by :func:`agent_tools.issue_first_gate.resolve_issue_first_target()`
# @used-by :func:`agent_tools.runtime_snapshot._set_local_hooks_path()`
# @used-by :func:`agent_tools.tdd.classifier.resolve_code_scope()`
# @used-by :func:`agent_tools.tdd.commands._resolve_shell_target()`
# @used-by :func:`agent_tools.tdd.enforcement._eval_pre_write()`
# @used-by :func:`agent_tools.tdd.enforcement._resolve_worktree_git_dirs()`
# @used-by :func:`agent_tools.tdd.evaluator._git_main_repo_root()`
# @used-by :func:`agent_tools.tdd.evaluator._resolve_event_target_scopes()`
# @used-by :func:`agent_tools.tdd.events._is_git_commit_command()`
# @used-by :func:`agent_tools.tdd.events.build_file_write_tdd_event()`
# @used-by :func:`agent_tools.tdd.mechanical._resolve_repo_binding()`
# @used-by :func:`agent_tools.xref_gate._resolve_xref_target()`
# @used-by :func:`git_shim._normalize_arg_token()`
# @used-by :func:`git_shim.resolve_system_git()`
# @used-by :meth:`ShellCommandInspector.scan_git_global_opts()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.__init__()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.assert_toplevel()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.main_repo()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.run_hook()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_write_invocation()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
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
# @used-by :func:`agent_tools.issue_first_gate._seed_open_issues_from_requests()`
# @used-by :func:`agent_tools.issues.parity.merge_turn_issue_item()`
# @used-by :func:`agent_tools.tdd.exemption._is_same_repo_url()`
# @used-by :func:`agent_tools.tdd.mechanical._recipe_matches_repo()`
# @used-by :func:`agent_tools.tdd.mechanical._validate_recipe_inputs()`
# @used-by :func:`agent_tools.tdd.ratchet._find_issue_ratchet_approval()`
# @used-by :meth:`ShellCommandInspector.prohibited_git_write_commands()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_workflow()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_write_invocation()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._committed_parent_numbers()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._has_workspace_parent_issue()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._parent_linked_committed_urls()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._verify_required_repo_issues()`
def parse_issue_url(url: str) -> tuple[str, int] | None:
	m = _COMMIT_MESSAGE_ISSUE_URL_RE.fullmatch((url or '').strip())
	return (m.group(1), int(m.group(2))) if m else None
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# @used-by :func:`agent_tools.gates.cdp_bypass.check()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m4_cdp_bypass_gate_and_m5_browser_mcp_gate()`
def prohibited_cdp_bypass_commands(text: str, *, config=None) -> list[str]:
	return _INSPECTOR.prohibited_cdp_bypass_commands(text, config=config)
# @used-by :func:`agent_tools.gates.git_write.check()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message()`
def prohibited_git_write_commands(text: str) -> list[str]:
	return _INSPECTOR.prohibited_git_write_commands(text)
# @used-by :func:`agent_tools.platforms.trace_common.collect_shell_violations()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_read_git_and_git_shim_and_unflagged_detector()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_unflagged_git_read_allows_env_assignment()`
def unflagged_git_read_commands(text: str) -> list[str]:
	return _INSPECTOR.unflagged_git_read_commands(text)
# @used-by :func:`agent_tools.platforms.trace_common.collect_shell_violations()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m4_cdp_bypass_gate_and_m5_browser_mcp_gate()`
def unpersisted_http_fetch_commands(text: str) -> list[str]:
	return _INSPECTOR.unpersisted_http_fetch_commands(text)
