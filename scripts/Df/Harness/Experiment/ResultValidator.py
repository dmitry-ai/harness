# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Experiment.RequirementValidator import RequirementValidator, STATUSES
from Df.Harness.Experiment.RunLoader import RunLoader
from Df.Qa.lib.validation.check_strict import df_is_sne
from agent_tools.research import inside
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ResultValidator:
	# @used-by :func:`agent_tools.experiments.result_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def __init__(self, root, requirement: dict, result) -> None:
		self.__root = root
		self.__requirement = requirement
		self.__result = result
	# @used-by :meth:`ResultValidator.issues()`
	def __check_run(self, issues: list[str]) -> None:
		try:
			from agent_tools.path_registry import project_paths
			path = inside(project_paths(self.__root, exact_root=True).kb_dir, self.__result.get('experiment', ''))
			run = RunLoader(self.__root, self.__result.get('experiment', '')).load_run()
			if df_sha256(path.read_bytes()) != self.__result.get('experiment_sha256'):
				issues.append('Experimental result hash differs from immutable run')
			if run['requirement_sha256'] != RequirementValidator.digest(self.__requirement):
				issues.append('Experimental run was performed for a different requirement version')
			if run['status'] != self.__result.get('status'):
				issues.append('Reported result status differs from the actual recorded run')
		except (OSError, ValueError, TypeError, KeyError) as exc:
			issues.append('Experimental run is missing, invalid or changed: ' + str(exc))
	# @used-by :func:`agent_tools.experiments.result_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_validators_and_evaluators()`
	def issues(self) -> list[str]:
		if not isinstance(self.__result, dict):
			r = ['Property result object required']
		else:
			r = []
			if self.__result.get('requirement_id') != self.__requirement.get('id') or self.__result.get('status') not in STATUSES:
				r.append('Property result must identify the exact requirement and valid status')
			self.__check_run(r)
			if self.__result.get('status') in ('unverified', 'unavailable') and (not df_is_sne(self.__result.get('limitation'))):
				r.append('Property result needs an explicit limitation')
		return r
