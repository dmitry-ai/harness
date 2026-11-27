# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.journal_core import TURN_RESERVATIONS_FILE, dfh_state_dir
from Df.Harness.lib.storage import dfh_locked, dfh_replace_bytes
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_reserve_turn_steps()`
def _assign_reserved_steps(request_ids: list[str], committed_index: dict[str, tuple[dict, int]], existing_ids: set[int], old_map: dict[str, int], other_reserved: set[int]) -> tuple[list[int], bool]:
	assigned: list[int] = []
	assigned_set: set[int] = set()
	all_committed = True
	for rid in request_ids:
		if rid in committed_index:
			st = int(committed_index[rid][1])
		else:
			all_committed = False
			prev = old_map.get(rid)
			if None is not prev and prev not in existing_ids and prev not in other_reserved and prev not in assigned_set:
				st = prev
			else:
				st = max(existing_ids | other_reserved | assigned_set, default=0) + 1
		assigned.append(st)
		assigned_set.add(st)
	return (assigned, all_committed)
# @used-by :func:`dfh_read_turn_reservations()`
def _parse_reservation_map(raw: dict) -> dict[str, dict]:
	out: dict[str, dict] = {}
	for key, entry in raw['reservations'].items():
		if isinstance(key, str) and key.strip() and isinstance(entry, dict):
			steps = [st for st in (entry.get('steps') or ()) if int is type(st) and 1 <= st]
			if steps:
				rids = [str(rid) for rid in (entry.get('request_ids') or ()) if isinstance(rid, str) and rid]
				out[key] = {'conversation_id': str(entry.get('conversation_id') or ''), 'request_ids': rids, 'steps': steps}
	return out
# @used-by :func:`dfh_reserve_turn_steps()`
def _persist_reservation_update(eff: Path, reservations: dict[str, dict], turn_key: str, conversation_id: str, request_ids: list[str], assigned: list[int], all_committed: bool, old_entry: dict) -> None:
	if all_committed:
		if turn_key in reservations:
			del reservations[turn_key]
			dfh_write_turn_reservations(eff, reservations)
	else:
		new_entry = {'conversation_id': str(conversation_id or ''), 'request_ids': list(request_ids), 'steps': list(assigned)}
		if old_entry != new_entry:
			reservations[turn_key] = new_entry
			dfh_write_turn_reservations(eff, reservations)
# @used-by :func:`Df.Harness.lib.completion_core.dfh_conversation_journal_steps()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_prune_terminal_conflict_reservations()`
# @used-by :func:`Df.Harness.lib.journal_sync_ops._collect_all_open_candidates()`
# @used-by :func:`Df.Harness.lib.journal_sync_ops.dfh_reconcile_foreign_open_reservations()`
# @used-by :meth:`Df.Harness.Journal.IntegrityAuditor.IntegrityAuditor.run()`
# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_conflict_recording_and_reconciliation_prune_terminal_reservations()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_handoff_launcher_turn_cascades_followup_without_job_url_and_clears_reservation()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_record_answer_subtracts_overlapping_request_ids_and_excludes_stale_steps_from_title()`
# @used-by :meth:`test_service_finalization_exempt_and_sync_all_open.ServiceFinalizationAndSyncAllOpenTests.test_journal_sync_all_open_reconciles_idle_turns_and_honors_adopt_conflict()`
# @used-by :meth:`test_stop_emergency_capture_and_foreign_sync.StopEmergencyCaptureAndForeignSyncTests.test_begin_syncs_idle_open_foreign_reservation_and_skips_conflict_failed_and_running()`
# @used-by :meth:`test_stop_emergency_capture_and_foreign_sync.StopEmergencyCaptureAndForeignSyncTests.test_stop_gate_fail_open_persists_emergency_capture_and_sync_avoids_duplicate()`
def dfh_iter_turn_reservations(directory: Path) -> dict[str, dict]:
	return dfh_read_turn_reservations(directory)
# @used-by :func:`dfh_iter_turn_reservations()`
# @used-by :func:`dfh_release_turn_steps()`
# @used-by :func:`dfh_reserve_turn_steps()`
# @used-by :func:`dfh_reserved_step_ids()`
# @used-by :meth:`Df.Harness.Completion.NarrowReconciler.NarrowReconciler.__trim_narrowed_reservation()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__prune_reservations()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__resolve_steps()`
def dfh_read_turn_reservations(directory: Path) -> dict[str, dict]:
	res_file = dfh_state_dir(Path(directory).resolve()) / TURN_RESERVATIONS_FILE
	r: dict[str, dict] = {}
	if res_file.is_file():
		try:
			raw = json.loads(res_file.read_bytes().decode('utf-8'))
		except (OSError, UnicodeDecodeError, ValueError):
			raw = None
		if isinstance(raw, dict) and isinstance(raw.get('reservations'), dict):
			r = _parse_reservation_map(raw)
	return r
