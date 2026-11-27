# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Workflow.StateUpdater import StateUpdater
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RequestUnadopter:
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.unadopt_requests()`
	def __init__(self, root, *, conversation_id=None, request_ids=None, engine=None, update_fn=None) -> None:
		self.__root = root
		self.__conversation_id = conversation_id
		self.__req_ids = set(request_ids or [])
		self.__engine = engine
		self.__update_fn = update_fn
	# @used-by :meth:`RequestUnadopter.unadopt()`
	def __apply(self, state: dict) -> None:
		state['requests'] = [x for x in state.get('requests', []) if not ((self.__conversation_id and x.get('native_conversation_id') == self.__conversation_id) or (self.__req_ids and x.get('id') in self.__req_ids))]
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.unadopt_requests()`
	def unadopt(self) -> dict:
		if not self.__conversation_id and (not self.__req_ids):
			raise ValueError('Provide --conversation or at least one --request-id to unadopt')
		upd = (lambda ev, fn: StateUpdater(self.__root, ev, fn, engine=self.__engine).update()) if None is self.__update_fn else (lambda ev, fn: self.__update_fn(self.__root, ev, fn))
		return upd({'action': 'unadopt_requests', 'conversation_id': self.__conversation_id, 'request_ids': sorted(self.__req_ids)}, self.__apply)
