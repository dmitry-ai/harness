# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
from pathlib import Path
import re
from ..git_gate import GitRepoGate
from ..runtime import PRIMARY, sanctioned_addon_code_roots
from ..shell_audit import _CDP_PROTOCOL_RE, is_code_file, prohibited_cdp_bypass_commands, protected_browser_perimeter
NAME = 'CDP-BYPASS-GATE'
PRIORITY = 80
def _is_inside_harness_code(raw_path: str) -> bool:
	r = False
	if raw_path:
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
		try:
			resolved = Path(raw_path).resolve()
			r = any((resolved.is_relative_to(root) for root in sanctioned_addon_code_roots()))
		except OSError:
			r = False
	return r
def _check_read_perimeter(raw_p: str) -> str | None:
	r = None
	if raw_p and (not _is_inside_harness_code(raw_p)):
		norm_p = raw_p.replace('\\', '/').casefold()
		perim = protected_browser_perimeter()
		ap_suffix = '/devtools' + 'activeport'
		if norm_p.endswith(ap_suffix) or norm_p in perim['active_port_files']:
			r = 'EXEC-1 / EXEC-3 / M-4: Direct read_file of DevTools' + 'ActivePort is prohibited; use harness.py or df_text.py GuardedCDP.'
		elif any((pdir and (norm_p == pdir or norm_p.startswith(pdir + '/')) and re.search('/(?:local state|cookies|login data|web data)$', norm_p) for pdir in perim['profile_dirs'])):
			r = 'EXEC-3 / EXEC-6 / M-4: Direct read_file of protected Chrome profile storage/state is prohibited.'
	return r
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r = None
	if 'run_command' == name:
		bad = prohibited_cdp_bypass_commands(args.get('CommandLine') or '')
		if bad:
			r = 'EXEC-1 / EXEC-3 / M-4: Direct loopback CDP / browser profile access bypassing harness.py or df_text.py GuardedCDP is prohibited: ' + '; '.join(bad)
	elif 'read_file' == name:
		r = _check_read_perimeter((args.get('Path') or '').strip())
	elif name in ('write_file', 'edit_file'):
		raw_p = (args.get('Path') or '').strip()
		content = args.get('Content') if 'write_file' == name else args.get('Replacement')
		if raw_p and isinstance(content, str) and content and (not _is_inside_sanctioned_code(raw_p)) and is_code_file(raw_p) and _CDP_PROTOCOL_RE.search(content):
			r = 'EXEC-1 / EXEC-3 / M-4: Writing external scripts that directly access loopback CDP endpoints outside sanctioned Harness code is prohibited; use harness.py or df_text.py.'
	return r
