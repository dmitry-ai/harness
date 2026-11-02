# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Separate publication admission from historical integrity verification":
# https://github.com/dmitry-ai/harness/issues/41
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag
from .claims import contract_issues, evidence_contract_issues
from .links import check_network, references, readable_reference
from .text_claims import registry_path, subset, evidence_inputs
from .text_core import Finding, scan
SOURCE_MAX_AGE = 86400
def _attempt(root, candidate, url, observation, reference, *, read_only=False):
	from .research import load_observation, json_data
	from .text_claims import digest
	from .storage import locked, replace_bytes
	url = readable_reference(url)
	folder = Path(root).resolve() / 'ꘖ/data/texts/sources'
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
def source_urls(text):
	prose = '\n'.join((line.raw for line in scan(text) if line.kind in ('prose', 'heading')))
	r = list(dict.fromkeys((readable_reference(url) for url in references(prose)[0] if url.startswith(('http://', 'https://')))))
	return r
def _evaluate(root, candidate, spec):
	from .claims import _verify_quote
	from .research import load_observation, inside
	from .text_claims import digest
	if not isinstance(spec, dict) or not isinstance(spec.get('url'), str) or readable_reference(spec['url']) not in source_urls(candidate):
		raise ValueError('Source check must name an exact external URL in this candidate')
	ref = spec.get('evidence')
	if not isinstance(ref, dict) or not isinstance(ref.get('source'), str) or readable_reference(ref['source']) != readable_reference(spec['url']) or (not isinstance(ref.get('quote'), str)) or (not ref['quote'].strip()) or (not isinstance(ref.get('locator'), dict)) or (ref['locator'].get('type') not in ('text', 'anchor', 'lines', 'json_pointer')) or (not isinstance(ref['locator'].get('value'), str)) or (not ref['locator']['value']) or (type(ref.get('documentation')) is not bool) or (not ref.get('observation')):
		raise ValueError('Use exact URL, quote, locator, explicit documentation flag and saved HTTP/DOM observation')
	if spec.get('currency') not in ('current', 'historical') or not isinstance(spec.get('currency_basis'), str) or (not spec['currency_basis'].strip()):
		raise ValueError('Declare current/historical currency and its applicability basis')
	if 'historical' == spec['currency'] and (not isinstance(spec.get('edition'), str) or not spec['edition'].strip()):
		raise ValueError('A historical source requires its explicit edition; it is not a current-source fallback')
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
	if 'current' == spec['currency'] and (datetime.now(timezone.utc) - observed).total_seconds() > SOURCE_MAX_AGE:
		raise ValueError('Current-source observation is older than 24 hours; collect a justified refresh')
	_verify_quote(root, ref, observation=ref['observation'])
	inputs = evidence_inputs(root, {'facts': [{'evidence': [ref]}]})
	if 'dom' == meta.get('kind'):
		identity = spec.get('cdp_identity')
		if not isinstance(identity, str):
			raise ValueError('DOM fallback requires its captured CDP identity receipt')
		path = inside(Path(root).resolve() / 'ꘖ/KB', identity)
		raw = path.read_bytes()
		data = json.loads(raw)
		if 1 != data.get('schema_version') or any((not isinstance(data.get(key), str) or not data[key] for key in ('session_id', 'target_id', 'browser_websocket', 'observed_at'))) or path.stem != digest(raw) or ('read-only-dom' != meta.get('collector')) or ('READ_DOM' != meta.get('method')) or (meta.get('conditions', {}).get('reported_context', {}).get('session_id') != data['session_id']) or (meta.get('request_scope') != f"CDP-session:{data.get('session_id')}:tab:{data.get('target_id')}:identity:{identity}"):
			raise ValueError('DOM identity does not bind this exact observation')
		inputs[path.relative_to(Path(root).resolve()).as_posix()] = digest(raw)
	r = {'url': readable_reference(spec['url']), 'requested_url': meta['url'], 'final_url': meta['final_url'], 'method': meta['method'], 'http_status': meta['status'], 'observed_at': meta['observed_at'], 'body_sha256': meta['body_sha256'], 'currency': spec['currency'], 'edition': spec.get('edition'), 'inputs': inputs}
	return r
def save_source_check(root, candidate, spec):
	from .text_claims import digest
	from .text_workflow import _folder, _immutable
	from .research import json_data
	result = {'schema_version': 1, 'candidate_sha256': digest(candidate.encode('utf-8')), 'spec': spec}
	try:
		result.update(_evaluate(root, candidate, spec), valid=True, issues=[])
	except (OSError, ValueError, KeyError, TypeError) as exc:
		result.update(valid=False, issues=[str(exc)], inputs={})
	raw = json_data(result)
	path = _immutable(_folder(root) / 'sources' / (digest(raw) + '-source.json'), raw)
	try:
		if isinstance(spec, dict) and isinstance(spec.get('url'), str) and (readable_reference(spec['url']) in source_urls(candidate)):
			_attempt(root, candidate, spec['url'], spec['evidence']['observation'], path.relative_to(Path(root).resolve()).as_posix())
	except (OSError, ValueError, KeyError, TypeError):
		pass
	r = {**result, 'source_check': path.relative_to(Path(root).resolve()).as_posix()}
	return r
