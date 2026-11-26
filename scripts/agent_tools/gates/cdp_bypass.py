# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
NAME = 'CDP-BYPASS-GATE'
PRIORITY = 80
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
TOOLS = frozenset({'run_command', 'read_file', 'write_file', 'edit_file'})
_CDP_CONTENT_HINT_RE = re.compile(r'(?:127\.0\.0\.1|localhost|\[::1\]|/json/|/devtools/|devtoolsactiveport|chrome-remote-interface|chrome-devtools-mcp)', re.I)
_SENSITIVE_READ_RE = re.compile(r'(?:/devtoolsactiveport|/(?:local state|cookies|login data|web data))$', re.I)
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
def _check_read_perimeter(raw_p: str) -> str | None:
	r = None
	norm_p = raw_p.replace('\\', '/').casefold() if raw_p else ''
	if norm_p and _SENSITIVE_READ_RE.search(norm_p) and (not _is_inside_harness_code(raw_p)):
		from ..shell_audit import protected_browser_perimeter
		perim = protected_browser_perimeter()
		ap_suffix = '/devtools' + 'activeport'
		if norm_p.endswith(ap_suffix) or norm_p in perim['active_port_files']:
			r = 'EXEC-1 / EXEC-3 / M-4: Direct read_file of DevTools' + 'ActivePort is prohibited; use harness.py or df_text.py GuardedCDP.'
		elif any((pdir and (norm_p == pdir or norm_p.startswith(pdir + '/')) and re.search('/(?:local state|cookies|login data|web data)$', norm_p) for pdir in perim['profile_dirs'])):
			r = 'EXEC-3 / EXEC-6 / M-4: Direct read_file of protected Chrome profile storage/state is prohibited.'
	return r
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
def _check_write_content(raw_p: str, content: object) -> str | None:
	r = None
	if raw_p and isinstance(content, str) and content and _CDP_CONTENT_HINT_RE.search(content):
		from ..shell_audit import _CDP_PROTOCOL_RE, is_code_file
		if is_code_file(raw_p) and _CDP_PROTOCOL_RE.search(content) and (not _is_inside_sanctioned_code(raw_p)):
			r = 'EXEC-1 / EXEC-3 / M-4: Writing external scripts that directly access loopback CDP endpoints outside sanctioned Harness code is prohibited; use harness.py or df_text.py.'
	return r
def _is_inside_harness_code(raw_path: str) -> bool:
	r = False
	if raw_path:
		# 2026-11-24
		# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
		# https://github.com/dmitry-ai/harness/issues/187
		from ..git_gate import GitRepoGate
		from ..runtime import PRIMARY
		try:
			resolved = Path(raw_path).resolve()
			prim = PRIMARY.resolve()
			if resolved.is_relative_to(prim):
				r = True
			else:
				for anc in (resolved, *resolved.parents):
					if (anc / '.git').exists():
						r = GitRepoGate(anc).main_repo() == prim
						break
		except OSError:
			r = False
	return r
def _is_inside_sanctioned_code(raw_path: str) -> bool:
	r = _is_inside_harness_code(raw_path)
	if (not r) and raw_path:
		# 2026-11-24
		# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
		# https://github.com/dmitry-ai/harness/issues/187
		from ..runtime import sanctioned_addon_code_roots
		try:
			resolved = Path(raw_path).resolve()
			r = any((resolved.is_relative_to(root) for root in sanctioned_addon_code_roots()))
		except OSError:
			r = False
	return r
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r = None
	if 'run_command' == name:
		# 2026-11-24
		# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
		# https://github.com/dmitry-ai/harness/issues/187
		from ..shell_audit import prohibited_cdp_bypass_commands
		bad = prohibited_cdp_bypass_commands(args.get('CommandLine') or '')
		if bad:
			r = 'EXEC-1 / EXEC-3 / M-4: Direct loopback CDP / browser profile access bypassing harness.py or df_text.py GuardedCDP is prohibited: ' + '; '.join(bad)
	elif 'read_file' == name:
		r = _check_read_perimeter((args.get('Path') or '').strip())
	elif name in ('write_file', 'edit_file'):
		raw_p = (args.get('Path') or '').strip()
		content = args.get('Content') if 'write_file' == name else args.get('Replacement')
		# 2026-11-24
		# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
		# https://github.com/dmitry-ai/harness/issues/187
		r = _check_write_content(raw_p, content)
	return r
