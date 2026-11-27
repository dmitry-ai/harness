# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from Df.Harness.lib.cleanup_lifecycle_ops import dfh_best_activity, dfh_collect_handoff_activity, dfh_collect_rename_activity, dfh_collect_workflow_finalize, dfh_journal_pair_activity
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class LifecycleEvaluator:
	# @used-by :func:`Df.Harness.lib.cleanup_store_ops.dfh_age()`
	# @used-by :func:`agent_tools.cleanup_lifecycle.effective_project_activity()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_cleanup_subsystem_classes()`
	def __init__(self, root, state: dict, config: dict, base_dt: datetime, base_basis: str, path_key_fn) -> None:
		self.__root = root
		self.__state = state
		self.__config = config
		self.__base_dt = base_dt
		self.__base_basis = base_basis
		self.__path_key_fn = path_key_fn
	# @used-by :func:`Df.Harness.lib.cleanup_store_ops.dfh_age()`
	# @used-by :func:`agent_tools.cleanup_lifecycle.effective_project_activity()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_cleanup_subsystem_classes()`
	def run(self) -> tuple[datetime, str]:
		if not isinstance(self.__root, Path) or (not self.__root.exists()):
			r = (self.__base_dt, self.__base_basis)
		else:
			jrn_dt, _ = dfh_journal_pair_activity(self.__root)
			cands = [
				(dfh_collect_workflow_finalize(self.__root), 'workflow.finalize'),
				(dfh_collect_rename_activity(self.__state), 'project.renamed_from'),
				(dfh_collect_handoff_activity(self.__root, self.__state, self.__config, self.__path_key_fn), 'handed_off_conversation'),
				(jrn_dt, 'journal.latest_pair'),
			]
			r = dfh_best_activity(cands, self.__base_dt, self.__base_basis)
		return r
