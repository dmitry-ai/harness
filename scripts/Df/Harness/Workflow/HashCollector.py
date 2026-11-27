# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from agent_tools.research import inside
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class HashCollector:
	# @used-by :func:`agent_tools.workflow.hashes()`
	# @used-by :meth:`Df.Harness.Review.ApprovedDigestCollector.ApprovedDigestCollector.digests()`
	# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__validate_current()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionAdder.QuestionAdder.add()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionFinisher.QuestionFinisher.__apply()`
	# @used-by :meth:`Df.Harness.Workflow.ReceiptVerifier.ReceiptVerifier.is_current()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__write_stage_receipt()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.complete()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.evidence_hashes()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.kb_hashes()`
	# @used-by :meth:`Df.Harness.Workflow.StatusSnapshotBuilder.StatusSnapshotBuilder.build()`
	# @used-by :meth:`Df.Harness.Workflow.WorkflowResumer.WorkflowResumer.__apply()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def __init__(self, root, paths) -> None:
		self.__root = Path(root).resolve()
		self.__paths = paths
	# @used-by :func:`agent_tools.workflow.hashes()`
	# @used-by :meth:`Df.Harness.Review.ApprovedDigestCollector.ApprovedDigestCollector.digests()`
	# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__validate_current()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionAdder.QuestionAdder.add()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionFinisher.QuestionFinisher.__apply()`
	# @used-by :meth:`Df.Harness.Workflow.ReceiptVerifier.ReceiptVerifier.is_current()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__write_stage_receipt()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.complete()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.evidence_hashes()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.kb_hashes()`
	# @used-by :meth:`Df.Harness.Workflow.StatusSnapshotBuilder.StatusSnapshotBuilder.build()`
	# @used-by :meth:`Df.Harness.Workflow.WorkflowResumer.WorkflowResumer.__apply()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def collect(self) -> dict[str, str]:
		r: dict[str, str] = {}
		for path in self.__paths:
			target = inside(self.__root, path)
			if not target.is_file():
				raise FileNotFoundError(f'Missing stage artifact: {path}')
			r[target.relative_to(self.__root).as_posix()] = self.file_hash(target)
		return r
	# @used-by :func:`agent_tools.workflow.evidence_paths()`
	# @used-by :meth:`Df.Harness.Review.ApprovedDigestCollector.ApprovedDigestCollector.digests()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__validate_current()`
	# @used-by :meth:`Df.Harness.Workflow.ReceiptVerifier.ReceiptVerifier.is_current()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__write_stage_receipt()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.evidence_hashes()`
	@staticmethod
	def evidence_paths(root) -> list[str]:
		from agent_tools.path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		resolved = pp.root
		evidence = pp.evidence_dir
		dirs = [d for d in (evidence, pp.manual_kb_dir, pp.source_dir) if d.is_dir() and d.resolve().is_relative_to(resolved)]
		return sorted({p.relative_to(resolved).as_posix() for directory in dirs for p in directory.rglob('*') if p.is_file() and (not p.is_relative_to(evidence / 'Reviews'))})
	# @used-by :func:`agent_tools.workflow.file_hash()`
	# @used-by :meth:`Df.Harness.Review.InputReceiptBuilder.InputReceiptBuilder.build()`
	# @used-by :meth:`Df.Harness.Workflow.ReceiptVerifier.ReceiptVerifier.is_current()`
	# @used-by :meth:`Df.Harness.Workflow.StatusSnapshotBuilder.StatusSnapshotBuilder.__proposals()`
	# @used-by :meth:`Df.Harness.Workflow.WorkflowResumer.WorkflowResumer.__apply()`
	# @used-by :meth:`HashCollector.collect()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	@staticmethod
	def file_hash(path) -> str:
		return df_sha256(Path(path).read_bytes())
	# @used-by :func:`agent_tools.workflow.kb_paths()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__validate_current()`
	# @used-by :meth:`Df.Harness.Workflow.KbAuditor.KbAuditor.issues()`
	# @used-by :meth:`Df.Harness.Workflow.ReceiptVerifier.ReceiptVerifier.is_current()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__write_stage_receipt()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.kb_hashes()`
	# @used-by :meth:`Df.Harness.Workflow.StatusSnapshotBuilder.StatusSnapshotBuilder.build()`
	@staticmethod
	def kb_paths(root) -> list[str]:
		from agent_tools.path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		kb = pp.kb_dir
		ev = pp.evidence_dir
		if not kb.is_dir():
			r: list[str] = []
		else:
			r = [p.relative_to(pp.root).as_posix() for p in sorted(kb.rglob('*')) if p.is_file() and (p.suffix.lower() in ('.md', '.json') or '.md' == p.name) and ('Progress.md' != p.name) and (not p.is_relative_to(ev))]
		return r
	# @used-by :func:`agent_tools.workflow.now()`
	# @used-by :meth:`Df.Harness.Review.DispositionRecorder.DispositionRecorder.record()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionAdder.QuestionAdder.__apply()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionSearchRecorder.QuestionSearchRecorder.__apply()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__write_stage_receipt()`
	# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
	# @used-by :meth:`Df.Harness.Workflow.WorkflowResumer.WorkflowResumer.__apply()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	@staticmethod
	def utc_now() -> str:
		return datetime.now(timezone.utc).isoformat(timespec='seconds')
