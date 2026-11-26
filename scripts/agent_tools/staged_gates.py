# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.StagedGates import StagedGates
# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_agent_staged()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_staged_pre_commit_enforces_approved_receipts_cache_and_anti_pattern_washing()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_pre_commit_emits_non_blocking_mixed_warning_to_stderr()`
# @used-by :meth:`test_repo_link_gate.RepoLinkGateTests.test_issue_linter_staged_gate_and_markdown_hook_enforce_repo_link_ban()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_pre_tool_use_rules_budget_and_doctor_and_pre_commit_enforce_limits()`
# @used-by :mod:`agent_tools.staged_gates`
def verify_staged_extra_gates(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	return StagedGates(repo_root, staged_paths, use_index=use_index).verify()
__all__ = ['verify_staged_extra_gates']
