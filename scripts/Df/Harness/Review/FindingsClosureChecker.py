# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.research import inside
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class FindingsClosureChecker:
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.findings_closed()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def __init__(self, root, evaluator, entry: dict) -> None:
		self.__root = root
		self.__evaluator = evaluator
		self.__entry = entry
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.findings_closed()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpSession.CdpSession.close()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def closed(self) -> bool:
		data = json.loads(inside(self.__root, self.__entry['report']).read_text(encoding='utf-8'))
		statuses = {f['id']: f.get('status') for f in data['findings']}
		ok = True
		for item in self.__entry.get('dispositions', []):
			if not self.__evaluator.entry_proof_current({'proof': item['proof']}):
				ok = False
				break
			saved = json.loads(inside(self.__root, item['file']).read_text(encoding='utf-8'))
			statuses[saved['finding_id']] = saved['status']
		return ok and all((status in ('resolved', 'rejected') for status in statuses.values()))
