# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce live PreToolUse Issue-First gate before TDD in check_rules_and_server_gate.py":
# https://github.com/dmitry-ai/harness/issues/145
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce live TDD PreToolUse gate in check_rules_and_server_gate.py":
# https://github.com/dmitry-ai/harness/issues/136
# 2026-11-22 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce similar_projects parity gate, hooks, and documented CLI contract across turn completion and issue lifecycle":
# https://github.com/dmitry-ai/harness/issues/123
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire automatic journal upgrade and bucketed step resolution across Harness subsystems":
# https://github.com/dmitry-ai/harness/issues/109
# 2026-11-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
# https://github.com/dmitry-ai/harness/issues/101
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Integrate declarative Antigravity addons health and sanctioning into Harness":
# https://github.com/dmitry-ai/harness/issues/92
# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix post-audit edge cases in parent-child issue validation and turn-scoped lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/87
# 2026-11-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
# https://github.com/dmitry-ai/harness/issues/84
# 2026-11-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent journal-watch duplicate pairs on orphan steps, block direct journal writes bypassing answer-prepare, add recover-turn-violation, and harden watcher lifecycle":
# https://github.com/dmitry-ai/harness/issues/36
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent_tools.git_gate import prohibited_git_write_commands
from agent_tools.issue_first_gate import evaluate_pre_tool_use_issue_first
from agent_tools.runtime import PRIMARY, sanctioned_addon_code_roots
from agent_tools.shell_audit import _CDP_PROTOCOL_RE, is_code_file, prohibited_cdp_bypass_commands, protected_browser_perimeter
from agent_tools.tdd_gate import evaluate_pre_tool_use_tdd
MAX_UNPERSISTED_SOURCE_READS = 10
def check_rules_budget(name: str, args: dict) -> str | None:
	r = None
	path = args.get('Path', '')
	normalized = path.replace('\\', '/').lower() if path else ''
	content = (args.get('Content') if 'write_file' == name else args.get('Replacement')) if '/.agents/rules/' in normalized else None
	if content:
		byte_len = len(content.encode('utf-8'))
		if normalized.endswith('90-project.md') and byte_len > 4000:
			r = f"Size of 90-project.md ({byte_len} bytes) exceeds the 4,000-byte limit to avoid dropping out of the Antigravity system prompt. Run 'python {(PRIMARY / 'scripts/split_project_rules.py').as_posix()}' for automatic splitting or move the new section into a separate module .agents/rules/9X-<topic>.md."
		elif re.search('/9[1-9]-[^/]+\\.md$', normalized) and byte_len > 6000:
			r = f'Size of rule module {path} ({byte_len} bytes) exceeds the 6,000-byte limit. Split it into smaller topical modules.'
	return r
def check_server_hygiene(name: str, args: dict) -> str | None:
	r = None
	if 'run_command' == name:
		cmd = args.get('CommandLine', '')
		is_server_cmd = bool(re.search('\\b(nxcli\\.io|nxcli\\.net|ssh\\.exe|ssh\\s+)\\b', cmd, re.IGNORECASE))
		backup_pattern = re.search('(\\.bak\\b|\\.backup\\b|\\.orig\\b|_backup\\w*|cp\\s+.*\\.bak)', cmd, re.IGNORECASE)
		if is_server_cmd and backup_pattern:
			r = 'Creating backup files (*.bak, *.backup, _backup, *.orig) on remote servers is strictly prohibited! Use local Git.'
	elif name in ('write_file', 'edit_file'):
		content = args.get('Content') if 'write_file' == name else args.get('Replacement')
		if content and isinstance(content, str):
			is_server_script = bool(re.search('\\b(nxcli\\.io|nxcli\\.net|ssh\\.exe)\\b', content, re.IGNORECASE))
			has_backup_cmd = bool(re.search('(\\.bak\\b|\\.backup\\b|\\.orig\\b|_backup\\w*|cp\\s+.*\\.bak)', content, re.IGNORECASE))
			if is_server_script and has_backup_cmd:
				r = 'Script contains server backup commands (*.bak, *.backup, _backup)! Creating backups on remote servers is strictly prohibited! Use local Git.'
	return r
