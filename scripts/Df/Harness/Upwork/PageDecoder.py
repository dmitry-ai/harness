# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Upwork.JobUrlParser import JobUrlParser
import json
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PageDecoder:
	# @used-by :func:`agent_tools.upwork_extract.decode_page()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__capture_on_page()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	def __init__(self, page, job_id: str) -> None:
		self.__page = page
		self.__job_id = job_id
	# @used-by :func:`Df.Harness.lib.ag_wire._decode_media_lines()`
	# @used-by :func:`Df.Harness.lib.ag_wire._decode_message_payload()`
	# @used-by :func:`Df.Harness.lib.ag_wire._extract_cmd_names()`
	# @used-by :func:`Df.Harness.lib.ag_wire._parse_structured_item()`
	# @used-by :func:`Df.Harness.lib.ag_wire.dfh_wire_path()`
	# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_run_cleanup_report_cli()`
	# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_remove_antigravity()`
	# @used-by :func:`Df.Harness.lib.cleanup_store_ops._parse_pending_ag_entry()`
	# @used-by :func:`Df.Harness.lib.cli_domain_ops._load_consumed()`
	# @used-by :func:`Df.Harness.lib.cli_domain_ops._merge_prior_collection()`
	# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_prepare_review()`
	# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_record_answer()`
	# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_execute_collect()`
	# @used-by :func:`Df.Harness.lib.completion_commands._execute_prepare_or_check()`
	# @used-by :func:`Df.Harness.lib.config_blocks.dfh_load_project_receipt()`
	# @used-by :func:`Df.Harness.lib.config_codex.dfh_native_config()`
	# @used-by :func:`Df.Harness.lib.hook_trace_cache.dfh_parse_jsonl_bytes()`
	# @used-by :func:`Df.Harness.lib.issue.dfh_gh_api_call()`
	# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_config_json()`
	# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_config_toml()`
	# @used-by :func:`Df.Harness.lib.native_codex_roles._collect_role_backup_originals()`
	# @used-by :func:`Df.Harness.lib.research._decode_readable_match()`
	# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_check_runtime_snapshot()`
	# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_export_git_archive()`
	# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_git_read()`
	# @used-by :func:`Df.Harness.lib.storage.dfh_read_addressed_json()`
	# @used-by :func:`Df.Harness.lib.trace_common.dfh_read_jsonl_objects()`
	# @used-by :func:`agent_tools.repo_tags.commit_date_day()`
	# @used-by :func:`agent_tools.repo_tags.list_repo_tags()`
	# @used-by :func:`agent_tools.repo_tags.tags_at_commit()`
	# @used-by :func:`agent_tools.upwork_extract.decode_page()`
	# @used-by :func:`agent_tools.worktree_flow._current_branch()`
	# @used-by :func:`test_arch_audit_gates._record_verdict()`
	# @used-by :func:`test_failfast_and_schedule_gate._run_hook()`
	# @used-by :func:`test_turn_completion.assert_journal_response_body()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ManifestPrimaryVerifier.ManifestPrimaryVerifier.__load_state()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.__load_base()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationContentLoader.ObservationContentLoader.load()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__sync_locked()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagSyncer.RedFlagSyncer.__write_card()`
	# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.__load_text_or_structured()`
	# @used-by :meth:`Df.Harness.Arch.ReviewCli.ReviewCli.__exec_arch_prepare()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__collect_modules()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.__load_verified_package()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.read_review_input()`
	# @used-by :meth:`Df.Harness.Arch.ReviewStore.ReviewStore.record_review()`
	# @used-by :meth:`Df.Harness.Experiment.AssertionEvaluator.AssertionEvaluator.__select_raw()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__read_staged_markdown()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.__cat_file_type()`
	# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.__load_blob_text()`
	# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.__read_local_tag_map()`
	# @used-by :meth:`Df.Harness.Gate.RepoTagGate.RepoTagGate.__read_remote_tags()`
	# @used-by :meth:`Df.Harness.Gate.RulesAuditor.RulesAuditor.__inspect_workspace_auto_files()`
	# @used-by :meth:`Df.Harness.Gate.RulesAuditor.RulesAuditor.__load_rule_entries()`
	# @used-by :meth:`Df.Harness.Gate.RulesManifest.RulesManifest.inspect_rule()`
	# @used-by :meth:`Df.Harness.Git.BlobSizeValidator.BlobSizeValidator.__verify_push()`
	# @used-by :meth:`Df.Harness.Git.BlobSizeValidator.BlobSizeValidator.__verify_staged()`
	# @used-by :meth:`Df.Harness.Git.BlobUrlBuilder.BlobUrlBuilder.__validate_blob_fragment()`
	# @used-by :meth:`Df.Harness.Git.BlobUrlBuilder.BlobUrlBuilder.__validate_tree_path()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.__commit_sha_and_day()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.__read_tag_refs()`
	# @used-by :meth:`Df.Harness.Git.DirtyMainChecker.DirtyMainChecker.__branch_touched()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.extract_added_diff_urls()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.git()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.read_git()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.staged_paths()`
	# @used-by :meth:`Df.Harness.Git.RepoWaiter.RepoWaiter.__dirty_files()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__plan()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__read_tag_refs()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__resolve_sha()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCleaner.WorktreeCleaner.__current_branch()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCreator.WorktreeCreator.__current_branch()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.__current_branch()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.__rev_distance()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.inspect()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__read_and_index_entry()`
	# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__read_raw_for_stat()`
	# @used-by :meth:`Df.Harness.Issue.DirtyIssueFirstScanner.DirtyIssueFirstScanner.__parse_dirty_porcelain()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.read_utf8_no_bom_file()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.__dirty_entries()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.__load_log()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.__tracked_diff_urls()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.find_commit_for_issue()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.latest_commit_urls_for_files()`
	# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.upstream_unpushed()`
	# @used-by :meth:`Df.Harness.Issue.RepoLocator.RepoLocator.origin_repo_slug()`
	# @used-by :meth:`Df.Harness.Perf.TimesheetCommon.TimesheetCommon.load_jsonl_rows()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__register_single()`
	# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.__read_state()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptBuilder.ReceiptBuilder.build()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.verify_snapshot()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__sync_antigravity_native_files()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.update_projects_index()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.__update_project_json()`
	# @used-by :meth:`Df.Harness.Research.NetworkLinkChecker.NetworkLinkChecker.fetch_page()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__validate_current()`
	# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__load_and_check()`
	# @used-by :meth:`Df.Harness.Tdd.DiffContract.DiffContract.__parse_batch_blobs()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__decode_git_blob()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__git_diff_entries()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.classify()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.extract_markdown()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__capture_on_page()`
	# @used-by :meth:`Df.Harness.Upwork.PdfLigatureRepairer.PdfLigatureRepairer.parse_streams()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.check()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.read_check()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.scope_issues()`
	# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_antigravity_arch_record_review_works_on_bare_code_workspace_without_text_marker()`
	# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_cli_prepare_input_record_needs_changes_and_check_text_roundtrip()`
	# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_prepare_input_record_and_check_roundtrip_with_module_cache()`
	# @used-by :meth:`test_arch_rules_contract.ArchRulesContractTests.test_architecture_rule_is_compact_always_on_and_passes_doctor_and_rules_audit()`
	# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_historical_explicit_project_root_receipt_reconciles_without_rewriting_saved_state()`
	# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_skill_rules_and_docs_codify_mandatory_separate_companion_tracks()`
	# @used-by :meth:`test_df_analysis_rules_contract.DfAnalysisRulesAndSkillContractTests.test_rules_adapters_and_docs_codify_df_analysis_and_pass_lint()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_batch_http_and_browser_collectors_and_site_summarizer()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_registered_intake_and_attachment_are_primary_but_quote_must_match_locator()`
	# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_and_consume_input_with_readback_verification()`
	# @used-by :meth:`test_issue_first_pre_tool_use.IssueFirstPreToolUseGateTests.test_cli_subprocess_smoke()`
	# @used-by :meth:`test_issue_first_rules_contract.IssueFirstRulesAndDocsContractTests.test_rules_skill_and_docs_codify_issue_first_before_tdd_and_pass_lint()`
	# @used-by :meth:`test_java_xref.JavaXrefTests.test_java_see_override_edges_unused_and_lf_sync()`
	# @used-by :meth:`test_metadata_rules_contract.MetadataRulesAndDocsContractTests.test_rules_skill_and_docs_codify_json_metadata_headers_and_pass_lint()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_explicit_website_is_published_and_reused_without_overwriting_card_or_metadata()`
	# @used-by :meth:`test_red_flags.RedFlagTests.test_both_risks_precede_technical_analysis_and_are_duplicated_in_card()`
	# @used-by :meth:`test_review_contract.ReviewContractTests.test_merkle_cached_single_reviewer_quorum_recognizes_approved_digests_and_storage_receipts()`
	# @used-by :meth:`test_scatter_banner_gate.ScatterBannerGateTests.test_rules_and_skill_codify_file6_banner_and_pass_lint()`
	# @used-by :meth:`test_snapshot_latency_and_delegation_policy.SnapshotLatencyAndDelegationPolicyTests.test_delegation_rule_and_worktree_doc_codify_multi_track_policy_and_pass_audits()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_real_http_failure_and_redirect_are_saved_once_per_base_url()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_source_check_cli_preserves_success_and_failed_receipts_with_exit_codes()`
	# @used-by :meth:`test_tdd_pre_tool_use.TddPreToolUseGateTests.test_cli_subprocess_smoke()`
	# @used-by :meth:`test_tdd_rules_contract.TddRulesAndDocumentationContractTests.test_rules_and_docs_codify_tdd_contract_and_pass_lint_checks()`
	def decode(self) -> dict:
		if not isinstance(self.__page, dict):
			raise ValueError('Browser page state is unavailable')
		raw = self.__page.get('nuxt') or ''
		decoded = JobUrlParser.resolve_nuxt_devalue(json.loads(raw)) if raw else {}
		details = (decoded.get('vuex') or {}).get('jobDetails') or {} if isinstance(decoded, dict) else {}
		if (details.get('job') or {}).get('ciphertext') == self.__job_id:
			r = details
		else:
			status = ' '.join((str(self.__page.get(k) or '') for k in ('title', 'heading', 'body')))
			if re.search('access denied|not authorized|no longer available|do not have permission|don.t have permission', status, re.I):
				raise PermissionError('Upwork denies access to this job. No job data captured; do not bypass the restriction.')
			if not raw:
				raise ValueError('Selected tab has no Upwork source data; it may be unloaded or use an unsupported page format')
			raise ValueError('Selected page data does not match the requested job ID')
		return r
