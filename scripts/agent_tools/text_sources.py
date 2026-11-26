# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urlsplit
from .claims import contract_issues, evidence_contract_issues
from .links import check_network, references, readable_reference
from .storage import locked, read_addressed_json, replace_bytes, write_immutable_bytes
from .text_claims import registry_path, subset, evidence_inputs
from .text_core import Finding, scan
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
SOURCE_MAX_AGE = 86400
# @used-by :func:`_evaluate()`
# @used-by :func:`probe_links()`
# @used-by :func:`save_source_check()`
def _attempt(root, candidate, url, observation, reference, *, read_only=False):
	from .research import load_observation, json_data
	from .text_claims import digest
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .text_workflow import _folder
	url = readable_reference(url)
	folder = _folder(root) / 'sources'
	key = digest(url.encode('utf-8'))
	index = folder / (key + '-latest.json')
	with locked(folder / 'attempts.lock'):
		previous = json.loads(index.read_text(encoding='utf-8')) if index.exists() else None
		if previous:
			actual = load_observation(root, previous['observation'])
			if actual['observed_at'] != previous['observed_at'] or urldefrag(url)[0] != readable_reference(actual['url']):
				raise ValueError('Latest source index differs from its primary observation')
		if read_only:
			r = previous
		else:
			meta = load_observation(root, observation)
			when = datetime.fromisoformat(meta['observed_at'])
			if None is when.tzinfo or when > datetime.now(timezone.utc):
				raise ValueError('A source attempt needs its nonfuture timezone-aware observation time')
			value = {'observed_at': meta['observed_at'], 'observation': observation, 'reference': reference, 'candidate_sha256': digest(candidate.encode('utf-8'))}
			if None is previous or datetime.fromisoformat(value['observed_at']) >= datetime.fromisoformat(previous['observed_at']):
				replace_bytes(index, json_data(value))
			r = previous
	return r
