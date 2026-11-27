# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Workflow.HashCollector import HashCollector
from Df.Harness.Workflow.ProgressPublisher import ProgressPublisher
from Df.Harness.Workflow.StageStatusEvaluator import StageStatusEvaluator
from Df.Harness.Workflow.StateLoader import StateLoader
from Df.Harness.Workflow.StatusSnapshotBuilder import StatusSnapshotBuilder
from agent_tools.research import json_data
from agent_tools.storage import locked, replace_bytes
import uuid
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class StateUpdater:
	# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.record()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionAdder.QuestionAdder.add()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionClaimer.QuestionClaimer.claim()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionFinisher.QuestionFinisher.finish()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionHandoff.QuestionHandoff.handoff()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionSearchRecorder.QuestionSearchRecorder.record()`
	# @used-by :meth:`Df.Harness.Workflow.RequestAdopter.RequestAdopter.adopt()`
	# @used-by :meth:`Df.Harness.Workflow.RequestUnadopter.RequestUnadopter.unadopt()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.complete()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.update()`
	# @used-by :meth:`Df.Harness.Workflow.WorkflowResumer.WorkflowResumer.resume()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def __init__(self, root, event: dict, change, *, engine=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__root = self.__pp.root
		self.__event = event
		self.__change = change
		self.__engine = engine
	# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.record()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionAdder.QuestionAdder.add()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionClaimer.QuestionClaimer.claim()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionFinisher.QuestionFinisher.finish()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionHandoff.QuestionHandoff.handoff()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionSearchRecorder.QuestionSearchRecorder.record()`
	# @used-by :meth:`Df.Harness.Workflow.RequestAdopter.RequestAdopter.adopt()`
	# @used-by :meth:`Df.Harness.Workflow.RequestUnadopter.RequestUnadopter.unadopt()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.complete()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.update()`
	# @used-by :meth:`Df.Harness.Workflow.WorkflowResumer.WorkflowResumer.resume()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def update(self) -> dict:
		with locked(self.__pp.data_dir / 'workflow.lock'):
			state = StateLoader(self.__root).load() if None is self.__engine else self.__engine.load()
			state['project_root'] = str(self.__root)
			self.__change(state)
			state['events'].append({'id': uuid.uuid4().hex, 'time': HashCollector.utc_now(), **self.__event})
			replace_bytes(self.__pp.workflow_json, json_data(state))
			if None is not self.__engine:
				self.__engine.invalidate_caches()
				statuses = self.__engine.stage_statuses(state)
				progress = self.__engine.publish_progress(state, statuses=statuses)
				snap = self.__engine.status(state=state, statuses=statuses)
			else:
				statuses = StageStatusEvaluator(self.__root, state).evaluate()
				progress = ProgressPublisher(self.__root, state, statuses=statuses).publish()
				snap = StatusSnapshotBuilder(self.__root, state=state, statuses=statuses).build()
		return {'workflow': str(self.__pp.workflow_json), 'progress': progress, **snap}
