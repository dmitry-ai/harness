# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Workflow.StateUpdater import StateUpdater
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class QuestionHandoff:
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.handoff()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def __init__(self, root, ident: str, previous_owner: str, new_owner: str, reason: str, *, update_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__root = project_paths(root, exact_root=True).root
		self.__ident = ident
		self.__previous_owner = previous_owner
		self.__new_owner = new_owner
		self.__reason = reason
		self.__update_fn = update_fn
	# @used-by :meth:`QuestionHandoff.handoff()`
	def __apply(self, state: dict) -> None:
		q = state['questions'][self.__ident]
		if q['owner'] != self.__previous_owner or 'running' != q['status']:
			raise ValueError('Task owner/status changed; refresh native progress before handoff')
		q.update(owner=self.__new_owner, handoff_reason=self.__reason)
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.handoff()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def handoff(self) -> dict:
		if not all((isinstance(s, str) and s.strip() for s in (self.__previous_owner, self.__new_owner, self.__reason))):
			raise ValueError('Explicit previous owner, new owner and observed stopping reason required')
		upd = (lambda ev, fn: StateUpdater(self.__root, ev, fn).update()) if None is self.__update_fn else (lambda ev, fn: self.__update_fn(self.__root, ev, fn))
		return upd({'action': 'handoff', 'question_id': self.__ident, 'reason': self.__reason}, self.__apply)
