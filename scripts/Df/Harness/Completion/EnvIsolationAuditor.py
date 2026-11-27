# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.env_isolation_ops import dfh_audit_metadata_test_env_isolation, dfh_audit_worktree_land_gate_contracts
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class EnvIsolationAuditor:
	# @used-by :func:`agent_tools.env_isolation_contracts.audit_metadata_test_env_isolation()`
	def __init__(self, tests_dir: str | Path, *, scripts_dir: str | Path | None=None, registry: dict | None=None) -> None:
		self.__tests_dir = Path(tests_dir)
		self.__scripts_dir = Path(scripts_dir) if None is not scripts_dir else None
		self.__registry = registry
	# @used-by :func:`agent_tools.env_isolation_contracts.audit_metadata_test_env_isolation()`
	def run(self) -> list[str]:
		r = dfh_audit_metadata_test_env_isolation(self.__tests_dir)
		if None is not self.__scripts_dir:
			r.extend(dfh_audit_worktree_land_gate_contracts(self.__scripts_dir, self.__tests_dir, registry=self.__registry))
		return r
