# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Review.ApprovalChecker import ApprovalChecker
from Df.Harness.Review.ApprovedDigestCollector import ApprovedDigestCollector
from Df.Harness.Review.AuthorizedGroupSelector import AuthorizedGroupSelector
from Df.Harness.Review.FindingsClosureChecker import FindingsClosureChecker
from Df.Harness.Review.QuorumChecker import QuorumChecker
from Df.Harness.Review.SignificantFindingScanner import SignificantFindingScanner
from Df.Harness.Review.UnhandledVerdictChecker import UnhandledVerdictChecker
_REVIEW_SCHEMA = 2
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class QuorumEvaluator:
	# @used-by :func:`agent_tools.review._approved_digests()`
	# @used-by :func:`agent_tools.review.approval_current()`
	# @used-by :func:`agent_tools.review.findings_closed()`
	# @used-by :func:`agent_tools.review.has_unhandled_verdicts()`
	# @used-by :func:`agent_tools.review.latest_for_subject()`
	# @used-by :func:`agent_tools.review.quorum_satisfied()`
	# @used-by :func:`agent_tools.review.significant_findings()`
	# @used-by :func:`agent_tools.text_review.authorize()`
	# @used-by :func:`agent_tools.text_review.prepare()`
	# @used-by :func:`agent_tools.text_review.read_package()`
	# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.classify()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__validate_current()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.authorize()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_quorum_evaluator_selects_authorized_group_and_checks_approval_current()`
	def __init__(self, root, state: dict, *, analysis_fn=None, package_reader=None, inside_fn=None) -> None:
		self.root = Path(root).resolve()
		self.state = state
		self.__analysis_fn = analysis_fn
		self.__package_reader = package_reader
		self.__inside_fn = inside_fn
	# @used-by :func:`agent_tools.review.approval_current()`
	# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_quorum_evaluator_selects_authorized_group_and_checks_approval_current()`
	def approval_current(self, approval, *, package_reader=None) -> bool:
		reader = self.__package_reader if None is package_reader else package_reader
		return ApprovalChecker(self.root, self.state, self, approval, package_reader=reader, inside_fn=self.__inside_fn).check()
	# @used-by :func:`agent_tools.review._approved_digests()`
	# @used-by :meth:`Df.Harness.Review.Classifier.Classifier.classify()`
	def approved_claim_digests(self, *, exclude_package=None) -> set:
		return ApprovedDigestCollector(self.root, self.state, self, exclude_package=exclude_package, analysis_fn=self.__analysis_fn).digests()
	# @used-by :func:`agent_tools.text_review.authorize()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__validate_entry()`
	def entry_proof_current(self, entry: dict) -> bool:
		from agent_tools.workflow import receipt_current
		return receipt_current(self.root, {'inputs': entry.get('proof', {})})
	# @used-by :func:`agent_tools.review.findings_closed()`
	# @used-by :func:`agent_tools.text_review.authorize()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__validate_entry()`
	def findings_closed(self, entry: dict) -> bool:
		return FindingsClosureChecker(self.root, self, entry).closed()
	# @used-by :func:`agent_tools.review.has_unhandled_verdicts()`
	def has_unhandled_verdicts(self, package: dict, latest=None) -> bool:
		return UnhandledVerdictChecker(self.state, self, package, latest).has_unhandled()
	# @used-by :func:`agent_tools.review.latest_for_subject()`
	def latest_for_subject(self, package: dict) -> dict:
		r: dict = {}
		for entry in self.state['reviews']:
			if _REVIEW_SCHEMA == entry.get('schema_version') and entry.get('subject_sha256') == package['subject_sha256']:
				r[entry['reviewer_id']] = entry
		return r
	# @used-by :func:`agent_tools.review.quorum_satisfied()`
	def quorum_satisfied(self, package: dict, latest: dict, eligible: list[dict], *, allow_falsifier_or_cached: bool=True) -> bool:
		return QuorumChecker(self, package, latest, eligible, allow_falsifier_or_cached=allow_falsifier_or_cached).satisfied()
	# @used-by :func:`agent_tools.text_review.authorize()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.authorize()`
	# @used-by :meth:`test_review_contract.ReviewDecompositionTests.test_quorum_evaluator_selects_authorized_group_and_checks_approval_current()`
	def select_authorized_group(self, groups: dict, *, allow_routine_self: bool=True, allow_falsifier_or_cached: bool=True):
		return AuthorizedGroupSelector(self, groups, allow_routine_self=allow_routine_self, allow_falsifier_or_cached=allow_falsifier_or_cached).select()
	# @used-by :func:`agent_tools.review.significant_findings()`
	# @used-by :func:`agent_tools.text_review.prepare()`
	# @used-by :func:`agent_tools.text_review.read_package()`
	# @used-by :meth:`Df.Harness.Review.PackagePreparer.PackagePreparer.__build_data()`
	# @used-by :meth:`Df.Harness.Review.PackageReader.PackageReader.__validate_current()`
	def significant_findings(self, subject: str) -> bool:
		return SignificantFindingScanner(self.root, self.state, self, subject).has_significant()
