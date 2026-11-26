# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Experiment.BrowserIdentityExtractor import BrowserIdentityExtractor
from Df.Harness.Experiment.CallChainParser import CallChainParser
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class TraceContextAuditor:
	# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.issues()`
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.context_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	def __init__(self, run: dict, events: dict, native_texts_fn) -> None:
		self.__run = run
		self.__events = events
		self.__native_texts = native_texts_fn
	# @used-by :meth:`TraceContextAuditor.__collect_relevant()`
	def __add_step_events(self, relevant: list) -> None:
		for step in self.__run.get('actual_steps', []):
			if isinstance(step, dict):
				event = self.__events.get(step.get('native_event_id'))
				if event and event not in relevant:
					relevant.append(event)
				for phase in ('before', 'after'):
					state = step.get(phase, {})
					if isinstance(state, dict):
						for ev in self.__native_texts(state.get('evidence', [])):
							if ev not in relevant:
								relevant.append(ev)
	# @used-by :meth:`TraceContextAuditor.issues()`
	def __collect_relevant(self, method: str) -> list:
		relevant = [event for event in self.__events.values() if CallChainParser.event_actions(event)]
		if 'browser_scenario' == method:
			self.__add_step_events(relevant)
		conditions = self.__run.get('conditions', {})
		for key in ('session', 'egress'):
			condition = conditions.get(key, {})
			if isinstance(condition, dict) and 'verified' == condition.get('verification'):
				for ev in self.__native_texts(condition.get('evidence', [])):
					if ev not in relevant:
						relevant.append(ev)
		return relevant
	# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.issues()`
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.context_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	def issues(self) -> list[str]:
		method = self.__run['requirement']['method']
		if method not in ('browser_scenario', 'admin', 'serp'):
			r: list[str] = []
		else:
			relevant = self.__collect_relevant(method)
			if not relevant:
				r = [] if 'serp' == method else ['Native browser context/tab identity is unknown']
			else:
				identities = [BrowserIdentityExtractor(event).extract_identity() for event in relevant]
				if any((None is ident for ident in identities)):
					r = ['Actual native browser/context/tab identity is unknown; record unverified, not an interaction proof']
				elif any((ident != identities[0] for ident in identities[1:])):
					r = ['Native before/action/after/egress browser, context, tab or session identities differ; record unverified']
				else:
					r = []
		return r
