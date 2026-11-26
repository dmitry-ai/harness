# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Analysis.Claim.ClosureCollector import ClosureCollector
from Df.Qa.lib.validation.check_strict import df_is_sne
import hashlib
import json
_SECTIONS = ('facts', 'claims', 'identity', 'concerns', 'misconceptions', 'causes', 'methods')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ClaimEvidenceCollector:
	# @used-by :func:`agent_tools.review._claim_evidence_pairs()`
	# @used-by :meth:`Df.Harness.Review.ApprovedDigestCollector.ApprovedDigestCollector.__add_claims()`
	# @used-by :meth:`Df.Harness.Review.BlindPredicateBuilder.BlindPredicateBuilder.build()`
	# @used-by :meth:`Df.Harness.Review.ClaimMerkleHasher.ClaimMerkleHasher.compute_hash()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.update()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_merkle_and_predicates()`
	def __init__(self, claim_id: str, index: dict, evidence_inputs: dict | None=None, visited: set | None=None) -> None:
		self.__claim_id = claim_id
		self.__index = index
		self.__ev_map = evidence_inputs if isinstance(evidence_inputs, dict) else {}
		self.__visited = set() if None is visited else visited
	# @used-by :meth:`ClaimEvidenceCollector.pairs()`
	def __collect_claim(self, claim: dict, out: dict[str, str]) -> None:
		for ref in list(claim.get('evidence') or []) + list(claim.get('primary_evidence') or []):
			if isinstance(ref, dict):
				for key in ('source', 'observation', 'manifest'):
					val = ref.get(key)
					if df_is_sne(val):
						src = val.strip()
						sha = self.__ev_map.get(src) or (str(ref.get('source_sha256') or '') if 'source' == key else '')
						if src not in out or (not out[src] and sha):
							out[src] = sha
	# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.__check_omitted()`
	# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.__resolve_claim()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__check_claims()`
	@staticmethod
	def claim_digest(claim: dict) -> str:
		return hashlib.sha256(json.dumps(claim, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
	# @used-by :meth:`Df.Harness.Review.ApprovedDigestCollector.ApprovedDigestCollector.__load_index()`
	# @used-by :meth:`Df.Harness.Review.BlindPredicateBuilder.BlindPredicateBuilder.build()`
	# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.classify()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.update()`
	# @used-by :meth:`Df.Harness.Review.MerkleDeltaCalculator.MerkleDeltaCalculator.compute()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__check_claims()`
	@staticmethod
	def claim_index(value) -> dict:
		r: dict = {}
		if isinstance(value, dict):
			for sec in _SECTIONS:
				items = value.get(sec)
				if isinstance(items, list):
					for item in items:
						if isinstance(item, dict) and df_is_sne(item.get('id')):
							r[item['id']] = item
		return r
	# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.classify()`
	@staticmethod
	def section_map(value) -> dict[str, str]:
		r: dict[str, str] = {}
		if isinstance(value, dict):
			for sec in _SECTIONS:
				items = value.get(sec)
				if isinstance(items, list):
					for item in items:
						if isinstance(item, dict) and df_is_sne(item.get('id')):
							r[item['id']] = sec
		return r
	# @used-by :func:`agent_tools.review._claim_evidence_pairs()`
	# @used-by :meth:`Df.Harness.Review.ApprovedDigestCollector.ApprovedDigestCollector.__add_claims()`
	# @used-by :meth:`Df.Harness.Review.BlindPredicateBuilder.BlindPredicateBuilder.build()`
	# @used-by :meth:`Df.Harness.Review.ClaimMerkleHasher.ClaimMerkleHasher.compute_hash()`
	# @used-by :meth:`Df.Harness.Review.MerkleCacheUpdater.MerkleCacheUpdater.update()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_merkle_and_predicates()`
	def pairs(self) -> list[tuple[str, str]]:
		if not df_is_sne(self.__claim_id) or self.__claim_id in self.__visited:
			r: list[tuple[str, str]] = []
		else:
			out: dict[str, str] = {}
			for cid in ClosureCollector([self.__claim_id], self.__index).collect():
				if cid not in self.__visited:
					self.__collect_claim(self.__index.get(cid) or {}, out)
			r = sorted(out.items())
		return r
