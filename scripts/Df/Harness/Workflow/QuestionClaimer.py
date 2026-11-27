# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Workflow.StateUpdater import StateUpdater
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class QuestionClaimer:
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.claim()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def __init__(self, root, ident: str, owner: str, *, update_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__root = project_paths(root, exact_root=True).root
		self.__ident = ident
		self.__owner = owner
		self.__update_fn = update_fn
	# @used-by :meth:`QuestionClaimer.claim()`
	def __apply(self, state: dict) -> None:
		q = state['questions'][self.__ident]
		if q['status'] in ('complete', 'gap'):
			raise ValueError('Use the existing result; reopening requires a new documented question')
		if q['owner'] and q['owner'] != self.__owner:
			raise ValueError('Question already has an owner; inspect native subagent status before explicit handoff')
		for other in state['questions'].values():
			if other['id'] != self.__ident and other['owner'] and ('running' == other['status']) and (set(other['allowed_outputs']) & set(q['allowed_outputs'])):
				raise ValueError('Another active question owns the same output file')
		q.update(owner=self.__owner, status='running')
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.claim()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def claim(self) -> dict:
		if not isinstance(self.__owner, str) or not self.__owner.strip():
			raise ValueError('Owner must be an observed session/subagent ID')
		upd = (lambda ev, fn: StateUpdater(self.__root, ev, fn).update()) if None is self.__update_fn else (lambda ev, fn: self.__update_fn(self.__root, ev, fn))
		return upd({'action': 'claim_question', 'question_id': self.__ident, 'owner': self.__owner}, self.__apply)
