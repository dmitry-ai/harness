# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from Df.Harness.Project.RegistrationAttemptStarter import RegistrationAttemptStarter
from Df.Harness.Project.RegistrationConflict import RegistrationConflict
from Df.Harness.Project.RegistrationExpectation import RegistrationExpectation
from Df.Harness.Project.RegistrationStore import RegistrationStore
from Df.Harness.Project.RegistrationValidator import RegistrationValidator
from agent_tools.runtime import platform_active, platform_name, settings
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class Registry:
	# @used-by :func:`agent_tools.registration.register_project()`
	# @used-by :func:`agent_tools.registration.register_projects()`
	# @used-by :func:`agent_tools.upwork_project.register_project()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_register()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__maybe_register()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.complete()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_registration_classes()`
	def __init__(self, project, label=None, day=None, *, settings_fn=None) -> None:
		self.__project = project
		self.__label = label
		self.__day = day
		self.__settings_fn = settings if None is settings_fn else settings_fn
	# @used-by :meth:`Registry.register()`
	def __attempt(self, root, label: str, day: str, target: str, expected: dict, registrar) -> tuple[dict, Exception | None]:
		started = RegistrationAttemptStarter(root, target, deepcopy(expected)).begin()
		error: Exception | None = None
		try:
			if None is registrar:
				from agent_tools.platforms import adapter
				registrar = adapter(target).register
			result = RegistrationValidator(root, label, day, target, registrar(root, label, day)).validate()
		except Exception as exc:
			error = exc
			result = {'status': 'conflict' if isinstance(exc, RegistrationConflict) else 'error', 'complete': False, 'error': {'type': type(exc).__name__, 'message': str(exc)}}
			if isinstance(exc, RegistrationConflict):
				result.update(expected=exc.expected, actual=exc.actual, issues=exc.issues)
		result.update(intent=started['intent'], attempt=started['attempt'])
		return (RegistrationStore(root, target, result).save(), error)
	# @used-by :meth:`Registry.register()`
	def __resolve_targets(self, active: str, targets) -> list[str]:
		config = self.__settings_fn()
		if None is not targets:
			chosen = list(dict.fromkeys(targets))
		else:
			configured = (config.get('registration') or {}).get('targets') or [active]
			chosen = list(dict.fromkeys([t for t in configured if platform_active(t, config=config) or t == active]))
		if active not in chosen:
			raise ValueError('Registration targets must include the active application')
		if any((t not in config['platforms'] for t in chosen)):
			raise ValueError('Unknown registration target')
		return chosen
	# @used-by :func:`agent_tools.registration.register_project()`
	# @used-by :func:`agent_tools.registration.register_projects()`
	# @used-by :func:`agent_tools.upwork_project.register_project()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_register()`
	# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__maybe_register()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.complete()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_registration_classes()`
	def register(self, *, platform=None, targets=None, registrars=None, single: bool=False) -> dict:
		active = platform_name(platform)
		if single:
			root, label, day, expected = RegistrationExpectation(self.__project, self.__label, self.__day).build()
			result, error = self.__attempt(root, label, day, active, expected, None)
			if error:
				raise error
			r = result
		else:
			chosen = self.__resolve_targets(active, targets)
			root, label, day, expected = RegistrationExpectation(self.__project, self.__label, self.__day).build()
			results = {}
			for target in [active, *(name for name in chosen if name != active)]:
				results[target], _ = self.__attempt(root, label, day, target, expected, (registrars or {}).get(target))
			r = {**results[active], 'platform': active, 'targets': chosen, 'registrations': results, 'complete': results[active]['complete'], 'all_registered': all((res['complete'] for res in results.values()))}
		return r