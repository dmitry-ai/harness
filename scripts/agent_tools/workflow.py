# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Workflow.HashCollector import HashCollector
from Df.Harness.Workflow.HealthAuditor import HealthAuditor as ProjectHealthAuditor
from Df.Harness.Workflow.KbAuditor import KbAuditor
from Df.Harness.Workflow.QuestionRegistry import QuestionRegistry as ResearchQuestionRegistry
from Df.Harness.Workflow.RegistrationStatusChecker import RegistrationStatusChecker
from Df.Harness.Workflow.StageEngine import StageEngine as WorkflowStateEngine
from Df.Harness.Workflow.StageStatusEvaluator import STAGES
from .analysis import SECTIONS, analysis_issues, publish_owned
from .evidence import evidence_issues
# @used-by :mod:`agent_tools.workflow`
def _target_complete(target, item):
	return RegistrationStatusChecker.target_complete(target, item)
# @used-by :func:`agent_tools.cli_domains._op_question_add()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_question_has_one_owner_and_explicit_handoff()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_search_cycle_returns_gap_or_requires_a_new_method()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_new_question_invalidates_completed_research_and_dependent_analysis()`
# @used-by :mod:`agent_tools.workflow`
def add_question(root, ident, question, impact, done_when, inputs, outputs, *, requirements=None):
	return ResearchQuestionRegistry(root, update_fn=update).add(ident, question, impact, done_when, inputs, outputs, requirements=requirements)
# @used-by :func:`agent_tools.cli_domains._op_adopt_requests()`
# @used-by :func:`test_contract_invariants._run_parity_defect_case()`
# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_answer_check_and_prepare_reject_misaligned_pending_without_writing_journal()`
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.setUp()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.setUp()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_exact_user_text_job_scope_and_cross_platform_request_merge()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_adopt_and_unadopt_requests_lifecycle()`
# @used-by :mod:`agent_tools.workflow`
def adopt_requests(root, conversation_id, *, allow_finalized=False, backend=None, platform=None):
	return WorkflowStateEngine(root, update_fn=update).adopt_requests(conversation_id, allow_finalized=allow_finalized, backend=backend, platform=platform)
# @used-by :meth:`test_onboarding.AttachmentTests.test_docx_and_text_attachments_saved_in_source_and_both_kbs()`
# @used-by :mod:`agent_tools.workflow`
def attachment_issues(root):
	return ProjectHealthAuditor(root).attachment_issues()
# @used-by :func:`agent_tools.cli_domains._op_check_project()`
# @used-by :func:`agent_tools.review.authorize()`
# @used-by :func:`complete_stage()`
# @used-by :func:`test_project_rename._assert_renamed_journal_and_state()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_html_links_json_summary_non_destructive_collect_and_scratch_cleanliness()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_validate_step_strict_sequence_and_check_project_detect_gaps_and_orphans()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_check_project_allows_unidentified_low_confidence_multi_target_and_exempt()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_check_project_flags_domain_drift_on_folder_and_registration_mismatch()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_new_analysis_cannot_finish_with_an_unpublished_website_card()`
# @used-by :meth:`test_readable_links.ReadableProjectTests.test_project_check_covers_agent_kb_and_client_markdown_text_and_html()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_public_example_passes_structure_evidence_and_project_checks()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_review_package_pins_primary_evidence_and_unquoted_new_contradiction()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_e12_check_project_flags_unsynced_client_identity_in_kb_project_md()`
# @used-by :mod:`agent_tools.workflow`
def check_project(root, *, prevalidated_analysis=None):
	from . import project_drift
	return ProjectHealthAuditor(root, analysis_issues_fn=analysis_issues, evidence_issues_fn=evidence_issues, drift_fn=project_drift.domain_drift_issues).check_project(prevalidated_analysis=prevalidated_analysis)
# @used-by :func:`agent_tools.cli_domains._op_question_claim()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_question_has_one_owner_and_explicit_handoff()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_search_cycle_returns_gap_or_requires_a_new_method()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_new_question_invalidates_completed_research_and_dependent_analysis()`
# @used-by :mod:`agent_tools.workflow`
def claim_question(root, ident, owner):
	return ResearchQuestionRegistry(root, update_fn=update).claim(ident, owner)
# @used-by :func:`agent_tools.cli_domains._op_stage()`
# @used-by :func:`agent_tools.shadow_replay._execute_finalize_reply()`
# @used-by :func:`test_finalized_project_contract._complete_review_and_finalize()`
# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_changed_completed_stage_output_invalidates_dependencies()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_significant_risk_cannot_finish_with_one_independent_aa()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.test_blocked_report_records_journal_without_closing_workflow_or_allowing_finalize()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_new_question_invalidates_completed_research_and_dependent_analysis()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_finalize_rejects_changed_journal_answer_after_approved_stage_receipts()`
# @used-by :mod:`agent_tools.workflow`
def complete_stage(root, stage, inputs, outputs, *, note=None):
	from . import project_drift
	from .review import authorize
	return WorkflowStateEngine(root, update_fn=update, check_project_fn=check_project, authorize_fn=authorize, drift_fn=project_drift.domain_drift_issues).complete_stage(stage, inputs, outputs, note=note)
