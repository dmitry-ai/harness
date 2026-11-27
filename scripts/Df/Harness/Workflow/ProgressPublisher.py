# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Analysis.OwnedPublisher import OwnedPublisher
from Df.Harness.Workflow.StageStatusEvaluator import STAGES, StageStatusEvaluator
from agent_tools.research import inside
import os
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ProgressPublisher:
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.publish_progress()`
	# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def __init__(self, root, state: dict, *, statuses=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__root = self.__pp.root
		self.__state = state
		self.__statuses = statuses
	# @used-by :meth:`ProgressPublisher.publish()`
	def __question_lines(self, markdown_link) -> list[str]:
		lines = ['', '## Questions']
		for question in self.__state['questions'].values():
			lines += [f"- {question['id']}: {question['question']}", f"  Status: {question['status']}; owner: {question.get('owner') or 'unassigned'}.", f"  Completion criterion: {question['done_when']}."]
			if question.get('gap'):
				lines.append('  Gap: ' + question['gap'])
			for ref in question.get('results', {}):
				relative = Path(os.path.relpath(inside(self.__root, ref), self.__pp.kb_dir)).as_posix()
				lines.append('  ' + markdown_link('Saved result', relative))
		return lines
	# @used-by :meth:`Df.Harness.Workflow.StageEngine.StageEngine.publish_progress()`
	# @used-by :meth:`Df.Harness.Workflow.StateUpdater.StateUpdater.update()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_stage_engine_and_helpers()`
	def publish(self) -> dict:
		from agent_tools.links import markdown_link
		resolved = StageStatusEvaluator(self.__root, self.__state).evaluate() if None is self.__statuses else self.__statuses
		lines = ['# Analysis Progress', '', 'Service navigation for the agent KB; statuses do not prove the truth of conclusions.', f"Job: {self.__state['job_id']}.", '', '## Stages']
		lines += [f'- {stage}: {resolved[stage]}.' for stage in STAGES if 'finalize' != stage]
		lines += ['Verify completion and external export receipt with the status command.', '']
		if self.__pp.continuation_md.is_file():
			cont_rel = Path(os.path.relpath(self.__pp.continuation_md, self.__pp.kb_dir)).as_posix()
			lines += [f"Current post-analysis instruction: {markdown_link('continuation state', cont_rel)}.", '']
		lines += self.__question_lines(markdown_link)
		lines += ['', '## Topical Modules']
		lines += ['- ' + markdown_link(p.name, p.name) for p in sorted(self.__pp.kb_dir.glob('*.md')) if 'Progress.md' != p.name]
		lines += ['', 'Before new research, check the overview and topical KB modules.', 'Corrections propagate to linked claims and documents; anything unverified is marked explicitly.', 'Context.md is intended for handoff to an external agent, not for internal work.', '']
		return OwnedPublisher(self.__pp.kb_dir / 'Progress.md', '\n'.join(lines), source=self.__pp.workflow_json, history=False).publish()
