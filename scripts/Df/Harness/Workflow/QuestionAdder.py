# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Experiment.RequirementValidator import RequirementValidator
from Df.Harness.Workflow.HashCollector import HashCollector
from Df.Harness.Workflow.StateUpdater import StateUpdater
from agent_tools.research import inside
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class QuestionAdder:
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.add()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def __init__(self, root, ident: str, question: str, impact: str, done_when: str, inputs: list, outputs: list, *, requirements=None, update_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__root = self.__pp.root
		self.__ident = ident
		self.__question = question
		self.__impact = impact
		self.__done_when = done_when
		self.__inputs = inputs
		self.__outputs = outputs
		self.__requirements = requirements
		self.__update_fn = update_fn
	# @used-by :meth:`QuestionAdder.add()`
	def __apply(self, state: dict, entry: dict) -> None:
		if self.__ident in state['questions']:
			raise ValueError('Question already exists; use its saved inputs/results')
		state['questions'][self.__ident] = {**entry, 'time': HashCollector.utc_now()}
	# @used-by :meth:`QuestionAdder.add()`
	def __validate_outputs(self) -> list[str]:
		permitted = [inside(self.__root, path).relative_to(self.__root).as_posix() for path in self.__outputs]
		ag_prefix = self.__pp.rel_to_root(self.__pp.agent_dir).rstrip('/') + '/'
		wf_prefix = self.__pp.rel_to_root(self.__pp.workflow_json).rsplit('.json', 1)[0]
		if not permitted or any((not (p.startswith('\ua616/') or p.startswith(ag_prefix)) or p.startswith('\ua616/data/workflow') or p.startswith(wf_prefix) for p in permitted)):
			raise ValueError('Declare exact project-owned outputs under \ua616; not workflow state')
		return permitted
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.add()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def add(self) -> dict:
		if not re.fullmatch('[A-Z][A-Z0-9-]*', self.__ident) or not all((isinstance(x, str) and x.strip() for x in (self.__question, self.__impact, self.__done_when))):
			raise ValueError('Question needs a stable ID, question, impact and completion criterion')
		if not self.__inputs:
			raise ValueError('Declare at least the saved capture or relevant KB module as question input')
		issues = RequirementValidator(self.__requirements).issues()
		if issues:
			raise ValueError('\n'.join(issues))
		input_hashes = HashCollector(self.__root, self.__inputs).collect()
		permitted = self.__validate_outputs()
		entry = {'id': self.__ident, 'question': self.__question, 'impact': self.__impact, 'done_when': self.__done_when, 'inputs': input_hashes, 'allowed_outputs': permitted, 'status': 'pending', 'owner': None, 'searches': [], 'results': {}, 'requirements': self.__requirements, 'requirement_results': []}
		upd = (lambda ev, fn: StateUpdater(self.__root, ev, fn).update()) if None is self.__update_fn else (lambda ev, fn: self.__update_fn(self.__root, ev, fn))
		return upd({'action': 'question', 'question_id': self.__ident}, lambda state: self.__apply(state, entry))
