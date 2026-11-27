# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Perf.TimedResult import TimedResult
from Df.Harness.Perf.TrackedPopen import TrackedPopen
import cProfile
import json
import os
import pstats
import sys
import time
import unittest
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class SuiteWorker:
	# @used-by :func:`agent_tools.perf.suite_worker.run_module_profile()`
	# @used-by :meth:`SuiteWorker.main()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_perf_classes_profile_and_build_timesheets()`
	def __init__(self, mod_path: Path, top_dir: Path, *, cprofile_top: int=0) -> None:
		self.__mod_path = Path(mod_path)
		self.__top_dir = Path(top_dir)
		self.__cprofile_top = cprofile_top
	# @used-by :func:`agent_tools.perf.suite_worker.run_module_profile()`
	# @used-by :meth:`SuiteWorker.main()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_perf_classes_profile_and_build_timesheets()`
	def run(self) -> dict[str, Any]:
		rel = self.__mod_path.relative_to(self.__top_dir).as_posix()
		stats = TimedResult.blank_stats()
		orig_popen, orig_sleep = TrackedPopen.install(stats)
		try:
			t_load0 = time.perf_counter()
			suite = unittest.defaultTestLoader.discover(str(self.__mod_path.parent), pattern=self.__mod_path.name, top_level_dir=str(self.__top_dir))
			load_s = round(max(0.0, time.perf_counter() - t_load0), 4)
			import_stats = TimedResult.diff_stats(TimedResult.blank_stats(), stats)
			result = TimedResult(stats, rel)
			prof = cProfile.Profile() if 0 < self.__cprofile_top else None
			t_run0 = time.perf_counter()
			suite.run(result) if None is prof else prof.runcall(suite.run, result)
			run_s = round(max(0.0, time.perf_counter() - t_run0), 4)
		finally:
			TrackedPopen.restore(orig_popen, orig_sleep)
		cp_rows = SuiteWorker.__extract_cprofile(prof, self.__cprofile_top) if None is not prof else []
		return {'file': rel, 'load_s': load_s, 'run_s': run_s, 'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped), 'import_stats': import_stats, 'tests': result.records, 'cprofile': cp_rows}
	# @used-by :meth:`SuiteWorker.run()`
	@staticmethod
	def __extract_cprofile(prof: cProfile.Profile, top_n: int) -> list[dict[str, Any]]:
		st = pstats.Stats(prof)
		rows = [{'file': Path(fname).as_posix() if fname else '', 'line': int(lineno), 'func': str(func), 'ncalls': int(nc), 'tottime': round(float(tt), 5), 'cumtime': round(float(ct), 5)} for (fname, lineno, func), (_cc, nc, tt, ct, _callers) in st.stats.items()]
		rows.sort(key=lambda item: (-item['cumtime'], -item['tottime']))
		return rows[:max(1, int(top_n))]
	# @used-by :func:`agent_tools.perf.suite_worker.main()`
	# @used-by :mod:`test_addon_observability`
	# @used-by :mod:`test_agent_tools`
	# @used-by :mod:`test_analysis_workflow`
	# @used-by :mod:`test_arch_audit_gates`
	# @used-by :mod:`test_arch_review_cli`
	# @used-by :mod:`test_arch_rules_contract`
	# @used-by :mod:`test_arch_spec_and_triggers`
	# @used-by :mod:`test_ask_question_clarifications_m8`
	# @used-by :mod:`test_ask_question_pre_tool_gate`
	# @used-by :mod:`test_atomic_prepare_and_narrowed_reconcile_m7`
	# @used-by :mod:`test_background_wait_and_tdd_inheritance`
	# @used-by :mod:`test_blocked_report_hygiene_and_doc5_m2`
	# @used-by :mod:`test_blocked_report_m2`
	# @used-by :mod:`test_bounded_foreign_sync`
	# @used-by :mod:`test_budget_status_scoping`
	# @used-by :mod:`test_chat_reply_link_issues_m5`
	# @used-by :mod:`test_clarification_stop_consent`
	# @used-by :mod:`test_cleanup_audit`
	# @used-by :mod:`test_cleanup_integration`
	# @used-by :mod:`test_cleanup_lifecycle`
	# @used-by :mod:`test_cleanup`
	# @used-by :mod:`test_cli_command_grounding`
	# @used-by :mod:`test_cli_common`
	# @used-by :mod:`test_cli_output_json`
	# @used-by :mod:`test_cli_registry`
	# @used-by :mod:`test_code_fanout_gates`
	# @used-by :mod:`test_code_formatting_rules`
	# @used-by :mod:`test_code_size_gate`
	# @used-by :mod:`test_code_style_gate`
	# @used-by :mod:`test_comment_exemption_and_denied_writes`
	# @used-by :mod:`test_context_and_storage_determinism`
	# @used-by :mod:`test_contract_invariants`
	# @used-by :mod:`test_cross_repo_issue_urls`
	# @used-by :mod:`test_df_analysis_companion_tracks`
	# @used-by :mod:`test_df_analysis_rules_contract`
	# @used-by :mod:`test_df_analysis`
	# @used-by :mod:`test_df_core_array`
	# @used-by :mod:`test_df_core_base`
	# @used-by :mod:`test_df_core_qa_s10`
	# @used-by :mod:`test_df_core_text_misc`
	# @used-by :mod:`test_df_dotpy_bootstrap`
	# @used-by :mod:`test_df_harness_dedup_s8`
	# @used-by :mod:`test_df_harness_lib_s10`
	# @used-by :mod:`test_df_harness_s11_wave2b_gate`
	# @used-by :mod:`test_df_harness_s11_wave2b_meta`
	# @used-by :mod:`test_df_harness_s11_wave2b_tdd`
	# @used-by :mod:`test_df_harness_s11_wave2b_xref`
	# @used-by :mod:`test_df_harness_s11_wave2e_arch`
	# @used-by :mod:`test_df_qa`
	# @used-by :mod:`test_df_upstream_fixes`
	# @used-by :mod:`test_diff_coverage_gate`
	# @used-by :mod:`test_diff_executability_contract`
	# @used-by :mod:`test_diff_executability_telemetry`
	# @used-by :mod:`test_diff_executability`
	# @used-by :mod:`test_dirty_diff_issue_scope`
	# @used-by :mod:`test_doc5_context_trigger`
	# @used-by :mod:`test_doc5_golden_feature_turn`
	# @used-by :mod:`test_doc5_replay_audit`
	# @used-by :mod:`test_env_isolation_and_worktree_gate_contracts`
	# @used-by :mod:`test_evidence_contract`
	# @used-by :mod:`test_evidence_unification`
	# @used-by :mod:`test_executor_metadata`
	# @used-by :mod:`test_experiments`
	# @used-by :mod:`test_failfast_and_schedule_gate`
	# @used-by :mod:`test_falsifier_and_schedule_subagent_gate_m8`
	# @used-by :mod:`test_falsifier_default_send_message_and_schedule_m8`
	# @used-by :mod:`test_finalized_project_contract`
	# @used-by :mod:`test_gate_registry`
	# @used-by :mod:`test_git_fixture_cache`
	# @used-by :mod:`test_git_ignore`
	# @used-by :mod:`test_git_lifecycle_memoization`
	# @used-by :mod:`test_github_issue`
	# @used-by :mod:`test_grounding_corpus_cache_m9`
	# @used-by :mod:`test_harness_xref_compliance`
	# @used-by :mod:`test_hook_lazy_imports`
	# @used-by :mod:`test_hook_runner_e2e_budget`
	# @used-by :mod:`test_hook_runner_watchdog`
	# @used-by :mod:`test_hook_trace_cache_and_watchdog`
	# @used-by :mod:`test_hook_unification`
	# @used-by :mod:`test_incomplete_scope_regression_matrix`
	# @used-by :mod:`test_instances_config`
	# @used-by :mod:`test_intake`
	# @used-by :mod:`test_issue44`
	# @used-by :mod:`test_issue45_to_48`
	# @used-by :mod:`test_issue_close_acceptance`
	# @used-by :mod:`test_issue_comment_gate`
	# @used-by :mod:`test_issue_conversation_isolation`
	# @used-by :mod:`test_issue_decomposition`
	# @used-by :mod:`test_issue_first_completion`
	# @used-by :mod:`test_issue_first_gate`
	# @used-by :mod:`test_issue_first_github_cli`
	# @used-by :mod:`test_issue_first_pre_tool_use`
	# @used-by :mod:`test_issue_first_rules_contract`
	# @used-by :mod:`test_issue_preflight_and_batch`
	# @used-by :mod:`test_java_xref`
	# @used-by :mod:`test_journal_clarifications_and_disclosure`
	# @used-by :mod:`test_journal_idle_sync_and_liveness`
	# @used-by :mod:`test_journal_integrity`
	# @used-by :mod:`test_journal_metadata`
	# @used-by :mod:`test_js_xref`
	# @used-by :mod:`test_landing_lease`
	# @used-by :mod:`test_metadata_decomposition`
	# @used-by :mod:`test_metadata_rules_contract`
	# @used-by :mod:`test_metadata`
	# @used-by :mod:`test_mixed_commit_audit`
	# @used-by :mod:`test_multiturn_handoff_stop_guard_and_schedule_m1`
	# @used-by :mod:`test_native_review_binding_m4`
	# @used-by :mod:`test_observability_diagnostics`
	# @used-by :mod:`test_open_child_deferral_gate`
	# @used-by :mod:`test_optimistic_worktree_land`
	# @used-by :mod:`test_parallel_runner`
	# @used-by :mod:`test_parallel_test_runner`
	# @used-by :mod:`test_path_cache_and_diff_cov_perf`
	# @used-by :mod:`test_path_registry_perf`
	# @used-by :mod:`test_path_registry`
	# @used-by :mod:`test_perf_improvement_skill_contract`
	# @used-by :mod:`test_perf_profile_tests`
	# @used-by :mod:`test_perf_timesheet`
	# @used-by :mod:`test_polyglot_land`
	# @used-by :mod:`test_problem_metadata`
	# @used-by :mod:`test_project_domain_drift`
	# @used-by :mod:`test_project_labels`
	# @used-by :mod:`test_project_rename_verification`
	# @used-by :mod:`test_project_rename`
	# @used-by :mod:`test_pytest_xdist_runner`
	# @used-by :mod:`test_python_integrity_gate`
	# @used-by :mod:`test_python_xref`
	# @used-by :mod:`test_red_flags`
	# @used-by :mod:`test_registration_portability`
	# @used-by :mod:`test_repo_link_gate`
	# @used-by :mod:`test_repo_locator_perf`
	# @used-by :mod:`test_repo_tag_close_gate`
	# @used-by :mod:`test_repo_tags_docs`
	# @used-by :mod:`test_repo_tags`
	# @used-by :mod:`test_repo_wait_and_retry`
	# @used-by :mod:`test_resume_exports`
	# @used-by :mod:`test_reused_reviewer_and_metadata_drift_m5`
	# @used-by :mod:`test_review_contract_package_and_paths_m6`
	# @used-by :mod:`test_review_target_claim_and_wait_m5`
	# @used-by :mod:`test_rules_architecture_m2`
	# @used-by :mod:`test_rules_audit`
	# @used-by :mod:`test_rules_progressive_disclosure`
	# @used-by :mod:`test_runtime_cache_and_evidence_fastpath_m9`
	# @used-by :mod:`test_runtime_snapshot`
	# @used-by :mod:`test_scatter_banner_gate`
	# @used-by :mod:`test_schema_help_and_analysis_merge_m10`
	# @used-by :mod:`test_scratch_slop_and_grounding_loc_m7`
	# @used-by :mod:`test_service_finalization_exempt_and_sync_all_open`
	# @used-by :mod:`test_shadow_replay_command`
	# @used-by :mod:`test_shadow_replay_m3`
	# @used-by :mod:`test_shell_herestring_write_targets_m4`
	# @used-by :mod:`test_snapshot_canary_and_hook_crash_audit`
	# @used-by :mod:`test_snapshot_latency_and_delegation_policy`
	# @used-by :mod:`test_source_admission`
	# @used-by :mod:`test_source_diagnostics_scanner`
	# @used-by :mod:`test_source_grounding`
	# @used-by :mod:`test_stdin_detachment`
	# @used-by :mod:`test_stop_emergency_capture_and_foreign_sync`
	# @used-by :mod:`test_stop_gate_contract`
	# @used-by :mod:`test_stop_gate_subagents_m1`
	# @used-by :mod:`test_storage_fsync_guard`
	# @used-by :mod:`test_subprocess_hygiene_and_tree_kill`
	# @used-by :mod:`test_tdd_comment_exemption`
	# @used-by :mod:`test_tdd_completion`
	# @used-by :mod:`test_tdd_decomposition`
	# @used-by :mod:`test_tdd_fast_path`
	# @used-by :mod:`test_tdd_gate`
	# @used-by :mod:`test_tdd_git_gate`
	# @used-by :mod:`test_tdd_mechanical_exemption`
	# @used-by :mod:`test_tdd_pre_tool_use_perf`
	# @used-by :mod:`test_tdd_pre_tool_use`
	# @used-by :mod:`test_tdd_rules_contract`
	# @used-by :mod:`test_tdd_worktree_and_subagent_trace`
	# @used-by :mod:`test_text_browser`
	# @used-by :mod:`test_text_diagnostics`
	# @used-by :mod:`test_text_native_binding`
	# @used-by :mod:`test_turn_begin_status_and_auditors`
	# @used-by :mod:`test_turn_completion`
	# @used-by :mod:`test_turn_routing_and_handoff_m6`
	# @used-by :mod:`test_upwork_data`
	# @used-by :mod:`test_upwork_init_e2e`
	# @used-by :mod:`test_verification_observability`
	# @used-by :mod:`test_watchdog_and_timeout_gate`
	# @used-by :mod:`test_worker_semaphore_and_xdist`
	# @used-by :mod:`test_worktree_cleanup_guard`
	# @used-by :mod:`test_worktree_comment_exemption`
	# @used-by :mod:`test_worktree_flow`
	# @used-by :mod:`test_worktree_ignore`
	# @used-by :mod:`test_worktree_isolation_gate`
	# @used-by :mod:`test_worktree_lifecycle`
	# @used-by :mod:`test_xref_gate`
	@staticmethod
	def main(argv: list[str] | None=None) -> int:
		args = list(sys.argv[1:] if None is argv else argv)
		mod_p, top_p, out_p = (Path(args[0]).resolve(), Path(args[1]).resolve(), Path(args[2]).resolve())
		cp_top = int(args[3]) if 3 < len(args) else 0
		if str(top_p) not in sys.path:
			sys.path.insert(0, str(top_p))
		os.environ.setdefault('HARNESS_TEST_NO_FSYNC', '1')
		data = SuiteWorker(mod_p, top_p, cprofile_top=cp_top).run()
		out_p.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
		return 0
