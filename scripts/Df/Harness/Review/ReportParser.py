# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ReportParser:
	# @used-by :func:`agent_tools.review.parse_report_object()`
	# @used-by :meth:`Df.Harness.Review.ReportAuthenticator.ReportAuthenticator.__auth_independent()`
	# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__load_and_check()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def __init__(self, text: str) -> None:
		self.__text = text
	# @used-by :func:`agent_tools.review.parse_report_object()`
	# @used-by :meth:`Df.Harness.Review.ReportAuthenticator.ReportAuthenticator.__auth_independent()`
	# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__load_and_check()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_quorum_and_authorizer_classes()`
	def parse(self) -> dict:
		value = self.__text.strip()
		if value.startswith('```'):
			match = re.fullmatch('```(?:json)?\\s*\\n(.*?)\\n```', value, re.S)
			if not match:
				raise ValueError('Reviewer final output must be one JSON report, optionally one fenced JSON block')
			value = match.group(1)
		try:
			result = json.loads(value)
		except ValueError as exc:
			raise ValueError('Reviewer authored final output is not a JSON report') from exc
		if not isinstance(result, dict):
			raise ValueError('Reviewer report must be a JSON object')
		return result
