# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.research import inside
import json
REVIEW_SCHEMA = 2
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class SignificantFindingScanner:
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.significant_findings()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def __init__(self, root, state: dict, evaluator, subject: str) -> None:
		self.__root = root
		self.__state = state
		self.__evaluator = evaluator
		self.__subject = subject
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.significant_findings()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def has_significant(self) -> bool:
		r = False
		for entry in self.__state['reviews']:
			if REVIEW_SCHEMA == entry.get('schema_version') and entry.get('subject_sha256') == self.__subject and self.__evaluator.entry_proof_current(entry):
				report = json.loads(inside(self.__root, entry['report']).read_text(encoding='utf-8'))
				if any((f.get('severity') in ('significant', 'critical') for f in report.get('findings', []))):
					r = True
					break
		return r
