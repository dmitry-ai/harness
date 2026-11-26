# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
_CLAIM_HINTS = {
	'analysis.empty': 'Add at least one claim to the section or record a non-empty explanation under notes.<section>. Run: harness.py schema-help analysis.',
	'argument.competing_reference': 'Remove inline source/quote prose when referencing claim_id or evidence_id. Run: harness.py schema-help analysis.',
	'argument.contradictory_reuse': 'Use a distinct primary counter-evidence item instead of reusing a for evidence_id in against. Run: harness.py schema-help analysis.',
	'argument.dependency': 'Add the referenced claim_id and its current claim_digest sha256 to derived_from. Run: harness.py schema-help analysis.',
	'argument.empty': 'Supply concrete for/against arguments, or document counterevidence (status, reviewed_sources, limitations) when against is empty. Run: harness.py schema-help analysis.',
	'argument.primary': 'Add a matching evidence entry under claim.evidence with id=evidence_id, or cite a derived_from claim_id. Run: harness.py schema-help analysis.',
	'claim.addresses': 'Link causes to concern IDs and methods to concern or cause IDs in addresses. Run: harness.py schema-help analysis.',
	'claim.counterevidence_cap': 'Add counter-evidence to against or set probability_percent <= 75 on unverified hypotheses. Run: harness.py schema-help analysis.',
	'claim.required': 'Populate all required string fields (essence, assessment_basis, and criterion for methods). Run: harness.py schema-help analysis.',
	'claim.scope': 'Set scope to {"description": "...", "sample": ["..."], "limitations": ["..."]} with non-empty strings. Run: harness.py schema-help analysis.',
	'claim.stale_dependency': 'Recompute derived_from[*].sha256 from the current claim_digest of each referenced claim. Run: harness.py schema-help analysis.',
	'documentation.locator': 'Include an #anchor in the documentation URL or add anchor_exception {section, observation}. Run: harness.py schema-help analysis.',
	'evidence.locator': 'Use harness.py source-ref to build an exact json_pointer or text locator for the saved file. Run: harness.py schema-help analysis.',
	'evidence.quote': 'Use a verbatim substring from the saved source (or quote_match: "whitespace" for whitespace runs only). Run: harness.py schema-help analysis.',
	'primary.unconfirmed': 'Back verified claims with saved primary evidence (source, source_sha256, quote, locator). Run: harness.py schema-help analysis.',
}
_CLAIM_PREFIXES = ('analysis.', 'argument.', 'claim.', 'documentation.', 'evidence.', 'fact.', 'hypothesis.', 'method.', 'primary.', 'red_flag', 'source.', 'website')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ClaimHintResolver:
	# @used-by :func:`agent_tools.schema_help.claim_error_hint()`
	# @used-by :meth:`Df.Harness.Project.Diagnostics.Diagnostics.problem()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_schema_help_classes()`
	def __init__(self, code: str) -> None:
		self.__code = str(code or '')
	# @used-by :func:`agent_tools.schema_help.claim_error_hint()`
	# @used-by :meth:`Df.Harness.Project.Diagnostics.Diagnostics.problem()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_schema_help_classes()`
	def resolve(self) -> str | None:
		r = _CLAIM_HINTS.get(self.__code)
		if None is r and self.__code.startswith(_CLAIM_PREFIXES):
			r = 'Run: harness.py schema-help analysis.'
		return r