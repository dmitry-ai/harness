# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.ArchAuditGate import ArchAuditGate
NAME = ArchAuditGate.NAME
PRIORITY = ArchAuditGate.PRIORITY
TOOLS = ArchAuditGate.TOOLS
# @used-by :meth:`Df.Harness.Gate.PreToolRegistry.PreToolRegistry.__load_builtin_entry()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_arch_audit_gate_spawns_zero_subprocesses_and_allows_trivial_or_test_edits()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_pre_tool_use_blocks_unaudited_structural_write_and_allows_cached_or_approved_design()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return ArchAuditGate().check(name, args, payload)
