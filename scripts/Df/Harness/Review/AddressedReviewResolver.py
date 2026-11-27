# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Qa.lib.validation.check_strict import df_is_sne
from agent_tools.research import inside
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AddressedReviewResolver:
	# @used-by :func:`agent_tools.review.resolve_addressed_reviews()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests._exercise_validator_branches()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def __init__(self, root, data: dict, package: dict, independent: bool, existing_reviews: list[dict]) -> None:
		self.__root = root
		self.__data = data
		self.__package = package
		self.__independent = independent
		self.__existing = existing_reviews
	# @used-by :meth:`AddressedReviewResolver.resolve_addressed()`
	def __resolve_one(self, resolution, prior_by_id: dict) -> tuple[str, list[str]]:
		prior = prior_by_id.get(resolution.get('review_id')) if isinstance(resolution, dict) and df_is_sne(resolution.get('review_id')) else None
		if not prior or prior.get('subject_sha256') != self.__package['subject_sha256'] or (not df_is_sne(resolution.get('basis'))) or (not isinstance(resolution.get('evidence'), list)) or (not resolution['evidence']):
			raise ValueError('Authored review resolution needs same-subject prior verdict, basis and saved evidence')
		return (prior['id'], [inside(self.__root, item).relative_to(self.__root).as_posix() for item in resolution['evidence']])
	# @used-by :func:`agent_tools.review.resolve_addressed_reviews()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests._exercise_validator_branches()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def resolve_addressed(self) -> tuple[list[str], list[str]]:
		addresses = self.__data.get('addresses_reviews', [])
		if not isinstance(addresses, list):
			raise ValueError('addresses_reviews must be an authored list of previous verdict resolutions')
		addressed, extra_proofs = ([], [])
		if addresses:
			if not self.__independent or 'approved' != self.__data.get('result'):
				raise ValueError('Only a new independent authored approval can address another reviewer verdict')
			prior_by_id = {item.get('id'): item for item in self.__existing}
			for resolution in addresses:
				pid, proofs = self.__resolve_one(resolution, prior_by_id)
				addressed.append(pid)
				extra_proofs.extend(proofs)
			if len(set(addressed)) != len(addressed):
				raise ValueError('Duplicate addressed review verdict')
		return (addressed, extra_proofs)
