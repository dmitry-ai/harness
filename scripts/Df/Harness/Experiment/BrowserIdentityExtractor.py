# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Experiment.CallChainParser import CallChainParser
import json
IDENTITY_ALIASES = {'browser_id': ('browser_id', 'browserId'), 'tab_id': ('tab_id', 'tabId', 'providerTabId'), 'context_id': ('context_id', 'contextId', 'browser_context_id', 'browserContextId'), 'session_id': ('session_id', 'sessionId')}
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class BrowserIdentityExtractor:
	# @used-by :meth:`Df.Harness.Experiment.AssertionEvaluator.AssertionEvaluator.__is_primary()`
	# @used-by :meth:`Df.Harness.Experiment.TraceContextAuditor.TraceContextAuditor.issues()`
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.event_browser_identity()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	def __init__(self, event: dict) -> None:
		self.__event = event
	# @used-by :meth:`BrowserIdentityExtractor.extract_identity()`
	@staticmethod
	def __extract_dict(value) -> dict | None:
		result, conflict = ({}, False)
		if isinstance(value, dict):
			for key, fields in IDENTITY_ALIASES.items():
				values = {str(value[field]) for field in fields if isinstance(value.get(field), (str, int)) and str(value[field]).strip()}
				if 1 < len(values):
					conflict = True
					break
				if values:
					result[key] = values.pop()
		return None if conflict else result
	# @used-by :meth:`BrowserIdentityExtractor.__iter_objects()`
	@classmethod
	def __iter_dict(cls, value: dict):
		yield value
		for key in ('metadata', 'browser_context', 'browserContext', 'state', 'result', 'value', 'content'):
			if key in value:
				yield from cls.__iter_objects(value[key])
		if value.get('type') in ('input_text', 'text') and isinstance(value.get('text'), str):
			yield from cls.__iter_objects(value['text'])
	# @used-by :meth:`BrowserIdentityExtractor.__iter_dict()`
	# @used-by :meth:`BrowserIdentityExtractor.extract_identity()`
	@classmethod
	def __iter_objects(cls, value):
		if isinstance(value, list):
			for part in value:
				yield from cls.__iter_objects(part)
		elif isinstance(value, str):
			parsed, ok = (None, False)
			try:
				parsed = json.loads(value)
				ok = True
			except ValueError:
				ok = False
			if ok and (not isinstance(parsed, str)):
				yield from cls.__iter_objects(parsed)
		elif isinstance(value, dict):
			yield from cls.__iter_dict(value)
	# @used-by :meth:`BrowserIdentityExtractor.extract_identity()`
	@staticmethod
	def __merge(present: list[dict]) -> dict | None:
		merged, conflict = ({}, False)
		for candidate in present:
			for key, value in candidate.items():
				if key in merged and merged[key] != value:
					conflict = True
					break
				merged[key] = value
			if conflict:
				break
		return merged if not conflict and all((key in merged for key in ('browser_id', 'tab_id'))) else None
	# @used-by :meth:`Df.Harness.Experiment.AssertionEvaluator.AssertionEvaluator.__is_primary()`
	# @used-by :meth:`Df.Harness.Experiment.TraceContextAuditor.TraceContextAuditor.issues()`
	# @used-by :meth:`Df.Harness.Experiment.TraceInspector.TraceInspector.event_browser_identity()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_trace_inspector_classes()`
	def extract_identity(self) -> dict | None:
		if not CallChainParser.event_actions(self.__event):
			r = None
		else:
			name = CallChainParser.native_tool_name(self.__event)
			is_script = name.endswith(('cua_repl__js', 'browser__run'))
			candidates = [] if is_script else [self.__extract_dict(self.__event.get('arguments', {}))]
			candidates += [self.__extract_dict(value) for value in self.__iter_objects(self.__event.get('result'))]
			if any((None is value for value in candidates)):
				r = None
			else:
				present = [value for value in candidates if value]
				r = self.__merge(present) if present else None
		return r
