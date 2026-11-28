# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from Df.Harness.Research.HtmlReferences import HtmlReferences as HTMLReferences
from Df.Harness.Research.LinkAuditor import LinkAuditor
from Df.Harness.Research.MarkdownHeadingParser import MarkdownHeadingParser
from Df.Harness.Research.NetworkLinkChecker import NetworkLinkChecker
from Df.Harness.Research.Page import Page
from Df.Harness.lib.markdown import dfh_decode_file_uri
from Df.Harness.lib.research import dfh_bare_urls, dfh_document_urls, dfh_markdown_link, dfh_readable_reference
# @used-by :func:`Df.Harness.lib.completion_links.dfh_authored_nonquote_hrefs()`
# @used-by :mod:`agent_tools.links`
def _bare_urls(text: str):
	return dfh_bare_urls(text)
# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__collect_block_targets()`
# @used-by :mod:`agent_tools.links`
def _document_urls(text: str):
	return dfh_document_urls(text)
# @used-by :func:`Df.Harness.lib.completion_links.dfh_response_link_issues()`
# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.record()`
# @used-by :meth:`Df.Harness.Workflow.FinalizeStageRunner.FinalizeStageRunner.run()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_chat_reply_link_issues_allows_unencoded_file_uri_and_rejects_encoded()`
# @used-by :meth:`test_repo_link_gate.RepoLinkGateTests.test_rejects_file_uri_to_github_repo_and_allows_non_repo_and_gitignored_files()`
# @used-by :meth:`test_repo_link_gate.RepoLinkGateTests.test_validates_github_blob_and_tree_tags_paths_lines_and_anchors()`
# @used-by :mod:`agent_tools.links`
def chat_reply_link_issues(content: str, *, root: Path | None=None) -> list[str]:
	return LinkAuditor.chat_reply_link_issues(content, root=root)
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_validate_links()`
# @used-by :meth:`test_agent_tools.LinkTests.test_anchor_html_parser_handles_spacing_entities_and_case()`
# @used-by :meth:`test_agent_tools.LinkTests.test_failed_cached_fetch_reports_each_anchor()`
# @used-by :meth:`test_agent_tools.LinkTests.test_real_http_redirect_anchor_and_404()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids()`
# @used-by :mod:`agent_tools.links`
def check_network(urls: list[str], *, anchors: bool=False, timeout: float=15, fetcher=None) -> list[dict]:
	return NetworkLinkChecker(urls, anchors=anchors, timeout=timeout, fetcher=fetcher).check()
# @used-by :meth:`Df.Harness.Analysis.LocalSourceResolver.LocalSourceResolver.resolve()`
# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_decode_file_uri_handles_windows_relative_and_remote()`
# @used-by :mod:`agent_tools.links`
def decode_file_uri(reference: str, *, reject_remote: bool=False) -> str:
	return dfh_decode_file_uri(reference, reject_remote=reject_remote)
# @used-by :mod:`agent_tools.links`
def fetch_page(url: str, timeout: float=15) -> Page:
	return NetworkLinkChecker.fetch_page(url, timeout=timeout)
# @used-by :func:`Df.Harness.lib.completion_links.dfh_response_link_issues()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.__validate_doc_or_json_anchor()`
# @used-by :mod:`agent_tools.links`
def heading_anchors(content: str) -> set[str]:
	return MarkdownHeadingParser(content).parse()[1]
# @used-by :meth:`Df.Harness.Analysis.Renderer.Renderer.render()`
# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.render_evidence_md()`
# @used-by :meth:`Df.Harness.Project.KbPopulator.KbPopulator.render_projects_md()`
# @used-by :meth:`Df.Harness.Upwork.DocxExtractor.DocxExtractor.__render_link()`
# @used-by :meth:`Df.Harness.Upwork.KbProjectMdFormatter.KbProjectMdFormatter.__site_text()`
# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__text_element_raw()`
# @used-by :meth:`Df.Harness.Workflow.ProgressPublisher.ProgressPublisher.publish()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_cli_readability_check_catches_original_encoding_and_accepts_readable_destination()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_original_file_uri_becomes_a_readable_local_reference()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_query_signatures_delimiters_literal_percent_and_invalid_utf8_are_preserved()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_navigation_links_can_address_a_directory()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_source_survives_a_renderer_that_encodes_its_href()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_utf8_anchor_and_balanced_parentheses_need_no_url_encoding()`
# @used-by :mod:`agent_tools.links`
def markdown_link(label: str | None, target: str | Path) -> str:
	return dfh_markdown_link(label, target)
# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.__markdown_section()`
# @used-by :mod:`agent_tools.links`
def parse_markdown_headings(content: str) -> tuple[list[dict], set[str], set[str], str]:
	return MarkdownHeadingParser(content).parse()
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
readable_link_issues = LinkAuditor.readable_link_issues
# @used-by :meth:`Df.Harness.Upwork.PdfExtractor.PdfExtractor.__text_element_raw()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_original_file_uri_becomes_a_readable_local_reference()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_query_signatures_delimiters_literal_percent_and_invalid_utf8_are_preserved()`
# @used-by :mod:`agent_tools.links`
def readable_reference(value: str | Path) -> str:
	return dfh_readable_reference(value)
# @used-by :func:`Df.Harness.lib.completion_links.dfh_response_link_issues()`
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_validate_links()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.__validate_doc_or_json_anchor()`
# @used-by :meth:`test_agent_tools.LinkTests.test_code_samples_are_not_document_links()`
# @used-by :meth:`test_agent_tools.LinkTests.test_markdown_reference_links_balanced_parentheses_and_html()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_source_survives_a_renderer_that_encodes_its_href()`
# @used-by :mod:`agent_tools.links`
def references(content: str, include_code: bool=False) -> tuple[list[str], list[str]]:
	return LinkAuditor.references(content, include_code=include_code)
# @used-by :meth:`test_agent_tools.LinkTests.test_invalid_port_is_diagnostic_not_crash()`
# @used-by :meth:`test_agent_tools.LinkTests.test_local_anchors_decode_and_are_case_sensitive()`
# @used-by :meth:`test_agent_tools.LinkTests.test_preserves_valid_urls_and_markdown()`
# @used-by :meth:`test_agent_tools.LinkTests.test_same_id_and_name_on_one_anchor_are_not_duplicates()`
# @used-by :meth:`test_agent_tools.LinkTests.test_unique_urls_is_explicit_policy()`
# @used-by :mod:`agent_tools.links`
def validate_content(content: str, *, local_anchors: bool=False, unique_urls: bool=False, include_code: bool=False, readable_links: bool=False) -> list[str]:
	return LinkAuditor.validate_content(content, local_anchors=local_anchors, unique_urls=unique_urls, include_code=include_code, readable_links=readable_links)
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_validate_step_cli()`
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_validate_links()`
# @used-by :meth:`Df.Harness.Gate.RulesAuditChecker.RulesAuditChecker.check_links_and_blind_references()`
# @used-by :meth:`Df.Harness.Workflow.KbAuditor.KbAuditor.issues()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_stage4_docs_document_arch_audit_gate_and_lint_cleanly()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_native_profiles_generates_arch_auditor_for_antigravity_and_codex()`
# @used-by :meth:`test_arch_rules_contract.ArchRulesContractTests.test_architecture_rule_is_compact_always_on_and_passes_doctor_and_rules_audit()`
# @used-by :meth:`test_arch_rules_contract.ArchRulesContractTests.test_df_architecture_skill_discovered_and_lints_cleanly()`
# @used-by :meth:`test_ask_question_clarifications_m8.AskQuestionClarificationsM8Tests.test_skill_and_turn_completion_docs_prohibit_ask_question_stop_gate_bypass()`
# @used-by :meth:`test_ask_question_pre_tool_gate.AskQuestionPreToolGateTests.test_pre_tool_gate_blocks_stop_gate_bypass_and_docs_codify_rule()`
# @used-by :meth:`test_budget_status_scoping.BudgetStatusScopingTests.test_turn_completion_doc_describes_client_artifact_budget_scoping()`
# @used-by :meth:`test_cli_registry.CliRegistryTests.test_modular_docs_and_per_feature_test_rule_valid()`
# @used-by :meth:`test_code_formatting_rules.CodeFormattingRulesContractTests._assert_clean_doc()`
# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_rules_doc_codifies_code4_size_ratchet()`
# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_skill_rules_and_docs_codify_mandatory_separate_companion_tracks()`
# @used-by :meth:`test_df_analysis_rules_contract.DfAnalysisRulesAndSkillContractTests.test_df_analysis_skill_discovered_by_native_profiles_and_lints_cleanly()`
# @used-by :meth:`test_df_analysis_rules_contract.DfAnalysisRulesAndSkillContractTests.test_rules_adapters_and_docs_codify_df_analysis_and_pass_lint()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_docs_and_rules_codify_contract_within_rules_audit_budgets()`
# @used-by :meth:`test_issue_first_rules_contract.IssueFirstRulesAndDocsContractTests.test_rules_skill_and_docs_codify_issue_first_before_tdd_and_pass_lint()`
# @used-by :meth:`test_journal_clarifications_and_disclosure.JournalClarificationsAndDisclosureTests.test_turn_completion_doc_covers_clarifications_header_and_deferral_disclosure()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_exec4_documents_fifo_lease_and_swarm()`
# @used-by :meth:`test_metadata_rules_contract.MetadataRulesAndDocsContractTests.test_rules_skill_and_docs_codify_json_metadata_headers_and_pass_lint()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_df_github_issue_skill_documents_decomposition_and_passes_lint()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_analysis_links_causes_to_concerns_and_methods_to_causes()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_cross_file_markdown_anchors_and_missing_file()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_json_pointer_is_checked()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_windows_file_uris_and_absolute_paths()`
# @used-by :meth:`test_perf_improvement_skill_contract.PerfImprovementSkillContractTests.test_adapters_and_readme_document_skill_and_perf_cli_and_pass_lint()`
# @used-by :meth:`test_perf_improvement_skill_contract.PerfImprovementSkillContractTests.test_perf_improvement_skill_discovered_and_references_pass_lint()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_creation_publishes_supplied_site_and_reinit_keeps_the_card()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_navigation_links_can_address_a_directory()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_readable_source_survives_a_renderer_that_encodes_its_href()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_utf8_anchor_and_balanced_parentheses_need_no_url_encoding()`
# @used-by :meth:`test_repo_link_gate.RepoLinkGateTests.test_cross_repo_relative_link_rejected_while_intra_repo_relative_link_allowed()`
# @used-by :meth:`test_repo_tags_docs.RepoTagsDocsTests.test_rules_and_docs_codify_daily_tagging_and_link6_within_budgets()`
# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_exec4_documents_wait_repo_wait_timeout_and_no_premature_user_escalation()`
# @used-by :meth:`test_rules_architecture_m2.RulesArchitectureM2Tests.test_rules_have_zero_html_comments_valid_links_and_legacy_reference()`
# @used-by :meth:`test_scatter_banner_gate.ScatterBannerGateTests.test_rules_and_skill_codify_file6_banner_and_pass_lint()`
# @used-by :meth:`test_shadow_replay_m3.ShadowReplayM3Tests.test_exec2_rules_and_readme_document_shadow_replay_gate()`
# @used-by :meth:`test_snapshot_latency_and_delegation_policy.SnapshotLatencyAndDelegationPolicyTests.test_delegation_rule_and_worktree_doc_codify_multi_track_policy_and_pass_audits()`
# @used-by :meth:`test_tdd_rules_contract.TddRulesAndDocumentationContractTests.test_rules_and_docs_codify_tdd_contract_and_pass_lint_checks()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_exec5_documents_worktree_and_landing_only_host_mutations()`
# @used-by :mod:`agent_tools.links`
def validate_file(file_path: Path, **options) -> list[str]:
	return LinkAuditor(file_path, **options).validate_file()
__all__ = ['HTMLReferences', 'Page', '_bare_urls', '_document_urls', 'chat_reply_link_issues', 'check_network', 'decode_file_uri', 'fetch_page', 'heading_anchors', 'markdown_link', 'parse_markdown_headings', 'readable_link_issues', 'readable_reference', 'references', 'validate_content', 'validate_file']