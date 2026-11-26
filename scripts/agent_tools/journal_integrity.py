# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Harden follow-up launcher handoff and journal reservation integrity":
# https://github.com/dmitry-ai/harness/issues/269
from __future__ import annotations
from pathlib import Path
import json
import re
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
from Df.Core.lib.json_io import df_json_dict_load
from . import journal
from .diagnostics import problem
SEQUENCE_RECOVERY_FILE = 'sequence-recovery.json'
_OTHER_JOB_RE = re.compile('~(\\d{10,})')
_TURN_AUX_SUFFIXES = ('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json', '-mechanical-exempt.json')
# @used-by :func:`validate_finalize_journal()`
def _check_reconciliation_failures(root: Path, cids: set[str]) -> None:
	by_key, _ = _turn_index_for_project(root)
	for st in by_key.values():
		cid = str(st.get('conversation_id') or '').strip().lower()
		rec = st.get('native_reconciliation')
		if (not cids or cid in cids) and isinstance(rec, dict) and False is rec.get('valid'):
			err_text = rec.get('error') or 'unknown'
			raise ValueError(f'Unresolved native_reconciliation error before finalizing: {err_text}')
# @used-by :func:`_eligible_active_turn_keys()`
# @used-by :func:`collect_conversation_journal_steps()`
def _committed_turn_steps(st_obj: dict) -> list[int]:
	r: list[int] = []
	for slot in ('prepared', 'journal_record', 'delivery'):
		rec = st_obj.get(slot)
		if isinstance(rec, dict) and isinstance(rec.get('journal_steps'), list):
			r.extend((s for s in rec['journal_steps'] if int is type(s) and 1 <= s))
	return r
# @used-by :func:`collect_conversation_journal_steps()`
def _eligible_active_turn_keys(cid_turns: list[tuple[str, dict]]) -> tuple[set[str], set[int]]:
	max_start = max((st['native_start_step'] for _, st in cid_turns if isinstance(st.get('native_start_step'), int)), default=-1)
	keys: set[str] = set()
	steps: set[int] = set()
	for t_key, st in cid_turns:
		rec = st.get('native_reconciliation')
		st_start = st['native_start_step'] if isinstance(st.get('native_start_step'), int) else max_start
		if (not _committed_turn_steps(st)) and 'open' == st.get('status') and (not (isinstance(rec, dict) and False is rec.get('valid'))) and st_start >= max_start:
			keys.add(t_key)
			if isinstance(st.get('reserved_journal_steps'), list):
				steps.update((s for s in st['reserved_journal_steps'] if int is type(s) and 1 <= s))
	return (keys, steps)
# @used-by :func:`collect_conversation_journal_steps()`
def _group_steps_for_cid(jdir: Path, cid: str, iter_groups_fn) -> set[int]:
	steps: set[int] = set()
	req_prefix, turn_prefix = (cid + '-', f'ag-{cid}-')
	for _, group in iter_groups_fn(jdir, ignore_errors=True):
		rids = group.get('request_ids') or ()
		t_name = str(group.get('turn') or '').lower()
		if any((isinstance(rid, str) and rid.lower().startswith(req_prefix) for rid in rids)) or t_name.startswith(turn_prefix):
			steps.update((st for st in (group.get('steps') or ()) if int is type(st) and 1 <= st))
	return steps
# @used-by :func:`_turn_index_for_project()`
# @used-by :func:`collect_conversation_journal_steps()`
# @used-by :func:`collect_handed_off_conversations()`
def _iter_turn_states(turns_dir: Path, read_fn) -> list[tuple[Path, dict]]:
	r: list[tuple[Path, dict]] = []
	if turns_dir.is_dir():
		for sf in sorted(turns_dir.glob('*.json')):
			if not sf.name.endswith(_TURN_AUX_SUFFIXES):
				try:
					obj = read_fn(sf)
					if isinstance(obj, dict):
						r.append((sf, obj))
				except (OSError, ValueError):
					pass
	return r
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`_turn_index_for_project()`
# @used-by :func:`acknowledged_sequence_gaps()`
# @used-by :func:`prune_terminal_conflict_reservations()`
def _load_json_dict(path: Path) -> dict | None:
	return df_json_dict_load(path)
