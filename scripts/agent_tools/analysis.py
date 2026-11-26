# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
import hashlib
import json
import re
from .diagnostics import problem, require_valid
# 2026-11-13
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
from .storage import create_bytes, data_dir_for, locked, replace_bytes, write_immutable_bytes
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
SECTIONS = ('identity', 'concerns', 'misconceptions', 'causes', 'methods')
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
TITLES = ('Client Identification', 'Client Concerns', 'Possible Misconceptions', 'Causes of the Problem in This Client System', 'Solution Methods')
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# @used-by :func:`agent_tools.analysis_merge._validate_partial()`
# @used-by :func:`agent_tools.review._analysis()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :func:`validate_analysis()`
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor._analysis_card_issues()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_many_independent_errors_are_reported_with_fields_and_ids()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_no_anchor_exception_uses_an_observed_specific_section()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_no_counterevidence_needs_documented_review_and_real_sources()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_source_registry_and_escaped_pointers_resolve()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.valid_review_analysis()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_6395_relative_to_5395_is_185357_percent_not_20()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_arbitrary_intake_receipt_cannot_promote_own_note_or_attachment()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_calculation_requires_sourced_common_units_and_explicit_percent_result()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_causal_alternatives_and_recommendation_conditions_are_required()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_critical_severity_needs_impact_evidence()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_currency_cannot_be_borrowed_from_another_quantity()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_dependency_change_and_cycle_are_reported()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e7_contradictory_evidence_reuse_in_against_and_intake_only_counterevidence_cap()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e8_relational_comparison_and_modification_require_two_distinct_operands_with_verified_hashes()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_experiment_primary_uses_recorder_artifact_and_actual_method()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_html_markup_cannot_hide_a_sign_between_spans()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_json_amount_currency_pair_is_an_exact_quantity_locator()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_legacy_is_readable_but_cannot_be_newly_saved_or_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_limited_hypothesis_keeps_missing_browser_check_and_can_be_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_misconception_hypothesis_requires_alternatives_and_discriminating_check()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_primary_http_fact_accepts_and_renders_with_scope()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_referenced_primary_cannot_be_replaced_with_an_own_kb_quote()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_signed_quantity_cannot_be_replaced_with_its_positive_substring()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_unavailable_result_is_valid_with_explicit_gap()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_unverified_hypothesis_with_empty_against_caps_probability_at_75()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_documentation_requires_verified_anchor_or_genuine_no_anchor_section()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_verified_observation_rejects_ungrounded_numbers_in_essence()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_website_requires_valid_url_and_identity_basis()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_legacy_analysis_does_not_silently_clear_existing_risks()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_unknown_duplicate_and_unsupported_basis_cannot_be_published()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_malformed_evidence_fields_return_diagnostics_without_crashing()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_public_example_passes_structure_evidence_and_project_checks()`
def analysis_issues(value):
	issues, claims, references = ([], {}, [])
	# @used-by :func:`analysis_issues()`
	def add(code, field, message, ident=None, hint=None):
		issues.append(problem(code, field, message, claim_id=ident, hint=hint))
	if not isinstance(value, dict):
		r = [problem('analysis.object', '/', 'Analysis must be a JSON object')]
	else:
		if type(value.get('schema_version', 1)) is not int or value.get('schema_version', 1) not in (1, 2, 3):
			add('analysis.version', '/schema_version', 'Supported versions: legacy 1/2 (read only), 3 (current)')
		notes = value.get('notes', {})
		if not isinstance(notes, dict):
			add('analysis.notes', '/notes', 'Analysis notes must be an object')
			notes = {}
		registry = value.get('sources', {})
		if not isinstance(registry, dict):
			add('source.registry', '/sources', 'Sources must be an object')
			registry = {}
		for source_id, source in registry.items():
			if not isinstance(source, str) or not source.strip():
				add('source.registry', f'/sources/{source_id}', 'Source ID must resolve to a nonempty source URI')
		for section in SECTIONS:
			items = value.get(section)
			if not isinstance(items, list):
				add('analysis.section', '/' + section, f'Analysis requires list: {section}')
				continue
			if not items and (not (isinstance(notes.get(section), str) and notes[section].strip())):
				add('analysis.empty', '/' + section, 'Explain what is unknown/not established in notes')
			for index, item in enumerate(items):
				field = f'/{section}/{index}'
				if not isinstance(item, dict):
					add('claim.object', field, 'Each claim must be an object')
					continue
				ident = item.get('id')
				if not isinstance(ident, str) or not re.fullmatch('[A-Z][A-Z0-9-]*', ident) or ident in claims:
					add('claim.id', field + '/id', 'Invalid or duplicate claim ID', str(ident))
				else:
					claims[ident] = section
				for key in ('essence', 'assessment_basis') + (('criterion',) if 'methods' == section else ()):
					if not isinstance(item.get(key), str) or not item[key].strip():
						add('claim.required', field + '/' + key, f'{key} is required', ident)
				score_key = 'score_percent' if 'methods' == section else 'probability_percent'
				score = item.get(score_key)
				if type(score) is not int or not 0 <= score <= 100:
					add('claim.score', field + '/' + score_key, 'Assessment must be an integer from 0 to 100', ident)
				addresses = item.get('addresses', [])
				if not isinstance(addresses, list) or any((not isinstance(x, str) for x in addresses)):
					add('claim.addresses', field + '/addresses', 'addresses must be a list of claim IDs', ident)
				else:
					references.append((field, ident, section, addresses))
					if section in ('causes', 'methods') and (not addresses):
						add('claim.addresses', field + '/addresses', 'Link causes to concerns, methods to causes/tasks', ident)
				for side in ('for', 'against'):
					arguments = item.get(side)
					if not isinstance(arguments, list):
						add('argument.list', field + '/' + side, f'{side} must be a list', ident)
						continue
					if not arguments:
						gap = item.get('counterevidence', {}) if 'against' == side else {}
						if 'against' != side or not valid_gap(gap):
							add('argument.empty', field + '/' + side, 'Concrete arguments required; empty against needs documented counterevidence status', ident)
					for number, arg in enumerate(arguments):
						af = f'{field}/{side}/{number}'
						if not isinstance(arg, dict):
							add('argument.object', af, 'Each argument must be an object', ident)
							continue
						# 2026-10-18
						# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
						# https://github.com/dmitry-ai/harness/issues/10
						if 3 == value.get('schema_version') and (arg.get('claim_id') or arg.get('evidence_id')):
							if not isinstance(arg.get('argument'), str) or not arg['argument'].strip():
								add('argument.required', af + '/argument', 'argument is required', ident)
							if arg.get('claim_id') and arg.get('evidence_id'):
								add('argument.source', af, 'Use one claim_id or evidence_id reference', ident)
							continue
						for key in ('argument', 'quote'):
							if not isinstance(arg.get(key), str) or not arg[key].strip():
								add('argument.required', af + '/' + key, f'{key} is required', ident)
						source = source_uri(arg, registry)
						if not isinstance(source, str) or not source.strip():
							add('argument.source', af + '/source', 'Needs a source or a resolvable source_id', ident)
						if arg.get('source') and arg.get('source_id'):
							add('argument.source', af, 'Use source or source_id, not two competing references', ident)
						if arg.get('documentation') and isinstance(source, str) and ('#' not in source or not source.split('#', 1)[1]):
							locator = arg.get('anchor_exception')
							if not isinstance(locator, dict) or not all((isinstance(locator.get(k), str) and locator[k].strip() for k in ('section', 'observation'))):
								add('documentation.locator', af + '/anchor_exception', 'Documentation needs a section anchor or section + saved observation', ident, 'collect the page; record its section and observation URI; verify evidence')
		for field, ident, section, addresses in references:
			for target in addresses:
				if target not in claims:
					add('claim.reference', field + '/addresses', f'Unknown claim reference: {target}', ident)
			allowed = ('concerns',) if 'causes' == section else ('concerns', 'causes')
			if section in ('causes', 'methods') and addresses and (not any((claims.get(x) in allowed for x in addresses))):
				add('claim.reference_kind', field + '/addresses', 'Reference must address a concern or applicable cause', ident)
		# 2026-10-15
		# "Detect Upwork client intermediation and unidentified target websites with managed Red Flags blocks":
		# https://github.com/dmitry-ai/harness/issues/5
		from .red_flags import red_flag_issues
		issues.extend(red_flag_issues(value, claims))
		# 2026-10-17
		# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
		# https://github.com/dmitry-ai/harness/issues/7
		from .knowledge import website_issues
		issues.extend(website_issues(value))
		# 2026-10-18
		# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
		# https://github.com/dmitry-ai/harness/issues/10
		from .claims import contract_issues
		issues.extend(contract_issues(value))
		r = issues
	return r
# @used-by :func:`analysis_issues()`
def valid_gap(gap):
	return isinstance(gap, dict) and gap.get('status') in ('not_found', 'unavailable') and isinstance(gap.get('reviewed_sources'), list) and bool(gap['reviewed_sources']) and all((isinstance(x, str) and x.strip() for x in gap['reviewed_sources'])) and isinstance(gap.get('limitations'), str) and bool(gap['limitations'].strip())
# @used-by :func:`analysis_issues()`
# @used-by :func:`iter_arguments()`
# @used-by :func:`render_analysis()`
def source_uri(argument, registry):
	if 'source_id' not in argument:
		r = argument.get('source')
	else:
		ident = argument.get('source_id')
		r = registry.get(ident) if isinstance(ident, str) and ident else None
	return r
# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
# @used-by :func:`agent_tools.upwork_data.format_kb_project_md()`
# @used-by :func:`publish_analysis()`
# @used-by :func:`render_analysis()`
# @used-by :func:`save_analysis()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_analysis_links_causes_to_concerns_and_methods_to_causes()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_malformed_analysis_has_actionable_errors()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_missing_counterevidence_probability_or_documentation_anchor_is_rejected()`
def validate_analysis(value):
	require_valid(analysis_issues(value))
# @used-by :func:`agent_tools.analysis_merge.save_merged_analysis()`
# @used-by :func:`agent_tools.cli_domains._op_save_analysis()`
# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
# @used-by :func:`test_project_domain_drift._save_and_publish()`
# @used-by :func:`test_project_rename._seed_project_artifacts()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_arbitrary_intake_receipt_cannot_promote_own_note_or_attachment()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_html_markup_cannot_hide_a_sign_between_spans()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_legacy_is_readable_but_cannot_be_newly_saved_or_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_limited_hypothesis_keeps_missing_browser_check_and_can_be_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_signed_quantity_cannot_be_replaced_with_its_positive_substring()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_documentation_requires_verified_anchor_or_genuine_no_anchor_section()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_save_checks_real_evidence_and_does_not_overwrite_invalid_candidate()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_analysis_commit_requires_current_hash_and_preserves_history()`
def save_analysis(root, candidate, expected_sha256=None):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	from .research import inside
	pp = project_paths(root, exact_root=True)
	root = pp.root
	# 2026-10-17
	# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
	# https://github.com/dmitry-ai/harness/issues/7
	value = candidate if isinstance(candidate, dict) else json.loads(inside(root, candidate).read_text(encoding='utf-8-sig'))
	validate_analysis(value)
	# 2026-10-18
	# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
	# https://github.com/dmitry-ai/harness/issues/10
	require_current_contract(value)
	from .evidence import evidence_issues
	# 2026-11-13
	# "Extract ClaimGraphValidator class and unify derived_from DAG traversals, numeric grounding, and primary quote verification across claims.py, text_claims.py, review.py, and evidence.py":
	# https://github.com/dmitry-ai/harness/issues/62
	require_valid(evidence_issues(root, value, skip_structural=True))
	payload = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
	target = pp.kb_dir / 'Analysis.json'
	target.parent.mkdir(parents=True, exist_ok=True)
	with locked(pp.data_dir / 'analysis.lock'):
		previous = target.read_bytes() if target.exists() else None
		if None is not previous and digest(previous) != expected_sha256:
			raise ValueError('Analysis changed or expected hash was not supplied; read current KB and reconcile the candidate')
		if None is previous and None is not expected_sha256:
			raise ValueError('Expected existing analysis is missing; preserve candidate and inspect state')
		if None is not previous and previous != payload:
			# 2026-11-13
			# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
			# https://github.com/dmitry-ai/harness/issues/63
			write_immutable_bytes(pp.data_dir / 'analysis-history' / (digest(previous) + '.json'), previous)
		if (target.read_bytes() if target.exists() else None) != previous:
			raise ValueError('Analysis changed during commit; external edit preserved')
		if None is previous:
			create_bytes(target, payload)
		elif previous != payload:
			replace_bytes(target, payload)
	r = {'target': str(target), 'sha256': digest(payload), 'schema_valid': True, 'evidence_checked': True, 'detail': 'Primary references checked; update dependent agent KB modules before independent semantic review'}
	return r
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# @used-by :func:`publish_analysis()`
# @used-by :func:`save_analysis()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine._apply_complete_stage()`
def require_current_contract(value):
	require_valid([] if isinstance(value, dict) and 3 == value.get('schema_version') else [problem('analysis.current_contract', '/schema_version', 'New saved/published analyses require schema_version 3 and explicit provenance; preserve legacy files and reconcile a candidate')])
# @used-by :func:`agent_tools.evidence.evidence_issues()`
def iter_arguments(value):
	registry = value.get('sources', {})
	registry = registry if isinstance(registry, dict) else {}
	for section in SECTIONS:
		for index, item in enumerate(value.get(section, []) if isinstance(value.get(section), list) else []):
			if not isinstance(item, dict):
				continue
			for side in ('for', 'against'):
				for number, arg in enumerate(item.get(side, []) if isinstance(item.get(side), list) else []):
					if isinstance(arg, dict):
						yield (item.get('id'), f'/{section}/{index}/{side}/{number}', arg, source_uri(arg, registry))
# @used-by :func:`publish_analysis()`
# @used-by :func:`test_atomic_prepare_and_narrowed_reconcile_m7._init_review_ready_project()`
# @used-by :func:`test_contract_invariants._init_tracked_project()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_source_registry_and_escaped_pointers_resolve()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_legacy_is_readable_but_cannot_be_newly_saved_or_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_primary_http_fact_accepts_and_renders_with_scope()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_documentation_requires_verified_anchor_or_genuine_no_anchor_section()`
# @used-by :meth:`test_onboarding.EvidenceTests.test_analysis_links_causes_to_concerns_and_methods_to_causes()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_readable_links.ReadableProjectTests.test_analysis_sources_are_readable_while_quotes_keep_their_exact_bytes()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_each_risk_can_be_shown_alone_without_combination_warning()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_no_flags_does_not_create_warning_or_change_original_card()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_suspected_intermediary_is_not_reported_as_confirmed()`
def render_analysis(value):
	validate_analysis(value)
	# 2026-10-15
	# "Detect Upwork client intermediation and unidentified target websites with managed Red Flags blocks":
	# https://github.com/dmitry-ai/harness/issues/5
	from .red_flags import render_red_flags
	# 2026-10-17
	# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
	# https://github.com/dmitry-ai/harness/issues/9
	from .links import markdown_link
	lines = [render_red_flags(value)] if value.get('red_flags') else []
	# 2026-10-18
	# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
	# https://github.com/dmitry-ai/harness/issues/10
	if 3 == value.get('schema_version'):
		lines.extend(['# Primary Observations and Calculations', ''])
		for fact in value['facts']:
			lines.extend([f"## {fact['id']}", fact['essence'], '', *_render_claim_contract(fact)])
	for number, (key, title) in enumerate(zip(SECTIONS, TITLES), 1):
		lines.extend([f'# {number}. {title}', ''])
		if not value[key]:
			lines.extend([value['notes'][key], ''])
		for item in value[key]:
			lines.extend([f"## {item['id']}", item['essence'], ''])
			if 3 == value.get('schema_version'):
				lines.extend(_render_claim_contract(item))
			if item.get('addresses'):
				lines.extend(['Addresses: ' + ', '.join((f'[{i}](#{i.lower()})' for i in item['addresses'])) + '.', ''])
			for side, label in (('for', 'For'), ('against', 'Against')):
				lines.append(f'### {label}')
				for arg in item[side]:
					if 3 == value.get('schema_version') and (arg.get('claim_id') or arg.get('evidence_id')):
						target = arg.get('claim_id') or arg['evidence_id']
						lines.extend([arg['argument'], f'[Basis: {target}](#{target.lower()})', ''])
						continue
					source = source_uri(arg, value.get('sources', {}))
					lines.extend([arg['argument'], '> ' + arg['quote'].replace('\n', '\n> '), markdown_link('Source', source), ''])
					if arg.get('anchor_exception'):
						locator = arg['anchor_exception']
						lines.extend([f"Section: {locator['section']}.", markdown_link('Address verification', locator['observation']), ''])
				if 'against' == side and (not item[side]):
					gap = item['counterevidence']
					lines.extend([f"Counterevidence status: {gap['status']}.", gap['limitations'], ''])
					lines.extend((markdown_link('Reviewed source', x) for x in gap['reviewed_sources']))
					lines.append('')
			if 'methods' == key:
				lines.append(f"Score: {item['score_percent']}% ({item['criterion']}).")
			else:
				lines.append(f"Expert plausibility: {item['probability_percent']}%.")
			lines.extend([item['assessment_basis'], ''])
	r = '\n'.join(lines)
	return r
# 2026-10-18
# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
# https://github.com/dmitry-ai/harness/issues/10
# @used-by :func:`render_analysis()`
def _render_claim_contract(claim):
	from .links import markdown_link
	lines = [f"Kind: {claim['knowledge_type']}. Verification status: {claim['verification_status']}.", 'Scope: ' + claim['scope']['description'], '']
	if claim['scope']['sample']:
		lines.extend(['Verified objects: ' + '; '.join(claim['scope']['sample']) + '.', ''])
	for limitation in claim['scope']['limitations']:
		lines.extend(['Limitation: ' + limitation, ''])
	for dep in claim['derived_from']:
		lines.extend([f"Dependency: [{dep['claim_id']}](#{dep['claim_id'].lower()}), version `{dep['sha256']}`.", ''])
	for ref in claim['evidence']:
		lines.extend([f"### {ref['id']}", '> ' + ref['quote'].replace('\n', '\n> '), markdown_link('Primary source', ref['source']), f"Locator: {ref['locator']['type']}: {ref['locator']['value']}. SHA-256: `{ref['source_sha256']}`.", ''])
		if ref.get('anchor_exception'):
			exception = ref['anchor_exception']
			lines.extend(['Documentation section: ' + exception['section'] + '.', markdown_link('Saved anchor-absence verification', exception['observation']), ''])
	for missing in claim['missing_checks']:
		lines.extend(['Missing check: ' + missing, ''])
	if claim.get('alternative_explanations'):
		lines.extend(['Alternatives: ' + '; '.join(claim['alternative_explanations']) + '.', claim['discriminating_check'], ''])
	if claim.get('applicability'):
		lines.extend(['Applicability conditions: ' + '; '.join(claim['applicability']) + '.', 'Result validation: ' + claim['validation'], ''])
	lines.extend(['Impact: ' + claim['impact']['severity'] + '. ' + claim['impact']['basis'], ''])
	if claim.get('calculation'):
		calc = claim['calculation']
		lines.extend([f"Calculation: `{calc['formula']}`; old={calc['operands']['old']['value']} {calc['operands']['old']['unit']}; new={calc['operands']['new']['value']} {calc['operands']['new']['unit']}; result {calc['result']}%; rounding {calc['rounding']} to {calc['rounding_places']} places.", ''])
	r = lines
	return r
# 2026-10-15
# "Detect Upwork client intermediation and unidentified target websites with managed Red Flags blocks":
# https://github.com/dmitry-ai/harness/issues/5
# @used-by :func:`agent_tools.cli_domains._op_render_analysis()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :func:`test_finalized_project_contract._seed_pre_review()`
# @used-by :func:`test_project_domain_drift._save_and_publish()`
# @used-by :func:`test_project_rename._seed_project_artifacts()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_legacy_is_readable_but_cannot_be_newly_saved_or_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_limited_hypothesis_keeps_missing_browser_check_and_can_be_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_save_checks_real_evidence_and_does_not_overwrite_invalid_candidate()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_explicit_website_is_published_and_reused_without_overwriting_card_or_metadata()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_new_analysis_cannot_finish_with_an_unpublished_website_card()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_website_and_red_flags_have_stable_order_and_preserve_manual_edits()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_both_risks_precede_technical_analysis_and_are_duplicated_in_card()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_repeated_render_preserves_new_user_notes_and_does_not_duplicate_block()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_resolved_risks_update_both_surfaces_and_keep_original_card_history()`
# @used-by :meth:`test_red_flags.RedFlagTests.test_standalone_input_never_updates_project_card()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_public_example_passes_structure_evidence_and_project_checks()`
def publish_analysis(source, target=None):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths, resolve_project_root
	from .red_flags import sync_project_red_flags
	source = Path(source).resolve()
	value = json.loads(source.read_text(encoding='utf-8-sig'))
	# 2026-10-18
	# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
	# https://github.com/dmitry-ai/harness/issues/10
	require_current_contract(value)
	proj_root = resolve_project_root(source)
	pp = project_paths(proj_root, exact_root=True)
	expected_source = (pp.kb_dir / 'Analysis.json').resolve()
	is_standard_layout = 'Analysis.json' == source.name and 'KB' == source.parent.name and ('ꘖ' == source.parent.parent.name)
	if source != expected_source and (not is_standard_layout):
		raise ValueError('Publish a reconciled schema 3 candidate from its project ꘖ/KB/Analysis.json')
	if source != expected_source and is_standard_layout:
		proj_root = source.parents[2]
	from .evidence import evidence_issues
	validate_analysis(value)
	# 2026-11-13
	# "Extract ClaimGraphValidator class and unify derived_from DAG traversals, numeric grounding, and primary quote verification across claims.py, text_claims.py, review.py, and evidence.py":
	# https://github.com/dmitry-ai/harness/issues/62
	require_valid(evidence_issues(proj_root, value, skip_structural=True))
	result = publish_owned(target or source.with_suffix('.md'), render_analysis(value), source=source)
	# 2026-10-17
	# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
	# https://github.com/dmitry-ai/harness/issues/7
	if 'conflict' == result['status']:
		r = result
	else:
		from .knowledge import sync_website_card
		result['website_card'] = sync_website_card(proj_root, value)
		card = sync_project_red_flags(proj_root, value)
		result['project_card'] = card
		if 'conflict' == card['status']:
			result['status'] = 'conflict'
		if 'conflict' == result['website_card']['status']:
			result['status'] = 'conflict'
		r = result
	return r
