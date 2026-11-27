# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Analysis.JsonPointer import JsonPointer
from Df.Harness.Experiment.BrowserIdentityExtractor import BrowserIdentityExtractor
from Df.Harness.Experiment.CallChainParser import CallChainParser
from Df.Harness.Experiment.RequirementValidator import RequirementValidator
import json
_NUMERIC_OPS = {'gt': lambda a, b: a > b, 'gte': lambda a, b: a >= b, 'lt': lambda a, b: a < b, 'lte': lambda a, b: a <= b}
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AssertionEvaluator:
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.load_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__audit_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunValidator.RunValidator.evaluate_assertions()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def __init__(self, run: dict, contents: dict, events: dict) -> None:
		self.__run = run
		self.__contents = contents
		self.__events = events
		self.__artifacts = {item.get('id'): item for item in run.get('artifacts', []) if isinstance(item, dict)}
	# @used-by :meth:`AssertionEvaluator.__evaluate_one()`
	@staticmethod
	def __compare(actual, operator: str, expected) -> bool:
		if 'contains' == operator:
			if not isinstance(actual, str) or not isinstance(expected, str):
				raise ValueError('contains needs text')
			r = expected in actual
		elif operator in _NUMERIC_OPS:
			if type(actual) not in (int, float) or type(expected) not in (int, float):
				raise ValueError('Numeric comparison needs JSON numbers')
			r = _NUMERIC_OPS[operator](actual, expected)
		else:
			both_num = type(actual) in (int, float) and type(expected) in (int, float)
			equal = (actual == expected) if both_num else (type(actual) is type(expected) and actual == expected)
			r = equal if 'equals' == operator else not equal
		return r
	# @used-by :meth:`AssertionEvaluator.evaluate()`
	def __evaluate_one(self, assertion: dict) -> dict:
		r = {'assertion_id': assertion['id'], 'status': 'unverified'}
		try:
			artifact = self.__select_artifact(assertion)
			actual = self.__select_raw(self.__contents[artifact['id']], assertion['locator'])
			positive = self.__compare(actual, assertion['operator'], assertion['expected'])
			dis = assertion['disconfirming']
			negative = self.__compare(actual, dis['operator'], dis['expected'])
			r.update(artifact_id=artifact['id'], artifact_sha256=artifact['sha256'], positive=positive, disconfirming=negative, selected_value_sha256=RequirementValidator.digest(actual), status=self.__verdict(positive, negative))
		except (ValueError, TypeError, KeyError, IndexError, UnicodeError) as exc:
			r['reason'] = type(exc).__name__ + ': missing, ambiguous or unparsable primary measurement'
		return r
	# @used-by :meth:`AssertionEvaluator.__select_raw()`
	@staticmethod
	def __invalid_constant(_value) -> None:
		raise ValueError('Non-finite JSON number')
	# @used-by :meth:`AssertionEvaluator.__select_artifact()`
	def __is_primary(self, artifact: dict) -> bool:
		method = self.__run['requirement']['method']
		r = artifact.get('observation_kind') == method and bool(artifact.get('source_observation'))
		if artifact.get('native_event_id'):
			event = self.__events.get(artifact['native_event_id'], {})
			r = bool(CallChainParser.event_actions(event)) and None is not BrowserIdentityExtractor(event).extract_identity() if method in ('browser_scenario', 'admin', 'geolocation') else 'serp' == method and True is event.get('successful')
		if 'geolocation' == method and True is artifact.get('geolocation_verified'):
			r = True
		return r
	# @used-by :meth:`AssertionEvaluator.__evaluate_one()`
	def __select_artifact(self, assertion: dict) -> dict:
		matches = [item for item in self.__artifacts.values() if item.get('id') == assertion['artifact_id']] if assertion.get('artifact_id') else [item for item in self.__artifacts.values() if item.get('role') == assertion.get('artifact_role')]
		if 1 != len(matches):
			raise ValueError('Assertion must select exactly one primary artifact')
		artifact = matches[0]
		if not self.__is_primary(artifact):
			raise ValueError('Assertion does not select an authentic primary measurement of this method')
		return artifact
	# @used-by :meth:`AssertionEvaluator.__evaluate_one()`
	@classmethod
	def __select_raw(cls, raw: bytes, locator: dict):
		if 'text' != locator['type']:
			r = JsonPointer(json.loads(raw, parse_constant=cls.__invalid_constant), locator['value'], decode_uri=False).resolve()
		else:
			text = raw.decode('utf-8')
			if locator['value'] and locator['value'] not in text:
				raise ValueError('Text locator absent')
			r = locator['value'] or text
		return r
	# @used-by :meth:`AssertionEvaluator.__evaluate_one()`
	@staticmethod
	def __verdict(positive: bool, negative: bool) -> str:
		if positive and (not negative):
			r = 'verified'
		elif negative and (not positive):
			r = 'refuted'
		else:
			r = 'unverified'
		return r
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.load_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__audit_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunValidator.RunValidator.evaluate_assertions()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def evaluate(self) -> dict:
		results = [self.__evaluate_one(a) for a in self.__run['requirement'].get('assertions', [])]
		statuses = {item['status'] for item in results}
		status = 'refuted' if 'refuted' in statuses else 'unverified' if not results or 'unverified' in statuses else 'verified'
		return {'status': status, 'assertions': results, 'interpretation': 'Restricted predicates establish only the preregistered raw property; A.A checks semantic entailment and alternative explanations'}
