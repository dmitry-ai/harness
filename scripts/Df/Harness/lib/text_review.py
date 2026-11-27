# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
import json
import sys
from Df.Harness.Text.SourceReceiptReader import SourceReceiptReader
from Df.Harness.lib.text_workflow import dfh_text_folder
from agent_tools.review import REPORT_CONTRACT, ReviewReportValidator, is_nonempty_text
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
SCOPES = ('format', 'scope', 'evidence', 'relevance', 'kb_consistency', 'response')
TEXT_CHECKS = ('role_and_coverage', 'source_applicability', 'scope_alignment', 'goal_relevance', 'semantic_deduplication', 'numeric_provenance')
# @used-by :func:`dfh_text_review_issues()`
# @used-by :meth:`Df.Harness.Text.ReviewRecorder.ReviewRecorder.record()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_reviewer_approval_needs_a_receipt_bound_assessment_for_each_url()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_reviewer_can_collect_its_own_equal_bytes_without_invalidating_the_author()`
def dfh_source_reviews(root, data: dict, package: dict, candidate: str) -> dict:
	required = {SourceReceiptReader(root, candidate, ref).read()['url'] for ref in package.get('source_checks', [])}
	values = data.get('source_reviews', [])
	if not isinstance(values, list):
		raise ValueError('source_reviews must be an authored list')
	seen, inputs = (set(), {})
	for item in values:
		if not isinstance(item, dict) or item.get('url') not in required or item['url'] in seen or (not is_nonempty_text(item.get('assessment'))) or (item.get('outcome') not in ('supported', 'unsupported')):
			raise ValueError('Assess each exact source URL once with receipt, basis and an explicit outcome')
		observed = SourceReceiptReader(root, candidate, item['receipt']).read()
		if observed['url'] != item['url']:
			raise ValueError('Reviewer source receipt belongs to another URL')
		if 'approved' == data.get('result') and 'supported' != item['outcome']:
			raise ValueError('An unsupported cited source cannot receive publication approval')
		seen.add(item['url'])
		inputs.update(observed['inputs'])
	if 'approved' == data.get('result') and required != seen:
		raise ValueError('Approval needs a receipt-bound assessment of every external source')
	return inputs
# @used-by :meth:`Df.Harness.Text.ReviewPreparer.ReviewPreparer.prepare()`
# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
# @used-by :mod:`agent_tools.text_review`
def dfh_text_report_contract() -> dict:
	value = deepcopy(REPORT_CONTRACT)
	value['required_scope'] = list(SCOPES)
	value['claim_review_fields'].append('text_checks')
	value['text_checks'] = {key: 'Authored assessment with concrete evidence and limits.' for key in TEXT_CHECKS}
	value['source_reviews'] = {'required_when': 'The package has external source_checks', 'fields': ['url', 'receipt', 'assessment', 'outcome'], 'outcome': ['supported', 'unsupported'], 'instruction': 'Assess every cited external URL against a verified source receipt and its exact quote/anchor/edition; a reviewer may supply its own candidate-bound receipt.'}
	value['instruction'] = 'Review the exact request, baseline, diff and candidate. Check every substantive statement, including those labelled nonfactual. Test the actual claim, quantifier and scope; give a counterexample. Distinguish product documentation from this site, historical from current measurements, purpose from motive. Read saved primary bytes and fetch primary sources when necessary. Network access is allowed. Do not edit the document, KB, package or previous verdicts. Return one authored JSON report; no default verdict.'
	return value
# @used-by :meth:`Df.Harness.Text.ApprovalIntegrityChecker.ApprovalIntegrityChecker.__check_native_proof()`
# @used-by :meth:`Df.Harness.Text.ReviewAuthorizer.ReviewAuthorizer.__check_entry()`
# @used-by :meth:`Df.Harness.Text.ReviewRecorder.ReviewRecorder.record()`
def dfh_text_review_issues(data: dict, package: dict, candidate: str, *, root=None):
	reviewer = (lambda d, p: dfh_source_reviews(root, d, p, candidate)) if None is not root else None
	return ReviewReportValidator(package, candidate=candidate, text_checks=TEXT_CHECKS, source_reviewer=reviewer).validate(data)
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__gate_applied_receipt()`
# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.apply()`
def dfh_text_review_seam(name: str, default):
	mod = sys.modules.get('agent_tools.text_review')
	cand = getattr(mod, name, None) if None is not mod else None
	return cand if callable(cand) and True is not getattr(cand, '_df_default_review_facade', False) else default
# @used-by :meth:`Df.Harness.Text.ApprovalIntegrityChecker.ApprovalIntegrityChecker.check()`
# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__verify_target_artifacts()`
# @used-by :meth:`Df.Harness.Text.ReviewAuthorizer.ReviewAuthorizer.authorize()`
# @used-by :meth:`Df.Harness.Text.ReviewPackageReader.ReviewPackageReader.read()`
# @used-by :meth:`Df.Harness.Text.ReviewPreparer.ReviewPreparer.__build_payload()`
# @used-by :meth:`Df.Harness.Text.ReviewRecorder.ReviewRecorder.record()`
def dfh_text_review_state(root) -> dict:
	path = dfh_text_folder(root) / 'reviews.json'
	value = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema_version': 1, 'reviews': []}
	if 1 != value.get('schema_version') or not isinstance(value.get('reviews'), list):
		raise ValueError('Invalid text review history; preserve it for recovery')
	return value
