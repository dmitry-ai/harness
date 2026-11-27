# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_check_doc_grounding_and_links()`
def _format_grounding_issues(issues: list[str]) -> str:
	from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
	unique = dfa_unique_fast(issues)
	return unique[0] if 1 == len(unique) else f'{len(unique)} grounding issues: ' + '; '.join(unique)
# @used-by :func:`dfh_check_markdown_content()`
def dfh_check_doc_grounding_and_links(proj_root: Path, content: str, p_obj: Path) -> str | None:
	from agent_tools.repo_link_gate import file_repo_link_issues, is_skipped_repo_link_doc
	from agent_tools.source_grounding import local_source_grounding_issues
	issues = list(local_source_grounding_issues(proj_root, content, doc_path=p_obj))
	if not is_skipped_repo_link_doc(p_obj):
		issues.extend(file_repo_link_issues(p_obj, content, repo_root=proj_root))
	return _format_grounding_issues(issues) if issues else None
# @used-by :meth:`Df.Harness.Hook.MarkdownSlopGate.MarkdownSlopGate.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
# @used-by :meth:`test_onboarding.InitializationTests.test_native_manifests_and_full_initial_port()`
# @used-by :meth:`test_repo_link_gate.RepoLinkGateTests.test_issue_linter_staged_gate_and_markdown_hook_enforce_repo_link_ban()`
# @used-by :meth:`test_scratch_slop_and_grounding_loc_m7.ScratchSlopAndGroundingLocM7Tests.test_non_scratch_md_reports_all_unique_grounding_issues_with_line_numbers_and_relpaths()`
# @used-by :meth:`test_scratch_slop_and_grounding_loc_m7.ScratchSlopAndGroundingLocM7Tests.test_scratch_draft_defers_grounding_but_keeps_doc4_syntax_checks()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_parallel_turn_scratch_isolation_and_budget_gate()`
def dfh_check_markdown_content(content, path=None) -> str | None:
	r: str | None = None
	if content and isinstance(content, str):
		slop = dfh_markdown_slop_issues(content)
		if slop:
			r = re.sub('^DOC-4\\s+', '', slop[0])
		if None is r and path:
			p_obj = Path(path)
			norm_p = path.replace('\\', '/').lower()
			if not dfh_is_request_journal_file(norm_p) and '/source/' not in norm_p and 'source.md' != p_obj.name.lower():
				proj_root = dfh_infer_project_root(p_obj)
				r = dfh_check_turn_budget_gate(proj_root, p_obj)
				if None is r and (not dfh_is_scratch_draft_file(norm_p)):
					r = dfh_check_doc_grounding_and_links(proj_root, content, p_obj)
	return r
# @used-by :func:`dfh_check_markdown_content()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
def dfh_check_turn_budget_gate(proj_root: Path, target: Path) -> str | None:
	from Df.Harness.lib.hook_runtime_ops import dfh_iter_turn_state_files
	from Df.Harness.lib.path_resolve import dfh_project_paths
	pp = dfh_project_paths(proj_root)
	norm_p = target.as_posix().lower()
	r: str | None = None
	if any((seg in norm_p for seg in pp.deliverable_segments)) and '/\ua616/' not in norm_p and '/\ua66e/' not in norm_p and '/\u26ef/' not in norm_p:
		for _, tdata in dfh_iter_turn_state_files(pp.turns_dir, exclude_hyphen=True):
			if tdata.get('status') in ('open', 'prepared', 'preparation_unverified'):
				bcheck = tdata.get('budget_check') or {}
				if bcheck.get('graceful_checkpoint_required') and (not bcheck.get('continuation_saved')):
					r = 'Turn Budget & Graceful Checkpoint Gate (M-4): active turn exceeded safe compaction/step budget (checkpoint_count >= 2, tool_step_count >= 120, or 5h window >= 400); persist verified findings to \ua616/KB/Evidence/ and \ua616/data/continuation.md and complete the turn via answer-prepare before generating new client deliverables'
					break
	return r
# @used-by :func:`dfh_check_markdown_content()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
def dfh_infer_project_root(target: Path) -> Path:
	from Df.Harness.lib.path_resolve import dfh_resolve_project_root
	resolved = dfh_resolve_project_root(target)
	markers = ('\ua616', '_/\ua616', '\ua66e', '\U0001f56e')
	if resolved != target.resolve().parent or any(((resolved / m).is_dir() for m in markers)):
		r = resolved
	else:
		cwd_res = dfh_resolve_project_root(Path.cwd().resolve())
		r = cwd_res if any(((cwd_res / m).is_dir() for m in markers)) else resolved
	return r
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
def dfh_is_abbreviation_end(text: str) -> bool:
	from Df.Harness.lib.hook_runtime_ops import ABBR_RE
	return bool(ABBR_RE.search(text.rstrip()))
