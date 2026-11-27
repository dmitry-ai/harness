# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_evaluate_prepared_match()`
# @used-by :func:`_find_turn_state()`
# @used-by :func:`_is_child_conversation()`
# @used-by :func:`_resolve_stop_paths()`
# @used-by :func:`_strip_local_file_scheme()`
# @used-by :func:`_tracked_workspace()`
# @used-by :func:`_turns_dir()`
# @used-by :func:`evaluate_stop_payload()`
# @used-by :func:`main()`
def _ensure_scripts_on_path() -> None:
	scripts_dir = str(Path(__file__).resolve().parent)
	if scripts_dir not in sys.path:
		sys.path.insert(0, scripts_dir)
# @used-by unused
def _evaluate_prepared_match(matched_state: dict, last_planner_text: str) -> dict:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_stop_ops import dfh_evaluate_prepared_match
	return dfh_evaluate_prepared_match(matched_state, last_planner_text)
# @used-by :func:`test_contract_invariants._run_routing_parity_case()`
# @used-by :meth:`test_multiturn_handoff_stop_guard_and_schedule_m1.MultiturnHandoffStopGuardAndScheduleM1Tests.test_handed_off_launcher_routes_turn2_followup_but_not_new_job_id()`
def _find_turn_state(t_dir: Path, session_id: str, last_user_step: int, *, rows: list | None=None) -> dict | None:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_stop_ops import dfh_find_turn_state
	return dfh_find_turn_state(t_dir, session_id, last_user_step, rows=rows)
# @used-by unused
def _is_child_conversation(backend: Path, conversation_id: str, *, conversations_db: Path | None=None) -> bool:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_stop_ops import dfh_is_child_conversation
	return dfh_is_child_conversation(backend, conversation_id, conversations_db=conversations_db)
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
def _is_tracked_workspace(root: Path, *, projects_dirs=None) -> bool:
	return _tracked_workspace(root, projects_dirs=projects_dirs)[0]
# @used-by unused
def _resolve_backend_fallback(session_id: str) -> Path:
	return _resolve_stop_paths(session_id)[0]
# @used-by :func:`_resolve_backend_fallback()`
def _resolve_stop_paths(session_id: str, t_path: Path | None=None, backend_override: Path | None=None) -> tuple[Path, Path, Path, Path]:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_stop_ops import dfh_resolve_ag_hook_paths
	from agent_tools import runtime
	backend, brain_dir, conversations_db, _, projects_dir = dfh_resolve_ag_hook_paths(session_id, t_path=t_path, backend_override=backend_override, swallow_errors=True, settings_fn=runtime.settings)
	return (backend, brain_dir, conversations_db, projects_dir)
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_hook_and_transcript_callers_delegate_to_df_harness()`
def _strip_local_file_scheme(text: str) -> str:
	_ensure_scripts_on_path()
	from Df.Harness.lib.journal import dfh_strip_local_file_scheme
	return dfh_strip_local_file_scheme(text)
# @used-by :func:`_is_tracked_workspace()`
def _tracked_workspace(root: Path, *, projects_dirs=None) -> tuple[bool, Path]:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_stop_ops import dfh_tracked_workspace
	return dfh_tracked_workspace(root, projects_dirs=projects_dirs)
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_hook_and_transcript_callers_delegate_to_df_harness()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
def _turns_dir(root: Path) -> Path:
	_ensure_scripts_on_path()
	from Df.Harness.lib.journal import dfh_turns_dir
	return dfh_turns_dir(root)
# @used-by :func:`main()`
# @used-by :func:`test_contract_invariants._run_routing_parity_case()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_per_instance_folders_json_uninitialized_instance_and_stop_gate_a6()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_antigravity_issue_first_gate_blocks_retroactive_and_passes_parent_then_tdd()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_antigravity_prepare_prepends_metadata_and_stop_gate_and_sync_accept_clean_chat_reply()`
# @used-by :meth:`test_multiturn_handoff_stop_guard_and_schedule_m1.MultiturnHandoffStopGuardAndScheduleM1Tests.test_handed_off_launcher_routes_turn2_followup_but_not_new_job_id()`
# @used-by :meth:`test_multiturn_handoff_stop_guard_and_schedule_m1.MultiturnHandoffStopGuardAndScheduleM1Tests.test_stop_guard_breaks_loop_without_continuation_active_across_steps()`
# @used-by :meth:`test_stop_emergency_capture_and_foreign_sync.StopEmergencyCaptureAndForeignSyncTests.test_stop_gate_fail_open_persists_emergency_capture_and_sync_avoids_duplicate()`
# @used-by :meth:`test_stop_gate_contract.StopGateContractTests.test_ag2_conversation_id_without_session_id_enforces_stop_gate()`
# @used-by :meth:`test_stop_gate_contract.StopGateContractTests.test_continuation_active_guards_against_unchanged_readiness_loops_but_allows_progress()`
# @used-by :meth:`test_stop_gate_contract.StopGateContractTests.test_fully_idle_false_pending_subagent_and_scope1_opt_out_allow_stop()`
# @used-by :meth:`test_stop_gate_contract.StopGateContractTests.test_transcript_path_uuid_fallback_when_ids_absent()`
# @used-by :meth:`test_stop_gate_subagents_m1.StopGateSubagentsM1Tests.test_ag2_system_message_fallback_without_db_and_killed_or_prior_children()`
# @used-by :meth:`test_stop_gate_subagents_m1.StopGateSubagentsM1Tests.test_idle_children_in_summary_db_enforce_stop_gate_while_running_child_allows()`
# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_antigravity_tdd_gate_blocks_violations_and_passes_full_bg_green()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_registered_empty_launcher_project_tracks_pre_init_failures_and_hands_off_to_daily_project()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_similar_projects_parity_gate_stop_hook_pre_invocation_and_exemption()`
# @used-by :meth:`test_turn_routing_and_handoff_m6.TurnRoutingAndHandoffM6Tests.test_stop_gate_deterministic_priority_prevents_alphabetical_shadowing()`
# @used-by :meth:`test_turn_routing_and_handoff_m6.TurnRoutingAndHandoffM6Tests.test_stop_gate_ignores_launcher_orphan_open_when_handed_off_matches()`
def evaluate_stop_payload(payload: dict, *, backend_override: Path | None=None) -> dict:
	_ensure_scripts_on_path()
	from Df.Harness.Hook.StopGate import StopGate
	from agent_tools import runtime
	return StopGate(payload, backend_override=backend_override, settings_fn=runtime.settings).run()
# @used-by :mod:`check_stop_gate`
def main():
	_ensure_scripts_on_path()
	from Df.Harness.Hook.JsonRunner import JsonRunner
	JsonRunner(evaluate_stop_payload).run()
if '__main__' == __name__:
	main()