# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Research.BatchCollector import BatchCollector
from Df.Harness.Research.BrowserCollector import BrowserCollector
from Df.Harness.Research.ChallengeClassifier import ChallengeClassifier
from Df.Harness.Research.Collector import Collector
from Df.Harness.Research.DomCapturer import DomCapturer
from Df.Harness.Research.EvidenceQuerier import EvidenceQuerier
from Df.Harness.Research.Extractor import Extractor
from Df.Harness.Research.HtmlData import HtmlData as HTMLData
from Df.Harness.Research.HttpCollector import HttpCollector
from Df.Harness.Research.JsonCollectionSummarizer import JsonCollectionSummarizer
from Df.Harness.Research.MarkdownExtractor import MarkdownExtractor
from Df.Harness.Research.Response import Response
from Df.Harness.Research.SafeRedirects import SafeRedirects
from Df.Harness.Research.SiteSummarizer import SiteSummarizer
from Df.Harness.Research.SitemapExtractor import SitemapExtractor
from Df.Harness.lib.research import BROWSER_MODES, HTTP_DEFAULT_ACCEPT, MAX_BYTES, METRIC_KEYS, PROFILES, VOID_ELEMENTS, dfh_bounded_metrics, dfh_classify_network_error, dfh_compact_extraction_for_disk, dfh_extract_github_blob_lines, dfh_extractor_version, dfh_fingerprint, dfh_inside, dfh_json_data, dfh_metric_counts, dfh_observation_capabilities, dfh_observed_use, dfh_request_context, dfh_request_key, dfh_select_dom_tab
# @used-by :mod:`agent_tools.research`
def _extract_sitemap(text):
	return SitemapExtractor(text).extract()
# @used-by :mod:`agent_tools.research`
def _fingerprint(value):
	return dfh_fingerprint(value)
# @used-by :mod:`agent_tools.research`
def _summarize_json_collections(value):
	return JsonCollectionSummarizer(value).summarize()
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.project_metrics()`
# @used-by :mod:`agent_tools.research`
def bounded_metrics(value):
	return dfh_bounded_metrics(value)
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_capture_dom()`
# @used-by :meth:`test_experiments.ExperimentTests.test_dom_is_fresh_and_never_proves_click()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_exact_dom_tab_is_read_without_inventing_http_status()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_dom_collector_does_not_issue_content_proof_if_browser_identity_changes()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_dom_collector_exact_url_and_guard_project_cannot_be_substituted()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_dom_collector_requires_verified_profile_before_native_dom_evaluation()`
# @used-by :mod:`agent_tools.research`
def capture_dom(root, url, tab_id, *, session_id=None, refresh_reason=None, context=None, config=None, guard=None):
	return DomCapturer(root, url, tab_id, session_id=session_id, refresh_reason=refresh_reason, context=context, config=config, guard=guard).capture()
