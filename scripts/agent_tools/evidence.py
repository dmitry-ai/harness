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
import json
import re
from .analysis import iter_arguments, SECTIONS
from .diagnostics import problem
from .research import inside, load_observation, extract_bytes
def pointer(*parts):
	return '/' + '/'.join((str(x).replace('~', '~0').replace('/', '~1') for x in parts)) if parts else ''
def resolve_pointer(value, fragment):
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
			if isinstance(value, list):
				if not re.fullmatch('0|[1-9][0-9]*', key):
					raise ValueError('Array pointer must be a nonnegative canonical index')
				value = value[int(key)]
			elif isinstance(value, dict):
				value = value[key]
			else:
				raise ValueError('Pointer traverses a scalar')
		r = value
	return r
def local_file(root, reference):
	reference = urldefrag(reference)[0]
	parsed = urlsplit(reference)
	if 'file' != parsed.scheme:
		path = unquote(reference)
	else:
		path = unquote(parsed.path)
		if re.match('^/[A-Za-z]:/', path):
			path = path[1:]
		if parsed.netloc and 'localhost' != parsed.netloc:
			raise ValueError('Remote file URI is not a local project source')
	root_resolved = Path(root).resolve()
	target = (root_resolved / 'ꘖ/KB' / path).resolve()
	if not target.exists() and path.replace('\\', '/').lstrip('/').startswith('source/'):
		alt = (root_resolved / path.replace('\\', '/').lstrip('/')).resolve()
		if alt.is_relative_to(root_resolved / 'source'):
			target = alt
	if not target.is_relative_to(root_resolved):
		raise ValueError('Source path escapes the project; copy authorized primary evidence into Evidence first')
	r = target
	return r
def _markdown_section(text: str, fragment: str) -> str:
	from markdown_it import MarkdownIt
	tokens = MarkdownIt('commonmark').parse(text)
	lines, headings, used = (text.splitlines(keepends=True), [], set())
	for index, token in enumerate(tokens):
		if 'heading_open' != token.type:
			continue
		inline = tokens[index + 1]
		title = ''.join((t.content for t in inline.children or [] if t.type in ('text', 'code_inline', 'image')))
		slug = re.sub('[^\\w\\- ]', '', title.lower()).replace(' ', '-')
		ident, number = (slug, 0)
		while ident in used:
			number += 1
			ident = f'{slug}-{number}'
		used.add(ident)
		headings.append((ident, int(token.tag[1]), token.map[0]))
	match = next((i for i, h in enumerate(headings) if h[0] == unquote(fragment)), None)
	if None is match:
		raise ValueError('Markdown section anchor is absent')
	heading = headings[match]
	end = next((h[2] for h in headings[match + 1:] if h[1] <= heading[1]), len(lines))
	r = ''.join(lines[heading[2]:end])
	return r
