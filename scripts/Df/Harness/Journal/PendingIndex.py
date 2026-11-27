# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.journal_sync_ops import dfh_read_index_doc, dfh_scan_prepared_dir
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class PendingIndex:
	# @used-by :func:`Df.Harness.lib.journal_sync_ops.dfh_reconcile_foreign_open_reservations()`
	# @used-by :func:`agent_tools.journal_pending_index.collect_pending_prepared()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_journal_subsystem_classes()`
	def __init__(self, turns_dir: Path, *, read_fn: Any) -> None:
		self.__turns_dir = Path(turns_dir)
		self.__read_fn = read_fn
	# @used-by :func:`Df.Harness.lib.journal_sync_ops.dfh_reconcile_foreign_open_reservations()`
	# @used-by :func:`agent_tools.journal_pending_index.collect_pending_prepared()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_journal_subsystem_classes()`
	def run(self) -> tuple[dict[str, dict[str, Any]], bool]:
		doc = dfh_read_index_doc(self.__turns_dir)
		if None is not doc and bool(doc.get('bootstrapped')):
			entries = {str(k): dict(v) for k, v in doc['entries'].items() if isinstance(v, dict) and v.get('conversation_id')}
			r = (entries, True)
		else:
			r = (dfh_scan_prepared_dir(self.__turns_dir, read_fn=self.__read_fn), None is not doc)
		return r
