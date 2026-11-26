# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.WorktreeIsolationGate import WorktreeIsolationGate
NAME = WorktreeIsolationGate.NAME
PRIORITY = WorktreeIsolationGate.PRIORITY
TOOLS = WorktreeIsolationGate.TOOLS
# @used-by :meth:`Df.Harness.Gate.PreToolRegistry.PreToolRegistry.__load_builtin_entry()`
# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_agent_metadata_and_read_only_tools_are_allowed()`
# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_harness_main_blocks_write_and_edit_while_linked_worktree_allows()`
# @used-by :meth:`test_worktree_isolation_gate.WorktreeIsolationGateTests.test_non_harness_repo_allows_single_turn_and_blocks_concurrent_open_turns()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return WorktreeIsolationGate().check(name, args, payload)
