# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import json
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_binding_violation_message()`
# @used-by :func:`_expected_turn_key()`
# @used-by :func:`_format_turn_begin_message()`
# @used-by :func:`_is_tracked_and_non_umbrella()`
# @used-by :func:`_latest_completed_user_step()`
# @used-by :func:`_pre_flush_begin_context()`
# @used-by :func:`_resolve_ag_paths()`
# @used-by :func:`_resolve_pre_invocation_target()`
# @used-by :func:`_resolve_root()`
# @used-by :func:`_routed_pre_invocation_root()`
# @used-by :func:`_scratch_answer_path()`
# @used-by :func:`_summary_primary_status()`
# @used-by :func:`_terminate_error()`
# @used-by :func:`_turn_step_already_covered()`
# @used-by :func:`_turns_dir()`
# @used-by :func:`evaluate_pre_invocation_payload()`
def _ensure_scripts_on_path() -> None:
	scripts_dir = str(Path(__file__).resolve().parent)
	if scripts_dir not in sys.path:
		sys.path.insert(0, scripts_dir)
# @used-by :func:`_is_binding_violation()`
def _binding_violation_message(exc: ValueError, canon_root: Path, conversation_id: str, backend: Path) -> str | None:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_binding_violation_message
	return dfh_binding_violation_message(exc, canon_root, conversation_id, backend)
# @used-by unused
def _expected_turn_key(backend: Path, conversation_id: str, start_step: int) -> str:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_expected_turn_key
	return dfh_expected_turn_key(backend, conversation_id, start_step)
# @used-by unused
def _format_turn_begin_message(canon_root: Path, res: dict) -> dict:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_format_turn_begin_message
	return dfh_format_turn_begin_message(canon_root, res)
# @used-by unused
def _is_binding_violation(exc: ValueError, canon_root: Path, conversation_id: str, backend: Path) -> bool:
	return None is not _binding_violation_message(exc, canon_root, conversation_id, backend)
# @used-by unused
def _is_tracked_and_non_umbrella(root: Path, *, projects_dirs=None) -> tuple[bool, Path]:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_stop_ops import dfh_tracked_workspace
	return dfh_tracked_workspace(root, projects_dirs=projects_dirs)
# @used-by unused
def _latest_completed_user_step(conversations_dir: Path, conversation_id: str) -> int | None:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_latest_completed_user_step
	return dfh_latest_completed_user_step(conversations_dir, conversation_id)
# @used-by unused
def _pre_flush_begin_context(brain_dir: Path, conversations_dir: Path, conversation_id: str):
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_pre_flush_begin_context
	return dfh_pre_flush_begin_context(brain_dir, conversations_dir, conversation_id)
# @used-by unused
def _resolve_ag_paths(conversation_id: str, t_path: Path | None=None, backend_override: Path | None=None) -> tuple[Path, Path, Path, Path, Path]:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_stop_ops import dfh_resolve_ag_hook_paths
	from agent_tools import runtime
	return dfh_resolve_ag_hook_paths(conversation_id, t_path=t_path, backend_override=backend_override, settings_fn=runtime.settings)
# @used-by unused
def _resolve_pre_invocation_target(canon_root: Path, backend: Path, conversation_id: str, max_user_step: int, brain_dir: Path, conversations_dir: Path, t_path: Path | None) -> Path | None:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_resolve_pre_invocation_target
	return dfh_resolve_pre_invocation_target(canon_root, backend, conversation_id, max_user_step, brain_dir, conversations_dir, t_path)
# @used-by unused
def _resolve_root(payload: dict) -> Path | None:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_resolve_hook_root
	return dfh_resolve_hook_root(payload)
# @used-by :func:`test_contract_invariants._run_routing_parity_case()`
def _routed_pre_invocation_root(canon_root: Path, conversation_id: str, max_user_step: int, brain_dir: Path, conversations_dir: Path, t_path: Path | None) -> Path:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_routed_pre_invocation_root
	return dfh_routed_pre_invocation_root(canon_root, conversation_id, max_user_step, brain_dir, conversations_dir, t_path)
# @used-by unused
def _scratch_answer_path(canon_root: Path, turn_key: str) -> str:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_scratch_answer_path
	return dfh_scratch_answer_path(canon_root, turn_key)
# @used-by unused
def _summary_primary_status(conversations_db: Path, conversation_id: str) -> str:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_summary_primary_status
	return dfh_summary_primary_status(conversations_db, conversation_id)
# @used-by unused
def _terminate_error(message: str) -> dict:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_terminate_error
	return dfh_terminate_error(message)
# @used-by unused
def _turn_step_already_covered(t_dir: Path, backend: Path, conversation_id: str, max_user_step: int) -> bool:
	_ensure_scripts_on_path()
	from Df.Harness.lib.hook_pre_invocation_ops import dfh_turn_step_already_covered
	return dfh_turn_step_already_covered(t_dir, backend, conversation_id, max_user_step)
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_hook_and_transcript_callers_delegate_to_df_harness()`
def _turns_dir(canon_root: Path) -> Path:
	_ensure_scripts_on_path()
	from Df.Harness.lib.journal import dfh_turns_dir
	return dfh_turns_dir(canon_root, explicit_only=True)
# @used-by :func:`main()`
# @used-by :meth:`test_continuation_binding.AntigravityContinuationTests.test_quoted_and_non_leading_upwork_init_never_override_or_poison_and_support_cross_platform_commands()`
# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_cli_ratchet_ok_and_tdd_check_commands()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_antigravity_journal_conversation_auto_titling_and_comma_append()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_pre_invocation_hook_idempotent_turn_begin_child_skip_terminate_and_dry_run()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_registered_empty_launcher_project_tracks_pre_init_failures_and_hands_off_to_daily_project()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_similar_projects_parity_gate_stop_hook_pre_invocation_and_exemption()`
# @used-by :meth:`test_turn_routing_and_handoff_m6.TurnRoutingAndHandoffM6Tests.test_pre_invocation_allows_new_job_in_launcher_instead_of_routing()`
# @used-by :meth:`test_turn_routing_and_handoff_m6.TurnRoutingAndHandoffM6Tests.test_pre_invocation_fast_exits_on_same_turn1_handed_off_step()`
# @used-by :meth:`test_turn_routing_and_handoff_m6.TurnRoutingAndHandoffM6Tests.test_pre_invocation_routes_turn2_handed_off_to_daily_without_launcher_orphan()`
def evaluate_pre_invocation_payload(payload: dict, *, backend_override: Path | None=None) -> dict:
	_ensure_scripts_on_path()
	from Df.Harness.Hook.PreInvocationGate import PreInvocationGate
	from agent_tools import completion, runtime
	return PreInvocationGate(payload, backend_override=backend_override, settings_fn=runtime.settings, begin_fn=completion.begin).run()
# @used-by :mod:`check_pre_invocation`
def main() -> None:
	out: dict = {}
	try:
		raw = sys.stdin.read()
		if raw.strip():
			out = evaluate_pre_invocation_payload(json.loads(raw))
	except Exception:
		out = {}
	sys.stdout.write(json.dumps(out, ensure_ascii=False))
if '__main__' == __name__:
	main()