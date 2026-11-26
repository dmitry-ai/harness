# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit
import hashlib
# 2026-11-16
# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
# https://github.com/dmitry-ai/harness/issues/81
import html as html_lib
import json
import re
from .analysis import iter_arguments, SECTIONS
from .diagnostics import problem
from .research import inside, load_observation, extract_bytes
# @used-by :func:`source_reference()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_source_registry_and_escaped_pointers_resolve()`
def pointer(*parts):
	return '/' + '/'.join((str(x).replace('~', '~0').replace('/', '~1') for x in parts)) if parts else ''
# 2026-11-14
# "Decompose experiments.py into ExperimentPlanStore, BrowserTraceInspector, and ExperimentRunValidator classes and unify raw_decode JSON object scanning":
# https://github.com/dmitry-ai/harness/issues/72
# @used-by :func:`agent_tools.completion._response_link_issues()`
# @used-by :func:`agent_tools.evidence_loader.load_observation_content()`
# @used-by :func:`agent_tools.experiments._select_raw()`
# @used-by :func:`agent_tools.links.validate_file()`
# @used-by :func:`saved_source()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkResolver.RepoLinkResolver.__validate_doc_or_json_anchor()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_source_registry_and_escaped_pointers_resolve()`
def resolve_pointer(value, fragment, *, decode_uri: bool=True):
	if decode_uri:
		fragment = unquote(fragment)
	if not fragment:
		r = value
	else:
		if not fragment.startswith('/'):
			raise ValueError('JSON fragment must be an RFC 6901 pointer')
		for raw in fragment[1:].split('/'):
			if re.search('~(?![01])', raw):
				raise ValueError('Invalid JSON pointer escape')
			key = raw.replace('~1', '/').replace('~0', '~')
			if isinstance(value, dict):
				value = value[key]
			elif not isinstance(value, list):
				raise ValueError('Pointer traverses a scalar')
			else:
				if not re.fullmatch('0|[1-9][0-9]*', key):
					raise ValueError('Array pointer must be a nonnegative canonical index')
				value = value[int(key)]
		r = value
	return r
# @used-by :func:`agent_tools.claims._manifest_primary()`
# @used-by :func:`agent_tools.claims._primary_capabilities()`
# @used-by :func:`agent_tools.evidence_loader.load_observation_content()`
# @used-by :func:`agent_tools.evidence_loader.probe_observation_status()`
# @used-by :func:`agent_tools.text_claims.evidence_inputs()`
# @used-by :func:`agent_tools.text_sources._evaluate()`
# @used-by :func:`evidence_issues()`
# @used-by :func:`saved_source()`
def local_file(root, reference):
	# 2026-11-23
	# "Unify local Tier 0 source hydration, HTTP/DOM Evidence observation loading, CommonMark helpers, and file:// path parsing across source_grounding.py, response_grounding.py, evidence.py, links.py, text_sources.py, and markdown_links.py":
	# https://github.com/dmitry-ai/harness/issues/76
	from .links import decode_file_uri
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	path = decode_file_uri(reference, reject_remote=True)
	pp = project_paths(root, exact_root=True)
	root_resolved = pp.root
	target = (pp.kb_dir / path).resolve()
	# 2026-10-17
	# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
	# https://github.com/dmitry-ai/harness/issues/7
	if not target.exists() and path.replace('\\', '/').lstrip('/').startswith('source/'):
		alt = (root_resolved / path.replace('\\', '/').lstrip('/')).resolve()
		if alt.is_relative_to(pp.source_dir):
			target = alt
	if not (target.is_relative_to(root_resolved) or target.is_relative_to(pp.kb_dir.resolve())):
		raise ValueError('Source path escapes the project; copy authorized primary evidence into Evidence first')
	r = target
	return r
