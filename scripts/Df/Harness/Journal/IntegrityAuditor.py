# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Journal.LivenessProbe import LivenessProbe
from Df.Harness.lib.journal_integrity_ops import dfh_turn_index_for_project, dfh_turn_state_orphan_reason
from Df.Harness.lib.journal_records import dfh_completed_request_group_index, dfh_get_existing_step_ids
from Df.Harness.lib.journal_reservations import dfh_iter_turn_reservations
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class IntegrityAuditor:
	# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_orphaned_reservation_issues()`
	# @used-by :func:`agent_tools.journal_integrity.classify_reservations()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_journal_subsystem_classes()`
	def __init__(self, jdir: Path, *, project_root: Path | None=None, conversation_ids: set[str] | None=None, require_empty_for_cids: bool=False) -> None:
		self.__jdir = Path(jdir).resolve()
		self.__project_root = project_root
		self.__cids = conversation_ids
		self.__require_empty = require_empty_for_cids
	# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_orphaned_reservation_issues()`
	# @used-by :func:`agent_tools.journal_integrity.classify_reservations()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_journal_subsystem_classes()`
	def run(self) -> dict[str, list]:
		reservations = dfh_iter_turn_reservations(self.__jdir)
		orphaned, active_parallel = ([], [])
		if reservations:
			max_existing = max(dfh_get_existing_step_ids(self.__jdir), default=0)
			committed_rids = set(dfh_completed_request_group_index(self.__jdir))
			by_key, max_start_by_cid = dfh_turn_index_for_project(self.__project_root)
			for r_key, entry in sorted(reservations.items()):
				cid = str(entry.get('conversation_id') or '').strip().lower()
				if None is not self.__cids and cid not in self.__cids:
					continue
				err, live = LivenessProbe(r_key, entry, max_existing, committed_rids, by_key, max_start_by_cid, require_empty=self.__require_empty, turn_reason_fn=dfh_turn_state_orphan_reason).run()
				if None is not err:
					orphaned.append(err)
				elif None is not live:
					active_parallel.append(live)
		return {'active_parallel': active_parallel, 'orphaned': orphaned}
