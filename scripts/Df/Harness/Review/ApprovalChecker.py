# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.sha256 import df_sha256
from agent_tools.research import inside
_REVIEW_SCHEMA = 2
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ApprovalChecker:
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.approval_current()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def __init__(self, root, state: dict, evaluator, approval, *, package_reader=None, inside_fn=None) -> None:
		self.__root = root
		self.__state = state
		self.__evaluator = evaluator
		self.__approval = approval
		self.__package_reader = package_reader
		self.__inside = inside if None is inside_fn else inside_fn
	# @used-by :meth:`ApprovalChecker.__verify_package()`
	def __entry_stale(self, item: dict, latest: dict) -> bool:
		return 'approved' != item.get('result') or latest[item['reviewer_id']].get('id') != item['id'] or (not self.__evaluator.findings_closed(item)) or (not self.__evaluator.entry_proof_current(item))
	# @used-by :meth:`ApprovalChecker.check()`
	def __verify_package(self, package: dict) -> bool:
		r = False
		if df_sha256(self.__inside(self.__root, self.__approval['package']).read_bytes()) == self.__approval['package_sha256']:
			approved = {item['id']: item for item in self.__state['reviews'] if _REVIEW_SCHEMA == item.get('schema_version')}
			selected = [approved[ident] for ident in self.__approval['review_ids']]
			latest = self.__evaluator.latest_for_subject(package)
			if not self.__evaluator.has_unhandled_verdicts(package, latest) and (not any((self.__entry_stale(item, latest) for item in selected))):
				eligible = [item for item in selected if 'routine' == package['risk'] or item.get('independent')]
				r = self.__evaluator.quorum_satisfied(package, latest, eligible)
		return r
	# @used-by :meth:`Df.Harness.Review.QuorumEvaluator.QuorumEvaluator.approval_current()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def check(self) -> bool:
		r = False
		if isinstance(self.__approval, dict) and self.__approval.get('package') and self.__approval.get('review_ids'):
			try:
				if None is self.__package_reader:
					from Df.Harness.Review.PackageReader import PackageReader
					package = PackageReader(self.__root, self.__approval['package'], state=self.__state, inside_fn=self.__inside).read_package()
				else:
					package = self.__package_reader(self.__root, self.__approval['package'], state=self.__state)
				r = self.__verify_package(package)
			except (ValueError, OSError, KeyError, TypeError):
				r = False
		return r
