"""Verify saved sources, locators and quotes without fetching or judging claims."""

from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit
import hashlib
import json
import re

from .analysis import iter_arguments, SECTIONS
from .diagnostics import problem
from .research import inside, load_observation, extract_bytes


def pointer(*parts):
    return '/' + '/'.join(str(x).replace('~', '~0').replace('/', '~1') for x in parts) if parts else ''


def resolve_pointer(value, fragment):
    fragment = unquote(fragment)
    if not fragment:
        return value
    if not fragment.startswith('/'):
        raise ValueError('JSON fragment must be an RFC 6901 pointer')
    for raw in fragment[1:].split('/'):
        if re.search(r'~(?![01])', raw):
            raise ValueError('Invalid JSON pointer escape')
        key = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', key):
                raise ValueError('Array pointer must be a nonnegative canonical index')
            value = value[int(key)]
        elif isinstance(value, dict):
            value = value[key]
        else:
            raise ValueError('Pointer traverses a scalar')
    return value


def local_file(root, reference):
    reference = urldefrag(reference)[0]
    parsed = urlsplit(reference)
    if parsed.scheme == 'file':
        path = unquote(parsed.path)
        if re.match(r'^/[A-Za-z]:/', path):
            path = path[1:]
        if parsed.netloc and parsed.netloc != 'localhost':
            raise ValueError('Remote file URI is not a local project source')
    else:
        path = unquote(reference)
    root_resolved = Path(root).resolve()
    target = (root_resolved / 'ꘖ/KB' / path).resolve()
    if not target.exists() and path.replace('\\', '/').lstrip('/').startswith('source/'):
        alt = (root_resolved / path.replace('\\', '/').lstrip('/')).resolve()
        if alt.is_relative_to(root_resolved / 'source'):
            target = alt
    if not target.is_relative_to(root_resolved):
        raise ValueError('Source path escapes the project; copy authorized primary evidence into Evidence first')
    return target


def _markdown_section(text: str, fragment: str) -> str:
    from markdown_it import MarkdownIt
    tokens = MarkdownIt('commonmark').parse(text)
    lines, headings, used = text.splitlines(keepends=True), [], set()
    for index, token in enumerate(tokens):
        if token.type != 'heading_open':
            continue
        inline = tokens[index + 1]
        title = ''.join(t.content for t in inline.children or [] if t.type in ('text', 'code_inline', 'image'))
        slug = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
        ident, number = slug, 0
        while ident in used:
            number += 1; ident = f'{slug}-{number}'
        used.add(ident)
        headings.append((ident, int(token.tag[1]), token.map[0]))
    match = next((i for i, h in enumerate(headings) if h[0] == unquote(fragment)), None)
    if match is None:
        raise ValueError('Markdown section anchor is absent')
    heading = headings[match]
    end = next((h[2] for h in headings[match + 1:] if h[1] <= heading[1]), len(lines))
    return ''.join(lines[heading[2]:end])


def saved_source(root, source, observation=None):
    base, fragment = urldefrag(source)
    if urlsplit(base).scheme.lower() in ('http', 'https'):
        if not observation:
            index = Path(root) / 'ꘖ/data/http-index.json'
            candidates = json.loads(index.read_text(encoding='utf-8')).values() if index.exists() else []
            for candidate in candidates:
                meta = load_observation(root, candidate['observation'])
                if base in (meta['url'], meta['final_url']):
                    observation = candidate['observation']; break
        if not observation:
            raise FileNotFoundError('No saved HTTP/DOM observation; use saved primary evidence or collect the required source once')
        meta = load_observation(root, observation)
        if base not in (meta['url'], meta['final_url']):
            raise ValueError('Observation belongs to a different URL')
        if meta.get('error') or (meta.get('kind', 'http') == 'http' and not 200 <= meta['status'] < 300):
            raise ValueError('Saved HTTP result is unavailable; use a different verification method')
        file = local_file(root, observation).parent / 'response.bin'
        body = file.read_bytes()
        if meta['content_type'] in ('text/html', 'application/xhtml+xml'):
            data = extract_bytes(body, meta['content_type'], 'html', meta.get('charset') or 'utf-8')
            return {'kind': 'html', 'data': data, 'raw': body.decode(meta.get('charset') or 'utf-8', errors='replace'), 'fragment': unquote(fragment), 'meta': meta}
        text = body.decode(meta.get('charset') or 'utf-8', errors='replace')
        if meta['content_type'] == 'application/json' or meta['content_type'].endswith('+json'):
            value = resolve_pointer(json.loads(text), fragment)
            text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
            return {'kind': 'json', 'text': text, 'fragment': unquote(fragment), 'meta': meta}
        if fragment:
            raise ValueError('This source format does not support a verified fragment locator')
        return {'kind': 'text', 'text': text, 'fragment': unquote(fragment), 'meta': meta}
    file = local_file(root, base)
    raw = file.read_bytes()
    if re.fullmatch(r'[a-f0-9]{64}', file.stem.lower()) and hashlib.sha256(raw).hexdigest() != file.stem.lower():
        raise ValueError('Immutable source file differs from its content-addressed filename')
    if file.suffix.lower() in ('.pdf', '.docx', '.odt', '.xlsx', '.xlsm', '.rtf'):
        from .upwork_data import extract_attachment_markdown
        md_text = extract_attachment_markdown(file, raw)
        if fragment:
            md_text = _markdown_section(md_text, fragment)
        plain_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', md_text).replace('**', '')
        return {'kind': 'text', 'text': md_text + '\n' + plain_text, 'fragment': unquote(fragment),
                'file': file, 'sha256': hashlib.sha256(raw).hexdigest()}
    text = raw.decode('utf-8-sig')
    if file.suffix.lower() == '.json':
        value = resolve_pointer(json.loads(text), fragment)
        rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
        return {'kind': 'json', 'text': rendered, 'fragment': unquote(fragment), 'file': file, 'sha256': hashlib.sha256(raw).hexdigest()}
    if file.suffix.lower() in ('.html', '.htm'):
        return {'kind': 'html', 'data': extract_bytes(raw, 'text/html', 'html'), 'raw': text,
                'fragment': unquote(fragment), 'file': file, 'sha256': hashlib.sha256(raw).hexdigest()}
    if (file.suffix.lower() == '.md' or file.name == '.md') and fragment:
        text = _markdown_section(text, fragment)
    elif fragment:
        raise ValueError('This source format does not support a verified fragment locator')
    return {'kind': 'text', 'text': text, 'fragment': unquote(fragment), 'file': file, 'sha256': hashlib.sha256(raw).hexdigest()}