# @used-by :func:`turn_matches_handoff()`
def _mentioned_other_job(reqs: list[dict], job_str: str) -> bool:
	target_num = str(job_str or '').lstrip('~').strip()
	r = False
	if target_num:
		for req in reqs:
			found = _OTHER_JOB_RE.findall(str(req.get('text') or ''))
			if any((num != target_num for num in found)):
				r = True
				break
	return r
# 2026-11-26 "Reconcile idle prepared turns and verify liveness for orphaned reservations": https://github.com/dmitry-ai/harness/issues/295
# @used-by unused
def _reservation_orphan_reason(r_key: str, entry: dict, max_existing: int, committed_rids: set[str], by_key: dict[str, dict], max_start_by_cid: dict[str, int], *, require_empty: bool) -> str | None:
	from .journal_liveness import classify_reservation_entry
	return classify_reservation_entry(r_key, entry, max_existing, committed_rids, by_key, max_start_by_cid, require_empty=require_empty, turn_reason_fn=_turn_state_orphan_reason)[0]
# @used-by :func:`prune_overlapping_reservations()`
def _subtract_entry_overlap(entry: dict, req_set: set[str], committed_steps: set[int]) -> tuple[dict | None, bool]:
	e_reqs = list(entry.get('request_ids') or ())
	e_steps = list(entry.get('steps') or ())
	if e_reqs and len(e_reqs) == len(e_steps):
		kept = [(rid, st) for rid, st in zip(e_reqs, e_steps) if rid not in req_set and st not in committed_steps]
		changed = len(kept) != len(e_reqs)
		new_entry = {**entry, 'request_ids': [p[0] for p in kept], 'steps': [p[1] for p in kept]} if kept else None
		r = (new_entry, changed)
	else:
		kept_reqs = [rid for rid in e_reqs if rid not in req_set]
		kept_steps = [st for st in e_steps if st not in committed_steps]
		changed = kept_reqs != e_reqs or kept_steps != e_steps
		drop = (not kept_steps) or (bool(e_reqs) and not kept_reqs)
		r = (None if drop else {**entry, 'request_ids': kept_reqs, 'steps': kept_steps}, changed)
	return r
# @used-by :func:`_check_reconciliation_failures()`
# @used-by :func:`classify_reservations()`
def _turn_index_for_project(project_root: Path | None) -> tuple[dict[str, dict], dict[str, int]]:
	by_key: dict[str, dict] = {}
	max_start: dict[str, int] = {}
	if None is not project_root:
		turns_dir = Path(project_root) / '\ua616/data/turns'
		for sf, obj in _iter_turn_states(turns_dir, _load_json_dict):
			t_key = str(obj.get('key') or sf.stem)
			by_key[t_key] = obj
			cid = str(obj.get('conversation_id') or '').strip().lower()
			start = obj.get('native_start_step')
			if cid and isinstance(start, int):
				max_start[cid] = max(start, max_start.get(cid, -1))
	return (by_key, max_start)
# @used-by :func:`_reservation_orphan_reason()`
# @used-by :func:`classify_reservations()`
def _turn_state_orphan_reason(r_key: str, st: dict, cid: str, max_start_by_cid: dict[str, int]) -> str | None:
	rec = st.get('native_reconciliation')
	start = st.get('native_start_step')
	st_val = st.get('status')
	if 'open' != st_val:
		r = f'orphaned reservation {r_key} belongs to non-open turn (status={st_val})'
	elif isinstance(rec, dict) and False is rec.get('valid'):
		r = f'orphaned reservation {r_key} belongs to turn with failed native_reconciliation'
	elif cid and isinstance(start, int) and start < max_start_by_cid.get(cid, start):
		r = f'orphaned reservation {r_key} belongs to superseded turn (start_step={start})'
	else:
		r = None
	return r
# @used-by :func:`missing_contiguous_steps()`
def acknowledged_sequence_gaps(jdir: Path) -> set[int]:
	data = _load_json_dict(journal.state_dir(Path(jdir).resolve()) / SEQUENCE_RECOVERY_FILE)
	r: set[int] = set()
	if isinstance(data, dict) and str(data.get('reason') or data.get('note') or '').strip():
		r = {s for s in (data.get('acknowledged_gaps') or ()) if int is type(s) and 1 <= s}
	return r