def saved_source(root, source, observation=None):
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
		if not observation:
			index = Path(root) / 'ꘖ/data/http-index.json'
			candidates = json.loads(index.read_text(encoding='utf-8')).values() if index.exists() else []
			for candidate in candidates:
				meta = load_observation(root, candidate['observation'])
				if base in (meta['url'], meta['final_url']):
					observation = candidate['observation']
					break
		if not observation:
			raise FileNotFoundError('No saved HTTP/DOM observation; use saved primary evidence or collect the required source once')
		meta = load_observation(root, observation)
		if base not in (meta['url'], meta['final_url']):
			raise ValueError('Observation belongs to a different URL')
		if meta.get('error') or ('http' == meta.get('kind', 'http') and (not 200 <= meta['status'] < 300)):
			raise ValueError('Saved HTTP result is unavailable; use a different verification method')
		file = local_file(root, observation).parent / 'response.bin'
		body = file.read_bytes()
		if meta['content_type'] in ('text/html', 'application/xhtml+xml'):
			data = extract_bytes(body, meta['content_type'], 'html', meta.get('charset') or 'utf-8')
			r = {'kind': 'html', 'data': data, 'raw': body.decode(meta.get('charset') or 'utf-8', errors='replace'), 'fragment': unquote(fragment), 'meta': meta}
		else:
			text = body.decode(meta.get('charset') or 'utf-8', errors='replace')
			if not ('application/json' == meta['content_type'] or meta['content_type'].endswith('+json')):
				if fragment:
					raise ValueError('This source format does not support a verified fragment locator')
				r = {'kind': 'text', 'text': text, 'fragment': unquote(fragment), 'meta': meta}
			else:
				value = resolve_pointer(json.loads(text), fragment)
				text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
				r = {'kind': 'json', 'text': text, 'fragment': unquote(fragment), 'meta': meta}
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
def evidence_issues(root, value):
	if not isinstance(value, dict):
		r = [problem('analysis.object', '/', 'Analysis must be a JSON object')]
	else:
		issues = []
		for ident, field, argument, source in iter_arguments(value):
			if not isinstance(source, str) or not isinstance(argument.get('quote'), str):
				continue
			locator = argument.get('anchor_exception') if isinstance(argument.get('anchor_exception'), dict) else {}
			try:
				saved = saved_source(root, source, argument.get('observation') or locator.get('observation'))
				quote, mode = (argument['quote'], argument.get('quote_match', 'exact'))
				expected_hash = argument.get('source_sha256')
				actual_hash = saved.get('sha256') or saved.get('meta', {}).get('body_sha256')
				if expected_hash and expected_hash != actual_hash:
					raise ValueError('Source hash differs from the referenced observation')
				if 'html' == saved['kind']:
					verify_html_quote_scope(saved, quote, mode, documentation=bool(argument.get('documentation')), exception=locator)
				elif not contains_quote(saved['text'], quote, mode):
					raise ValueError('Quote is absent from the referenced source fragment')
				elif argument.get('documentation') and (not saved.get('fragment')):
					raise ValueError('No-anchor documentation exception requires a verifiable saved HTML section')
			except (OSError, ValueError, KeyError, IndexError, TypeError, UnicodeError) as exc:
				issues.append(problem('evidence.unconfirmed', field, str(exc), claim_id=ident, hint='Use the exact saved source and locator; keep the claim unverified until resolved'))
		for section in SECTIONS:
			for index, claim in enumerate(value.get(section, []) if isinstance(value.get(section), list) else []):
				if not isinstance(claim, dict) or claim.get('against') != []:
					continue
				gap = claim.get('counterevidence', {})
				reviewed = gap.get('reviewed_sources', []) if isinstance(gap, dict) else []
				for source in reviewed if isinstance(reviewed, list) else []:
					if not isinstance(source, str):
						continue
					try:
						if source.startswith(('http://', 'https://')):
							saved_source(root, source)
						else:
							file = local_file(root, source)
							if 'observation.json' == file.name:
								observation = load_observation(root, source)
								if 'not_found' == gap.get('status') and (observation.get('error') or ('http' == observation.get('kind', 'http') and (not 200 <= observation['status'] < 300))):
									raise ValueError('An unavailable observation establishes unavailable, not a completed search for counterevidence')
							elif not file.is_file():
								raise FileNotFoundError(source)
					except (OSError, ValueError, KeyError, TypeError) as exc:
						issues.append(problem('counterevidence.unconfirmed', f'/{section}/{index}/counterevidence', str(exc), claim_id=claim.get('id')))
		from .claims import evidence_contract_issues
		issues.extend(evidence_contract_issues(root, value))
		r = issues
	return r
def source_reference(root, file, parts=()):
	file = inside(Path(root) / 'ꘖ/KB', file)
	r = file.relative_to(Path(root).resolve() / 'ꘖ/KB').as_posix() + ('#' + pointer(*parts) if parts else '')
	return r
def verify_html_quote_scope(saved, quote, mode='exact', *, documentation=False, exception=None, observation=None, require_bound_observation=False) -> str:
	from .research import _CHALLENGE_RE
	data, fragment = (saved['data'], saved.get('fragment'))
	if data.get('browser_check_required') or _CHALLENGE_RE.search(data['text'] + saved['raw'][:8000]):
		raise ValueError('Challenge page requires browser verification; it cannot establish the intended page content')
	if fragment:
		if fragment not in data['anchors'] or fragment in data.get('ambiguous_anchors', []):
			raise ValueError('Primary anchor is absent or ambiguous')
		scopes = [h['content'] for h in data['sections'] if h.get('anchor') == fragment] or data['anchor_content'].get(fragment, [])
		if not scopes or not any((contains_quote(s, quote, mode) for s in scopes)):
			raise ValueError('Quote does not belong to the primary anchor')
		r = '\n'.join(scopes)
	elif not documentation:
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
		if matches[0].get('anchor') or matches[0].get('ancestor_anchors'):
			raise ValueError('Documentation section has an available anchor; use its verified address')
		if not contains_quote(matches[0]['content'], quote, mode):
			raise ValueError('Quote does not match the documented section')
		r = matches[0]['content']
	return r
