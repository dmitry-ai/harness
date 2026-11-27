# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from Df.Harness.Analysis.Validator import Validator
from Df.Harness.Project.Registry import Registry
from Df.Harness.Project.StageValidityGuard import StageValidityGuard
from Df.Harness.Review.ReviewAuthorizer import ReviewAuthorizer
from Df.Harness.Workflow.FinalizeStageRunner import FinalizeStageRunner
from Df.Harness.Workflow.HashCollector import HashCollector
from Df.Harness.Workflow.HealthAuditor import HealthAuditor
from Df.Harness.Workflow.QuestionRegistry import QuestionRegistry
from Df.Harness.Workflow.RegistrationStatusChecker import RegistrationStatusChecker
from Df.Harness.Workflow.StageStatusEvaluator import STAGES, StageStatusEvaluator
from Df.Harness.Workflow.StateUpdater import StateUpdater
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class StageCompleter:
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.complete_stage()`
	# @used-by :meth:`test_df_harness_s11_wave2a_facade_exports.DfHarnessS11Wave2aFacadeExportsTests.test_stage_completer_passes_platform_and_targets_to_registry_register()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	def __init__(self, root, stage: str, inputs: list, outputs: list, *, note=None, engine=None, check_project_fn=None, authorize_fn=None, drift_fn=None, update_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__root = self.__pp.root
		self.__stage = stage
		self.__inputs = inputs
		self.__outputs = outputs
		self.__note = note
		self.__engine = engine
		self.__check_project = (lambda r: HealthAuditor(r).check_project()) if None is check_project_fn else check_project_fn
		self.__authorize_fn = authorize_fn
		self.__drift_fn = drift_fn
		self.__update_fn = update_fn
	# @used-by :meth:`StageCompleter.complete()`
	def __apply(self, state: dict, in_hashes: dict, out_hashes: dict) -> None:
		if None is not self.__engine:
			self.__engine.invalidate_caches()
		statuses = StageStatusEvaluator(self.__root, state).evaluate() if None is self.__engine else self.__engine.stage_statuses(state)
		if any(('complete' != statuses[s] for s in STAGES[:STAGES.index(self.__stage)])):
			raise ValueError('Complete/check preceding stages before marking this stage complete')
		self.__check_prereqs(state, out_hashes)
		approval = self.__run_approval_gate(state, out_hashes)
		self.__write_stage_receipt(state, in_hashes, out_hashes, approval)
	# @used-by :meth:`StageCompleter.__apply()`
	def __check_prereqs(self, state: dict, out_hashes: dict) -> None:
		reg = RegistrationStatusChecker(self.__root).status() if None is self.__engine else self.__engine.registration_status()
		if 'identity_init' == self.__stage and (not reg['complete']):
			raise ValueError('Complete native project/folder registration in the current platform/profile first')
		if 'research' == self.__stage and (not QuestionRegistry(self.__root).current(state)):
			raise ValueError('A research question is open or its inputs/results changed')
		if 'analysis' == self.__stage:
			analysis_json = self.__pp.kb_dir / 'Analysis.json'
			Validator.require_current_contract(json.loads(analysis_json.read_text(encoding='utf-8-sig')))
			StageValidityGuard(self.__root, self.__check_project, 'Resolve project/evidence diagnostics before completing analysis').require()
			if self.__pp.rel_to_root(analysis_json) not in out_hashes:
				raise ValueError('Analysis.json must be a declared stage output')
		if 'kb_review' == self.__stage and (not self.__note):
			raise ValueError('Record the result of the semantic KB consistency review')
	# @used-by :meth:`StageCompleter.__apply()`
	def __run_approval_gate(self, state: dict, out_hashes: dict) -> dict | None:
		r = None
		if self.__stage in ('review', 'kb_review'):
			r = ReviewAuthorizer(self.__root, state).authorize() if None is self.__authorize_fn else self.__authorize_fn(self.__root, state)
			StageValidityGuard(self.__root, self.__check_project, 'Current KB/evidence checks failed').require()
		elif 'finalize' == self.__stage:
			StageValidityGuard(self.__root, self.__check_project, 'Current KB/evidence checks failed').require()
			r = FinalizeStageRunner(self.__root, state, out_hashes, self.__outputs, authorize_fn=self.__authorize_fn, drift_fn=self.__drift_fn).run()
		return r
	# @used-by :meth:`StageCompleter.__apply()`
	def __write_stage_receipt(self, state: dict, in_hashes: dict, out_hashes: dict, approval) -> None:
		state['stages'][self.__stage] = {'status': 'complete', 'time': HashCollector.utc_now(), 'inputs': in_hashes, 'outputs': out_hashes, 'note': self.__note}
		if 'finalize' == self.__stage:
			state['stages'][self.__stage]['request_ids'] = [request['id'] for request in state['requests']]
		if 'research' == self.__stage:
			state['stages'][self.__stage]['research_questions'] = deepcopy(state['questions'])
		if self.__stage in ('review', 'kb_review', 'finalize'):
			if None is not self.__engine:
				self.__engine.invalidate_caches()
				kb_h, ev_h = (self.__engine.kb_hashes(), self.__engine.evidence_hashes())
			else:
				kb_h = HashCollector(self.__root, HashCollector.kb_paths(self.__root)).collect()
				ev_h = HashCollector(self.__root, HashCollector.evidence_paths(self.__root)).collect()
			state['stages'][self.__stage]['review_approval'] = approval
			state['stages'][self.__stage]['kb_inputs'] = kb_h
			state['stages'][self.__stage]['evidence_inputs'] = ev_h
		for dependent in STAGES[STAGES.index(self.__stage) + 1:]:
			if dependent in state['stages']:
				state['stages'][dependent].update(status='stale', invalidated_by=self.__stage)
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.complete_stage()`
	# @used-by :meth:`test_df_harness_s11_wave2a_facade_exports.DfHarnessS11Wave2aFacadeExportsTests.test_stage_completer_passes_platform_and_targets_to_registry_register()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	def complete(self) -> dict:
		if self.__stage not in STAGES or not self.__inputs or (not self.__outputs):
			raise ValueError('Known stage and explicit nonempty input/output artifacts required')
		if self.__stage in ('identity_init', 'finalize'):
			reg = RegistrationStatusChecker(self.__root).status() if None is self.__engine else self.__engine.registration_status()
			if reg['required'] and (not reg['all_registered']):
				Registry(self.__root).register(platform=reg['platform'], targets=[reg['platform'], *reg['pending_targets']])
				if None is not self.__engine:
					self.__engine.invalidate_caches()
		in_hashes = HashCollector(self.__root, self.__inputs).collect()
		out_hashes = HashCollector(self.__root, self.__outputs).collect()
		forbidden = {'\ua616/data/workflow.json', '\ua616/data/rendered.json', '\ua616/KB/Progress.md', self.__pp.rel_to_root(self.__pp.workflow_json), self.__pp.rel_to_root(self.__pp.rendered_json), self.__pp.rel_to_root(self.__pp.kb_dir / 'Progress.md')}
		if set((*in_hashes, *out_hashes)) & forbidden:
			raise ValueError('Generated workflow/navigation state cannot serve as its own stage proof')
		upd = (lambda ev, fn: StateUpdater(self.__root, ev, fn, engine=self.__engine).update()) if None is self.__update_fn else (lambda ev, fn: self.__update_fn(self.__root, ev, fn))
		return upd({'action': 'complete_stage', 'stage': self.__stage}, lambda state: self.__apply(state, in_hashes, out_hashes))
