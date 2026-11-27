# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Analysis.CardValidationLoader import CardValidationLoader
from Df.Harness.Analysis.EvidenceAuditor import EvidenceAuditor
from Df.Harness.Analysis.Validator import Validator
from Df.Harness.Project.CardSyncAuditor import CardSyncAuditor
from Df.Harness.Project.Diagnostics import Diagnostics
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AnalysisCardAuditor:
	# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.check_project()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def __init__(self, root, path: Path, prevalidated=None, *, analysis_issues_fn=None, evidence_issues_fn=None, drift_fn=None) -> None:
		from agent_tools.path_registry import project_paths
		self.__pp = project_paths(root, exact_root=True)
		self.__root = self.__pp.root
		self.__path = path
		self.__prevalidated = prevalidated
		self.__analysis_issues_fn = (lambda v: Validator(v).issues()) if None is analysis_issues_fn else analysis_issues_fn
		self.__evidence_issues_fn = (lambda r, v, **kw: EvidenceAuditor(r, v, **kw).issues()) if None is evidence_issues_fn else evidence_issues_fn
		self.__drift_fn = drift_fn
	# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.check_project()`
	# @used-by :meth:`test_df_harness_s11_wave2a_workflow.DfHarnessS11Wave2aWorkflowTests.test_workflow_question_registry_and_auditors()`
	def issues(self) -> list[dict]:
		r: list[dict] = []
		analysis_rel = self.__pp.rel_to_root(self.__path)
		if not self.__path.is_file():
			r.append(Diagnostics().problem('analysis.missing', analysis_rel, 'Analysis draft is not saved'))
		else:
			try:
				value, contract_issues, ev_issues = CardValidationLoader(self.__root, self.__path, self.__prevalidated, analysis_issues_fn=self.__analysis_issues_fn, evidence_issues_fn=self.__evidence_issues_fn).load()
				r.extend(contract_issues)
				r.extend(ev_issues)
				if isinstance(value, dict) and value.get('schema_version') in (2, 3) and (not contract_issues):
					r.extend(CardSyncAuditor(self.__pp, value, drift_fn=self.__drift_fn).audit())
			except (OSError, ValueError, TypeError) as exc:
				r.append(Diagnostics().problem('analysis.input', str(self.__path), str(exc)))
		return r
