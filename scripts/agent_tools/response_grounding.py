# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from __future__ import annotations
from pathlib import Path
from Df.Harness.Grounding.EvidenceBundleIngestor import EvidenceBundleIngestor
from Df.Harness.Grounding.ResponseAuditor import ResponseAuditor
ResponseEvidenceAuditor = ResponseAuditor
# @used-by unused
def _discourse_topic_key(url: str):
	return EvidenceBundleIngestor.discourse_topic_key(url)
# @used-by unused
def _is_descriptive_title_label(label: str, href: str) -> bool:
	return ResponseAuditor.is_descriptive_title_label(label, href)
# @used-by unused
def _norm_url(url: str) -> str:
	return EvidenceBundleIngestor.norm_url(url)
# @used-by unused
def _titles_compatible(claimed: str, observed: str) -> bool:
	return ResponseAuditor.titles_compatible(claimed, observed)
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__check_source_grounding()`
# @used-by :meth:`test_analysis_workflow.MetricsTests.test_collect_http_positional_batch_extract_profile_and_14_url_evidence_query()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_provenance_tiers_and_tier2_rejection()`
def response_source_and_kb_issues(root: Path, response: str, requests: list[dict], *, touched_files=None, turn=None, native=None) -> list[str]:
	return ResponseAuditor(root, response, requests, touched_files=touched_files, turn=turn, native=native).validate()