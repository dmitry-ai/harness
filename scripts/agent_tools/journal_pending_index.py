# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Journal.PendingIndex import PendingIndex
from Df.Harness.lib.journal_sync_ops import PENDING_INDEX_FILE, _entry_from_state, _parse_iso_epoch, dfh_candidate_recency as candidate_recency, dfh_is_pending_prepared as is_pending_prepared, dfh_order_candidates_by_recency as order_candidates_by_recency, dfh_persist_turn_state as persist_turn_state, dfh_prune_resolved_from_index as prune_resolved_from_index, dfh_read_index_doc as _read_index_doc, dfh_rebuild_pending_index as rebuild_pending_index, dfh_scan_prepared_dir as _scan_prepared_dir, dfh_update_index_for_turn as update_index_for_turn, dfh_write_index_doc as _write_index_doc
# @used-by :mod:`agent_tools.journal_pending_index`
def collect_pending_prepared(root: Path, *, folder_fn, read_fn) -> tuple[dict[str, dict[str, Any]], bool]:
	return PendingIndex(folder_fn(root), read_fn=read_fn).run()
__all__ = ['PENDING_INDEX_FILE', 'candidate_recency', 'collect_pending_prepared', 'is_pending_prepared', 'order_candidates_by_recency', 'persist_turn_state', 'prune_resolved_from_index', 'rebuild_pending_index', 'update_index_for_turn']
