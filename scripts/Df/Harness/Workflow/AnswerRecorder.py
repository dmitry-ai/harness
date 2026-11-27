# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Review.ReviewAuthorizer import ReviewAuthorizer
from Df.Harness.Workflow.StateLoader import StateLoader
from Df.Harness.Workflow.StateUpdater import StateUpdater
import json
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AnswerRecorder:
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.record_current_answer()`
	def __init__(self, root, response: str, *, journal_directory=None, request_ids=None, preauthorized=None, recorded_steps=None, turn_token=None, engine=None, authorize_fn=None, update_fn=None) -> None:
		self.__root = root
		self.__response = response
		self.__journal_directory = journal_directory
		self.__request_ids = request_ids
		self.__preauthorized = preauthorized
		self.__recorded_steps = recorded_steps
		self.__turn_token = turn_token
		self.__engine = engine
		self.__authorize_fn = authorize_fn
		self.__update_fn = update_fn
	# @used-by :meth:`AnswerRecorder.record()`
	def __apply_answer(self, root_p, locked_state: dict, initial_state: dict, approval: dict, auth_kw: dict, ids: set, turn: str, steps: list, directory, resp_sha: str) -> None:
		if locked_state != initial_state:
			if None is self.__authorize_fn:
				ReviewAuthorizer(root_p, locked_state, package_path=approval['package'], **auth_kw).authorize()
			else:
				self.__authorize_fn(root_p, locked_state, package_path=approval['package'], **auth_kw)
		for request in locked_state['requests']:
			if request['id'] in ids:
				request['response_prepared'] = {'turn': turn, 'steps': steps, 'journal': str(directory), 'sha256': resp_sha, 'review_approval': approval}
	# @used-by :meth:`AnswerRecorder.record()`
	def __authorize_and_select(self, root_p) -> tuple[dict, dict, dict, list]:
		state = StateLoader(root_p).load() if None is self.__engine else self.__engine.load()
		filter_ids = set(self.__request_ids) if None is not self.__request_ids else None
		auth_kw = {'response': self.__response, **({'request_ids': filter_ids} if None is not filter_ids else {})}
		if None is not self.__preauthorized:
			approval = self.__preauthorized
		elif None is self.__authorize_fn:
			approval = ReviewAuthorizer(root_p, state, **auth_kw).authorize()
		else:
			approval = self.__authorize_fn(root_p, state, **auth_kw)
		unanswered = [x for x in state['requests'] if not x.get('response_prepared') and (None is filter_ids or x['id'] in filter_ids)]
		if not unanswered:
			raise ValueError('No unrecorded current requests; import exact native inputs or save the current request first')
		return (state, auth_kw, approval, unanswered)
	# @used-by :meth:`AnswerRecorder.record()`
	def __check_red_flags(self, pp) -> None:
		analysis_path = pp.kb_dir / 'Analysis.json'
		if analysis_path.is_file():
			try:
				val = json.loads(analysis_path.read_text(encoding='utf-8-sig'))
			except Exception:
				val = None
			if isinstance(val, dict) and [] == val.get('red_flags') and re.search('(?im)^\\s*#{1,6}\\s+Red Flags\\b', self.__response):
				raise ValueError('Do not include a Red Flags heading in the response when Analysis.json red_flags is empty (INIT-5)')
	# @used-by :meth:`AnswerRecorder.record()`
	def __resolve_steps(self, root_p, directory, unanswered: list) -> tuple[str, list]:
		from agent_tools.journal import record_answer
		turn = self.__turn_token or unanswered[-1]['id']
		if None is not self.__recorded_steps:
			steps = list(self.__recorded_steps)
		else:
			if not re.fullmatch('[A-Za-z0-9_-]{1,100}', turn):
				turn = 'native-' + df_sha256(turn.encode('utf-8'))
			steps = record_answer(directory, [x['text'] for x in unanswered], self.__response, turn, [x['id'] for x in unanswered], admission_roots=[root_p, directory])
		return (turn, steps)
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.record_current_answer()`
	def record(self) -> dict:
		from agent_tools.journal import ensure_project_journal_upgraded, resolve_journal_dir
		from agent_tools.links import chat_reply_link_issues
		from agent_tools.path_registry import project_paths
		ensure_project_journal_upgraded(self.__root, selected=self.__journal_directory)
		pp = project_paths(self.__root, exact_root=True)
		if None is not self.__engine:
			self.__engine.pp = pp
		issues = chat_reply_link_issues(self.__response)
		if issues:
			raise ValueError('\n'.join(issues))
		self.__check_red_flags(pp)
		state, auth_kw, approval, unanswered = self.__authorize_and_select(pp.root)
		directory = resolve_journal_dir(pp.root, self.__journal_directory)
		turn, steps = self.__resolve_steps(pp.root, directory, unanswered)
		ids, resp_sha = ({x['id'] for x in unanswered}, df_sha256(self.__response.encode()))
		upd = (lambda ev, fn: StateUpdater(pp.root, ev, fn, engine=self.__engine).update()) if None is self.__update_fn else (lambda ev, fn: self.__update_fn(pp.root, ev, fn))
		result = upd({'action': 'reply_prepared', 'turn': turn, 'steps': steps}, lambda ls: self.__apply_answer(pp.root, ls, state, approval, auth_kw, ids, turn, steps, directory, resp_sha))
		return {**result, 'journal_steps': steps, 'delivery_verified': False}
