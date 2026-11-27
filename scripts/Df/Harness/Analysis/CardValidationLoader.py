# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class CardValidationLoader:
	# @used-by :func:`agent_tools.evidence_loader.load_analysis_card_validation()`
	# @used-by :meth:`Df.Harness.Workflow.AnalysisCardAuditor.AnalysisCardAuditor.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def __init__(self, root, path: Path, prevalidated, *, analysis_issues_fn, evidence_issues_fn) -> None:
		self.__root = root
		self.__path = path
		self.__prevalidated = prevalidated
		self.__analysis_issues_fn = analysis_issues_fn
		self.__evidence_issues_fn = evidence_issues_fn
	# @used-by :func:`agent_tools.evidence_loader.load_analysis_card_validation()`
	# @used-by :meth:`Df.Harness.Workflow.AnalysisCardAuditor.AnalysisCardAuditor.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def load(self) -> tuple[dict | None, list, list]:
		if None is not self.__prevalidated:
			r = (self.__prevalidated, [], [])
		else:
			value = json.loads(self.__path.read_text(encoding='utf-8-sig'))
			contract = self.__analysis_issues_fn(value)
			ev_issues = self.__evidence_issues_fn(self.__root, value) if isinstance(value, dict) else []
			r = (value, contract, ev_issues)
		return r