# 2026-10-17
# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
# https://github.com/dmitry-ai/harness/issues/7
# 2026-11-16
# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
# https://github.com/dmitry-ai/harness/issues/81
# @used-by :func:`saved_source()`
def _markdown_section(text: str, fragment: str) -> str:
	from .links import parse_markdown_headings
	headings, _, ambiguous, _ = parse_markdown_headings(text)
	target = unquote(fragment)
	if target in ambiguous:
		raise ValueError('Markdown section anchor is ambiguous')
	match = next((i for i, h in enumerate(headings) if target in h['section_anchors']), None)
	if None is match:
		raise ValueError('Markdown section anchor is absent')
	lines = text.splitlines(keepends=True)
	heading = headings[match]
	end = next((h['start_line'] for h in headings[match + 1:] if h['level'] <= heading['level']), len(lines))
	raw_sec = ''.join(lines[heading['start_line']:end])
	unesc_sec = html_lib.unescape(raw_sec)
	r = raw_sec if unesc_sec == raw_sec else raw_sec + '\n' + unesc_sec
	return r
# 2026-11-24
# "Cache runtime settings and deduplicate evidence validation in hot paths":
# https://github.com/dmitry-ai/harness/issues/227
# @used-by :func:`evidence_issues()`
# @used-by :func:`verify_saved_quote()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_m1_and_m2_html_wrapper_anchors_and_markdown_explicit_heading_ids_in_evidence_contract()`
def saved_source(root, source, observation=None, *, need_sections=True):
	base, fragment = urldefrag(source)
	if urlsplit(base).scheme.lower() not in ('http', 'https'):
		file = local_file(root, base)
		raw = file.read_bytes()
		if re.fullmatch('[a-f0-9]{64}', file.stem.lower()) and hashlib.sha256(raw).hexdigest() != file.stem.lower():
			raise ValueError('Immutable source file differs from its content-addressed filename')
		if file.suffix.lower() not in ('.pdf', '.docx', '.odt', '.xlsx', '.xlsm', '.rtf'):
			text = raw.decode('utf-8-sig')
			if '.json' == file.suffix.lower():
				value = resolve_pointer(json.loads(text), fragment)
				rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
				r = {'kind': 'json', 'text': rendered, 'fragment': unquote(fragment), 'file': file, 'sha256': hashlib.sha256(raw).hexdigest()}
			elif file.suffix.lower() in ('.html', '.htm'):
				r = {'kind': 'html', 'data': extract_bytes(raw, 'text/html', 'html'), 'raw': text, 'fragment': unquote(fragment), 'file': file, 'sha256': hashlib.sha256(raw).hexdigest()}
			else:
				if ('.md' == file.suffix.lower() or '.md' == file.name) and fragment:
					text = _markdown_section(text, fragment)
				elif fragment:
					raise ValueError('This source format does not support a verified fragment locator')
				r = {'kind': 'text', 'text': text, 'fragment': unquote(fragment), 'file': file, 'sha256': hashlib.sha256(raw).hexdigest()}
		else:
			# 2026-10-17
			# "Enforce complete client attachment ingestion, verbatim media transcription, and intake-drain staging":
			# https://github.com/dmitry-ai/harness/issues/7
			from .upwork_data import extract_attachment_markdown
			md_text = extract_attachment_markdown(file, raw)
			if fragment:
				md_text = _markdown_section(md_text, fragment)
			plain_text = re.sub('\\[([^\\]]+)\\]\\([^)]+\\)', '\\1', md_text).replace('**', '')
			r = {'kind': 'text', 'text': md_text + '\n' + plain_text, 'fragment': unquote(fragment), 'file': file, 'sha256': hashlib.sha256(raw).hexdigest()}
	else:
		# 2026-11-23
		# "Unify local Tier 0 source hydration, HTTP/DOM Evidence observation loading, CommonMark helpers, and file:// path parsing across source_grounding.py, response_grounding.py, evidence.py, links.py, text_sources.py, and markdown_links.py":
		# https://github.com/dmitry-ai/harness/issues/76
		from .evidence_loader import load_observation_content, resolve_http_observation
		obs_ref, meta = resolve_http_observation(root, base, observation)
		r = load_observation_content(root, obs_ref, meta, fragment=fragment, need_sections=need_sections)
	return r
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`verify_html_quote_scope()`
# @used-by :func:`verify_saved_quote()`
def contains_quote(text, quote, mode='exact'):
	if 'exact' == mode:
		r = quote in text
	elif 'whitespace' != mode:
		raise ValueError('quote_match must be exact or whitespace')
	else:
		r = ' '.join(quote.split()) in ' '.join(text.split())
	return r
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# @used-by :func:`agent_tools.analysis.publish_analysis()`
# @used-by :func:`agent_tools.analysis.save_analysis()`
# @used-by :func:`agent_tools.analysis_merge._validate_partial()`
# @used-by :func:`agent_tools.review._analysis()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor._analysis_card_issues()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_anchored_quote_from_another_section_is_rejected()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_content_addressed_primary_evidence_tampering_is_detected()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_existing_heading_or_ancestor_anchor_is_required()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_local_markdown_quote_must_belong_to_the_linked_section()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_no_anchor_exception_uses_an_observed_specific_section()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_no_counterevidence_needs_documented_review_and_real_sources()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_quote_from_another_json_field_is_rejected()`
# @used-by :meth:`test_analysis_workflow.AnalysisContractTests.test_source_registry_and_escaped_pointers_resolve()`
# @used-by :meth:`test_analysis_workflow.ProjectCase.valid_review_analysis()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_6395_relative_to_5395_is_185357_percent_not_20()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_agent_site_hypothesis_in_intake_manifest_is_not_primary()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_arbitrary_intake_receipt_cannot_promote_own_note_or_attachment()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_calculation_operand_must_match_its_own_primary_quote()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_calculation_requires_sourced_common_units_and_explicit_percent_result()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_currency_cannot_be_borrowed_from_another_quantity()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e1_and_e2_sitemap_alone_and_unobserved_sample_urls_are_rejected()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e3_network_error_classification_and_unverified_dns_claim_rejection()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e4_site_wide_schema_absence_requires_multi_page_or_product_template_sample()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_e8_relational_comparison_and_modification_require_two_distinct_operands_with_verified_hashes()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_experiment_primary_uses_recorder_artifact_and_actual_method()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_explicit_text_locator_does_not_cover_another_part_of_page()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_full_real_intake_receipt_binds_source_to_snapshot_and_rejects_relabelled_note()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_html_markup_cannot_hide_a_sign_between_spans()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_http_does_not_establish_click_currency_ip_or_admin()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_json_amount_currency_pair_is_an_exact_quantity_locator()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_limited_hypothesis_keeps_missing_browser_check_and_can_be_published()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_m1_and_m2_html_wrapper_anchors_and_markdown_explicit_heading_ids_in_evidence_contract()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_malformed_properties_and_dependency_keep_field_diagnostics_in_cli()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_missing_or_revised_primary_hash_is_rejected()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_own_prya_kb_note_in_evidence_is_not_a_primary_observation()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_primary_http_fact_accepts_and_renders_with_scope()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_registered_intake_and_attachment_are_primary_but_quote_must_match_locator()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_signed_quantity_cannot_be_replaced_with_its_positive_substring()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_supported_signed_quantities_preserve_decimal_value_and_units()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_unavailable_result_is_valid_with_explicit_gap()`
# @used-by :meth:`test_evidence_contract.EvidenceContractTests.test_v3_documentation_requires_verified_anchor_or_genuine_no_anchor_section()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_malformed_evidence_fields_return_diagnostics_without_crashing()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_public_example_passes_structure_evidence_and_project_checks()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_remote_json_pointer_checks_only_the_target_field()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_authorize_deduplicates_evidence_issues_across_check_project()`
def evidence_issues(root, value, *, skip_structural=False):
	if not isinstance(value, dict):
		r = [problem('analysis.object', '/', 'Analysis must be a JSON object')]
	else:
		issues = []
		for ident, field, argument, source in iter_arguments(value):
			if not isinstance(source, str) or not isinstance(argument.get('quote'), str):
				continue
			exception = argument.get('anchor_exception') if isinstance(argument.get('anchor_exception'), dict) else {}
			try:
				# 2026-11-13
				# "Extract ClaimGraphValidator class and unify derived_from DAG traversals, numeric grounding, and primary quote verification across claims.py, text_claims.py, review.py, and evidence.py":
				# https://github.com/dmitry-ai/harness/issues/62
				verify_saved_quote(root, source, argument['quote'], mode=argument.get('quote_match', 'exact'), expected_hash=argument.get('source_sha256'), observation=argument.get('observation') or exception.get('observation'), documentation=bool(argument.get('documentation')), exception=exception)
			except (OSError, ValueError, KeyError, IndexError, TypeError, UnicodeError) as exc:
				issues.append(problem('evidence.unconfirmed', field, str(exc), claim_id=ident, hint='Use the exact saved source and locator; keep the claim unverified until resolved'))
		for section in SECTIONS:
			for index, claim in enumerate(value.get(section, []) if isinstance(value.get(section), list) else []):
				if not isinstance(claim, dict) or [] != claim.get('against'):
					continue
				gap = claim.get('counterevidence', {})
				reviewed = gap.get('reviewed_sources', []) if isinstance(gap, dict) else []
				for source in reviewed if isinstance(reviewed, list) else []:
					if not isinstance(source, str):
						continue
					try:
						if source.startswith(('http://', 'https://')):
							# 2026-11-24
							# "Cache runtime settings and deduplicate evidence validation in hot paths":
							# https://github.com/dmitry-ai/harness/issues/227
							saved_source(root, source, need_sections=False)
						else:
							file = local_file(root, source)
							if 'observation.json' != file.name and (not file.is_file()):
								raise FileNotFoundError(source)
							elif 'observation.json' == file.name:
								observation = load_observation(root, source)
								if 'not_found' == gap.get('status') and (observation.get('error') or ('http' == observation.get('kind', 'http') and (not 200 <= observation['status'] < 300))):
									raise ValueError('An unavailable observation establishes unavailable, not a completed search for counterevidence')
					except (OSError, ValueError, KeyError, TypeError) as exc:
						issues.append(problem('counterevidence.unconfirmed', f'/{section}/{index}/counterevidence', str(exc), claim_id=claim.get('id')))
		# 2026-10-18
		# "Enforce pre-registered experiment plans, claim-to-test alignment, native reviewer provenance, and executor metadata verification":
		# https://github.com/dmitry-ai/harness/issues/10
		from .claims import evidence_contract_issues
		issues.extend(evidence_contract_issues(root, value, skip_structural=skip_structural))
		r = issues
	return r
