# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Clarify verbatim target_claim contract and add native-review-proof wait timeout":
# https://github.com/dmitry-ai/harness/issues/212
from __future__ import annotations
TARGET_CLAIM_RULE = 'Copy claims[i].essence verbatim in its original language without translating or paraphrasing (see claim_targets)'
def _nonempty(value) -> bool:
	return isinstance(value, str) and bool(value.strip())
def alignment_issues(ident: str, alignment, expected_target: str | None) -> list[str]:
	issues: list[str] = []
	if not isinstance(alignment, dict):
		issues.append(f'{ident}: test_alignment must be an object binding target_claim, tested_claim, relationship, rationale and a concrete counterexample')
	else:
		actual_target = alignment.get('target_claim')
		if actual_target != expected_target:
			issues.append(f'{ident}: test_alignment.target_claim mismatch (copy claims[i].essence verbatim without translation): expected {expected_target!r}, got {actual_target!r}')
		missing = [k for k in ('tested_claim', 'rationale', 'counterexample') if not _nonempty(alignment.get(k))]
		if missing:
			issues.append(f"{ident}: test_alignment missing nonempty field(s): {', '.join(missing)}")
		rel = alignment.get('relationship')
		if rel not in ('direct', 'proxy', 'irrelevant'):
			issues.append(f'{ident}: test_alignment.relationship must be direct, proxy or irrelevant, got {rel!r}')
	return issues
def build_claim_targets(claims: list | tuple | None) -> dict[str, str]:
	return {c['claim_id']: c['essence'] for c in (claims or ()) if isinstance(c, dict) and _nonempty(c.get('claim_id')) and isinstance(c.get('essence'), str)}