def probe_links(root, candidate, *, fetcher=None):
	from .research import collect, json_data, extract_bytes
	from .text_workflow import _folder, _immutable
	from .text_claims import digest
	from urllib.parse import unquote
	observed, results, findings = ({}, [], [])
	for url in source_urls(candidate):
		base, fragment = urldefrag(url)
		if base not in observed:
			observed[base] = collect(root, base, scope='client-text-source', max_age=0, refresh_reason='Explicit network check of the exact client-text candidate', fetcher=fetcher)
		meta = observed[base]
		status = 'http-ok'
		if meta.get('error') or not 200 <= (meta.get('status') or 0) < 300:
			status = 'unavailable'
		elif urldefrag(meta['final_url'])[0] != base:
			status = 'redirect-unverified'
		elif meta['content_type'] in ('text/html', 'application/xhtml+xml'):
			from .evidence import local_file
			body = local_file(root, meta['observation']).with_name('response.bin').read_bytes()
			data = extract_bytes(body, meta['content_type'], 'html', meta.get('charset') or 'utf-8')
			if data.get('browser_check_required'):
				status = 'browser-check-required'
			elif fragment and (unquote(fragment) not in data['anchors'] or unquote(fragment) in data.get('ambiguous_anchors', [])):
				status = 'anchor-unverified'
		elif fragment:
			status = 'anchor-unverified'
		result = {'url': url, 'status': status, 'observation': meta['observation'], 'final_url': meta['final_url'], 'http_status': meta['status']}
		raw = json_data({'schema_version': 1, 'candidate_sha256': digest(candidate.encode()), **result})
		path = _immutable(_folder(root) / 'sources' / (digest(raw) + '-probe.json'), raw)
		reference = path.relative_to(Path(root).resolve()).as_posix()
		_attempt(root, candidate, url, meta['observation'], reference)
		results.append({**result, 'probe': reference})
		if 'http-ok' != status:
			findings.append(Finding('error', 'SOURCE-UNVERIFIED', 1, url + ': ' + status))
	r = {'results': results, 'findings': findings}
	return r
def read_source_check(root, candidate, reference):
	from .text_claims import digest
	from .research import inside
	path = inside(root, reference)
	raw = path.read_bytes()
	value = json.loads(raw)
	if path.name != digest(raw) + '-source.json' or 1 != value.get('schema_version'):
		raise ValueError('Invalid or changed immutable source receipt')
	if value.get('candidate_sha256') != digest(candidate.encode('utf-8')) or True is not value.get('valid'):
		raise ValueError('Source receipt is failed or belongs to another candidate')
	actual = _evaluate(root, candidate, value['spec'])
	if any((value.get(key) != actual[key] for key in actual)):
		raise ValueError('Source bytes or provenance changed since the source receipt')
	r = {**value, 'source_check': reference, 'inputs': {**actual['inputs'], path.relative_to(Path(root).resolve()).as_posix(): digest(raw)}}
	return r
def source_integrity(root, candidate, reference):
	from .text_claims import digest
	from .research import inside
	root = Path(root).resolve()
	path = inside(root, reference)
	raw = path.read_bytes()
	value = json.loads(raw)
	if path.name != digest(raw) + '-source.json' or 1 != value.get('schema_version') or True is not value.get('valid') or value.get('candidate_sha256') != digest(candidate.encode('utf-8')):
		raise ValueError('Historical source receipt is failed, changed or belongs to another candidate')
	inputs = value.get('inputs')
	if not isinstance(inputs, dict) or not inputs:
		raise ValueError('Historical source receipt has no admitted primary inputs')
	for name, expected in inputs.items():
		if digest(inside(root, name).read_bytes()) != expected:
			raise ValueError('Historical source evidence changed: ' + name)
	return {**value, 'source_check': reference, 'inputs': {**inputs, path.relative_to(root).as_posix(): digest(raw)}}
# 2026-10-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement turn-completion contract, journal watcher, primary source admission, and Codex root AGENTS.md loader":
# https://github.com/dmitry-ai/harness/issues/16
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
def check_claim_sources(root, identifiers, *, reference='ꘖ/KB/TextClaims.json'):
	path = registry_path(root, reference)
	selected = subset(json.loads(path.read_text(encoding='utf-8-sig')), identifiers)
	issues = contract_issues(selected)
	if not issues:
		issues.extend(evidence_contract_issues(root, selected))
	r = {'valid': not issues, 'issues': issues, 'inputs': evidence_inputs(root, selected) if not issues else {}, 'coverage': 'Saved primary bytes, quotes, locators and declared method contracts; source applicability and entailment require authored review.'}
	return r
def check_links(text, *, fetcher=None):
	prose = '\n'.join((line.raw for line in scan(text) if 'prose' == line.kind))
	urls = references(prose)[0]
	urls = list(dict.fromkeys((url.rstrip('.,;') for url in urls if url.startswith(('https://', 'http://')))))
	results = check_network(urls, fetcher=fetcher)
	results += check_network(urls, anchors=True, fetcher=fetcher)
	allowed = {'http-ok', 'found-in-source'}
	r = [Finding('error', 'SOURCE-UNVERIFIED', 1, f"{result['url']}: {result['status']}; save an authorized DOM/console observation if the HTML cannot establish the target") for result in results if result['status'] not in allowed]
	return r
