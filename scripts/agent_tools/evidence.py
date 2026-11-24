# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# 2026-11-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
# https://github.com/dmitry-ai/harness/issues/81
# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose experiments.py into ExperimentPlanStore, BrowserTraceInspector, and ExperimentRunValidator classes and unify raw_decode JSON object scanning":
# https://github.com/dmitry-ai/harness/issues/72
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract ClaimGraphValidator class and unify derived_from DAG traversals, numeric grounding, and primary quote verification across claims.py, text_claims.py, review.py, and evidence.py":
# https://github.com/dmitry-ai/harness/issues/62
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify quote normalization, MarkdownIt link/quote traversal, locale checks, numeric corpus tokenization, and Evidence loading across response_grounding.py, completion.py, source_grounding.py, claims.py, and review.py":
# https://github.com/dmitry-ai/harness/issues/59
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit
import hashlib
import html as html_lib
import json
import re
from .analysis import iter_arguments, SECTIONS
from .diagnostics import problem
from .research import inside, load_observation, extract_bytes
def pointer(*parts):
	return '/' + '/'.join((str(x).replace('~', '~0').replace('/', '~1') for x in parts)) if parts else ''
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
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/76
def local_file(root, reference):
	from .links import decode_file_uri
	from .path_registry import project_paths
	path = decode_file_uri(reference, reject_remote=True)
	pp = project_paths(root, exact_root=True)
	root_resolved = pp.root
	target = (pp.kb_dir / path).resolve()
	if not target.exists() and path.replace('\\', '/').lstrip('/').startswith('source/'):
		alt = (root_resolved / path.replace('\\', '/').lstrip('/')).resolve()
		if alt.is_relative_to(pp.source_dir):
			target = alt
	if not (target.is_relative_to(root_resolved) or target.is_relative_to(pp.kb_dir.resolve())):
		raise ValueError('Source path escapes the project; copy authorized primary evidence into Evidence first')
	r = target
	return r
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
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Cache runtime settings and deduplicate evidence validation in hot paths":
# https://github.com/dmitry-ai/harness/issues/227
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
			from .upwork_data import extract_attachment_markdown
			md_text = extract_attachment_markdown(file, raw)
			if fragment:
				md_text = _markdown_section(md_text, fragment)
			plain_text = re.sub('\\[([^\\]]+)\\]\\([^)]+\\)', '\\1', md_text).replace('**', '')
			r = {'kind': 'text', 'text': md_text + '\n' + plain_text, 'fragment': unquote(fragment), 'file': file, 'sha256': hashlib.sha256(raw).hexdigest()}
	else:
		from .evidence_loader import load_observation_content, resolve_http_observation
		obs_ref, meta = resolve_http_observation(root, base, observation)
		r = load_observation_content(root, obs_ref, meta, fragment=fragment, need_sections=need_sections)
	return r
def contains_quote(text, quote, mode='exact'):
	if 'exact' == mode:
		r = quote in text
	elif 'whitespace' != mode:
		raise ValueError('quote_match must be exact or whitespace')
	else:
		r = ' '.join(quote.split()) in ' '.join(text.split())
	return r
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
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
		from .claims import evidence_contract_issues
		issues.extend(evidence_contract_issues(root, value, skip_structural=skip_structural))
		r = issues
	return r
def source_reference(root, file, parts=()):
	from .path_registry import project_paths
	kb_dir = project_paths(root, exact_root=True).kb_dir.resolve()
	file = inside(kb_dir, file)
	r = file.relative_to(kb_dir).as_posix() + ('#' + pointer(*parts) if parts else '')
	return r
def verify_html_quote_scope(saved, quote, mode='exact', *, documentation=False, exception=None, observation=None, require_bound_observation=False) -> str:
	from .research import classify_html_challenge
	data, fragment = (saved['data'], saved.get('fragment'))
	is_md = bool(saved.get('is_markdown'))
	meta_status = (saved.get('meta') or {}).get('status')
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
def verify_saved_quote(root, source, quote, *, mode='exact', expected_hash=None, require_hash=False, observation=None, documentation=False, exception=None, locator=None, require_bound_observation=False, hash_error='Source hash differs from the referenced observation', absent_error='Quote is absent from the referenced source fragment'):
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