# @used-by :meth:`test_hook_unification.HookUnificationTests.test_doc4_scanner_supports_hook_and_workflow_modes()`
# @used-by :mod:`agent_tools.workflow`
def doc4_sentence_issues(text):
	return KbAuditor.doc4_sentence_issues(text)
# @used-by :mod:`agent_tools.workflow`
def evidence_paths(root):
	return HashCollector.evidence_paths(root)
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :mod:`agent_tools.workflow`
def file_hash(path):
	return HashCollector.file_hash(path)
# @used-by :func:`agent_tools.cli_domains._op_question_finish()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_question_has_one_owner_and_explicit_handoff()`
# @used-by :mod:`agent_tools.workflow`
def finish_question(root, ident, owner, outputs, gap=None, *, results=None):
	return ResearchQuestionRegistry(root, update_fn=update).finish(ident, owner, outputs, gap=gap, results=results)
# @used-by :func:`agent_tools.cli_domains._op_question_handoff()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_question_has_one_owner_and_explicit_handoff()`
# @used-by :mod:`agent_tools.workflow`
def handoff(root, ident, previous_owner, new_owner, reason):
	return ResearchQuestionRegistry(root, update_fn=update).handoff(ident, previous_owner, new_owner, reason)
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_overview_and_nested_kb_module_change_invalidates_review_receipt()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_answer_change_and_new_request_need_new_review_even_without_kb_change()`
# @used-by :mod:`agent_tools.workflow`
def hashes(root, paths):
	return HashCollector(root, paths).collect()
# @used-by :mod:`agent_tools.workflow`
def kb_issues(root):
	return ProjectHealthAuditor(root).kb_issues()
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.test_blocked_report_records_journal_without_closing_workflow_or_allowing_finalize()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_overview_and_nested_kb_module_change_invalidates_review_receipt()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_answer_change_and_new_request_need_new_review_even_without_kb_change()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_finalize_rejects_changed_journal_answer_after_approved_stage_receipts()`
# @used-by :mod:`agent_tools.workflow`
def kb_paths(root):
	return HashCollector.kb_paths(root)
