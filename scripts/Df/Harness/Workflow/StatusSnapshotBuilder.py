# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Workflow.HashCollector import HashCollector
from Df.Harness.Workflow.RegistrationStatusChecker import RegistrationStatusChecker
from Df.Harness.Workflow.StageStatusEvaluator import STAGES, StageStatusEvaluator
from Df.Harness.Workflow.StateLoader import StateLoader
from agent_tools.research import inside
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class StatusSnapshotBuilder:
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.status()`
	# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def __init__(self, root, *, state=None, statuses=None, kb_hashes_fn=None, reg_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__root = self.__pp.root
		self.__state = state
		self.__statuses = statuses
		self.__kb_hashes_fn = kb_hashes_fn
		self.__reg_fn = reg_fn
	# @used-by :meth:`StatusSnapshotBuilder.build()`
	def __proposals(self) -> list[dict]:
		prop_dirs = list(dict.fromkeys((d.resolve() for d in (self.__pp.path('proposals_dir', self.__root / 'result'), self.__root / 'result') if d.is_dir() and d.resolve().is_relative_to(self.__root))))
		prop_files = list({p.resolve(): p for d in prop_dirs for p in sorted(d.rglob('*.md'))}.values())
		return [{'path': inside(self.__root, path).relative_to(self.__root).as_posix(), 'sha256': HashCollector.file_hash(inside(self.__root, path))} for path in prop_files if path.is_file() and path.name in ('draft.md', 'final.md', 'draft.prev.md')]
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.status()`
	# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def build(self) -> dict:
		state = StateLoader(self.__root).load() if None is self.__state else self.__state
		statuses = StageStatusEvaluator(self.__root, state).evaluate() if None is self.__statuses else self.__statuses
		existing = {name: (self.__pp.kb_dir / name).is_file() for name in ('Analysis.json', 'Analysis.md', 'Progress.md')}
		kb_hashes = HashCollector(self.__root, HashCollector.kb_paths(self.__root)).collect() if None is self.__kb_hashes_fn else self.__kb_hashes_fn()
		reg = RegistrationStatusChecker(self.__root).status() if None is self.__reg_fn else self.__reg_fn()
		checkpoint = self.__pp.continuation_md
		return {'project': str(self.__root), 'job_id': state['job_id'], 'legacy': state['legacy'], 'stages': statuses, 'scope': 'initial_analysis', 'proposal_artifacts': self.__proposals(), 'continuation': {'file': self.__pp.rel_to_root(checkpoint), 'exists': checkpoint.is_file()}, 'next_stage': next((s for s in STAGES if 'complete' != statuses[s]), None), 'agent_kb': str(self.__pp.kb_dir), 'existing_drafts': existing, 'kb_hashes': kb_hashes, 'questions': list(state['questions'].values()), 'registration': reg, 'detail': 'Stages track saved analysis. Every new analytical reply requires current request/answer-bound approval. Continue the same filesystem project in either UI using agent KB, journal and actual proposal files; Context.md is an external export.'}
