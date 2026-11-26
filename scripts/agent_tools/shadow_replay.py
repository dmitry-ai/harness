# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import sys
import uuid
from . import completion, review, workflow
from .journal import get_existing_step_ids, journal_pair_dirs, resolve_journal_dir, state_dir, step_file
from .metadata import strip_leading_metadata_header
from .path_registry import project_paths
from .runtime import resolve_antigravity_paths
from .shadow_replay_clone import build_stop_transcript, cleanup_shadow_root, clone_project_tree, remap_shadow_state, shadow_isolation_context
# 2026-11-26 "Add mutating command execution mode to shadow-replay with isolated native profiles": https://github.com/dmitry-ai/harness/issues/289
from .shadow_replay_command import execute_shadow_command, persist_shadow_replay_receipt, resolve_shadow_launcher, stage_command_shadow_copies
from .turn_routing import resolve_active_turn_state
# 2026-11-25
# "Add workspace-local shadow-replay CLI command and EXEC-2 acceptance gate":
# https://github.com/dmitry-ai/harness/issues/237
NOT_RUN_STAGES = ('live_llm_generation', 'live_upwork_browser_capture', 'live_antigravity_rpc_title_sync')
# @used-by :func:`_run_pre_invocation()`
# @used-by :func:`_run_stop_gate()`
def _ensure_scripts_path() -> None:
	scripts_dir = str(Path(__file__).resolve().parents[1])
	if scripts_dir not in sys.path:
		sys.path.insert(0, scripts_dir)
# @used-by :func:`_run_finalize_stage()`
def _execute_finalize_reply(shadow_project: Path, reply_p: Path, checks: dict, verified: list[str], errors: list[str]) -> None:
	try:
		reply_rel = reply_p.resolve().relative_to(shadow_project.resolve()).as_posix()
		inputs = ['\ua616/KB/Analysis.json'] if (shadow_project / '\ua616/KB/Analysis.json').is_file() else ['\ua616/project.json']
		res = workflow.complete_stage(shadow_project, 'finalize', inputs, [reply_rel], note='Shadow replay finalize verification')
		fin_val = (res.get('stages') or {}).get('finalize')
		stage_status = fin_val.get('status') if isinstance(fin_val, dict) else fin_val
		checks['stage_finalize'] = {'status': stage_status, 'output': reply_rel}
		if 'complete' == stage_status:
			verified.append('stage_finalize')
		else:
			errors.append(f'stage_finalize unexpected status: {stage_status}')
	except (OSError, ValueError) as exc:
		checks['stage_finalize'] = {'status': 'failed', 'error': str(exc)}
		errors.append(f'stage_finalize: {exc}')
# @used-by :func:`_run_shadow_mode()`
def _execute_replay_pipeline(shadow_project: Path, shadow_launcher: Path | None, shadow_root: Path, cid: str, platform: str, backend_dir: Path, native_tx: Path | None, response_file: Path | None, checks: dict, verified: list[str], errors: list[str]) -> None:
	_run_pre_invocation(shadow_launcher or shadow_project, shadow_launcher, cid, native_tx, backend_dir, checks, verified, errors)
	_run_turn_begin(shadow_project, cid, platform, backend_dir, checks, verified, errors)
	cand_path, cand_body = _load_candidate(shadow_project, shadow_root, response_file, cid)
	_run_review_stage(shadow_project, cand_body, checks, verified, errors)
	_run_answer_check(shadow_project, cand_path, cid, platform, backend_dir, checks, verified, errors)
	prep_res = _run_answer_prepare(shadow_project, cand_path, cid, platform, backend_dir, checks, verified, errors)
	_run_finalize_stage(shadow_project, prep_res, cid, checks, verified, errors)
	stop_tx = build_stop_transcript(native_tx, cand_body, shadow_root / 'stop-transcript') if None is not native_tx and cand_body else native_tx
	_run_stop_gate(shadow_project, 'stop_gate_project', cid, stop_tx, backend_dir, checks, verified, errors)
	if None is not shadow_launcher:
		_run_stop_gate(shadow_launcher, 'stop_gate_launcher', cid, stop_tx, backend_dir, checks, verified, errors)
