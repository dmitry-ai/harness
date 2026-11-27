# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Workflow.HashCollector import HashCollector
from Df.Harness.Workflow.StateUpdater import StateUpdater
from agent_tools.research import inside
import json
import re
import uuid
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class WorkflowResumer:
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.resume()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def __init__(self, root, reason: str, request=None, *, engine=None, update_fn=None) -> None:
		self.__root = root
		self.__reason = reason
		self.__request = request
		self.__engine = engine
		self.__update_fn = update_fn
	# @used-by :meth:`WorkflowResumer.resume()`
	def __apply(self, pp, state: dict) -> None:
		from agent_tools.upwork_data import normalize_job_id
		state['legacy'] = False
		if None is not self.__request:
			state['requests'].append({'id': uuid.uuid4().hex, 'time': HashCollector.utc_now(), 'text': self.__request})
		pj = json.loads(pp.project_json.read_text(encoding='utf-8'))
		source = inside(pp.root, pj['snapshot'])
		data = json.loads(source.read_text(encoding='utf-8'))
		if normalize_job_id(data.get('job_id')) != pj['job_id'] or not data.get('title') or (not data.get('description')):
			raise ValueError('Existing capture does not match this project')
		if re.fullmatch('[a-f0-9]{64}', source.stem) and HashCollector.file_hash(source) != source.stem:
			raise ValueError('Immutable capture hash differs')
		state['stages']['capture'] = {'status': 'complete', 'time': HashCollector.utc_now(), 'inputs': {}, 'outputs': HashCollector(pp.root, [pj['snapshot']]).collect(), 'method': 'verified saved capture'}
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.resume()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def resume(self) -> dict:
		from agent_tools.journal import ensure_project_journal_upgraded
		from agent_tools.path_registry import project_paths
		if not isinstance(self.__reason, str) or not self.__reason.strip():
			raise ValueError('Record why the current analysis is being continued')
		if None is not self.__request and (not isinstance(self.__request, str) or not self.__request.strip()):
			raise ValueError('Continuation request must preserve exact nonempty user text')
		ensure_project_journal_upgraded(self.__root)
		pp = project_paths(self.__root, exact_root=True)
		if None is not self.__engine:
			self.__engine.pp = pp
		upd = (lambda ev, fn: StateUpdater(pp.root, ev, fn, engine=self.__engine).update()) if None is self.__update_fn else (lambda ev, fn: self.__update_fn(pp.root, ev, fn))
		return upd({'action': 'resume', 'reason': self.__reason}, lambda state: self.__apply(pp, state))
