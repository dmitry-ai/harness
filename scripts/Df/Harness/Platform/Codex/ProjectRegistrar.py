# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.codex_control import dfh_shared_control
from Df.Harness.lib.runtime_context import dfh_registration_profile_name, dfh_request_day
from agent_tools.registration import validate_registration
import time
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ProjectRegistrar:
	# @used-by :func:`agent_tools.platforms.codex.register()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_ag_and_codex_registrars_verifiers_and_title_sync()`
	def __init__(self, project_dir, domain_or_topic: str, date_str=None, *, _ops: dict[str, Any] | None=None) -> None:
		self.__project_dir = project_dir
		self.__domain_or_topic = domain_or_topic
		self.__date_str = date_str
		self.__ops = _ops or {}
	# @used-by :meth:`ProjectRegistrar.run()`
	def __poll_pending_receipt(self, receipt: dict, profile: str, control_fn) -> dict:
		has_connecting = lambda rec: any((isinstance(info, dict) and info.get('state') in ('connected', 'initializing') for info in (rec.get('accounts') or {}).values()))
		if not receipt.get('complete') and receipt.get('shared_id') and has_connecting(receipt):
			for _ in range(8):
				time.sleep(0.4)
				receipt = control_fn({'command': 'shared-registration', 'sharedId': receipt['shared_id'], 'profile': profile})
				if receipt.get('complete') or (not has_connecting(receipt)):
					break
		return receipt
	# @used-by :func:`agent_tools.platforms.codex.register()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_ag_and_codex_registrars_verifiers_and_title_sync()`
	def run(self) -> dict[str, Any]:
		control_fn = self.__ops.get('shared_control') or (lambda req: dfh_shared_control(req, platform_settings_fn=self.__ops.get('platform_settings'), run_fn=self.__ops.get('subprocess_run')))
		profile_fn = self.__ops.get('registration_profile_name') or (lambda: dfh_registration_profile_name(settings_fn=self.__ops.get('settings')))
		day_fn = self.__ops.get('request_day') or (lambda d: dfh_request_day(d, settings_fn=self.__ops.get('settings')))
		profile, day = (profile_fn(), day_fn(self.__date_str))
		receipt = control_fn({'command': 'shared-ensure-project', 'profile': profile, 'project': {'name': f'{self.__domain_or_topic} - U.P.{day:%Y.%m.%d}', 'trustPolicy': 'upwork-daily', 'rootPaths': [str(Path(self.__project_dir).resolve())], 'folderPath': ['Upwork', 'Proposals', f'{day.year:04d}', f'{day.month:02d}', f'{day.day:02d}']}})
		receipt = self.__poll_pending_receipt(receipt, profile, control_fn)
		return validate_registration(self.__project_dir, self.__domain_or_topic, day.isoformat(), 'codex', {**receipt, 'surface': 'codex-ui', 'profile': profile})