# @used-by :func:`agent_tools.blocked_report._standard_workflow_errors()`
# @used-by :func:`agent_tools.blocked_report.evaluate_check_workflow_errors()`
# @used-by :func:`agent_tools.completion._workflow_gate_resolved()`
# @used-by :func:`agent_tools.project_rename_verify._probe_workflow()`
# @used-by :func:`agent_tools.shadow_replay._run_finalize_stage()`
# @used-by :func:`agent_tools.shadow_replay._run_review_stage()`
# @used-by :func:`test_finalized_project_contract._complete_review_and_finalize()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.project_metrics()`
# @used-by :meth:`agent_tools.completion.AnswerPreparationRunner._audit_workflow_scope()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_resume_uses_existing_capture_and_agent_kb_without_reading_context()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.setUp()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.setUp()`
# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.test_blocked_report_records_journal_without_closing_workflow_or_allowing_finalize()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_explicit_upwork_init_binds_generic_workspace_without_rewriting_user_text()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_legacy_job_mention_after_foreign_init_cannot_reactivate_old_project()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_native_workspace_supports_self_review_and_empty_metadata_keeps_legacy_job_id()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_missing_native_root_keeps_legacy_job_id_but_foreign_root_does_not()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests._exercise_review_record_and_auth()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.test_significant_prepare_review_defaults_to_falsifier_and_authorizes_single_auditor()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_render_analysis_promote_domain_preserves_finalized_invariants()`
# @used-by :meth:`test_native_review_binding_m4.NativeReviewBindingM4Tests.setUp()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_exact_user_text_job_scope_and_cross_platform_request_merge()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_self_review_uses_codex_parent_evidence_without_requiring_antigravity()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_progress_is_replaced_without_archiving_derived_navigation()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_routine_self_review_is_explicit_and_never_counts_as_independent()`
# @used-by :meth:`test_review_contract.ReviewContractTests.authorize()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_cli_preregistered_unavailable_experiment_finishes_question_with_explicit_gap()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_legacy_review_and_analysis_cannot_authorize_new_answer()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_needs_changes_and_open_findings_persist_and_parent_disposition_cannot_approve()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_original_report_proof_is_immutable_when_input_filename_is_reused()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_parent_cannot_replace_authored_needs_changes_with_an_approved_json()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_relabeling_same_answer_cannot_hide_an_independent_rejection()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_routine_fact_approves_and_exact_answer_is_recorded()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_significant_self_finding_requires_two_independent_authored_followups()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_classifier_has_significant_flags_and_post_finalize_synthetic_claims()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_quorum_evaluator_selects_authorized_group_and_checks_approval_current()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_authorize_deduplicates_evidence_issues_across_check_project()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unadopted_substantive_followup_in_tracked_project_cannot_bypass_review()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unpersisted_source_reads_and_af_worker_cannot_bypass_substantive_review()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_tracked_prepare_preserves_finalizer_receipt_without_duplicate_pair()`
# @used-by :meth:`test_turn_completion.CompletionCase.tracked()`
# @used-by :mod:`agent_tools.workflow`
def load(root):
	return WorkflowStateEngine(root).load()
# @used-by :func:`agent_tools.text_review.record()`
# @used-by :mod:`agent_tools.workflow`
def now():
	return HashCollector.utc_now()
# @used-by :func:`agent_tools.cli_domains._op_prepare_review()`
# @used-by :func:`test_atomic_prepare_and_narrowed_reconcile_m7._authorize_routine_reply()`
# @used-by :func:`test_contract_invariants._authorize_routine()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_missing_risk_basis_or_manifest_is_rejected()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_relabeling_same_answer_cannot_hide_an_independent_rejection()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_task_flags_cannot_omit_typed_work_or_silently_default()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_quorum_evaluator_selects_authorized_group_and_checks_approval_current()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_report_validator_covers_falsifier_and_text_checks()`
# @used-by :mod:`agent_tools.workflow`
def prepare_review(root, parent_id, spec=None, response=None):
	from .review import prepare
	return prepare(root, parent_id, spec, response)
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_progress_is_replaced_without_archiving_derived_navigation()`
# @used-by :mod:`agent_tools.workflow`
def publish_progress(root, state, *, statuses=None):
	return WorkflowStateEngine(root).publish_progress(state, statuses=statuses)
# @used-by :mod:`agent_tools.workflow`
def question_contract_issues(root, question):
	return ResearchQuestionRegistry(root).contract_issues(question)
# @used-by :meth:`test_review_contract.ReviewContractTests.test_cli_preregistered_unavailable_experiment_finishes_question_with_explicit_gap()`
# @used-by :mod:`agent_tools.workflow`
def questions_current(root, state):
	return ResearchQuestionRegistry(root).current(state)
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_overview_and_nested_kb_module_change_invalidates_review_receipt()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_review_package_pins_primary_evidence_and_unquoted_new_contradiction()`
# @used-by :mod:`agent_tools.workflow`
def receipt_current(root, receipt):
	return WorkflowStateEngine(root).receipt_current(receipt)
# @used-by :func:`agent_tools.blocked_report.sync_authorized_workflow_requests()`
# @used-by :func:`agent_tools.cli_domains._op_record_answer()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_readable_links.ReadableProjectTests.test_record_answer_blocks_encoded_authored_links_before_any_journal_mutation()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_answer_change_and_new_request_need_new_review_even_without_kb_change()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_finalize_rejects_changed_journal_answer_after_approved_stage_receipts()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_routine_fact_approves_and_exact_answer_is_recorded()`
# @used-by :mod:`agent_tools.workflow`
def record_current_answer(root, response, *, journal_directory=None, request_ids=None, preauthorized=None, recorded_steps=None, turn_token=None):
	from .review import authorize
	return WorkflowStateEngine(root, update_fn=update, authorize_fn=authorize).record_current_answer(response, journal_directory=journal_directory, request_ids=request_ids, preauthorized=preauthorized, recorded_steps=recorded_steps, turn_token=turn_token)