# @used-by :meth:`Df.Harness.Analysis.HtmlQuoteVerifier.HtmlQuoteVerifier.verify()`
# @used-by :meth:`Df.Harness.Analysis.ObservationBundleLoader.ObservationBundleLoader.__extract_html()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m3_passive_cloudflare_jsd_script_is_admitted_while_real_interstitial_is_blocked()`
# @used-by :mod:`agent_tools.research`
def classify_html_challenge(raw_html: str, *, parsed: dict | None=None, status: int | None=None) -> bool:
	return ChallengeClassifier(raw_html, parsed=parsed, status=status).is_challenge()
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e3_network_error_classification_and_unverified_dns_claim_rejection()`
# @used-by :mod:`agent_tools.research`
def classify_network_error(exc):
	return dfh_classify_network_error(exc)
# @used-by :func:`test_evidence_contract.v3_analysis()`
# @used-by :func:`test_runtime_cache_and_evidence_fastpath_m9._build_html_obs_project()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_anchored_quote_from_another_section_is_rejected()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_existing_heading_or_ancestor_anchor_is_required()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_no_anchor_exception_uses_an_observed_specific_section()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_void_elements_compact_extracted_disk_json_and_max_bytes_guard()`
# @used-by :meth:`test_analysis_workflow.ResearchTests.test_changed_cached_body_is_not_silently_used()`
# @used-by :meth:`test_analysis_workflow.ResearchTests.test_concurrent_and_repeated_fetches_reuse_one_saved_response()`
# @used-by :meth:`test_analysis_workflow.ResearchTests.test_conditions_scope_and_explicit_refresh_make_separate_measurements()`
# @used-by :meth:`test_analysis_workflow.ResearchTests.test_real_get_and_cross_origin_redirect_strip_authentication()`
# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_review_lifecycle_and_validators_extra()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.signed_price_analysis()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_currency_cannot_be_borrowed_from_another_quantity()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e1_and_e2_sitemap_alone_and_unobserved_sample_urls_are_rejected()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e3_network_error_classification_and_unverified_dns_claim_rejection()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e4_site_wide_schema_absence_requires_multi_page_or_product_template_sample()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e5_and_e6_html_sitemap_and_site_summary_diagnostics()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e8_relational_comparison_and_modification_require_two_distinct_operands_with_verified_hashes()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_html_markup_cannot_hide_a_sign_between_spans()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_json_amount_currency_pair_is_an_exact_quantity_locator()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_m1_and_m2_html_wrapper_anchors_and_markdown_explicit_heading_ids_in_evidence_contract()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_documentation_requires_verified_anchor_or_genuine_no_anchor_section()`
# @used-by :meth:`test_experiments.ExperimentTests.observe()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_remote_json_pointer_checks_only_the_target_field()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_review_package_rejects_ungrounded_numbers_in_response_excerpt_and_reviewer_report()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.spec()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_valid_dom_capture_identity_can_resolve_the_http_channel_failure()`
# @used-by :mod:`agent_tools.research`
def collect(root, url, *, headers=None, scope='public', max_age=86400, refresh_reason=None, timeout=15, fetcher=None, observation_kind='http', context=None, extra_meta=None):
	return Collector(root, url, headers=headers, scope=scope, max_age=max_age, refresh_reason=refresh_reason, timeout=timeout, fetcher=fetcher, observation_kind=observation_kind, context=context, extra_meta=extra_meta).collect()
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_collect_browser()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_collect_browser_never_hijacks_open_user_tab_without_tab_id_and_uses_hidden_target()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m1_live_headless_shell_public_isolation_and_h_chs_6_static_skip()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m2a_extension_manifest_key_and_multi_profile_tab_broker_isolation()`
# @used-by :mod:`agent_tools.research`
def collect_browser(root, url, *, profile='html', scope='public', session_id=None, refresh_reason=None, max_age=86400, cdp_port=None, timeout=15, context=None, config=None, http_get=None, cdp_call=None, cdp_fetcher=None, headless_shell=None):
	return BrowserCollector(root, url, profile=profile, scope=scope, session_id=session_id, refresh_reason=refresh_reason, max_age=max_age, cdp_port=cdp_port, timeout=timeout, context=context, config=config, http_get=http_get, cdp_call=cdp_call, cdp_fetcher=cdp_fetcher, headless_shell=headless_shell).collect()
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_collect_browser()`
# @used-by :mod:`agent_tools.research`
def collect_browser_batch(root, urls, *, profile='html', scope='public', session_id=None, refresh_reason=None, max_age=86400, cdp_port=None, timeout=15, context=None, config=None, http_get=None, cdp_call=None, cdp_fetcher=None):
	return BatchCollector.collect_browser_batch(root, urls, profile=profile, scope=scope, session_id=session_id, refresh_reason=refresh_reason, max_age=max_age, cdp_port=cdp_port, timeout=timeout, context=context, config=config, http_get=http_get, cdp_call=cdp_call, cdp_fetcher=cdp_fetcher)
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_collect_http()`
# @used-by :meth:`test_analysis_workflow.MetricsTests.test_collect_http_positional_batch_extract_profile_and_14_url_evidence_query()`
# @used-by :meth:`test_df_analysis.DfAnalysisGatesTests.test_documentation_link_requires_anchor_when_observation_has_anchors()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_collect_http_auto_fallback_to_browser_on_reddit_js_challenge_shell()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m1_live_headless_shell_public_isolation_and_h_chs_6_static_skip()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_adhoc_http_fetch_in_shell_blocks_and_collect_http_persists()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_universal_source_kb_check_blocks_reddit_js_shell_unverified_short_links_missing_anchors_and_fake_quotes()`
# @used-by :mod:`agent_tools.research`
def collect_http(root, url, *, profile='html', scope='public', session_id=None, refresh_reason=None, max_age=86400, headers=None, context=None, fetcher=None, browser='auto', cdp_port=None, cdp_fetcher=None, http_get=None, cdp_call=None, headless_shell=None):
	return HttpCollector(root, url, profile=profile, scope=scope, session_id=session_id, refresh_reason=refresh_reason, max_age=max_age, headers=headers, context=context, fetcher=fetcher, browser=browser, cdp_port=cdp_port, cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call, headless_shell=headless_shell).collect()
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_collect_http()`
# @used-by :mod:`agent_tools.research`
def collect_http_batch(root, urls, *, profile='auto', scope='public', session_id=None, refresh_reason=None, max_age=86400, headers=None, context=None, fetcher=None, browser='auto', cdp_port=None, cdp_fetcher=None, http_get=None, cdp_call=None):
	return BatchCollector.collect_http_batch(root, urls, profile=profile, scope=scope, session_id=session_id, refresh_reason=refresh_reason, max_age=max_age, headers=headers, context=context, fetcher=fetcher, browser=browser, cdp_port=cdp_port, cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call)
# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_execute_collect()`
# @used-by :meth:`test_analysis_workflow.ResearchTests.test_http_error_observation_is_completed_and_preserved()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_failed_extraction_keeps_saved_observation_and_reuses_it()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m1_live_headless_shell_public_isolation_and_h_chs_6_static_skip()`
# @used-by :mod:`agent_tools.research`
def collect_plan(root, plan, *, fetcher=None, browser='auto', cdp_port=None, session_id=None, cdp_fetcher=None, http_get=None, cdp_call=None):
	return BatchCollector(root, plan, fetcher=fetcher, browser=browser, cdp_port=cdp_port, session_id=session_id, cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call).run()
# @used-by :mod:`agent_tools.research`
def compact_extraction_for_disk(data):
	return dfh_compact_extraction_for_disk(data)
# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_execute_collect()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e5_and_e6_html_sitemap_and_site_summary_diagnostics()`
# @used-by :mod:`agent_tools.research`
def compute_site_summary(root, results):
	return SiteSummarizer(root, results).summarize()
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_evidence_query()`
# @used-by :meth:`test_analysis_workflow.MetricsTests.test_collect_http_positional_batch_extract_profile_and_14_url_evidence_query()`
# @used-by :mod:`agent_tools.research`
def evidence_query(root, *, urls=None, include_anchors: bool=False, grep_pattern: str | None=None, context_lines: int=2, max_matches: int=20) -> dict:
	return EvidenceQuerier(root, urls=urls, include_anchors=include_anchors, grep_pattern=grep_pattern, context_lines=context_lines, max_matches=max_matches).query()
# @used-by :func:`agent_tools.evidence.saved_source()`
# @used-by :func:`agent_tools.evidence.verify_saved_quote()`
# @used-by :func:`agent_tools.evidence_loader.load_observation_content()`
# @used-by :func:`agent_tools.evidence_loader.probe_observation_status()`
# @used-by :meth:`Df.Harness.Analysis.ObservationHtmlResolver.ObservationHtmlResolver.resolve()`
# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.__load_text_or_structured()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_html_links_json_summary_non_destructive_collect_and_scratch_cleanliness()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_void_elements_compact_extracted_disk_json_and_max_bytes_guard()`
# @used-by :meth:`test_analysis_workflow.ResearchTests.test_tracking_and_shopify_extraction_preserve_provenance_limits()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_tracking_extraction_handles_quoted_keys_and_declares_unparsed_js()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_evidence_loader_reuses_saved_extracted_html_and_caches_fragment_parse()`
# @used-by :mod:`agent_tools.evidence_loader`
# @used-by :mod:`agent_tools.research`
def extract_bytes(body, content_type, profile, charset='utf-8', *, status=None):
	return Extractor(body, content_type, profile, charset, status=status).extract()
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_extract_file()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
# @used-by :mod:`agent_tools.research`
def extract_file(root, file, profile='document'):
	return Extractor.extract_file(root, file, profile=profile)
