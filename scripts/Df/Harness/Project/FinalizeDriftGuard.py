# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.json_io import df_json_dict_load
from Df.Harness.Project.DriftAuditor import DriftAuditor
from agent_tools.path_registry import project_paths
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class FinalizeDriftGuard:
	# @used-by :func:`agent_tools.project_drift.require_no_domain_drift_for_finalize()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def __init__(self, root: Path | str, *, drift_fn=None) -> None:
		self.__root = root
		self.__drift_fn = drift_fn
	# @used-by :func:`agent_tools.project_drift.require_no_domain_drift_for_finalize()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def require(self) -> None:
		drift_fn = (lambda r, v: DriftAuditor(r, v).audit()) if None is self.__drift_fn else self.__drift_fn
		pp = project_paths(self.__root, exact_root=True)
		value = df_json_dict_load(pp.kb_dir / 'Analysis.json')
		if None is not value:
			issues = drift_fn(pp.root, value)
			if issues:
				raise ValueError(issues[0]['message'])
		scratch_dir = pp.scratch_dir
		if scratch_dir.is_dir() and any((p.is_file() for p in scratch_dir.rglob('*'))):
			raise ValueError('Clean or consume all temporary files in \ua616/data/scratch before finalizing')