# @used-by :func:`agent_tools.cli_domains._op_record_review()`
# @used-by :func:`test_atomic_prepare_and_narrowed_reconcile_m7._authorize_routine_reply()`
# @used-by :func:`test_contract_invariants._authorize_routine()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_significant_risk_cannot_finish_with_one_independent_aa()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_native_workspace_supports_self_review_and_empty_metadata_keeps_legacy_job_id()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_explicit_other_job_stays_foreign_despite_repeated_cwd_and_blocks_reviews()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.test_new_native_root_chat_imports_exact_continuation_and_allows_both_review_kinds()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests._native_record()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_self_review_uses_codex_parent_evidence_without_requiring_antigravity()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_routine_self_review_is_explicit_and_never_counts_as_independent()`
# @used-by :meth:`test_review_contract.ReviewContractTests.native_record()`
# @used-by :meth:`test_review_contract.ReviewContractTests.self_record()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_audit_must_explain_falsifiability_and_compare_raw_criteria()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_handwritten_empty_manifest_package_cannot_pass_record_review()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_official_distributor_is_not_established_by_contains_lunos_proxy()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_original_report_proof_is_immutable_when_input_filename_is_reused()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_per_claim_audit_is_required_and_qualified_gap_can_pass()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_quorum_evaluator_selects_authorized_group_and_checks_approval_current()`
# @used-by :mod:`agent_tools.workflow`
def record_review(root, report, *, parent_id, reviewer_id, role='AA', native_evidence=None, risk=None):
	from .review import record
	return record(root, report, parent_id=parent_id, reviewer_id=reviewer_id, role=role, native_evidence=native_evidence, risk=risk)
# @used-by :func:`agent_tools.cli_domains._op_review_disposition()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_needs_changes_and_open_findings_persist_and_parent_disposition_cannot_approve()`
# @used-by :mod:`agent_tools.workflow`
def record_review_disposition(root, review_id, finding_id, status, basis, evidence, parent_id):
	from .review import disposition
	return disposition(root, review_id, finding_id, status, basis, evidence, parent_id)
# @used-by :func:`agent_tools.cli_domains._op_question_search()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_search_cycle_returns_gap_or_requires_a_new_method()`
# @used-by :mod:`agent_tools.workflow`
def record_search(root, ident, owner, query, useful=False, method_change=None):
	return ResearchQuestionRegistry(root, update_fn=update).record_search(ident, owner, query, useful=useful, method_change=method_change)
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
# @used-by :meth:`test_registration_portability.RegistrationTests.test_workflow_registration_status_exposes_all_targets_and_pending_targets()`
# @used-by :mod:`agent_tools.workflow`
def registration_status(root):
	return WorkflowStateEngine(root).registration_status()
# @used-by :func:`agent_tools.cli_domains._op_resume()`
# @used-by :func:`test_contract_invariants._run_parity_defect_case()`
# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_changed_completed_stage_output_invalidates_dependencies()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_file_presence_does_not_complete_analysis_or_review()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_question_has_one_owner_and_explicit_handoff()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_resume_uses_existing_capture_and_agent_kb_without_reading_context()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_search_cycle_returns_gap_or_requires_a_new_method()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_significant_risk_cannot_finish_with_one_independent_aa()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_answer_check_and_prepare_reject_misaligned_pending_without_writing_journal()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.setUp()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.setUp()`
# @used-by :meth:`test_portability.CodexEvidenceTests.setUp()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_exact_user_text_job_scope_and_cross_platform_request_merge()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_new_question_invalidates_completed_research_and_dependent_analysis()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_routine_self_review_is_explicit_and_never_counts_as_independent()`
# @used-by :meth:`test_review_contract.ReviewContractTests.setUp()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_answer_change_and_new_request_need_new_review_even_without_kb_change()`
# @used-by :meth:`test_review_contract.ReviewDecompositionTests.setUp()`
# @used-by :meth:`test_review_target_claim_and_wait_m5.ReviewTargetClaimAndWaitM5Tests.setUp()`
# @used-by :mod:`agent_tools.workflow`
def resume(root, reason, request=None):
	return WorkflowStateEngine(root, update_fn=update).resume(reason, request=request)
