# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Review.QuorumEvaluator import QuorumEvaluator
from Df.Harness.Workflow.ReceiptVerifier import ReceiptVerifier
from Df.Harness.Workflow.RegistrationStatusChecker import RegistrationStatusChecker
STAGES = ('capture', 'identity_init', 'research', 'analysis', 'review', 'kb_review', 'finalize')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class StageStatusEvaluator:
	# @used-by :meth:`Df.Harness.Workflow.ProgressPublisher.ProgressPublisher.publish()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__apply()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.stage_statuses()`
	# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
	# @used-by :meth:`Df.Harness.Workflow.StatusSnapshotBuilder.StatusSnapshotBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_remaining_branches()`
	def __init__(self, root, state: dict, *, receipt_fn=None, reg_fn=None) -> None:
		self.__root = root
		self.__state = state
		self.__receipt_fn = receipt_fn
		self.__reg_fn = reg_fn
	# @used-by :meth:`StageStatusEvaluator.__stage_current()`
	def __check_finalize(self, receipt) -> bool:
		covered = receipt.get('request_ids') if receipt else None
		reqs = self.__state['requests']
		return covered == [request['id'] for request in reqs] if None is not covered else all((request.get('response_prepared') for request in reqs))
	# @used-by :meth:`StageStatusEvaluator.evaluate()`
	def __stage_current(self, stage: str, receipt) -> bool:
		is_rec_ok = (lambda rec: ReceiptVerifier(self.__root, rec).is_current()) if None is self.__receipt_fn else self.__receipt_fn
		r = bool(receipt and 'complete' == receipt.get('status') and is_rec_ok(receipt))
		if 'identity_init' == stage:
			reg = RegistrationStatusChecker(self.__root).status() if None is self.__reg_fn else self.__reg_fn()
			r = r and reg['complete']
		elif 'research' == stage and receipt:
			from Df.Harness.Workflow.QuestionRegistry import QuestionRegistry
			r = r and QuestionRegistry(self.__root).current(self.__state) and (receipt.get('research_questions') == self.__state['questions'])
		elif stage in ('review', 'kb_review', 'finalize') and r:
			r = QuorumEvaluator(self.__root, self.__state).approval_current(receipt.get('review_approval'))
			if 'finalize' == stage:
				r = r and self.__check_finalize(receipt)
		return r
	# @used-by :meth:`Df.Harness.Workflow.ProgressPublisher.ProgressPublisher.publish()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__apply()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.stage_statuses()`
	# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
	# @used-by :meth:`Df.Harness.Workflow.StatusSnapshotBuilder.StatusSnapshotBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_remaining_branches()`
	def evaluate(self) -> dict[str, str]:
		r, dep_ok = ({}, True)
		for stage in STAGES:
			receipt = self.__state['stages'].get(stage)
			current = self.__stage_current(stage, receipt)
			r[stage] = 'complete' if current and dep_ok else 'stale' if receipt else 'pending'
			dep_ok = dep_ok and current
		return r
