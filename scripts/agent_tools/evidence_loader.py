# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Analysis.CardValidationLoader import CardValidationLoader
from Df.Harness.Analysis.ObservationBundleLoader import ObservationBundleLoader
from Df.Harness.Analysis.ObservationContentLoader import ObservationContentLoader
from Df.Harness.Analysis.ObservationHtmlResolver import _OBS_HTML_CACHE
from Df.Harness.Analysis.ObservationProber import ObservationProber
from Df.Harness.Analysis.ObservationResolver import ObservationResolver
from .research import extract_bytes
# @used-by :func:`agent_tools.runtime_cache.clear_runtime_cache()`
# @used-by :mod:`agent_tools.evidence_loader`
def clear_observation_cache() -> None:
	_OBS_HTML_CACHE.clear()
# @used-by :mod:`agent_tools.evidence_loader`
def is_valid_observation_status(meta: dict) -> bool:
	return (not meta.get('error')) and ('dom' == meta.get('kind') or 200 <= (meta.get('status') or 0) < 300)
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor._analysis_card_issues()`
# @used-by :mod:`agent_tools.evidence_loader`
def load_analysis_card_validation(root, path: Path, prevalidated, *, analysis_issues_fn, evidence_issues_fn) -> tuple[dict | None, list, list]:
	return CardValidationLoader(root, path, prevalidated, analysis_issues_fn=analysis_issues_fn, evidence_issues_fn=evidence_issues_fn).load()
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._ingest_observation_bundle()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_evidence_loader_full_probe_and_bundle_modes()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_evidence_loader_rejects_empty_shell_bundle()`
# @used-by :mod:`agent_tools.evidence_loader`
def load_observation_bundle(jfile: Path, data: dict, *, max_bytes: int) -> dict:
	return ObservationBundleLoader(jfile, data, max_bytes=max_bytes).load()
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_evidence_loader_full_probe_and_bundle_modes()`
# @used-by :mod:`agent_tools.evidence_loader`
def load_observation_content(root, observation_ref: str, meta: dict, *, fragment: str='', need_sections: bool=True) -> dict:
	return ObservationContentLoader(root, observation_ref, meta, fragment=fragment, need_sections=need_sections, extract_fn=extract_bytes).load()
# @used-by :func:`agent_tools.text_sources.probe_links()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_evidence_loader_full_probe_and_bundle_modes()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_evidence_loader_reuses_saved_extracted_html_and_caches_fragment_parse()`
# @used-by :mod:`agent_tools.evidence_loader`
def probe_observation_status(root, meta: dict, base_url: str, fragment: str='') -> str:
	return ObservationProber(root, meta, base_url, fragment, extract_fn=extract_bytes).probe()
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_evidence_loader_full_probe_and_bundle_modes()`
# @used-by :mod:`agent_tools.evidence_loader`
def resolve_http_observation(root, base_url: str, observation: str | None=None) -> tuple[str, dict]:
	return ObservationResolver(root, base_url, observation).resolve()
__all__ = ['clear_observation_cache', 'extract_bytes', 'is_valid_observation_status', 'load_analysis_card_validation', 'load_observation_bundle', 'load_observation_content', 'probe_observation_status', 'resolve_http_observation']