# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Analysis.AssertionValidator import AssertionValidator
from Df.Harness.Analysis.IssueHintAnnotator import IssueHintAnnotator
from Df.Qa.lib.validation.check_strict import df_is_sne
import hashlib
import json
STATUSES = ('verified', 'refuted', 'unverified', 'unavailable')
METHODS = ('http', 'dom', 'browser_scenario', 'admin', 'serp', 'geolocation')
OPERATORS = ('equals', 'not_equals', 'contains', 'gt', 'gte', 'lt', 'lte')
PROPERTY_METHODS = {'content': set(METHODS), 'markup': {'http', 'dom', 'browser_scenario'}, 'dom': {'dom', 'browser_scenario'}, 'interaction': {'browser_scenario'}, 'currency_transition': {'browser_scenario'}, 'ip_country': {'geolocation', 'browser_scenario'}, 'admin_configuration': {'admin'}, 'serp': {'serp'}, 'platform_capability': {'http', 'dom'}, 'causality': set(), 'business_impact': set()}
_REQ_FIELDS = ('claim', 'expected', 'falsification', 'discriminating_test', 'completion_criterion')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RequirementValidator:
	# @used-by :func:`agent_tools.experiments.requirement_issues()`
	# @used-by :meth:`Df.Harness.Experiment.PlanLoader.PlanLoader.load_plan()`
	# @used-by :meth:`Df.Harness.Experiment.PlanPreparer.PlanPreparer.prepare_plan()`
	# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.__check_header()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__init_run()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def __init__(self, requirements) -> None:
		self.__requirements = requirements
	# @used-by :meth:`RequirementValidator.__check_one()`
	@staticmethod
	def __check_fields(label: str, req: dict, seen: set[str], issues: list[str]) -> None:
		ident = req.get('id')
		if not df_is_sne(ident) or ident in seen:
			issues.append(label + ': unique nonempty id required')
		if isinstance(ident, str):
			seen.add(ident)
		for field in _REQ_FIELDS:
			if not df_is_sne(req.get(field)):
				issues.append(label + f': {field} required')
		alternatives = req.get('alternatives')
		if not isinstance(alternatives, list) or not alternatives or (not all((df_is_sne(x) for x in alternatives))):
			issues.append(label + ': explicit alternative explanations required')
	# @used-by :meth:`RequirementValidator.__check_one()`
	@staticmethod
	def __check_method_and_scope(label: str, req: dict, issues: list[str]) -> None:
		prop, method = (req.get('property'), req.get('method'))
		if prop not in PROPERTY_METHODS or method not in METHODS:
			issues.append(label + ': supported property and measurement method required')
		elif method not in PROPERTY_METHODS[prop]:
			issues.append(label + ': method cannot establish the requested property; split the observation from the inference')
		scope = req.get('scope')
		if not isinstance(scope, dict) or not isinstance(scope.get('objects'), list) or (not scope['objects']) or (not all((df_is_sne(x) for x in scope['objects']))):
			issues.append(label + ': scope.objects must identify the exact sampled objects')
		if not isinstance(req.get('conditions'), dict):
			issues.append(label + ': explicit conditions object required')
	# @used-by :meth:`RequirementValidator.issues()`
	def __check_one(self, number: int, req, seen: set[str], issues: list[str]) -> None:
		label = f'Requirement {number}'
		if not isinstance(req, dict):
			issues.append(label + ': object required')
		else:
			self.__check_fields(label, req, seen, issues)
			self.__check_method_and_scope(label, req, issues)
			issues.extend(AssertionValidator(label, req, OPERATORS).issues())
	# @used-by :func:`agent_tools.experiments.digest()`
	# @used-by :meth:`Df.Harness.Experiment.AssertionEvaluator.AssertionEvaluator.__evaluate_one()`
	# @used-by :meth:`Df.Harness.Experiment.PlanLoader.PlanLoader.load_plan()`
	# @used-by :meth:`Df.Harness.Experiment.PlanPreparer.PlanPreparer.prepare_plan()`
	# @used-by :meth:`Df.Harness.Experiment.ResultValidator.ResultValidator.__check_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.__check_unsigned_digest()`
	# @used-by :meth:`Df.Harness.Experiment.RunLoader.RunLoader.__load_raw()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__init_run()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__write_run()`
	@staticmethod
	def digest(value) -> str:
		return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
	# @used-by :func:`agent_tools.experiments.requirement_issues()`
	# @used-by :meth:`Df.Harness.Experiment.PlanLoader.PlanLoader.load_plan()`
	# @used-by :meth:`Df.Harness.Experiment.PlanPreparer.PlanPreparer.prepare_plan()`
	# @used-by :meth:`Df.Harness.Experiment.RunAuditor.RunAuditor.__check_header()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__init_run()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def issues(self) -> list[str]:
		if not isinstance(self.__requirements, list) or not self.__requirements:
			raw = ['Research needs nonempty property-specific experimental requirements']
		else:
			raw, seen = ([], set())
			for number, req in enumerate(self.__requirements, 1):
				self.__check_one(number, req, seen, raw)
		return IssueHintAnnotator('experiment', raw).annotate()
