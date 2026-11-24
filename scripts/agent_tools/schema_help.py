# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add schema-help CLI, validator hints, save-analysis --merge, and af-worker file handoff":
# https://github.com/dmitry-ai/harness/issues/217
from __future__ import annotations
import json
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
_EXPERIMENT_HINT = 'Hint: run "harness.py schema-help experiment" for required fields, valid property/method pairs, and assertion locators.'
_REVIEW_HINT = 'Hint: run "harness.py schema-help review" for review_mode (falsifier vs standard), claim_targets, and schema_version 2 fields.'
def _analysis_payload() -> dict:
	from .claims import KINDS, PROPERTIES, SECTIONS, STATUSES
	return {
		'valid': True,
		'topic': 'analysis',
		'schema_version': 3,
		'commands': ['harness.py save-analysis <project> --candidate <file> [--merge] [--partial] [--expected-sha256 <sha>]', 'harness.py validate-analysis <project>/\ua616/KB/Analysis.json --format json --evidence', 'harness.py render-analysis <project>/\ua616/KB/Analysis.json'],
		'required_fields': {'top_level': ['schema_version', 'facts', *SECTIONS, 'notes', 'websites', 'red_flags'], 'claim': ['id', 'essence', 'assessment_basis', 'knowledge_type', 'verification_status', 'scope', 'properties', 'derived_from', 'evidence', 'missing_checks', 'materiality', 'novelty', 'category', 'impact'], 'stage_claim_extra': ['for', 'against', 'counterevidence (when against is empty)', 'probability_percent (or score_percent + criterion + applicability + validation for methods)', 'addresses (required for causes/methods)', 'alternative_explanations + discriminating_check (for causes/misconceptions)']},
		'enums': {'knowledge_type': sorted(KINDS), 'verification_status': sorted(STATUSES), 'properties': sorted(PROPERTIES), 'materiality': ['routine', 'significant'], 'novelty': ['new', 'restatement'], 'category': ['architecture', 'causal', 'descriptive', 'interaction', 'pricing']},
		'common_pitfalls': ['Never put inline source/quote inside for/against when referencing claim_id or evidence_id.', 'Unverified hypotheses with empty against cannot exceed probability_percent 75.', 'Use save-analysis --merge --partial to validate and stage sections incrementally into \ua616/data/analysis-draft.json.'],
		'minimal_example': {'schema_version': 3, 'facts': [], 'identity': [{'id': 'F-ID', 'essence': 'Verbatim intake fact.', 'assessment_basis': 'Saved intake.', 'knowledge_type': 'client_report', 'verification_status': 'verified', 'scope': {'description': 'Intake only.', 'sample': ['Evidence/intake.json'], 'limitations': ['No admin access.']}, 'properties': ['content'], 'derived_from': [], 'evidence': [{'id': 'E-1', 'kind': 'intake', 'source': 'Evidence/intake.json', 'manifest': 'Evidence/intake.json', 'source_sha256': '<64-hex>', 'quote': 'Verbatim intake fact.', 'locator': {'type': 'json_pointer', 'value': '/title'}}], 'missing_checks': [], 'materiality': 'routine', 'novelty': 'new', 'category': 'descriptive', 'impact': {'severity': 'unknown', 'basis': 'Not measured.', 'evidence_claim_ids': []}, 'probability_percent': 100, 'addresses': [], 'for': [{'argument': 'Exact quote.', 'evidence_id': 'E-1'}], 'against': [], 'counterevidence': {'status': 'not_found', 'reviewed_sources': ['Evidence/intake.json'], 'limitations': 'Intake only.'}}], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': [], 'notes': {'concerns': 'Explain empty section.'}, 'websites': [{'role': 'client', 'url': None, 'basis_id': 'F-ID'}], 'red_flags': []},
	}
def _check_one_assertion(label: str, item, seen_ids: set[str], operators: tuple[str, ...], issues: list[str]) -> None:
	if not isinstance(item, dict):
		issues.append(label + ': deterministic assertion object required')
	else:
		aid = item.get('id')
		if not isinstance(aid, str) or not aid.strip() or aid in seen_ids:
			issues.append(label + ': assertion needs a unique id')
		if isinstance(aid, str):
			seen_ids.add(aid)
		has_id = isinstance(item.get('artifact_id'), str) and bool(item['artifact_id'].strip())
		has_role = isinstance(item.get('artifact_role'), str) and bool(item['artifact_role'].strip())
		if has_id == has_role:
			issues.append(label + ': assertion prebinds exactly one logical artifact ID or role')
		if not _valid_assertion_locator(item.get('locator')):
			issues.append(label + ': assertion needs an exact JSON pointer or text locator')
		if not (_valid_comparison(item, operators) and _valid_comparison(item.get('disconfirming'), operators)):
			issues.append(label + ': explicit positive and disconfirming deterministic comparisons required')
def _experiment_payload() -> dict:
	from .experiments import METHODS, OPERATORS, PROPERTY_METHODS, STATUSES
	return {
		'valid': True,
		'topic': 'experiment',
		'schema_version': 1,
		'commands': ['harness.py prepare-experiment <project> --spec <plan.json>', 'harness.py record-experiment <project> --spec <run.json>'],
		'required_fields': {'requirement': ['id', 'claim', 'property', 'method', 'scope.objects', 'conditions', 'expected', 'falsification', 'discriminating_test', 'completion_criterion', 'alternatives', 'assertions'], 'assertion': ['id', 'artifact_id XOR artifact_role', 'locator {type, value}', 'operator', 'expected', 'disconfirming {operator, expected}'], 'run': ['plan', 'plan_sha256', 'status', 'actual_result', 'actual_steps', 'conditions', 'artifacts']},
		'enums': {'methods': list(METHODS), 'operators': list(OPERATORS), 'statuses': list(STATUSES), 'property_methods': {k: sorted(v) for k, v in sorted(PROPERTY_METHODS.items())}},
		'common_pitfalls': ['property must be supported by the chosen method in property_methods.', 'Every assertion requires exactly one of artifact_id or artifact_role and both positive and disconfirming comparisons.', 'json_pointer locator values must be empty or start with "/".'],
		'minimal_example': {'id': 'EXP-1', 'claim': 'Target page exposes Product JSON-LD.', 'property': 'markup', 'method': 'http', 'scope': {'objects': ['https://example.com/product']}, 'conditions': {'session': {'mode': 'unknown'}}, 'expected': 'JSON-LD script contains Product type.', 'falsification': 'No Product type appears in fetched HTML.', 'discriminating_test': 'Inspect extracted JSON-LD @type.', 'completion_criterion': 'Saved HTTP observation inspected.', 'alternatives': ['Markup injected only after client JS.'], 'assertions': [{'id': 'A-1', 'artifact_id': 'page_html', 'locator': {'type': 'text', 'value': 'Product'}, 'operator': 'contains', 'expected': 'Product', 'disconfirming': {'operator': 'equals', 'expected': ''}}]},
	}
def _review_payload() -> dict:
	from .review import REPORT_CONTRACT, REVIEW_SCHEMA, SCOPES, TASK_FLAGS
	return {
		'valid': True,
		'topic': 'review',
		'schema_version': REVIEW_SCHEMA,
		'commands': ['harness.py prepare-review <project> --parent <uuid> --spec <spec.json> --response-file <resp.md>', 'harness.py review-input <project> --package <pkg-json>', 'harness.py native-review-proof <project> --parent <uuid> --reviewer <child-uuid> [--wait-timeout 60]', 'harness.py record-review <project> --parent <uuid> --reviewer <child-uuid> --report <report.json> --native-evidence <proof.json>'],
		'required_fields': {'falsifier_report': ['schema_version', 'review_mode', 'package', 'package_sha256', 'scope', 'result', 'disproved_claims', 'findings'], 'standard_report': ['schema_version', 'package', 'package_sha256', 'scope', 'result', 'claim_reviews', 'findings'], 'claim_review': ['claim_id', 'observed', 'inferred', 'method', 'alternatives', 'limits', 'falsification', 'raw_vs_criteria', 'outcome', 'test_alignment']},
		'enums': {'result': ['approved', 'needs_changes'], 'review_mode': ['falsifier', 'standard'], 'outcome': ['supported', 'qualified', 'unsupported'], 'relationship': ['direct', 'proxy', 'irrelevant'], 'scope': list(SCOPES), 'task_flags': sorted(TASK_FLAGS)},
		'common_pitfalls': ['Copy test_alignment.target_claim verbatim from review-input claim_targets[claim_id] without paraphrasing.', 'Return the JSON verdict once in the final native PLANNER_RESPONSE message; never duplicate full JSON via send_message.', 'Default significant /upwork-init audits to one adversarial falsifier reviewer; escalate to 2 only on findings/needs_changes.'],
		'minimal_example': {'schema_version': REVIEW_SCHEMA, 'review_mode': 'falsifier', 'package': '<package-rel-path>', 'package_sha256': '<64-hex>', 'scope': list(SCOPES), 'result': 'approved', 'disproved_claims': [], 'findings': []},
		'report_contract': dict(REPORT_CONTRACT),
	}
def _valid_assertion_locator(loc) -> bool:
	r = False
	if isinstance(loc, dict) and loc.get('type') in ('json_pointer', 'text') and isinstance(loc.get('value'), str):
		r = ('json_pointer' != loc.get('type')) or (not loc['value']) or loc['value'].startswith('/')
	return r
def _valid_comparison(cmp_obj, operators: tuple[str, ...]) -> bool:
	return isinstance(cmp_obj, dict) and cmp_obj.get('operator') in operators and ('expected' in cmp_obj) and (not isinstance(cmp_obj.get('expected'), (dict, list)))
def annotate_experiment_issues(issues: list[str]) -> list[str]:
	return [msg if 'schema-help experiment' in msg else f'{msg} ({_EXPERIMENT_HINT})' for msg in issues]
def annotate_review_issues(issues: list[str]) -> list[str]:
	return [msg if 'schema-help review' in msg else f'{msg} ({_REVIEW_HINT})' for msg in issues]
def claim_error_hint(code: str) -> str | None:
	c = str(code or '')
	r = _CLAIM_HINTS.get(c)
	if None is r and c.startswith(_CLAIM_PREFIXES):
		r = 'Run: harness.py schema-help analysis.'
	return r
def format_schema_help_text(res: dict) -> str:
	lines = [f"Schema Help: {res['topic']} (schema_version: {res['schema_version']})", 'Commands:']
	lines.extend((f'  - {cmd}' for cmd in res.get('commands') or ()))
	lines.append('Required fields: ' + json.dumps(res.get('required_fields') or {}, ensure_ascii=False))
	lines.append('Enums: ' + json.dumps(res.get('enums') or {}, ensure_ascii=False))
	lines.append('Common pitfalls:')
	lines.extend((f'  - {tip}' for tip in res.get('common_pitfalls') or ()))
	lines.append('Minimal example:')
	lines.append(json.dumps(res.get('minimal_example') or {}, ensure_ascii=False, indent='\t'))
	return '\n'.join(lines) + '\n'
def requirement_assertion_issues(label: str, requirement: dict, operators: tuple[str, ...]) -> list[str]:
	issues: list[str] = []
	assertions = requirement.get('assertions', [])
	if not isinstance(assertions, list):
		issues.append(label + ': assertions must be a list')
	else:
		seen_ids: set[str] = set()
		for item in assertions:
			_check_one_assertion(label, item, seen_ids, operators, issues)
	return issues
def schema_help_payload(topic: str) -> dict:
	key = str(topic or '').strip().lower()
	builders = {'analysis': _analysis_payload, 'experiment': _experiment_payload, 'review': _review_payload}
	builder = builders.get(key)
	if None is builder:
		raise ValueError('Supported schema-help topics: ' + ', '.join(sorted(builders)))
	return builder()
