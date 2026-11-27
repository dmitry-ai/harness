# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Experiment.CallChainParser import CallChainParser
from Df.Harness.Experiment.ConditionAuditor import ConditionAuditor
from Df.Qa.lib.validation.check_strict import df_is_sne
import json
_ACTIONS = ('click', 'select', 'fill', 'press', 'navigate')
_STATE_ACTIONS = {'read', 'inspect', 'navigate', 'click', 'select', 'press', 'fill'}
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class BrowserStepAuditor:
	# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.__check_method()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def __init__(self, run: dict, artifacts: dict, events: dict, native_texts_fn) -> None:
		self.__run = run
		self.__artifacts = artifacts
		self.__events = events
		self.__native_texts = native_texts_fn
	# @used-by :meth:`BrowserStepAuditor.__check_step()`
	def __check_phase(self, phase: str, state, event: dict, issues: list[str]) -> None:
		if not isinstance(state, dict):
			issues.append('Browser action needs before/after states')
		else:
			if not df_is_sne(state.get('url')) or any((key not in state for key in ('currency', 'language', 'selected_country'))):
				issues.append('Before/after states must record URL, currency, language and selected country (unknown may be null)')
			issues += ConditionAuditor.evidence_issues(state.get('evidence'), self.__artifacts, 'Browser ' + phase)
			state_events = self.__native_texts(state.get('evidence', []))
			if not state_events:
				issues.append('Browser state must bind to actual native browser output, not an authored summary')
			elif not any((CallChainParser.event_actions(ev) & _STATE_ACTIONS for ev in state_events)):
				issues.append('Browser state evidence is not a native UI measurement')
			self.__check_phase_order_and_values(phase, state, event, state_events, issues)
	# @used-by :meth:`BrowserStepAuditor.__check_phase()`
	@staticmethod
	def __check_phase_order_and_values(phase: str, state: dict, event: dict, state_events: list, issues: list[str]) -> None:
		if event:
			positions = [ev.get('output_step', -1) for ev in state_events]
			if 'before' == phase and (not positions or max(positions) >= event.get('step', -1)):
				issues.append('Before state must be captured before the actual native action')
			if 'after' == phase and (not positions or min(positions) < event.get('output_step', -1)):
				issues.append('After state must follow actual native action completion')
		values = [str(state[key]) for key in ('url', 'currency', 'language', 'selected_country') if None is not state.get(key)]
		raw_text = '\n'.join((json.dumps(ev.get('result'), ensure_ascii=False) for ev in state_events))
		if any((value not in raw_text for value in values)):
			issues.append('Declared browser state contains values absent from its raw native output')
	# @used-by :meth:`BrowserStepAuditor.issues()`
	def __check_step(self, step, issues: list[str]) -> None:
		if not isinstance(step, dict):
			issues.append('Actual step object required')
		else:
			action = step.get('action')
			event = self.__events.get(step.get('native_event_id'), {})
			if action not in _ACTIONS or action not in CallChainParser.event_actions(event):
				issues.append('Actual UI action must match a successful native browser tool event')
			for phase in ('before', 'after'):
				self.__check_phase(phase, step.get(phase), event, issues)
			issues += ConditionAuditor.evidence_issues(step.get('evidence'), self.__artifacts, 'Browser action')
	# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.__check_method()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def issues(self) -> list[str]:
		r: list[str] = []
		if not self.__run['actual_steps']:
			r.append('Browser interaction needs actual action steps, not only snapshots')
		for step in self.__run['actual_steps']:
			self.__check_step(step, r)
		return r