def check_git_write_gate(name: str, args: dict) -> str | None:
	if 'run_command' != name:
		return None
	cmd = args.get('CommandLine', '')
	violations = prohibited_git_write_commands(cmd)
	return '; '.join(violations) if violations else None
def check_journal_write_gate(name: str, args: dict) -> str | None:
	if name in ('write_file', 'edit_file'):
		path = (args.get('Path') or '').replace('\\', '/')
		if re.search('(?:^|/)\\ua66e/(?:[^/]+/)?(?:req|res|\\u227b|\\u227a)/(?:\\d+[-\\u2013]\\d+/)?[^/]+\\.md$', path, re.IGNORECASE):
			return 'FILE-3 / FILE-4: Direct write_file or edit_file to journal req/res (or \u227b/\u227a) files is prohibited; use harness.py answer-prepare to record primary responses with answer-groups receipts.'
	elif 'run_command' == name:
		cmd = args.get('CommandLine') or ''
		if re.search('\\brecord_step\\.py\\b', cmd, re.IGNORECASE) and (not re.search('\\bgit\\b[^;|\\n]*\\brm\\b[^;|\\n]*\\brecord_step\\.py\\b', cmd, re.IGNORECASE)):
			return 'FILE-3 / FILE-4: Executing record_step.py is prohibited; use harness.py answer-prepare to record primary responses with answer-groups receipts.'
	return None
def check_batch_analysis_generator(name: str, args: dict) -> str | None:
	if name in ('write_file', 'edit_file'):
		path = (args.get('Path') or '').replace('\\', '/').lower()
		content = args.get('Content') if 'write_file' == name else args.get('Replacement')
		if path.endswith('.py') and ('/scratch/' in path or '/\ua616/' in path) and isinstance(content, str):
			if re.search('analysis\\.md', content, re.I) and re.search('\\b(?:write_text|write_bytes|open\\s*\\()\\b', content):
				return 'FILE-5 / EXEC-1 / VERIFY-1: Writing batch Python generator scripts in scratch/ to synthesize analysis.md files from memory is prohibited. Write each analysis.md directly from its primary source.md or delegate via invoke_subagent.'
	elif 'run_command' == name:
		cmd = args.get('CommandLine') or ''
		if re.search('build_analyses\\.py', cmd, re.I):
			return 'FILE-5 / EXEC-1 / VERIFY-1: Executing batch analysis.md synthesis scripts is prohibited.'
	return None
