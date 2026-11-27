# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Platform.Codex.ReviewProver import ReviewProver
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.runtime_context import dfh_platform_settings
from Df.Harness.lib.runtime_instances import dfh_extract_platform_homes
from Df.Harness.lib.trace_review import dfh_verify_review_proof_core
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ProofVerifier:
	# @used-by :func:`agent_tools.platforms.codex.verify_native_proof()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_ag_and_codex_registrars_verifiers_and_title_sync()`
	def __init__(self, root, native: dict[str, Any], package: str | None=None, *, _ops: dict[str, Any] | None=None) -> None:
		self.__root = root
		self.__native = native
		self.__package = package
		self.__ops = _ops or {}
	# @used-by :func:`agent_tools.platforms.codex.verify_native_proof()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_ag_and_codex_registrars_verifiers_and_title_sync()`
	def run(self) -> dict[str, Any]:
		load_cfg = self.__ops.get('settings') or (lambda: SettingsLoader().run())
		ps_fn = self.__ops.get('platform_settings') or (lambda name: dfh_platform_settings(name, settings_fn=load_cfg))
		homes_fn = self.__ops.get('extract_platform_homes') or dfh_extract_platform_homes
		home = Path(self.__native.get('native_profile_home', '')).resolve()
		role = (self.__native.get('executor_metadata') or {}).get('role') or 'AA'
		allowed_homes = [Path(value).resolve() for value in homes_fn(ps_fn('codex'), platform='codex', include_disabled=True).values()]
		if home not in allowed_homes:
			raise ValueError('Saved Codex proof names an unconfigured profile')
		prover_fn = self.__ops.get('native_review_proof') or (lambda r, pid, rid, **kw: ReviewProver(r, pid, rid, _ops=self.__ops, **kw).run())
		live = prover_fn(self.__root, self.__native.get('parent_id', ''), self.__native.get('reviewer_id', ''), backend=home, instance=self.__native.get('instance'), write=False, role=role)
		r = dfh_verify_review_proof_core(self.__root, self.__native, live, ('native_log_sha256', 'final_response_sha256', 'assignment_sha256', 'assignment_source', 'review_inputs', 'final_step', 'job_id', 'observed_model', 'model_selection'), trace_error='Codex review proof differs from the actual native trace', identity_error='Codex review proof has a different explicit project identity')
		if self.__package and (not any((Path(item['package']).name == self.__package for item in r['review_inputs']))):
			raise ValueError('Codex reviewer did not verify this immutable KB review package')
		return r