# @used-by :func:`dfh_check_markdown_content()`
# @used-by :meth:`Df.Harness.Hook.MarkdownSlopGate.MarkdownSlopGate.run()`
def dfh_is_request_journal_file(norm_p: str) -> bool:
	return '/req/' in norm_p or bool(re.search('(?:^|/)\\ua66e/(?:[^/]+/)?\\u227b/', norm_p))
# @used-by :func:`dfh_check_markdown_content()`
def dfh_is_scratch_draft_file(norm_p: str) -> bool:
	return '/data/scratch/' in norm_p
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :func:`dfh_check_markdown_content()`
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
# @used-by :meth:`test_df_analysis.DfAnalysisGatesTests.test_markdown_table_blocked_across_doc4_hook_linter_and_grounding()`
# @used-by :meth:`test_df_analysis_companion_tracks.DfAnalysisCompanionTracksTests.test_skill_rules_and_docs_codify_mandatory_separate_companion_tracks()`
# @used-by :meth:`test_df_analysis_rules_contract.DfAnalysisRulesAndSkillContractTests.test_df_analysis_skill_discovered_by_native_profiles_and_lints_cleanly()`
# @used-by :meth:`test_df_analysis_rules_contract.DfAnalysisRulesAndSkillContractTests.test_rules_adapters_and_docs_codify_df_analysis_and_pass_lint()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_docs_and_rules_codify_contract_within_rules_audit_budgets()`
# @used-by :meth:`test_hook_unification.HookUnificationTests.test_doc4_scanner_supports_hook_and_workflow_modes()`
# @used-by :meth:`test_issue_first_rules_contract.IssueFirstRulesAndDocsContractTests.test_rules_skill_and_docs_codify_issue_first_before_tdd_and_pass_lint()`
# @used-by :meth:`test_journal_clarifications_and_disclosure.JournalClarificationsAndDisclosureTests.test_turn_completion_doc_covers_clarifications_header_and_deferral_disclosure()`
# @used-by :meth:`test_landing_lease.LandingLeaseTests.test_exec4_documents_fifo_lease_and_swarm()`
# @used-by :meth:`test_metadata_rules_contract.MetadataRulesAndDocsContractTests.test_rules_skill_and_docs_codify_json_metadata_headers_and_pass_lint()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_df_github_issue_skill_documents_decomposition_and_passes_lint()`
# @used-by :meth:`test_perf_improvement_skill_contract.PerfImprovementSkillContractTests.test_adapters_and_readme_document_skill_and_perf_cli_and_pass_lint()`
# @used-by :meth:`test_perf_improvement_skill_contract.PerfImprovementSkillContractTests.test_perf_improvement_skill_discovered_and_references_pass_lint()`
# @used-by :meth:`test_repo_tags_docs.RepoTagsDocsTests.test_rules_and_docs_codify_daily_tagging_and_link6_within_budgets()`
# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_exec4_documents_wait_repo_wait_timeout_and_no_premature_user_escalation()`
# @used-by :meth:`test_rules_architecture_m2.RulesArchitectureM2Tests.test_rules_have_zero_html_comments_valid_links_and_legacy_reference()`
# @used-by :meth:`test_scatter_banner_gate.ScatterBannerGateTests.test_rules_and_skill_codify_file6_banner_and_pass_lint()`
# @used-by :meth:`test_shadow_replay_m3.ShadowReplayM3Tests.test_exec2_rules_and_readme_document_shadow_replay_gate()`
# @used-by :meth:`test_snapshot_latency_and_delegation_policy.SnapshotLatencyAndDelegationPolicyTests.test_delegation_rule_and_worktree_doc_codify_multi_track_policy_and_pass_audits()`
# @used-by :meth:`test_tdd_rules_contract.TddRulesAndDocumentationContractTests.test_rules_and_docs_codify_tdd_contract_and_pass_lint_checks()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_exec5_documents_worktree_and_landing_only_host_mutations()`
def dfh_markdown_slop_issues(content: str) -> list[str]:
	from Df.Harness.lib.hook_runtime_ops import dfh_scan_doc4_sentence_issues
	return dfh_scan_doc4_sentence_issues(content, mode='hook')
# @used-by :meth:`Df.Harness.Hook.MarkdownSlopGate.MarkdownSlopGate.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
def dfh_resolve_markdown_content(name: str, args: dict, path: str):
	if 'write_file' == name:
		content = args.get('Content')
	else:
		content = args.get('Replacement')
		p_file, target_str = (Path(path), args.get('Target'))
		if p_file.is_file() and isinstance(target_str, str) and target_str and isinstance(content, str):
			try:
				raw_doc = p_file.read_text(encoding='utf-8')
				if target_str in raw_doc:
					content = raw_doc.replace(target_str, content)
			except OSError:
				pass
	return content