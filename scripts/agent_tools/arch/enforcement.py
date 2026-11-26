# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add blocking architecture audit gates with module-hash caching":
# https://github.com/dmitry-ai/harness/issues/363
from __future__ import annotations
from pathlib import Path
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
from Df.Harness.Arch.Enforcement import Enforcement
# @used-by :meth:`Df.Harness.Gate.ArchAuditGate.ArchAuditGate.check()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_enforcement_preserves_gates_and_395_participants()`
# @used-by :mod:`agent_tools.arch.enforcement`
def evaluate_pre_tool_use_arch_audit(name: str, args: dict, payload: dict) -> str | None:
	return Enforcement.evaluate_pre_tool_use(name, args, payload)
# @used-by :meth:`Df.Harness.Gate.StagedGates.StagedGates.verify()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_staged_pre_commit_handles_participant_file_paths_and_incremental_multi_wave_commits()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_enforcement_preserves_gates_and_395_participants()`
# @used-by :mod:`agent_tools.arch.enforcement`
def verify_staged_arch_audit(repo_root: Path, staged_paths: list[str], *, use_index: bool=True, strict: bool=False) -> list[str]:
	return Enforcement().verify_staged(repo_root, staged_paths, use_index=use_index, strict=strict)
__all__ = ['evaluate_pre_tool_use_arch_audit', 'verify_staged_arch_audit']
