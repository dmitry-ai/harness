# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from Df.Harness.Project.RegistrationConflict import RegistrationConflict
from Df.Harness.Project.RegistrationExpectation import RegistrationExpectation
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RegistrationValidator:
	# @used-by :func:`agent_tools.registration.validate_registration()`
	# @used-by :meth:`Df.Harness.Project.Registry.Registry.__attempt()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_registration_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def __init__(self, project, label, day, platform: str, result) -> None:
		self.__project = project
		self.__label = label
		self.__day = day
		self.__platform = platform
		self.__result = result
	# @used-by :meth:`RegistrationValidator.validate()`
	def __check_antigravity(self, value: dict, issues: list[str]) -> object:
		roots = value.get('root_paths')
		if 'antigravity' == self.__platform and value.get('project_file'):
			native = json.loads(Path(value['project_file']).read_text(encoding='utf-8-sig'))
			from agent_tools.platforms.antigravity import folder_path, resource_uri
			roots = [str(folder_path(resource_uri(item))) for item in native.get('projectResources', {}).get('resources', []) if resource_uri(item)]
			if native.get('name') != value.get('project_name'):
				issues.append('Native project name differs from the registration receipt')
			if native.get('id') and native['id'] != value.get('project_id'):
				issues.append('Native project ID differs from the registration receipt')
		return roots
	# @used-by :meth:`RegistrationValidator.__check_fields()`
	def __check_codex(self, value: dict, issues: list[str]) -> dict | None:
		binding = None
		if 'codex' == self.__platform:
			profiles = value.get('profiles')
			binding = profiles.get(value.get('profile')) if isinstance(profiles, dict) else None
			if not isinstance(binding, dict) or not binding.get('project_id'):
				issues.append('Shared-Projects did not confirm the selected profile native identity')
		return binding
	# @used-by :meth:`RegistrationValidator.validate()`
	def __check_fields(self, value: dict, expected: dict, normalized_roots, issues: list[str]) -> dict | None:
		if normalized_roots != expected['root_paths']:
			issues.append('Native project roots differ from the requested workspace')
		if value.get('project_name') != expected['project_name']:
			issues.append('Native project name differs from the requested name; manual name preserved')
		if value.get('folder_path') != expected['folder_path'] or not value.get('folder_id'):
			issues.append('Native folder assignment differs from the requested branch')
		identity = 'shared_id' if 'codex' == self.__platform else 'project_id'
		if not value.get(identity):
			issues.append('Native registration did not confirm its project identity')
		return self.__check_codex(value, issues)
	# @used-by :meth:`RegistrationValidator.validate()`
	def __complete(self, value: dict) -> bool:
		if False is value.get('complete'):
			r = False
		elif not isinstance(value.get('profiles'), dict):
			r = bool(value.get('complete', value.get('project_id') and value.get('folder_id')))
		else:
			profile = value.get('profile')
			r = bool(profile and value['profiles'].get(profile, {}).get('ready'))
		return r
	# @used-by :meth:`RegistrationValidator.validate()`
	def __normalize_roots(self, roots) -> list[str] | None:
		try:
			r = [str(Path(path).resolve()) for path in roots] if isinstance(roots, list) else None
		except (TypeError, ValueError):
			r = None
		return r
	# @used-by :func:`agent_tools.registration.validate_registration()`
	# @used-by :meth:`Df.Harness.Project.Registry.Registry.__attempt()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_registration_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def validate(self) -> dict:
		_, _, _, expected = RegistrationExpectation(self.__project, self.__label, self.__day).build()
		if not isinstance(self.__result, dict):
			raise ValueError('Native registration receipt must be a JSON object')
		value, issues = (deepcopy(self.__result), [])
		roots = self.__check_antigravity(value, issues)
		value['root_paths'] = roots
		normalized_roots = self.__normalize_roots(roots)
		binding = self.__check_fields(value, expected, normalized_roots, issues)
		if issues:
			raise RegistrationConflict('; '.join(issues), expected=expected, actual=value, issues=issues)
		value['root_paths'] = normalized_roots
		value['complete'] = self.__complete(value)
		block = binding.get('registration_block') or {} if 'codex' == self.__platform and isinstance(binding, dict) else {}
		value['status'] = 'registered' if value['complete'] else block['status'] if block.get('status') in ('untrusted', 'blocked') else 'pending'
		return value