# @used-by :func:`_evaluate()`
# @used-by :func:`probe_links()`
# @used-by :func:`save_source_check()`
# @used-by :func:`validate_source_checks()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_unicode_address_and_encoded_markdown_destination_share_one_identity()`
def source_urls(text):
	prose = '\n'.join((line.raw for line in scan(text) if line.kind in ('prose', 'heading')))
	r = list(dict.fromkeys((readable_reference(url) for url in references(prose)[0] if url.startswith(('http://', 'https://')))))
	return r
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`read_source_check()`
# @used-by :func:`save_source_check()`
def _evaluate(root, candidate, spec):
	from .claims import _manifest_primary, _verify_quote
	from .evidence import local_file
	from .research import load_observation, inside
	from .text_claims import digest
	from .upwork_data import extract_upwork_job_url_id
	if not isinstance(spec, dict) or not isinstance(spec.get('url'), str) or readable_reference(spec['url']) not in source_urls(candidate):
		raise ValueError('Source check must name an exact external URL in this candidate')
	if spec.get('currency') not in ('current', 'historical') or not isinstance(spec.get('currency_basis'), str) or (not spec['currency_basis'].strip()):
		raise ValueError('Declare current/historical currency and its applicability basis')
	if 'historical' == spec['currency'] and (not isinstance(spec.get('edition'), str) or not spec['edition'].strip()):
		raise ValueError('A historical source requires its explicit edition; it is not a current-source fallback')
	ref = spec.get('evidence')
	# 2026-11-16
	# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
	# https://github.com/dmitry-ai/harness/issues/81
	if isinstance(ref, dict) and 'intake' == ref.get('kind'):
		url_base, url_frag = urldefrag(spec['url'].strip())
		if url_frag or urlsplit(url_base).query:
			raise ValueError('Intake job snapshot cannot verify URL query parameters or HTML fragments')
		cited_job_id = extract_upwork_job_url_id(spec['url'])
		if not cited_job_id:
			raise ValueError('Intake source-check provenance applies only to the registered Upwork job URL of this project')
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		from .path_registry import project_paths
		pp = project_paths(root, exact_root=True)
		state_file = pp.project_json
		state = json.loads(state_file.read_text(encoding='utf-8-sig')) if state_file.is_file() else {}
		if not isinstance(state, dict) or True is not state.get('initialized') or state.get('job_id') != cited_job_id:
			raise ValueError('Cited Upwork job URL does not match the registered initialized project job_id')
		if not isinstance(ref.get('manifest'), str) or not ref['manifest'].strip() or (not isinstance(ref.get('source_sha256'), str)) or (not ref['source_sha256'].strip()) or (not isinstance(ref.get('quote'), str)) or (not ref['quote'].strip()) or (not isinstance(ref.get('locator'), dict)) or (ref['locator'].get('type') not in ('json_pointer', 'text', 'lines')) or (not isinstance(ref['locator'].get('value'), str)) or (not ref['locator']['value']) or (False is not ref.get('documentation', False)):
			raise ValueError('Intake source-check requires manifest, source_sha256, quote, non-documentation flag and json_pointer/text/lines locator')
		root_resolved = pp.root
		manifest_file = local_file(root, ref['manifest'])
		manifest_doc = json.loads(manifest_file.read_text(encoding='utf-8-sig'))
		raw_src = ref.get('source')
		if isinstance(raw_src, str) and urlsplit(raw_src).scheme.lower() in ('http', 'https'):
			if readable_reference(raw_src) != readable_reference(spec['url']):
				raise ValueError('Intake evidence URL differs from the exact cited resource')
			local_source = None
		elif isinstance(raw_src, str) and raw_src.strip():
			local_source = raw_src
		else:
			local_source = None
		if None is local_source:
			if isinstance(manifest_doc, dict) and isinstance(manifest_doc.get('entries'), list):
				matched_entry = next((e for e in manifest_doc['entries'] if isinstance(e, dict) and 'identity' == e.get('transform') and 'source.json' == e.get('original_relative_provenance') and (e.get('sha256') == ref['source_sha256']) and isinstance(e.get('durable_file'), str)), None)
				if not matched_entry:
					raise ValueError('Intake receipt has no matching source.json entry for this Upwork job snapshot')
				local_source = inside(root_resolved, matched_entry['durable_file']).relative_to(pp.kb_dir).as_posix()
			else:
				local_source = ref['manifest']
		src_file = local_file(root, local_source)
		if '.json' != src_file.suffix.lower():
			raise ValueError('Intake source-check for an Upwork job URL requires the JSON job snapshot, not plain-text request notes')
		snap_file = inside(root_resolved, state['snapshot']) if isinstance(state.get('snapshot'), str) and state['snapshot'].strip() else None
		if manifest_file != snap_file and isinstance(manifest_doc, dict) and isinstance(manifest_doc.get('entries'), list):
			matched_src = next((e for e in manifest_doc['entries'] if isinstance(e, dict) and isinstance(e.get('durable_file'), str) and (inside(root_resolved, e['durable_file']) == src_file) and (e.get('sha256') == ref['source_sha256'])), None)
			if not matched_src or 'source.json' != matched_src.get('original_relative_provenance'):
				raise ValueError('Intake source-check for an Upwork job URL requires source.json provenance')
		local_ref = {**ref, 'kind': 'intake', 'source': local_source, 'documentation': False}
		_manifest_primary(root, local_ref)
		_verify_quote(root, local_ref)
		inputs = evidence_inputs(root, {'facts': [{'evidence': [local_ref]}]})
		snap_doc = json.loads(src_file.read_text(encoding='utf-8-sig'))
		if not isinstance(snap_doc, dict) or snap_doc.get('job_id') != cited_job_id:
			raise ValueError('Intake job snapshot job_id differs from the cited Upwork job URL')
		snap_observed = snap_doc.get('captured_at') or snap_doc.get('observed_at')
		base_cited = urldefrag(readable_reference(spec['url']))[0]
		return {'url': readable_reference(spec['url']), 'requested_url': base_cited, 'final_url': base_cited, 'method': 'INTAKE_SNAPSHOT', 'http_status': None, 'observed_at': snap_observed if isinstance(snap_observed, str) and snap_observed else None, 'body_sha256': local_ref['source_sha256'], 'currency': spec['currency'], 'edition': spec.get('edition'), 'inputs': inputs}
	if not isinstance(ref, dict) or not isinstance(ref.get('source'), str) or readable_reference(ref['source']) != readable_reference(spec['url']) or (not isinstance(ref.get('quote'), str)) or (not ref['quote'].strip()) or (not isinstance(ref.get('locator'), dict)) or (ref['locator'].get('type') not in ('text', 'anchor', 'lines', 'json_pointer')) or (not isinstance(ref['locator'].get('value'), str)) or (not ref['locator']['value']) or (type(ref.get('documentation')) is not bool) or (not ref.get('observation')):
		raise ValueError('Use exact URL, quote, locator, explicit documentation flag and saved HTTP/DOM observation')
	if ref['documentation'] and (not urldefrag(spec['url'])[1]) and ('anchor' == ref['locator']['type']):
		raise ValueError('Put the verified documentation anchor in the cited URL itself')
	meta = load_observation(root, ref['observation'])
	if readable_reference(meta['url']) != readable_reference(urldefrag(spec['url'])[0]):
		raise ValueError('Requested URL differs from the exact cited resource')
	latest = _attempt(root, candidate, spec['url'], None, None, read_only=True)
	if latest and datetime.fromisoformat(latest['observed_at']) > datetime.fromisoformat(meta['observed_at']):
		recent = load_observation(root, latest['observation'])
		if recent.get('error') or ('dom' != recent.get('kind') and (not 200 <= (recent.get('status') or 0) < 300)) or recent['body_sha256'] != meta['body_sha256'] or (recent['final_url'] != meta['final_url']):
			raise ValueError('A newer conflicting source observation exists for this candidate; resolve it instead of reusing an older success')
	expected = spec.get('expected_final_url', urldefrag(spec['url'])[0])
	if readable_reference(urldefrag(meta['final_url'])[0]) != readable_reference(urldefrag(expected)[0]):
		raise ValueError('Final URL differs from the intended resource; verify redirects explicitly')
	observed = datetime.fromisoformat(meta['observed_at'])
	if None is observed.tzinfo or observed > datetime.now(timezone.utc):
		raise ValueError('Source observation needs a nonfuture timezone-aware timestamp')
	if 'current' == spec['currency'] and SOURCE_MAX_AGE < (datetime.now(timezone.utc) - observed).total_seconds():
		raise ValueError('Current-source observation is older than 24 hours; collect a justified refresh')
	_verify_quote(root, ref, observation=ref['observation'])
	inputs = evidence_inputs(root, {'facts': [{'evidence': [ref]}]})
	if 'dom' == meta.get('kind'):
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		from .path_registry import project_paths
		identity = spec.get('cdp_identity')
		if not isinstance(identity, str) or not identity.strip():
			raise ValueError('DOM fallback requires its captured CDP identity receipt')
		path = inside(project_paths(root, exact_root=True).kb_dir, identity)
		# 2026-11-13
		# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
		# https://github.com/dmitry-ai/harness/issues/63
		raw, data = read_addressed_json(path, stem_match=True, error_msg='DOM identity does not bind this exact observation')
		# 2026-11-16
		# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
		# https://github.com/dmitry-ai/harness/issues/81
		prof = data.get('profile')
		if 1 != data.get('schema_version') or any((not isinstance(data.get(key), str) or not data[key] for key in ('target_id', 'browser_websocket', 'observed_at'))) or ('read-only-dom' != meta.get('collector')) or ('READ_DOM' != meta.get('method')) or (not isinstance(prof, dict)) or ('verified' != prof.get('status')):
			raise ValueError('DOM identity does not bind this exact observation')
		sid = data.get('session_id')
		req_scope = meta.get('request_scope') or ''
		ctx_sid = meta.get('conditions', {}).get('reported_context', {}).get('session_id')
		expected_tab_scope = f"CDP-session:{sid}:tab:{data.get('target_id')}:identity:{identity}"
		mode_tab = isinstance(sid, str) and bool(sid) and (ctx_sid == sid) and (req_scope == expected_tab_scope) and (meta.get('cdp_identity') in (None, identity)) and (meta.get('cdp_identity_sha256') in (None, digest(raw)))
		mode_auth = isinstance(sid, str) and bool(sid) and (ctx_sid == sid) and (req_scope == f'CDP-session:{sid}' or (not req_scope.startswith('CDP-session:'))) and (data.get('target_mode') in ('hidden_session_target', 'm2a_extension_background_tab')) and (meta.get('cdp_identity') == identity) and (meta.get('cdp_identity_sha256') in (None, digest(raw)))
		mode_public = (None is sid) and (None is ctx_sid) and bool(req_scope) and (not req_scope.startswith('CDP-session:')) and (data.get('target_mode') in ('ephemeral_headless_context', 'hidden_session_target')) and (meta.get('cdp_identity') == identity) and (meta.get('cdp_identity_sha256') in (None, digest(raw)))
		if not (mode_tab or mode_auth or mode_public):
			raise ValueError('DOM identity does not bind this exact observation')
		inputs[path.relative_to(Path(root).resolve()).as_posix()] = digest(raw)
	return {'url': readable_reference(spec['url']), 'requested_url': meta['url'], 'final_url': meta['final_url'], 'method': meta['method'], 'http_status': meta['status'], 'observed_at': meta['observed_at'], 'body_sha256': meta['body_sha256'], 'currency': spec['currency'], 'edition': spec.get('edition'), 'inputs': inputs}
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.check_and_review()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.saved()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_full_native_review_fixture_requires_and_preserves_source_assessments()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
def save_source_check(root, candidate, spec):
	from .research import json_data
	from .text_claims import digest
	from .text_workflow import _folder
	result = {'schema_version': 1, 'candidate_sha256': digest(candidate.encode('utf-8')), 'spec': spec}
	try:
		result.update(_evaluate(root, candidate, spec), valid=True, issues=[])
	except (OSError, ValueError, KeyError, TypeError) as exc:
		result.update(valid=False, issues=[str(exc)], inputs={})
	raw = json_data(result)
	# 2026-11-13
	# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
	# https://github.com/dmitry-ai/harness/issues/63
	path = write_immutable_bytes(_folder(root) / 'sources' / (digest(raw) + '-source.json'), raw, diff_error='Immutable source receipt differs')
	try:
		# 2026-11-16
		# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
		# https://github.com/dmitry-ai/harness/issues/81
		if isinstance(spec, dict) and isinstance(spec.get('url'), str) and isinstance(spec.get('evidence'), dict) and ('intake' != spec['evidence'].get('kind')) and spec['evidence'].get('observation') and (readable_reference(spec['url']) in source_urls(candidate)):
			_attempt(root, candidate, spec['url'], spec['evidence']['observation'], path.relative_to(Path(root).resolve()).as_posix())
	except (OSError, ValueError, KeyError, TypeError):
		pass
	return {**result, 'source_check': path.relative_to(Path(root).resolve()).as_posix()}
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# 2026-11-23
# "Unify local Tier 0 source hydration, HTTP/DOM Evidence observation loading, CommonMark helpers, and file:// path parsing across source_grounding.py, response_grounding.py, evidence.py, links.py, text_sources.py, and markdown_links.py":
# https://github.com/dmitry-ai/harness/issues/76
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :meth:`test_historical_admission.HistoricalAdmissionTests.test_later_conflicting_probe_rejects_new_publication_but_preserves_history()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_a_later_failed_probe_cannot_be_overridden_by_minting_an_older_success()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_changing_candidate_does_not_erase_a_later_failure_of_the_same_url()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_later_failure_invalidates_apply_and_an_already_applied_gate()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m2_remote_text_markdown_content_negotiation_and_explicit_heading_ids()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_real_http_failure_and_redirect_are_saved_once_per_base_url()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_valid_dom_capture_identity_can_resolve_the_http_channel_failure()`
def probe_links(root, candidate, *, fetcher=None):
	from .evidence_loader import probe_observation_status
	from .research import collect, json_data
	from .text_claims import digest
	from .text_workflow import _folder
	observed, results, findings = ({}, [], [])
	for url in source_urls(candidate):
		base, fragment = urldefrag(url)
		if base not in observed:
			observed[base] = collect(root, base, scope='client-text-source', max_age=0, refresh_reason='Explicit network check of the exact client-text candidate', fetcher=fetcher)
		meta = observed[base]
		status = probe_observation_status(root, meta, base, fragment)
		result = {'url': url, 'status': status, 'observation': meta['observation'], 'final_url': meta['final_url'], 'http_status': meta['status']}
		raw = json_data({'schema_version': 1, 'candidate_sha256': digest(candidate.encode()), **result})
		# 2026-11-13
		# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
		# https://github.com/dmitry-ai/harness/issues/63
		path = write_immutable_bytes(_folder(root) / 'sources' / (digest(raw) + '-probe.json'), raw, diff_error='Immutable source probe differs')
		reference = path.relative_to(Path(root).resolve()).as_posix()
		_attempt(root, candidate, url, meta['observation'], reference)
		results.append({**result, 'probe': reference})
		if 'http-ok' != status:
			findings.append(Finding('error', 'SOURCE-UNVERIFIED', 1, url + ': ' + status))
	return {'results': results, 'findings': findings}
