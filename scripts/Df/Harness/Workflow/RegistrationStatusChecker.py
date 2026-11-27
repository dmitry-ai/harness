# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import os
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RegistrationStatusChecker:
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__check_prereqs()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.complete()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.registration_status()`
	# @used-by :meth:`Df.Harness.Workflow.StageStatusEvaluator.StageStatusEvaluator.__stage_current()`
	# @used-by :meth:`Df.Harness.Workflow.StatusSnapshotBuilder.StatusSnapshotBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def __init__(self, root) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__root = self.__pp.root
	# @used-by :meth:`RegistrationStatusChecker.target_complete()`
	@staticmethod
	def __resolve_profile(target: str, item: dict) -> str | None:
		from agent_tools.runtime import profile_name, registration_profile_name
		if 'codex' == target and 'CODEX_HOME' in os.environ:
			r: str | None = profile_name()
		else:
			r = item.get('profile')
			if not r and 'codex' == target:
				try:
					r = registration_profile_name()
				except ValueError:
					r = None
		return r
	# @used-by :meth:`RegistrationStatusChecker.status()`
	@staticmethod
	def __resolve_targets(config: dict, platform: str, platform_active) -> list[str]:
		raw = list(dict.fromkeys((config.get('registration') or {}).get('targets') or [platform]))
		r = [target for target in raw if platform_active(target, config=config) or target == platform]
		if platform not in r:
			r.insert(0, platform)
		return r
	# @used-by :meth:`RegistrationStatusChecker.status()`
	@classmethod
	def __target_entry(cls, target: str, data: dict, required: bool) -> dict:
		item = data.get(target) if isinstance(data, dict) else None
		done = not required or cls.target_complete(target, item)
		status = (item.get('status') if isinstance(item, dict) else None) or ('registered' if done else 'pending')
		attempts = item.get('attempts', 0) if isinstance(item, dict) else 0
		return {'complete': done, 'status': status, 'attempts': attempts}
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__check_prereqs()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.complete()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.registration_status()`
	# @used-by :meth:`Df.Harness.Workflow.StageStatusEvaluator.StageStatusEvaluator.__stage_current()`
	# @used-by :meth:`Df.Harness.Workflow.StatusSnapshotBuilder.StatusSnapshotBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def status(self) -> dict:
		from agent_tools.runtime import platform_active, platform_name, settings
		config, platform = (settings(), platform_name())
		path = self.__pp.registrations_json
		required = path.exists() or self.__root.is_relative_to(Path(config['workspace_root']) / config['daily_root'])
		data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
		receipt = data.get(platform) if isinstance(data, dict) else None
		targets = self.__resolve_targets(config, platform, platform_active)
		targets_status = {t: self.__target_entry(t, data, required) for t in targets}
		pending = [t for t, info in targets_status.items() if not info['complete']]
		return {'platform': platform, 'required': required, 'complete': targets_status[platform]['complete'], 'all_registered': not pending, 'targets': targets_status, 'pending_targets': pending, 'receipt': receipt}
	# @used-by :func:`agent_tools.workflow._target_complete()`
	# @used-by :meth:`RegistrationStatusChecker.__target_entry()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_remaining_branches()`
	@classmethod
	def target_complete(cls, target: str, item) -> bool:
		if not isinstance(item, dict):
			r = False
		elif not isinstance(item.get('profiles'), dict):
			r = bool(item.get('complete', item.get('project_id') and item.get('folder_id')))
		else:
			prof = cls.__resolve_profile(target, item)
			r = bool(prof and item['profiles'].get(prof, {}).get('ready'))
		return r