def contains_quote(text, quote, mode='exact'):
    if mode == 'exact':
        return quote in text
    if mode == 'whitespace':
        # Explicit policy only: no punctuation, word, case or number substitution.
        return ' '.join(quote.split()) in ' '.join(text.split())
    raise ValueError('quote_match must be exact or whitespace')


def evidence_issues(root, value):
    issues = []
    for ident, field, argument, source in iter_arguments(value):
        if not isinstance(source, str) or not isinstance(argument.get('quote'), str):
            continue  # Structural diagnostics already identify these fields.
        locator = argument.get('anchor_exception') if isinstance(argument.get('anchor_exception'), dict) else {}
        try:
            saved = saved_source(root, source, argument.get('observation') or locator.get('observation'))
            quote, mode = argument['quote'], argument.get('quote_match', 'exact')
            expected_hash = argument.get('source_sha256')
            actual_hash = saved.get('sha256') or saved.get('meta', {}).get('body_sha256')
            if expected_hash and expected_hash != actual_hash:
                raise ValueError('Source hash differs from the referenced observation')
            if saved['kind'] == 'html':
                data, fragment = saved['data'], saved.get('fragment')
                if data.get('browser_check_required'):
                    raise ValueError('Challenge page requires browser verification; it is not the intended source')
                # Parsed HTMLData has no heuristic challenge key; inspect its content too.
                if re.search(r'(?i)verify you are human|checking your browser|__LS_SEQ_LOADER__', data['text'] + saved['raw'][:8000]):
                    raise ValueError('Challenge page requires browser verification')
                if fragment:
                    if fragment not in data['anchors']:
                        raise ValueError('Anchor not found in saved source HTML; rendered DOM needs separate evidence')
                    if fragment in data.get('ambiguous_anchors', []):
                        raise ValueError('Anchor occurs more than once; use an unambiguous source locator')
                    heading = [h for h in data['sections'] if h.get('anchor') == fragment]
                    scopes = [h['content'] for h in heading] or data['anchor_content'].get(fragment, [])
                    if not scopes:
                        raise ValueError('Named anchor scope requires a separate section locator')
                    if not any(contains_quote(s, quote, mode) for s in scopes):
                        raise ValueError('Quote does not match the referenced anchor section')
                elif argument.get('documentation'):
                    section = locator.get('section')
                    matches = [h for h in data['sections'] if h['text'] == section]
                    if len(matches) != 1:
                        raise ValueError('Documentation section is missing or ambiguous')
                    if matches[0].get('anchor') or matches[0].get('ancestor_anchors'):
                        raise ValueError('Section has an available anchor; use its verified address')
                    if not contains_quote(matches[0]['content'], quote, mode):
                        raise ValueError('Quote does not match the documented section')
                elif not (contains_quote(data['text'], quote, mode) or contains_quote(saved['raw'], quote, mode)):
                    raise ValueError('Quote is absent from the saved page')
            elif not contains_quote(saved['text'], quote, mode):
                raise ValueError('Quote is absent from the referenced source fragment')
            elif argument.get('documentation') and not saved.get('fragment'):
                raise ValueError('No-anchor documentation exception requires a verifiable saved HTML section')
        except (OSError, ValueError, KeyError, IndexError, TypeError, UnicodeError) as exc:
            issues.append(problem('evidence.unconfirmed', field, str(exc), claim_id=ident,
                hint='Use the exact saved source and locator; keep the claim unverified until resolved'))
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
                        if file.name == 'observation.json':
                            observation = load_observation(root, source)
                            if gap.get('status') == 'not_found' and (observation.get('error') or (observation.get('kind', 'http') == 'http' and not 200 <= observation['status'] < 300)):
                                raise ValueError('An unavailable observation establishes unavailable, not a completed search for counterevidence')
                        elif not file.is_file():
                            raise FileNotFoundError(source)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    issues.append(problem('counterevidence.unconfirmed', f'/{section}/{index}/counterevidence', str(exc), claim_id=claim.get('id')))
    return issues


def source_reference(root, file, parts=()):
    file = inside(Path(root) / 'ꘖ/KB', file)
    return file.relative_to(Path(root).resolve() / 'ꘖ/KB').as_posix() + ('#' + pointer(*parts) if parts else '')