# @used-by :func:`agent_tools.text_review._source_reviews()`
# @used-by :func:`validate_source_checks()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_plain_authored_verified_objects_and_changed_candidates_are_rejected()`
def read_source_check(root, candidate, reference):
	from .research import inside
	from .text_claims import digest
	path = inside(root, reference)
	# 2026-11-13
	# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
	# https://github.com/dmitry-ai/harness/issues/63
	raw, value = read_addressed_json(path, suffix='-source.json', error_msg='Invalid or changed immutable source receipt')
	if 1 != value.get('schema_version'):
		raise ValueError('Invalid or changed immutable source receipt')
	if value.get('candidate_sha256') != digest(candidate.encode('utf-8')) or True is not value.get('valid'):
		raise ValueError('Source receipt is failed or belongs to another candidate')
	actual = _evaluate(root, candidate, value['spec'])
	if any((value.get(key) != actual[key] for key in actual)):
		raise ValueError('Source bytes or provenance changed since the source receipt')
	return {**value, 'source_check': reference, 'inputs': {**actual['inputs'], path.relative_to(Path(root).resolve()).as_posix(): digest(raw)}}
# 2026-11-03
# "Replace persistent journal daemon with foreground-only idempotent reconciliation":
# https://github.com/dmitry-ai/harness/issues/41
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.applied_integrity()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m5_intake_job_snapshot_source_check_provenance_and_attempt_isolation()`
def source_integrity(root, candidate, reference):
	from .research import inside
	from .text_claims import digest
	root_p = Path(root).resolve()
	path = inside(root_p, reference)
	# 2026-11-13
	# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
	# https://github.com/dmitry-ai/harness/issues/63
	raw, value = read_addressed_json(path, suffix='-source.json', error_msg='Historical source receipt is failed, changed or belongs to another candidate')
	if 1 != value.get('schema_version') or True is not value.get('valid') or value.get('candidate_sha256') != digest(candidate.encode('utf-8')):
		raise ValueError('Historical source receipt is failed, changed or belongs to another candidate')
	inputs = value.get('inputs')
	if not isinstance(inputs, dict) or not inputs:
		raise ValueError('Historical source receipt has no admitted primary inputs')
	for name, expected in inputs.items():
		if digest(inside(root_p, name).read_bytes()) != expected:
			raise ValueError('Historical source evidence changed: ' + name)
	return {**value, 'source_check': reference, 'inputs': {**inputs, path.relative_to(root_p).as_posix(): digest(raw)}}
# 2026-10-23
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace._gate_target()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.check()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_unicode_address_and_encoded_markdown_destination_share_one_identity()`
def validate_source_checks(root, candidate, records):
	required = set(source_urls(candidate))
	inputs, checks, seen, issues = ({}, [], set(), [])
	if not isinstance(records, list):
		r = {'issues': [{'code': 'text.source_checks', 'message': 'source_checks must list immutable source receipt paths'}], 'inputs': {}, 'checks': []}
	else:
		for reference in records:
			try:
				if not isinstance(reference, str):
					raise ValueError('An authored source-check object cannot replace a verified receipt')
				value = read_source_check(root, candidate, reference)
				if value['url'] in seen:
					raise ValueError('Duplicate source coverage')
				seen.add(value['url'])
				inputs.update(value['inputs'])
				checks.append(reference)
			except (OSError, ValueError, KeyError, TypeError) as exc:
				issues.append({'code': 'text.source_checks', 'message': str(exc), 'source_check': str(reference)})
		for url in sorted(required - seen):
			issues.append({'code': 'text.source_missing', 'message': 'External source needs a candidate-bound quote/anchor receipt: ' + url})
		r = {'issues': issues, 'inputs': inputs, 'checks': checks}
	return r
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# @used-by :func:`agent_tools.text_cli.main()`
def check_claim_sources(root, identifiers, *, reference=None):
	path = registry_path(root, reference)
	selected = subset(json.loads(path.read_text(encoding='utf-8-sig')), identifiers)
	issues = contract_issues(selected)
	if not issues:
		issues.extend(evidence_contract_issues(root, selected))
	r = {'valid': not issues, 'issues': issues, 'inputs': evidence_inputs(root, selected) if not issues else {}, 'coverage': 'Saved primary bytes, quotes, locators and declared method contracts; source applicability and entailment require authored review.'}
	return r
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_network_source_checks_distinguish_missing_anchor_and_skip_inline_code()`
def check_links(text, *, fetcher=None):
	prose = '\n'.join((line.raw for line in scan(text) if 'prose' == line.kind))
	urls = references(prose)[0]
	urls = list(dict.fromkeys((url.rstrip('.,;') for url in urls if url.startswith(('https://', 'http://')))))
	results = check_network(urls, fetcher=fetcher)
	results += check_network(urls, anchors=True, fetcher=fetcher)
	allowed = {'http-ok', 'found-in-source'}
	r = [Finding('error', 'SOURCE-UNVERIFIED', 1, f"{result['url']}: {result['status']}; save an authorized DOM/console observation if the HTML cannot establish the target") for result in results if result['status'] not in allowed]
	return r