# @used-by :func:`Df.Harness.lib.completion_record._commit_or_verify_journal_group()`
# @used-by :func:`Df.Harness.lib.completion_recovery._handoff_single_turn()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._persist_emergency_state()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_finalize_conflict_turn()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_prune_terminal_conflict_reservations()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__complete_turn_delivery()`
def dfh_release_turn_steps(directory: Path, turn_key: str, *, request_ids: list[str] | None=None) -> bool:
	from Df.Harness.lib.journal_integrity_ops import dfh_prune_overlapping_reservations
	eff = Path(directory).resolve()
	journal_state = dfh_state_dir(eff)
	r = False
	if (journal_state / TURN_RESERVATIONS_FILE).is_file():
		with dfh_locked(journal_state / 'writer.lock'):
			reservations = dfh_read_turn_reservations(eff)
			r = dfh_prune_overlapping_reservations(reservations, turn_key, set(request_ids or ()), set())
			if r:
				dfh_write_turn_reservations(eff, reservations)
	return r
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_record._maybe_prepend_journal_metadata()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_conflict_recording_and_reconciliation_prune_terminal_reservations()`
# @used-by :meth:`test_atomic_prepare_and_narrowed_reconcile_m7.AtomicPrepareAndNarrowedReconcileM7Tests.test_narrowed_open_turn_reconciles_safely_and_trims_stale_reservation()`
# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_live_running_parallel_reservation_not_orphaned_while_idle_stuck_is_orphaned()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_handoff_launcher_turn_cascades_followup_without_job_url_and_clears_reservation()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_record_answer_subtracts_overlapping_request_ids_and_excludes_stale_steps_from_title()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_validate_step_strict_sequence_and_check_project_detect_gaps_and_orphans()`
def dfh_reserve_turn_steps(directory: Path, turn_key: str, conversation_id: str, request_ids: list[str]) -> list[int]:
	from Df.Harness.lib.journal_records import dfh_completed_request_group_index, dfh_get_existing_step_ids
	if not isinstance(turn_key, str) or (not turn_key.strip()) or (not isinstance(request_ids, list)) or (not request_ids) or any((not isinstance(x, str) or (not x) for x in request_ids)):
		raise ValueError('Stable turn key and nonempty exact request ID list required for step reservation')
	eff = Path(directory).resolve()
	journal_state = dfh_state_dir(eff)
	journal_state.mkdir(parents=True, exist_ok=True)
	with dfh_locked(journal_state / 'writer.lock'):
		committed_index = dfh_completed_request_group_index(eff)
		existing_ids = dfh_get_existing_step_ids(eff)
		reservations = dfh_read_turn_reservations(eff)
		old_entry = reservations.get(turn_key) if isinstance(reservations.get(turn_key), dict) else {}
		old_map = {rid: st for rid, st in zip(old_entry.get('request_ids') or (), old_entry.get('steps') or ()) if isinstance(rid, str) and int is type(st) and 1 <= st}
		other_reserved = {st for k, e in reservations.items() if k != turn_key for st in (e.get('steps') or ()) if int is type(st) and 1 <= st}
		assigned, all_committed = _assign_reserved_steps(request_ids, committed_index, existing_ids, old_map, other_reserved)
		_persist_reservation_update(eff, reservations, turn_key, conversation_id, request_ids, assigned, all_committed, old_entry)
	return assigned
# @used-by :func:`Df.Harness.lib.journal_records._reserve_and_publish_step()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__resolve_steps()`
def dfh_reserved_step_ids(directory: Path, *, exclude_turn: str | None=None) -> set[int]:
	r: set[int] = set()
	for key, entry in dfh_read_turn_reservations(directory).items():
		if None is exclude_turn or key != exclude_turn:
			r.update((st for st in (entry.get('steps') or ()) if int is type(st) and 1 <= st))
	return r
# @used-by :func:`_persist_reservation_update()`
# @used-by :func:`dfh_release_turn_steps()`
# @used-by :meth:`Df.Harness.Completion.NarrowReconciler.NarrowReconciler.__trim_narrowed_reservation()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__prune_reservations()`
def dfh_write_turn_reservations(directory: Path, reservations: dict[str, dict]) -> None:
	eff = Path(directory).resolve()
	res_file = dfh_state_dir(eff) / TURN_RESERVATIONS_FILE
	if not reservations:
		res_file.unlink(missing_ok=True)
	else:
		payload = (json.dumps({'journal': str(eff), 'reservations': reservations, 'version': 1}, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
		same = False
		if res_file.is_file():
			try:
				same = res_file.read_bytes() == payload
			except OSError:
				same = False
		if not same:
			res_file.parent.mkdir(parents=True, exist_ok=True)
			dfh_replace_bytes(res_file, payload)
