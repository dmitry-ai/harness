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
	# @used-by :func:`agent_tools.cleanup.antigravity_projects()`
	# @used-by :func:`agent_tools.cleanup.remove_antigravity()`
	# @used-by :func:`agent_tools.cleanup_audit.run_cleanup_report_cli()`
	# @used-by :func:`agent_tools.cli_domains._load_consumed()`
	# @used-by :func:`agent_tools.cli_domains._op_prepare_review()`
	# @used-by :func:`agent_tools.cli_domains._op_record_answer()`
	# @used-by :func:`agent_tools.completion.execute()`
	# @used-by :func:`agent_tools.configuration._native_config()`
	# @used-by :func:`agent_tools.configuration.load_project_receipt()`
	# @used-by :func:`agent_tools.issues.repo_locator.origin_repo_slug()`
	# @used-by :func:`agent_tools.issues.service_helpers._parse_dirty_porcelain()`
	# @used-by :func:`agent_tools.issues.service_helpers.gh_api_call()`
	# @used-by :func:`agent_tools.journal.step_errors()`
	# @used-by :func:`agent_tools.links._readable_escapes()`
	# @used-by :func:`agent_tools.links.fetch_page()`
	# @used-by :func:`agent_tools.native_profiles._antigravity_plan()`
	# @used-by :func:`agent_tools.native_profiles._codex_plan()`
	# @used-by :func:`agent_tools.native_profiles._role_config()`
	# @used-by :func:`agent_tools.operations._execute_collect()`
	# @used-by :func:`agent_tools.operations._load_consumed_json()`
	# @used-by :func:`agent_tools.platforms.antigravity._decode_user_step_entry()`
	# @used-by :func:`agent_tools.platforms.antigravity._extract_user_step_meta()`
	# @used-by :func:`agent_tools.platforms.antigravity._wire_path()`
	# @used-by :func:`agent_tools.platforms.antigravity.register_antigravity_project()`
	# @used-by :func:`agent_tools.platforms.trace_common.read_jsonl_objects()`
	# @used-by :func:`agent_tools.polyglot_land._branch_touched_files()`
	# @used-by :func:`agent_tools.repo_tags._commit_sha_and_day()`
	# @used-by :func:`agent_tools.repo_tags._read_tag_refs()`
	# @used-by :func:`agent_tools.repo_tags._resolve_commit_sha()`
	# @used-by :func:`agent_tools.repo_tags._validate_blob_fragment()`
	# @used-by :func:`agent_tools.repo_tags.commit_date_day()`
	# @used-by :func:`agent_tools.repo_tags.list_repo_tags()`
	# @used-by :func:`agent_tools.repo_tags.plan_retro_tags()`
	# @used-by :func:`agent_tools.repo_tags.tags_at_commit()`
	# @used-by :func:`agent_tools.repo_tags.validate_tree_path_and_fragment()`
	# @used-by :func:`agent_tools.repo_wait._dirty_files()`
	# @used-by :func:`agent_tools.research.extract_bytes()`
	# @used-by :func:`agent_tools.runtime_snapshot._export_git_archive()`
	# @used-by :func:`agent_tools.runtime_snapshot._git_read()`
	# @used-by :func:`agent_tools.runtime_snapshot.check_runtime_snapshot()`
	# @used-by :func:`agent_tools.storage.read_addressed_json()`
	# @used-by :func:`agent_tools.trace_event_cache._parse_jsonl_bytes()`
	# @used-by :func:`agent_tools.upwork_extract.decode_page()`
	# @used-by :func:`agent_tools.worktree_flow._current_branch()`
	# @used-by :func:`agent_tools.worktree_flow._rev_distance()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_status()`
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
	# @used-by :meth:`Df.Harness.Perf.TimesheetCommon.TimesheetCommon.load_jsonl_rows()`
	# @used-by :meth:`Df.Harness.Project.CardSyncer.CardSyncer.__read_state()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptBuilder.ReceiptBuilder.build()`
	# @used-by :meth:`Df.Harness.Project.Intake.ReceiptValidator.ReceiptValidator.verify_snapshot()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.__sync_antigravity_native_files()`
	# @used-by :meth:`Df.Harness.Project.Rename.ProjectRenamer.ProjectRenamer.update_projects_index()`
	# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.__update_project_json()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__validate_current()`
	# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__load_and_check()`
	# @used-by :meth:`Df.Harness.Tdd.DiffContract.DiffContract.__parse_batch_blobs()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__decode_git_blob()`
	# @used-by :meth:`Df.Harness.Tdd.DiffExecutability.DiffExecutability.__git_diff_entries()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.classify()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.extract_markdown()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__capture_on_page()`
	# @used-by :meth:`Df.Harness.Upwork.PdfLigatureRepairer.PdfLigatureRepairer.parse_streams()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate._extract_added_diff_urls()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate._staged_paths()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.git()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.read_git()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_push_blob_sizes()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_staged_blob_sizes()`
	# @used-by :meth:`agent_tools.issues.git_read_cache.RepoReadCache._dirty_entries()`
	# @used-by :meth:`agent_tools.issues.git_read_cache.RepoReadCache._load_log()`
	# @used-by :meth:`agent_tools.issues.git_read_cache.RepoReadCache._tracked_diff_urls()`
	# @used-by :meth:`agent_tools.issues.git_read_cache.RepoReadCache.find_commit_for_issue()`
	# @used-by :meth:`agent_tools.issues.git_read_cache.RepoReadCache.latest_commit_urls_for_files()`
	# @used-by :meth:`agent_tools.issues.git_read_cache.RepoReadCache.upstream_unpushed()`
	# @used-by :meth:`agent_tools.issues.linter.IssueMarkdownLinter.read_utf8_no_bom_file()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex._stat_and_read()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.ensure_entry()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.load_source_info()`
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
