# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Hook.ContinuationGuard import ContinuationGuard
from Df.Harness.Hook.SubagentChecker import SubagentChecker
from Df.Harness.lib import journal as dfh_journal
from Df.Harness.lib.hook_runtime_ops import dfh_read_last_user_segment
from Df.Harness.lib.hook_stop_ops import dfh_evaluate_prepared_match, dfh_extract_stop_context, dfh_find_turn_state, dfh_is_child_conversation, dfh_is_journal_opt_out, dfh_resolve_ag_hook_paths, dfh_tracked_workspace
from Df.Harness.lib.hook_subagent_ops import dfh_extract_segment_subagent_state
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class StopGate:
	# @used-by :func:`check_stop_gate.evaluate_stop_payload()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__run_stop_gate()`
	def __init__(self, payload: dict, *, backend_override: Path | None=None, settings_fn=None) -> None:
		self.__payload = payload
		self.__backend_override = backend_override
		self.__settings_fn = settings_fn
	# @used-by :meth:`StopGate.run()`
	def __evaluate_handoff(self, ctx: dict, state_ctx: dict) -> dict | None:
		matched_state = state_ctx['matched_state']
		r: dict | None = None
		if None is not matched_state and 'handed_off' == matched_state.get('status'):
			handoff_info = matched_state.get('handed_off_to') if isinstance(matched_state.get('handed_off_to'), dict) else {}
			handoff_raw = str(handoff_info.get('project_root') or '').strip()
			if handoff_raw:
				handoff_root = Path(handoff_raw).resolve()
				target_state = dfh_find_turn_state(dfh_journal.dfh_turns_dir(handoff_root), ctx['session_id'], state_ctx['last_user_step'])
				if None is target_state:
					reason = f'FILE-3 / SCOPE-3 Stop Gate: Launcher turn was handed off to {handoff_root}, which has no turn-begin / answer-prepare record for the active turn. Run turn-begin and answer-prepare (or answer-prepare --blocked-report after saving continuation.md if blocked) in {handoff_root} before finishing the response.'
					r = ContinuationGuard(state_ctx['t_dir'], ctx['session_id'], state_ctx['last_user_step'], matched_state, {'decision': 'continue', 'reason': reason}, self.__payload, segment=state_ctx['segment']).run()
				else:
					state_ctx['matched_state'] = target_state
		return r
	# @used-by :meth:`StopGate.run()`
	def __evaluate_matched_state(self, ctx: dict, state_ctx: dict) -> dict:
		from agent_tools.gates import run_stop_gates
		matched_state = state_ctx['matched_state']
		emergency_ctx = {'backend': ctx['backend'], 'last_planner_text': state_ctx['last_planner_text'], 'log_file': state_ctx['log_file'], 'root': ctx['canon_root'], 'rows': state_ctx['rows']}
		if None is matched_state:
			decision = {'decision': 'continue', 'reason': 'FILE-3 / SCOPE-3 Stop Gate: Active turn has no turn-begin / answer-prepare record. Run turn-begin and answer-prepare (or answer-prepare --blocked-report after saving continuation.md for a pre-finalize blocker) before finishing the response.'}
		else:
			gate_hit = run_stop_gates(matched_state)
			decision = gate_hit if None is not gate_hit else dfh_evaluate_prepared_match(matched_state, state_ctx['last_planner_text'])
		return ContinuationGuard(state_ctx['t_dir'], ctx['session_id'], state_ctx['last_user_step'], matched_state, decision, self.__payload, segment=state_ctx['segment'], emergency_ctx=emergency_ctx).run()
	# @used-by :meth:`StopGate.run()`
	def __load_state_context(self, ctx: dict) -> dict | None:
		t_path = ctx['t_path']
		logs_dir = t_path.parent if None is not t_path else (ctx['brain_dir'] / ctx['session_id'] / '.system_generated/logs')
		full_t, compact_t = (logs_dir / 'transcript_full.jsonl', logs_dir / 'transcript.jsonl')
		log_file = full_t if full_t.is_file() else (t_path if None is not t_path and t_path.is_file() else compact_t)
		r: dict | None = None
		if None is not log_file and log_file.is_file():
			rows, last_user_step, segment = dfh_read_last_user_segment(log_file, by_step_index=True)
			if None is not last_user_step:
				sub_state = dfh_extract_segment_subagent_state(segment)
				if not SubagentChecker(sub_state, ctx['session_id'], ctx['conversations_db']).run():
					t_dir = dfh_journal.dfh_turns_dir(ctx['canon_root'])
					matched_state = dfh_find_turn_state(t_dir, ctx['session_id'], last_user_step, rows=rows)
					if not dfh_is_journal_opt_out(self.__payload, rows, last_user_step, matched_state):
						r = {'last_planner_text': sub_state['last_planner_text'], 'last_user_step': last_user_step, 'log_file': log_file, 'matched_state': matched_state, 'rows': rows, 'segment': segment, 't_dir': t_dir}
		return r
	# @used-by :meth:`StopGate.run()`
	def __resolve_tracked_context(self) -> dict | None:
		r: dict | None = None
		if isinstance(self.__payload, dict) and 'NO_TOOL_CALL' == self.__payload.get('terminationReason') and (not bool(self.__payload.get('error'))) and False is not self.__payload.get('fullyIdle'):
			cwd_raw, session_id, t_path_raw = dfh_extract_stop_context(self.__payload)
			if cwd_raw and session_id:
				root = Path(cwd_raw).resolve()
				t_path = Path(t_path_raw).resolve() if t_path_raw else None
				fast_tracked, canon_root = dfh_tracked_workspace(root, projects_dirs=())
				backend, brain_dir, conversations_db, _, projects_dir = dfh_resolve_ag_hook_paths(session_id, t_path=t_path, backend_override=self.__backend_override, swallow_errors=True, settings_fn=self.__settings_fn)
				tracked = True
				if not fast_tracked:
					tracked, canon_root = dfh_tracked_workspace(root, projects_dirs=(projects_dir,))
				if tracked and (not dfh_is_child_conversation(backend, session_id, conversations_db=conversations_db)):
					r = {'backend': backend, 'brain_dir': brain_dir, 'canon_root': canon_root, 'conversations_db': conversations_db, 'session_id': session_id, 't_path': t_path}
		return r
	# @used-by :func:`check_stop_gate.evaluate_stop_payload()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__run_stop_gate()`
	def run(self) -> dict:
		r = {'decision': 'allow'}
		ctx = self.__resolve_tracked_context()
		if None is not ctx:
			state_ctx = self.__load_state_context(ctx)
			if None is not state_ctx:
				handoff_decision = self.__evaluate_handoff(ctx, state_ctx)
				r = handoff_decision if None is not handoff_decision else self.__evaluate_matched_state(ctx, state_ctx)
		return r