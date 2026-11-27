# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Workflow.AnswerRecorder import AnswerRecorder
from Df.Harness.Workflow.HashCollector import HashCollector
from Df.Harness.Workflow.ProgressPublisher import ProgressPublisher
from Df.Harness.Workflow.ReceiptVerifier import ReceiptVerifier
from Df.Harness.Workflow.RegistrationStatusChecker import RegistrationStatusChecker
from Df.Harness.Workflow.RequestAdopter import RequestAdopter
from Df.Harness.Workflow.RequestUnadopter import RequestUnadopter
from Df.Harness.Workflow.StageCompleter import StageCompleter
from Df.Harness.Workflow.StageStatusEvaluator import StageStatusEvaluator
from Df.Harness.Workflow.StateLoader import StateLoader
from Df.Harness.Workflow.StateUpdater import StateUpdater
from Df.Harness.Workflow.StatusSnapshotBuilder import StatusSnapshotBuilder
from Df.Harness.Workflow.WorkflowResumer import WorkflowResumer
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class StageEngine:
	# @used-by :func:`agent_tools.workflow.adopt_requests()`
	# @used-by :func:`agent_tools.workflow.complete_stage()`
	# @used-by :func:`agent_tools.workflow.load()`
	# @used-by :func:`agent_tools.workflow.publish_progress()`
	# @used-by :func:`agent_tools.workflow.receipt_current()`
	# @used-by :func:`agent_tools.workflow.record_current_answer()`
	# @used-by :func:`agent_tools.workflow.registration_status()`
	# @used-by :func:`agent_tools.workflow.resume()`
	# @used-by :func:`agent_tools.workflow.stage_statuses()`
	# @used-by :func:`agent_tools.workflow.state_path()`
	# @used-by :func:`agent_tools.workflow.status()`
	# @used-by :func:`agent_tools.workflow.unadopt_requests()`
	# @used-by :func:`agent_tools.workflow.update()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_remaining_branches()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage()`
	def __init__(self, root, *, update_fn=None, check_project_fn=None, authorize_fn=None, drift_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.pp = project_paths(root, exact_root=True)
		self.root = self.pp.root
		self._evidence_cache = None
		self._kb_cache = None
		self._reg_cache = None
		self.__update_fn = update_fn
		self.__check_project_fn = check_project_fn
		self.__authorize_fn = authorize_fn
		self.__drift_fn = drift_fn
	# @used-by :func:`agent_tools.workflow.adopt_requests()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	def adopt_requests(self, conversation_id: str, *, allow_finalized: bool=False, backend=None, platform=None) -> dict:
		return RequestAdopter(self.root, conversation_id, allow_finalized=allow_finalized, backend=backend, platform=platform, engine=self, update_fn=self.__update_fn).adopt()
	# @used-by :func:`agent_tools.workflow.complete_stage()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	def complete_stage(self, stage: str, inputs: list, outputs: list, *, note=None) -> dict:
		return StageCompleter(self.root, stage, inputs, outputs, note=note, engine=self, check_project_fn=self.__check_project_fn, authorize_fn=self.__authorize_fn, drift_fn=self.__drift_fn, update_fn=self.__update_fn).complete()
	# @used-by :meth:`StageEngine.receipt_current()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	def evidence_hashes(self) -> dict[str, str]:
		if None is self._evidence_cache:
			self._evidence_cache = HashCollector(self.root, HashCollector.evidence_paths(self.root)).collect()
		return self._evidence_cache
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	def invalidate_caches(self) -> None:
		self._evidence_cache = None
		self._kb_cache = None
		self._reg_cache = None
	# @used-by :meth:`StageEngine.receipt_current()`
	# @used-by :meth:`StageEngine.status()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	def kb_hashes(self) -> dict[str, str]:
		if None is self._kb_cache:
			self._kb_cache = HashCollector(self.root, HashCollector.kb_paths(self.root)).collect()
		return self._kb_cache
	# @used-by :func:`agent_tools.workflow.load()`
	# @used-by :meth:`StageEngine.status()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def load(self) -> dict:
		return StateLoader(self.root).load()
	# @used-by :func:`agent_tools.workflow.publish_progress()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	def publish_progress(self, state: dict, *, statuses=None) -> dict:
		resolved = self.stage_statuses(state) if None is statuses else statuses
		return ProgressPublisher(self.root, state, statuses=resolved).publish()
	# @used-by :func:`agent_tools.workflow.receipt_current()`
	# @used-by :meth:`StageEngine.stage_statuses()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage()`
	def receipt_current(self, receipt: dict) -> bool:
		return ReceiptVerifier(self.root, receipt, kb_hashes_fn=self.kb_hashes, ev_hashes_fn=self.evidence_hashes).is_current()
	# @used-by :func:`agent_tools.workflow.record_current_answer()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	def record_current_answer(self, response: str, *, journal_directory=None, request_ids=None, preauthorized=None, recorded_steps=None, turn_token=None) -> dict:
		return AnswerRecorder(self.root, response, journal_directory=journal_directory, request_ids=request_ids, preauthorized=preauthorized, recorded_steps=recorded_steps, turn_token=turn_token, engine=self, authorize_fn=self.__authorize_fn, update_fn=self.__update_fn).record()
	# @used-by :func:`agent_tools.workflow.registration_status()`
	# @used-by :meth:`StageEngine.stage_statuses()`
	# @used-by :meth:`StageEngine.status()`
	def registration_status(self) -> dict:
		if None is self._reg_cache:
			self._reg_cache = RegistrationStatusChecker(self.root).status()
		return self._reg_cache
	# @used-by :func:`agent_tools.workflow.resume()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	def resume(self, reason: str, request=None) -> dict:
		return WorkflowResumer(self.root, reason, request=request, engine=self, update_fn=self.__update_fn).resume()
	# @used-by :func:`agent_tools.workflow.stage_statuses()`
	# @used-by :meth:`StageEngine.publish_progress()`
	# @used-by :meth:`StageEngine.status()`
	def stage_statuses(self, state: dict) -> dict[str, str]:
		return StageStatusEvaluator(self.root, state, receipt_fn=self.receipt_current, reg_fn=self.registration_status).evaluate()
	# @used-by :func:`agent_tools.workflow.state_path()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	def state_path(self) -> Path:
		return self.pp.workflow_json
	# @used-by :func:`agent_tools.workflow.status()`
	def status(self, *, state=None, statuses=None) -> dict:
		resolved_state = self.load() if None is state else state
		resolved_statuses = self.stage_statuses(resolved_state) if None is statuses else statuses
		return StatusSnapshotBuilder(self.root, state=resolved_state, statuses=resolved_statuses, kb_hashes_fn=self.kb_hashes, reg_fn=self.registration_status).build()
	# @used-by :func:`agent_tools.workflow.unadopt_requests()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_adopt_answer_complete_and_finalize()`
	def unadopt_requests(self, conversation_id=None, request_ids=None) -> dict:
		return RequestUnadopter(self.root, conversation_id=conversation_id, request_ids=request_ids, engine=self, update_fn=self.__update_fn).unadopt()
	# @used-by :func:`agent_tools.workflow.update()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_z_workflow_remaining_branches()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
	def update(self, event: dict, change) -> dict:
		return StateUpdater(self.root, event, change, engine=self).update()
