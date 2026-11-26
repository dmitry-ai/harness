# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add blocking architecture audit gates with module-hash caching":
# https://github.com/dmitry-ai/harness/issues/363
from __future__ import annotations
NAME = 'ARCH-AUDIT-GATE'
PRIORITY = 105
TOOLS = frozenset({'write_file', 'edit_file'})
# @used-by :func:`agent_tools.gates._load_builtin_entry()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_arch_audit_gate_spawns_zero_subprocesses_and_allows_trivial_or_test_edits()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_pre_tool_use_blocks_unaudited_structural_write_and_allows_cached_or_approved_design()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	from ..arch.enforcement import evaluate_pre_tool_use_arch_audit
	return evaluate_pre_tool_use_arch_audit(name, args, payload or {})
