# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Workflow.StateLoader import StateLoader
from Df.Harness.Workflow.StateUpdater import StateUpdater
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RequestAdopter:
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.adopt_requests()`
	def __init__(self, root, conversation_id: str, *, allow_finalized: bool=False, backend=None, platform=None, engine=None, update_fn=None) -> None:
		self.__root = root
		self.__conversation_id = conversation_id
		self.__allow_finalized = allow_finalized
		self.__backend = backend
		self.__platform = platform
		self.__engine = engine
		self.__update_fn = update_fn
	# @used-by :meth:`RequestAdopter.adopt()`
	@staticmethod
	def __apply(state: dict, requests: list, saved_answers: dict) -> None:
		recorded = {x['id']: x for x in state['requests'] if x.get('native_conversation_id')}
		incoming = {x['id'] for x in requests}
		exact_texts = {x['text'] for x in requests}
		state['requests'] = [x for x in state['requests'] if x['id'] not in incoming and (x.get('native_conversation_id') or x['text'] not in exact_texts)]
		for request in requests:
			prepared = saved_answers.get(request['id']) or recorded.get(request['id'], {}).get('response_prepared')
			state['requests'].append({**request, **({'response_prepared': prepared} if prepared else {})})
	# @used-by :meth:`RequestAdopter.adopt()`
	@staticmethod
	def __saved_answers(root_p, requests: list) -> dict:
		from agent_tools.journal import answer_groups, journal_pair_dirs, resolve_journal_dir, step_file
		from agent_tools.metadata import strip_leading_metadata_header
		jdir = resolve_journal_dir(root_p)
		_, res_dir = journal_pair_dirs(jdir)
		saved: dict = {}
		for group in answer_groups(jdir, request_ids={x['id'] for x in requests}):
			body_sha = group['response_sha256']
			if group.get('steps'):
				rp = step_file(res_dir, group['steps'][0], directory=jdir)
				if rp.is_file():
					try:
						body_sha = df_sha256(strip_leading_metadata_header(rp.read_bytes().decode('utf-8')).encode('utf-8'))
					except (OSError, UnicodeDecodeError):
						pass
			for ident in group.get('request_ids') or []:
				saved[ident] = {'turn': group['turn'], 'steps': group['steps'], 'sha256': body_sha}
		return saved
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.adopt_requests()`
	def adopt(self) -> dict:
		from agent_tools.journal import ensure_project_journal_upgraded
		from agent_tools.metrics import native_requests
		from agent_tools.path_registry import project_paths
		state = StateLoader(self.__root).load() if None is self.__engine else self.__engine.load()
		if 'complete' == state.get('stages', {}).get('finalize', {}).get('status') and (not self.__allow_finalized):
			raise ValueError('Initial analysis finalize stage is already complete. Post-finalize questions do not require adopt-requests unless explicitly reopening analysis with --allow-finalized')
		ensure_project_journal_upgraded(self.__root)
		pp = project_paths(self.__root, exact_root=True)
		if None is not self.__engine:
			self.__engine.pp = pp
		requests = native_requests(pp.root, self.__conversation_id, backend=self.__backend, platform=self.__platform)
		saved = self.__saved_answers(pp.root, requests)
		upd = (lambda ev, fn: StateUpdater(pp.root, ev, fn, engine=self.__engine).update()) if None is self.__update_fn else (lambda ev, fn: self.__update_fn(pp.root, ev, fn))
		return upd({'action': 'adopt_requests', 'conversation_id': self.__conversation_id}, lambda current: self.__apply(current, requests, saved))