# @used-by :func:`agent_tools.cli_domains._op_source_ref()`
def source_reference(root, file, parts=()):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	kb_dir = project_paths(root, exact_root=True).kb_dir.resolve()
	file = inside(kb_dir, file)
	r = file.relative_to(kb_dir).as_posix() + ('#' + pointer(*parts) if parts else '')
	return r
# 2026-11-13
# "Unify quote normalization, MarkdownIt link/quote traversal, locale checks, numeric corpus tokenization, and Evidence loading across response_grounding.py, completion.py, source_grounding.py, claims.py, and review.py":
# https://github.com/dmitry-ai/harness/issues/59
# @used-by :func:`verify_saved_quote()`
def verify_html_quote_scope(saved, quote, mode='exact', *, documentation=False, exception=None, observation=None, require_bound_observation=False) -> str:
	# 2026-11-16
	# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
	# https://github.com/dmitry-ai/harness/issues/81
	from .research import classify_html_challenge
	data, fragment = (saved['data'], saved.get('fragment'))
	is_md = bool(saved.get('is_markdown'))
	meta_status = (saved.get('meta') or {}).get('status')
	# 2026-11-24
	# "Cache runtime settings and deduplicate evidence validation in hot paths":
	# https://github.com/dmitry-ai/harness/issues/227
	if data.get('browser_check_required') or ((not is_md) and (not saved.get('challenge_checked')) and classify_html_challenge(saved['raw'], parsed=data, status=meta_status)):
		raise ValueError('Challenge page requires browser verification; it cannot establish the intended page content')
	if fragment:
		if fragment not in data['anchors'] or fragment in data.get('ambiguous_anchors', []):
			raise ValueError('Primary anchor is absent or ambiguous')
		scopes = [h['content'] for h in data['sections'] if fragment in (h.get('section_anchors') or ([h['anchor']] if h.get('anchor') else []))] or data['anchor_content'].get(fragment, [])
		if not scopes or not any((contains_quote(s, quote, mode) for s in scopes)):
			raise ValueError('Quote does not belong to the primary anchor')
		r = '\n'.join(scopes)
	elif not documentation:
		if is_md:
			if not (contains_quote(saved['raw'], quote, mode) or contains_quote(data['text'], quote, mode)):
				raise ValueError('Quote is absent from the saved page')
			r = saved['raw'] if contains_quote(saved['raw'], quote, mode) else data['text']
		else:
			if not (contains_quote(data['text'], quote, mode) or contains_quote(saved['raw'], quote, mode) or contains_quote(data['text'] + '\n' + saved['raw'], quote, mode)):
				raise ValueError('Quote is absent from the saved page')
			r = data['text'] + '\n' + saved['raw']
	else:
		if not isinstance(exception, dict):
			raise ValueError('Documentation without an anchor needs a named saved section')
		if require_bound_observation and (not observation or exception.get('observation') != observation):
			raise ValueError('Documentation anchor exception must bind the exact primary observation')
		matches = [section for section in data['sections'] if section['text'] == exception.get('section')]
		if 1 != len(matches):
			raise ValueError('Documentation section is missing or ambiguous')
		if matches[0].get('section_anchors') or matches[0].get('anchor') or any((contains_quote(s, quote, mode) for ca in matches[0].get('container_anchors') or [] for s in data['anchor_content'].get(ca, []))):
			raise ValueError('Documentation section has an available anchor; use its verified address')
		if not contains_quote(matches[0]['content'], quote, mode):
			raise ValueError('Quote does not match the documented section')
		r = matches[0]['content']
	return r
