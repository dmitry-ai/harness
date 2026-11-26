# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Review.ClaimEvidenceCollector import ClaimEvidenceCollector
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class BlindPredicateBuilder:
	# @used-by :func:`agent_tools.review.build_blind_verification_predicates()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_merkle_and_predicates()`
	def __init__(self, manifest: list[dict], value: dict) -> None:
		self.__manifest = manifest
		self.__value = value
	# @used-by :func:`agent_tools.review.build_blind_verification_predicates()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_merkle_and_predicates()`
	def build(self) -> list[dict]:
		index = ClaimEvidenceCollector.claim_index(self.__value)
		r: list[dict] = []
		for item in self.__manifest:
			ident = item['claim_id']
			raw_ess = str(item.get('essence') or '')
			clean = re.sub('(?:\\s*\\(\\d{1,3}%\\)|\\s+with\\s+\\d{1,3}%\\s+(?:confidence|probability|plausibility|score)|\\s*[—–-]\\s*\\d{1,3}%)', '', raw_ess, flags=re.I).strip()
			sources = [s for s, _ in ClaimEvidenceCollector(ident, index, {}).pairs()]
			r.append({'claim_id': ident, 'knowledge_type': item.get('knowledge_type'), 'atomic_predicate': clean, 'primary_sources': sources, 'question': f'Does the Tier 0 primary evidence directly entail or falsify the atomic statement for {ident}: "{clean}"?'})
		return r
