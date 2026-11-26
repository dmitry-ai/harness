# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from copy import deepcopy
from typing import override
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from agent_tools.text_browser import GuardedCDP, operation, preflight
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
class NativeFixture:
	# @used-by :func:`dom_fixture()`
	# @used-by :meth:`TextBrowserTests.setUp()`
	# @used-by :meth:`TextBrowserTests.test_collect_browser_never_hijacks_open_user_tab_without_tab_id_and_uses_hidden_target()`
	# @used-by :meth:`TextBrowserTests.test_collect_http_auto_fallback_to_browser_on_reddit_js_challenge_shell()`
	# @used-by :meth:`TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
	def __init__(self):
		self.calls = []
		self.arguments = ['browser', '--user-data-dir=C:/authorized', '--profile-directory=Default']
		self.targets = [{'id': 'selected', 'type': 'page', 'url': 'https://example.invalid/start', 'title': 'Selected', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/selected'}]
		self.browser = 'ws://127.0.0.1:9222/devtools/browser/live'
		self.unavailable = False
	# @used-by :func:`agent_tools.addon_observability._runtime_issues_from_data()`
	# @used-by :func:`agent_tools.addon_observability._touches_antigravity_addons()`
	# @used-by :func:`agent_tools.addon_observability.default_companion_runtime_path()`
	# @used-by :func:`agent_tools.addon_observability.detect_suppressed_worktree_errors()`
	# @used-by :func:`agent_tools.addon_observability.evaluate_addon_observability()`
	# @used-by :func:`agent_tools.addon_observability.evaluate_worktree_removal_audit()`
	# @used-by :func:`agent_tools.addon_observability.is_live_runtime_data_file()`
	# @used-by :func:`agent_tools.admission._same_binding()`
	# @used-by :func:`agent_tools.admission.verify()`
	# @used-by :func:`agent_tools.analysis._render_claim_contract()`
	# @used-by :func:`agent_tools.analysis.analysis_issues()`
	# @used-by :func:`agent_tools.analysis.iter_arguments()`
	# @used-by :func:`agent_tools.analysis.publish_owned()`
	# @used-by :func:`agent_tools.analysis.render_analysis()`
	# @used-by :func:`agent_tools.analysis.require_current_contract()`
	# @used-by :func:`agent_tools.analysis.source_uri()`
	# @used-by :func:`agent_tools.analysis.valid_gap()`
	# @used-by :func:`agent_tools.analysis_merge._claim_id()`
	# @used-by :func:`agent_tools.analysis_merge._merge_extra_fields()`
	# @used-by :func:`agent_tools.analysis_merge._validate_partial()`
	# @used-by :func:`agent_tools.analysis_merge.merge_analysis_candidate()`
	# @used-by :func:`agent_tools.analysis_merge.save_merged_analysis()`
	# @used-by :func:`agent_tools.article.check_graph()`
	# @used-by :func:`agent_tools.article.check_link_style()`
	# @used-by :func:`agent_tools.article.parse_sections()`
	# @used-by :func:`agent_tools.article.render()`
	# @used-by :func:`agent_tools.article.to_source()`
	# @used-by :func:`agent_tools.blocked_report._authorize_workflow_errors()`
	# @used-by :func:`agent_tools.blocked_report._standard_workflow_errors()`
	# @used-by :func:`agent_tools.blocked_report.audit_runner_workflow_scope()`
	# @used-by :func:`agent_tools.blocked_report.evaluate_check_workflow_errors()`
	# @used-by :func:`agent_tools.blocked_report.evaluate_runner_code_hygiene()`
	# @used-by :func:`agent_tools.blocked_report.pending_workflow_alignment_issues()`
	# @used-by :func:`agent_tools.blocked_report.record_blocked_report_entry()`
	# @used-by :func:`agent_tools.blocked_report.sync_authorized_workflow_requests()`
	# @used-by :func:`agent_tools.claims._calculation_structure()`
	# @used-by :func:`agent_tools.claims._check_calculation()`
	# @used-by :func:`agent_tools.claims._check_comparison()`
	# @used-by :func:`agent_tools.claims._claim_numeric_corpus()`
	# @used-by :func:`agent_tools.claims._comparison_structure()`
	# @used-by :func:`agent_tools.claims._dependencies()`
	# @used-by :func:`agent_tools.claims._manifest_primary()`
	# @used-by :func:`agent_tools.claims._primary_capabilities()`
	# @used-by :func:`agent_tools.claims._quantity_matches()`
	# @used-by :func:`agent_tools.claims._verify_quote()`
	# @used-by :func:`agent_tools.claims.claim_index()`
	# @used-by :func:`agent_tools.claims.claim_locations()`
	# @used-by :func:`agent_tools.claims.collect_claim_closure()`
	# @used-by :func:`agent_tools.claims.grounded_numbers_for_claim()`
	# @used-by :func:`agent_tools.cleanup._base_age()`
	# @used-by :func:`agent_tools.cleanup._belongs_cached()`
	# @used-by :func:`agent_tools.cleanup._collect_folder_ancestors()`
	# @used-by :func:`agent_tools.cleanup._load_conversation_index()`
	# @used-by :func:`agent_tools.cleanup.antigravity_projects()`
	# @used-by :func:`agent_tools.cleanup.candidates()`
	# @used-by :func:`agent_tools.cleanup.catalog_projects()`
	# @used-by :func:`agent_tools.cleanup.legacy_initialization()`
	# @used-by :func:`agent_tools.cleanup.prune_folders()`
	# @used-by :func:`agent_tools.cleanup.restore_antigravity()`
	# @used-by :func:`agent_tools.cleanup_audit._build_manifest_payload()`
	# @used-by :func:`agent_tools.cleanup_audit._collect_instance_rollbacks()`
	# @used-by :func:`agent_tools.cleanup_audit._extract_removed_record()`
	# @used-by :func:`agent_tools.cleanup_audit._project_summary_entry()`
	# @used-by :func:`agent_tools.cleanup_audit._resolve_meta_root()`
	# @used-by :func:`agent_tools.cleanup_audit.build_cleanup_metadata()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._collect_handoff_activity()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._collect_rename_activity()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._collect_workflow_finalize()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._count_ag_conversations()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._count_codex_conversations()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._disabled_ag_history()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._disabled_codex_history()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._extract_nested_project_ids()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._launcher_turn_dirs()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._probe_disabled_ag_db()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._recorded_native_ids()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._step_response_time()`
	# @used-by :func:`agent_tools.cleanup_lifecycle._turn_matches_project()`
	# @used-by :func:`agent_tools.cleanup_lifecycle.load_codex_history_rows()`
	# @used-by :func:`agent_tools.cleanup_lifecycle.project_canonical_keys()`
	# @used-by :func:`agent_tools.cleanup_lifecycle.resolve_readonly_history()`
	# @used-by :func:`agent_tools.cli_command_grounding._cmd_from_tool_call()`
	# @used-by :func:`agent_tools.cli_command_grounding._collect_passing_trace_commands()`
	# @used-by :func:`agent_tools.cli_command_grounding._collect_row_outputs()`
	# @used-by :func:`agent_tools.cli_command_grounding._is_passing_output()`
	# @used-by :func:`agent_tools.cli_command_grounding._record_call_outcome()`
	# @used-by :func:`agent_tools.cli_command_grounding._resolve_bg_completions()`
	# @used-by :func:`agent_tools.cli_command_grounding.unverified_cli_command_issues()`
	# @used-by :func:`agent_tools.cli_common.consume_scratch_input()`
	# @used-by :func:`agent_tools.cli_common.load_operation_input()`
	# @used-by :func:`agent_tools.cli_common.result_exit_code()`
	# @used-by :func:`agent_tools.cli_domains._op_question_add()`
	# @used-by :func:`agent_tools.cli_domains._op_render_analysis()`
	# @used-by :func:`agent_tools.cli_registry._register_analysis_builtins()`
	# @used-by :func:`agent_tools.cli_registry._register_runtime_builtins()`
	# @used-by :func:`agent_tools.cli_registry.dispatch_registered()`
	# @used-by :func:`agent_tools.cli_registry.execute_registered()`
	# @used-by :func:`agent_tools.code_size_gate._check_function_limits()`
	# @used-by :func:`agent_tools.code_size_gate._resolve_python_target()`
	# @used-by :func:`agent_tools.code_size_gate._unique_fn_map()`
	# @used-by :func:`agent_tools.code_style_gate._check_function_returns()`
	# @used-by :func:`agent_tools.code_style_gate._unique_return_map()`
	# @used-by :func:`agent_tools.completion._active()`
	# @used-by :func:`agent_tools.completion._budget_status()`
	# @used-by :func:`agent_tools.completion._compact_compaction_check()`
	# @used-by :func:`agent_tools.completion._compaction_status()`
	# @used-by :func:`agent_tools.completion._conflict()`
	# @used-by :func:`agent_tools.completion._delegation_status()`
	# @used-by :func:`agent_tools.completion._factual_kb_note_issues()`
	# @used-by :func:`agent_tools.completion._find_evicted_cited_files()`
	# @used-by :func:`agent_tools.completion._gate_resolved()`
	# @used-by :func:`agent_tools.completion._group()`
	# @used-by :func:`agent_tools.completion._instruction_snapshot()`
	# @used-by :func:`agent_tools.completion._intermediate_or_language_issues()`
	# @used-by :func:`agent_tools.completion._issue_first_status()`
	# @used-by :func:`agent_tools.completion._matches_recorded_response()`
	# @used-by :func:`agent_tools.completion._native()`
	# @used-by :func:`agent_tools.completion._record()`
	# @used-by :func:`agent_tools.completion._recorded()`
	# @used-by :func:`agent_tools.completion._recoverable_step_status()`
	# @used-by :func:`agent_tools.completion._same_saved_request()`
	# @used-by :func:`agent_tools.completion._scan_child_trace_turn()`
	# @used-by :func:`agent_tools.completion._similar_projects_metadata()`
	# @used-by :func:`agent_tools.completion._state()`
	# @used-by :func:`agent_tools.completion._sync_antigravity_conversation_title()`
	# @used-by :func:`agent_tools.completion._tdd_status()`
	# @used-by :func:`agent_tools.completion._workflow_gate_resolved()`
	# @used-by :func:`agent_tools.completion._write_compaction_index_file()`
	# @used-by :func:`agent_tools.completion.begin()`
	# @used-by :func:`agent_tools.completion.check_answer()`
	# @used-by :func:`agent_tools.completion.handoff_launcher_turn()`
	# @used-by :func:`agent_tools.completion.issue_first_check_turn()`
	# @used-by :func:`agent_tools.completion.ratchet_ok()`
	# @used-by :func:`agent_tools.completion.recover_checkpoint()`
	# @used-by :func:`agent_tools.completion.similar_project_exempt()`
	# @used-by :func:`agent_tools.completion.sync_conversation_title()`
	# @used-by :func:`agent_tools.completion.tdd_check_turn()`
	# @used-by :func:`agent_tools.configuration._native_config()`
	# @used-by :func:`agent_tools.configuration._project_rule_paths()`
	# @used-by :func:`agent_tools.configuration._publish()`
	# @used-by :func:`agent_tools.configuration._root_options()`
	# @used-by :func:`agent_tools.configuration.build_native()`
	# @used-by :func:`agent_tools.configuration.configure_codex_project()`
	# @used-by :func:`agent_tools.configuration.global_codex_instructions()`
	# @used-by :func:`agent_tools.configuration.load_discovery_manifest()`
	# @used-by :func:`agent_tools.configuration.receipt_sha256()`
	# @used-by :func:`agent_tools.configuration.resolve_manifest_entry()`
	# @used-by :func:`agent_tools.context.assemble()`
	# @used-by :func:`agent_tools.context.generate()`
	# @used-by :func:`agent_tools.diagnostics.require_valid()`
	# @used-by :func:`agent_tools.doc5_context._cmd_from_call()`
	# @used-by :func:`agent_tools.doc5_context._earliest_cli_failure_step()`
	# @used-by :func:`agent_tools.doc5_context._has_post_failure_parent_issue()`
	# @used-by :func:`agent_tools.doc5_context._inspect_call_failure()`
	# @used-by :func:`agent_tools.doc5_context._is_failed_cli_output()`
	# @used-by :func:`agent_tools.doc5_context._record_bg_cli_failures()`
	# @used-by :func:`agent_tools.doc5_context._row_outputs()`
	# @used-by :func:`agent_tools.doc5_context.turn_requires_doc5_problem_analysis()`
	# @used-by :func:`agent_tools.evidence.evidence_issues()`
	# @used-by :func:`agent_tools.evidence.verify_html_quote_scope()`
	# @used-by :func:`agent_tools.evidence.verify_saved_quote()`
	# @used-by :func:`agent_tools.evidence_loader._collect_ext_metadata()`
	# @used-by :func:`agent_tools.evidence_loader._extract_bundle_html()`
	# @used-by :func:`agent_tools.evidence_loader._extract_bundle_markdown()`
	# @used-by :func:`agent_tools.evidence_loader._first_h1()`
	# @used-by :func:`agent_tools.evidence_loader._has_full_sections()`
	# @used-by :func:`agent_tools.evidence_loader._inspect_ext_file()`
	# @used-by :func:`agent_tools.evidence_loader._inspect_resp_bin()`
	# @used-by :func:`agent_tools.evidence_loader._load_saved_extracted_html()`
	# @used-by :func:`agent_tools.evidence_loader._resolve_html_data()`
	# @used-by :func:`agent_tools.evidence_loader.is_valid_observation_status()`
	# @used-by :func:`agent_tools.evidence_loader.load_observation_bundle()`
	# @used-by :func:`agent_tools.evidence_loader.load_observation_content()`
	# @used-by :func:`agent_tools.evidence_loader.probe_observation_status()`
	# @used-by :func:`agent_tools.experiments.requirement_issues()`
	# @used-by :func:`agent_tools.experiments.result_issues()`
	# @used-by :func:`agent_tools.failfast_gate._active_turn_run_command_tasks()`
	# @used-by :func:`agent_tools.failfast_gate._apply_sync_wait()`
	# @used-by :func:`agent_tools.failfast_gate._schedule_block_reason()`
	# @used-by :func:`agent_tools.failfast_gate.evaluate_pre_tool_use_schedule()`
	# @used-by :func:`agent_tools.failfast_gate.evaluate_pre_tool_use_test_failfast()`
	# @used-by :func:`agent_tools.gates._load_builtin_pre_tool_gates()`
	# @used-by :func:`agent_tools.gates.answer_checks._addon_observability_messages()`
	# @used-by :func:`agent_tools.gates.answer_checks._build_checks_map()`
	# @used-by :func:`agent_tools.gates.answer_checks._compaction_messages()`
	# @used-by :func:`agent_tools.gates.answer_checks._delegation_messages()`
	# @used-by :func:`agent_tools.gates.answer_checks._exec5_messages()`
	# @used-by :func:`agent_tools.gates.answer_checks._hook_crash_messages()`
	# @used-by :func:`agent_tools.gates.answer_checks._http_messages()`
	# @used-by :func:`agent_tools.gates.answer_checks._lifecycle_messages()`
	# @used-by :func:`agent_tools.gates.answer_checks._partial_read_messages()`
	# @used-by :func:`agent_tools.gates.answer_checks._verification_obs_messages()`
	# @used-by :func:`agent_tools.gates.answer_checks.run_answer_gates()`
	# @used-by :func:`agent_tools.gates.batch_synthesis.check()`
	# @used-by :func:`agent_tools.gates.browser_mcp._turn_has_background_mcp_new_page()`
	# @used-by :func:`agent_tools.gates.browser_mcp.check()`
	# @used-by :func:`agent_tools.gates.bulk_source_read._update_streak()`
	# @used-by :func:`agent_tools.gates.bulk_source_read.check()`
	# @used-by :func:`agent_tools.gates.cdp_bypass.check()`
	# @used-by :func:`agent_tools.gates.external_write._is_uninstructed_open_turn()`
	# @used-by :func:`agent_tools.gates.external_write.check()`
	# @used-by :func:`agent_tools.gates.git_write.check()`
	# @used-by :func:`agent_tools.gates.journal_write.check()`
	# @used-by :func:`agent_tools.gates.rules_budget._check_local_rule()`
	# @used-by :func:`agent_tools.gates.rules_budget.check()`
	# @used-by :func:`agent_tools.gates.send_message_gate.check()`
	# @used-by :func:`agent_tools.gates.server_hygiene.check()`
	# @used-by :func:`agent_tools.gates.stop_checks._check_code_lifecycle()`
	# @used-by :func:`agent_tools.gates.stop_checks._check_issue_first()`
	# @used-by :func:`agent_tools.gates.stop_checks._check_prepared()`
	# @used-by :func:`agent_tools.gates.stop_checks._check_tdd()`
	# @used-by :func:`agent_tools.gates.worktree_isolation._active_turn_id()`
	# @used-by :func:`agent_tools.gates.worktree_isolation._turn_timestamp()`
	# @used-by :func:`agent_tools.gates.worktree_isolation.check()`
	# @used-by :func:`agent_tools.git_gate.cleanup_stale_credential_locks()`
	# @used-by :func:`agent_tools.git_gate.is_agent_git_context()`
	# @used-by :func:`agent_tools.git_ignore.finalize_install_result()`
	# @used-by :func:`agent_tools.git_ignore.resolve_global_git_ignore_path()`
	# @used-by :func:`agent_tools.grounding_domains._check_load_average_tuples()`
	# @used-by :func:`agent_tools.grounding_domains._check_mem_tuples()`
	# @used-by :func:`agent_tools.grounding_domains._check_null_cpu_tuples()`
	# @used-by :func:`agent_tools.grounding_domains._check_swap_tuples()`
	# @used-by :func:`agent_tools.grounding_domains._collect_json_fact_tuples()`
	# @used-by :func:`agent_tools.grounding_domains.fact_tuple_contradictions()`
	# @used-by :func:`agent_tools.grounding_helpers._load_ext_url_entry()`
	# @used-by :func:`agent_tools.grounding_helpers._obs_bucket()`
	# @used-by :func:`agent_tools.grounding_helpers.build_active_corpus_cached()`
	# @used-by :func:`agent_tools.hook_crash_audit._collect_issue_refs()`
	# @used-by :func:`agent_tools.hook_crash_audit._extract_hook_error()`
	# @used-by :func:`agent_tools.hook_crash_audit._issue_evidence_mentions_crash()`
	# @used-by :func:`agent_tools.hook_crash_audit._load_turn_rows()`
	# @used-by :func:`agent_tools.hook_crash_audit._slice_turn_rows()`
	# @used-by :func:`agent_tools.hook_crash_audit._text_documents_hook_crash()`
	# @used-by :func:`agent_tools.hook_crash_audit.build_violation_recovery_receipt()`
	# @used-by :func:`agent_tools.hook_crash_audit.detect_hook_crashes()`
	# @used-by :func:`agent_tools.hook_crash_audit.evaluate_hook_crash_check()`
	# @used-by :func:`agent_tools.hook_runtime._slice_after_last_user()`
	# @used-by :func:`agent_tools.intake._project()`
	# @used-by :func:`agent_tools.intake._snapshot()`
	# @used-by :func:`agent_tools.intake._validate_new()`
	# @used-by :func:`agent_tools.intake._validate_receipt()`
	# @used-by :func:`agent_tools.intake.commit_capture()`
	# @used-by :func:`agent_tools.issue_comment_gate._check_added_issue_line()`
	# @used-by :func:`agent_tools.issue_comment_gate._check_class_scope()`
	# @used-by :func:`agent_tools.issue_comment_gate._resolve_comment_target()`
	# @used-by :func:`agent_tools.issue_first_bg._collect_row_outputs()`
	# @used-by :func:`agent_tools.issue_first_bg._dispatch_segment_call()`
	# @used-by :func:`agent_tools.issue_first_bg._handle_run_command_call()`
	# @used-by :func:`agent_tools.issue_first_bg._handle_write_call()`
	# @used-by :func:`agent_tools.issue_first_bg._process_segment_row()`
	# @used-by :func:`agent_tools.issue_first_bg._record_bg_issue_completion()`
	# @used-by :func:`agent_tools.issue_first_bg._record_bg_seg_issues()`
	# @used-by :func:`agent_tools.issue_first_bg.handle_antigravity_bg_task_message()`
	# @used-by :func:`agent_tools.issue_first_gate._extract_request_text()`
	# @used-by :func:`agent_tools.issue_first_gate._load_evidence_issue_info()`
	# @used-by :func:`agent_tools.issue_first_gate._seed_open_issues_from_requests()`
	# @used-by :func:`agent_tools.issue_first_gate.build_issue_action_events()`
	# @used-by :func:`agent_tools.issue_first_gate.evaluate_issue_first_events()`
	# @used-by :func:`agent_tools.issue_first_gate.evaluate_pre_tool_use_issue_first()`
	# @used-by :func:`agent_tools.issue_first_gate.extract_antigravity_issue_first_events()`
	# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_acceptance_receipt()`
	# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_readiness()`
	# @used-by :func:`agent_tools.issues.parity._evaluate_similar_peer_item()`
	# @used-by :func:`agent_tools.issues.parity._exemption_matches_peer()`
	# @used-by :func:`agent_tools.issues.parity._find_peer_issue_resolution()`
	# @used-by :func:`agent_tools.issues.parity._item_belongs_to_turn()`
	# @used-by :func:`agent_tools.issues.parity._load_similar_project_exemptions()`
	# @used-by :func:`agent_tools.issues.parity._match_similar_exemption()`
	# @used-by :func:`agent_tools.issues.parity._resolve_peer_parity()`
	# @used-by :func:`agent_tools.issues.parity.merge_turn_issue_item()`
	# @used-by :func:`agent_tools.issues.repo_commands._audit_repo_comments()`
	# @used-by :func:`agent_tools.issues.repo_commands._audit_repo_issues()`
	# @used-by :func:`agent_tools.issues.repo_commands._poll_transferred_repo()`
	# @used-by :func:`agent_tools.issues.repo_commands.run_fetch()`
	# @used-by :func:`agent_tools.issues.repo_commands.run_transfer_repo()`
	# @used-by :func:`agent_tools.issues.repo_locator._search_registry_and_roots()`
	# @used-by :func:`agent_tools.issues.service_helpers._collect_recorded_repos_from_turn()`
	# @used-by :func:`agent_tools.issues.service_helpers._recorded_open_turn_repos()`
	# @used-by :func:`agent_tools.issues.turn_scope._fallback_env_session()`
	# @used-by :func:`agent_tools.issues.turn_scope._resolve_antigravity_parent_cid()`
	# @used-by :func:`agent_tools.issues.turn_scope.has_competing_open_turns()`
	# @used-by :func:`agent_tools.issues.workspace._extract_issue_num()`
	# @used-by :func:`agent_tools.issues.workspace._merge_entry_lists()`
	# @used-by :func:`agent_tools.issues.workspace._parse_parent_from_issue_dict()`
	# @used-by :func:`agent_tools.issues.workspace._update_turn_issue_entry()`
	# @used-by :func:`agent_tools.journal._read_turn_reservations()`
	# @used-by :func:`agent_tools.journal._sync_overlay_journal_slot()`
	# @used-by :func:`agent_tools.journal.answer_groups()`
	# @used-by :func:`agent_tools.journal.completed_request_group_index()`
	# @used-by :func:`agent_tools.journal.find_orphan_or_overwritten_steps()`
	# @used-by :func:`agent_tools.journal.get_existing_step_ids()`
	# @used-by :func:`agent_tools.journal.matching_group_response()`
	# @used-by :func:`agent_tools.journal.record_answer()`
	# @used-by :func:`agent_tools.journal.recover_step()`
	# @used-by :func:`agent_tools.journal.reserve_turn_steps()`
	# @used-by :func:`agent_tools.journal.reserved_step_ids()`
	# @used-by :func:`agent_tools.journal.upgrade_journal()`
	# @used-by :func:`agent_tools.journal.verify_answer()`
	# @used-by :func:`agent_tools.journal_integrity._check_reconciliation_failures()`
	# @used-by :func:`agent_tools.journal_integrity._committed_turn_steps()`
	# @used-by :func:`agent_tools.journal_integrity._eligible_active_turn_keys()`
	# @used-by :func:`agent_tools.journal_integrity._group_steps_for_cid()`
	# @used-by :func:`agent_tools.journal_integrity._is_terminal_conflict()`
	# @used-by :func:`agent_tools.journal_integrity._mentioned_other_job()`
	# @used-by :func:`agent_tools.journal_integrity._subtract_entry_overlap()`
	# @used-by :func:`agent_tools.journal_integrity._turn_index_for_project()`
	# @used-by :func:`agent_tools.journal_integrity._turn_state_orphan_reason()`
	# @used-by :func:`agent_tools.journal_integrity.acknowledged_sequence_gaps()`
	# @used-by :func:`agent_tools.journal_integrity.classify_reservations()`
	# @used-by :func:`agent_tools.journal_integrity.collect_conversation_journal_steps()`
	# @used-by :func:`agent_tools.journal_integrity.collect_handed_off_conversations()`
	# @used-by :func:`agent_tools.journal_integrity.finalize_conflict_turn()`
	# @used-by :func:`agent_tools.journal_integrity.finalize_project_check()`
	# @used-by :func:`agent_tools.journal_integrity.prune_terminal_conflict_reservations()`
	# @used-by :func:`agent_tools.journal_integrity.sync_begin_turn_state()`
	# @used-by :func:`agent_tools.journal_integrity.turn_matches_handoff()`
	# @used-by :func:`agent_tools.journal_integrity.validate_finalize_journal()`
	# @used-by :func:`agent_tools.journal_liveness.classify_reservation_entry()`
	# @used-by :func:`agent_tools.journal_liveness.is_conversation_running_live()`
	# @used-by :func:`agent_tools.journal_sync_all._collect_all_open_candidates()`
	# @used-by :func:`agent_tools.journal_sync_all._is_foreign_open_eligible()`
	# @used-by :func:`agent_tools.journal_sync_all._is_native_idle_for_sync()`
	# @used-by :func:`agent_tools.journal_sync_all._iter_idle_prepared_candidates()`
	# @used-by :func:`agent_tools.journal_sync_all._reconcile_current_earlier()`
	# @used-by :func:`agent_tools.journal_sync_all._resolve_ag_summary_db()`
	# @used-by :func:`agent_tools.journal_sync_all._try_sync_foreign_entry()`
	# @used-by :func:`agent_tools.journal_sync_all.reconcile_foreign_open_reservations()`
	# @used-by :func:`agent_tools.journal_sync_all.resolve_sync_provenance()`
	# @used-by :func:`agent_tools.journal_sync_all.sync_all_open()`
	# @used-by :func:`agent_tools.knowledge._render_evidence_md()`
	# @used-by :func:`agent_tools.knowledge._render_projects_md()`
	# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
	# @used-by :func:`agent_tools.knowledge.populate_agent_kb()`
	# @used-by :func:`agent_tools.knowledge.sync_initial_website()`
	# @used-by :func:`agent_tools.knowledge.sync_project_attachments_and_kb()`
	# @used-by :func:`agent_tools.knowledge.sync_website_card()`
	# @used-by :func:`agent_tools.knowledge.website_issues()`
	# @used-by :func:`agent_tools.landing_lease._default_owner()`
	# @used-by :func:`agent_tools.landing_lease._enqueue_owner()`
	# @used-by :func:`agent_tools.landing_lease._is_entry_alive()`
	# @used-by :func:`agent_tools.landing_lease._load_state()`
	# @used-by :func:`agent_tools.landing_lease._prune_state()`
	# @used-by :func:`agent_tools.landing_lease._try_acquire_once()`
	# @used-by :func:`agent_tools.landing_lease._unqueue_owner()`
	# @used-by :func:`agent_tools.landing_lease.acquire_lease()`
	# @used-by :func:`agent_tools.landing_lease.lease_status()`
	# @used-by :func:`agent_tools.landing_lease.release_lease()`
	# @used-by :func:`agent_tools.links.validate_file()`
	# @used-by :func:`agent_tools.markdown_links.display_address()`
	# @used-by :func:`agent_tools.meta.blocks._resolve_hook()`
	# @used-by :func:`agent_tools.meta.builders._apply_issue_state_details()`
	# @used-by :func:`agent_tools.meta.builders._collect_ag_issue_ctx()`
	# @used-by :func:`agent_tools.meta.builders._collect_codex_issue_ctx()`
	# @used-by :func:`agent_tools.meta.builders._collect_journal_turn_state()`
	# @used-by :func:`agent_tools.meta.builders._detect_env_platform()`
	# @used-by :func:`agent_tools.meta.builders._enrich_journal_ag()`
	# @used-by :func:`agent_tools.meta.builders._merge_transcript_fields()`
	# @used-by :func:`agent_tools.meta.builders._refine_issue_ctx_from_state()`
	# @used-by :func:`agent_tools.meta.builders._resolve_issue_group_file()`
	# @used-by :func:`agent_tools.meta.builders._resolve_journal_platform()`
	# @used-by :func:`agent_tools.meta.builders._resolve_turn_index()`
	# @used-by :func:`agent_tools.meta.builders.build_github_issue_metadata()`
	# @used-by :func:`agent_tools.meta.builders.build_journal_metadata()`
	# @used-by :func:`agent_tools.meta.formatting._split_model_and_effort()`
	# @used-by :func:`agent_tools.meta.formatting._system_display_name()`
	# @used-by :func:`agent_tools.meta.headers._is_harness_metadata_obj()`
	# @used-by :func:`agent_tools.meta.identity._antigravity_project_dirs()`
	# @used-by :func:`agent_tools.meta.identity._load_projects_dir_items()`
	# @used-by :func:`agent_tools.meta.identity._lookup_name_by_project_id()`
	# @used-by :func:`agent_tools.meta.identity._lookup_name_from_project_dirs()`
	# @used-by :func:`agent_tools.meta.identity._lookup_name_from_project_json()`
	# @used-by :func:`agent_tools.meta.transcripts._ag_transcript_file()`
	# @used-by :func:`agent_tools.meta.transcripts._apply_codex_context()`
	# @used-by :func:`agent_tools.meta.transcripts._apply_codex_event()`
	# @used-by :func:`agent_tools.meta.transcripts._extract_turn_steps_from_state()`
	# @used-by :func:`agent_tools.meta.transcripts._parse_antigravity_source_metadata()`
	# @used-by :func:`agent_tools.meta.transcripts._read_ag_summary_row()`
	# @used-by :func:`agent_tools.meta.transcripts._record_ag_row()`
	# @used-by :func:`agent_tools.meta.transcripts._record_codex_task_started()`
	# @used-by :func:`agent_tools.meta.transcripts._resolve_ag_model_and_effort()`
	# @used-by :func:`agent_tools.meta.transcripts._turn_state_candidate()`
	# @used-by :func:`agent_tools.metrics._resolve_target()`
	# @used-by :func:`agent_tools.metrics._save_executor_metadata()`
	# @used-by :func:`agent_tools.metrics.native_tool_trace()`
	# @used-by :func:`agent_tools.metrics.project_metrics()`
	# @used-by :func:`agent_tools.metrics.summarize()`
	# @used-by :func:`agent_tools.metrics.summarize_instance()`
	# @used-by :func:`agent_tools.metrics.verify_native_proof()`
	# @used-by :func:`agent_tools.native_profiles._antigravity_plan()`
	# @used-by :func:`agent_tools.native_profiles._apply()`
	# @used-by :func:`agent_tools.native_profiles._codex_plan()`
	# @used-by :func:`agent_tools.native_profiles._directory_link()`
	# @used-by :func:`agent_tools.native_profiles._disable_codex_bundled_chrome_plugin()`
	# @used-by :func:`agent_tools.native_profiles._execute()`
	# @used-by :func:`agent_tools.native_profiles._legacy_role_config()`
	# @used-by :func:`agent_tools.native_profiles._load_state()`
	# @used-by :func:`agent_tools.native_profiles._manifest()`
	# @used-by :func:`agent_tools.native_profiles._model_fields()`
	# @used-by :func:`agent_tools.native_profiles._profile_agents()`
	# @used-by :func:`agent_tools.native_profiles._profile_state()`
	# @used-by :func:`agent_tools.native_profiles._retire_profile_roles()`
	# @used-by :func:`agent_tools.native_profiles._retire_profile_skills()`
	# @used-by :func:`agent_tools.native_profiles._retire_shared_roles()`
	# @used-by :func:`agent_tools.native_profiles._role_config()`
	# @used-by :func:`agent_tools.native_profiles._role_values()`
	# @used-by :func:`agent_tools.native_profiles._shared_plan()`
	# @used-by :func:`agent_tools.native_profiles._skills()`
	# @used-by :func:`agent_tools.native_profiles.install_native_profiles()`
	# @used-by :func:`agent_tools.native_profiles.retire_owned_project_projections()`
	# @used-by :func:`agent_tools.native_profiles.shared_native_outputs()`
	# @used-by :func:`agent_tools.operations._execute_collect()`
	# @used-by :func:`agent_tools.operations.add_parsers()`
	# @used-by :func:`agent_tools.operations.execute()`
	# @used-by :func:`agent_tools.parallel_runner._save_timings()`
	# @used-by :func:`agent_tools.parallel_runner.discover_test_modules()`
	# @used-by :func:`agent_tools.path_cache.lookup_fast_project_paths()`
	# @used-by :func:`agent_tools.path_cache.lru_get()`
	# @used-by :func:`agent_tools.path_cache.resolve_code_anchor()`
	# @used-by :func:`agent_tools.path_registry._candidate_discovery_roots()`
	# @used-by :func:`agent_tools.path_registry._env_fingerprint()`
	# @used-by :func:`agent_tools.path_registry._find_local_marker_root()`
	# @used-by :func:`agent_tools.path_registry._has_v2_markers()`
	# @used-by :func:`agent_tools.path_registry._infer_default_profile()`
	# @used-by :func:`agent_tools.path_registry._inspect_journal_dir_on_disk()`
	# @used-by :func:`agent_tools.path_registry._is_registered_single_project()`
	# @used-by :func:`agent_tools.path_registry._journal_cache_sig()`
	# @used-by :func:`agent_tools.path_registry._refresh_known_overlay_links()`
	# @used-by :func:`agent_tools.path_registry._v2_software_deliverable_dir()`
	# @used-by :func:`agent_tools.path_registry._validate_overlay()`
	# @used-by :func:`agent_tools.path_registry._validate_similar_project_groups()`
	# @used-by :func:`agent_tools.path_registry.canonicalize_root_dir()`
	# @used-by :func:`agent_tools.path_registry.default_platform_paths()`
	# @used-by :func:`agent_tools.path_registry.derive_platform_system_paths()`
	# @used-by :func:`agent_tools.path_registry.evaluate_similar_project_touches()`
	# @used-by :func:`agent_tools.path_registry.load_registry()`
	# @used-by :func:`agent_tools.path_registry.paths_report()`
	# @used-by :func:`agent_tools.path_registry.relocated_harness_code_dirs()`
	# @used-by :func:`agent_tools.path_registry.workspace_override()`
	# @used-by :func:`agent_tools.perf.suite_profiler._aggregate_cprofile()`
	# @used-by :func:`agent_tools.perf.suite_profiler._aggregate_totals()`
	# @used-by :func:`agent_tools.perf.suite_profiler._assemble_report()`
	# @used-by :func:`agent_tools.perf.suite_profiler._file_summary()`
	# @used-by :func:`agent_tools.perf.suite_profiler._run_worker()`
	# @used-by :func:`agent_tools.perf.suite_profiler.format_profile_text()`
	# @used-by :func:`agent_tools.perf.timesheet._detect_surface()`
	# @used-by :func:`agent_tools.perf.timesheet._infer_conversation_id()`
	# @used-by :func:`agent_tools.perf.timesheet._slice_rows()`
	# @used-by :func:`agent_tools.perf.timesheet_ag._ag_timestamps()`
	# @used-by :func:`agent_tools.perf.timesheet_ag._bg_match_records()`
	# @used-by :func:`agent_tools.perf.timesheet_ag._command_wall_and_bg()`
	# @used-by :func:`agent_tools.perf.timesheet_ag._extract_step_end_ts()`
	# @used-by :func:`agent_tools.perf.timesheet_ag._process_planner_step()`
	# @used-by :func:`agent_tools.perf.timesheet_ag._record_checkpoint()`
	# @used-by :func:`agent_tools.perf.timesheet_ag._record_generic_step()`
	# @used-by :func:`agent_tools.perf.timesheet_ag._record_tokens_and_switches()`
	# @used-by :func:`agent_tools.perf.timesheet_ag._record_tool_call()`
	# @used-by :func:`agent_tools.perf.timesheet_ag._resolve_bg_wait()`
	# @used-by :func:`agent_tools.perf.timesheet_ag._sync_generic_dur()`
	# @used-by :func:`agent_tools.perf.timesheet_ag.analyze_antigravity_rows()`
	# @used-by :func:`agent_tools.perf.timesheet_codex._build_codex_result()`
	# @used-by :func:`agent_tools.perf.timesheet_codex._process_codex_row()`
	# @used-by :func:`agent_tools.perf.timesheet_codex._record_codex_call()`
	# @used-by :func:`agent_tools.perf.timesheet_codex._record_codex_event()`
	# @used-by :func:`agent_tools.perf.timesheet_codex._record_codex_item()`
	# @used-by :func:`agent_tools.perf.timesheet_codex._record_codex_output()`
	# @used-by :func:`agent_tools.perf.timesheet_codex._record_codex_tokens()`
	# @used-by :func:`agent_tools.perf.timesheet_common._lookup_conversation_trace()`
	# @used-by :func:`agent_tools.perf.timesheet_common.format_timesheet_text()`
	# @used-by :func:`agent_tools.perf.timesheet_common.resolve_journal_step_meta()`
	# @used-by :func:`agent_tools.platforms.adapter()`
	# @used-by :func:`agent_tools.platforms.antigravity._decode_user_step_entry()`
	# @used-by :func:`agent_tools.platforms.antigravity._default_folders_json()`
	# @used-by :func:`agent_tools.platforms.antigravity._extract_subagent_uuids()`
	# @used-by :func:`agent_tools.platforms.antigravity._extract_transcript_user_input()`
	# @used-by :func:`agent_tools.platforms.antigravity._find_subagent_invocations()`
	# @used-by :func:`agent_tools.platforms.antigravity._load_transcript_inputs()`
	# @used-by :func:`agent_tools.platforms.antigravity._native_invocation()`
	# @used-by :func:`agent_tools.platforms.antigravity._project_item_matches_root()`
	# @used-by :func:`agent_tools.platforms.antigravity._project_roots()`
	# @used-by :func:`agent_tools.platforms.antigravity._proof_paths()`
	# @used-by :func:`agent_tools.platforms.antigravity._read_current_conversation_title()`
	# @used-by :func:`agent_tools.platforms.antigravity._resolve_folders_json()`
	# @used-by :func:`agent_tools.platforms.antigravity.discover_live_daemon()`
	# @used-by :func:`agent_tools.platforms.antigravity.native_executor_metadata()`
	# @used-by :func:`agent_tools.platforms.antigravity.native_review_proof()`
	# @used-by :func:`agent_tools.platforms.antigravity.native_tool_trace()`
	# @used-by :func:`agent_tools.platforms.antigravity.register()`
	# @used-by :func:`agent_tools.platforms.antigravity.register_antigravity_project()`
	# @used-by :func:`agent_tools.platforms.antigravity.update_conversation_title()`
	# @used-by :func:`agent_tools.platforms.antigravity.verify_native_proof()`
	# @used-by :func:`agent_tools.platforms.antigravity_review_helpers._is_incoming_assignment_row()`
	# @used-by :func:`agent_tools.platforms.antigravity_review_helpers._probe_reviewer_final()`
	# @used-by :func:`agent_tools.platforms.antigravity_review_helpers.resolve_parent_binding_inputs()`
	# @used-by :func:`agent_tools.platforms.antigravity_review_helpers.reviewer_assigned_package()`
	# @used-by :func:`agent_tools.platforms.clarifications._extract_question_texts()`
	# @used-by :func:`agent_tools.platforms.clarifications._find_generic_output()`
	# @used-by :func:`agent_tools.platforms.clarifications._record_ask_call()`
	# @used-by :func:`agent_tools.platforms.clarifications.build_segment_metadata()`
	# @used-by :func:`agent_tools.platforms.clarifications.extract_ask_question_clarifications()`
	# @used-by :func:`agent_tools.platforms.clarifications.merge_segment_metadata()`
	# @used-by :func:`agent_tools.platforms.codex._actual_user_input()`
	# @used-by :func:`agent_tools.platforms.codex._assignment_source()`
	# @used-by :func:`agent_tools.platforms.codex._extract_codex_spawn_output_uuids()`
	# @used-by :func:`agent_tools.platforms.codex._extract_codex_target_subagents()`
	# @used-by :func:`agent_tools.platforms.codex._messages()`
	# @used-by :func:`agent_tools.platforms.codex._model()`
	# @used-by :func:`agent_tools.platforms.codex._request_scope()`
	# @used-by :func:`agent_tools.platforms.codex._review_inputs()`
	# @used-by :func:`agent_tools.platforms.codex._selection()`
	# @used-by :func:`agent_tools.platforms.codex._spawn()`
	# @used-by :func:`agent_tools.platforms.codex._state_db_files()`
	# @used-by :func:`agent_tools.platforms.codex._trace()`
	# @used-by :func:`agent_tools.platforms.codex.native_executor_metadata()`
	# @used-by :func:`agent_tools.platforms.codex.native_review_proof()`
	# @used-by :func:`agent_tools.platforms.codex.native_tool_trace()`
	# @used-by :func:`agent_tools.platforms.codex.register()`
	# @used-by :func:`agent_tools.platforms.codex.summarize()`
	# @used-by :func:`agent_tools.platforms.codex.verify_native_proof()`
	# @used-by :func:`agent_tools.platforms.proof_metadata._dict_prefix_match()`
	# @used-by :func:`agent_tools.platforms.proof_metadata.executor_metadata_equivalent()`
	# @used-by :func:`agent_tools.platforms.proof_metadata.proof_semantically_equivalent()`
	# @used-by :func:`agent_tools.platforms.request_binding._extract_leading_upwork_init_ids()`
	# @used-by :func:`agent_tools.platforms.request_binding.format_binding_diagnostic()`
	# @used-by :func:`agent_tools.platforms.request_binding.native_project_id()`
	# @used-by :func:`agent_tools.platforms.trace_common._iter_normalized_tool_calls()`
	# @used-by :func:`agent_tools.platforms.trace_common.extract_resource_uri()`
	# @used-by :func:`agent_tools.platforms.trace_common.finalize_executor_checks()`
	# @used-by :func:`agent_tools.platforms.trace_common.iter_antigravity_subagents()`
	# @used-by :func:`agent_tools.platforms.trace_common.merge_turn_accumulators()`
	# @used-by :func:`agent_tools.platforms.trace_common.partial_candidate_read_issues()`
	# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
	# @used-by :func:`agent_tools.platforms.trace_common.reviewer_isolation_issues()`
	# @used-by :func:`agent_tools.platforms.trace_common.summarize_token_records()`
	# @used-by :func:`agent_tools.platforms.trace_common.summarize_turn_activity()`
	# @used-by :func:`agent_tools.platforms.trace_common.verify_review_proof_core()`
	# @used-by :func:`agent_tools.polyglot_land._auto_node_spec()`
	# @used-by :func:`agent_tools.polyglot_land._diff_host_snapshots()`
	# @used-by :func:`agent_tools.polyglot_land._expand_spec()`
	# @used-by :func:`agent_tools.polyglot_land._interpret_health_proc()`
	# @used-by :func:`agent_tools.polyglot_land._parse_health_state()`
	# @used-by :func:`agent_tools.polyglot_land._snapshot_one_host_file()`
	# @used-by :func:`agent_tools.polyglot_land.resolve_repo_verification_spec()`
	# @used-by :func:`agent_tools.polyglot_land.run_polyglot_land_tests()`
	# @used-by :func:`agent_tools.polyglot_land.run_repo_health_check()`
	# @used-by :func:`agent_tools.problem_tracks._block_scope_text()`
	# @used-by :func:`agent_tools.project_card.sync_block()`
	# @used-by :func:`agent_tools.project_drift._established_client_identity()`
	# @used-by :func:`agent_tools.project_drift._registered_title_mismatches()`
	# @used-by :func:`agent_tools.project_drift.domain_drift_issues()`
	# @used-by :func:`agent_tools.project_drift.require_stage_project_valid()`
	# @used-by :func:`agent_tools.project_rename._ag_id_from_receipt()`
	# @used-by :func:`agent_tools.project_rename._antigravity_dirs_map()`
	# @used-by :func:`agent_tools.project_rename._apply_rename_mutations()`
	# @used-by :func:`agent_tools.project_rename._item_matches_uri()`
	# @used-by :func:`agent_tools.project_rename._sync_antigravity_native_files()`
	# @used-by :func:`agent_tools.project_rename.apply_domain_promotion()`
	# @used-by :func:`agent_tools.project_rename.maybe_promote_project_domain()`
	# @used-by :func:`agent_tools.project_rename.rename_project()`
	# @used-by :func:`agent_tools.project_rename.resolve_promotable_target_domain()`
	# @used-by :func:`agent_tools.project_rename_state._rename_lineage_roots()`
	# @used-by :func:`agent_tools.project_rename_state._update_project_json()`
	# @used-by :func:`agent_tools.project_rename_verify._check_config_status()`
	# @used-by :func:`agent_tools.project_rename_verify._probe_review_auth()`
	# @used-by :func:`agent_tools.project_rename_verify._verify_stage_regression()`
	# @used-by :func:`agent_tools.project_rename_verify.capture_pre_rename_snapshot()`
	# @used-by :func:`agent_tools.project_rename_verify.verify_post_rename()`
	# @used-by :func:`agent_tools.proposal._check_references()`
	# @used-by :func:`agent_tools.proposal._check_sequence()`
	# @used-by :func:`agent_tools.proposal._format_checks()`
	# @used-by :func:`agent_tools.proposal.lint_text()`
	# @used-by :func:`agent_tools.proposal.parse_blocks()`
	# @used-by :func:`agent_tools.reconcile_helpers._can_narrow_open_turn()`
	# @used-by :func:`agent_tools.reconcile_helpers._tail_present_in_other_turns()`
	# @used-by :func:`agent_tools.reconcile_helpers._trim_narrowed_reservation()`
	# @used-by :func:`agent_tools.reconcile_helpers.resolve_saved_turn_requests()`
	# @used-by :func:`agent_tools.red_flags.red_flag_issues()`
	# @used-by :func:`agent_tools.red_flags.render_red_flags()`
	# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
	# @used-by :func:`agent_tools.registration._begin()`
	# @used-by :func:`agent_tools.registration._complete()`
	# @used-by :func:`agent_tools.registration._success()`
	# @used-by :func:`agent_tools.registration.register_projects()`
	# @used-by :func:`agent_tools.registration.save_registration()`
	# @used-by :func:`agent_tools.registration.validate_registration()`
	# @used-by :func:`agent_tools.repo_tag_gate._cached_local_tag_map()`
	# @used-by :func:`agent_tools.repo_tag_gate._cached_remote_tags()`
	# @used-by :func:`agent_tools.repo_tag_gate._resolve_origin_push_target()`
	# @used-by :func:`agent_tools.repo_tag_gate.verify_closing_commit_tag()`
	# @used-by :func:`agent_tools.repo_tags._build_retro_entry()`
	# @used-by :func:`agent_tools.repo_tags._configured_timezone()`
	# @used-by :func:`agent_tools.repo_tags.ensure_commit_tag()`
	# @used-by :func:`agent_tools.repo_wait._probe_repo_state()`
	# @used-by :func:`agent_tools.research._grep_section_windows()`
	# @used-by :func:`agent_tools.research._summarize_json_collections()`
	# @used-by :func:`agent_tools.research._summarize_observation_bundle()`
	# @used-by :func:`agent_tools.research._write_cached_extraction()`
	# @used-by :func:`agent_tools.research.bounded_metrics()`
	# @used-by :func:`agent_tools.research.capture_dom()`
	# @used-by :func:`agent_tools.research.classify_html_challenge()`
	# @used-by :func:`agent_tools.research.collect()`
	# @used-by :func:`agent_tools.research.collect_browser()`
	# @used-by :func:`agent_tools.research.collect_browser_batch()`
	# @used-by :func:`agent_tools.research.collect_http()`
	# @used-by :func:`agent_tools.research.collect_plan()`
	# @used-by :func:`agent_tools.research.compact_extraction_for_disk()`
	# @used-by :func:`agent_tools.research.compute_site_summary()`
	# @used-by :func:`agent_tools.research.evidence_query()`
	# @used-by :func:`agent_tools.research.extract_bytes()`
	# @used-by :func:`agent_tools.research.extract_github_blob_lines()`
	# @used-by :func:`agent_tools.research.extract_markdown()`
	# @used-by :func:`agent_tools.research.extract_observation()`
	# @used-by :func:`agent_tools.research.load_observation()`
	# @used-by :func:`agent_tools.research.metric_counts()`
	# @used-by :func:`agent_tools.research.observation_capabilities()`
	# @used-by :func:`agent_tools.research.observed_use()`
	# @used-by :func:`agent_tools.research.request_context()`
	# @used-by :func:`agent_tools.research.select_dom_tab()`
	# @used-by :func:`agent_tools.review._analysis()`
	# @used-by :func:`agent_tools.review._claim_evidence_pairs()`
	# @used-by :func:`agent_tools.review._package_handler()`
	# @used-by :func:`agent_tools.review.authenticate_report()`
	# @used-by :func:`agent_tools.review.authorize()`
	# @used-by :func:`agent_tools.review.build_blind_verification_predicates()`
	# @used-by :func:`agent_tools.review.claim_merkle_hash()`
	# @used-by :func:`agent_tools.review.compute_claim_merkle_delta()`
	# @used-by :func:`agent_tools.review.disposition()`
	# @used-by :func:`agent_tools.review.input_receipt()`
	# @used-by :func:`agent_tools.review.load_verified_claims_cache()`
	# @used-by :func:`agent_tools.review.prepare()`
	# @used-by :func:`agent_tools.review.prepare_verdict_record()`
	# @used-by :func:`agent_tools.review.read_package()`
	# @used-by :func:`agent_tools.review.read_package_envelope()`
	# @used-by :func:`agent_tools.review.record()`
	# @used-by :func:`agent_tools.review.resolve_addressed_reviews()`
	# @used-by :func:`agent_tools.review.subject_digest()`
	# @used-by :func:`agent_tools.review.update_verified_claims_cache()`
	# @used-by :func:`agent_tools.review.verify_entry_native_proof()`
	# @used-by :func:`agent_tools.review_alignment._package_envelope_issues()`
	# @used-by :func:`agent_tools.review_alignment.alignment_issues()`
	# @used-by :func:`agent_tools.review_alignment.bind_contract_envelope()`
	# @used-by :func:`agent_tools.review_alignment.build_claim_targets()`
	# @used-by :func:`agent_tools.review_alignment.envelope_issues()`
	# @used-by :func:`agent_tools.review_alignment.resolve_package_review_mode()`
	# @used-by :func:`agent_tools.rules_audit._load_rule_entries()`
	# @used-by :func:`agent_tools.rules_audit._prospective_always_on_totals()`
	# @used-by :func:`agent_tools.rules_audit._prospective_rule_text()`
	# @used-by :func:`agent_tools.rules_audit.check_shared_rule_edit()`
	# @used-by :func:`agent_tools.rules_audit.format_rules_audit_text()`
	# @used-by :func:`agent_tools.rules_manifest._split_codex_rule_paths()`
	# @used-by :func:`agent_tools.rules_manifest.inspect_shared_rule()`
	# @used-by :func:`agent_tools.runtime._antigravity_backend_has_conversation()`
	# @used-by :func:`agent_tools.runtime._codex_home_conversation_trace()`
	# @used-by :func:`agent_tools.runtime._resolve_platform_cfg()`
	# @used-by :func:`agent_tools.runtime._validate_runtime()`
	# @used-by :func:`agent_tools.runtime.all_instances()`
	# @used-by :func:`agent_tools.runtime.default_system_paths()`
	# @used-by :func:`agent_tools.runtime.default_user_locale()`
	# @used-by :func:`agent_tools.runtime.extract_platform_homes()`
	# @used-by :func:`agent_tools.runtime.extract_platform_instances()`
	# @used-by :func:`agent_tools.runtime.find_conversation_instance()`
	# @used-by :func:`agent_tools.runtime.platform_adapter_name()`
	# @used-by :func:`agent_tools.runtime.platform_enabled()`
	# @used-by :func:`agent_tools.runtime.platform_key_for_adapter()`
	# @used-by :func:`agent_tools.runtime.platform_name()`
	# @used-by :func:`agent_tools.runtime.profile_name()`
	# @used-by :func:`agent_tools.runtime.registration_profile_name()`
	# @used-by :func:`agent_tools.runtime.resolve_antigravity_paths()`
	# @used-by :func:`agent_tools.runtime.resolve_codex_home()`
	# @used-by :func:`agent_tools.runtime.resolve_codex_paths()`
	# @used-by :func:`agent_tools.runtime.role_settings()`
	# @used-by :func:`agent_tools.runtime_cache._collect_one_session()`
	# @used-by :func:`agent_tools.runtime_cache._compute_addon_roots()`
	# @used-by :func:`agent_tools.runtime_cache._compute_browser_perimeter()`
	# @used-by :func:`agent_tools.runtime_cache._extract_platform_addon_roots()`
	# @used-by :func:`agent_tools.runtime_cache._load_uncached_settings()`
	# @used-by :func:`agent_tools.runtime_cache.cached_addon_roots()`
	# @used-by :func:`agent_tools.runtime_cache.cached_browser_perimeter()`
	# @used-by :func:`agent_tools.runtime_cache.load_cached_settings_readonly()`
	# @used-by :func:`agent_tools.runtime_cache.run_shell_violation_scan()`
	# @used-by :func:`agent_tools.runtime_snapshot._activate_release()`
	# @used-by :func:`agent_tools.runtime_snapshot.check_runtime_snapshot()`
	# @used-by :func:`agent_tools.runtime_snapshot.effective_git_hooks_dir()`
	# @used-by :func:`agent_tools.runtime_snapshot.finalize_native_install()`
	# @used-by :func:`agent_tools.schema_help._check_one_assertion()`
	# @used-by :func:`agent_tools.schema_help._valid_assertion_locator()`
	# @used-by :func:`agent_tools.schema_help._valid_comparison()`
	# @used-by :func:`agent_tools.schema_help.claim_error_hint()`
	# @used-by :func:`agent_tools.schema_help.format_schema_help_text()`
	# @used-by :func:`agent_tools.schema_help.requirement_assertion_issues()`
	# @used-by :func:`agent_tools.schema_help.schema_help_payload()`
	# @used-by :func:`agent_tools.shadow_replay._execute_finalize_reply()`
	# @used-by :func:`agent_tools.shadow_replay._find_reply_path()`
	# @used-by :func:`agent_tools.shadow_replay._run_answer_check()`
	# @used-by :func:`agent_tools.shadow_replay._run_answer_prepare()`
	# @used-by :func:`agent_tools.shadow_replay._run_finalize_stage()`
	# @used-by :func:`agent_tools.shadow_replay._run_pre_invocation()`
	# @used-by :func:`agent_tools.shadow_replay._run_review_stage()`
	# @used-by :func:`agent_tools.shadow_replay._run_stop_gate()`
	# @used-by :func:`agent_tools.shadow_replay._run_turn_begin()`
	# @used-by :func:`agent_tools.shadow_replay_clone.build_stop_transcript()`
	# @used-by :func:`agent_tools.shadow_replay_command._run_exec_rename_domain()`
	# @used-by :func:`agent_tools.shadow_replay_command._run_generic_command()`
	# @used-by :func:`agent_tools.shadow_replay_command._stage_ag_from_receipt()`
	# @used-by :func:`agent_tools.shadow_replay_command.persist_shadow_replay_receipt()`
	# @used-by :func:`agent_tools.source_grounding.detect_prose_locale()`
	# @used-by :func:`agent_tools.source_grounding.load_fact_ledger()`
	# @used-by :func:`agent_tools.source_grounding.verify_target_locale()`
	# @used-by :func:`agent_tools.statements._requests_invoke_df_analysis()`
	# @used-by :func:`agent_tools.statements.external_anchor_issues()`
	# @used-by :func:`agent_tools.stop_emergency_capture._find_target_turn()`
	# @used-by :func:`agent_tools.stop_emergency_capture._record_emergency_locked()`
	# @used-by :func:`agent_tools.stop_emergency_capture.maybe_emergency_capture_journal()`
	# @used-by :func:`agent_tools.stop_hook_guard._evaluate_continuation_reentry()`
	# @used-by :func:`agent_tools.stop_hook_guard._failure_fingerprint()`
	# @used-by :func:`agent_tools.stop_hook_guard._guard_file_path()`
	# @used-by :func:`agent_tools.stop_hook_guard._is_continuation_reentry()`
	# @used-by :func:`agent_tools.stop_hook_guard._max_segment_step()`
	# @used-by :func:`agent_tools.stop_hook_guard.apply_continuation_guard()`
	# @used-by :func:`agent_tools.stop_hook_guard.extract_stop_context()`
	# @used-by :func:`agent_tools.stop_hook_guard.handoff_matches_user_step()`
	# @used-by :func:`agent_tools.stop_hook_guard.is_journal_opt_out()`
	# @used-by :func:`agent_tools.stop_subagent_check._apply_call()`
	# @used-by :func:`agent_tools.stop_subagent_check._collect_invoke_outputs()`
	# @used-by :func:`agent_tools.stop_subagent_check._filter_turn_db_rows()`
	# @used-by :func:`agent_tools.stop_subagent_check._is_row_running()`
	# @used-by :func:`agent_tools.stop_subagent_check._process_manage_subagents()`
	# @used-by :func:`agent_tools.stop_subagent_check._process_row_calls()`
	# @used-by :func:`agent_tools.stop_subagent_check._process_row_message()`
	# @used-by :func:`agent_tools.stop_subagent_check._read_turn_segment()`
	# @used-by :func:`agent_tools.stop_subagent_check._record_invoke()`
	# @used-by :func:`agent_tools.stop_subagent_check.evaluate_schedule_subagent_block()`
	# @used-by :func:`agent_tools.stop_subagent_check.has_running_subagents()`
	# @used-by :func:`agent_tools.storage._should_skip_fsync()`
	# @used-by :func:`agent_tools.suite_runner.format_text_report()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_c._c_like_comment_step()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_c._c_like_special_step()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_c._c_like_string_step()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_c.lex_c_like()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_script._hash_block_step()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_script._hash_comment_allowed()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_script._hash_here_or_regex()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_script._hash_quote_step()`
	# @used-by :func:`agent_tools.tdd.comment_lexers_script._hash_step()`
	# @used-by :func:`agent_tools.tdd.diff_coverage._touched_git_repos()`
	# @used-by :func:`agent_tools.tdd.diff_coverage.enrich_tdd_check_report()`
	# @used-by :func:`agent_tools.tdd.diff_coverage.run_trace_diff_coverage()`
	# @used-by :func:`agent_tools.tdd.enforcement._eval_pre_code_write()`
	# @used-by :func:`agent_tools.tdd.enforcement._eval_pre_prod_write()`
	# @used-by :func:`agent_tools.tdd.enforcement._eval_pre_write()`
	# @used-by :func:`agent_tools.tdd.enforcement._eval_shell_prod_writes()`
	# @used-by :func:`agent_tools.tdd.enforcement._eval_test_ratchet_and_fitting()`
	# @used-by :func:`agent_tools.tdd.enforcement._load_pre_tool_tdd_state()`
	# @used-by :func:`agent_tools.tdd.enforcement._resolve_new_text()`
	# @used-by :func:`agent_tools.tdd.enforcement.evaluate_pre_tool_use_tdd()`
	# @used-by :func:`agent_tools.tdd.evaluator._apply_command_event()`
	# @used-by :func:`agent_tools.tdd.evaluator._apply_file_write_event()`
	# @used-by :func:`agent_tools.tdd.evaluator._apply_prod_file_event()`
	# @used-by :func:`agent_tools.tdd.evaluator._command_matches_scope()`
	# @used-by :func:`agent_tools.tdd.evaluator._order_tdd_events()`
	# @used-by :func:`agent_tools.tdd.evaluator._update_scope_from_test_cmd()`
	# @used-by :func:`agent_tools.tdd.evaluator.evaluate_tdd_events()`
	# @used-by :func:`agent_tools.tdd.events._antigravity_segment_is_interrupted()`
	# @used-by :func:`agent_tools.tdd.events._append_command_tool_event()`
	# @used-by :func:`agent_tools.tdd.events._append_write_tool_event()`
	# @used-by :func:`agent_tools.tdd.events._collect_following_outputs()`
	# @used-by :func:`agent_tools.tdd.events._extract_row_call_events()`
	# @used-by :func:`agent_tools.tdd.events._record_bg_task_completion()`
	# @used-by :func:`agent_tools.tdd.events._scan_segment_calls()`
	# @used-by :func:`agent_tools.tdd.events._scan_segment_status_row()`
	# @used-by :func:`agent_tools.tdd.events._select_active_segment()`
	# @used-by :func:`agent_tools.tdd.events.extract_antigravity_tdd_events()`
	# @used-by :func:`agent_tools.tdd.mechanical._compile_recipe_regex()`
	# @used-by :func:`agent_tools.tdd.mechanical._line_matches_recipe()`
	# @used-by :func:`agent_tools.tdd.mechanical._load_recipe_entries()`
	# @used-by :func:`agent_tools.tdd.mechanical._recipe_matches_repo()`
	# @used-by :func:`agent_tools.tdd.mechanical.record_mechanical_exemption()`
	# @used-by :func:`agent_tools.tdd.ratchet._find_receipt_ratchet_approval()`
	# @used-by :func:`agent_tools.tdd.ratchet._load_receipt_file()`
	# @used-by :func:`agent_tools.tdd.ratchet._match_issue_evidence_file()`
	# @used-by :func:`agent_tools.tdd.ratchet.ratchet_diff_violations()`
	# @used-by :func:`agent_tools.tdd.service_exempt.is_service_finalization_call()`
	# @used-by :func:`agent_tools.text_browser._endpoint_with_meta()`
	# @used-by :func:`agent_tools.text_browser._node_binary()`
	# @used-by :func:`agent_tools.text_browser._poll_dom_on_session()`
	# @used-by :func:`agent_tools.text_browser._profile()`
	# @used-by :func:`agent_tools.text_browser._query_target_infos()`
	# @used-by :func:`agent_tools.text_browser._session()`
	# @used-by :func:`agent_tools.text_browser._verify_context_anchor()`
	# @used-by :func:`agent_tools.text_browser.browser_anchor_status()`
	# @used-by :func:`agent_tools.text_browser.collect_cdp_dom()`
	# @used-by :func:`agent_tools.text_browser.collect_headless_dom()`
	# @used-by :func:`agent_tools.text_browser.discover_cdp_browser()`
	# @used-by :func:`agent_tools.text_browser.operation()`
	# @used-by :func:`agent_tools.text_browser.preflight()`
	# @used-by :func:`agent_tools.text_browser.probe_cdp_arguments()`
	# @used-by :func:`agent_tools.text_browser.resolve_cdp_port()`
	# @used-by :func:`agent_tools.text_browser.resolve_headless_shell()`
	# @used-by :func:`agent_tools.text_claims.evidence_inputs()`
	# @used-by :func:`agent_tools.text_claims.primary_numbers()`
	# @used-by :func:`agent_tools.text_claims.save_registry()`
	# @used-by :func:`agent_tools.text_claims.subset()`
	# @used-by :func:`agent_tools.text_claims.validate_map()`
	# @used-by :func:`agent_tools.text_cli.main()`
	# @used-by :func:`agent_tools.text_core.check_prose()`
	# @used-by :func:`agent_tools.text_core.default_shell()`
	# @used-by :func:`agent_tools.text_core.find_bans()`
	# @used-by :func:`agent_tools.text_core.replay()`
	# @used-by :func:`agent_tools.text_review._source_reviews()`
	# @used-by :func:`agent_tools.text_review._state()`
	# @used-by :func:`agent_tools.text_review.approval_integrity()`
	# @used-by :func:`agent_tools.text_review.authorize()`
	# @used-by :func:`agent_tools.text_review.prepare()`
	# @used-by :func:`agent_tools.text_review.read_package()`
	# @used-by :func:`agent_tools.text_review.record()`
	# @used-by :func:`agent_tools.text_sections.lint_document()`
	# @used-by :func:`agent_tools.text_sections.mechanical_projection()`
	# @used-by :func:`agent_tools.text_sections.scope_blocks()`
	# @used-by :func:`agent_tools.text_sources._evaluate()`
	# @used-by :func:`agent_tools.text_sources.read_source_check()`
	# @used-by :func:`agent_tools.text_sources.save_source_check()`
	# @used-by :func:`agent_tools.text_sources.source_integrity()`
	# @used-by :func:`agent_tools.text_workflow._find_registered()`
	# @used-by :func:`agent_tools.text_workflow.verify_integrity()`
	# @used-by :func:`agent_tools.turn_routing._collect_turn_candidates()`
	# @used-by :func:`agent_tools.turn_routing._extract_user_text()`
	# @used-by :func:`agent_tools.turn_routing._handoff_rank()`
	# @used-by :func:`agent_tools.turn_routing._match_tier()`
	# @used-by :func:`agent_tools.turn_routing._select_best_turn_candidate()`
	# @used-by :func:`agent_tools.turn_routing._state_rank()`
	# @used-by :func:`agent_tools.turn_routing.resolve_handoff_target_root()`
	# @used-by :func:`agent_tools.upwork_data._extract_xlsx_markdown()`
	# @used-by :func:`agent_tools.upwork_data._parse_pdf_streams()`
	# @used-by :func:`agent_tools.upwork_data.collect_unique_public_past_jobs()`
	# @used-by :func:`agent_tools.upwork_data.detect_client_videos()`
	# @used-by :func:`agent_tools.upwork_data.discover_pdf_ligature_repairs()`
	# @used-by :func:`agent_tools.upwork_data.extract_client_names()`
	# @used-by :func:`agent_tools.upwork_data.extract_loom_video()`
	# @used-by :func:`agent_tools.upwork_data.format_kb_project_md()`
	# @used-by :func:`agent_tools.upwork_extract._eval_session()`
	# @used-by :func:`agent_tools.upwork_extract.decode_page()`
	# @used-by :func:`agent_tools.upwork_extract.download_attachment()`
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :func:`agent_tools.upwork_extract.select_tab()`
	# @used-by :func:`agent_tools.upwork_project._has_entry()`
	# @used-by :func:`agent_tools.upwork_project.antigravity_global_config_dirs()`
	# @used-by :func:`agent_tools.upwork_project.check_configuration()`
	# @used-by :func:`agent_tools.upwork_project.configure_project()`
	# @used-by :func:`agent_tools.upwork_project.doctor()`
	# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
	# @used-by :func:`agent_tools.upwork_project.run()`
	# @used-by :func:`agent_tools.verification_observability._classify_shadow_output()`
	# @used-by :func:`agent_tools.verification_observability._closed_issues_after()`
	# @used-by :func:`agent_tools.verification_observability._cmd_from_call()`
	# @used-by :func:`agent_tools.verification_observability._inspect_shadow_call()`
	# @used-by :func:`agent_tools.verification_observability._latest_unresolved_failure()`
	# @used-by :func:`agent_tools.verification_observability._resolve_bg_shadow_runs()`
	# @used-by :func:`agent_tools.verification_observability._row_outputs()`
	# @used-by :func:`agent_tools.verification_observability.detect_shadow_replay_runs()`
	# @used-by :func:`agent_tools.verification_observability.evaluate_verification_observability()`
	# @used-by :func:`agent_tools.workflow._target_complete()`
	# @used-by :func:`agent_tools.worktree_flow._enrich_worktree_entry()`
	# @used-by :func:`agent_tools.worktree_flow._post_merge_checks()`
	# @used-by :func:`agent_tools.worktree_flow._push_and_finish_land()`
	# @used-by :func:`agent_tools.worktree_flow._run_land_checks()`
	# @used-by :func:`agent_tools.worktree_flow._run_land_tests()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_status()`
	# @used-by :func:`agent_tools.worktree_guard._parse_process_row()`
	# @used-by :func:`agent_tools.xref.format_xref_text()`
	# @used-by :func:`agent_tools.xref.java_graph._add_external_entry_edges()`
	# @used-by :func:`agent_tools.xref.java_graph._infer_external_override()`
	# @used-by :func:`agent_tools.xref.java_graph._link_fallback_unique_method()`
	# @used-by :func:`agent_tools.xref.java_graph._link_java_base_method()`
	# @used-by :func:`agent_tools.xref.java_graph._link_super_method()`
	# @used-by :func:`agent_tools.xref.java_graph._matching_methods_on_type()`
	# @used-by :func:`agent_tools.xref.java_graph._scan_java_token()`
	# @used-by :func:`agent_tools.xref.java_graph.find_java_overridden_method()`
	# @used-by :func:`agent_tools.xref.java_sync._check_java_def()`
	# @used-by :func:`agent_tools.xref.java_sync._sync_java_def_edit()`
	# @used-by :func:`agent_tools.xref.java_tags._shorten_java_type()`
	# @used-by :func:`agent_tools.xref.js_graph._link_js_class_member()`
	# @used-by :func:`agent_tools.xref.js_graph._record_js_word_ref()`
	# @used-by :func:`agent_tools.xref.js_graph._record_obj_member_call()`
	# @used-by :func:`agent_tools.xref.js_graph._resolve_js_class()`
	# @used-by :func:`agent_tools.xref.js_graph._resolve_js_ns_class()`
	# @used-by :func:`agent_tools.xref.js_graph._scan_js_inline_require()`
	# @used-by :func:`agent_tools.xref.js_graph._try_record_class_member()`
	# @used-by :func:`agent_tools.xref.js_graph.find_js_overridden_method()`
	# @used-by :func:`agent_tools.xref.js_sync._check_js_def()`
	# @used-by :func:`agent_tools.xref.js_sync._sync_js_def_edit()`
	# @used-by :func:`agent_tools.xref.js_tags._format_cross_file_symbol()`
	# @used-by :func:`agent_tools.xref.js_tags._resolve_member_in_file()`
	# @used-by :func:`agent_tools.xref.python_graph._add_method_framework_edges()`
	# @used-by :func:`agent_tools.xref.python_graph._link_super_member()`
	# @used-by :func:`agent_tools.xref.python_graph._link_unique_or_typed_attr()`
	# @used-by :func:`agent_tools.xref.python_graph._resolve_call_class()`
	# @used-by :func:`agent_tools.xref.python_graph._step_reexport()`
	# @used-by :func:`agent_tools.xref.python_overrides.find_overridden_method()`
	# @used-by :func:`agent_tools.xref.python_overrides.is_unittest_testcase_subclass()`
	# @used-by :func:`agent_tools.xref.python_sync._check_def_xref()`
	# @used-by :func:`agent_tools.xref.python_sync._override_base_for_def()`
	# @used-by :func:`agent_tools.xref.python_sync._sync_def_edit()`
	# @used-by :func:`agent_tools.xref.python_tags._resolve_module_attr_in_repo()`
	# @used-by :func:`agent_tools.xref.python_tags.collect_file_uses()`
	# @used-by :func:`agent_tools.xref.run_xref_check()`
	# @used-by :func:`agent_tools.xref.run_xref_sync()`
	# @used-by :func:`check_markdown_slop._check_turn_budget_gate()`
	# @used-by :func:`check_markdown_slop._evaluate_payload()`
	# @used-by :func:`check_markdown_slop._resolve_markdown_content()`
	# @used-by :func:`check_pre_invocation._binding_violation_message()`
	# @used-by :func:`check_pre_invocation._format_turn_begin_message()`
	# @used-by :func:`check_pre_invocation._resolve_ag_paths()`
	# @used-by :func:`check_pre_invocation._resolve_pre_invocation_target()`
	# @used-by :func:`check_pre_invocation._resolve_root()`
	# @used-by :func:`check_pre_invocation._turn_step_already_covered()`
	# @used-by :func:`check_pre_invocation.evaluate_pre_invocation_payload()`
	# @used-by :func:`check_rules_and_server_gate.__getattr__()`
	# @used-by :func:`check_rules_and_server_gate._apply_failfast()`
	# @used-by :func:`check_rules_and_server_gate._evaluate_payload()`
	# @used-by :func:`check_stop_gate._evaluate_prepared_match()`
	# @used-by :func:`check_stop_gate._resolve_stop_paths()`
	# @used-by :func:`check_stop_gate.evaluate_stop_payload()`
	# @used-by :func:`dom_fixture()`
	# @used-by :func:`git_shim.prepare_git_invocation()`
	# @used-by :func:`git_shim.resolve_system_git()`
	# @used-by :func:`test_contract_invariants._run_routing_parity_case()`
	# @used-by :func:`test_evidence_contract.v3_analysis()`
	# @used-by :func:`test_hook_runner_e2e_budget._configured_rules_gate_timeout()`
	# @used-by :func:`test_project_domain_drift._complete_review_and_prepare()`
	# @used-by :func:`test_upwork_init_e2e._run_turn1_init_and_review()`
	# @used-by :meth:`NativeFixture.call()`
	# @used-by :meth:`TextBrowserTests.test_collect_browser_never_hijacks_open_user_tab_without_tab_id_and_uses_hidden_target()`
	# @used-by :meth:`TextBrowserTests.test_collect_http_auto_fallback_to_browser_on_reddit_js_challenge_shell()`
	# @used-by :meth:`TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
	# @used-by :meth:`TextBrowserTests.test_dom_collector_does_not_issue_content_proof_if_browser_identity_changes()`
	# @used-by :meth:`TextBrowserTests.test_m1_live_headless_shell_public_isolation_and_h_chs_6_static_skip()`
	# @used-by :meth:`TextBrowserTests.test_m2a_extension_manifest_key_and_multi_profile_tab_broker_isolation()`
	# @used-by :meth:`TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator.__init__()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._add()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._check_claim_arguments()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._check_claim_dependencies_and_caps()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._check_claim_structure()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._check_counterevidence_cap()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._check_cycles()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._check_primary_evidence_list()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._has_http_dns_error()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._inherited()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._load_direct_evidence()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._verify_claim_evidence()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._verify_scope_coverage()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator.evidence_issues()`
	# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner.__init__()`
	# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner._apply_removal()`
	# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner._inspect_candidate()`
	# @used-by :meth:`agent_tools.cleanup.ProjectCleanupScanner._recover_preserved()`
	# @used-by :meth:`agent_tools.completion.AnswerPreparationRunner._authorize_and_sync_workflow()`
	# @used-by :meth:`agent_tools.completion.AnswerPreparationRunner._check_turn_hygiene()`
	# @used-by :meth:`agent_tools.completion.AnswerPreparationRunner._verify_delivered_fast_path()`
	# @used-by :meth:`agent_tools.completion.TurnJournalReconciler._build_delivery()`
	# @used-by :meth:`agent_tools.completion.TurnJournalReconciler._cleanup_adopted_conflict()`
	# @used-by :meth:`agent_tools.completion.TurnJournalReconciler._reconcile_turn()`
	# @used-by :meth:`agent_tools.completion.TurnJournalReconciler._resolve_effective_response()`
	# @used-by :meth:`agent_tools.completion.TurnJournalReconciler.run()`
	# @used-by :meth:`agent_tools.diagnostics.ValidationError.__init__()`
	# @used-by :meth:`agent_tools.experiments.BrowserTraceInspector._extract_identity_dict()`
	# @used-by :meth:`agent_tools.experiments.BrowserTraceInspector._iter_identity_objects()`
	# @used-by :meth:`agent_tools.experiments.BrowserTraceInspector.context_issues()`
	# @used-by :meth:`agent_tools.experiments.BrowserTraceInspector.event_actions()`
	# @used-by :meth:`agent_tools.experiments.BrowserTraceInspector.event_browser_identity()`
	# @used-by :meth:`agent_tools.experiments.BrowserTraceInspector.extract_verified_country()`
	# @used-by :meth:`agent_tools.experiments.BrowserTraceInspector.native_geolocation()`
	# @used-by :meth:`agent_tools.experiments.BrowserTraceInspector.native_tool_name()`
	# @used-by :meth:`agent_tools.experiments.ExperimentPlanStore._is_plan_commit()`
	# @used-by :meth:`agent_tools.experiments.ExperimentPlanStore.load()`
	# @used-by :meth:`agent_tools.experiments.ExperimentPlanStore.preregistration_issues()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.__init__()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._check_admin_run()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._check_browser_scenario_steps()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._check_conditions()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._check_serp_run()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._collector_artifact()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._ingest_artifacts_and_trace()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._verify_saved_artifacts()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.capabilities()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.evaluate_assertions()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.load()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.record()`
	# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.run_issues()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_ready_for_close()`
	# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_workflow()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._bind_issue_repos()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._check_comments_evidence()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._check_issue_file_evidence()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._check_multi_subtask_decomposition()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._check_turn_issue_evidence()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._collect_repos_and_issues()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._extract_saved_parent()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._flag_unclosed_completed_parents()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._flag_unparented_multi_commits()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._lint_saved_issue_obj()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._resolve_parent_number()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._verify_required_repo_issues()`
	# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor.collect_turn_issues()`
	# @used-by :meth:`agent_tools.issues.git_read_cache.RepoReadCache.dirty_referencing_issue()`
	# @used-by :meth:`agent_tools.issues.git_read_cache.RepoReadCache.find_commit_for_issue()`
	# @used-by :meth:`agent_tools.issues.git_read_cache.RepoReadCache.latest_commit_urls_for_files()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._build_mutation_success_payload()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._edit_parent_only()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._execute_create()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._execute_edit()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._finalize_close()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._load_cached_parent_issue()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._post_close_comment()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._prepend_issue_metadata()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._verify_mutation_readback()`
	# @used-by :meth:`agent_tools.issues.service.GitHubIssueService.verify_and_persist_parent_issue()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._build_issue_record()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._collect_child_issue_file()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._scan_open_turn_files()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._update_single_turn_locked()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.evidence_issue_state()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.find_existing_issue_comments()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.load_saved_issue_container_text()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.persist_issue_evidence()`
	# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.saved_issue_parent_number()`
	# @used-by :meth:`agent_tools.knowledge.AttachmentInventory._evidence_entries()`
	# @used-by :meth:`agent_tools.knowledge.AttachmentInventory.sync()`
	# @used-by :meth:`agent_tools.links.HTMLReferences.handle_starttag()`
	# @used-by :meth:`agent_tools.path_registry.PathRegistry.__init__()`
	# @used-by :meth:`agent_tools.path_registry.PathRegistry._resolve_profile_chain()`
	# @used-by :meth:`agent_tools.path_registry.ProjectPaths.__init__()`
	# @used-by :meth:`agent_tools.path_registry.ProjectPaths.similar_projects()`
	# @used-by :meth:`agent_tools.platforms.antigravity.AntigravityTurnScanner._collect_outputs()`
	# @used-by :meth:`agent_tools.platforms.antigravity.AntigravityTurnScanner._finalize_segment()`
	# @used-by :meth:`agent_tools.platforms.antigravity.AntigravityTurnScanner._load_context()`
	# @used-by :meth:`agent_tools.platforms.antigravity.AntigravityTurnScanner._record_subagent_calls()`
	# @used-by :meth:`agent_tools.platforms.antigravity.AntigravityTurnScanner._record_tool_calls()`
	# @used-by :meth:`agent_tools.platforms.antigravity.AntigravityTurnScanner._scan_segment()`
	# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._collect_subagent_bfs()`
	# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._finalize_turn()`
	# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._index_profile_subagents()`
	# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._load_context()`
	# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._resolve_subagent_child()`
	# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._scan_primary_turns()`
	# @used-by :meth:`agent_tools.platforms.codex.CodexTurnScanner._visit_subagent_rows()`
	# @used-by :meth:`agent_tools.research.HTMLData.handle_starttag()`
	# @used-by :meth:`agent_tools.research.HTMLData.result()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._collect_client_urls()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._ingest_evidence_files()`
	# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._ingest_json_observations()`
	# @used-by :meth:`agent_tools.review.ReviewClassifier.__init__()`
	# @used-by :meth:`agent_tools.review.ReviewClassifier._check_omitted_stage_claims()`
	# @used-by :meth:`agent_tools.review.ReviewClassifier._evaluate_claim_risk()`
	# @used-by :meth:`agent_tools.review.ReviewClassifier._resolve_claim()`
	# @used-by :meth:`agent_tools.review.ReviewClassifier._validate_spec()`
	# @used-by :meth:`agent_tools.review.ReviewClassifier.classify()`
	# @used-by :meth:`agent_tools.review.ReviewClassifier.has_significant_flags()`
	# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.approval_current()`
	# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.approved_claim_digests()`
	# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.entry_proof_current()`
	# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.findings_closed()`
	# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.has_unhandled_verdicts()`
	# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.latest_for_subject()`
	# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.quorum_satisfied()`
	# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.select_authorized_group()`
	# @used-by :meth:`agent_tools.review.ReviewQuorumEvaluator.significant_findings()`
	# @used-by :meth:`agent_tools.review.ReviewReportValidator.__init__()`
	# @used-by :meth:`agent_tools.review.ReviewReportValidator._check_alignment_and_outcome()`
	# @used-by :meth:`agent_tools.review.ReviewReportValidator._check_claim_reviews()`
	# @used-by :meth:`agent_tools.review.ReviewReportValidator._check_disproved_claim()`
	# @used-by :meth:`agent_tools.review.ReviewReportValidator._check_falsifier()`
	# @used-by :meth:`agent_tools.review.ReviewReportValidator._check_findings()`
	# @used-by :meth:`agent_tools.review.ReviewReportValidator._check_text_checks()`
	# @used-by :meth:`agent_tools.review.ReviewReportValidator.is_falsifier_report()`
	# @used-by :meth:`agent_tools.shell_audit.ShellCommandInspector.extract_issue_actions()`
	# @used-by :meth:`agent_tools.source_grounding.LocalSourceGroundingAuditor._load_ledger_tuples()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex._ensure_disk_loaded()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex._persist_if_dirty()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.discover_entities()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.ensure_entry()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.for_root()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.load_source_info()`
	# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.sync_ledger()`
	# @used-by :meth:`agent_tools.text_browser.CDPSession.__enter__()`
	# @used-by :meth:`agent_tools.text_browser.CDPSession.attach_target()`
	# @used-by :meth:`agent_tools.text_browser.CDPSession.send()`
	# @used-by :meth:`agent_tools.text_browser.GuardedCDP._broker_create_tab()`
	# @used-by :meth:`agent_tools.text_browser.GuardedCDP._broker_remove_tab()`
	# @used-by :meth:`agent_tools.text_browser.GuardedCDP.call()`
	# @used-by :meth:`agent_tools.text_browser.GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`agent_tools.text_browser.GuardedCDP.create_target()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._apply_native_toml_data()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._check_native_overrides()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._check_rule_and_skill_divergence()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._check_skill_candidates()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._discover_references()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._populate_source_metadata()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_canonical_sources()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_codex_profiles()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_discovery_manifests()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._verify_projection_receipt()`
	# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner.run()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace._check_replay()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace._gate_target()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace._validate_begin_spec()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.apply()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.begin()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.check()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.index()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.operation_meta()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.read_check()`
	# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.scope_issues()`
	# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.applied_integrity()`
	# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.claim_snapshot()`
	# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.reconciled_integrity()`
	# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.verify()`
	# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.verify_applied_successor()`
	# @used-by :meth:`agent_tools.upwork_data.DocxMarkdownExtractor._extract_paragraph_text()`
	# @used-by :meth:`agent_tools.upwork_data.DocxMarkdownExtractor._load_numbering()`
	# @used-by :meth:`agent_tools.upwork_data.DocxMarkdownExtractor._load_relationships()`
	# @used-by :meth:`agent_tools.upwork_data.DocxMarkdownExtractor._parse_paragraph()`
	# @used-by :meth:`agent_tools.upwork_data.PdfMarkdownExtractor._collect_visual_lines()`
	# @used-by :meth:`agent_tools.upwork_data.PdfMarkdownExtractor._detect_bold_fonts()`
	# @used-by :meth:`agent_tools.upwork_data.PdfMarkdownExtractor._extract_from_raw_streams()`
	# @used-by :meth:`agent_tools.upwork_extract.RPC.call()`
	# @used-by :meth:`agent_tools.upwork_extract.RPC.evaluate()`
	# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor._analysis_card_issues()`
	# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor._load_snapshot()`
	# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor.attachment_issues()`
	# @used-by :meth:`agent_tools.workflow.ResearchQuestionRegistry._apply_search()`
	# @used-by :meth:`agent_tools.workflow.ResearchQuestionRegistry.contract_issues()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._apply_adopt()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._apply_resume()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._apply_unadopt()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._finalize_stage()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._resolve_receipt_artifact()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.adopt_requests()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.load()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.publish_progress()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.receipt_current()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.record_current_answer()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.registration_status()`
	# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.stage_statuses()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	# @used-by :meth:`test_analysis_workflow.MetricsTests.test_collect_http_positional_batch_extract_profile_and_14_url_evidence_query()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_void_elements_compact_extracted_disk_json_and_max_bytes_guard()`
	# @used-by :meth:`test_analysis_workflow.ProjectCase.review_package()`
	# @used-by :meth:`test_ask_question_clarifications_m8.AskQuestionClarificationsM8Tests.test_antigravity_scanner_and_turn_state_preserve_clarifications_without_breaking_user_turns()`
	# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_answer_check_and_prepare_reject_misaligned_pending_without_writing_journal()`
	# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.test_blocked_report_records_journal_despite_hygiene_failures_and_allows_doc5()`
	# @used-by :meth:`test_blocked_report_m2.BlockedReportM2Tests.test_blocked_report_records_journal_without_closing_workflow_or_allowing_finalize()`
	# @used-by :meth:`test_cleanup.CleanupTests.control()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_new_chat_restores_a_partially_held_codex_project()`
	# @used-by :meth:`test_cleanup.CleanupTests.test_pending_sibling_restores_full_folder_ancestry_after_other_project_pruned_it()`
	# @used-by :meth:`test_cli_command_grounding.CliCommandGroundingTests.test_answer_check_blocks_unverified_and_allows_shadow_replay_or_disclaimer()`
	# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
	# @used-by :meth:`test_df_article.LexiconAndProjectionTests.test_lexicon_entries_are_complete_and_compile()`
	# @used-by :meth:`test_diff_coverage_gate.DiffCoverageGateTests.test_run_trace_diff_coverage_handles_timeout_gracefully()`
	# @used-by :meth:`test_doc5_context_trigger.Doc5ContextTriggerTests.test_active_turn_cli_failure_plus_new_parent_issue_forces_doc5_four_tracks()`
	# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_malformed_properties_and_dependency_keep_field_diagnostics_in_cli()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_actual_exec_wrapper_with_nested_shell_plan_receipt_is_supported()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_actual_namespaced_cua_read_is_recognized_but_text_header_does_not_prove_identity()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_canonical_harness_cli_plan_commit_receipt_is_supported()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_conflicting_native_action_parameter_and_output_identity_is_unknown()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_context_or_session_difference_is_rejected_even_for_same_tab_ids()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_egress_must_be_measured_in_the_actual_action_browser_context()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_explicit_native_primitives_with_same_context_remain_supported()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_false_branch_loops_definitions_and_dynamic_scripts_never_prove_executed_click()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_missing_native_identity_cannot_be_repaired_by_declared_session()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_native_before_and_action_in_different_browser_tabs_are_rejected()`
	# @used-by :meth:`test_failfast_and_schedule_gate.FailFastAndScheduleGateTests.test_pre_tool_use_blocks_redundant_schedule_timer_over_run_command()`
	# @used-by :meth:`test_failfast_and_schedule_gate.FailFastAndScheduleGateTests.test_pre_tool_use_denies_multi_segment_test_command_without_failfast()`
	# @used-by :meth:`test_failfast_and_schedule_gate.FailFastAndScheduleGateTests.test_pre_tool_use_overwrites_single_segment_test_commands_and_low_wait_ms()`
	# @used-by :meth:`test_failfast_and_schedule_gate.FailFastAndScheduleGateTests.test_tdd_gate_records_non_failfast_full_suite_warning_without_breaking_verified()`
	# @used-by :meth:`test_falsifier_default_send_message_and_schedule_m8.FalsifierDefaultSendMessageAndScheduleM8Tests.test_significant_prepare_review_defaults_to_falsifier_and_authorizes_single_auditor()`
	# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
	# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_rolls_back_finalized_fixture_on_review_authorize_regression()`
	# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_create_prepends_tab_indented_json_metadata_header_and_supports_opt_out()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_legacy_record_has_visible_proof_gap_and_unchanged_history()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_proof_evidence_review_document_and_journal_changes_remain_conflicts()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_real_pre_change_legacy_conflict_remains_conflict_permanently()`
	# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_real_pre_change_legacy_record_reports_legacy_proof_gap_and_remains_stable()`
	# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_disabled_codex_is_skipped_in_registration_workflow_cleanup_install_and_diagnostics()`
	# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_post_checkpoint_res_citation_and_issue48_recursive_subagent_aggregation()`
	# @used-by :meth:`test_issue_close_acceptance.IssueCloseAcceptanceTests.test_close_requires_fresh_passing_receipt_for_upwork_init_and_allows_ordinary_issue()`
	# @used-by :meth:`test_issue_close_acceptance.IssueCloseAcceptanceTests.test_close_requires_passing_shadow_replay_for_new_cli_command()`
	# @used-by :meth:`test_issue_decomposition.IssueDecompositionTests.test_issue_markdown_linter_and_service_classes_exist()`
	# @used-by :meth:`test_issue_first_pre_tool_use.IssueFirstPreToolUseGateTests.test_blocks_tests_production_docs_and_shell_writes_before_parent_issue()`
	# @used-by :meth:`test_issue_first_pre_tool_use.IssueFirstPreToolUseGateTests.test_cli_subprocess_smoke()`
	# @used-by :meth:`test_issue_first_pre_tool_use.IssueFirstPreToolUseGateTests.test_full_issue_first_then_tdd_red_green_child_and_parent_close_reset_in_live_hook()`
	# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_all_open_syncs_idle_prepared_turn()`
	# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_idle_prepared_turn_transitions_to_delivered_via_foreign_sync_and_all_open_without_mutating_journal()`
	# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_validate_step_strict_sequence_and_check_project_detect_gaps_and_orphans()`
	# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_codex_prepare_reprepare_and_unprepared_recovery_prepend_metadata()`
	# @used-by :meth:`test_onboarding.CapturedProjectTests.test_real_captures_preserve_description_port_and_curated_work()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
	# @used-by :meth:`test_portability.CodexEvidenceTests.set_review_input()`
	# @used-by :meth:`test_portability.CodexEvidenceTests.test_encrypted_assignment_or_missing_native_package_execution_cannot_prove_a_review()`
	# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_check_project_flags_domain_drift_on_folder_and_registration_mismatch()`
	# @used-by :meth:`test_project_labels.ProjectLabelValidationTests.test_init_cli_domain_records_domain_label_kind()`
	# @used-by :meth:`test_project_labels.ProjectLabelValidationTests.test_init_cli_legacy_topic_via_domain_warns_and_marks_provisional()`
	# @used-by :meth:`test_project_labels.ProjectLabelValidationTests.test_init_cli_topic_records_provisional_topic_label_kind()`
	# @used-by :meth:`test_project_rename.ProjectRenameTests.test_save_and_render_analysis_promote_domain_flag()`
	# @used-by :meth:`test_project_rename_verification.ProjectRenameVerificationTests.test_auto_detects_sibling_init_launcher_without_flag()`
	# @used-by :meth:`test_project_rename_verification.ProjectRenameVerificationTests.test_post_verify_rolls_back_all_state_on_stage_or_review_regression()`
	# @used-by :meth:`test_pytest_xdist_runner.PytestXdistRunnerTests.test_classify_pytest_xdist_full_suite_and_filtered()`
	# @used-by :meth:`test_pytest_xdist_runner.PytestXdistRunnerTests.test_conftest_adds_scripts_and_tests_paths_and_sets_default_no_fsync()`
	# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_snapshot_promotion_and_auditor_reject_undefined_global()`
	# @used-by :meth:`test_resume_exports.ResumeExportTests.test_multiple_exact_requests_share_one_answer_and_adoption_does_not_duplicate()`
	# @used-by :meth:`test_review_contract_package_and_paths_m6.ReviewContractPackageAndPathsM6Tests.test_report_contract_and_validator_require_package_envelope_keys()`
	# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_authorize_deduplicates_evidence_issues_across_check_project()`
	# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_ensure_hooks_uses_deployed_immutable_git_hooks_dir()`
	# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_validators_emit_actionable_hints()`
	# @used-by :meth:`test_snapshot_canary_and_hook_crash_audit.SnapshotCanaryAndHookCrashAuditTests.test_promote_rejects_chatty_pre_tool_use_snapshot_and_keeps_current()`
	# @used-by :meth:`test_snapshot_canary_and_hook_crash_audit.SnapshotCanaryAndHookCrashAuditTests.test_promote_rejects_slow_pre_tool_use_snapshot_and_keeps_current()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids()`
	# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
	# @used-by :meth:`test_stop_emergency_capture_and_foreign_sync.StopEmergencyCaptureAndForeignSyncTests.test_stop_gate_fail_open_persists_emergency_capture_and_sync_avoids_duplicate()`
	# @used-by :meth:`test_tdd_pre_tool_use.TddPreToolUseGateTests.test_blocks_production_code_across_languages_before_red_test()`
	# @used-by :meth:`test_tdd_pre_tool_use.TddPreToolUseGateTests.test_cli_subprocess_smoke()`
	# @used-by :meth:`test_tdd_pre_tool_use.TddPreToolUseGateTests.test_ratchet_anti_fitting_substantive_and_behavioral_test_guards()`
	# @used-by :meth:`test_tdd_pre_tool_use.TddPreToolUseGateTests.test_shell_write_bypass_and_test_deletion_blocked()`
	# @used-by :meth:`test_text_diagnostics.TextDiagnosticsTests.test_profile_instructions_are_separate_candidates_without_guessing_active_account()`
	# @used-by :meth:`test_text_workflow.TextWorkspaceCase.start()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_antigravity_journal_conversation_auto_titling_and_comma_append()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_compaction_index_offload_stdout_bounds_delivery_cleanup_and_dry_run_non_bypass()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_pre_invocation_hook_idempotent_turn_begin_child_skip_terminate_and_dry_run()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_registered_empty_launcher_project_tracks_pre_init_failures_and_hands_off_to_daily_project()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_similar_projects_parity_gate_stop_hook_pre_invocation_and_exemption()`
	# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_post_finalize_turn_with_adopted_request_skips_authorize_when_non_substantive()`
	# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_recover_turn_violation_unblocks_prepare_and_gate_blocks_direct_journal_writes()`
	# @used-by :meth:`test_turn_completion.CompletionCase.test_changed_prepared_bytes_and_new_uncovered_request_do_not_overwrite()`
	# @used-by :meth:`test_turn_routing_and_handoff_m6.TurnRoutingAndHandoffM6Tests.test_pre_invocation_allows_new_job_in_launcher_instead_of_routing()`
	# @used-by :meth:`test_turn_routing_and_handoff_m6.TurnRoutingAndHandoffM6Tests.test_pre_invocation_routes_turn2_handed_off_to_daily_without_launcher_orphan()`
	# @used-by :meth:`test_upwork_data.UpworkDataExtractorTests.test_pdf_extractor_xml_layout_and_raw_stream_ligature_fallback()`
	# @used-by :mod:`agent_tools.completion`
	# @used-by :mod:`agent_tools.gates.answer_checks`
	# @used-by :mod:`agent_tools.platforms.antigravity`
	# @used-by :mod:`agent_tools.runtime`
	def get(self, url):
		if url.endswith('/json/version'):
			r = {'Browser': 'Fixture/1', 'webSocketDebuggerUrl': self.browser}
		elif url.endswith('/json/list'):
			r = deepcopy(self.targets)
		else:
			raise AssertionError(url)
		return r
	# @used-by :func:`dom_fixture()`
	# @used-by :meth:`TextBrowserTests.test_collect_browser_never_hijacks_open_user_tab_without_tab_id_and_uses_hidden_target()`
	# @used-by :meth:`TextBrowserTests.test_collect_http_auto_fallback_to_browser_on_reddit_js_challenge_shell()`
	# @used-by :meth:`TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
	def call(self, url, method, params):
		self.calls.append((url, method, deepcopy(params)))
		if 'Browser.getBrowserCommandLine' == method:
			if self.unavailable:
				raise RuntimeError('Command line unavailable without automation flag')
			r = {'arguments': self.arguments}
		elif 'Target.createTarget' == method:
			self.targets.append({'id': 'owned', 'type': 'page', 'url': params['url'], 'title': 'New', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/owned'})
			r = {'targetId': 'owned'}
		# 2026-10-31
		# "Extract universal harness.py CLI, add CDP browser fallback on port 9222, and harden source/quote/anchor verification in answer-prepare":
		# https://github.com/dmitry-ai/harness/issues/27
		elif 'Target.closeTarget' == method:
			tid = params.get('targetId')
			self.targets = [t for t in self.targets if t.get('id') != tid]
			r = {'success': True}
		elif 'Page.navigate' != method:
			r = {'ok': True}
		else:
			self.targets[-1]['url'] = params['url']
			r = {'frameId': 'main'}
		return r
# @used-by :meth:`TextBrowserTests.test_dom_collector_does_not_issue_content_proof_if_browser_identity_changes()`
# @used-by :meth:`TextBrowserTests.test_dom_collector_exact_url_and_guard_project_cannot_be_substituted()`
# @used-by :meth:`TextBrowserTests.test_dom_collector_requires_verified_profile_before_native_dom_evaluation()`
# @used-by :meth:`test_experiments.ExperimentTests.test_dom_is_fresh_and_never_proves_click()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_exact_dom_tab_is_read_without_inventing_http_status()`
def dom_fixture(root, url, tab_id, html):
	native = NativeFixture()
	native.targets[0].update(id=tab_id, url=url, webSocketDebuggerUrl=f'ws://127.0.0.1:9222/devtools/page/{tab_id}')
	config = {'workspace_root': str(root), 'platforms': {}, 'text': {'browser': {'sessions': {'offline-dom': {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222', 'profile': {'path': 'C:/authorized', 'argument': '--user-data-dir'}, 'target_url_patterns': [url], 'allowed_operations': ['read']}}}}}
	# @used-by :func:`dom_fixture()`
	def call(endpoint, method, params):
		if 'Runtime.evaluate' != method:
			r = native.call(endpoint, method, params)
		else:
			native.calls.append((endpoint, method, deepcopy(params)))
			r = {'result': {'type': 'object', 'value': {'url': url, 'html': html}}}
		return r
	guard = GuardedCDP(root, {'session_id': 'offline-dom', 'target_id': tab_id}, config=config, http_get=native.get, cdp_call=call)
	return (guard, native)
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
class TextBrowserTests(unittest.TestCase):
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :meth:`unittest.TestCase.setUp()`
	# @used-by :mod:`unittest`
	# @see :meth:`unittest.TestCase.setUp()`
	@override
	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp.cleanup)
		self.root = Path(self.temp.name)
		self.config = {'workspace_root': str(self.root), 'platforms': {'codex': {'homes': {'C1': 'C:/authorized'}}}, 'text': {'browser': {'sessions': {'approved': {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222', 'profile': {'path': 'C:/authorized', 'argument': '--user-data-dir'}, 'target_url_patterns': ['https://example.invalid/*'], 'allowed_operations': ['read', 'screenshot', 'create', 'navigate', 'write', 'close']}}}}}
		self.spec = {'session_id': 'approved', 'target_id': 'selected'}
		self.native = NativeFixture()
	# @used-by :meth:`TextBrowserTests.test_actual_profile_mismatch_rejected_before_content_read()`
	# @used-by :meth:`TextBrowserTests.test_common_user_data_directory_does_not_override_selected_profile()`
	# @used-by :meth:`TextBrowserTests.test_dynamic_antigravity_port_read_each_time_without_launch()`
	# @used-by :meth:`TextBrowserTests.test_explicit_current_page_and_url_are_required()`
	# @used-by :meth:`TextBrowserTests.test_live_account_marker_is_separate_from_profile_and_caller_assertion()`
	# @used-by :meth:`TextBrowserTests.test_port_and_caller_profile_do_not_prove_identity()`
	# @used-by :meth:`TextBrowserTests.test_runtime_profile_reference_uses_single_home_configuration()`
	def check(self, spec=None):
		return preflight(spec or self.spec, config=self.config, http_get=self.native.get, cdp_call=self.native.call)
	# @used-by :meth:`TextBrowserTests.test_actual_profile_mismatch_rejected_before_content_read()`
	# @used-by :meth:`TextBrowserTests.test_browser_window_read_is_bound_to_the_exact_target_and_cookies_are_unsupported()`
	# @used-by :meth:`TextBrowserTests.test_dynamic_antigravity_port_read_each_time_without_launch()`
	# @used-by :meth:`TextBrowserTests.test_javascript_read_requires_v8_side_effect_guard()`
	# @used-by :meth:`TextBrowserTests.test_only_real_created_target_can_be_mutated_and_ownership_change_stops_close()`
	# @used-by :meth:`TextBrowserTests.test_port_and_caller_profile_do_not_prove_identity()`
	# @used-by :meth:`TextBrowserTests.test_preflight_is_repeated_and_cannot_use_stale_target()`
	# @used-by :meth:`TextBrowserTests.test_session_lock_serializes_preflight_with_its_action()`
	# @used-by :meth:`TextBrowserTests.test_target_routing_and_application_shutdown_are_denied()`
	# @used-by :meth:`TextBrowserTests.test_user_target_read_and_screenshot_work_but_mutation_does_not()`
	def guard(self):
		return GuardedCDP(self.root, self.spec, config=self.config, http_get=self.native.get, cdp_call=self.native.call)
	# @used-by :mod:`unittest`
	def test_port_and_caller_profile_do_not_prove_identity(self):
		self.native.unavailable = True
		spec = {**self.spec, 'profile': {'status': 'verified', 'path': 'C:/authorized'}, 'owner': 'agent'}
		report = self.check(spec)
		self.assertFalse(report['valid'])
		self.assertEqual(report['profile']['status'], 'unknown')
		self.assertTrue(report['independent_http_allowed'])
		with self.assertRaises(PermissionError):
			self.guard().call('DOM.getDocument')
		self.assertFalse(any(('DOM.getDocument' == call[1] for call in self.native.calls)))
	# @used-by :mod:`unittest`
	def test_actual_profile_mismatch_rejected_before_content_read(self):
		self.native.arguments = ['browser', '--user-data-dir=C:/private']
		self.assertEqual(self.check()['profile']['status'], 'mismatch')
		with self.assertRaises(PermissionError):
			self.guard().call('Page.captureScreenshot')
		self.assertEqual({call[1] for call in self.native.calls}, {'Browser.getBrowserCommandLine'})
	# @used-by :mod:`unittest`
	def test_explicit_current_page_and_url_are_required(self):
		self.assertFalse(self.check({'session_id': 'approved'})['valid'])
		self.native.targets[0]['type'] = 'iframe'
		self.assertFalse(self.check()['valid'])
		self.native.targets[0]['type'] = 'page'
		self.native.targets[0]['url'] = 'https://signin.invalid/'
		self.assertFalse(self.check()['valid'])
		self.assertEqual(len(self.native.calls), 3)
	# @used-by :mod:`unittest`
	def test_user_target_read_and_screenshot_work_but_mutation_does_not(self):
		guard = self.guard()
		self.assertEqual(guard.call('DOM.getDocument'), {'ok': True})
		self.assertEqual(guard.call('Page.captureScreenshot'), {'ok': True})
		for method, params in [('Page.navigate', {'url': 'https://example.invalid/new'}), ('Page.reload', {}), ('Target.closeTarget', {'targetId': 'selected'}), ('Runtime.evaluate', {'expression': 'document.body.remove()'})]:
			with self.assertRaises(PermissionError):
				guard.call(method, params)
		substantive = [method for _, method, _ in self.native.calls if 'Browser.getBrowserCommandLine' != method]
		self.assertEqual(substantive, ['DOM.getDocument', 'Page.captureScreenshot'])
	# @used-by :mod:`unittest`
	def test_javascript_read_requires_v8_side_effect_guard(self):
		guard = self.guard()
		guard.call('Runtime.evaluate', {'expression': 'document.title', 'throwOnSideEffect': True})
		self.assertEqual(operation('Runtime.evaluate', {'expression': 'document.title'}), 'write')
		with self.assertRaises(PermissionError):
			guard.call('Runtime.evaluate', {'expression': 'document.title'})
		with self.assertRaises(PermissionError):
			guard.call('Runtime.evaluate', {'throwOnSideEffect': True, 'sessionId': 'other'})
	# @used-by :mod:`unittest`
	def test_preflight_is_repeated_and_cannot_use_stale_target(self):
		guard = self.guard()
		guard.call('DOM.getDocument')
		self.native.targets[0]['url'] = 'https://other.invalid/'
		with self.assertRaises(PermissionError):
			guard.call('DOM.getDocument')
		self.assertEqual([method for _, method, _ in self.native.calls].count('DOM.getDocument'), 1)
	# @used-by :mod:`unittest`
	def test_runtime_profile_reference_uses_single_home_configuration(self):
		self.config['text']['browser']['sessions']['approved']['profile'] = {'platform': 'codex', 'name': 'C1', 'argument': '--user-data-dir'}
		self.assertTrue(self.check()['valid'])
	# @used-by :mod:`unittest`
	def test_dynamic_antigravity_port_read_each_time_without_launch(self):
		active = self.root / 'DevToolsActivePort'
		active.write_text('9222\n/devtools/browser/live\n', encoding='utf-8')
		session = self.config['text']['browser']['sessions']['approved']
		session.pop('endpoint')
		session.update(surface='antigravity', devtools_active_port=str(active))
		self.assertTrue(self.check()['valid'])
		active.write_text('9333\n/devtools/browser/new\n', encoding='utf-8')
		self.native.browser = self.native.browser.replace('9222', '9333')
		self.native.targets[0]['webSocketDebuggerUrl'] = self.native.targets[0]['webSocketDebuggerUrl'].replace('9222', '9333')
		self.assertEqual(self.check()['endpoint'], 'http://127.0.0.1:9333')
		with self.assertRaises(PermissionError):
			self.guard().create_target('https://example.invalid/test')
		self.assertFalse(any(('Target.createTarget' == method for _, method, _ in self.native.calls)))
	# @used-by :mod:`unittest`
	def test_only_real_created_target_can_be_mutated_and_ownership_change_stops_close(self):
		guard = self.guard()
		receipt = guard.create_target('https://example.invalid/test')
		creation = next((call for call in self.native.calls if 'Target.createTarget' == call[1]))
		self.assertTrue(creation[2]['newWindow'])
		guard.select_owned(receipt['target_id'])
		guard.call('Page.navigate', {'url': 'https://example.invalid/next'})
		guard.call('Runtime.evaluate', {'expression': 'window.test = 1'})
		self.native.targets[-1]['url'] = 'https://example.invalid/user-work'
		with self.assertRaises(PermissionError):
			guard.call('Target.closeTarget')
		with self.assertRaises(PermissionError):
			self.guard().select_owned(receipt['target_id'])
	# @used-by :mod:`unittest`
	def test_target_routing_and_application_shutdown_are_denied(self):
		guard = self.guard()
		for method, params in [('Browser.close', {}), ('Target.createTarget', {}), ('Target.attachToTarget', {'targetId': 'other'}), ('Browser.getWindowForTarget', {'targetId': 'other'})]:
			with self.assertRaises(PermissionError):
				guard.call(method, params)
		self.assertEqual({method for _, method, _ in self.native.calls}, {'Browser.getBrowserCommandLine'})
	# @used-by :mod:`unittest`
	def test_browser_window_read_is_bound_to_the_exact_target_and_cookies_are_unsupported(self):
		self.guard().call('Browser.getWindowForTarget')
		self.assertEqual(self.native.calls[-1][2], {'targetId': 'selected'})
		with self.assertRaises(PermissionError):
			self.guard().call('Network.getCookies', {'urls': ['https://private.invalid/']})
	# @used-by :mod:`unittest`
	def test_common_user_data_directory_does_not_override_selected_profile(self):
		self.config['text']['browser']['sessions']['approved']['profile']['additional_arguments'] = {'--profile-directory': 'Default'}
		self.assertTrue(self.check()['valid'])
		self.native.arguments[-1] = '--profile-directory=Private'
		self.assertFalse(self.check()['valid'])
		self.native.arguments.pop()
		report = self.check()
		self.assertFalse(report['valid'])
		self.assertEqual(report['profile']['status'], 'unknown')
	# @used-by :mod:`unittest`
	def test_live_account_marker_is_separate_from_profile_and_caller_assertion(self):
		self.assertEqual(self.check()['account']['status'], 'unknown')
		self.config['text']['browser']['sessions']['approved']['account'] = {'expected': 'authorized@example.invalid', 'expression': 'document.querySelector("#account").textContent'}
		observed_account = 'wrong@example.invalid'
		# @used-by :meth:`TextBrowserTests.test_live_account_marker_is_separate_from_profile_and_caller_assertion()`
		def call(url, method, params):
			if 'Runtime.evaluate' != method:
				r = self.native.call(url, method, params)
			else:
				self.assertIs(params['throwOnSideEffect'], True)
				r = {'result': {'type': 'string', 'value': observed_account}}
			return r
		report = preflight({**self.spec, 'account': 'authorized@example.invalid'}, config=self.config, http_get=self.native.get, cdp_call=call)
		self.assertFalse(report['valid'])
		self.assertEqual(report['account']['status'], 'mismatch')
		observed_account = 'authorized@example.invalid'
		report = preflight(self.spec, config=self.config, http_get=self.native.get, cdp_call=call)
		self.assertTrue(report['valid'])
		self.assertEqual(report['account']['status'], 'verified')
	# @used-by :mod:`unittest`
	def test_dom_collector_requires_verified_profile_before_native_dom_evaluation(self):
		from agent_tools.research import capture_dom
		guard, native = dom_fixture(self.root, 'https://example.invalid/a', 'tab-A', '<p>Fixture DOM</p>')
		native.unavailable = True
		with self.assertRaises(PermissionError):
			capture_dom(self.root, 'https://example.invalid/a', 'tab-A', session_id='offline-dom', guard=guard)
		self.assertFalse(any(('Runtime.evaluate' == method for _, method, _ in native.calls)))
		with self.assertRaises(ValueError):
			capture_dom(self.root, 'https://example.invalid/a', 'tab-A')
		native.unavailable = False
		result = capture_dom(self.root, 'https://example.invalid/a', 'tab-A', session_id='offline-dom', guard=guard)
		self.assertEqual(result['kind'], 'dom')
		self.assertIsNone(result['status'])
		self.assertFalse(result['http_status_verified'])
		saved = json.loads((self.root / 'ꘖ/KB' / result['cdp_identity']).read_text(encoding='utf-8'))
		self.assertEqual(saved['profile']['status'], 'verified')
		self.assertEqual(saved['account']['status'], 'unknown')
		self.assertTrue(next((params for _, method, params in native.calls if 'Runtime.evaluate' == method))['throwOnSideEffect'])
	# @used-by :mod:`unittest`
	def test_dom_collector_exact_url_and_guard_project_cannot_be_substituted(self):
		from agent_tools.research import capture_dom
		guard, native = dom_fixture(self.root, 'https://example.invalid/a', 'tab-A', '<p>Fixture DOM</p>')
		with self.assertRaises(ValueError):
			capture_dom(self.root, 'https://example.invalid/other', 'tab-A', session_id='offline-dom', guard=guard)
		with self.assertRaises(ValueError):
			capture_dom(self.root, 'https://example.invalid/a', 'foreign', session_id='offline-dom', guard=guard)
		other = self.root / 'other'
		other.mkdir()
		with self.assertRaises(ValueError):
			capture_dom(other, 'https://example.invalid/a', 'tab-A', session_id='offline-dom', guard=guard)
		self.assertFalse(any(('Runtime.evaluate' == method for _, method, _ in native.calls)))
	# @used-by :mod:`unittest`
	def test_dom_collector_does_not_issue_content_proof_if_browser_identity_changes(self):
		from agent_tools.research import capture_dom, observation_capabilities
		guard, native = dom_fixture(self.root, 'https://example.invalid/a', 'tab-A', '<p>Fixture DOM</p>')
		versions = []
		# @used-by :meth:`TextBrowserTests.test_dom_collector_does_not_issue_content_proof_if_browser_identity_changes()`
		def get(url):
			if url.endswith('/json/version'):
				versions.append(url)
				if 2 == len(versions):
					native.browser = 'ws://127.0.0.1:9222/devtools/browser/restarted'
			r = native.get(url)
			return r
		guard.get = get
		result = capture_dom(self.root, 'https://example.invalid/a', 'tab-A', session_id='offline-dom', guard=guard)
		self.assertEqual(result['error'], 'ValueError')
		self.assertEqual(observation_capabilities(result), set())
	# @used-by :mod:`unittest`
	def test_session_lock_serializes_preflight_with_its_action(self):
		first, second = (self.guard(), self.guard())
		active, maximum = (0, 0)
		mutex = threading.Lock()
		# @used-by :meth:`TextBrowserTests.test_session_lock_serializes_preflight_with_its_action()`
		def delayed(url, method, params):
			nonlocal active, maximum
			with mutex:
				active += 1
				maximum = max(maximum, active)
			time.sleep(0.015)
			result = self.native.call(url, method, params)
			with mutex:
				active -= 1
			r = result
			return r
		first.call_native = second.call_native = delayed
		errors = []
		# @used-by :meth:`TextBrowserTests.test_session_lock_serializes_preflight_with_its_action()`
		def run(guard):
			try:
				guard.call('DOM.getDocument')
			except Exception as exc:
				errors.append(exc)
		threads = [threading.Thread(target=run, args=(guard,)) for guard in (first, second)]
		for thread in threads:
			thread.start()
		for thread in threads:
			thread.join(timeout=3)
		self.assertFalse(errors)
		self.assertEqual(maximum, 1)
		self.assertEqual([method for _, method, _ in self.native.calls], ['Browser.getBrowserCommandLine', 'DOM.getDocument'] * 2)
	# 2026-10-31
	# "Extract universal harness.py CLI, add CDP browser fallback on port 9222, and harden source/quote/anchor verification in answer-prepare":
	# https://github.com/dmitry-ai/harness/issues/27
	# 2026-11-16
	# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
	# https://github.com/dmitry-ai/harness/issues/80
	# @used-by :mod:`unittest`
	def test_collect_browser_never_hijacks_open_user_tab_without_tab_id_and_uses_hidden_target(self):
		from agent_tools.research import collect_browser
		native = NativeFixture()
		reddit_url = 'https://www.reddit.com/r/GoogleGeminiAI/comments/1abc/post/'
		rendered_html = '<html><head><title>Google Antigravity Thread</title></head><body><h1>Google Antigravity Thread</h1><div id="t1_nvz0p8c"><p>I hit a brick wall with Google Antigravity in production.</p></div></body></html>'
		# @used-by :meth:`TextBrowserTests.test_collect_browser_never_hijacks_open_user_tab_without_tab_id_and_uses_hidden_target()`
		def call(endpoint, method, params):
			if 'Runtime.evaluate' != method:
				return native.call(endpoint, method, params)
			native.calls.append((endpoint, method, deepcopy(params)))
			return {'result': {'type': 'object', 'value': {'readyState': 'complete', 'url': reddit_url, 'title': 'Google Antigravity Thread', 'html': rendered_html, 'textLen': 65}}}
		obs_bg = collect_browser(self.root, reddit_url, cdp_port=9222, http_get=native.get, cdp_call=call)
		self.assertEqual(obs_bg['kind'], 'dom')
		self.assertEqual(obs_bg['collector'], 'read-only-dom')
		self.assertFalse(obs_bg.get('browser_check_required'))
		self.assertGreater(obs_bg.get('word_count', 0), 0)
		create_calls = [params for _, method, params in native.calls if 'Target.createTarget' == method]
		close_calls = [params for _, method, params in native.calls if 'Target.closeTarget' == method]
		self.assertEqual(len(create_calls), 1)
		self.assertTrue(create_calls[0].get('background'))
		self.assertTrue(create_calls[0].get('hidden'))
		self.assertFalse(create_calls[0].get('newWindow', False))
		self.assertEqual(close_calls, [{'targetId': 'owned'}])
		native.calls.clear()
		native.targets[0]['url'] = reddit_url
		obs_user = collect_browser(self.root, reddit_url, cdp_port=9222, http_get=native.get, cdp_call=call, refresh_reason='verify open user tab is untouched')
		self.assertEqual(obs_user['kind'], 'dom')
		self.assertTrue(any(('Target.createTarget' == m and p.get('hidden') for _, m, p in native.calls)))
		self.assertFalse(any(('ws://127.0.0.1:9222/devtools/page/selected' == ep and 'Runtime.evaluate' == m for ep, m, _ in native.calls)))
	# 2026-10-31
	# "Extract universal harness.py CLI, add CDP browser fallback on port 9222, and harden source/quote/anchor verification in answer-prepare":
	# https://github.com/dmitry-ai/harness/issues/27
	# @used-by :mod:`unittest`
	def test_collect_http_auto_fallback_to_browser_on_reddit_js_challenge_shell(self):
		from agent_tools.research import Response, collect_http
		native = NativeFixture()
		reddit_url = 'https://www.reddit.com/r/GoogleGeminiAI/comments/1abc/post/'
		js_shell = ('<!DOCTYPE html><html><head><title>Reddit</title><style>' + ('body{}' * 1400) + '</style></head><body><form><input type="hidden" name="js_challenge" value="1"/></form></body></html>').encode('utf-8')
		self.assertGreater(len(js_shell), 8000)
		rendered_html = '<html><head><title>Google Antigravity Thread</title></head><body><h1>Google Antigravity Thread</h1><div id="t1_nvz0p8c"><p>Verified DOM body from user browser session.</p></div></body></html>'
		# @used-by :meth:`TextBrowserTests.test_collect_http_auto_fallback_to_browser_on_reddit_js_challenge_shell()`
		def call(endpoint, method, params):
			if 'Runtime.evaluate' != method:
				return native.call(endpoint, method, params)
			native.calls.append((endpoint, method, deepcopy(params)))
			return {'result': {'type': 'object', 'value': {'readyState': 'complete', 'url': reddit_url, 'title': 'Google Antigravity Thread', 'html': rendered_html, 'textLen': 48}}}
		obs_never = collect_http(self.root, reddit_url, fetcher=lambda u, h, t: Response(u, 200, 'text/html', js_shell), browser='never')
		self.assertTrue(obs_never.get('browser_check_required'))
		self.assertEqual(obs_never.get('word_count'), 0)
		obs_auto = collect_http(self.root, reddit_url, fetcher=lambda u, h, t: Response(u, 200, 'text/html', js_shell), browser='auto', cdp_port=9222, http_get=native.get, cdp_call=call, refresh_reason='auto browser fallback')
		self.assertEqual(obs_auto['kind'], 'dom')
		self.assertTrue(obs_auto.get('browser_fallback_from_http'))
		self.assertFalse(obs_auto.get('browser_check_required'))
		self.assertGreater(obs_auto.get('word_count', 0), 0)
	# 2026-11-13
	# "Deduplicate HTTP/CDP collection pipeline with browser fallback, extraction cache, and CDP primitives across research.py and text_browser.py":
	# https://github.com/dmitry-ai/harness/issues/66
	# @used-by :mod:`unittest`
	def test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives(self):
		from agent_tools.research import Response, collect_plan, extract_file
		from agent_tools.text_browser import discover_cdp_browser, probe_cdp_arguments, save_cdp_identity
		native = NativeFixture()
		version, targets, browser_ws = discover_cdp_browser('http://127.0.0.1:9222', native.get)
		self.assertEqual('Fixture/1', version['Browser'])
		self.assertEqual(1, len(targets))
		self.assertEqual(native.browser, browser_ws)
		self.assertEqual(native.arguments, probe_cdp_arguments(browser_ws, native.call))
		ref_one, sha_one = save_cdp_identity(self.root, {'schema_version': 1, 'endpoint': 'http://127.0.0.1:9222'})
		ref_two, sha_two = save_cdp_identity(self.root, {'schema_version': 1, 'endpoint': 'http://127.0.0.1:9222'})
		self.assertEqual((ref_one, sha_one), (ref_two, sha_two))
		sample = self.root / 'sample.txt'
		sample.write_text('cached extraction body', encoding='utf-8')
		ext_first = extract_file(self.root, 'sample.txt', profile='document')
		ext_second = extract_file(self.root, 'sample.txt', profile='document')
		self.assertEqual(ext_first, ext_second)
		json_url = 'https://example.invalid/feed.json'
		challenge_url = 'https://example.invalid/protected'
		js_shell = b'<html><body><form><input name="js_challenge" value="1"/></form></body></html>'
		rendered_html = '<html><head><title>Protected</title></head><body><h1>Protected Content</h1><p>Body text.</p></body></html>'
		# @used-by :meth:`TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
		def fetcher(url, headers, timeout):
			if json_url == url:
				r = Response(url, 200, 'application/json', b'{"items":[{"id":"1","title":"Alpha"}]}')
			else:
				r = Response(url, 403, 'text/html', js_shell)
			return r
		# @used-by :meth:`TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
		def call(endpoint, method, params):
			if 'Runtime.evaluate' != method:
				r = native.call(endpoint, method, params)
			else:
				native.calls.append((endpoint, method, deepcopy(params)))
				r = {'result': {'type': 'object', 'value': {'readyState': 'complete', 'url': challenge_url, 'title': 'Protected', 'html': rendered_html, 'textLen': 25}}}
			return r
		plan = {'requests': [{'url': json_url, 'profile': 'html'}, {'url': challenge_url, 'profile': 'html'}]}
		batch = collect_plan(self.root, plan, fetcher=fetcher, browser='auto', cdp_port=9222, http_get=native.get, cdp_call=call)
		self.assertTrue(batch['complete'])
		self.assertTrue(batch['content_available_for_all'])
		self.assertEqual('document', batch['results'][0]['profile'])
		self.assertEqual('dom', batch['results'][1]['kind'])
		self.assertTrue(batch['results'][1]['browser_fallback_from_http'])
	# 2026-11-16
	# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
	# https://github.com/dmitry-ai/harness/issues/80
	# @used-by :mod:`unittest`
	def test_m2a_extension_manifest_key_and_multi_profile_tab_broker_isolation(self):
		import base64
		import hashlib as _hl
		from agent_tools.runtime import PRIMARY, settings as rt_settings
		from agent_tools.research import collect_browser
		ext_dir = PRIMARY / 'browser_extension'
		manifest = json.loads((ext_dir / 'manifest.json').read_text(encoding='utf-8'))
		self.assertEqual(manifest['manifest_version'], 3)
		self.assertEqual(manifest['permissions'], ['offscreen'])
		self.assertNotIn('host_permissions', manifest)
		der = base64.b64decode(manifest['key'])
		computed_id = ''.join((chr(97 + int(c, 16)) for c in _hl.sha256(der).hexdigest()[:32]))
		cfg_session = rt_settings()['text']['browser']['sessions']['chrome-default']
		ext_id = cfg_session['profile']['extension_id']
		self.assertEqual(computed_id, ext_id)
		active_port = self.root / 'DevToolsActivePort'
		active_port.write_text('9222\n/devtools/browser/live\n', encoding='utf-8')
		cfg = {'workspace_root': str(self.root), 'platforms': {'antigravity': {'browser': {'cdp_port': 9222}}}, 'text': {'browser': {'primary_session_id': 'chrome-default', 'sessions': {'chrome-default': {'surface': 'browser', 'devtools_active_port': str(active_port), 'profile': {'path': str(self.root), 'argument': '--user-data-dir', 'extension_id': ext_id, 'sentinel_origin': 'https://harness-profile.invalid'}, 'target_url_patterns': ['https://*', 'http://*'], 'allowed_operations': ['read', 'screenshot', 'create', 'navigate', 'write', 'close']}}}}}
		targets = [
			{'id': 'tab-default', 'targetId': 'tab-default', 'type': 'page', 'url': 'https://example.invalid/default', 'title': 'Default Tab', 'browserContextId': 'ctx-default', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/tab-default'},
			{'id': 'tab-prof7', 'targetId': 'tab-prof7', 'type': 'page', 'url': 'https://example.invalid/prof7', 'title': 'Profile 7 Tab', 'browserContextId': 'ctx-prof7', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/tab-prof7'},
			{'id': 'ext-offscreen', 'targetId': 'ext-offscreen', 'type': 'background_page', 'url': f'chrome-extension://{ext_id}/offscreen.html', 'title': 'Offscreen', 'browserContextId': 'ctx-default', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/ext-offscreen'},
		]
		state = {'secondary_focused': True, 'no_default_windows': False, 'removed_tabs': []}
		# @used-by :meth:`TextBrowserTests.test_m2a_extension_manifest_key_and_multi_profile_tab_broker_isolation()`
		def get(url):
			if url.endswith('/json/version'):
				return {'Browser': 'Chrome/139.0.7258.155', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/browser/live'}
			if url.endswith('/json/list'):
				return deepcopy(targets)
			raise AssertionError(url)
		# @used-by :meth:`TextBrowserTests.test_m2a_extension_manifest_key_and_multi_profile_tab_broker_isolation()`
		def call(ws_url, method, params):
			if 'Browser.getBrowserCommandLine' == method:
				raise RuntimeError('Command line not returned because --enable-automation not set.')
			if 'Target.getTargets' == method:
				return {'targetInfos': deepcopy(targets)}
			if 'Target.attachToTarget' == method:
				return {'sessionId': 'sid-' + params['targetId']}
			if 'Target.detachFromTarget' == method:
				return {}
			if 'Target.createTarget' == method:
				if state['secondary_focused']:
					raise RuntimeError('InvalidParams: Failed to find browser context with id ' + str(params.get('browserContextId')))
				targets.append({'id': 'hidden-1', 'targetId': 'hidden-1', 'type': 'page', 'url': params['url'], 'title': 'Hidden', 'browserContextId': 'ctx-default', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/hidden-1'})
				return {'targetId': 'hidden-1'}
			if 'Target.closeTarget' == method:
				tid = params.get('targetId')
				targets[:] = [t for t in targets if t.get('id') != tid]
				return {'success': True}
			if 'Page.navigate' == method:
				for t in targets:
					if ws_url.endswith(t['id']):
						t['url'] = params['url']
				return {'frameId': 'main'}
			if 'Runtime.evaluate' == method:
				expr = params.get('expression', '')
				if '__harnessBroker' in expr:
					payload = json.loads(expr.split('__harnessBroker(', 1)[1].rsplit(')', 1)[0])
					if 'createBackgroundTab' == payload['action']:
						if state['no_default_windows']:
							return {'result': {'value': {'ok': False, 'error': 'Primary Chrome profile Default has no open normal non-incognito window'}}}
						targets.append({'id': 'broker-tab', 'targetId': 'broker-tab', 'type': 'page', 'url': payload['url'], 'title': '', 'browserContextId': 'ctx-default', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/broker-tab'})
						return {'result': {'value': {'ok': True, 'tabId': 77, 'windowId': 1}}}
					if 'removeTab' == payload['action']:
						state['removed_tabs'].append(payload['tabId'])
						targets[:] = [t for t in targets if 'broker-tab' != t.get('id')]
						return {'result': {'value': {'ok': True, 'removed': True, 'tabId': payload['tabId']}}}
				return {'result': {'value': {'url': 'https://portal.example.invalid/dashboard', 'html': '<html><body><h1>Default Portal</h1></body></html>', 'title': 'Portal', 'readyState': 'complete', 'textLen': 14}}}
			return {'ok': True}
		bad_guard = GuardedCDP(self.root, {'session_id': 'chrome-default', 'target_id': 'tab-prof7'}, config=cfg, http_get=get, cdp_call=call)
		with self.assertRaises(PermissionError):
			bad_guard.call('DOM.getDocument')
		ok_guard = GuardedCDP(self.root, {'session_id': 'chrome-default', 'target_id': 'tab-default'}, config=cfg, http_get=get, cdp_call=call)
		self.assertEqual(ok_guard.call('DOM.getDocument'), {'ok': True})
		auth_obs = collect_browser(self.root, 'https://portal.example.invalid/dashboard', session_id='chrome-default', config=cfg, http_get=get, cdp_call=call)
		self.assertEqual(auth_obs['kind'], 'dom')
		self.assertEqual(auth_obs['target_mode'], 'm2a_extension_background_tab')
		self.assertTrue(auth_obs['closed_after_capture'])
		self.assertEqual(state['removed_tabs'], [77])
		saved_id = json.loads((self.root / 'ꘖ/KB' / auth_obs['cdp_identity']).read_text(encoding='utf-8'))
		self.assertEqual(saved_id['profile']['status'], 'verified')
		self.assertEqual(saved_id['profile']['evidence_method'], 'M-2A:extension-offscreen-anchor')
		self.assertEqual(saved_id['profile']['browser_context_id'], 'ctx-default')
		state['no_default_windows'] = True
		with self.assertRaises(PermissionError):
			collect_browser(self.root, 'https://portal.example.invalid/other', session_id='chrome-default', config=cfg, http_get=get, cdp_call=call)
	# 2026-11-16
	# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
	# https://github.com/dmitry-ai/harness/issues/80
	# @used-by :mod:`unittest`
	def test_m2b_zero_extension_sentinel_skips_discarded_tabs_never_enumerates_cookies_and_guards_upwork_extract(self):
		from agent_tools.upwork_extract import extract_upwork_job
		cfg = {'workspace_root': str(self.root), 'platforms': {'antigravity': {'browser': {'cdp_port': 9222}}}, 'text': {'browser': {'primary_session_id': 'chrome-default', 'sessions': {'chrome-default': {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222', 'profile': {'path': str(self.root), 'argument': '--user-data-dir', 'sentinel_origin': 'https://harness-profile.invalid', 'sentinel_cookie_name': '__harness_primary_profile'}, 'target_url_patterns': ['https://*', 'http://*'], 'allowed_operations': ['read', 'screenshot', 'create', 'navigate', 'write', 'close']}}}}}
		nuxt_payload = json.dumps([{'vuex': 1}, {'jobDetails': 2}, {'job': 3, 'buyer': 6, 'workHistory': 7, 'openJobs': 8}, {'ciphertext': 4, 'title': 5, 'description': 5}, '~021234567890', 'Verified Default Upwork Job', {}, [], []])
		targets = [
			{'id': 'discarded-def', 'targetId': 'discarded-def', 'type': 'page', 'url': 'https://example.invalid/discarded', 'title': 'Discarded', 'browserContextId': 'ctx-default', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/discarded-def'},
			{'id': 'upwork-def', 'targetId': 'upwork-def', 'type': 'page', 'url': 'https://www.upwork.com/jobs/~021234567890', 'title': 'Upwork Default', 'browserContextId': 'ctx-default', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/upwork-def'},
			{'id': 'upwork-prof2', 'targetId': 'upwork-prof2', 'type': 'page', 'url': 'https://www.upwork.com/jobs/~021234567890', 'title': 'Upwork Profile 2', 'browserContextId': 'ctx-prof2', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/upwork-prof2'},
		]
		called_methods = []
		# @used-by :meth:`TextBrowserTests.test_m2b_zero_extension_sentinel_skips_discarded_tabs_never_enumerates_cookies_and_guards_upwork_extract()`
		def get(url):
			if url.endswith('/json/version'):
				return {'Browser': 'Chrome/139', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/browser/live'}
			if url.endswith('/json/list'):
				return deepcopy(targets)
			raise AssertionError(url)
		# @used-by :meth:`TextBrowserTests.test_m2b_zero_extension_sentinel_skips_discarded_tabs_never_enumerates_cookies_and_guards_upwork_extract()`
		def call(ws_url, method, params):
			called_methods.append((ws_url, method, deepcopy(params)))
			if 'Browser.getBrowserCommandLine' == method:
				raise RuntimeError('No --enable-automation')
			if 'Target.getTargets' == method:
				return {'targetInfos': deepcopy(targets)}
			if 'Target.attachToTarget' == method:
				return {'sessionId': 'sid:' + params['targetId']}
			if 'Target.detachFromTarget' == method:
				return {}
			if 'Storage.getUsageAndQuota' == method:
				self.assertEqual(params, {'origin': 'https://harness-profile.invalid'})
				if ws_url.endswith('discarded-def'):
					raise RuntimeError('InternalError: Partition not available')
				return {'usage': 1024 if ws_url.endswith('upwork-def') else 0, 'quota': 100000}
			if 'Runtime.evaluate' == method:
				return {'result': {'value': {'nuxt': nuxt_payload, 'title': 'Job', 'heading': 'Job', 'body': 'Body', 'readyState': 'complete'}}}
			return {'ok': True}
		with self.assertRaises(PermissionError):
			extract_upwork_job('~021234567890', cdp_port=9222, fetch_related=False, tab_id='upwork-prof2', config=cfg, http_get=get, cdp_call=call)
		captured = extract_upwork_job('~021234567890', cdp_port=9222, fetch_related=False, config=cfg, http_get=get, cdp_call=call)
		self.assertEqual(captured['source_tab']['id'], 'upwork-def')
		self.assertEqual(captured['coverage']['cdp_profile']['status'], 'verified')
		self.assertEqual(captured['coverage']['cdp_profile']['evidence_method'], 'M-2B:sentinel-origin')
		self.assertNotIn('Storage.getCookies', {m for _, m, _ in called_methods})
	# 2026-11-16
	# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
	# https://github.com/dmitry-ai/harness/issues/80
	# @used-by :mod:`unittest`
	def test_m1_live_headless_shell_public_isolation_and_h_chs_6_static_skip(self):
		from http.server import BaseHTTPRequestHandler, HTTPServer
		from agent_tools.research import Response, collect_browser, collect_http, collect_plan
		from agent_tools.text_browser import resolve_headless_shell
		with self.assertRaises(PermissionError):
			collect_browser(self.root, 'https://example.invalid/public', scope='public', cdp_port=9222)
		json_obs = collect_http(self.root, 'https://example.invalid/api.json', fetcher=lambda u, h, t: Response(u, 200, 'application/json', b'{"ok":true}'), browser='auto')
		self.assertEqual(json_obs['kind'], 'http')
		self.assertFalse(json_obs.get('browser_fallback'))
		try:
			resolve_headless_shell()
		except FileNotFoundError:
			self.skipTest('chrome-headless-shell not installed on host')
		class SpaHandler(BaseHTTPRequestHandler):
			# @used-by :meth:`TextBrowserTests.test_m1_live_headless_shell_public_isolation_and_h_chs_6_static_skip()`
			def log_message(self, *args):
				pass
			# @used-by :meth:`TextBrowserTests.test_m1_live_headless_shell_public_isolation_and_h_chs_6_static_skip()`
			def do_GET(self):
				self.send_response(200)
				self.send_header('Content-Type', 'text/html; charset=utf-8')
				self.end_headers()
				html = '<!DOCTYPE html><html><head><title>SPA</title><style>' + ('body{}' * 1400) + '</style></head><body><noscript>Enable JavaScript</noscript><script>document.body.innerHTML="<h1>Headless Rendered</h1><p>Clean isolated public DOM capture.</p>";</script></body></html>'
				self.wfile.write(html.encode('utf-8'))
		server = HTTPServer(('127.0.0.1', 0), SpaHandler)
		thread = threading.Thread(target=server.serve_forever, daemon=True)
		thread.start()
		try:
			spa_url = f'http://127.0.0.1:{server.server_port}/spa'
			batch = collect_plan(self.root, {'requests': [{'url': spa_url, 'profile': 'html'}]}, browser='auto')
			self.assertTrue(batch['complete'], batch)
			item = batch['results'][0]
			self.assertEqual(item['kind'], 'dom')
			self.assertTrue(item.get('browser_fallback_from_http'))
			self.assertEqual(item.get('target_mode'), 'ephemeral_headless_context')
			self.assertGreater(item.get('word_count', 0), 0)
			saved_id = json.loads((self.root / 'ꘖ/KB' / item['cdp_identity']).read_text(encoding='utf-8'))
			self.assertEqual(saved_id['profile']['status'], 'verified')
			self.assertEqual(saved_id['profile']['mode'], 'ephemeral_headless_shell')
			self.assertIn('HeadlessChrome/', saved_id['browser'])
		finally:
			server.shutdown()
			server.server_close()
	# 2026-11-16
	# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
	# https://github.com/dmitry-ai/harness/issues/80
	# @used-by :mod:`unittest`
	def test_m4_cdp_bypass_gate_and_m5_browser_mcp_gate(self):
		from check_rules_and_server_gate import check_browser_mcp_gate, check_cdp_bypass_gate
		from agent_tools.shell_audit import prohibited_cdp_bypass_commands, unpersisted_http_fetch_commands
		for bad_cmd in (
			'curl.exe -s http://127.0.0.1:9222/json',
			'python -c "import urllib.request; urllib.request.urlopen(\'http://127.0.0.1:9222/json/list\')"',
			'node -e "new WebSocket(\'ws://127.0.0.1:9222/devtools/page/abc\')"',
			'Get-Content C:/ChromeU/DevToolsActivePort',
			'npx chrome-devtools-mcp --autoConnect',
		):
			self.assertTrue(prohibited_cdp_bypass_commands(bad_cmd), bad_cmd)
			self.assertTrue(unpersisted_http_fetch_commands(bad_cmd), bad_cmd)
			self.assertIsNotNone(check_cdp_bypass_gate('run_command', {'CommandLine': bad_cmd}), bad_cmd)
		for allowed_cmd in (
			'python C:/work/research/provision/code/AI/harness/code/scripts/harness.py collect-browser C:/proj --url https://example.com',
			'python C:/work/research/provision/code/AI/harness/code/scripts/df_text.py browser-check C:/proj --spec s.json',
			'python -m unittest discover -s C:/work/research/provision/code/AI/harness/code/tests',
		):
			self.assertEqual(prohibited_cdp_bypass_commands(allowed_cmd), [], allowed_cmd)
			self.assertIsNone(check_cdp_bypass_gate('run_command', {'CommandLine': allowed_cmd}), allowed_cmd)
		self.assertIsNotNone(check_cdp_bypass_gate('read_file', {'Path': 'C:/ChromeU/DevToolsActivePort'}))
		self.assertIsNotNone(check_cdp_bypass_gate('read_file', {'Path': 'C:/ChromeU/Default/Network/Cookies'}))
		self.assertIsNotNone(check_cdp_bypass_gate('write_file', {'Path': str(self.root / 'bypass.py'), 'Content': 'urllib.request.urlopen("http://127.0.0.1:9222/json/list")\n'}))
		self.assertIsNone(check_cdp_bypass_gate('write_file', {'Path': str(self.root / 'notes.md'), 'Content': 'Discussing `/json/list` in Markdown prose.\n'}))
		transcript = self.root / 'transcript.jsonl'
		transcript.write_text(json.dumps({'type': 'USER_INPUT', 'content': 'go'}) + '\n', encoding='utf-8')
		self.assertIsNotNone(check_browser_mcp_gate('mcp_chrome-devtools_new_page', {'url': 'https://example.com'}, {'transcriptPath': str(transcript)}))
		self.assertIsNone(check_browser_mcp_gate('mcp_chrome-devtools_new_page', {'url': 'https://example.com', 'background': True}, {'transcriptPath': str(transcript)}))
		self.assertIsNotNone(check_browser_mcp_gate('mcp_chrome-devtools_navigate_page', {'url': 'https://example.com'}, {'transcriptPath': str(transcript)}))
		transcript.write_text(json.dumps({'type': 'USER_INPUT', 'content': 'go'}) + '\n' + json.dumps({'type': 'PLANNER_RESPONSE', 'tool_calls': [{'name': 'mcp_chrome-devtools_new_page', 'args': {'url': 'about:blank', 'background': True}}]}) + '\n', encoding='utf-8')
		self.assertIsNone(check_browser_mcp_gate('mcp_chrome-devtools_navigate_page', {'url': 'https://example.com'}, {'transcriptPath': str(transcript)}))
		self.assertIsNotNone(check_browser_mcp_gate('write_file', {'Path': str(self.root / 'mcp_config.json'), 'Content': '{"mcpServers":{"chrome-devtools":{"args":["--autoConnect"]}}}'}, {}))
	# 2026-11-23
	# "Replace getElementById with querySelector in read-only CDP registry and verify on live headless Chromium":
	# https://github.com/dmitry-ai/harness/issues/130
	# @used-by :mod:`unittest`
	def test_read_only_cdp_expressions_live_headless_shell_contract(self):
		import ast
		from http.server import BaseHTTPRequestHandler, HTTPServer
		import time
		from agent_tools.text_browser import CDPSession, ManagedHeadlessShell, READ_ONLY_CDP_EXPRESSIONS, resolve_headless_shell
		from agent_tools import upwork_extract
		self.assertEqual(set(READ_ONLY_CDP_EXPRESSIONS), {'dom_capture', 'minimal_dom_capture', 'upwork_page_state', 'user_agent'})
		self.assertEqual(upwork_extract._PAGE_STATE_EXPR, READ_ONLY_CDP_EXPRESSIONS['upwork_page_state'])
		for name, expr in READ_ONLY_CDP_EXPRESSIONS.items():
			self.assertIsInstance(expr, str, name)
			self.assertNotIn('getElementById', expr, name)
		tools_dir = Path(__file__).resolve().parents[1] / 'scripts/agent_tools'
		for mod_name in ('text_browser.py', 'upwork_extract.py', 'research.py'):
			tree = ast.parse((tools_dir / mod_name).read_text(encoding='utf-8'))
			for node in ast.walk(tree):
				if isinstance(node, ast.Dict):
					keys = [k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]
					if 'throwOnSideEffect' in keys and 'expression' in keys:
						expr_val = node.values[keys.index('expression')]
						self.assertFalse(isinstance(expr_val, ast.Constant) and isinstance(expr_val.value, str), f'Inline literal throwOnSideEffect expression in {mod_name}; register it in READ_ONLY_CDP_EXPRESSIONS')
		try:
			resolve_headless_shell()
		except FileNotFoundError:
			self.skipTest('chrome-headless-shell not installed on host')
		nuxt_payload = json.dumps([{'vuex': 1}, {'jobDetails': 2}, {'job': 3, 'buyer': 6, 'workHistory': 7, 'openJobs': 8}, {'ciphertext': 4, 'title': 5, 'description': 5}, '~021234567890', 'Live Chromium Contract Job', {}, [], []])
		class NuxtHandler(BaseHTTPRequestHandler):
			# @used-by :meth:`TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
			def log_message(self, *args):
				pass
			# @used-by :meth:`TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
			def do_GET(self):
				self.send_response(200)
				self.send_header('Content-Type', 'text/html; charset=utf-8')
				self.end_headers()
				html = f'<!DOCTYPE html><html><head><title>Contract Page</title></head><body><h1>Contract Heading</h1><p>Body text for live throwOnSideEffect verification.</p><script id="__NUXT_DATA__" type="application/json">{nuxt_payload}</script></body></html>'
				self.wfile.write(html.encode('utf-8'))
		server = HTTPServer(('127.0.0.1', 0), NuxtHandler)
		thread = threading.Thread(target=server.serve_forever, daemon=True)
		thread.start()
		try:
			page_url = f'http://127.0.0.1:{server.server_port}/job'
			with ManagedHeadlessShell() as shell, CDPSession(shell.browser_ws) as mux:
				ctx_id = mux.send('Target.createBrowserContext', {})['browserContextId']
				target_id = mux.send('Target.createTarget', {'url': page_url, 'browserContextId': ctx_id})['targetId']
				page_sid = mux.attach_target(target_id)
				try:
					deadline = time.time() + 10.0
					page_state = None
					while time.time() < deadline:
						res = mux.send('Runtime.evaluate', {'expression': READ_ONLY_CDP_EXPRESSIONS['upwork_page_state'], 'throwOnSideEffect': True, 'returnByValue': True}, session_id=page_sid)
						self.assertIsNone(res.get('exceptionDetails'), res)
						val = res.get('result', {}).get('value')
						if isinstance(val, dict) and val.get('nuxt') and 'complete' == val.get('readyState'):
							page_state = val
							break
						time.sleep(0.1)
					self.assertIsNotNone(page_state)
					decoded = upwork_extract.decode_page(page_state, '~021234567890')
					self.assertEqual(decoded['job']['title'], 'Live Chromium Contract Job')
					self.assertEqual(page_state['title'], 'Contract Page')
					self.assertEqual(page_state['heading'], 'Contract Heading')
					self.assertIn('live throwOnSideEffect verification', page_state['body'])
					for name, expr in READ_ONLY_CDP_EXPRESSIONS.items():
						res = mux.send('Runtime.evaluate', {'expression': expr, 'throwOnSideEffect': True, 'returnByValue': True}, session_id=page_sid)
						self.assertIsNone(res.get('exceptionDetails'), f'{name} failed under throwOnSideEffect=True: {res}')
						val = res.get('result', {}).get('value')
						if 'user_agent' == name:
							self.assertIsInstance(val, str)
							self.assertTrue(val.strip())
						else:
							self.assertIsInstance(val, dict, name)
							if 'html' in val:
								self.assertIn('Contract Heading', val['html'])
				finally:
					mux.detach_target(page_sid)
					mux.send('Target.disposeBrowserContext', {'browserContextId': ctx_id})
		finally:
			server.shutdown()
			server.server_close()
if '__main__' == __name__:
	unittest.main()
