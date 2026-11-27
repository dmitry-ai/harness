# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.Diagnostics import Diagnostics
from Df.Harness.Workflow.HashCollector import HashCollector
from agent_tools.research import inside
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class KbAuditor:
	# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.kb_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def __init__(self, root) -> None:
		from agent_tools.path_registry import project_paths
		self.__root = project_paths(root, exact_root=True).root
	# @used-by :func:`agent_tools.workflow.doc4_sentence_issues()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__validate_response()`
	# @used-by :meth:`KbAuditor.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	@staticmethod
	def doc4_sentence_issues(text: str) -> list[str]:
		from agent_tools.hook_runtime import scan_doc4_sentence_issues
		return scan_doc4_sentence_issues(text, mode='workflow')
	# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.kb_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests._exercise_stage_completer_and_auditors()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def issues(self) -> list[dict]:
		from agent_tools.links import validate_file
		r: list[dict] = []
		for relative in HashCollector.kb_paths(self.__root):
			file = inside(self.__root, relative)
			if '.md' != file.suffix.lower() and '.md' != file.name:
				continue
			for error in validate_file(file, local_anchors=True, readable_links=True):
				r.append(Diagnostics().problem('kb.link', relative, error, file=file))
			text = file.read_text(encoding='utf-8')
			if re.search('(?im)^\\s*\\|.*\\|\\s*$\\n\\s*\\|?\\s*:?-{3,}', text) or re.search('(?i)<a\\s+[^>]*(?:name|id)\\s*=', text):
				r.append(Diagnostics().problem('kb.format', relative, 'Markdown tables or HTML anchors conflict with DOC-4/LINK-4', file=file))
			if 'Analysis.md' != file.name:
				for doc4_err in self.doc4_sentence_issues(text):
					r.append(Diagnostics().problem('kb.doc4_sentence', relative, doc4_err, file=file))
		return r
