# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Project.Diagnostics import Diagnostics
from Df.Harness.Workflow.AnalysisCardAuditor import AnalysisCardAuditor
from Df.Harness.Workflow.AttachmentAuditor import AttachmentAuditor
from Df.Harness.Workflow.KbAuditor import KbAuditor
_SCRIPT_EXTS = ('.py', '.ps1', '.sh', '.bat', '.cmd')
_DOC_EXTS = ('.md', '.markdown', '.txt', '.html', '.htm')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class HealthAuditor:
	# @used-by :func:`agent_tools.workflow.attachment_issues()`
	# @used-by :func:`agent_tools.workflow.check_project()`
	# @used-by :func:`agent_tools.workflow.kb_issues()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__check_prereqs()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__init__()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def __init__(self, root, *, analysis_issues_fn=None, evidence_issues_fn=None, drift_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.pp = project_paths(root, exact_root=True)
		self.root = self.pp.root
		self.__analysis_issues_fn = analysis_issues_fn
		self.__evidence_issues_fn = evidence_issues_fn
		self.__drift_fn = drift_fn
	# @used-by :meth:`HealthAuditor.check_project()`
	def __check_deliverable_links(self, issues: list[dict]) -> None:
		from agent_tools.links import readable_link_issues
		d_dirs = list(dict.fromkeys((d.resolve() for d in (self.pp.path('proposals_dir', self.root / 'result'), self.pp.path('letters_dir', self.root / 'Letters'), self.pp.path('articles_dir', self.root / '\u2c0f/\u227b/\u2655/\U0001f582/Articles'), self.root / 'result') if d.is_dir())))
		overview = self.pp.path('overview_md', self.root / '.md')
		docs = list({p.resolve(): p for d in d_dirs for p in sorted(d.rglob('*'))}.values())
		for document in [overview, *docs]:
			if document.is_file() and 'draft.prev.md' != document.name and ('.md' == document.name or document.suffix.lower() in _DOC_EXTS):
				for error in readable_link_issues(document.read_text(encoding='utf-8')):
					issues.append(Diagnostics().problem('document.link_style', self.pp.rel_to_root(document), error, file=document))
	# @used-by :meth:`HealthAuditor.check_project()`
	def __check_one_off_scripts(self, issues: list[dict]) -> None:
		from agent_tools.runtime import PRIMARY
		folders = [self.pp.data_dir]
		if self.pp.agents_config_dir.resolve() != Path(PRIMARY).resolve():
			folders.append(self.pp.agents_config_dir)
		elif (self.root / '.agents').is_dir():
			folders.append(self.root / '.agents')
		for folder in folders:
			if folder.is_dir():
				for script in sorted(folder.rglob('*')):
					if script.is_file() and script.suffix.lower() in _SCRIPT_EXTS:
						issues.append(Diagnostics().problem('project.one_off_script', self.pp.rel_to_root(script), 'Executable one-off scripts are prohibited in project directories (FILE-5/EXEC-1); use shared upwork_project.py commands', file=script))
	# @used-by :func:`agent_tools.workflow.attachment_issues()`
	# @used-by :meth:`HealthAuditor.check_project()`
	# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_workflow_classes_and_shared_attachment_inventory()`
	def attachment_issues(self) -> list[dict]:
		return AttachmentAuditor(self.root).issues()
	# @used-by :func:`agent_tools.workflow.check_project()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__check_prereqs()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def check_project(self, *, prevalidated_analysis=None) -> dict:
		from agent_tools.journal_integrity import finalize_project_check
		issues = self.kb_issues() + self.attachment_issues()
		self.__check_one_off_scripts(issues)
		self.__check_deliverable_links(issues)
		path = self.pp.kb_dir / 'Analysis.json'
		issues.extend(AnalysisCardAuditor(self.root, path, prevalidated=prevalidated_analysis, analysis_issues_fn=self.__analysis_issues_fn, evidence_issues_fn=self.__evidence_issues_fn, drift_fn=self.__drift_fn).issues())
		return finalize_project_check(self.pp, issues, path)
	# @used-by :func:`agent_tools.workflow.kb_issues()`
	# @used-by :meth:`HealthAuditor.check_project()`
	def kb_issues(self) -> list[dict]:
		return KbAuditor(self.root).issues()
