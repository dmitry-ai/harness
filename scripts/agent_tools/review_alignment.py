# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Review.AlignmentValidator import AlignmentValidator, TARGET_CLAIM_RULE
from Df.Harness.Review.ClaimTargetBuilder import ClaimTargetBuilder
from Df.Harness.Review.ContractBinder import ContractBinder
from Df.Harness.Review.EnvelopeValidator import EnvelopeValidator
from Df.Harness.Review.ReviewModeResolver import ReviewModeResolver
from Df.Qa.lib.validation.check_strict import df_is_sne
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
# @used-by :mod:`agent_tools.review_alignment`
def _nonempty(value) -> bool:
	return df_is_sne(value)
# @used-by :mod:`agent_tools.review_alignment`
def alignment_issues(ident: str, alignment, expected_target: str | None) -> list[str]:
	return AlignmentValidator(ident, alignment, expected_target).issues()
# @used-by :mod:`agent_tools.review_alignment`
def bind_contract_envelope(contract: dict, package_path: str, package_sha: str, review_mode: str | None=None) -> dict:
	return ContractBinder(contract, package_path, package_sha, review_mode).bind()
# @used-by :mod:`agent_tools.review_alignment`
def build_claim_targets(claims: list | tuple | None) -> dict[str, str]:
	return ClaimTargetBuilder(claims).build()
# @used-by :mod:`agent_tools.review_alignment`
def envelope_issues(data: dict, package: dict, *, review_schema: int, scopes: tuple[str, ...], require_envelope: bool=False) -> list[str]:
	return EnvelopeValidator(data, package, review_schema=review_schema, scopes=scopes, require_envelope=require_envelope).issues()
# @used-by :mod:`agent_tools.review_alignment`
def resolve_package_review_mode(spec: object, package: dict, evaluator) -> str | None:
	return ReviewModeResolver(spec, package, evaluator).resolve()
__all__ = ['TARGET_CLAIM_RULE', '_nonempty', 'alignment_issues', 'bind_contract_envelope', 'build_claim_targets', 'envelope_issues', 'resolve_package_review_mode']
