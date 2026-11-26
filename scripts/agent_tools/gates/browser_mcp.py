# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.BrowserMcpGate import BrowserMcpGate
NAME = BrowserMcpGate.NAME
PRIORITY = BrowserMcpGate.PRIORITY
TOOLS = BrowserMcpGate.TOOLS
# @used-by :mod:`agent_tools.gates.browser_mcp`
def _turn_has_background_mcp_new_page(payload: dict) -> bool:
	return BrowserMcpGate.turn_has_background_mcp_new_page(payload)
# @used-by :meth:`Df.Harness.Gate.PreToolRegistry.PreToolRegistry.__load_builtin_entry()`
# @used-by :mod:`agent_tools.gates.browser_mcp`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return BrowserMcpGate().check(name, args, payload)
__all__ = ['NAME', 'PRIORITY', 'TOOLS', '_turn_has_background_mcp_new_page', 'check']