def check_bulk_source_read_streak(name: str, args: dict, payload: dict) -> str | None:
	if 'read_file' != name:
		return None
	target = (args.get('Path') or '').replace('\\', '/').lower()
	if not target.endswith('/kb/source.md'):
		return None
	t_path_raw = payload.get('transcriptPath') or ''
	if not t_path_raw:
		return None
	t_path = Path(t_path_raw)
	if not t_path.is_file():
		return None
	try:
		lines = [json.loads(line) for line in t_path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
	except Exception:
		return None
	last_user = -1
	for idx, row in enumerate(lines):
		if isinstance(row, dict) and 'USER_INPUT' == row.get('type'):
			last_user = idx
	streak_sources = set()
	for row in lines[last_user + 1:]:
		if not isinstance(row, dict):
			continue
		for call in row.get('tool_calls') or []:
			if not isinstance(call, dict):
				continue
			cname = call.get('name', '')
			cargs = call.get('args') or {}
			if isinstance(cargs, str):
				try:
					cargs = json.loads(cargs)
				except ValueError:
					cargs = {}
			if not isinstance(cargs, dict):
				cargs = {}
			if 'invoke_subagent' == cname:
				streak_sources.clear()
			elif cname in ('write_file', 'edit_file'):
				wpath = (cargs.get('Path') or '').replace('\\', '/').lower()
				if wpath.endswith('/kb/analysis.md') or '/\ua616/kb/' in wpath:
					streak_sources.clear()
			elif 'read_file' == cname:
				rpath = (cargs.get('Path') or '').replace('\\', '/').lower()
				if rpath.endswith('/kb/source.md'):
					streak_sources.add(rpath)
	if target not in streak_sources and len(streak_sources) >= MAX_UNPERSISTED_SOURCE_READS:
		return f'REVIEW-1 / KB-3: Already read {len(streak_sources)} source.md files in a row without persisting analysis.md or delegating to af-worker (limit: {MAX_UNPERSISTED_SOURCE_READS}). Persist analysis.md for already-read cases or delegate via invoke_subagent before reading more source.md files.'
	return None
EXTERNAL_WRITE_INTENT_RE = re.compile(
	'(?i)\\b(?:'
	'github|gh\\s+issue|df_github_issue|df-github-issue|issue\\s*#?\\d+|'
	'create\\s+(?:an?\\s+)?issue|open\\s+(?:an?\\s+)?issue|close\\s+(?:the\\s+)?issue|edit\\s+(?:the\\s+)?issue|comment\\s+on\\s+issue|'
	'git\\s+push|commit|pull\\s+request|'
	'\\u0438\\u0441\\u043f\\u0440\\u0430\\u0432\\w+|\\u0441\\u0434\\u0435\\u043b\\u0430\\u0439\\w*|\\u0440\\u0435\\u0430\\u043b\\u0438\\u0437\\u0443\\u0439\\w*|\\u043f\\u0435\\u0440\\u0435\\u0434\\u0435\\u043b\\u0430\\u0439\\w*|'
	'\\u0437\\u0430\\u043a\\u043e\\u043c\\u043c\\u0438\\u0442\\w+|\\u043e\\u043f\\u0443\\u0431\\u043b\\u0438\\u043a\\u0443\\u0439\\w*|'
	'\\u0441\\u043e\\u0437\\u0434\\u0430\\u0439\\w*\\s+issue|\\u0437\\u0430\\u043a\\u0440\\u043e\\u0439\\w*\\s+issue|\\u043e\\u0431\\u043d\\u043e\\u0432\\u0438\\w*\\s+issue'
	')\\b'
)
def _upwork_project_root_for_command(cmd: str) -> Path | None:
	candidates = []
	for m in re.finditer('(?:--project-root|--body-file|-F|--title-file|--comment-file)\\s+(?:"([^"]+)"|\'([^\']+)\'|(\\S+))', cmd):
		raw_p = m.group(1) or m.group(2) or m.group(3)
		if raw_p:
			try:
				candidates.append(Path(raw_p).resolve())
			except OSError:
				pass
	try:
		candidates.append(Path.cwd().resolve())
	except OSError:
		pass
	from agent_tools.path_registry import project_paths
	for c in candidates:
		try:
			pp = project_paths(c)
			if pp.project_json.is_file():
				return pp.root
		except (OSError, ValueError):
			pass
		for anc in (c, *c.parents):
			if (anc / '\ua616/project.json').is_file():
				return anc
	return None
def check_external_write_gate(name: str, args: dict) -> str | None:
	if 'run_command' != name:
		return None
	cmd = args.get('CommandLine') or ''
	if re.search('(?:^|[;|\\n&]|\\s)gh(?:\\.exe)?\\s+issue\\s+(?:create|edit|comment|close|reopen|delete)\\b', cmd, re.I):
		return 'EXEC-5 / SCOPE-2: Direct gh issue write commands in the shell are prohibited; use df_github_issue.py with UTF-8 file input and mandatory API read-back verification.'
	if re.search('(?:^|[;|\\n&]|\\s)gh(?:\\.exe)?\\s+api\\b[^;|\\n]*(?:--method(?:\\s+|=)|-X\\s*)(?:POST|PATCH|PUT|DELETE)\\b', cmd, re.I):
		return 'EXEC-5 / SCOPE-2: Direct mutating gh api calls (POST/PATCH/PUT/DELETE) in the shell are prohibited; use df_github_issue.py.'
	for gh_m in re.finditer('(?:^|[;|\\n&]|\\s)(gh(?:\\.exe)?\\s+api\\b[^;|\\n]*)', cmd, re.I):
		gh_seg = gh_m.group(1)
		if re.search('(?:--input|-f|--raw-field|-F|--field)(?:\\s|=|$)', gh_seg) and (not re.search('(?:--method(?:\\s+|=)|-X\\s*)GET\\b', gh_seg, re.I)):
			return 'EXEC-5 / SCOPE-2: Direct mutating gh api calls with input/field arguments are prohibited; use df_github_issue.py.'
	if re.search('\\bdf_github_issue\\.py\\s+(?:create|edit|comment|close)\\b', cmd, re.I):
		proj_root = _upwork_project_root_for_command(cmd)
		if None is not proj_root:
			from agent_tools.path_registry import project_paths
			turns_dir = project_paths(proj_root).turns_dir
			if turns_dir.is_dir():
				for tfile in turns_dir.glob('*.json'):
					if tfile.name.endswith(('-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json')):
						continue
					try:
						tdata = json.loads(tfile.read_text(encoding='utf-8'))
					except (OSError, ValueError):
						continue
					if not isinstance(tdata, dict) or 'open' != tdata.get('status'):
						continue
					if True is tdata.get('external_write_authorized'):
						continue
					req_text = '\n'.join((r.get('text', '') if isinstance(r, dict) else str(r) for r in tdata.get('requests') or []))
					if req_text.strip() and (not EXTERNAL_WRITE_INTENT_RE.search(req_text)):
						return 'SCOPE-2 / EXEC-5: Uninstructed external GitHub write (df_github_issue.py create/edit/comment/close) during a read-only analysis turn is prohibited without an explicit user instruction.'
	return None
def _is_inside_harness_code(raw_path: str) -> bool:
	if not raw_path:
		return False
	try:
		return Path(raw_path).resolve().is_relative_to(PRIMARY.resolve())
	except OSError:
		return False
def _is_inside_sanctioned_code(raw_path: str) -> bool:
	if _is_inside_harness_code(raw_path):
		return True
	if not raw_path:
		return False
	try:
		resolved = Path(raw_path).resolve()
		return any((resolved.is_relative_to(root) for root in sanctioned_addon_code_roots()))
	except OSError:
		return False
def check_cdp_bypass_gate(name: str, args: dict) -> str | None:
	if 'run_command' == name:
		cmd = args.get('CommandLine') or ''
		bad = prohibited_cdp_bypass_commands(cmd)
		if bad:
			return 'EXEC-1 / EXEC-3 / M-4: Direct loopback CDP / browser profile access bypassing harness.py or df_text.py GuardedCDP is prohibited: ' + '; '.join(bad)
	elif 'read_file' == name:
		raw_p = (args.get('Path') or '').strip()
		if raw_p and (not _is_inside_harness_code(raw_p)):
			norm_p = raw_p.replace('\\', '/').casefold()
			perim = protected_browser_perimeter()
			if norm_p.endswith('/devtoolsactiveport') or norm_p in perim['active_port_files']:
				return 'EXEC-1 / EXEC-3 / M-4: Direct read_file of DevToolsActivePort is prohibited; use harness.py or df_text.py GuardedCDP.'
			for pdir in perim['profile_dirs']:
				if pdir and (norm_p == pdir or norm_p.startswith(pdir + '/')) and re.search('/(?:local state|cookies|login data|web data)$', norm_p):
					return 'EXEC-3 / EXEC-6 / M-4: Direct read_file of protected Chrome profile storage/state is prohibited.'
	elif name in ('write_file', 'edit_file'):
		raw_p = (args.get('Path') or '').strip()
		content = args.get('Content') if 'write_file' == name else args.get('Replacement')
		if raw_p and isinstance(content, str) and content and (not _is_inside_sanctioned_code(raw_p)) and is_code_file(raw_p):
			if _CDP_PROTOCOL_RE.search(content):
				return 'EXEC-1 / EXEC-3 / M-4: Writing external scripts that directly access loopback CDP endpoints (/json, /devtools/page/, /devtools/browser/, DevToolsActivePort) outside sanctioned Harness code is prohibited; use harness.py or df_text.py.'
	return None
def _turn_has_background_mcp_new_page(payload: dict) -> bool:
	t_path_raw = payload.get('transcriptPath') or ''
	if not t_path_raw:
		return False
	t_path = Path(t_path_raw)
	if not t_path.is_file():
		return False
	try:
		rows = [json.loads(line) for line in t_path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
	except Exception:
		return False
	last_user = -1
	for idx, row in enumerate(rows):
		if isinstance(row, dict) and 'USER_INPUT' == row.get('type'):
			last_user = idx
	for row in rows[last_user + 1:]:
		if not isinstance(row, dict):
			continue
		for call in row.get('tool_calls') or []:
			if not isinstance(call, dict):
				continue
			cname = str(call.get('name') or '')
			if cname.startswith('mcp_') and cname.endswith('new_page'):
				cargs = call.get('args') or {}
				if isinstance(cargs, str):
					try:
						cargs = json.loads(cargs)
					except ValueError:
						cargs = {}
				if isinstance(cargs, dict) and (True is cargs.get('background') or bool(cargs.get('isolatedContext'))):
					return True
	return False
def check_browser_mcp_gate(name: str, args: dict, payload: dict) -> str | None:
	if name.startswith('mcp_') and re.search('(?:chrome|devtools|browser|playwright|page)', name, re.I):
		if name.endswith('new_page'):
			if True is not args.get('background') and (not args.get('isolatedContext')):
				return 'EXEC-3 / M-5: Browser MCP new_page must set background=true (or isolatedContext) so user browser windows are never focused or hijacked.'
		elif name.endswith(('navigate_page', 'close_page', 'select_page')):
			if not _turn_has_background_mcp_new_page(payload):
				return 'EXEC-3 / M-5: Calling navigate_page/close_page/select_page without first creating an agent-owned background page via new_page(background=true) in this turn is prohibited; user tabs are strictly read-only.'
	elif 'invoke_subagent' == name:
		prompt_text = str(args.get('Prompt') or '')
		if 'browser' == str(args.get('TypeName') or '').strip().lower() and _CDP_PROTOCOL_RE.search(prompt_text):
			return 'EXEC-3 / M-5: Instructing browser subagent to attach to loopback CDP endpoints is prohibited.'
	elif name in ('write_file', 'edit_file'):
		norm_p = (args.get('Path') or '').replace('\\', '/').lower()
		content = args.get('Content') if 'write_file' == name else args.get('Replacement')
		if norm_p.endswith('/mcp_config.json') and isinstance(content, str) and re.search('chrome-devtools', content, re.I) and re.search('(?:--autoConnect|--browser-url|--browserUrl)', content, re.I):
			return 'EXEC-3 / M-5: Configuring chrome-devtools-mcp with --autoConnect or --browser-url against the user Chrome session is prohibited; bind it to chrome-headless-shell with --headless and --isolated.'
	return None
def check_issue_first_gate(name: str, args: dict, payload: dict) -> str | None:
	return evaluate_pre_tool_use_issue_first(name, args, payload)
def check_tdd_gate(name: str, args: dict, payload: dict) -> str | None:
	return evaluate_pre_tool_use_tdd(name, args, payload)
def main():
	decision = {'decision': 'allow'}
	try:
		raw = sys.stdin.read()
		if raw.strip():
			payload = json.loads(raw)
			tool_call = payload.get('toolCall', {})
			name = tool_call.get('name', '')
			args = tool_call.get('args', {})
			for gate_label, check_fn in (
				('RULES-BUDGET-GATE', lambda: check_rules_budget(name, args)),
				('SERVER-HYGIENE-GATE', lambda: check_server_hygiene(name, args)),
				('EXEC-5-GIT-GATE', lambda: check_git_write_gate(name, args)),
				('SCOPE-2-EXTERNAL-WRITE-GATE', lambda: check_external_write_gate(name, args)),
				('FILE-3-JOURNAL-GATE', lambda: check_journal_write_gate(name, args)),
				('VERIFY-1-BATCH-SYNTHESIS-GATE', lambda: check_batch_analysis_generator(name, args)),
				('REVIEW-1-BULK-SOURCE-GATE', lambda: check_bulk_source_read_streak(name, args, payload)),
				('CDP-BYPASS-GATE', lambda: check_cdp_bypass_gate(name, args)),
				('M-5-BROWSER-MCP-GATE', lambda: check_browser_mcp_gate(name, args, payload)),
				('EXEC-5-ISSUE-FIRST-GATE', lambda: check_issue_first_gate(name, args, payload)),
				('EXEC-2-TDD-GATE', lambda: check_tdd_gate(name, args, payload)),
			):
				err = check_fn()
				if err:
					decision = {'decision': 'deny', 'reason': f'REJECTED ({gate_label}): {err}'}
					break
	except Exception:
		decision = {'decision': 'allow'}
	sys.stdout.write(json.dumps(decision, ensure_ascii=False))
if '__main__' == __name__:
	main()
