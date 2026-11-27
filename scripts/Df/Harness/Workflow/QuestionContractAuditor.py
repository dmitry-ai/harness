# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Experiment.RequirementValidator import RequirementValidator
from Df.Harness.Experiment.ResultValidator import ResultValidator
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class QuestionContractAuditor:
	# @used-by :meth:`Df.Harness.Workflow.QuestionFinisher.QuestionFinisher.__apply()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.contract_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def __init__(self, root, question: dict) -> None:
		self.__root = root
		self.__question = question
	# @used-by :meth:`QuestionContractAuditor.issues()`
	def __check_results(self, expected: dict, results: list, out: list[str]) -> None:
		seen: set[str] = set()
		for result in results:
			ident = result.get('requirement_id') if isinstance(result, dict) else None
			if ident not in expected or ident in seen:
				out.append('Each declared requirement must have one structured result')
			else:
				seen.add(ident)
				out.extend(ResultValidator(self.__root, expected[ident], result).issues())
		if seen != set(expected):
			out.append('Research requirement results are incomplete')
		if any((item.get('status') in ('unverified', 'unavailable') for item in results if isinstance(item, dict))) and (not self.__question.get('gap')):
			out.append('Unavailable/unverified requirements require an explicit question gap')
	# @used-by :meth:`QuestionContractAuditor.issues()`
	@staticmethod
	def __expected_map(requirements) -> dict:
		return {req['id']: req for req in requirements if isinstance(req, dict) and isinstance(req.get('id'), str)} if isinstance(requirements, list) else {}
	# @used-by :meth:`Df.Harness.Workflow.QuestionFinisher.QuestionFinisher.__apply()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.contract_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def issues(self) -> list[str]:
		requirements = self.__question.get('requirements')
		r = RequirementValidator(requirements).issues()
		results = self.__question.get('requirement_results', [])
		if not isinstance(results, list):
			r.append('Structured requirement_results list is required')
		else:
			self.__check_results(self.__expected_map(requirements), results, r)
		return r
