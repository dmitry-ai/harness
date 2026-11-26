# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from agent_tools.runtime import request_day
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RegistrationExpectation:
	# @used-by :func:`agent_tools.registration._expected()`
	# @used-by :meth:`Df.Harness.Project.RegistrationValidator.RegistrationValidator.validate()`
	# @used-by :meth:`Df.Harness.Project.Registry.Registry.register()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_registration_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def __init__(self, project, label=None, day=None) -> None:
		self.__project = project
		self.__label = label
		self.__day = day
	# @used-by :func:`agent_tools.registration._expected()`
	# @used-by :meth:`Df.Harness.Project.RegistrationValidator.RegistrationValidator.validate()`
	# @used-by :meth:`Df.Harness.Project.Registry.Registry.register()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_registration_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def build(self) -> tuple[Path, str, str, dict]:
		from agent_tools.path_registry import project_paths
		root = Path(self.__project).resolve()
		if not root.is_dir():
			raise ValueError('Registration requires an existing project directory')
		day_val = self.__day
		if None is day_val:
			state = json.loads(project_paths(root, exact_root=True).project_json.read_text(encoding='utf-8'))
			day_val = state['request_date']
		day_obj = request_day(day_val)
		label = self.__label or root.name.split(' - ', 1)[-1]
		return (root, label, day_obj.isoformat(), {'project_name': f'{label} - U.P.{day_obj:%Y.%m.%d}', 'root_paths': [str(root)], 'folder_path': f'Upwork / Proposals / {day_obj:%Y / %m / %d}'})