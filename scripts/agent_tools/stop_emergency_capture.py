# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib
from . import admission, journal
from .metadata import build_journal_metadata, prepend_metadata_header, strip_leading_metadata_header
from .storage import locked
# @used-by :func:`_record_emergency_files()`
def _build_emergency_response(root: Path, native: dict[str, Any], turn: dict[str, Any], raw_text: str, reason: str, *, jdir: Path, steps: list[int], turn_key: str, state_path: Path, group_file: Path, conv_steps: list[int]) -> str:
	meta = build_journal_metadata(root, native, turn, journal_dir=jdir, steps=steps, turn_key=turn_key, turn_state_path=state_path, group_file=group_file, conversation_steps=conv_steps)
	j_sec = meta.setdefault('Journal', {})
	j_sec['Provenance'] = 'stop_gate_emergency_capture'
	j_sec['Preparation Verified'] = False
	j_sec['FILE-3 Warning'] = reason
	return prepend_metadata_header(raw_text, meta)
# @used-by :func:`maybe_emergency_capture_journal()`
def _find_target_turn(native: dict[str, Any], last_user_step: int) -> dict[str, Any] | None:
	r = None
	owned = [item for item in reversed(native.get('turns') or ()) if item.get('owned')]
	for item in owned:
		if last_user_step == item.get('start_step') or any((last_user_step == req.get('native_step') for req in item.get('requests') or ())):
			r = item
			break
	if None is r and owned:
		r = owned[0]
	return r
# @used-by :func:`_record_emergency_locked()`
def _persist_emergency_state(completion_mod, path: Path, value: dict[str, Any], recorded: dict[str, Any], *, reason: str, jdir: Path, request_ids: list[str]) -> dict[str, Any]:
	value['prepared'] = None
	value['journal_record'] = recorded
	value['completion_provenance'] = 'stop_gate_emergency_capture'
	value['preparation_verified'] = False
	value['recovered_after_delivery'] = True
	value['emergency_capture'] = {'captured_at': recorded['recorded_at'], 'reason': reason, 'journal_steps': list(recorded['journal_steps'])}
	value.pop('reserved_journal_steps', None)
	completion_mod._persist(path, value)
	journal.release_turn_steps(jdir, value['key'], request_ids=request_ids)
	return {'captured': True, 'turn_key': value['key'], 'journal_steps': list(recorded['journal_steps'])}
# @used-by :func:`_record_emergency_locked()`
def _record_emergency_files(root: Path, native: dict[str, Any], turn: dict[str, Any], raw_text: str, reason: str, *, jdir: Path, turn_key: str, state_path: Path, completion_mod) -> tuple[dict[str, Any], list[str]] | None:
	r = None
	token, request_ids = completion_mod._group(root, native, turn, raw_text, jdir)
	group_file = journal.state_dir(jdir) / 'answer-groups' / (token + '.json')
	if not (group_file.exists() and 'complete' == completion_mod._read(group_file).get('status')):
		steps_res = journal.reserve_turn_steps(jdir, turn_key, native['conversation_id'], request_ids)
		conv_steps = completion_mod.conversation_journal_steps(root, jdir, native['conversation_id'])
		eff_resp = _build_emergency_response(root, native, turn, raw_text, reason, jdir=jdir, steps=steps_res, turn_key=turn_key, state_path=state_path, group_file=group_file, conv_steps=conv_steps)
		eff_reqs = [req['text'] for req in turn['requests']]
		identity = admission.binding(jdir, eff_reqs, eff_resp, token, request_ids)
		cap = admission.capture([root, jdir], eff_reqs, eff_resp, identity)
		steps = journal.record_answer(jdir, eff_reqs, eff_resp, token, request_ids, admission=cap, reserved_turn_key=turn_key)
		_, res_dir = journal.journal_pair_dirs(jdir)
		body_sha = hashlib.sha256(strip_leading_metadata_header(raw_text).encode('utf-8')).hexdigest()
		rec = {'journal_steps': steps, 'response_sha256': hashlib.sha256(eff_resp.encode('utf-8')).hexdigest(), 'body_sha256': body_sha, 'response_file': str(journal.step_file(res_dir, steps[0], directory=jdir)), 'group_file': str(group_file), 'group_sha256': hashlib.sha256(group_file.read_bytes()).hexdigest(), 'recorded_at': completion_mod._now(), 'reused_complete_journal_group': False, 'admission': cap.reference}
		r = (rec, request_ids)
	return r
# @used-by :func:`maybe_emergency_capture_journal()`
def _record_emergency_locked(root: Path, native: dict[str, Any], turn: dict[str, Any], raw_text: str, reason: str, completion_mod) -> dict[str, Any] | None:
	r = None
	path, value = completion_mod._state(root, native, turn, recovered=True, allow_extended=True)
	if None is completion_mod._recorded(value) and 'handed_off' != value.get('status'):
		jdir = completion_mod._directory(root, value['journal'])
		journal.ensure_project_journal_upgraded(root, selected=jdir)
		written = _record_emergency_files(root, native, turn, raw_text, reason, jdir=jdir, turn_key=value['key'], state_path=path, completion_mod=completion_mod)
		if None is not written:
			r = _persist_emergency_state(completion_mod, path, value, written[0], reason=reason, jdir=jdir, request_ids=written[1])
	return r
# 2026-11-26
# "Persist emergency journal capture on Stop Gate fail-open and sync idle foreign reservations in turn-begin":
# https://github.com/dmitry-ai/harness/issues/255
# @used-by :func:`agent_tools.stop_hook_guard._evaluate_continuation_reentry()`
# @used-by :mod:`agent_tools.stop_emergency_capture`
def maybe_emergency_capture_journal(root_or_data: Path, session_id: str, last_user_step: int, matched_state: dict | None, decision: dict, emergency_ctx: dict[str, Any] | None) -> dict[str, Any] | None:
	r: dict[str, Any] | None = None
	raw_text = str((emergency_ctx or {}).get('last_planner_text') or '')
	if None is not emergency_ctx and raw_text.strip() and session_id:
		try:
			from . import completion
			root = Path(emergency_ctx['root']).resolve()
			native = completion._native(root, session_id, platform='antigravity', backend=emergency_ctx.get('backend'))
			turn = _find_target_turn(native, last_user_step)
			if None is not turn and turn.get('requests'):
				key = completion._key(native, turn)
				reason = str(decision.get('reason') or 'Stop Gate fail-open')
				with locked(completion._turn_lock(root, key)):
					r = _record_emergency_locked(root, native, turn, raw_text, reason, completion)
		except Exception:
			r = None
	return r
__all__ = ['maybe_emergency_capture_journal']