# @used-by :func:`finalize_project_check()`
def check_project_journal_problems(pp) -> list[dict]:
	r: list[dict] = []
	jdir = pp.journal_dir
	if jdir.is_dir():
		ids = journal.get_existing_step_ids(jdir)
		missing = missing_contiguous_steps(jdir, ids)
		if missing:
			nums = ', '.join((str(s) for s in missing))
			r.append(problem('journal.step_gap', pp.rel_to_root(jdir), f'Missing contiguous journal steps: {nums} (recover missing pairs or document {SEQUENCE_RECOVERY_FILE})', file=jdir))
		res_file = journal.state_dir(jdir) / journal.TURN_RESERVATIONS_FILE
		for msg in orphaned_reservation_issues(jdir, project_root=pp.root):
			r.append(problem('journal.orphaned_reservation', pp.rel_to_root(res_file), msg, file=res_file))
	return r
# @used-by :func:`agent_tools.completion.conversation_journal_steps()`
def collect_conversation_journal_steps(t_dir: Path, jdir: Path, cid: str, *, iter_groups_fn, iter_res_fn, read_fn, same_j_fn) -> list[int]:
	steps = _group_steps_for_cid(jdir, cid, iter_groups_fn)
	cid_turns: list[tuple[str, dict]] = []
	for sf, st_obj in _iter_turn_states(t_dir, read_fn):
		if str(st_obj.get('conversation_id') or '').strip().lower() == cid and (not st_obj.get('journal') or same_j_fn(st_obj.get('journal'), jdir)):
			cid_turns.append((str(st_obj.get('key') or sf.stem), st_obj))
			steps.update(_committed_turn_steps(st_obj))
	eligible_keys, active_res = _eligible_active_turn_keys(cid_turns)
	steps.update(active_res)
	for r_key, entry in iter_res_fn(jdir).items():
		if str(entry.get('conversation_id') or '').strip().lower() == cid and (r_key in eligible_keys or not cid_turns):
			steps.update((s for s in (entry.get('steps') or ()) if int is type(s) and 1 <= s))
	return sorted(steps)
# @used-by :func:`agent_tools.completion.handoff_launcher_turn()`
def collect_handed_off_conversations(turns_dir: Path, target_p: Path, *, read_fn, same_root_fn) -> set[str]:
	r: set[str] = set()
	for _, st in _iter_turn_states(turns_dir, read_fn):
		if 'handed_off' == st.get('status'):
			dest = st.get('handed_off_to') if isinstance(st.get('handed_off_to'), dict) else {}
			cid = str(st.get('conversation_id') or '').strip().lower()
			if cid and same_root_fn(dest.get('project_root'), target_p):
				r.add(cid)
	return r
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor.check_project()`
def finalize_project_check(pp, issues: list[dict], default_file: Path) -> dict:
	issues.extend(check_project_journal_problems(pp))
	for issue in issues:
		if not issue.get('file'):
			issue['file'] = str(default_file)
	return {'valid': not issues, 'issues': issues, 'semantic_truth_verified': False}
# @used-by :func:`agent_tools.project_rename_verify._collect_journal_errors()`
# @used-by :func:`validate_step_cli()`
def journal_validation_errors(jdir: Path, *, project_root: Path | None=None, strict_sequence: bool=False) -> list[str]:
	eff = Path(jdir).resolve()
	r: list[str] = []
	if strict_sequence:
		missing = missing_contiguous_steps(eff, journal.get_existing_step_ids(eff))
		if missing:
			nums = ', '.join((str(s) for s in missing))
			r.append(f'Missing contiguous journal steps: {nums} (recover missing pairs or document {SEQUENCE_RECOVERY_FILE})')
		inferred = project_root if None is not project_root else (eff.parent if (eff.parent / '\ua616/data/turns').is_dir() else None)
		r.extend(orphaned_reservation_issues(eff, project_root=inferred))
	return r
# @used-by :func:`check_project_journal_problems()`
# @used-by :func:`journal_validation_errors()`
# @used-by :func:`validate_finalize_journal()`
def missing_contiguous_steps(jdir: Path, ids: set[int]) -> list[int]:
	r: list[int] = []
	if ids:
		expected = set(range(1, max(ids) + 1))
		r = sorted((expected - set(ids)) - acknowledged_sequence_gaps(jdir))
	return r
# 2026-11-26 "Reconcile idle prepared turns and verify liveness for orphaned reservations": https://github.com/dmitry-ai/harness/issues/295
# @used-by :func:`orphaned_reservation_issues()`
# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_live_running_parallel_reservation_not_orphaned_while_idle_stuck_is_orphaned()`
def classify_reservations(jdir: Path, *, project_root: Path | None=None, conversation_ids: set[str] | None=None, require_empty_for_cids: bool=False) -> dict[str, list]:
	from .journal_liveness import classify_reservation_entry
	eff = Path(jdir).resolve()
	reservations = journal.iter_turn_reservations(eff)
	orphaned, active_parallel = ([], [])
	if reservations:
		max_existing = max(journal.get_existing_step_ids(eff), default=0)
		committed_rids = set(journal.completed_request_group_index(eff))
		by_key, max_start_by_cid = _turn_index_for_project(project_root)
		for r_key, entry in sorted(reservations.items()):
			cid = str(entry.get('conversation_id') or '').strip().lower()
			if None is not conversation_ids and cid not in conversation_ids:
				continue
			err, live = classify_reservation_entry(r_key, entry, max_existing, committed_rids, by_key, max_start_by_cid, require_empty=require_empty_for_cids, turn_reason_fn=_turn_state_orphan_reason)
			if None is not err:
				orphaned.append(err)
			elif None is not live:
				active_parallel.append(live)
	return {'orphaned': orphaned, 'active_parallel': active_parallel}
