# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Qa.lib.validation.check_strict import df_is_sne
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class FalsifierValidator:
	# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_report_validator_classes()`
	def __init__(self, package: dict, expected: set[str], pkg_root: Path | None) -> None:
		self.__package = package
		self.__expected = expected
		self.__pkg_root = pkg_root
	# @used-by :meth:`FalsifierValidator.__check_disproved()`
	def __check_tier0_source(self, cid_val, src_str: str, quote_str, issues: list[str]) -> None:
		from agent_tools.source_grounding import classify_provenance_tier, norm_quote_text, quote_segments_present
		src_cand = Path(src_str)
		if None is not self.__pkg_root and (not src_cand.is_absolute()):
			src_cand = (self.__pkg_root / src_cand).resolve()
		if 'tier_0' != classify_provenance_tier(src_cand, self.__pkg_root):
			issues.append(f"disproved_claims[{cid_val or '?'}]: contradicting_tier0_source ({src_str}) must be a Tier 0 primary source")
		elif src_cand.is_file() and df_is_sne(quote_str):
			try:
				raw_src = src_cand.read_text(encoding='utf-8', errors='replace')
				if not quote_segments_present(quote_str, norm_quote_text(raw_src), 8):
					issues.append(f"disproved_claims[{cid_val or '?'}]: verbatim_quote_from_source is absent from Tier 0 source {src_str}")
			except OSError:
				pass
	# @used-by :meth:`FalsifierValidator.check()`
	def __check_disproved(self, dc: dict, issues: list[str]) -> None:
		cid_val = dc.get('claim_id')
		if cid_val not in self.__expected:
			issues.append('Each disproved_claims entry must reference a valid response claim_id')
		for req_field in ('excerpt_from_answer', 'contradicting_tier0_source', 'verbatim_quote_from_source', 'falsification_reason'):
			if not df_is_sne(dc.get(req_field)):
				issues.append(f"disproved_claims[{cid_val or '?'}]: {req_field} is required")
		src_str = dc.get('contradicting_tier0_source')
		if df_is_sne(src_str):
			self.__check_tier0_source(cid_val, src_str, dc.get('verbatim_quote_from_source'), issues)
	# @used-by :meth:`Df.Harness.Review.ReportValidator.ReportValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_review_report_validator_classes()`
	def check(self, data: dict, issues: list[str]) -> None:
		disproved = data.get('disproved_claims')
		if not isinstance(disproved, list):
			issues.append('Adversarial falsifier report requires a disproved_claims list')
		else:
			for dc in disproved:
				if not isinstance(dc, dict):
					issues.append('Each disproved_claims entry must be an object')
				else:
					self.__check_disproved(dc, issues)
			if disproved and 'approved' == data.get('result'):
				issues.append('Adversarial falsifier report with non-empty disproved_claims requires needs_changes')
			if not disproved and 'needs_changes' == data.get('result') and (not data.get('findings')):
				issues.append('Adversarial falsifier needs_changes verdict requires at least one disproved_claims entry or open finding')
