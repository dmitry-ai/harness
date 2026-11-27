# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Experiment.PlanLoader import PlanLoader
from Df.Harness.Experiment.PlanPreparer import PlanPreparer
from Df.Harness.Experiment.PreregistrationAuditor import CLI_NAMES, PreregistrationAuditor
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PlanStore:
	CLI_NAMES = CLI_NAMES
	# @used-by :func:`agent_tools.experiments.load_plan()`
	# @used-by :func:`agent_tools.experiments.prepare_experiment()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def __init__(self, root) -> None:
		from agent_tools.path_registry import project_paths
		self.pp = project_paths(root, exact_root=True)
		self.root = self.pp.root
	# @used-by :func:`agent_tools.experiments.load_plan()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def load(self, reference: str) -> dict:
		return PlanLoader(self.root, reference).load_plan()
	# @used-by :func:`agent_tools.experiments.prepare_experiment()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def prepare(self, requirement: dict, *, amendment_of=None, amendment_reason=None) -> dict:
		return PlanPreparer(self.root, requirement, amendment_of=amendment_of, amendment_reason=amendment_reason).prepare_plan()
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	def preregistration_issues(self, run: dict, events=None) -> list[str]:
		return PreregistrationAuditor(self.root, run, events).issues()
