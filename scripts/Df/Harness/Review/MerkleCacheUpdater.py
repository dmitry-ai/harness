# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Analysis.EvidenceAuditor import EvidenceAuditor
from Df.Harness.Analysis.Validator import Validator
from Df.Harness.Review.ClaimEvidenceCollector import ClaimEvidenceCollector
from Df.Harness.Review.ClaimMerkleHasher import ClaimMerkleHasher
from Df.Harness.Review.MerkleDeltaCalculator import MerkleDeltaCalculator
from Df.Qa.lib.validation.check_strict import df_is_sne
from agent_tools.research import json_data
from agent_tools.storage import replace_bytes
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class MerkleCacheUpdater:
	# @used-by :func:`agent_tools.review.update_verified_claims_cache()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.authorize()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests._exercise_review_record_and_auth()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_merkle_and_predicates()`
	def __init__(self, root, package: dict, value: dict | None=None, *, analysis_fn=None) -> None:
		self.__root = Path(root).resolve()
		self.__package = package
		self.__value = value
		self.__analysis_fn = analysis_fn
	# @used-by :meth:`MerkleCacheUpdater.__load_value()`
	def __default_analysis(self) -> dict:
		from agent_tools.path_registry import project_paths
		path = project_paths(self.__root, exact_root=True).kb_dir / 'Analysis.json'
		val = json.loads(path.read_text(encoding='utf-8-sig'))
		if not isinstance(val, dict) or 3 != val.get('schema_version'):
			raise ValueError('New review and publication require Analysis schema 3; legacy files remain readable')
		if Validator(val).issues() or EvidenceAuditor(self.__root, val, skip_structural=True).issues():
			raise ValueError('Resolve Analysis schema 3 and evidence diagnostics before preparing or accepting review')
		return val
	# @used-by :meth:`MerkleCacheUpdater.update()`
	def __load_value(self) -> dict:
		if None is not self.__value:
			r = self.__value
		else:
			fn = self.__default_analysis if None is self.__analysis_fn else (lambda: self.__analysis_fn(self.__root))
			try:
				r = fn()
			except (OSError, ValueError):
				r = {}
		return r
	# @used-by :func:`agent_tools.review.update_verified_claims_cache()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.authorize()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests._exercise_review_record_and_auth()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_merkle_and_predicates()`
	def update(self) -> dict:
		from agent_tools.path_registry import project_paths
		index = ClaimEvidenceCollector.claim_index(self.__load_value())
		ev_inputs = self.__package.get('evidence_inputs') or {}
		r = MerkleDeltaCalculator.load_cache(self.__root)
		claims_map = r.setdefault('claims', {})
		for item in self.__package.get('claims') or []:
			if isinstance(item, dict) and df_is_sne(item.get('claim_id')):
				ident = item['claim_id']
				c_obj = index.get(ident) or {}
				m_hash = (self.__package.get('merkle_delta') or {}).get('merkle_hashes', {}).get(ident) or ClaimMerkleHasher(item, index, ev_inputs).compute_hash()
				claims_map[ident] = {'claim_id': ident, 'claim_sha256': item.get('claim_sha256', ''), 'knowledge_type': item.get('knowledge_type') or c_obj.get('knowledge_type') or '', 'verification_status': item.get('verification_status') or c_obj.get('verification_status') or '', 'tier0_evidence_hashes': dict(ClaimEvidenceCollector(ident, index, ev_inputs).pairs()), 'merkle_sha256': m_hash, 'response_sha256': (self.__package.get('response') or {}).get('sha256', '')}
		pp = project_paths(self.__root, exact_root=True)
		if pp.verified_claims_json.parent.is_dir() or pp.agent_dir.is_dir():
			replace_bytes(pp.verified_claims_json, json_data(r))
		return r
