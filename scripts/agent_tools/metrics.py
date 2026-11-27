# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from Df.Harness.Meta.MetricsSummarizer import MetricsSummarizer
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by unused
def _resolve_platform_and_backend(platform, backend, instance, conversation_id=None):
	return _resolve_target(platform, backend, instance, conversation_id=conversation_id)[:2]
# @used-by :func:`_resolve_platform_and_backend()`
def _resolve_target(platform, backend, instance, conversation_id=None):
	return MetricsSummarizer.resolve_target(platform, backend, instance, conversation_id=conversation_id)
# @used-by :func:`agent_tools.cli_domains._op_native_executor_metadata()`
# @used-by :func:`record_executor_metadata()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_cli_prepare_input_record_needs_changes_and_check_text_roundtrip()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_instance_flag_and_codex_auto_lookup_for_handoff_and_audit()`
def native_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, platform=None, backend=None, instance=None, write=False):
	return MetricsSummarizer.native_executor_metadata(root, conversation_id, role=role, parent_id=parent_id, platform=platform, backend=backend, instance=instance, write=write)
# @used-by :meth:`Df.Harness.Workflow.RequestAdopter.RequestAdopter.adopt()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_antigravity_verify_native_proof_tool_trace_and_custom_system_paths()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_instance_flag_and_codex_auto_lookup_for_handoff_and_audit()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_native_requests_preserve_exact_bytes_and_current_job_scope()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_unknown_native_format_does_not_reconstruct_request()`
def native_requests(root, conversation_id, *, backend=None, platform=None, instance=None):
	return MetricsSummarizer.native_requests(root, conversation_id, backend=backend, platform=platform, instance=instance)
# @used-by :func:`agent_tools.cli_domains._op_native_review_proof()`
# @used-by :func:`test_finalized_project_contract._complete_review_and_finalize()`
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.authenticate_report()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_af_or_terminal_quota_error_is_not_an_independent_completed_aa_review()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_native_review_rejects_prompt_bias_and_reviewer_isolation_violations()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_parent_model_selection_allowed_and_observed_mismatch_rejected()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_significant_risk_cannot_finish_with_one_independent_aa()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_native_review_proof_and_verify_support_arch_role()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_native_windows_extended_path_keeps_the_profile_boundary()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_parent_can_select_another_model_and_effort_with_native_proof()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_review_provenance_checks_parent_completion_model_and_assignment()`
def native_review_proof(root, parent_id, reviewer_id, *, backend=None, write=True, platform=None, instance=None, wait_timeout=0.0, role='AA'):
	return MetricsSummarizer.native_review_proof(root, parent_id, reviewer_id, backend=backend, write=write, platform=platform, instance=instance, wait_timeout=wait_timeout, role=role)
# @used-by :meth:`Df.Harness.Experiment.ArtifactIngestor.ArtifactIngestor.__ingest_trace()`
# @used-by :meth:`Df.Harness.Experiment.ArtifactVerifier.ArtifactVerifier.__verify_trace()`
# @used-by :meth:`test_experiments.ExperimentTests.test_actual_namespaced_cua_read_is_recognized_but_text_header_does_not_prove_identity()`
# @used-by :meth:`test_experiments.ExperimentTests.test_supplied_native_events_are_rejected()`
def native_tool_trace(root, request):
	return MetricsSummarizer.native_tool_trace(root, request)
# @used-by :func:`agent_tools.cli_domains._op_metrics()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_failed_extraction_keeps_saved_observation_and_reuses_it()`
def project_metrics(root):
	return MetricsSummarizer.project_metrics(root)
# @used-by :func:`agent_tools.cli_domains._op_native_executor_metadata()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_immutable_executor_snapshots_cover_all_roles_and_can_be_reused()`
def record_executor_metadata(root, conversation_id, *, role='primary', parent_id=None, platform=None, backend=None, instance=None):
	return native_executor_metadata(root, conversation_id, role=role, parent_id=parent_id, platform=platform, backend=backend, instance=instance, write=True)
# @used-by :func:`agent_tools.cli_domains._op_metrics()`
# @used-by :meth:`test_analysis_workflow.MetricsTests.test_unknown_tokens_stay_unknown_and_duplicate_exports_are_not_summed()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_token_metrics_use_response_usage_and_do_not_count_summaries()`
def summarize(paths, bindings=None):
	return MetricsSummarizer(paths, bindings).summarize()
# @used-by :func:`agent_tools.cli_domains._op_metrics()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cross_instance_handoff_and_audit_resolve_antigravity_and_disabled_codex_traces()`
def summarize_instance(conversation_id, *, instance=None, platform=None, bindings=None):
	return MetricsSummarizer.summarize_instance(conversation_id, instance=instance, platform=platform, bindings=bindings)
# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.authenticate_report()`
# @used-by :meth:`Df.Harness.Review.NativeProofVerifier.NativeProofVerifier.verify()`
# @used-by :meth:`Df.Harness.Review.ReportAuthenticator.ReportAuthenticator.__auth_independent()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_parent_can_select_another_model_and_effort_with_native_proof()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_review_provenance_checks_parent_completion_model_and_assignment()`
def verify_native_proof(root, native, package=None):
	return MetricsSummarizer.verify_native_proof(root, native, package=package)
# @used-by unused
def wire_fields(data):
	return MetricsSummarizer.wire_fields(data)
