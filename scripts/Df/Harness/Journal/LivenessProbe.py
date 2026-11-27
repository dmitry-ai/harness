# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.lib.journal_integrity_ops import dfh_is_conversation_running_live
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class LivenessProbe:
	# @used-by :func:`agent_tools.journal_integrity._reservation_orphan_reason()`
	# @used-by :func:`agent_tools.journal_liveness.classify_reservation_entry()`
	# @used-by :meth:`Df.Harness.Journal.IntegrityAuditor.IntegrityAuditor.run()`
	def __init__(self, r_key: str, entry: dict[str, Any], max_existing: int, committed_rids: set[str], by_key: dict[str, dict[str, Any]], max_start_by_cid: dict[str, int], *, require_empty: bool, turn_reason_fn: Any) -> None:
		self.__r_key = r_key
		self.__entry = entry
		self.__max_existing = max_existing
		self.__committed_rids = committed_rids
		self.__by_key = by_key
		self.__max_start_by_cid = max_start_by_cid
		self.__require_empty = require_empty
		self.__turn_reason_fn = turn_reason_fn
	# @used-by :func:`agent_tools.journal_integrity._reservation_orphan_reason()`
	# @used-by :func:`agent_tools.journal_liveness.classify_reservation_entry()`
	# @used-by :meth:`Df.Harness.Journal.IntegrityAuditor.IntegrityAuditor.run()`
	def run(self) -> tuple[str | None, dict[str, Any] | None]:
		cid = str(self.__entry.get('conversation_id') or '').strip().lower()
		e_steps = [s for s in (self.__entry.get('steps') or ()) if int is type(s) and 1 <= s]
		e_reqs = [rid for rid in (self.__entry.get('request_ids') or ()) if isinstance(rid, str) and rid]
		st = self.__by_key.get(self.__r_key)
		err, live = (None, None)
		if self.__require_empty:
			err = f'dangling reservation {self.__r_key} (steps={e_steps}) remains for finalized conversation'
		elif any((rid in self.__committed_rids for rid in e_reqs)):
			err = f'orphaned reservation {self.__r_key} references already-committed request_ids'
		elif isinstance(st, dict) and None is not self.__turn_reason_fn(self.__r_key, st, cid, self.__max_start_by_cid):
			err = self.__turn_reason_fn(self.__r_key, st, cid, self.__max_start_by_cid)
		elif any((s <= self.__max_existing for s in e_steps)):
			if dfh_is_conversation_running_live(self.__r_key, self.__entry, self.__by_key):
				live = {'classification': 'active_parallel_reservation', 'conversation_id': cid, 'steps': e_steps, 'turn_key': self.__r_key}
			else:
				err = f'orphaned reservation {self.__r_key} holds steps {e_steps} <= committed max step {self.__max_existing}'
		return (err, live)
