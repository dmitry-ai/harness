# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Experiment.RequirementValidator import RequirementValidator
from agent_tools.research import inside
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PlanLoader:
	# @used-by :meth:`Df.Harness.Experiment.PlanPreparer.PlanPreparer.__resolve_previous()`
	# @used-by :meth:`Df.Harness.Experiment.PlanStore.PlanStore.load()`
	# @used-by :meth:`Df.Harness.Experiment.PreregistrationAuditor.PreregistrationAuditor.__load_plan()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__init_run()`
	# @used-by :meth:`PlanLoader.load_plan()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	def __init__(self, root, reference: str) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__reference = reference
	# @used-by :meth:`Df.Harness.Experiment.PlanPreparer.PlanPreparer.__resolve_previous()`
	# @used-by :meth:`Df.Harness.Experiment.PlanStore.PlanStore.load()`
	# @used-by :meth:`Df.Harness.Experiment.PreregistrationAuditor.PreregistrationAuditor.__load_plan()`
	# @used-by :meth:`Df.Harness.Experiment.RunRecorder.RunRecorder.__init_run()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	def load_plan(self) -> dict:
		path = inside(self.__pp.kb_dir, self.__reference)
		base = self.__pp.evidence_dir / 'Experiments/Plans'
		plan = json.loads(path.read_text(encoding='utf-8'))
		if not path.is_relative_to(base) or 'plan.json' != path.name or path.parent.name != RequirementValidator.digest(plan) or (1 != plan.get('schema_version')) or ('experiment_plan' != plan.get('kind')) or (plan.get('requirement_sha256') != RequirementValidator.digest(plan.get('requirement'))) or RequirementValidator([plan.get('requirement')]).issues():
			raise ValueError('Missing/changed immutable experimental plan')
		if plan.get('amendment_of'):
			previous = PlanLoader(self.__pp.root, plan['amendment_of']).load_plan()
			if plan.get('previous_plan_sha256') != RequirementValidator.digest(previous) or plan.get('revision') != previous['revision'] + 1:
				raise ValueError('Plan revision chain changed')
		return plan
