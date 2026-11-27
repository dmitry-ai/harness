# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Qa.lib.validation.check_strict import df_is_sne
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class FindingValidator:
	# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests._exercise_validator_branches()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_report_validator_classes()`
	def __init__(self, package: dict, expected: set[str]) -> None:
		self.__package = package
		self.__expected = expected
	# @used-by :meth:`FindingValidator.check()`
	def __check_one(self, finding, result, seen: set[str], issues: list[str]) -> None:
		if not isinstance(finding, dict):
			issues.append('Finding must be an object')
		else:
			ident = finding.get('id')
			if not df_is_sne(ident):
				issues.append('Findings need string IDs')
			else:
				if ident in seen:
					issues.append('Findings need unique IDs')
				seen.add(ident)
				self.__check_fields(finding, result, issues)
	# @used-by :meth:`FindingValidator.__check_one()`
	def __check_fields(self, finding: dict, result, issues: list[str]) -> None:
		if finding.get('status') not in ('open', 'resolved', 'rejected'):
			issues.append('Finding status must be open, resolved or rejected')
		if finding.get('severity') not in ('minor', 'significant', 'critical') or (not df_is_sne(finding.get('description'))):
			issues.append('Finding needs severity and description')
		if finding.get('severity') in ('significant', 'critical') and 'approved' == result and ('routine' == self.__package['risk']):
			issues.append('A significant/critical finding cannot approve a routine package; prepare significant review')
		if not isinstance(finding.get('claim_ids'), list) or any((c not in self.__expected for c in finding['claim_ids'])):
			issues.append('Finding claim_ids must refer to response manifest claims')
		if finding.get('status') in ('resolved', 'rejected') and (not df_is_sne(finding.get('disposition')) or not finding.get('evidence')):
			issues.append('Closed finding needs an authored disposition and evidence')
	# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests._exercise_validator_branches()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_report_validator_classes()`
	def check(self, data: dict, issues: list[str]) -> None:
		findings = data.get('findings')
		if not isinstance(findings, list):
			issues.append('Review findings list is required')
		else:
			seen: set[str] = set()
			for finding in findings:
				self.__check_one(finding, data.get('result'), seen, issues)
