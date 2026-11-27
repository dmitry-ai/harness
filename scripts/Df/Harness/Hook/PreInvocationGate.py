# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.hook_pre_invocation_ops import dfh_binding_violation_message, dfh_format_turn_begin_message, dfh_latest_completed_user_step, dfh_pre_flush_begin_context, dfh_resolve_hook_root, dfh_resolve_pre_invocation_target, dfh_summary_primary_status, dfh_terminate_error
from Df.Harness.lib.hook_stop_ops import dfh_resolve_ag_hook_paths, dfh_tracked_workspace
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class PreInvocationGate:
	# @used-by :func:`check_pre_invocation.evaluate_pre_invocation_payload()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__run_pre_invocation()`
	def __init__(self, payload: dict, *, backend_override: Path | None=None, settings_fn=None, begin_fn=None) -> None:
		self.__payload = payload
		self.__backend_override = backend_override
		self.__settings_fn = settings_fn
		self.__begin_fn = begin_fn
	# @used-by :meth:`PreInvocationGate.__resolve_invocation()`
	def __resolve_ag_context(self, root: Path, conversation_id: str) -> tuple[dict | None, dict | None]:
		fast_tracked, canon_root = dfh_tracked_workspace(root, projects_dirs=())
		t_path_raw = str(self.__payload.get('transcriptPath') or '').strip()
		t_path = Path(t_path_raw).resolve() if t_path_raw else None
		err_out, ctx = (None, None)
		try:
			backend, brain_dir, conversations_db, conversations_dir, projects_dir = dfh_resolve_ag_hook_paths(conversation_id, t_path=t_path, backend_override=self.__backend_override, settings_fn=self.__settings_fn)
		except ValueError as exc:
			err_out = dfh_terminate_error(str(exc)) if fast_tracked and 'exists in multiple Antigravity instances' in str(exc) else {}
		except Exception:
			err_out = {}
		else:
			ctx = {'backend': backend, 'brain_dir': brain_dir, 'canon_root': canon_root, 'conversations_db': conversations_db, 'conversations_dir': conversations_dir, 'fast_tracked': fast_tracked, 'projects_dir': projects_dir, 't_path': t_path}
		return (err_out, ctx)
	# @used-by :meth:`PreInvocationGate.run()`
	def __resolve_invocation(self) -> tuple[dict | None, dict | None]:
		err_out, ctx = (None, None)
		conversation_id = str(self.__payload.get('conversationId') or self.__payload.get('sessionId') or '').strip().lower() if isinstance(self.__payload, dict) else ''
		root = dfh_resolve_hook_root(self.__payload) if conversation_id and re.fullmatch('[a-f0-9-]{36}', conversation_id) else None
		if None is root:
			err_out = {}
		else:
			err_out, ag_ctx = self.__resolve_ag_context(root, conversation_id)
			if None is err_out and None is not ag_ctx:
				ctx = self.__resolve_target(root, conversation_id, ag_ctx)
		return (err_out, ctx)
	# @used-by :meth:`PreInvocationGate.__resolve_invocation()`
	def __resolve_target(self, root: Path, conversation_id: str, ag_ctx: dict) -> dict | None:
		canon_root = ag_ctx['canon_root']
		tracked = True
		if not ag_ctx['fast_tracked']:
			tracked, canon_root = dfh_tracked_workspace(root, projects_dirs=(ag_ctx['projects_dir'],))
		r: dict | None = None
		if tracked and 'primary' == dfh_summary_primary_status(ag_ctx['conversations_db'], conversation_id):
			max_user_step = dfh_latest_completed_user_step(ag_ctx['conversations_dir'], conversation_id)
			if None is not max_user_step:
				target_root = dfh_resolve_pre_invocation_target(canon_root, ag_ctx['backend'], conversation_id, max_user_step, ag_ctx['brain_dir'], ag_ctx['conversations_dir'], ag_ctx['t_path'])
				if None is not target_root:
					r = {**ag_ctx, 'canon_root': target_root, 'conversation_id': conversation_id}
		return r
	# @used-by :meth:`PreInvocationGate.run()`
	def __run_begin(self, ctx: dict) -> dict:
		from Df.Harness.lib.completion_commands import dfh_begin
		r: dict = {}
		canon_root, backend, conversation_id = (ctx['canon_root'], ctx['backend'], ctx['conversation_id'])
		begin_cb = self.__begin_fn if None is not self.__begin_fn else dfh_begin
		with dfh_pre_flush_begin_context(ctx['brain_dir'], ctx['conversations_dir'], conversation_id):
			try:
				res = begin_cb(canon_root, conversation_id, platform='antigravity', backend=backend)
			except ValueError as exc:
				violation_msg = dfh_binding_violation_message(exc, canon_root, conversation_id, backend)
				r = dfh_terminate_error(violation_msg) if None is not violation_msg else {}
			except Exception:
				r = {}
			else:
				if 'primary' == res.get('role') and res.get('turn_key') and 'handed_off' != res.get('status'):
					r = dfh_format_turn_begin_message(canon_root, res)
		return r
	# @used-by :func:`check_pre_invocation.evaluate_pre_invocation_payload()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__run_pre_invocation()`
	def run(self) -> dict:
		err_out, ctx = self.__resolve_invocation()
		if None is not err_out:
			r = err_out
		elif None is ctx:
			r = {}
		else:
			r = self.__run_begin(ctx)
		return r