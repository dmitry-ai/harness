# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from agent_tools.storage import locked, replace_bytes
import json
import uuid
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RegistrationAttemptStarter:
	# @used-by :func:`agent_tools.registration._begin()`
	# @used-by :meth:`Df.Harness.Project.Registry.Registry.__attempt()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_registration_classes()`
	def __init__(self, root: Path, platform: str, intent: dict) -> None:
		self.__root = Path(root)
		self.__platform = platform
		self.__intent = intent
	# @used-by :meth:`RegistrationAttemptStarter.begin()`
	def __build_entry(self, previous: dict) -> dict:
		history = deepcopy(previous.get('attempt_history', []))
		prior = previous.get('attempt')
		if prior and (not any((part.get('id') == prior['id'] for part in history))):
			history.append(deepcopy(prior))
		attempt = {'id': str(uuid.uuid4()), 'started_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'status': 'attempting', 'intent': deepcopy(self.__intent)}
		entry = {'platform': self.__platform, 'intent': self.__intent, 'attempt': attempt, 'attempts': previous.get('attempts', 0) + 1, 'attempt_history': history, 'status': 'attempting', 'complete': False}
		success = self.__success(previous)
		if success:
			entry['last_success'] = success
		return entry
	# @used-by :meth:`RegistrationAttemptStarter.__success()`
	def __complete(self, result: dict) -> bool:
		if False is result.get('complete'):
			r = False
		elif not isinstance(result.get('profiles'), dict):
			r = bool(result.get('complete', result.get('project_id') and result.get('folder_id')))
		else:
			profile = result.get('profile')
			r = bool(profile and result['profiles'].get(profile, {}).get('ready'))
		return r
	# @used-by :meth:`RegistrationAttemptStarter.__build_entry()`
	def __success(self, previous: dict) -> dict | None:
		if previous.get('last_success'):
			r: dict | None = deepcopy(previous['last_success'])
		elif not self.__complete(previous):
			r = None
		else:
			r = {k: deepcopy(v) for k, v in previous.items() if k not in ('intent', 'attempt', 'attempts', 'attempt_history', 'last_success')}
		return r
	# @used-by :func:`agent_tools.registration._begin()`
	# @used-by :meth:`Df.Harness.Project.Registry.Registry.__attempt()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_registration_classes()`
	def begin(self) -> dict:
		from agent_tools.path_registry import project_paths
		pp = project_paths(self.__root, exact_root=True)
		with locked(pp.data_dir / 'registration.lock'):
			path = pp.registrations_json
			data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
			if not isinstance(data, dict):
				raise ValueError('Registrations must be a map of platform receipts')
			entry = self.__build_entry(data.get(self.__platform, {}))
			data[self.__platform] = entry
			replace_bytes(path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
			r = deepcopy(entry)
		return r