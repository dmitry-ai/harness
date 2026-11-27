# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class StateLoader:
	# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.prepare()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.read_package()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.__authorize_and_select()`
	# @used-by :meth:`Df.Harness.Workflow.RequestAdopter.RequestAdopter.adopt()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.load()`
	# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
	# @used-by :meth:`Df.Harness.Workflow.StatusSnapshotBuilder.StatusSnapshotBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def __init__(self, root) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__root = self.__pp.root
	# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.prepare()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.read_package()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.__authorize_and_select()`
	# @used-by :meth:`Df.Harness.Workflow.RequestAdopter.RequestAdopter.adopt()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.load()`
	# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
	# @used-by :meth:`Df.Harness.Workflow.StatusSnapshotBuilder.StatusSnapshotBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def load(self) -> dict:
		pj = self.__pp.project_json
		if not pj.is_file():
			raise ValueError('Provide the existing project root from this chat; no project is selected or initialized implicitly')
		project = json.loads(pj.read_text(encoding='utf-8'))
		path = self.__pp.workflow_json
		if not path.exists():
			r = {'schema_version': 1, 'project_root': str(self.__root), 'job_id': project['job_id'], 'stages': {}, 'questions': {}, 'reviews': [], 'events': [], 'requests': [], 'legacy': True}
		else:
			from agent_tools.path_registry import same_project_root
			state = json.loads(path.read_text(encoding='utf-8'))
			if 1 != state.get('schema_version') or (not same_project_root(state.get('project_root'), self.__root)) or state.get('job_id') != project['job_id']:
				raise ValueError('Workflow identity/version mismatch; preserve the file for explicit migration')
			r = state
		return r
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	@staticmethod
	def state_path(root) -> Path:
		from agent_tools.path_registry import project_paths
		return project_paths(root, exact_root=True).workflow_json
