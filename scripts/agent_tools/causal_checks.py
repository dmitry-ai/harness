# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Grounding.ProbabilityClaimChecker import ProbabilityClaimChecker
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :func:`Df.Harness.lib.completion_commands._validate_prepare_response()`
# @used-by :meth:`Df.Harness.Project.FactualNoteValidator.FactualNoteValidator.issues()`
# @used-by :meth:`test_turn_completion.CausalBasisTests.test_observed_ignorance_to_equal_probability_error_is_rejected()`
# @used-by :meth:`test_turn_completion.CausalBasisTests.test_quotes_code_negation_and_explicit_symmetric_prior_are_allowed()`
def unsupported_probability_claims(text):
	return ProbabilityClaimChecker(text).check()