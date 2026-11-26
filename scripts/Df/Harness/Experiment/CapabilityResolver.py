# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class CapabilityResolver:
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.load_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__audit_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunValidator.RunValidator.capabilities()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def __init__(self, run: dict) -> None:
		self.__run = run
	# @used-by :meth:`CapabilityResolver.capabilities()`
	def __add_method_caps(self, found: set[str]) -> None:
		method = self.__run['requirement']['method']
		if 'browser_scenario' == method:
			found.update(('content', 'dom', 'interaction'))
			if 'currency_transition' == self.__run['requirement']['property'] and all((isinstance(step.get(phase, {}).get('currency'), str) for step in self.__run['actual_steps'] for phase in ('before', 'after'))):
				found.add('currency_transition')
		if 'admin' == method:
			found.update(('content', 'admin_configuration'))
		if 'serp' == method:
			found.update(('content', 'serp'))
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.load_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__audit_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunValidator.RunValidator.capabilities()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def capabilities(self) -> list[str]:
		if self.__run.get('status') not in ('verified', 'refuted'):
			r: list[str] = []
		else:
			found: set[str] = set()
			for artifact in self.__run['artifacts']:
				found.update(artifact.get('observation_capabilities', []))
			self.__add_method_caps(found)
			if 'verified' == self.__run.get('conditions', {}).get('egress', {}).get('verification'):
				found.add('ip_country')
			r = sorted(found)
		return r
