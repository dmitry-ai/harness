# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class LabelStateUpdater:
	# @used-by :func:`agent_tools.project_labels.update_state_label()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def __init__(self, state: dict, root: Path, snapshot: Path, day, label_kind: str) -> None:
		self.__state = state
		self.__root = Path(root)
		self.__snapshot = Path(snapshot)
		self.__day = day
		self.__label_kind = label_kind
	# @used-by :func:`agent_tools.project_labels.update_state_label()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def update(self) -> None:
		day_val = self.__day.isoformat() if hasattr(self.__day, 'isoformat') else str(self.__day)
		self.__state.update(initialized=True, snapshot=str(self.__snapshot.relative_to(self.__root)))
		self.__state.setdefault('label', self.__root.name.split(' - ', 1)[-1])
		self.__state.setdefault('label_kind', self.__label_kind)
		self.__state.setdefault('request_date', day_val)