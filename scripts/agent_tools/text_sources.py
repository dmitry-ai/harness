# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Text.SourceCheckValidator import SourceCheckValidator
from Df.Harness.Text.SourceEvaluator import SourceEvaluator
from Df.Harness.Text.SourceIntegrityChecker import SourceIntegrityChecker
from Df.Harness.Text.SourceProber import SourceProber
from Df.Harness.Text.SourceReceiptReader import SourceReceiptReader
from Df.Harness.Text.SourceReceiptStore import SourceReceiptStore
from Df.Harness.lib.text_sources import SOURCE_MAX_AGE, dfh_check_claim_sources as check_claim_sources, dfh_check_source_links as check_links, dfh_source_attempt as _attempt, dfh_source_urls as source_urls
# @used-by unused
def _evaluate(root, candidate, spec):
	return SourceEvaluator(root, candidate, spec).evaluate()
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_later_conflicting_probe_rejects_new_publication_but_preserves_history()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_a_later_failed_probe_cannot_be_overridden_by_minting_an_older_success()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_changing_candidate_does_not_erase_a_later_failure_of_the_same_url()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_later_failure_invalidates_apply_and_an_already_applied_gate()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_real_http_failure_and_redirect_are_saved_once_per_base_url()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_valid_dom_capture_identity_can_resolve_the_http_channel_failure()`
def probe_links(root, candidate, *, fetcher=None):
	return SourceProber(root, candidate, fetcher=fetcher).probe()
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_plain_authored_verified_objects_and_changed_candidates_are_rejected()`
def read_source_check(root, candidate, reference):
	return SourceReceiptReader(root, candidate, reference).read()
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.check_and_review()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.saved()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_full_native_review_fixture_requires_and_preserves_source_assessments()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
def save_source_check(root, candidate, spec):
	return SourceReceiptStore(root, candidate, spec).save()
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
def source_integrity(root, candidate, reference):
	return SourceIntegrityChecker(root, candidate, reference).check()
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_unicode_address_and_encoded_markdown_destination_share_one_identity()`
def validate_source_checks(root, candidate, records):
	return SourceCheckValidator(root, candidate, records).validate()