# @used-by :func:`check_project_journal_problems()`
# @used-by :func:`journal_validation_errors()`
# @used-by :func:`validate_finalize_journal()`
def orphaned_reservation_issues(jdir: Path, *, project_root: Path | None=None, conversation_ids: set[str] | None=None, require_empty_for_cids: bool=False) -> list[str]:
	return classify_reservations(jdir, project_root=project_root, conversation_ids=conversation_ids, require_empty_for_cids=require_empty_for_cids)['orphaned']
# 2026-11-26 "Harden addon companion observability and conflict reservation hygiene": https://github.com/dmitry-ai/harness/issues/302
# @used-by :func:`agent_tools.completion._conflict()`
# @used-by :mod:`agent_tools.journal_sync_all`
def finalize_conflict_turn(root_p: Path, path: Path, value: dict, turn: dict, *, dir_fn, persist_fn) -> None:
	value.pop('reserved_journal_steps', None)
	persist_fn(path, value)
	if value.get('journal') and value.get('key'):
		req_ids = [req['id'] for req in (turn.get('requests') or ()) if isinstance(req, dict) and req.get('id')]
		journal.release_turn_steps(dir_fn(root_p, value['journal']), value['key'], request_ids=req_ids)
# 2026-11-26 "Harden addon companion observability and conflict reservation hygiene": https://github.com/dmitry-ai/harness/issues/302
# @used-by :func:`prune_terminal_conflict_reservations()`
def _is_terminal_conflict(st: dict | None, entry: dict, max_existing: int) -> bool:
	r = False
	if isinstance(st, dict) and 'conflict' == st.get('status'):
		delivery = st.get('delivery') if isinstance(st.get('delivery'), dict) else {}
		e_steps = [s for s in (entry.get('steps') or ()) if int is type(s) and 1 <= s]
		r = False is delivery.get('retryable') or bool(delivery.get('conflict_evidence')) or any((s <= max_existing for s in e_steps))
	return r
# 2026-11-26 "Harden addon companion observability and conflict reservation hygiene": https://github.com/dmitry-ai/harness/issues/302
# @used-by :func:`agent_tools.journal_sync_all.reconcile_foreign_open_reservations()`
# @used-by :func:`agent_tools.journal_sync_all.sync_all_open()`
# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_conflict_recording_and_reconciliation_prune_terminal_reservations()`
def prune_terminal_conflict_reservations(root: Path, jdir: Path, *, folder_fn, read_fn) -> list[str]:
	pruned: list[str] = []
	turns_dir = folder_fn(root)
	max_existing = max(journal.get_existing_step_ids(jdir), default=0)
	for turn_key, entry in sorted(journal.iter_turn_reservations(jdir).items()):
		st_path = turns_dir / f'{turn_key}.json'
		st = _load_json_dict(st_path) if st_path.is_file() else None
		if _is_terminal_conflict(st, entry, max_existing):
			if journal.release_turn_steps(jdir, turn_key, request_ids=list(entry.get('request_ids') or ())):
				pruned.append(turn_key)
	return pruned
