# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Workflow.HashCollector import HashCollector
from Df.Harness.lib.project import dfh_resolve_overview_md
from agent_tools.research import inside
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ReceiptVerifier:
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.entry_proof_current()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.current()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.receipt_current()`
	# @used-by :meth:`Df.Harness.Workflow.StageStatusEvaluator.StageStatusEvaluator.__stage_current()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_receipt_verifier_and_dir_resolver_support_dot_md_and_readme_bidirectional()`
	def __init__(self, root, receipt: dict, *, kb_hashes_fn=None, ev_hashes_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__root = self.__pp.root
		self.__receipt = receipt
		self.__kb_hashes_fn = kb_hashes_fn
		self.__ev_hashes_fn = ev_hashes_fn
	# @used-by :meth:`ReceiptVerifier.is_current()`
	def __resolve_artifact(self, path: str) -> Path:
		target = inside(self.__root, path)
		r = target
		if not target.is_file():
			from agent_tools.journal import resolve_migrated_step_file
			cand = resolve_migrated_step_file(target)
			if cand.is_file() and cand.is_relative_to(self.__root):
				r = cand
			else:
				# 2026-11-28 "Use .md root card via v2_upwork profile": https://github.com/dmitry-ai/harness/issues/415
				v2_cand = {'\ua66e/0/Context.md': self.__pp.context_output, 'KB/Project.md': self.__pp.manual_kb_dir / 'Project.md', '.md': self.__root / 'readme.md', 'readme.md': dfh_resolve_overview_md(self.__pp)}.get(Path(path).as_posix())
				if None is not v2_cand and v2_cand.is_file() and v2_cand.is_relative_to(self.__root):
					r = v2_cand
		return r
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.entry_proof_current()`
	# @used-by :meth:`Df.Harness.Workflow.QuestionRegistry.QuestionRegistry.current()`
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.receipt_current()`
	# @used-by :meth:`Df.Harness.Workflow.StageStatusEvaluator.StageStatusEvaluator.__stage_current()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	# @used-by :meth:`test_upwork_v2_root_card.UpworkV2RootCardTests.test_receipt_verifier_and_dir_resolver_support_dot_md_and_readme_bidirectional()`
	def is_current(self) -> bool:
		kb_fn = self.__kb_hashes_fn or (lambda: HashCollector(self.__root, HashCollector.kb_paths(self.__root)).collect())
		ev_fn = self.__ev_hashes_fn or (lambda: HashCollector(self.__root, HashCollector.evidence_paths(self.__root)).collect())
		files_ok = all(((t := self.__resolve_artifact(path)).is_file() and HashCollector.file_hash(t) == digest for group in ('inputs', 'outputs') for path, digest in self.__receipt.get(group, {}).items()))
		return files_ok and ('kb_inputs' not in self.__receipt or self.__receipt['kb_inputs'] == kb_fn()) and ('evidence_inputs' not in self.__receipt or self.__receipt['evidence_inputs'] == ev_fn())
