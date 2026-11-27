# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Workflow.HashCollector import HashCollector
from Df.Harness.Workflow.StateUpdater import StateUpdater
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class QuestionSearchRecorder:
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.record_search()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def __init__(self, root, ident: str, owner: str, query: str, useful: bool=False, method_change=None, *, update_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__root = project_paths(root, exact_root=True).root
		self.__ident = ident
		self.__owner = owner
		self.__query = query
		self.__useful = useful
		self.__method_change = method_change
		self.__update_fn = update_fn
	# @used-by :meth:`QuestionSearchRecorder.record()`
	def __apply(self, state: dict) -> None:
		q = state['questions'][self.__ident]
		if q['owner'] != self.__owner or 'running' != q['status']:
			raise ValueError('Only current task owner can record searches')
		recent = []
		for attempt in reversed(q['searches']):
			recent.append(attempt)
			if attempt.get('method_change') or 3 == len(recent):
				break
		if 3 == len(recent) and all((not x['useful'] for x in recent)) and (not self.__method_change):
			raise ValueError('Three unsuccessful searches: return a gap or document a different method before continuing')
		q['searches'].append({'query': ' '.join(self.__query.casefold().split()), 'useful': bool(self.__useful), 'method_change': self.__method_change, 'time': HashCollector.utc_now()})
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.record_search()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def record(self) -> dict:
		if not isinstance(self.__query, str) or not self.__query.strip():
			raise ValueError('Search query required')
		upd = (lambda ev, fn: StateUpdater(self.__root, ev, fn).update()) if None is self.__update_fn else (lambda ev, fn: self.__update_fn(self.__root, ev, fn))
		return upd({'action': 'search', 'question_id': self.__ident}, self.__apply)
