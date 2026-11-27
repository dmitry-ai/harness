# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.Platform.Antigravity.ReviewProver import ReviewProver
from Df.Harness.lib.ag_metadata import dfh_proof_paths
from Df.Harness.lib.ag_review_wait import dfh_reviewer_assigned_package
from Df.Harness.lib.trace_review import dfh_verify_review_proof_core
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ProofVerifier:
	# @used-by :func:`agent_tools.platforms.antigravity.verify_native_proof()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_ag_and_codex_registrars_verifiers_and_title_sync()`
	def __init__(self, root, native: dict[str, Any], package: str | None=None, *, _ops: dict[str, Any] | None=None) -> None:
		self.__root = root
		self.__native = native
		self.__package = package
		self.__ops = _ops or {}
	# @used-by :func:`agent_tools.platforms.antigravity.verify_native_proof()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_ag_and_codex_registrars_verifiers_and_title_sync()`
	def run(self) -> dict[str, Any]:
		paths_fn = self.__ops.get('proof_paths') or (lambda n: dfh_proof_paths(n, settings_fn=self.__ops.get('settings'), instances_fn=self.__ops.get('platform_instances')))
		paths = paths_fn(self.__native)
		role = (self.__native.get('executor_metadata') or {}).get('role') or ('ARCH' if 'arch-auditor' == self.__native.get('agent_name') else 'AA')
		prover_fn = self.__ops.get('native_review_proof') or (lambda r, pid, rid, **kw: ReviewProver(r, pid, rid, _ops=self.__ops, **kw).run())
		live = prover_fn(self.__root, self.__native.get('parent_id', ''), self.__native.get('reviewer_id', ''), backend=paths['backend_dir'], instance=paths['instance'], write=False, role=role)
		r = dfh_verify_review_proof_core(self.__root, self.__native, live, ('native_log_sha256', 'final_response_sha256', 'final_step', 'job_id'), allow_legacy_generation_model=True)
		if self.__package and (not dfh_reviewer_assigned_package(r['native_log'], self.__package, parent_id=r.get('parent_id'), final_step=r.get('final_step'))):
			raise ValueError('Native reviewer was not assigned this immutable KB review package')
		return r
