# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
VOLATILE_META_KEYS = frozenset({'metadata_sources', 'observation_history', 'observed', 'requested'})
# @used-by :func:`_history_equivalent()`
# @used-by :func:`dfh_executor_metadata_equivalent()`
def _dict_prefix_match(saved: object, live: object, *, same_values: bool) -> bool:
	r = False
	if isinstance(saved, list) and isinstance(live, list) and len(live) >= len(saved) and live[:len(saved)] == saved:
		if not same_values:
			r = True
		else:
			saved_vals = {item.get('value') for item in saved if isinstance(item, dict)}
			live_vals = {item.get('value') for item in live if isinstance(item, dict)}
			r = saved_vals == live_vals
	return r
# @used-by :func:`dfh_executor_metadata_equivalent()`
def _history_equivalent(saved_h: object, live_h: object) -> bool:
	if saved_h == live_h:
		r = True
	elif isinstance(saved_h, dict) and isinstance(live_h, dict) and set(saved_h) == set(live_h):
		r = all((_dict_prefix_match(saved_h[k], live_h[k], same_values=True) for k in saved_h))
	else:
		r = False
	return r
# @used-by :func:`dfh_executor_metadata_equivalent()`
def _project_section(saved_sec: object, live_sec: object, *, project_keys: bool) -> bool:
	if not project_keys:
		r = saved_sec == live_sec
	elif isinstance(saved_sec, dict) and isinstance(live_sec, dict):
		r = saved_sec == {k: v for k, v in live_sec.items() if k in saved_sec}
	else:
		r = saved_sec == live_sec
	return r
# @used-by :func:`Df.Harness.lib.trace_review.dfh_verify_review_proof_core()`
# @used-by :func:`dfh_proof_semantically_equivalent()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_codex_roles_and_proof_metadata_tail()`
def dfh_executor_metadata_equivalent(saved: object, live: object, *, allow_legacy_generation_model: bool=False) -> bool:
	if saved == live:
		r = True
	elif not isinstance(saved, dict) or (not isinstance(live, dict)):
		r = False
	else:
		legacy = allow_legacy_generation_model and ('generation_model' not in (saved.get('observed') or {}))
		stable_keys = (set(saved) | set(live)) - VOLATILE_META_KEYS
		stable_ok = all((saved.get(k) == live.get(k) for k in stable_keys))
		obs_ok = _project_section(saved.get('observed'), live.get('observed'), project_keys=legacy)
		req_ok = _project_section(saved.get('requested'), live.get('requested'), project_keys=legacy)
		src_ok = saved.get('metadata_sources') == live.get('metadata_sources') or _dict_prefix_match(saved.get('metadata_sources'), live.get('metadata_sources'), same_values=False)
		hist_ok = _history_equivalent(saved.get('observation_history'), live.get('observation_history'))
		r = stable_ok and obs_ok and req_ok and src_ok and hist_ok
	return r
# @used-by :func:`dfh_reuse_equivalent_proof()`
# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_platform_subsystem_classes()`
def dfh_proof_semantically_equivalent(saved: object, live: object) -> bool:
	r = False
	if isinstance(saved, dict) and isinstance(live, dict):
		saved_rest = {k: v for k, v in saved.items() if 'executor_metadata' != k}
		live_rest = {k: v for k, v in live.items() if 'executor_metadata' != k}
		r = saved_rest == live_rest and dfh_executor_metadata_equivalent(saved.get('executor_metadata'), live.get('executor_metadata'), allow_legacy_generation_model=True)
	return r
# @used-by :func:`Df.Harness.lib.trace_review.dfh_persist_review_proof()`
# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_trace_effects_review_and_clarifications()`
def dfh_reuse_equivalent_proof(target: Path, proof: dict) -> dict | None:
	r = None
	if target.is_file():
		try:
			existing = json.loads(target.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			existing = None
		if dfh_proof_semantically_equivalent(existing, proof):
			r = existing
	return r
