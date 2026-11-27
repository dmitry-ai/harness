# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Experiment.AssertionEvaluator import AssertionEvaluator
from Df.Harness.Experiment.CapabilityResolver import CapabilityResolver
from Df.Harness.Experiment.ConditionAuditor import CONTEXT_FIELDS, MODE_PATTERNS
from Df.Harness.Experiment.RunAuditor import RunAuditor
from Df.Harness.Experiment.RunLoader import RunLoader
from Df.Harness.Experiment.RunRecorder import RunRecorder
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RunValidator:
	CONTEXT_FIELDS = CONTEXT_FIELDS
	MODE_PATTERNS = MODE_PATTERNS
	# @used-by :func:`agent_tools.experiments.evaluate_assertions()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def __init__(self, root, run: dict, contents=None) -> None:
		self.root = Path(root).resolve() if None is not root else None
		self.run = run
		self.contents = contents if None is not contents else {}
		self.artifacts = {item.get('id'): item for item in run.get('artifacts', []) if isinstance(item, dict)}
		self.event_list = list(run.get('native_trace', {}).get('events', []))
		self.events = {event.get('id'): event for event in self.event_list if isinstance(event, dict)}
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	def capabilities(self) -> list[str]:
		return CapabilityResolver(self.run).capabilities()
	# @used-by :func:`agent_tools.experiments.evaluate_assertions()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def evaluate_assertions(self) -> dict:
		return AssertionEvaluator(self.run, self.contents, self.events).evaluate()
	# @used-by :func:`agent_tools.experiments.load_experiment()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	@classmethod
	def load(cls, root, reference: str) -> dict:
		return RunLoader(root, reference).load_run()
	# @used-by :meth:`RunValidator.run_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	def native_texts(self, ids: list) -> list[dict]:
		return [self.events[nid] for ident in ids if isinstance(ident, str) and (nid := self.artifacts.get(ident, {}).get('native_event_id')) in self.events]
	# @used-by :func:`agent_tools.experiments.record_experiment()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_experiment_extra_branches()`
	@classmethod
	def record(cls, root, specification, *, tool_trace=None) -> dict:
		return RunRecorder(root, specification, tool_trace=tool_trace).record_run()
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_experiment_plan_and_run_classes()`
	def run_issues(self) -> list[str]:
		return RunAuditor(self.run, self.artifacts, self.events, self.native_texts).issues()
