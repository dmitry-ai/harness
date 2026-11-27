# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
import json
import sys
from urllib.parse import urldefrag
from Df.Harness.Research.Collector import Collector
from Df.Harness.Research.LinkAuditor import LinkAuditor
from Df.Harness.Research.NetworkLinkChecker import NetworkLinkChecker
from Df.Harness.Text.Finding import Finding
from Df.Harness.lib.research import dfh_json_data, dfh_readable_reference
from Df.Harness.lib.text_claims import dfh_claim_subset, dfh_evidence_inputs, dfh_registry_path, dfh_text_digest
from Df.Harness.lib.text_core import dfh_scan
from Df.Harness.lib.text_workflow import dfh_text_folder
from agent_tools.claims import contract_issues, evidence_contract_issues
from agent_tools.storage import locked, replace_bytes
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
SOURCE_MAX_AGE = 86400
# @used-by :func:`dfh_source_attempt()`
def _write_attempt_if_newer(root, candidate: str, observation, reference, previous, index, dt) -> None:
	meta = Collector.load_observation(root, observation)
	when = dt.fromisoformat(meta['observed_at'])
	if None is when.tzinfo or when > dt.now(timezone.utc):
		raise ValueError('A source attempt needs its nonfuture timezone-aware observation time')
	value = {'observed_at': meta['observed_at'], 'observation': observation, 'reference': reference, 'candidate_sha256': dfh_text_digest(candidate.encode('utf-8'))}
	if None is previous or dt.fromisoformat(value['observed_at']) >= dt.fromisoformat(previous['observed_at']):
		replace_bytes(index, dfh_json_data(value))
# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
def dfh_check_claim_sources(root, identifiers, *, reference=None) -> dict:
	path = dfh_registry_path(root, reference)
	selected = dfh_claim_subset(json.loads(path.read_text(encoding='utf-8-sig')), identifiers)
	issues = contract_issues(selected)
	if not issues:
		issues.extend(evidence_contract_issues(root, selected))
	return {'valid': not issues, 'issues': issues, 'inputs': dfh_evidence_inputs(root, selected) if not issues else {}, 'coverage': 'Saved primary bytes, quotes, locators and declared method contracts; source applicability and entailment require authored review.'}
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_network_source_checks_distinguish_missing_anchor_and_skip_inline_code()`
def dfh_check_source_links(text: str, *, fetcher=None) -> list[Finding]:
	prose = '\n'.join((line.raw for line in dfh_scan(text) if 'prose' == line.kind))
	urls = list(dict.fromkeys((url.rstrip('.,;') for url in LinkAuditor.references(prose)[0] if url.startswith(('https://', 'http://')))))
	results = NetworkLinkChecker(urls, fetcher=fetcher).check() + NetworkLinkChecker(urls, anchors=True, fetcher=fetcher).check()
	allowed = {'http-ok', 'found-in-source'}
	return [Finding('error', 'SOURCE-UNVERIFIED', 1, f"{res['url']}: {res['status']}; save an authorized DOM/console observation if the HTML cannot establish the target") for res in results if res['status'] not in allowed]
# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.__check_freshness()`
# @used-by :meth:`Df.Harness.Text.SourceProber.SourceProber.probe()`
# @used-by :meth:`Df.Harness.Text.SourceReceiptStore.SourceReceiptStore.save()`
def dfh_source_attempt(root, candidate: str, url: str, observation, reference, *, read_only: bool=False):
	dt = dfh_source_datetime()
	norm_url = dfh_readable_reference(url)
	folder = dfh_text_folder(root) / 'sources'
	index = folder / (dfh_text_digest(norm_url.encode('utf-8')) + '-latest.json')
	with locked(folder / 'attempts.lock'):
		previous = json.loads(index.read_text(encoding='utf-8')) if index.exists() else None
		if previous:
			actual = Collector.load_observation(root, previous['observation'])
			if actual['observed_at'] != previous['observed_at'] or urldefrag(norm_url)[0] != dfh_readable_reference(actual['url']):
				raise ValueError('Latest source index differs from its primary observation')
		if not read_only:
			_write_attempt_if_newer(root, candidate, observation, reference, previous, index, dt)
	return previous
# @used-by :func:`dfh_source_attempt()`
# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.__check_freshness()`
def dfh_source_datetime():
	mod = sys.modules.get('agent_tools.text_sources')
	return getattr(mod, 'datetime', datetime) if None is not mod else datetime
# @used-by :meth:`Df.Harness.Text.SourceCheckValidator.SourceCheckValidator.validate()`
# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.__validate_spec()`
# @used-by :meth:`Df.Harness.Text.SourceProber.SourceProber.probe()`
# @used-by :meth:`Df.Harness.Text.SourceReceiptStore.SourceReceiptStore.save()`
# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_unicode_address_and_encoded_markdown_destination_share_one_identity()`
def dfh_source_urls(text: str) -> list[str]:
	prose = '\n'.join((line.raw for line in dfh_scan(text) if line.kind in ('prose', 'heading')))
	return list(dict.fromkeys((dfh_readable_reference(url) for url in LinkAuditor.references(prose)[0] if url.startswith(('http://', 'https://')))))
