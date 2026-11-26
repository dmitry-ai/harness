# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Gate.BulkSourceReadGate import BulkSourceReadGate
from pathlib import Path
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class BrowserMcpGate:
	NAME = 'M-5-BROWSER-MCP-GATE'
	PRIORITY = 90
	TOOLS = frozenset({'mcp_*', 'invoke_subagent', 'write_file', 'edit_file'})
	__AUTO_CONN_RE = re.compile('(?:--auto' + 'Connect|--browser' + '-url|--browser' + 'Url)', re.I)
	# @used-by :meth:`BrowserMcpGate.check()`
	@staticmethod
	def __prompt_uses_loopback_cdp(prompt: str) -> bool:
		from agent_tools.shell_audit import _CDP_PROTOCOL_RE
		return bool(_CDP_PROTOCOL_RE.search(prompt))
	# @used-by :func:`agent_tools.gates.browser_mcp._turn_has_background_mcp_new_page()`
	# @used-by :meth:`BrowserMcpGate.check()`
	@staticmethod
	def turn_has_background_mcp_new_page(payload: dict) -> bool:
		t_raw = (payload or {}).get('transcriptPath') or ''
		r = False
		if t_raw:
			for row in BulkSourceReadGate.recent_segment_rows(Path(t_raw)):
				for call in row.get('tool_calls') or []:
					if isinstance(call, dict):
						cname = str(call.get('name') or '')
						if cname.startswith('mcp_') and cname.endswith('new_page'):
							cargs = BulkSourceReadGate.parse_call_args(call.get('args'))
							if True is cargs.get('background') or bool(cargs.get('isolatedContext')):
								r = True
								break
				if r:
					break
		return r
	# @used-by :func:`agent_tools.gates.browser_mcp.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_pretool_classes_cover_all_guards()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		r = None
		if name.startswith('mcp_') and re.search('(?:chrome|devtools|browser|playwright|page)', name, re.I):
			if name.endswith('new_page') and True is not args.get('background') and (not args.get('isolatedContext')):
				r = 'EXEC-3 / M-5: Browser MCP new_page must set background=true (or isolatedContext) so user browser windows are never focused or hijacked.'
			elif name.endswith(('navigate_page', 'close_page', 'select_page')) and (not BrowserMcpGate.turn_has_background_mcp_new_page(payload or {})):
				r = 'EXEC-3 / M-5: Calling navigate_page/close_page/select_page without first creating an agent-owned background page via new_page(background=true) in this turn is prohibited; user tabs are strictly read-only.'
		elif 'invoke_subagent' == name and 'browser' == str(args.get('TypeName') or '').strip().lower() and BrowserMcpGate.__prompt_uses_loopback_cdp(str(args.get('Prompt') or '')):
			r = 'EXEC-3 / M-5: Instructing browser subagent to attach to loopback CDP endpoints is prohibited.'
		elif name in ('write_file', 'edit_file'):
			norm_p = (args.get('Path') or '').replace('\\', '/').lower()
			content = args.get('Content') if 'write_file' == name else args.get('Replacement')
			if norm_p.endswith('/mcp_config.json') and isinstance(content, str) and re.search('chrome-devtools', content, re.I) and BrowserMcpGate.__AUTO_CONN_RE.search(content):
				r = 'EXEC-3 / M-5: Configuring chrome-devtools-mcp with --auto' + 'Connect or --browser' + '-url against the user Chrome session is prohibited; bind it to chrome-headless-shell with --headless and --isolated.'
		return r
