# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Review.ClaimEvidenceCollector import ClaimEvidenceCollector
from agent_tools.research import json_data
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ClaimMerkleHasher:
	# @used-by :func:`agent_tools.review.claim_merkle_hash()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.update()`
	# @used-by :meth:`Df.Harness.Review.MerkleDeltaCalculator.MerkleDeltaCalculator.compute()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_merkle_and_predicates()`
	def __init__(self, claim_entry: dict, index: dict, evidence_inputs: dict | None) -> None:
		self.__entry = claim_entry
		self.__index = index
		self.__ev_inputs = evidence_inputs or {}
	# @used-by :func:`agent_tools.review.claim_merkle_hash()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.update()`
	# @used-by :meth:`Df.Harness.Review.MerkleDeltaCalculator.MerkleDeltaCalculator.compute()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_merkle_and_predicates()`
	def compute_hash(self) -> str:
		ident = self.__entry.get('claim_id', '')
		claim_obj = self.__index.get(ident) or {}
		ev_pairs = ClaimEvidenceCollector(ident, self.__index, self.__ev_inputs).pairs()
		norm_excerpt = ' '.join(str(self.__entry.get('response_excerpt', '')).split())
		payload = json_data({
			'claim_id': ident,
			'claim_sha256': self.__entry.get('claim_sha256', ''),
			'knowledge_type': self.__entry.get('knowledge_type') or claim_obj.get('knowledge_type') or '',
			'verification_status': self.__entry.get('verification_status') or claim_obj.get('verification_status') or '',
			'response_excerpt': norm_excerpt,
			'evidence_hashes': ev_pairs,
		})
		return df_sha256(payload)