# @used-by :func:`_load_candidate()`
# @used-by :func:`_run_finalize_stage()`
def _find_reply_path(shadow_project: Path, cid: str) -> Path | None:
	turns_dir = project_paths(shadow_project, exact_root=True).turns_dir
	state = resolve_active_turn_state(turns_dir, cid, 10**9) if turns_dir.is_dir() else None
	prep = state.get('prepared') if isinstance(state, dict) and isinstance(state.get('prepared'), dict) else {}
	cand = Path(str(prep.get('response_file') or '')) if prep.get('response_file') else None
	if None is not cand and cand.is_file():
		r = cand
	else:
		jdir = resolve_journal_dir(shadow_project)
		ids = get_existing_step_ids(jdir) if jdir.is_dir() else []
		r = step_file(journal_pair_dirs(jdir)[1], max(ids), directory=jdir) if ids else None
	return r
# @used-by :func:`_execute_replay_pipeline()`
def _load_candidate(shadow_project: Path, shadow_root: Path, response_file: Path | None, cid: str) -> tuple[Path | None, str]:
	if None is not response_file:
		body = strip_leading_metadata_header(Path(response_file).read_bytes().decode('utf-8-sig'))
	else:
		found = _find_reply_path(shadow_project, cid)
		body = strip_leading_metadata_header(found.read_bytes().decode('utf-8-sig')) if None is not found and found.is_file() else ''
	dest = shadow_root / 'candidate-reply.md' if body else None
	if None is not dest:
		dest.write_bytes(body.encode('utf-8'))
	return (dest, body)
# @used-by :func:`_run_shadow_mode()`
def _resolve_native_paths(cid: str, backend: Path | None) -> tuple[Path, Path | None]:
	resolved = resolve_antigravity_paths(backend=backend, conversation_id=cid)
	backend_dir = Path(resolved['backend_dir']).resolve()
	logs_dir = Path(resolved['brain_dir']).resolve() / cid / '.system_generated/logs'
	full_t = logs_dir / 'transcript_full.jsonl'
	comp_t = logs_dir / 'transcript.jsonl'
	tx = full_t if full_t.is_file() else (comp_t if comp_t.is_file() else None)
	return (backend_dir, tx)
# @used-by :func:`_execute_replay_pipeline()`
def _run_answer_check(shadow_project: Path, cand_path: Path | None, cid: str, platform: str, backend: Path, checks: dict, verified: list[str], errors: list[str]) -> None:
	if None is cand_path:
		errors.append('answer_check: No candidate response file or prepared journal reply found')
	else:
		try:
			chk = completion.check_answer(shadow_project, cand_path.read_bytes().decode('utf-8'), conversation=cid, response_path=cand_path, platform=platform, backend=backend)
			issues = chk.get('issues') or []
			checks['answer_check'] = {'valid': bool(chk.get('valid')), 'issue_count': len(issues), 'issues': issues}
			if chk.get('valid'):
				verified.append('answer_check')
			else:
				errors.append(f'answer_check failed ({len(issues)} issues)')
		except (OSError, ValueError) as exc:
			checks['answer_check'] = {'valid': False, 'error': str(exc)}
			errors.append(f'answer_check: {exc}')
# @used-by :func:`_execute_replay_pipeline()`
def _run_answer_prepare(shadow_project: Path, cand_path: Path | None, cid: str, platform: str, backend: Path, checks: dict, verified: list[str], errors: list[str]) -> dict | None:
	r = None
	if None is not cand_path:
		try:
			r = completion.prepare(shadow_project, cand_path.read_bytes().decode('utf-8'), conversation=cid, platform=platform, backend=backend)
			checks['answer_prepare'] = {'ready': bool(r.get('ready')), 'response_file': r.get('response_file'), 'body_sha256': r.get('body_sha256')}
			if r.get('ready'):
				verified.append('answer_prepare')
			else:
				errors.append('answer_prepare returned ready=False')
		except (OSError, ValueError) as exc:
			checks['answer_prepare'] = {'ready': False, 'error': str(exc)}
			errors.append(f'answer_prepare: {exc}')
	return r