# @used-by :meth:`Df.Harness.Analysis.ObservationBundleLoader.ObservationBundleLoader.__extract_html()`
# @used-by :mod:`agent_tools.research`
def extract_github_blob_lines(raw_text: str) -> list[str]:
	return dfh_extract_github_blob_lines(raw_text)
# @used-by :meth:`Df.Harness.Analysis.ObservationBundleLoader.ObservationBundleLoader.__extract_markdown()`
# @used-by :mod:`agent_tools.research`
def extract_markdown(text: str) -> dict:
	return MarkdownExtractor(text).extract()
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_extract()`
# @used-by :func:`test_runtime_cache_and_evidence_fastpath_m9._build_html_obs_project()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_void_elements_compact_extracted_disk_json_and_max_bytes_guard()`
# @used-by :meth:`test_analysis_workflow.ResearchTests.test_concurrent_and_repeated_fetches_reuse_one_saved_response()`
# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_review_lifecycle_and_validators_extra()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e5_and_e6_html_sitemap_and_site_summary_diagnostics()`
# @used-by :mod:`agent_tools.research`
def extract_observation(root, reference, profile='html'):
	return Extractor.extract_observation(root, reference, profile=profile)
# @used-by :meth:`Df.Harness.Analysis.ObservationBundleLoader.ObservationBundleLoader.__scan_ext_files()`
# @used-by :meth:`Df.Harness.Analysis.ObservationHtmlResolver.ObservationHtmlResolver.__load_saved()`
# @used-by :meth:`Df.Harness.Analysis.ObservationHtmlResolver.ObservationHtmlResolver.resolve()`
# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
# @used-by :mod:`agent_tools.research`
def extractor_version():
	return dfh_extractor_version()
