# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce single falsifier review default and block duplicate send_message reports":
# https://github.com/dmitry-ai/harness/issues/226
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Include required package keys in REPORT_CONTRACT and resolve record-review paths":
# https://github.com/dmitry-ai/harness/issues/223
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Clarify verbatim target_claim contract and add native-review-proof wait timeout":
# https://github.com/dmitry-ai/harness/issues/212
from __future__ import annotations
TARGET_CLAIM_RULE = 'Copy claims[i].essence verbatim in its original language without translating or paraphrasing (see claim_targets)'
def _nonempty(value) -> bool:
	return isinstance(value, str) and bool(value.strip())
def _package_envelope_issues(data: dict, package: dict) -> list[str]:
	r: list[str] = []
	if not _nonempty(data.get('package')):
		r.append('Review report must identify its immutable package (top-level "package" key is required)')
	if not _nonempty(data.get('package_sha256')):
		r.append('Review report must include top-level "package_sha256" matching the immutable package')
	elif _nonempty(package.get('package_sha256')) and data.get('package_sha256') != package.get('package_sha256'):
		r.append('Review report package_sha256 does not match the immutable package')
	return r
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
def bind_contract_envelope(contract: dict, package_path: str, package_sha: str, review_mode: str | None=None) -> dict:
	r = dict(contract)
	if 'falsifier' == review_mode and isinstance(r.get('falsifier_required_top_level_fields'), list):
		r['required_top_level_fields'] = list(r['falsifier_required_top_level_fields'])
	r['expected_package'] = package_path
	r['expected_package_sha256'] = package_sha
	return r
def build_claim_targets(claims: list | tuple | None) -> dict[str, str]:
	return {c['claim_id']: c['essence'] for c in (claims or ()) if isinstance(c, dict) and _nonempty(c.get('claim_id')) and isinstance(c.get('essence'), str)}
def envelope_issues(data: dict, package: dict, *, review_schema: int, scopes: tuple[str, ...], require_envelope: bool=False) -> list[str]:
	r: list[str] = []
	if review_schema != data.get('schema_version'):
		r.append(f'Review report schema_version {review_schema} is required')
	if data.get('result') not in ('approved', 'needs_changes'):
		r.append('Review result must be approved or needs_changes')
	required_scope = package.get('scope', list(scopes)) if 'client_text' == package.get('kind') else scopes
	if not isinstance(data.get('scope'), list) or not all((_nonempty(x) for x in data['scope'])) or (not set(required_scope).issubset(data['scope'])):
		r.append('Review must cover the required subject scope: ' + ', '.join(required_scope))
	if require_envelope or ('package' in data) or ('package_sha256' in data):
		r.extend(_package_envelope_issues(data, package))
	return r
def resolve_package_review_mode(spec: object, package: dict, evaluator) -> str | None:
	if isinstance(spec, dict) and spec.get('review_mode') in ('standard', 'falsifier'):
		r: str | None = spec['review_mode']
	elif 'significant' == package.get('risk'):
		has_esc = evaluator.significant_findings(package['subject_sha256']) or any(('approved' != item.get('result') for item in evaluator.latest_for_subject(package).values()))
		r = 'standard' if has_esc else 'falsifier'
	else:
		r = None
	return r
