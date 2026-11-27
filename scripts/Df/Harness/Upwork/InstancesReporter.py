# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.runtime import all_instances, find_conversation_instance, instance_entry, settings
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class InstancesReporter:
	# @used-by :func:`agent_tools.upwork_project.instances_report()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__run_instances()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_project_management_classes()`
	def __init__(self, *, platform=None, instance=None, conversation=None, include_disabled: bool=True, check_exists: bool=True, settings_fn=None) -> None:
		self.__platform, self.__instance, self.__conversation = (platform, instance, conversation)
		self.__include_disabled, self.__check_exists = (include_disabled, check_exists)
		self.__settings_fn = settings if None is settings_fn else settings_fn
	# @used-by :func:`agent_tools.upwork_project.instances_report()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__run_instances()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_project_management_classes()`
	def report(self) -> dict:
		config = self.__settings_fn()
		if self.__conversation:
			matches = find_conversation_instance(self.__conversation, platform=self.__platform, config=config, include_disabled=self.__include_disabled)
			if self.__instance:
				matches = [m for m in matches if m['id'] == self.__instance]
			r = {'conversation_id': self.__conversation, 'matches': matches, 'found': bool(matches), 'available_handoff_targets': all_instances(config=config, include_disabled=False)['available_handoff_targets']}
		elif self.__instance:
			entry = instance_entry(self.__instance, platform=self.__platform, config=config, include_disabled=self.__include_disabled)
			inv = all_instances(config=config, platform=entry['platform'], include_disabled=self.__include_disabled, check_exists=self.__check_exists)
			r = {'instance': inv['environments'][entry['platform']]['instances'][entry['id']], 'available_handoff_targets': all_instances(config=config, include_disabled=False)['available_handoff_targets']}
		else:
			r = all_instances(config=config, platform=self.__platform, include_disabled=self.__include_disabled, check_exists=self.__check_exists)
		return r
