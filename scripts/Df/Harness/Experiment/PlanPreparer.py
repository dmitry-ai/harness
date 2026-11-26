# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Experiment.PlanLoader import PlanLoader
from Df.Harness.Experiment.RequirementValidator import RequirementValidator
from Df.Qa.lib.validation.check_strict import df_is_sne
from agent_tools.research import json_data
from agent_tools.storage import create_bytes
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PlanPreparer:
	# @used-by :meth:`Df.Harness.Experiment.PlanStore.PlanStore.prepare()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	def __init__(self, root, requirement: dict, *, amendment_of=None, amendment_reason=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__requirement = requirement
		self.__amendment_of = amendment_of
		self.__amendment_reason = amendment_reason
	# @used-by :meth:`PlanPreparer.prepare_plan()`
	def __resolve_previous(self) -> dict | None:
		r = None
		if None is self.__amendment_of:
			if self.__amendment_reason:
				raise ValueError('Amendment reason needs the exact previous immutable plan')
		else:
			r = PlanLoader(self.__pp.root, self.__amendment_of).load_plan()
			if not df_is_sne(self.__amendment_reason):
				raise ValueError('Plan amendment needs an explicit reason')
			if r['requirement']['id'] != self.__requirement['id']:
				raise ValueError('An amendment must preserve the experimental requirement ID')
		return r
	# @used-by :meth:`Df.Harness.Experiment.PlanStore.PlanStore.prepare()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	def prepare_plan(self) -> dict:
		issues = RequirementValidator([self.__requirement]).issues()
		if issues:
			raise ValueError('; '.join(issues))
		previous = self.__resolve_previous()
		plan = {'schema_version': 1, 'kind': 'experiment_plan', 'prepared_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'requirement': self.__requirement, 'requirement_sha256': RequirementValidator.digest(self.__requirement), 'revision': previous['revision'] + 1 if previous else 1, 'amendment_of': self.__amendment_of, 'amendment_reason': self.__amendment_reason, 'previous_plan_sha256': RequirementValidator.digest(previous) if previous else None}
		directory = self.__pp.evidence_dir / 'Experiments/Plans' / RequirementValidator.digest(plan)
		directory.mkdir(parents=True, exist_ok=False)
		path = directory / 'plan.json'
		create_bytes(path, json_data(plan))
		return {'upwork_experiment_plan': 1, 'project_root': str(self.__pp.root), 'plan': path.relative_to(self.__pp.kb_dir).as_posix(), 'plan_sha256': df_sha256(path.read_bytes()), **plan}
