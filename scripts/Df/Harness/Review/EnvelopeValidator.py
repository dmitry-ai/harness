# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Qa.lib.validation.check_strict import df_is_sne
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class EnvelopeValidator:
	# @used-by :func:`agent_tools.review_alignment.envelope_issues()`
	# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
	def __init__(self, data: dict, package: dict, *, review_schema: int, scopes: tuple[str, ...], require_envelope: bool=False) -> None:
		self.__data = data
		self.__package = package
		self.__schema = review_schema
		self.__scopes = scopes
		self.__require_env = require_envelope
	# @used-by :meth:`EnvelopeValidator.issues()`
	def __package_issues(self) -> list[str]:
		r: list[str] = []
		if not df_is_sne(self.__data.get('package')):
			r.append('Review report must identify its immutable package (top-level "package" key is required)')
		if not df_is_sne(self.__data.get('package_sha256')):
			r.append('Review report must include top-level "package_sha256" matching the immutable package')
		elif df_is_sne(self.__package.get('package_sha256')) and self.__data.get('package_sha256') != self.__package.get('package_sha256'):
			r.append('Review report package_sha256 does not match the immutable package')
		return r
	# @used-by :func:`agent_tools.review_alignment.envelope_issues()`
	# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_alignment_and_classifier_classes()`
	def issues(self) -> list[str]:
		r: list[str] = []
		if self.__schema != self.__data.get('schema_version'):
			r.append(f'Review report schema_version {self.__schema} is required')
		if self.__data.get('result') not in ('approved', 'needs_changes'):
			r.append('Review result must be approved or needs_changes')
		req_scope = self.__package.get('scope', list(self.__scopes)) if 'client_text' == self.__package.get('kind') else self.__scopes
		if not isinstance(self.__data.get('scope'), list) or not all((df_is_sne(x) for x in self.__data['scope'])) or (not set(req_scope).issubset(self.__data['scope'])):
			r.append('Review must cover the required subject scope: ' + ', '.join(req_scope))
		if self.__require_env or ('package' in self.__data) or ('package_sha256' in self.__data):
			r.extend(self.__package_issues())
		return r
