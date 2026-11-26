# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Review.ClaimEvidenceCollector import ClaimEvidenceCollector
from Df.Harness.Review.ClaimMerkleHasher import ClaimMerkleHasher
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class MerkleDeltaCalculator:
	# @used-by :func:`agent_tools.review.compute_claim_merkle_delta()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_merkle_and_predicates()`
	def __init__(self, root, manifest: list[dict], value: dict, evidence_inputs: dict | None) -> None:
		self.__root = root
		self.__manifest = manifest
		self.__value = value
		self.__ev_inputs = evidence_inputs or {}
	# @used-by :func:`agent_tools.review.compute_claim_merkle_delta()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_merkle_and_predicates()`
	def compute(self) -> dict:
		index = ClaimEvidenceCollector.claim_index(self.__value)
		cache = self.load_cache(self.__root).get('claims', {})
		cached_ids, unverified_ids, merkle_hashes = ([], [], {})
		for item in self.__manifest:
			ident = item['claim_id']
			m_hash = ClaimMerkleHasher(item, index, self.__ev_inputs).compute_hash()
			merkle_hashes[ident] = m_hash
			entry = cache.get(ident)
			if isinstance(entry, dict) and entry.get('merkle_sha256') == m_hash and entry.get('claim_sha256') == item.get('claim_sha256'):
				cached_ids.append(ident)
			else:
				unverified_ids.append(ident)
		return {'cached_claim_ids': cached_ids, 'unverified_claim_ids': unverified_ids, 'merkle_hashes': merkle_hashes}
	# @used-by :func:`agent_tools.review.load_verified_claims_cache()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.update()`
	# @used-by :meth:`MerkleDeltaCalculator.compute()`
	@staticmethod
	def load_cache(root) -> dict:
		from agent_tools.path_registry import project_paths
		path = project_paths(root, exact_root=True).verified_claims_json
		r = {'version': 1, 'claims': {}}
		if path.is_file():
			try:
				data = json.loads(path.read_text(encoding='utf-8'))
				if isinstance(data, dict) and isinstance(data.get('claims'), dict):
					r = data
			except (OSError, ValueError):
				pass
		return r
