# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Journal.Publisher import Publisher
from Df.Harness.lib.admission_ops import dfh_admission_binding, dfh_capture_admission, dfh_verify_admission
from Df.Harness.lib.completion_checks import dfh_intermediate_or_language_issues
from Df.Harness.lib.completion_core import dfh_conversation_journal_steps, dfh_hash, dfh_journal_dir, dfh_now, dfh_read_meta, dfh_turn_key, dfh_turns_folder
from Df.Harness.lib.journal_core import dfh_journal_pair_dirs, dfh_norm_journal_response_text, dfh_norm_journal_text, dfh_parse_step_file_path, dfh_resolve_migrated_step_file, dfh_same_journal_identity, dfh_state_dir, dfh_step_file
from Df.Harness.lib.journal_records import dfh_find_orphan_or_overwritten_steps, dfh_iter_answer_group_records, dfh_verify_answer
from Df.Harness.lib.journal_reservations import dfh_release_turn_steps, dfh_reserve_turn_steps
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_same_project_root
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_record()`
def _build_record_receipt(root: Path, directory: Path, res_dir: Path, group_file: Path, steps: list[int], effective_response: str, clean_body_sha: str, existing: dict | None, already_complete: bool, reprepared: bool, adopted_existing: bool, proof: Any, verification: dict, ops: dict[str, Any]) -> tuple[dict, dict]:
	hash_fn = ops.get('hash') or dfh_hash
	now_fn = ops.get('now') or dfh_now
	recorded = {'journal_steps': steps, 'response_sha256': hash_fn(effective_response.encode('utf-8')), 'body_sha256': clean_body_sha, 'response_file': str(dfh_step_file(res_dir, steps[0], directory=directory)), 'group_file': str(group_file)}
	if existing:
		if existing.get('journal_steps') != recorded['journal_steps'] or existing.get('response_sha256') != recorded['response_sha256'] or (not dfh_same_turn_artifact_path(root, existing.get('response_file'), recorded['response_file'], kind='response')) or (not dfh_same_turn_artifact_path(root, existing.get('group_file'), recorded['group_file'], kind='group')):
			raise ValueError('Recorded answer receipt differs from its verified journal identity; preserve history')
		if existing.get('group_sha256') and existing['group_sha256'] != hash_fn(group_file.read_bytes()):
			raise ValueError('Recorded answer-group bytes changed; preserve history')
		r = (dict(existing), verification)
	else:
		res_receipt = {**recorded, 'group_sha256': hash_fn(group_file.read_bytes()), 'recorded_at': now_fn(), 'reused_complete_journal_group': bool((already_complete and (not reprepared)) or adopted_existing), 'admission': proof}
		if reprepared:
			res_receipt['reprepared_before_delivery'] = True
		r = (res_receipt, verification)
	return r
# @used-by :func:`dfh_record()`
def _commit_or_verify_journal_group(root: Path, native: dict, turn: dict, directory: Path, group_file: Path, token: str, request_ids: list[str] | None, effective_requests: list[str], effective_response: str, already_complete: bool, reprepared: bool, adopt_steps: list[int] | None, existing: dict | None, purpose: str, ops: dict[str, Any]) -> tuple[list[int], Any, dict]:
	key_fn = ops.get('key') or dfh_turn_key
	read_fn = ops.get('read') or dfh_read_meta
	identity = dfh_admission_binding(directory, effective_requests, effective_response, token, request_ids)
	if already_complete and (not reprepared):
		if 'publication' == purpose:
			from agent_tools.text_workflow import gate_requests
			gate_requests([root, directory], effective_requests, effective_response)
		steps = dfh_verify_answer(directory, effective_requests, effective_response, token, request_ids)
		dfh_release_turn_steps(directory, key_fn(native, turn), request_ids=request_ids)
		proof = read_fn(group_file).get('admission')
		if existing and existing.get('admission') != proof:
			raise ValueError('Recorded admission differs from the original answer group; preserve history')
		verification = dfh_verify_admission(proof, identity) if proof else {'status': 'legacy_proof_gap', 'scope': 'journal_and_native_identity_only'}
	else:
		capability = dfh_capture_admission([root, directory], effective_requests, effective_response, identity)
		steps = Publisher(directory, effective_requests, effective_response, token, request_ids, adopt_steps=adopt_steps, admission=capability, allow_reprepare=reprepared, reserved_turn_key=key_fn(native, turn)).run()
		proof = capability.reference
		verification = {'status': 'verified', 'scope': 'original_publication_admission' if 'observation' == purpose else 'current_publication_readiness'}
	return (steps, proof, verification)
# @used-by :func:`dfh_group()`
def _find_matching_groups(directory: Path, res_dir: Path, native_ids: list[str], turn: dict, response: str, norm_reqs: list[str], norm_resp: str, hash_fn, allow_reprepare: bool) -> list[dict]:
	matches: list[dict] = []
	for _, old in dfh_iter_answer_group_records(directory):
		if old.get('request_ids') == native_ids:
			if not _group_payload_matches(old, turn, response, directory, res_dir, norm_reqs, norm_resp, hash_fn, allow_reprepare):
				raise ValueError('A journal for these exact native request IDs has different bytes; preserve the conflict')
			matches.append(old)
	if 1 < len(matches):
		raise ValueError('More than one journal group claims these native request IDs; preserve the ambiguity')
	return matches
# @used-by :func:`_find_matching_groups()`
# @used-by :func:`_resolve_legacy_group()`
def _group_payload_matches(old: dict, turn: dict, response: str, directory: Path, res_dir: Path, norm_turn_reqs: list[str], norm_turn_resp: str, hash_fn, allow_reprepare: bool) -> bool:
	old_reqs = old.get('requests') or []
	reqs_ok = old_reqs == [req['text'] for req in turn['requests']] or [dfh_norm_journal_text(x) for x in old_reqs] == norm_turn_reqs
	resp_ok = old.get('response_sha256') == hash_fn(response.encode('utf-8'))
	if not resp_ok and old.get('steps'):
		res_p = dfh_step_file(res_dir, old['steps'][0], directory=directory)
		if res_p.is_file():
			try:
				disk_r = res_p.read_bytes().decode('utf-8')
				resp_ok = hash_fn(disk_r.encode('utf-8')) == old.get('response_sha256') and dfh_norm_journal_response_text(disk_r) == norm_turn_resp
			except (OSError, UnicodeDecodeError):
				pass
	return bool(reqs_ok and (resp_ok or allow_reprepare))
# @used-by :func:`dfh_record()`
def _maybe_prepend_journal_metadata(root: Path, native: dict, turn: dict, directory: Path, group_file: Path, request_ids: list[str] | None, effective_response: str, g_data: dict | None, already_complete: bool, adopted_existing: bool, reprepared: bool, ops: dict[str, Any]) -> str:
	from agent_tools.metadata import build_journal_metadata, extract_leading_metadata_header, prepend_metadata_header
	r = effective_response
	if ((not already_complete and (not adopted_existing)) or reprepared) and None is extract_leading_metadata_header(effective_response)[0]:
		turn_key = (ops.get('key') or dfh_turn_key)(native, turn)
		folder_fn = ops.get('folder') or dfh_turns_folder
		target_steps = list(g_data['steps']) if reprepared and isinstance(g_data, dict) and g_data.get('steps') else dfh_reserve_turn_steps(directory, turn_key, native['conversation_id'], request_ids)
		conv_steps = dfh_conversation_journal_steps(root, directory, native['conversation_id'], ops=ops)
		meta = build_journal_metadata(root, native, turn, journal_dir=directory, steps=target_steps, turn_key=turn_key, turn_state_path=folder_fn(root) / (turn_key + '.json'), group_file=group_file, conversation_steps=conv_steps)
		r = prepend_metadata_header(effective_response, meta)
	return r
# @used-by :func:`_resolve_record_payload()`
def _resolve_existing_group_payload(directory: Path, res_dir: Path, group_file: Path, effective_requests: list[str], effective_response: str, allow_reprepare: bool, ops: dict[str, Any]) -> tuple[dict, list[str], str, bool]:
	hash_fn = ops.get('hash') or dfh_hash
	g_data = (ops.get('read') or dfh_read_meta)(group_file)
	g_reqs = g_data.get('requests') or []
	if [dfh_norm_journal_text(x) for x in g_reqs] == [dfh_norm_journal_text(x) for x in effective_requests]:
		effective_requests = list(g_reqs)
	reprepared = False
	if g_data.get('steps') and hash_fn(effective_response.encode('utf-8')) != g_data.get('response_sha256'):
		res_p = dfh_step_file(res_dir, g_data['steps'][0], directory=directory)
		if res_p.is_file():
			try:
				disk_r = res_p.read_bytes().decode('utf-8')
				if hash_fn(disk_r.encode('utf-8')) == g_data.get('response_sha256') and dfh_norm_journal_response_text(disk_r) == dfh_norm_journal_response_text(effective_response):
					effective_response = disk_r
			except (OSError, UnicodeDecodeError):
				pass
		if hash_fn(effective_response.encode('utf-8')) != g_data.get('response_sha256') and allow_reprepare:
			reprepared = True
	return (g_data, effective_requests, effective_response, reprepared)
# @used-by :func:`dfh_group()`
def _resolve_legacy_group(groups: Path, legacy: str, turn: dict, response: str, directory: Path, res_dir: Path, norm_reqs: list[str], norm_resp: str, hash_fn, read_fn, allow_reprepare: bool) -> tuple[str, list[str] | None] | None:
	r: tuple[str, list[str] | None] | None = None
	if re.fullmatch('[A-Za-z0-9_-]{1,100}', legacy) and (groups / (legacy + '.json')).exists():
		old = read_fn(groups / (legacy + '.json'))
		if not _group_payload_matches(old, turn, response, directory, res_dir, norm_reqs, norm_resp, hash_fn, allow_reprepare):
			raise ValueError('Existing native-turn journal has different bytes; preserve the conflict')
		r = (legacy, old.get('request_ids'))
	return r
# @used-by :func:`dfh_record()`
def _resolve_record_payload(jdir: Path, res_dir: Path, group_file: Path, turn: dict, response: str, request_ids: list[str] | None, existing: dict | None, already_complete: bool, allow_reprepare: bool, ops: dict[str, Any]) -> tuple[list[str], str, list[int] | None, bool, bool, dict | None]:
	eff_reqs, eff_resp, adopt_steps, adopted, reprepared, g_data = ([r['text'] for r in turn['requests']], response, None, False, False, None)
	if already_complete:
		g_data, eff_reqs, eff_resp, reprepared = _resolve_existing_group_payload(jdir, res_dir, group_file, eff_reqs, eff_resp, allow_reprepare, ops)
	elif None is existing:
		adopt_steps, disk_reqs, disk_resp = dfh_find_orphan_or_overwritten_steps(jdir, eff_reqs, eff_resp, request_ids)
		if None is not adopt_steps:
			eff_reqs, eff_resp, adopted = (disk_reqs, disk_resp, True)
	return (eff_reqs, eff_resp, adopt_steps, adopted, reprepared, g_data)
# @used-by :func:`dfh_record()`
def _validate_record_preconditions(turn: dict, response: str, group_file: Path, existing: dict | None, already_complete: bool, allow_reprepare: bool, ops: dict[str, Any]) -> None:
	read_fn = ops.get('read') or dfh_read_meta
	if not already_complete or allow_reprepare:
		lang_issues = (ops.get('lang_issues') or (lambda reqs, resp: dfh_intermediate_or_language_issues(reqs, resp, ops=ops)))(turn['requests'], response)
		if lang_issues:
			raise ValueError('; '.join(lang_issues))
	if existing:
		if not already_complete:
			raise ValueError('Recorded answer-group receipt is missing or incomplete; preserve journal history')
		if read_fn(group_file).get('steps') != existing['journal_steps']:
			raise ValueError('Recorded answer-group steps changed; preserve journal history')
# @used-by :func:`dfh_record()`
def _verify_recorded_readback(directory: Path, req_dir: Path, res_dir: Path, steps: list[int], effective_requests: list[str], effective_response: str) -> None:
	for step, request in zip(steps, effective_requests):
		if dfh_step_file(req_dir, step, directory=directory).read_bytes() != request.encode('utf-8'):
			raise ValueError('Recorded request read-back differs from native text')
		if dfh_step_file(res_dir, step, directory=directory).read_bytes() != effective_response.encode('utf-8'):
			raise ValueError('Recorded response read-back differs from prepared text')
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :func:`agent_tools.completion._group()`
# @used-by :func:`dfh_record()`
def dfh_group(root: str | Path, native: dict, turn: dict, response: str, directory: Path, *, allow_reprepare: bool=False, ops: dict[str, Any] | None=None) -> tuple[str, list[str] | None]:
	eff_ops = ops or {}
	hash_fn, read_fn = (eff_ops.get('hash') or dfh_hash, eff_ops.get('read') or dfh_read_meta)
	key = 'native-' + (eff_ops.get('key') or dfh_turn_key)(native, turn)
	native_ids = [req['id'] for req in turn['requests']]
	norm_reqs = [dfh_norm_journal_text(req['text']) for req in turn['requests']]
	norm_resp = dfh_norm_journal_response_text(response)
	_, res_dir = dfh_journal_pair_dirs(directory)
	matches = _find_matching_groups(directory, res_dir, native_ids, turn, response, norm_reqs, norm_resp, hash_fn, allow_reprepare)
	if matches:
		r: tuple[str, list[str] | None] = (matches[0]['turn'], native_ids)
	else:
		leg = _resolve_legacy_group(dfh_state_dir(directory) / 'answer-groups', turn['turn_id'], turn, response, directory, res_dir, norm_reqs, norm_resp, hash_fn, read_fn, allow_reprepare)
		r = leg if None is not leg else (key, native_ids)
	return r
# @used-by :func:`agent_tools.completion._matches_recorded_response()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__check_reprepare_and_conflict()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__verify_delivered_fast_path()`
def dfh_matches_recorded_response(recorded: Any, raw_response: str, raw_sha: str, *, ops: dict[str, Any] | None=None) -> bool:
	hash_fn = (ops or {}).get('hash') or dfh_hash
	if not isinstance(recorded, dict):
		r = False
	elif recorded.get('response_sha256') == raw_sha or recorded.get('body_sha256') == raw_sha:
		r = True
	else:
		r = False
		raw_prep = recorded.get('response_file') or ''
		if raw_prep:
			prep_file = dfh_resolve_migrated_step_file(raw_prep)
			if prep_file.is_file():
				try:
					prep_text = prep_file.read_bytes().decode('utf-8')
					if hash_fn(prep_text.encode('utf-8')) == recorded.get('response_sha256'):
						from agent_tools.metadata import strip_leading_metadata_header
						r = hash_fn(strip_leading_metadata_header(prep_text).encode('utf-8')) == raw_sha
				except (OSError, UnicodeDecodeError):
					r = False
	return r
# @used-by :func:`agent_tools.completion._record()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__verify_delivered_fast_path()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer._record_journal_entry()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__try_record_turn()`
def dfh_record(root: str | Path, native: dict, turn: dict, response: str, directory: Any, *, existing: dict | None=None, purpose: str='publication', allow_reprepare: bool=False, ops: dict[str, Any] | None=None) -> tuple[dict, dict]:
	from agent_tools.metadata import strip_leading_metadata_header
	eff_ops = ops or {}
	if purpose not in ('publication', 'observation'):
		raise ValueError('Choose publication admission or historical observation')
	jdir = (eff_ops.get('directory') or dfh_journal_dir)(root, directory)
	req_dir, res_dir = dfh_journal_pair_dirs(jdir)
	clean_body_sha = (eff_ops.get('hash') or dfh_hash)(strip_leading_metadata_header(response).encode('utf-8'))
	token, request_ids = (eff_ops.get('group') or (lambda r, n, t, resp, d, **kw: dfh_group(r, n, t, resp, d, ops=eff_ops, **kw)))(root, native, turn, response, jdir, allow_reprepare=allow_reprepare)
	group_file = dfh_state_dir(jdir) / 'answer-groups' / (token + '.json')
	already_complete = group_file.exists() and 'complete' == (eff_ops.get('read') or dfh_read_meta)(group_file).get('status')
	_validate_record_preconditions(turn, response, group_file, existing, already_complete, allow_reprepare, eff_ops)
	eff_reqs, eff_resp, adopt_steps, adopted, reprepared, g_data = _resolve_record_payload(jdir, res_dir, group_file, turn, response, request_ids, existing, already_complete, allow_reprepare, eff_ops)
	eff_resp = _maybe_prepend_journal_metadata(Path(root), native, turn, jdir, group_file, request_ids, eff_resp, g_data, already_complete, adopted, reprepared, eff_ops)
	steps, proof, verification = _commit_or_verify_journal_group(Path(root), native, turn, jdir, group_file, token, request_ids, eff_reqs, eff_resp, already_complete, reprepared, adopt_steps, existing, purpose, eff_ops)
	_verify_recorded_readback(jdir, req_dir, res_dir, steps, eff_reqs, eff_resp)
	return _build_record_receipt(Path(root), jdir, res_dir, group_file, steps, eff_resp, clean_body_sha, existing, already_complete, reprepared, adopted, proof, verification, eff_ops)
# @used-by :func:`_build_record_receipt()`
def dfh_same_turn_artifact_path(root: Path, saved_str: str | None, current_str: str, *, kind: str) -> bool:
	if saved_str == current_str:
		r = True
	elif not isinstance(saved_str, str) or (not saved_str.strip()):
		r = False
	else:
		saved_p, cur_p = (Path(saved_str), Path(current_str))
		if saved_p.exists() or saved_p.name != cur_p.name:
			r = False
		elif 'response' == kind:
			s_info, c_info = (dfh_parse_step_file_path(saved_p), dfh_parse_step_file_path(cur_p))
			r = None is not s_info and None is not c_info and s_info[1] in ('res', '\u227a') and c_info[1] in ('res', '\u227a') and s_info[2] == c_info[2] and dfh_same_journal_identity(s_info[0], c_info[0])
		elif 'group' == kind and 'answer-groups' == saved_p.parent.name and 4 <= len(saved_p.parents) and 4 <= len(cur_p.parents) and '.journal' == saved_p.parents[2].name:
			canon_root = dfh_canonicalize_root_dir(root, dfh_load_registry())
			r = any((dfh_same_project_root(anc, canon_root) for anc in saved_p.parents[3:7])) and any((dfh_same_project_root(anc, canon_root) for anc in cur_p.parents[3:7]))
		else:
			r = False
	return r