# @used-by :func:`_execute_replay_pipeline()`
def _run_finalize_stage(shadow_project: Path, prep_res: dict | None, cid: str, checks: dict, verified: list[str], errors: list[str]) -> None:
	wf_path = shadow_project / '\ua616/data/workflow.json'
	if wf_path.is_file():
		state = workflow.load(shadow_project)
		if 'complete' == state.get('stages', {}).get('finalize', {}).get('status'):
			checks['stage_finalize'] = {'status': 'complete', 'already_complete': True}
			verified.append('stage_finalize')
		else:
			reply_p = Path(str(prep_res['response_file'])) if isinstance(prep_res, dict) and prep_res.get('response_file') else _find_reply_path(shadow_project, cid)
			if None is reply_p or (not reply_p.is_file()):
				errors.append('stage_finalize: Missing prepared journal reply file')
			else:
				_execute_finalize_reply(shadow_project, reply_p, checks, verified, errors)
# @used-by :func:`_execute_replay_pipeline()`
def _run_pre_invocation(target_root: Path, shadow_launcher: Path | None, cid: str, native_tx: Path | None, backend: Path, checks: dict, verified: list[str], errors: list[str]) -> None:
	_ensure_scripts_path()
	import check_pre_invocation
	l_turns = project_paths(shadow_launcher, exact_root=True).turns_dir if None is not shadow_launcher else None
	before = {p.name for p in l_turns.glob('*.json')} if None is not l_turns and l_turns.is_dir() else set()
	payload = {'cwd': str(target_root), 'conversationId': cid, **({'transcriptPath': str(native_tx)} if None is not native_tx else {})}
	res = check_pre_invocation.evaluate_pre_invocation_payload(payload, backend_override=backend)
	after = {p.name for p in l_turns.glob('*.json')} if None is not l_turns and l_turns.is_dir() else set()
	orphans = len(after - before)
	checks['pre_invocation'] = {'target': str(target_root), 'termination': res.get('terminationBehavior'), 'launcher_orphans_created': orphans}
	if 'terminate' == res.get('terminationBehavior') or 0 < orphans:
		errors.append(f'pre_invocation failed (termination={res.get("terminationBehavior")}, launcher_orphans_created={orphans})')
	else:
		verified.append('pre_invocation')
# @used-by :func:`_execute_replay_pipeline()`
def _run_review_stage(shadow_project: Path, cand_body: str, checks: dict, verified: list[str], errors: list[str]) -> None:
	wf_path = shadow_project / '\ua616/data/workflow.json'
	if wf_path.is_file():
		state = workflow.load(shadow_project)
		if state.get('reviews'):
			try:
				auth = review.authorize(shadow_project, state, response=cand_body or None)
				checks['review_authorization'] = {'authorized': True, 'risk': auth.get('risk'), 'review_ids': auth.get('review_ids') or []}
				verified.append('review_authorization')
			except (OSError, ValueError) as exc:
				checks['review_authorization'] = {'authorized': False, 'error': str(exc)}
				errors.append(f'review_authorization: {exc}')
# @used-by :func:`_execute_replay_pipeline()`
def _run_stop_gate(target_root: Path, stage_name: str, cid: str, stop_tx: Path | None, backend: Path, checks: dict, verified: list[str], errors: list[str]) -> None:
	_ensure_scripts_path()
	import check_stop_gate
	if None is stop_tx:
		errors.append(f'{stage_name}: Native transcript unavailable')
	else:
		payload = {'cwd': str(target_root), 'conversationId': cid, 'terminationReason': 'NO_TOOL_CALL', 'fullyIdle': True, 'transcriptPath': str(stop_tx)}
		res = check_stop_gate.evaluate_stop_payload(payload, backend_override=backend)
		checks[stage_name] = res
		if 'allow' == res.get('decision'):
			verified.append(stage_name)
		else:
			errors.append(f"{stage_name} blocked: {res.get('reason') or res}")