# @used-by :func:`agent_tools.journal.record_answer()`
# @used-by :func:`agent_tools.journal.release_turn_steps()`
def prune_overlapping_reservations(reservations: dict[str, dict], turn_key: str | None, req_set: set[str], committed_steps: set[int]) -> bool:
	changed = False
	if turn_key and turn_key in reservations:
		del reservations[turn_key]
		changed = True
	if req_set or committed_steps:
		for r_key in list(reservations):
			updated, hit = _subtract_entry_overlap(reservations[r_key], req_set, committed_steps)
			if hit:
				changed = True
				if None is updated:
					del reservations[r_key]
				else:
					reservations[r_key] = updated
	return changed
# @used-by :func:`agent_tools.completion.begin()`
def sync_begin_turn_state(root: Path, value: dict, native: dict, turn: dict, native_reconciliation: dict | None, *, dir_fn, recorded_fn, reserve_fn) -> None:
	if 'open' == value.get('status') and (not recorded_fn(value)) and (not turn.get('completed')):
		req_ids = [req['id'] for req in (turn.get('requests') or ()) if isinstance(req, dict) and req.get('id')]
		if req_ids:
			value['reserved_journal_steps'] = reserve_fn(dir_fn(root, value['journal']), value['key'], native['conversation_id'], req_ids)
	elif 'reserved_journal_steps' in value and recorded_fn(value):
		value.pop('reserved_journal_steps', None)
	if isinstance(native_reconciliation, dict):
		if False is native_reconciliation.get('valid'):
			value['native_reconciliation'] = native_reconciliation
		elif True is native_reconciliation.get('valid'):
			value.pop('native_reconciliation', None)
# @used-by :func:`agent_tools.completion.handoff_launcher_turn()`
def turn_matches_handoff(st: dict, st_cid: str, job_str: str | None, prior_cids: set[str], explicit_fn) -> bool:
	reqs = [x for x in (st.get('requests') or ()) if isinstance(x, dict)]
	if None is job_str:
		r = True
	elif any((explicit_fn(str(x.get('text') or ''), job_str)[0] for x in reqs)):
		r = True
	else:
		r = bool(st_cid and st_cid in prior_cids and (not _mentioned_other_job(reqs, job_str)))
	return r
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._finalize_stage()`
def validate_finalize_journal(root: Path, jdir: Path, state: dict) -> set[int]:
	ids = journal.get_existing_step_ids(jdir)
	if not ids or any((journal.step_errors(jdir, ident) for ident in ids)):
		raise ValueError('Complete exact req/res journal pairs before finalizing')
	missing = missing_contiguous_steps(jdir, ids)
	if missing:
		nums = ', '.join((str(s) for s in missing))
		raise ValueError(f'Missing contiguous journal steps before finalizing: {nums} (recover missing pairs or document {SEQUENCE_RECOVERY_FILE})')
	cids = {str(req.get('native_conversation_id') or '').strip().lower() for req in (state.get('requests') or ()) if isinstance(req, dict) and req.get('native_conversation_id')}
	orphans = orphaned_reservation_issues(jdir, project_root=root, conversation_ids=cids or None, require_empty_for_cids=bool(cids))
	if orphans:
		raise ValueError('; '.join(orphans))
	_check_reconciliation_failures(root, cids)
	return ids
# @used-by :func:`agent_tools.cli.main()`
def validate_step_cli(args) -> str:
	steps = sorted(journal.get_existing_step_ids(args.dir)) if args.all else [args.step]
	if not steps:
		raise ValueError('No journal steps found')
	errors = [error for step in steps for error in journal.step_errors(args.dir, step)]
	if args.all and getattr(args, 'strict_sequence', False):
		errors.extend(journal_validation_errors(args.dir, strict_sequence=True))
	if args.file:
		from .links import validate_file
		errors += [e for path in args.file for e in validate_file(path)]
	if errors:
		raise ValueError('\n'.join(errors))
	return f'Checked {len(steps)} journal pairs and {len(args.file)} explicit files; content truth and authorization require review'