# @used-by :mod:`agent_tools.research`
def fetch(url, headers, timeout):
	return Collector.fetch(url, headers, timeout)
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_save_analysis()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops._resolve_project_input()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_execute_collect()`
# @used-by :func:`Df.Harness.lib.codex_metadata._match_review_receipt()`
# @used-by :func:`agent_tools.evidence.source_reference()`
# @used-by :func:`agent_tools.review._approved_digests()`
# @used-by :func:`agent_tools.review.approval_current()`
# @used-by :func:`agent_tools.review.authenticate_report()`
# @used-by :func:`agent_tools.review.authorize()`
# @used-by :func:`agent_tools.review.disposition()`
# @used-by :func:`agent_tools.review.findings_closed()`
# @used-by :func:`agent_tools.review.has_unhandled_verdicts()`
# @used-by :func:`agent_tools.review.input_receipt()`
# @used-by :func:`agent_tools.review.prepare_verdict_record()`
# @used-by :func:`agent_tools.review.read_package()`
# @used-by :func:`agent_tools.review.read_package_envelope()`
# @used-by :func:`agent_tools.review.record()`
# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__check_intake()`
# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__load_state()`
# @used-by :meth:`Df.Harness.Analysis.Saver.Saver.save()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__collect_modules()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__load_verified_package()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.read_review_input()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.__build_item()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.collector_artifact()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactVerifier.ArtifactVerifier.__verify_artifact()`
# @used-by :meth:`Df.Harness.Experiment.PlanLoader.PlanLoader.load_plan()`
# @used-by :meth:`Df.Harness.Experiment.PreregistrationAuditor.PreregistrationAuditor.__load_plan()`
# @used-by :meth:`Df.Harness.Experiment.ResultValidator.ResultValidator.__check_run()`
# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.__load_raw()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__collect_project_executors()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__collect_project_reviews()`
# @used-by :meth:`Df.Harness.Review.AddressedReviewResolver.AddressedReviewResolver.__resolve_one()`
# @used-by :meth:`Df.Harness.Review.ApprovalChecker.ApprovalChecker.__init__()`
# @used-by :meth:`Df.Harness.Review.ApprovedDigestCollector.ApprovedDigestCollector.__collect_groups()`
# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.__init__()`
# @used-by :meth:`Df.Harness.Review.FindingsClosureChecker.FindingsClosureChecker.closed()`
# @used-by :meth:`Df.Harness.Review.InputReceiptBuilder.InputReceiptBuilder.__init__()`
# @used-by :meth:`Df.Harness.Review.NativeProofVerifier.NativeProofVerifier.verify()`
# @used-by :meth:`Df.Harness.Review.PackageEnvelopeReader.PackageEnvelopeReader.__init__()`
# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__init__()`
# @used-by :meth:`Df.Harness.Review.ReportAuthenticator.ReportAuthenticator.__init__()`
# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__init__()`
# @used-by :meth:`Df.Harness.Review.SignificantFindingScanner.SignificantFindingScanner.has_significant()`
# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__init__()`
# @used-by :meth:`Df.Harness.Workflow.HashCollector.HashCollector.collect()`
# @used-by :meth:`Df.Harness.Workflow.KbAuditor.KbAuditor.issues()`
# @used-by :meth:`Df.Harness.Workflow.ProgressPublisher.ProgressPublisher.__question_lines()`
# @used-by :meth:`Df.Harness.Workflow.QuestionAdder.QuestionAdder.__validate_outputs()`
# @used-by :meth:`Df.Harness.Workflow.QuestionFinisher.QuestionFinisher.__apply()`
# @used-by :meth:`Df.Harness.Workflow.ReceiptVerifier.ReceiptVerifier.__resolve_artifact()`
# @used-by :meth:`Df.Harness.Workflow.StatusSnapshotBuilder.StatusSnapshotBuilder.__proposals()`
# @used-by :meth:`Df.Harness.Workflow.WorkflowResumer.WorkflowResumer.__apply()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :mod:`agent_tools.research`
def inside(root, relative):
	return dfh_inside(root, relative)
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops._commit_pruned_folders()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops._restore_pending_folders()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops._save_pending_snapshot()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_finish_pending()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_execute_collect()`
# @used-by :func:`Df.Harness.lib.trace_review.dfh_make_tool_trace_event()`
# @used-by :func:`Df.Harness.lib.trace_review.dfh_persist_review_proof()`
# @used-by :func:`test_df_harness_s11_wave2a_review._sample_package()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__persist_review_index()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__register_package_index()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__subject_digest()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.prepare_package()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.result_bytes()`
# @used-by :meth:`Df.Harness.Experiment.PlanPreparer.PlanPreparer.prepare_plan()`
# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__write_run()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__append_executor_receipt()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__save_executor_metadata()`
# @used-by :meth:`Df.Harness.Platform.Codex.ExecutorMetadataReader.ExecutorMetadataReader.run()`
# @used-by :meth:`Df.Harness.Review.ClaimMerkleHasher.ClaimMerkleHasher.compute_hash()`
# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.__resolve_claim()`
# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.update()`
# @used-by :meth:`Df.Harness.Review.PackageEnvelopeReader.PackageEnvelopeReader.subject_digest()`
# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.prepare()`
# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__write_artifacts()`
# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
# @used-by :meth:`test_df_harness_s11_wave2a_facade_exports.DfHarnessS11Wave2aFacadeExportsTests.test_review_facade_reexports_json_data()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests._native_record()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_review_contract.ReviewContractTests.native_record()`
# @used-by :meth:`test_review_contract.ReviewContractTests.self_record()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_audit_must_explain_falsifiability_and_compare_raw_criteria()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_cli_exact_candidate_and_report_support_stdin_without_implicit_risk()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_cli_preregistered_unavailable_experiment_finishes_question_with_explicit_gap()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_handwritten_empty_manifest_package_cannot_pass_record_review()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_handwritten_routine_package_cannot_bypass_computed_risk()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_merkle_cached_single_reviewer_quorum_recognizes_approved_digests_and_storage_receipts()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_official_distributor_is_not_established_by_contains_lunos_proxy()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_per_claim_audit_is_required_and_qualified_gap_can_pass()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_package_handler_registry_dispatches_custom_kind()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_quorum_evaluator_selects_authorized_group_and_checks_approval_current()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_valid_dom_capture_identity_can_resolve_the_http_channel_failure()`
# @used-by :meth:`test_text_integration.TextReviewTests.test_parent_cannot_authorize_its_own_text()`
# @used-by :mod:`agent_tools.research`
def json_data(value):
	return dfh_json_data(value)
