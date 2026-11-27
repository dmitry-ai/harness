# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Core.lib.json_io import df_json_dict_load as _load_json_dict
from Df.Harness.Journal.IntegrityAuditor import IntegrityAuditor
from Df.Harness.Journal.LivenessProbe import LivenessProbe
from Df.Harness.lib.journal_integrity_ops import SEQUENCE_RECOVERY_FILE, _OTHER_JOB_RE, _TURN_AUX_SUFFIXES, _check_reconciliation_failures, _committed_turn_steps, _eligible_active_turn_keys, _group_steps_for_cid, _is_terminal_conflict, _iter_turn_states, _mentioned_other_job, _subtract_entry_overlap, dfh_acknowledged_sequence_gaps as acknowledged_sequence_gaps, dfh_check_project_journal_problems as check_project_journal_problems, dfh_collect_conversation_journal_steps as collect_conversation_journal_steps, dfh_collect_handed_off_conversations as collect_handed_off_conversations, dfh_finalize_conflict_turn as finalize_conflict_turn, dfh_finalize_project_check as finalize_project_check, dfh_journal_validation_errors as journal_validation_errors, dfh_missing_contiguous_steps as missing_contiguous_steps, dfh_orphaned_reservation_issues as orphaned_reservation_issues, dfh_prune_overlapping_reservations as prune_overlapping_reservations, dfh_prune_terminal_conflict_reservations as prune_terminal_conflict_reservations, dfh_sync_begin_turn_state as sync_begin_turn_state, dfh_turn_index_for_project as _turn_index_for_project, dfh_turn_matches_handoff as turn_matches_handoff, dfh_turn_state_orphan_reason as _turn_state_orphan_reason, dfh_validate_finalize_journal as validate_finalize_journal, dfh_validate_step_cli as validate_step_cli
# @used-by unused
def _reservation_orphan_reason(r_key: str, entry: dict, max_existing: int, committed_rids: set[str], by_key: dict[str, dict], max_start_by_cid: dict[str, int], *, require_empty: bool) -> str | None:
	return LivenessProbe(r_key, entry, max_existing, committed_rids, by_key, max_start_by_cid, require_empty=require_empty, turn_reason_fn=_turn_state_orphan_reason).run()[0]
# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_live_running_parallel_reservation_not_orphaned_while_idle_stuck_is_orphaned()`
def classify_reservations(jdir: Path, *, project_root: Path | None=None, conversation_ids: set[str] | None=None, require_empty_for_cids: bool=False) -> dict[str, list]:
	return IntegrityAuditor(jdir, project_root=project_root, conversation_ids=conversation_ids, require_empty_for_cids=require_empty_for_cids).run()
