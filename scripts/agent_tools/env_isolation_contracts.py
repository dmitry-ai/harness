# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Completion.EnvIsolationAuditor import EnvIsolationAuditor
from Df.Harness.lib.env_isolation_ops import HOST_PROFILE_ENV_VARS, WORKTREE_LAND_GATE_CONTRACTS, dfh_audit_worktree_land_gate_contracts as audit_worktree_land_gate_contracts, dfh_isolated_host_env as isolated_host_env, dfh_isolated_subprocess_env as isolated_subprocess_env
# @used-by :meth:`test_env_isolation_and_worktree_gate_contracts.EnvIsolationAndWorktreeGateContractsTests.test_harness_metadata_tests_pass_host_env_isolation_contract_and_negative_detection()`
def audit_metadata_test_env_isolation(tests_dir: Path) -> list[str]:
	return EnvIsolationAuditor(tests_dir).run()