# @used-by :func:`agent_tools.analysis_merge._load_merge_base()`
# @used-by :func:`agent_tools.analysis_merge.save_merged_analysis()`
# @used-by :func:`agent_tools.knowledge.sync_website_card()`
# @used-by :func:`agent_tools.operations._execute_collect()`
# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
# @used-by :func:`publish_owned()`
# @used-by :func:`save_analysis()`
def digest(data):
	return hashlib.sha256(data).hexdigest()
# @used-by :func:`agent_tools.intake._index()`
# @used-by :func:`agent_tools.operations._execute_collect()`
# @used-by :func:`publish_analysis()`
# @used-by :func:`test_atomic_prepare_and_narrowed_reconcile_m7._init_review_ready_project()`
# @used-by :func:`test_contract_invariants._init_tracked_project()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.publish_progress()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_full_workflow_requires_native_review_and_current_kb_then_exports_complete_context()`
# @used-by :meth:`test_analysis_workflow.PublicationTests.test_interrupted_state_write_preserves_published_output_for_recovery()`
# @used-by :meth:`test_analysis_workflow.PublicationTests.test_repeat_render_updates_owned_file_and_archives_previous_bytes()`
# @used-by :meth:`test_analysis_workflow.PublicationTests.test_untracked_or_manually_edited_file_is_preserved_with_candidate()`
# @used-by :meth:`test_chat_reply_link_issues_m5.ChatReplyLinkIssuesM5Tests.test_finalize_stage_accepts_unencoded_file_uri_chat_links()`
# @used-by :meth:`test_portability.CodexEvidenceTests.test_codex_workflow_reviews_current_kb_and_exports_exact_native_request_and_reply()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_exact_quotes_code_and_source_copies_are_not_rewritten_or_rejected()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_publication_guard_keeps_previous_document_and_primary_json_intact()`
def publish_owned(target, content, *, source=None, history=True):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	target = Path(target).resolve()
	payload = content.encode('utf-8') if isinstance(content, str) else content
	# 2026-10-17
	# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
	# https://github.com/dmitry-ai/harness/issues/9
	if target.suffix.lower() in ('.md', '.markdown', '.txt', '.html', '.htm'):
		from .links import readable_link_issues
		issues = readable_link_issues(payload.decode('utf-8'))
		if issues:
			raise ValueError('\n'.join(issues))
	pp = project_paths(target)
	state_dir = pp.data_dir
	state_file = pp.rendered_json
	with locked(state_dir / 'render.lock'):
		receipt = json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else {}
		key = str(target)
		previous = target.read_bytes() if target.exists() else None
		expected = receipt.get(key, {}).get('sha256')
		if None is not previous and previous != payload and (digest(previous) != expected):
			# 2026-11-13
			# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
			# https://github.com/dmitry-ai/harness/issues/63
			candidate = write_immutable_bytes(state_dir / 'render-candidates' / (digest(key.encode())[:16] + '-' + digest(payload)[:16] + target.suffix), payload)
			r = {'status': 'conflict', 'target': str(target), 'candidate': str(candidate), 'detail': 'Existing file is untracked or changed; preserved for reconciliation'}
		else:
			if history and None is not previous and (previous != payload):
				write_immutable_bytes(state_dir / 'render-history' / digest(key.encode())[:16] / (digest(previous) + target.suffix), previous)
			target.parent.mkdir(parents=True, exist_ok=True)
			if (target.read_bytes() if target.exists() else None) != previous:
				raise ValueError('Target changed during publication; preserve the external edit and retry reconciliation')
			if previous != payload:
				replace_bytes(target, payload)
			if target.read_bytes() != payload:
				raise OSError('Published file failed read-back verification')
			receipt[key] = {**receipt.get(key, {}), 'sha256': digest(payload), 'source': source if isinstance(source, dict) else str(source) if source else None}
			replace_bytes(state_file, (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode())
			r = {'status': 'unchanged' if previous == payload else 'published', 'target': str(target), 'sha256': digest(payload)}
	return r
