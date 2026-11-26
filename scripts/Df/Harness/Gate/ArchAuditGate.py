# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.gates.arch_audit`
class ArchAuditGate:
	NAME = 'ARCH-AUDIT-GATE'
	PRIORITY = 105
	TOOLS = frozenset({'write_file', 'edit_file'})
	# @used-by :func:`agent_tools.gates.arch_audit.check()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		from agent_tools.arch.enforcement import evaluate_pre_tool_use_arch_audit
		return evaluate_pre_tool_use_arch_audit(name, args, payload or {})
