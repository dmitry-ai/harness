# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.completion_commands import dfh_begin, dfh_check_answer, dfh_prepare
from Df.Harness.lib.path_resolve import dfh_project_paths
from Df.Harness.lib.shadow_clone import dfh_build_stop_transcript
from Df.Harness.lib.turn_routing_ops import dfh_resolve_active_turn_state
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ReplayPipeline:
	# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.__run_shadow_mode()`
	# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_shadow_pipeline_and_runner()`
	# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_shadow_tail()`
	def __init__(self, shadow_project: Path, shadow_launcher: Path | None, shadow_root: Path, cid: str, platform: str, backend_dir: Path, native_tx: Path | None, response_file: Path | None, checks: dict, verified: list[str], errors: list[str]) -> None:
		self.__shadow_project = shadow_project
		self.__shadow_launcher = shadow_launcher
		self.__shadow_root = shadow_root
		self.__cid = cid
		self.__platform = platform
		self.__backend_dir = backend_dir
		self.__native_tx = native_tx
		self.__response_file = response_file
		self.__checks = checks
		self.__verified = verified
		self.__errors = errors
	# @used-by :meth:`ReplayPipeline.__run_finalize_stage()`
	def __execute_finalize_reply(self, reply_p: Path) -> None:
		from agent_tools import workflow
		try:
			reply_rel = reply_p.resolve().relative_to(self.__shadow_project.resolve()).as_posix()
			inputs = ['\ua616/KB/Analysis.json'] if (self.__shadow_project / '\ua616/KB/Analysis.json').is_file() else ['\ua616/project.json']
			res = workflow.complete_stage(self.__shadow_project, 'finalize', inputs, [reply_rel], note='Shadow replay finalize verification')
			fin_val = (res.get('stages') or {}).get('finalize')
			stage_status = fin_val.get('status') if isinstance(fin_val, dict) else fin_val
			self.__checks['stage_finalize'] = {'output': reply_rel, 'status': stage_status}
			if 'complete' == stage_status:
				self.__verified.append('stage_finalize')
			else:
				self.__errors.append(f'stage_finalize unexpected status: {stage_status}')
		except (OSError, ValueError) as exc:
			self.__checks['stage_finalize'] = {'error': str(exc), 'status': 'failed'}
			self.__errors.append(f'stage_finalize: {exc}')
	# @used-by :meth:`ReplayPipeline.__load_candidate()`
	# @used-by :meth:`ReplayPipeline.__run_finalize_stage()`
	def __find_reply_path(self) -> Path | None:
		from Df.Harness.lib.journal_core import dfh_journal_pair_dirs, dfh_resolve_journal_dir, dfh_step_file
		from Df.Harness.lib.journal_records import dfh_get_existing_step_ids
		turns_dir = dfh_project_paths(self.__shadow_project, exact_root=True).turns_dir
		state = dfh_resolve_active_turn_state(turns_dir, self.__cid, 10**9) if turns_dir.is_dir() else None
		prep = state.get('prepared') if isinstance(state, dict) and isinstance(state.get('prepared'), dict) else {}
		cand = Path(str(prep.get('response_file') or '')) if prep.get('response_file') else None
		if None is not cand and cand.is_file():
			r: Path | None = cand
		else:
			jdir = dfh_resolve_journal_dir(self.__shadow_project)
			ids = dfh_get_existing_step_ids(jdir) if jdir.is_dir() else []
			r = dfh_step_file(dfh_journal_pair_dirs(jdir)[1], max(ids), directory=jdir) if ids else None
		return r
	# @used-by :meth:`ReplayPipeline.run()`
	def __load_candidate(self) -> tuple[Path | None, str]:
		from agent_tools.metadata import strip_leading_metadata_header
		if None is not self.__response_file:
			body = strip_leading_metadata_header(Path(self.__response_file).read_bytes().decode('utf-8-sig'))
		else:
			found = self.__find_reply_path()
			body = strip_leading_metadata_header(found.read_bytes().decode('utf-8-sig')) if None is not found and found.is_file() else ''
		dest = self.__shadow_root / 'candidate-reply.md' if body else None
		if None is not dest:
			dest.write_bytes(body.encode('utf-8'))
		return (dest, body)
	# @used-by :meth:`ReplayPipeline.run()`
	def __run_answer_check(self, cand_path: Path | None) -> None:
		if None is cand_path:
			self.__errors.append('answer_check: No candidate response file or prepared journal reply found')
		else:
			try:
				chk = dfh_check_answer(self.__shadow_project, cand_path.read_bytes().decode('utf-8'), conversation=self.__cid, response_path=cand_path, platform=self.__platform, backend=self.__backend_dir)
				issues = chk.get('issues') or []
				self.__checks['answer_check'] = {'issue_count': len(issues), 'issues': issues, 'valid': bool(chk.get('valid'))}
				if chk.get('valid'):
					self.__verified.append('answer_check')
				else:
					self.__errors.append(f'answer_check failed ({len(issues)} issues)')
			except (OSError, ValueError) as exc:
				self.__checks['answer_check'] = {'error': str(exc), 'valid': False}
				self.__errors.append(f'answer_check: {exc}')
	# @used-by :meth:`ReplayPipeline.run()`
	def __run_answer_prepare(self, cand_path: Path | None) -> dict | None:
		r: dict | None = None
		if None is not cand_path:
			try:
				r = dfh_prepare(self.__shadow_project, cand_path.read_bytes().decode('utf-8'), conversation=self.__cid, platform=self.__platform, backend=self.__backend_dir)
				self.__checks['answer_prepare'] = {'body_sha256': r.get('body_sha256'), 'ready': bool(r.get('ready')), 'response_file': r.get('response_file')}
				if r.get('ready'):
					self.__verified.append('answer_prepare')
				else:
					self.__errors.append('answer_prepare returned ready=False')
			except (OSError, ValueError) as exc:
				self.__checks['answer_prepare'] = {'error': str(exc), 'ready': False}
				self.__errors.append(f'answer_prepare: {exc}')
		return r
	# @used-by :meth:`ReplayPipeline.run()`
	def __run_finalize_stage(self, prep_res: dict | None) -> None:
		from agent_tools import workflow
		if (self.__shadow_project / '\ua616/data/workflow.json').is_file():
			state = workflow.load(self.__shadow_project)
			if 'complete' == state.get('stages', {}).get('finalize', {}).get('status'):
				self.__checks['stage_finalize'] = {'already_complete': True, 'status': 'complete'}
				self.__verified.append('stage_finalize')
			else:
				reply_p = Path(str(prep_res['response_file'])) if isinstance(prep_res, dict) and prep_res.get('response_file') else self.__find_reply_path()
				if None is reply_p or (not reply_p.is_file()):
					self.__errors.append('stage_finalize: Missing prepared journal reply file')
				else:
					self.__execute_finalize_reply(reply_p)
	# @used-by :meth:`ReplayPipeline.run()`
	def __run_pre_invocation(self) -> None:
		from Df.Harness.Hook.PreInvocationGate import PreInvocationGate
		target = self.__shadow_launcher or self.__shadow_project
		l_turns = dfh_project_paths(self.__shadow_launcher, exact_root=True).turns_dir if None is not self.__shadow_launcher else None
		before = {p.name for p in l_turns.glob('*.json')} if None is not l_turns and l_turns.is_dir() else set()
		payload = {'conversationId': self.__cid, 'cwd': str(target), **({'transcriptPath': str(self.__native_tx)} if None is not self.__native_tx else {})}
		res = PreInvocationGate(payload, backend_override=self.__backend_dir).run()
		after = {p.name for p in l_turns.glob('*.json')} if None is not l_turns and l_turns.is_dir() else set()
		orphans = len(after - before)
		term = res.get('terminationBehavior')
		self.__checks['pre_invocation'] = {'launcher_orphans_created': orphans, 'target': str(target), 'termination': term}
		if 'terminate' == term or 0 < orphans:
			self.__errors.append(f'pre_invocation failed (termination={term}, launcher_orphans_created={orphans})')
		else:
			self.__verified.append('pre_invocation')
	# @used-by :meth:`ReplayPipeline.run()`
	def __run_review_stage(self, cand_body: str) -> None:
		from agent_tools import review, workflow
		if (self.__shadow_project / '\ua616/data/workflow.json').is_file():
			state = workflow.load(self.__shadow_project)
			if state.get('reviews'):
				try:
					auth = review.authorize(self.__shadow_project, state, response=cand_body or None)
					self.__checks['review_authorization'] = {'authorized': True, 'review_ids': auth.get('review_ids') or [], 'risk': auth.get('risk')}
					self.__verified.append('review_authorization')
				except (OSError, ValueError) as exc:
					self.__checks['review_authorization'] = {'authorized': False, 'error': str(exc)}
					self.__errors.append(f'review_authorization: {exc}')
	# @used-by :meth:`ReplayPipeline.run()`
	def __run_stop_gate(self, target_root: Path, stage_name: str, stop_tx: Path | None) -> None:
		from Df.Harness.Hook.StopGate import StopGate
		if None is stop_tx:
			self.__errors.append(f'{stage_name}: Native transcript unavailable')
		else:
			payload = {'conversationId': self.__cid, 'cwd': str(target_root), 'fullyIdle': True, 'terminationReason': 'NO_TOOL_CALL', 'transcriptPath': str(stop_tx)}
			res = StopGate(payload, backend_override=self.__backend_dir).run()
			self.__checks[stage_name] = res
			if 'allow' == res.get('decision'):
				self.__verified.append(stage_name)
			else:
				self.__errors.append(f"{stage_name} blocked: {res.get('reason') or res}")
	# @used-by :meth:`ReplayPipeline.run()`
	def __run_turn_begin(self) -> None:
		try:
			res = dfh_begin(self.__shadow_project, self.__cid, platform=self.__platform, backend=self.__backend_dir)
			rec_errs = [item for item in (res.get('reconciled') or ()) if isinstance(item, dict) and item.get('error')]
			self.__checks['turn_begin'] = {'reconciled_error_count': len(rec_errs), 'reconciled_errors': rec_errs, 'status': res.get('status'), 'turn_key': res.get('turn_key')}
			if rec_errs:
				self.__errors.append(f'turn_begin reconciliation errors: {rec_errs}')
			else:
				self.__verified.append('turn_begin')
		except (OSError, ValueError) as exc:
			self.__checks['turn_begin'] = {'error': str(exc)}
			self.__errors.append(f'turn_begin: {exc}')
	# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.__run_shadow_mode()`
	# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_shadow_pipeline_and_runner()`
	def run(self) -> None:
		self.__run_pre_invocation()
		self.__run_turn_begin()
		cand_path, cand_body = self.__load_candidate()
		self.__run_review_stage(cand_body)
		self.__run_answer_check(cand_path)
		prep_res = self.__run_answer_prepare(cand_path)
		self.__run_finalize_stage(prep_res)
		stop_tx = dfh_build_stop_transcript(self.__native_tx, cand_body, self.__shadow_root / 'stop-transcript') if None is not self.__native_tx and cand_body else self.__native_tx
		self.__run_stop_gate(self.__shadow_project, 'stop_gate_project', stop_tx)
		if None is not self.__shadow_launcher:
			self.__run_stop_gate(self.__shadow_launcher, 'stop_gate_launcher', stop_tx)