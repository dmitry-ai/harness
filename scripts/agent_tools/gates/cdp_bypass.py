# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.CdpBypassGate import CdpBypassGate
NAME = CdpBypassGate.NAME
PRIORITY = CdpBypassGate.PRIORITY
TOOLS = CdpBypassGate.TOOLS
# @used-by :mod:`agent_tools.gates.cdp_bypass`
def _is_inside_harness_code(raw_path: str) -> bool:
	return CdpBypassGate.is_inside_harness_code(raw_path)
# @used-by :mod:`agent_tools.gates.cdp_bypass`
def _is_inside_sanctioned_code(raw_path: str) -> bool:
	return CdpBypassGate.is_inside_sanctioned_code(raw_path)
# @used-by :meth:`Df.Harness.Gate.PreToolRegistry.PreToolRegistry.__load_builtin_entry()`
# @used-by :meth:`test_hook_lazy_imports.HookLazyImportsTests.test_cdp_bypass_py_edit_and_read_skip_git_gate_and_still_blocks_loopback()`
# @used-by :mod:`agent_tools.gates.cdp_bypass`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return CdpBypassGate().check(name, args, payload)
__all__ = ['NAME', 'PRIORITY', 'TOOLS', '_is_inside_harness_code', '_is_inside_sanctioned_code', 'check']