# @used-by :func:`_execute_replay_pipeline()`
def _run_turn_begin(shadow_project: Path, cid: str, platform: str, backend: Path, checks: dict, verified: list[str], errors: list[str]) -> None:
	try:
		res = completion.begin(shadow_project, cid, platform=platform, backend=backend)
		rec_errs = [item for item in (res.get('reconciled') or ()) if isinstance(item, dict) and item.get('error')]
		checks['turn_begin'] = {'turn_key': res.get('turn_key'), 'status': res.get('status'), 'reconciled_error_count': len(rec_errs), 'reconciled_errors': rec_errs}
		if rec_errs:
			errors.append(f'turn_begin reconciliation errors: {rec_errs}')
		else:
			verified.append('turn_begin')
	except (OSError, ValueError) as exc:
		checks['turn_begin'] = {'error': str(exc)}
		errors.append(f'turn_begin: {exc}')
# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.run()`
def _remap_staged_copies(src_project: Path, shadow_project: Path, src_launcher: Path | None, shadow_launcher: Path | None, old_states: dict[str, Path]) -> None:
	remap_shadow_state(src_project, shadow_project, old_state=old_states['project'])
	if None is not src_launcher and None is not shadow_launcher:
		remap_shadow_state(src_launcher, shadow_launcher, extra_pairs=((src_project, shadow_project),), old_state=old_states['launcher'])
# @used-by :func:`_prepare_shadow_stage()`
def _stage_shadow_copies(src_project: Path, src_launcher: Path | None, shadow_root: Path) -> tuple[Path, Path | None, dict[Path, Path], dict[str, Path]]:
	shadow_project = shadow_root / 'project'
	clone_project_tree(src_project, shadow_project, hardlink_evidence=True)
	old_states = {'project': state_dir(resolve_journal_dir(src_project))}
	relocations = {src_project: shadow_project}
	shadow_launcher = None
	if None is not src_launcher:
		shadow_launcher = shadow_root / 'launcher'
		clone_project_tree(src_launcher, shadow_launcher, hardlink_evidence=False)
		old_states['launcher'] = state_dir(resolve_journal_dir(src_launcher))
		relocations[src_launcher] = shadow_launcher
	return (shadow_project, shadow_launcher, relocations, old_states)
# 2026-11-26 "Add mutating command execution mode to shadow-replay with isolated native profiles": https://github.com/dmitry-ai/harness/issues/289
# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.run()`
def _prepare_shadow_stage(src_project: Path, src_launcher: Path | None, shadow_root: Path, command_mode: bool) -> tuple[Path, Path | None, dict[Path, Path], dict[str, Path], Path | None]:
	if command_mode:
		r = stage_command_shadow_copies(src_project, src_launcher, shadow_root)
	else:
		sp, sl, relocs, states = _stage_shadow_copies(src_project, src_launcher, shadow_root)
		r = (sp, sl, relocs, states, None)
	return r
# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.run()`
def _run_shadow_mode(src_project: Path, shadow_project: Path, shadow_launcher: Path | None, shadow_daily: Path | None, shadow_root: Path, *, cid: str, platform: str, backend: str | Path | None, response_file: str | Path | None, exec_rename_domain: str | None, command: str | None, checks: dict, verified: list[str], errors: list[str]) -> None:
	if exec_rename_domain or command:
		execute_shadow_command(src_project, shadow_project, shadow_launcher, shadow_daily, shadow_root, exec_rename_domain=exec_rename_domain, command=command, checks=checks, verified=verified, errors=errors)
	elif not cid:
		raise ValueError('shadow-replay requires --conversation, --exec-rename-domain, or --command')
	else:
		backend_dir, native_tx = _resolve_native_paths(cid, Path(backend).resolve() if None is not backend else None)
		_execute_replay_pipeline(shadow_project, shadow_launcher, shadow_root, cid, platform, backend_dir, native_tx, Path(response_file).resolve() if None is not response_file else None, checks, verified, errors)
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`agent_tools.cli_registry._exec_shadow_replay()`
def run_shadow_replay(project: str | Path, conversation_id: str | None=None, *, launcher: str | Path | None=None, workspace: str | Path | None=None, platform: str='antigravity', backend: str | Path | None=None, response_file: str | Path | None=None, keep: bool=False, exec_rename_domain: str | None=None, command: str | None=None) -> dict:
	from Df.Harness.Shadow.ReplayRunner import ReplayRunner
	return ReplayRunner(project, conversation_id, launcher=launcher, workspace=workspace, platform=platform, backend=backend, response_file=response_file, keep=keep, exec_rename_domain=exec_rename_domain, command=command).run()