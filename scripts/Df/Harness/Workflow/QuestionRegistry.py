# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Workflow.QuestionAdder import QuestionAdder
from Df.Harness.Workflow.QuestionClaimer import QuestionClaimer
from Df.Harness.Workflow.QuestionContractAuditor import QuestionContractAuditor
from Df.Harness.Workflow.QuestionFinisher import QuestionFinisher
from Df.Harness.Workflow.QuestionHandoff import QuestionHandoff
from Df.Harness.Workflow.QuestionSearchRecorder import QuestionSearchRecorder
from Df.Harness.Workflow.ReceiptVerifier import ReceiptVerifier
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class QuestionRegistry:
	# @used-by :func:`agent_tools.workflow.add_question()`
	# @used-by :func:`agent_tools.workflow.claim_question()`
	# @used-by :func:`agent_tools.workflow.finish_question()`
	# @used-by :func:`agent_tools.workflow.handoff()`
	# @used-by :func:`agent_tools.workflow.question_contract_issues()`
	# @used-by :func:`agent_tools.workflow.questions_current()`
	# @used-by :func:`agent_tools.workflow.record_search()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__check_prereqs()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__check_prereqs()`
	# @used-by :meth:`Df.Harness.Workflow.StageStatusEvaluator.StageStatusEvaluator.__stage_current()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_remaining_branches()`
	def __init__(self, root, *, update_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.pp = project_paths(root, exact_root=True)
		self.root = self.pp.root
		self.__update_fn = update_fn
	# @used-by :func:`agent_tools.workflow.add_question()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_remaining_branches()`
	def add(self, ident: str, question: str, impact: str, done_when: str, inputs: list, outputs: list, *, requirements=None) -> dict:
		return QuestionAdder(self.root, ident, question, impact, done_when, inputs, outputs, requirements=requirements, update_fn=self.__update_fn).add()
	# @used-by :func:`agent_tools.workflow.claim_question()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_remaining_branches()`
	def claim(self, ident: str, owner: str) -> dict:
		return QuestionClaimer(self.root, ident, owner, update_fn=self.__update_fn).claim()
	# @used-by :func:`agent_tools.workflow.question_contract_issues()`
	# @used-by :meth:`QuestionRegistry.current()`
	def contract_issues(self, question: dict) -> list[str]:
		return QuestionContractAuditor(self.root, question).issues()
	# @used-by :func:`agent_tools.workflow.questions_current()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__check_prereqs()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__check_prereqs()`
	# @used-by :meth:`Df.Harness.Workflow.StageStatusEvaluator.StageStatusEvaluator.__stage_current()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def current(self, state: dict) -> bool:
		return all((q['status'] in ('complete', 'gap') and ReceiptVerifier(self.root, {'inputs': q['inputs'], 'outputs': q['results']}).is_current() and (not self.contract_issues(q)) for q in state['questions'].values()))
	# @used-by :func:`agent_tools.workflow.finish_question()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_remaining_branches()`
	def finish(self, ident: str, owner: str, outputs: list, gap=None, *, results=None) -> dict:
		return QuestionFinisher(self.root, ident, owner, outputs, gap=gap, results=results, update_fn=self.__update_fn).finish()
	# @used-by :func:`agent_tools.workflow.handoff()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	def handoff(self, ident: str, previous_owner: str, new_owner: str, reason: str) -> dict:
		return QuestionHandoff(self.root, ident, previous_owner, new_owner, reason, update_fn=self.__update_fn).handoff()
	# @used-by :func:`agent_tools.workflow.record_search()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	def record_search(self, ident: str, owner: str, query: str, useful: bool=False, method_change=None) -> dict:
		return QuestionSearchRecorder(self.root, ident, owner, query, useful=useful, method_change=method_change, update_fn=self.__update_fn).record()