# 2026-11-13
# "Extract ClaimGraphValidator class and unify derived_from DAG traversals, numeric grounding, and primary quote verification across claims.py, text_claims.py, review.py, and evidence.py":
# https://github.com/dmitry-ai/harness/issues/62
# @used-by :func:`agent_tools.claims._verify_quote()`
# @used-by :func:`evidence_issues()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_evidence_loader_reuses_saved_extracted_html_and_caches_fragment_parse()`
def verify_saved_quote(root, source, quote, *, mode='exact', expected_hash=None, require_hash=False, observation=None, documentation=False, exception=None, locator=None, require_bound_observation=False, hash_error='Source hash differs from the referenced observation', absent_error='Quote is absent from the referenced source fragment'):
	# 2026-11-24
	# "Cache runtime settings and deduplicate evidence validation in hot paths":
	# https://github.com/dmitry-ai/harness/issues/227
	r = saved_source(root, source, observation, need_sections=bool(urldefrag(source)[1] or documentation))
	actual_hash = r.get('sha256') or r.get('meta', {}).get('body_sha256')
	if (require_hash or expected_hash) and expected_hash != actual_hash:
		raise ValueError(hash_error)
	if 'html' == r['kind']:
		text = verify_html_quote_scope(r, quote, mode, documentation=documentation, exception=exception, observation=observation, require_bound_observation=require_bound_observation)
	else:
		text = r['text']
		if documentation and (not r.get('fragment')) and (None is not locator or contains_quote(text, quote, mode)):
			raise ValueError('No-anchor documentation exception requires a verifiable saved HTML section')
	r['quantity_context'] = r['data']['text'] if 'html' == r['kind'] and (not r.get('fragment')) and (not documentation) else text
	if isinstance(locator, dict) and 'text' == locator.get('type'):
		if not contains_quote(text, locator['value'], mode):
			raise ValueError('Exact text locator is absent from primary source')
		text = locator['value']
	elif isinstance(locator, dict) and 'lines' == locator.get('type'):
		match = re.fullmatch('([1-9][0-9]*)-([1-9][0-9]*)', locator['value'])
		if not match or int(match[2]) < int(match[1]) or int(match[2]) > len(text.splitlines()):
			raise ValueError('Line locator must name an existing inclusive line range')
		text = '\n'.join(text.splitlines()[int(match[1]) - 1:int(match[2])])
	if not contains_quote(text, quote, mode):
		raise ValueError(absent_error)
	return r