# @used-by :func:`test_runtime_cache_and_evidence_fastpath_m9._build_html_obs_project()`
# @used-by :meth:`Df.Harness.Analysis.Claim.PrimaryCapabilities.PrimaryCapabilities.resolve()`
# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_counter_source()`
# @used-by :meth:`Df.Harness.Analysis.ObservationResolver.ObservationResolver.__lookup_index()`
# @used-by :meth:`Df.Harness.Analysis.ObservationResolver.ObservationResolver.resolve()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.collector_artifact()`
# @used-by :meth:`test_analysis_workflow.ResearchTests.test_changed_cached_body_is_not_silently_used()`
# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_review_lifecycle_and_validators_extra()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
# @used-by :mod:`agent_tools.research`
def load_observation(root, reference):
	return Collector.load_observation(root, reference)
# @used-by :mod:`agent_tools.research`
def metric_counts(events):
	return dfh_metric_counts(events)
# @used-by :meth:`Df.Harness.Analysis.Claim.PrimaryCapabilities.PrimaryCapabilities.resolve()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.collector_artifact()`
# @used-by :meth:`test_experiments.ExperimentTests.test_dom_is_fresh_and_never_proves_click()`
# @used-by :meth:`test_experiments.ExperimentTests.test_observation_kind_alone_never_grants_extra_capabilities()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_dom_collector_does_not_issue_content_proof_if_browser_identity_changes()`
# @used-by :mod:`agent_tools.research`
def observation_capabilities(meta):
	return dfh_observation_capabilities(meta)
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_collector_retains_totals_and_only_32_recent_diagnostics()`
# @used-by :mod:`agent_tools.research`
def observed_use(root, result):
	return dfh_observed_use(root, result)
# @used-by :meth:`Df.Harness.Experiment.ConditionAuditor.ConditionAuditor.issues()`
# @used-by :mod:`agent_tools.research`
def request_context(value=None):
	return dfh_request_context(value)
# @used-by :meth:`test_experiments.ExperimentTests.test_cache_distinguishes_network_country_language_and_session_state()`
# @used-by :mod:`agent_tools.research`
def request_key(url, headers, scope, context=None):
	return dfh_request_key(url, headers, scope, context)
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_exact_dom_tab_is_read_without_inventing_http_status()`
# @used-by :mod:`agent_tools.research`
def select_dom_tab(tabs, url, tab_id):
	return dfh_select_dom_tab(tabs, url, tab_id)
_extract_github_blob_lines = extract_github_blob_lines
setattr(extractor_version, '_df_default_research_facade', True)
setattr(fetch, '_df_default_research_facade', True)
__all__ = ['BROWSER_MODES', 'HTMLData', 'HTTP_DEFAULT_ACCEPT', 'MAX_BYTES', 'METRIC_KEYS', 'PROFILES', 'Response', 'SafeRedirects', 'VOID_ELEMENTS', '_extract_github_blob_lines', '_extract_sitemap', '_fingerprint', '_summarize_json_collections', 'bounded_metrics', 'capture_dom', 'classify_html_challenge', 'classify_network_error', 'collect', 'collect_browser', 'collect_browser_batch', 'collect_http', 'collect_http_batch', 'collect_plan', 'compact_extraction_for_disk', 'compute_site_summary', 'evidence_query', 'extract_bytes', 'extract_file', 'extract_github_blob_lines', 'extract_markdown', 'extract_observation', 'extractor_version', 'fetch', 'inside', 'json_data', 'load_observation', 'metric_counts', 'observation_capabilities', 'observed_use', 'request_context', 'request_key', 'select_dom_tab']