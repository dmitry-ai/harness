# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class StageValidityGuard:
	# @used-by :func:`agent_tools.project_drift.require_stage_project_valid()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def __init__(self, root: Path | str, check_fn, base_msg: str) -> None:
		self.__root = root
		self.__check_fn = check_fn
		self.__base_msg = base_msg
	# @used-by :func:`agent_tools.project_drift.require_stage_project_valid()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_drift_red_flags_and_card_sync_classes()`
	def require(self) -> None:
		chk = self.__check_fn(self.__root)
		if not chk['valid']:
			detail = '; '.join((i['message'] for i in chk['issues'][:3] if i.get('message')))
			raise ValueError(f'{self.__base_msg}: {detail}' if detail else self.__base_msg)