# @used-by :func:`agent_tools.cli_domains._op_review_input()`
# @used-by :meth:`test_continuation_binding.CodexContinuationTests.setUp()`
# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.test_significant_prepare_review_defaults_to_falsifier_and_authorizes_single_auditor()`
# @used-by :meth:`test_portability.CodexEvidenceTests.set_review_input()`
# @used-by :mod:`agent_tools.workflow`
def review_input(root, package):
	from .review import input_receipt
	return input_receipt(root, package)
# @used-by :func:`agent_tools.project_rename_verify._probe_workflow()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.project_metrics()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_render_analysis_promote_domain_preserves_finalized_invariants()`
# @used-by :mod:`agent_tools.workflow`
def stage_statuses(root, state):
	return WorkflowStateEngine(root).stage_statuses(state)
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unadopted_substantive_followup_in_tracked_project_cannot_bypass_review()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_unpersisted_source_reads_and_af_worker_cannot_bypass_substantive_review()`
# @used-by :meth:`test_turn_completion.CompletionCase.tracked()`
# @used-by :mod:`agent_tools.workflow`
def state_path(root):
	return WorkflowStateEngine(root).state_path()
# @used-by :func:`agent_tools.cli_domains._op_status()`
# @used-by :func:`record_review_disposition()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_changed_completed_stage_output_invalidates_dependencies()`
# @used-by :meth:`test_analysis_workflow.ContinuationTests.test_file_presence_does_not_complete_analysis_or_review()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_new_question_invalidates_completed_research_and_dependent_analysis()`
# @used-by :meth:`test_review_contract.ReviewContractTests.test_legacy_review_and_analysis_cannot_authorize_new_answer()`
# @used-by :mod:`agent_tools.workflow`
def status(root, *, state=None, statuses=None):
	return WorkflowStateEngine(root).status(state=state, statuses=statuses)
# @used-by :func:`agent_tools.cli_domains._op_unadopt_requests()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_adopt_and_unadopt_requests_lifecycle()`
# @used-by :mod:`agent_tools.workflow`
def unadopt_requests(root, conversation_id=None, request_ids=None):
	return WorkflowStateEngine(root, update_fn=update).unadopt_requests(conversation_id=conversation_id, request_ids=request_ids)
# @used-by :func:`add_question()`
# @used-by :func:`adopt_requests()`
# @used-by :func:`agent_tools.blocked_report.sync_authorized_workflow_requests()`
# @used-by :func:`claim_question()`
# @used-by :func:`complete_stage()`
# @used-by :func:`finish_question()`
# @used-by :func:`handoff()`
# @used-by :func:`record_current_answer()`
# @used-by :func:`record_search()`
# @used-by :func:`resume()`
# @used-by :func:`unadopt_requests()`
# @used-by :meth:`agent_tools.completion.AnswerPreparationRunner._authorize_and_sync_workflow()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_exact_user_text_job_scope_and_cross_platform_request_merge()`
# @used-by :mod:`agent_tools.workflow`
def update(root, event, change):
	return WorkflowStateEngine(root).update(event, change)
__all__ = ['ProjectHealthAuditor', 'ResearchQuestionRegistry', 'SECTIONS', 'STAGES', 'WorkflowStateEngine', '_target_complete', 'add_question', 'adopt_requests', 'analysis_issues', 'attachment_issues', 'check_project', 'claim_question', 'complete_stage', 'doc4_sentence_issues', 'evidence_issues', 'evidence_paths', 'file_hash', 'finish_question', 'handoff', 'hashes', 'kb_issues', 'kb_paths', 'load', 'now', 'prepare_review', 'publish_owned', 'publish_progress', 'question_contract_issues', 'questions_current', 'receipt_current', 'record_current_answer', 'record_review', 'record_review_disposition', 'record_search', 'registration_status', 'resume', 'review_input', 'stage_statuses', 'state_path', 'status', 'unadopt_requests', 'update']
