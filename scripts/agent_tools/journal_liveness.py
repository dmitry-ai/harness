# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Journal.LivenessProbe import LivenessProbe
from Df.Harness.lib.journal_integrity_ops import dfh_is_conversation_running_live as is_conversation_running_live
# @used-by :mod:`agent_tools.journal_liveness`
def classify_reservation_entry(r_key: str, entry: dict[str, Any], max_existing: int, committed_rids: set[str], by_key: dict[str, dict[str, Any]], max_start_by_cid: dict[str, int], *, require_empty: bool, turn_reason_fn) -> tuple[str | None, dict[str, Any] | None]:
	return LivenessProbe(r_key, entry, max_existing, committed_rids, by_key, max_start_by_cid, require_empty=require_empty, turn_reason_fn=turn_reason_fn).run()
__all__ = ['classify_reservation_entry', 'is_conversation_running_live']
