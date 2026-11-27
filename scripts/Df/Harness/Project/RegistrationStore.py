# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from agent_tools.runtime import platform_name
from agent_tools.storage import locked, replace_bytes
import json
import uuid
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RegistrationStore:
	# @used-by :func:`agent_tools.registration.save_registration()`
	# @used-by :func:`agent_tools.upwork_project.save_registration()`
	# @used-by :meth:`Df.Harness.Project.Registry.Registry.__attempt()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_registration_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def __init__(self, root: Path, platform: str, result: dict) -> None:
		self.__root = root
		self.__platform = platform_name(platform)
		self.__result = result
	# @used-by :meth:`RegistrationStore.save()`
	def __build_entry(self, previous: dict) -> tuple[dict, dict, dict | None]:
		now = datetime.now(timezone.utc).isoformat(timespec='microseconds')
		value = deepcopy(self.__result)
		attempt = value.get('attempt') or {'id': str(uuid.uuid4()), 'started_at': now}
		value['complete'] = self.__complete(value)
		value.setdefault('status', 'registered' if value['complete'] else 'pending')
		attempt.update(finished_at=now, status=value['status'])
		if value.get('error'):
			attempt['error'] = value['error']
		value.update(platform=self.__platform, attempt=attempt, attempts=previous.get('attempts', 0) + (0 if self.__result.get('attempt') else 1))
		value.setdefault('intent', previous.get('intent', {}))
		history = [part for part in previous.get('attempt_history', []) if part.get('id') != attempt['id']]
		value['attempt_history'] = [*history, deepcopy(attempt)]
		success = {k: deepcopy(v) for k, v in value.items() if k not in ('intent', 'attempt', 'attempts', 'attempt_history', 'last_success')} if value['complete'] else self.__prior_success(previous)
		if success:
			value['last_success'] = success
		return (value, attempt, success)
	# @used-by :meth:`RegistrationStore.__build_entry()`
	# @used-by :meth:`RegistrationStore.__prior_success()`
	def __complete(self, result: dict) -> bool:
		if False is result.get('complete'):
			r = False
		elif not isinstance(result.get('profiles'), dict):
			r = bool(result.get('complete', result.get('project_id') and result.get('folder_id')))
		else:
			profile = result.get('profile')
			r = bool(profile and result['profiles'].get(profile, {}).get('ready'))
		return r
	# @used-by :meth:`RegistrationStore.save()`
	def __merge_entry(self, data: dict, previous: dict, value: dict, attempt: dict, success: dict | None) -> None:
		current_id = previous.get('attempt', {}).get('id')
		if not (self.__result.get('attempt') and current_id and (current_id != attempt['id'])):
			data[self.__platform] = value
		else:
			previous['attempt_history'] = value['attempt_history']
			if success:
				previous['last_success'] = success
			data[self.__platform] = previous
	# @used-by :meth:`RegistrationStore.__build_entry()`
	def __prior_success(self, previous: dict) -> dict | None:
		if previous.get('last_success'):
			r: dict | None = deepcopy(previous['last_success'])
		elif not self.__complete(previous):
			r = None
		else:
			r = {k: deepcopy(v) for k, v in previous.items() if k not in ('intent', 'attempt', 'attempts', 'attempt_history', 'last_success')}
		return r
	# @used-by :func:`agent_tools.registration.save_registration()`
	# @used-by :func:`agent_tools.upwork_project.save_registration()`
	# @used-by :meth:`Df.Harness.Project.Registry.Registry.__attempt()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_registration_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def save(self) -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__root, exact_root=True)
		with locked(pp.data_dir / 'registration.lock'):
			path = pp.registrations_json
			data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
			if not isinstance(data, dict):
				raise ValueError('Registrations must be a map of platform receipts')
			previous = data.get(self.__platform, {})
			value, attempt, success = self.__build_entry(previous)
			self.__merge_entry(data, previous, value, attempt, success)
			replace_bytes(path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
			r = deepcopy(value)
		return r