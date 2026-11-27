# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Workflow.HashCollector import HashCollector
from Df.Harness.Workflow.QuestionContractAuditor import QuestionContractAuditor
from Df.Harness.Workflow.StateUpdater import StateUpdater
from agent_tools.research import inside
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class QuestionFinisher:
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.finish()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	def __init__(self, root, ident: str, owner: str, outputs: list, gap=None, *, results=None, update_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__root = project_paths(root, exact_root=True).root
		self.__ident = ident
		self.__owner = owner
		self.__outputs = outputs
		self.__gap = gap
		self.__results = results
		self.__update_fn = update_fn
	# @used-by :meth:`QuestionFinisher.finish()`
	def __apply(self, state: dict) -> None:
		q = state['questions'][self.__ident]
		if q['owner'] != self.__owner or 'running' != q['status']:
			raise ValueError('Only the current task owner may finish the question')
		if not all((inside(self.__root, p).relative_to(self.__root).as_posix() in q['allowed_outputs'] for p in self.__outputs)):
			raise ValueError('Result was not among declared outputs')
		if HashCollector(self.__root, list(q['inputs'])).collect() != q['inputs']:
			raise ValueError('Question inputs changed; review the result against the new inputs')
		if not self.__outputs or (None is not self.__gap and (not self.__gap.strip())):
			raise ValueError('A saved result/report and explicit gap explanation are required')
		issues = QuestionContractAuditor(self.__root, {**q, 'gap': self.__gap, 'requirement_results': self.__results}).issues()
		if issues:
			raise ValueError('\n'.join(issues))
		q.update(status='gap' if self.__gap else 'complete', results=HashCollector(self.__root, self.__outputs).collect(), gap=self.__gap, requirement_results=self.__results)
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.finish()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	def finish(self) -> dict:
		upd = (lambda ev, fn: StateUpdater(self.__root, ev, fn).update()) if None is self.__update_fn else (lambda ev, fn: self.__update_fn(self.__root, ev, fn))
		return upd({'action': 'finish_question', 'question_id': self.__ident}, self.__apply)
