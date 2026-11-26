# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Analysis.Claim.SourceNumericTokenizer import SourceNumericTokenizer
from Df.Harness.Analysis.Claim.StandaloneNumberExtractor import StandaloneNumberExtractor
from Df.Harness.Review.AlignmentValidator import AlignmentValidator
from Df.Qa.lib.validation.check_strict import df_is_sne
_FIELDS = ('observed', 'inferred', 'method', 'alternatives', 'limits', 'falsification', 'raw_vs_criteria')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ClaimReviewValidator:
	# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_report_validator_classes()`
	def __init__(self, package: dict, expected: set, package_claims: dict, targets: dict, candidate) -> None:
		self.__package = package
		self.__expected = expected
		self.__package_claims = package_claims
		self.__targets = targets
		self.__candidate = candidate
	# @used-by :meth:`ClaimReviewValidator.__check_item()`
	def __check_alignment(self, ident: str, item: dict, issues: list[str]):
		alignment = item.get('test_alignment')
		if (align_errs := AlignmentValidator(ident, alignment, self.__targets.get(ident)).issues()):
			issues.extend(align_errs)
		elif 'proxy' == alignment['relationship'] and 'supported' == item.get('outcome'):
			issues.append(f'{ident}: a proxy test cannot support the broader target; qualify the claim and show the limitation in the response')
		elif 'irrelevant' == alignment['relationship'] and 'unsupported' != item.get('outcome'):
			issues.append(f'{ident}: an irrelevant test must leave the target unsupported')
		return alignment
	# @used-by :meth:`ClaimReviewValidator.check()`
	def __check_item(self, item, result, covered: set[str], issues: list[str]) -> None:
		if not isinstance(item, dict):
			issues.append('Claim review must be an object')
		elif not df_is_sne(item.get('claim_id')):
			issues.append('Claim review needs a string claim_id')
		else:
			ident = item['claim_id']
			if ident not in self.__expected or ident in covered:
				issues.append('Claim review must cover each response claim exactly once')
			covered.add(ident)
			for field in _FIELDS:
				if not df_is_sne(item.get(field)):
					issues.append(f'{ident}: review {field} must explain the evidence assessment')
			alignment = self.__check_alignment(ident, item, issues)
			self.__check_outcome(ident, item, result, issues)
			self.__check_numeric_grounding(ident, item, alignment, issues)
	# @used-by :meth:`ClaimReviewValidator.__check_item()`
	def __check_numeric_grounding(self, ident: str, item: dict, alignment, issues: list[str]) -> None:
		if ident in self.__package_claims and 'supported' == item.get('outcome') and (not item.get('preflight_numeric_grounded')):
			pkg_claim = self.__package_claims[ident]
			claim_nums = StandaloneNumberExtractor(str(pkg_claim.get('essence', '')) + '\n' + str(pkg_claim.get('response_excerpt', ''))).extract()
			if claim_nums:
				corpus = str(item.get('observed', '')) + '\n' + str((alignment or {}).get('tested_claim', ''))
				missing = sorted(claim_nums - SourceNumericTokenizer(corpus).tokenize())
				if missing:
					issues.append(f'{ident}: claim/response numeric figures {missing} are not confirmed in reviewer observed/tested_claim')
	# @used-by :meth:`ClaimReviewValidator.__check_item()`
	def __check_outcome(self, ident: str, item: dict, result, issues: list[str]) -> None:
		outcome = item.get('outcome')
		if outcome not in ('supported', 'qualified', 'unsupported'):
			issues.append(f'{ident}: unsupported review outcome')
		if 'unsupported' == outcome and 'approved' == result:
			issues.append(f'{ident}: an unsupported claim requires needs_changes')
		if 'qualified' == outcome:
			self.__check_qualified(ident, item, issues)
	# @used-by :meth:`ClaimReviewValidator.__check_outcome()`
	def __check_qualified(self, ident: str, item: dict, issues: list[str]) -> None:
		excerpt = item.get('response_qualification')
		if not df_is_sne(excerpt):
			issues.append(f'{ident}: qualified claim needs an exact response_qualification excerpt')
		elif None is not self.__candidate and excerpt not in self.__candidate:
			issues.append('Claim qualification must occur verbatim in the exact response')
	# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_report_validator_classes()`
	def check(self, data: dict, issues: list[str]) -> None:
		if not isinstance(data.get('claim_reviews'), list):
			issues.append('Per-claim review coverage is required')
		else:
			covered: set[str] = set()
			for item in data['claim_reviews']:
				self.__check_item(item, data.get('result'), covered, issues)
			unverified = set((self.__package.get('merkle_delta') or {}).get('unverified_claim_ids') or [])
			if covered != self.__expected and (not (data.get('use_merkle_delta') and covered == unverified)):
				issues.append('Every response claim requires an authored evidence assessment')
