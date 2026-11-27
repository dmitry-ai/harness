# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Review.ClaimEvidenceCollector import ClaimEvidenceCollector
from Df.Harness.Review.PackageEnvelopeReader import PackageEnvelopeReader
from agent_tools.research import inside
import json
_REVIEW_SCHEMA = 2
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ApprovedDigestCollector:
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.approved_claim_digests()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def __init__(self, root, state: dict, evaluator, *, exclude_package=None, analysis_fn=None) -> None:
		self.__root = root
		self.__state = state
		self.__evaluator = evaluator
		self.__exclude_package = exclude_package
		self.__analysis_fn = analysis_fn
	# @used-by :meth:`ApprovedDigestCollector.__process_group()`
	def __add_claims(self, package: dict, cur_ev: dict, ev_exact: bool, index: dict, out: set) -> None:
		if ev_exact:
			out.update(((c['claim_id'], c['claim_sha256']) for c in package['claims']))
		else:
			pkg_ev = package.get('evidence_inputs') or {}
			for claim in package['claims']:
				cid = claim['claim_id']
				pairs = ClaimEvidenceCollector(cid, index, pkg_ev).pairs()
				if all((cur_ev.get(src) == sha for src, sha in pairs if sha)):
					out.add((cid, claim['claim_sha256']))
	# @used-by :meth:`ApprovedDigestCollector.digests()`
	def __collect_groups(self) -> dict:
		groups: dict = {}
		for entry in self.__state['reviews']:
			if self.__is_approved_entry(entry):
				pkg_rel = entry['package']
				if pkg_rel not in groups:
					groups[pkg_rel] = (json.loads(inside(self.__root, pkg_rel).read_text(encoding='utf-8')), [])
				groups[pkg_rel][1].append(entry)
		return groups
	# @used-by :meth:`ApprovedDigestCollector.__collect_groups()`
	def __is_approved_entry(self, entry: dict) -> bool:
		ok = _REVIEW_SCHEMA == entry.get('schema_version') and 'approved' == entry.get('result') and bool(entry.get('independent'))
		return ok and entry.get('package') != self.__exclude_package and self.__evaluator.entry_proof_current(entry) and self.__evaluator.findings_closed(entry)
	# @used-by :meth:`ApprovedDigestCollector.digests()`
	def __load_index(self, is_finalized: bool) -> dict:
		r: dict = {}
		if is_finalized:
			fn = PackageEnvelopeReader.load_analysis if None is self.__analysis_fn else self.__analysis_fn
			try:
				r = ClaimEvidenceCollector.claim_index(fn(self.__root))
			except (OSError, ValueError):
				r = {}
		return r
	# @used-by :meth:`ApprovedDigestCollector.digests()`
	def __process_group(self, package: dict, matching: list[dict], cur_ev: dict, is_finalized: bool, index: dict, out: set) -> None:
		ev_exact = (package.get('evidence_inputs') or {}) == cur_ev
		if ev_exact or is_finalized:
			latest = self.__evaluator.latest_for_subject(package)
			if not self.__evaluator.has_unhandled_verdicts(package, latest):
				eligible = [item for item in matching if latest.get(item['reviewer_id'], {}).get('id') == item['id']]
				if self.__evaluator.quorum_satisfied(package, latest, eligible):
					self.__add_claims(package, cur_ev, ev_exact, index, out)
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.approved_claim_digests()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def digests(self) -> set:
		from Df.Harness.Workflow.HashCollector import HashCollector
		r: set = set()
		is_finalized = 'complete' == self.__state.get('stages', {}).get('finalize', {}).get('status')
		cur_ev = HashCollector(self.__root, HashCollector.evidence_paths(self.__root)).collect()
		index = self.__load_index(is_finalized)
		for package, matching in self.__collect_groups().values():
			self.__process_group(package, matching, cur_ev, is_finalized, index, r)
		return r
