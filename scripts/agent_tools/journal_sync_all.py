# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Journal.OpenTurnSyncer import OpenTurnSyncer
from Df.Harness.lib.journal_integrity_ops import dfh_finalize_conflict_turn as finalize_conflict_turn, dfh_prune_terminal_conflict_reservations as prune_terminal_conflict_reservations, dfh_resolve_ag_summary_db as _resolve_ag_summary_db
from Df.Harness.lib.journal_sync_ops import DEFAULT_FOREIGN_MAX_ENTRIES, DEFAULT_FOREIGN_TIME_BUDGET_S, _antigravity_summary_is_idle, _collect_all_open_candidates, _is_foreign_open_eligible, _is_native_idle_for_sync, _iter_idle_prepared_candidates, _load_turn_state_safe, _reconcile_current_earlier, _resolve_current_sync_journal, _sync_foreign_batch, _try_sync_foreign_entry, dfh_persist_turn_state as persist_turn_state, dfh_reconcile_before_begin as reconcile_before_begin, dfh_reconcile_foreign_open_reservations as reconcile_foreign_open_reservations, dfh_resolve_sync_provenance as resolve_sync_provenance, dfh_run_all_open_sweep as _run_all_open_sweep
# @used-by :meth:`test_bounded_foreign_sync.BoundedForeignSyncTests.test_reconcile_foreign_stops_on_time_budget_while_all_open_sweeps_all()`
# @used-by :mod:`agent_tools.journal_sync_all`
def sync_all_open(root: Path, *, journal_directory: Any=None, adopt_conflict: bool=False, from_step: int=0, folder_fn, dir_fn, read_fn, sync_fn) -> dict[str, Any]:
	return OpenTurnSyncer(root, journal_directory=journal_directory, adopt_conflict=adopt_conflict, from_step=from_step, folder_fn=folder_fn, dir_fn=dir_fn, read_fn=read_fn, sync_fn=sync_fn).run()
__all__ = ['finalize_conflict_turn', 'persist_turn_state', 'reconcile_before_begin', 'reconcile_foreign_open_reservations', 'resolve_sync_provenance', 'sync_all_open']
