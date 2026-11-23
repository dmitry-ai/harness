# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/76
import json
import re
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlsplit
from .research import classify_html_challenge, extract_bytes, extract_github_blob_lines, extract_markdown, extractor_version, load_observation
_HTML_CTYPES = ('text/html', 'application/xhtml+xml')
_MD_CTYPES = ('text/markdown', 'text/x-markdown')
def _add_anchor(anchors: set[str], value: str) -> None:
	if value:
		anchors.add(value)
		if value.startswith('user-content-') and 13 < len(value):
			anchors.add(value[13:])
def _first_h1(headings) -> str:
	r = ''
	if isinstance(headings, list):
		r = next((h.get('text', '').strip() for h in headings if isinstance(h, dict) and 1 == h.get('level') and h.get('text')), '')
	return r
def _collect_ext_metadata(ext: dict, state: dict) -> None:
	title = (ext.get('title') or '').strip() or _first_h1(ext.get('headings'))
	if title:
		state['titles'].append(title)
	if isinstance(ext.get('anchors'), list):
		state['has_html_anchors'] = True
		for raw_a in ext['anchors']:
			_add_anchor(state['anchors'], str(raw_a) if raw_a else '')
	if isinstance(ext.get('text'), str) and ext['text'].strip():
		state['texts'].append(ext['text'])
def _extract_bundle_html(raw_text: str, data: dict, urls_here: list[str], host: str, state: dict) -> None:
	if ((not state['has_ext']) or state['recheck']) and classify_html_challenge(raw_text, status=data.get('status')):
		state['shell_reason'] = 'unextracted HTML JS challenge or empty shell'
	state['has_html_anchors'] = True
	for m_id in re.finditer('\\b(?:id|name)=["\\\']([^"\\\']+)["\\\']', raw_text, re.I):
		_add_anchor(state['anchors'], m_id.group(1))
	m_t = re.search('<title[^>]*>(.*?)</title>', raw_text[:16000], re.I | re.S)
	if m_t:
		title = ' '.join(m_t.group(1).split())
		if title:
			state['titles'].append(title)
	if 'github.com' == host and any(('/blob/' in (urlsplit(u).path or '') for u in urls_here)):
		gh_lines = extract_github_blob_lines(raw_text)
		if gh_lines:
			state['texts'].append('\n'.join(gh_lines))
			state['anchors'].update((f'LC{ln}' for ln in range(1, len(gh_lines) + 1)))
def _extract_bundle_markdown(raw_text: str, state: dict) -> None:
	md_info = extract_markdown(raw_text)
	if 0 == md_info.get('word_count', 0):
		state['shell_reason'] = 'word_count=0 (empty Markdown response)'
	if md_info.get('title'):
		state['titles'].append(md_info['title'])
	state['has_html_anchors'] = True
	for anchor in md_info.get('anchors') or []:
		_add_anchor(state['anchors'], str(anchor))
	if md_info.get('text'):
		state['texts'].append(md_info['text'])
def _inspect_ext_file(ext: dict, cur_ext_ver, has_resp_bin: bool, state: dict) -> None:
	if ext.get('extractor_version') != cur_ext_ver and has_resp_bin:
		state['recheck'] = True
	elif True is ext.get('browser_check_required'):
		state['shell_reason'] = 'browser_check_required=True (JS/anti-bot challenge or empty SPA shell)'
	elif 'headings' in ext and None is ext.get('sitemap') and (0 == ext.get('word_count', 0)):
		state['shell_reason'] = 'word_count=0 (empty HTML shell)'
	_collect_ext_metadata(ext, state)
def _inspect_resp_bin(resp_bin: Path, data: dict, urls_here: list[str], host: str, max_bytes: int, valid_status: bool, state: dict) -> None:
	try:
		if resp_bin.stat().st_size <= max_bytes:
			raw_text = resp_bin.read_bytes().decode(data.get('charset') or 'utf-8', errors='replace')
			ctype = (data.get('content_type') or '').split(';', 1)[0].strip().lower()
			is_md = ctype in _MD_CTYPES
			is_html = (not is_md) and ('html' in ctype or '<title' in raw_text[:4000].lower() or raw_text.lstrip().lower().startswith(('<!doctype html', '<html')))
			if is_md:
				_extract_bundle_markdown(raw_text, state)
			elif is_html:
				_extract_bundle_html(raw_text, data, urls_here, host, state)
			if raw_text.strip():
				state['texts'].append(raw_text)
			if ('json' in ctype or raw_text.lstrip().startswith('{')) and valid_status and (not state['shell_reason']):
				state['json_payload'] = json.loads(raw_text)
	except (OSError, ValueError):
		pass
def _scan_ext_files(ext_files: list[Path], has_resp_bin: bool, state: dict) -> None:
	cur_ext_ver = extractor_version()
	for ext_file in ext_files:
		try:
			ext = json.loads(ext_file.read_text(encoding='utf-8'))
			if isinstance(ext, dict):
				_inspect_ext_file(ext, cur_ext_ver, has_resp_bin, state)
		except (OSError, ValueError):
			continue
def is_valid_observation_status(meta: dict) -> bool:
	r = (not meta.get('error')) and ('dom' == meta.get('kind') or 200 <= (meta.get('status') or 0) < 300)
	return r
def load_observation_bundle(jfile: Path, data: dict, *, max_bytes: int) -> dict:
	urls_here = [u for u in (data.get('url'), data.get('final_url')) if isinstance(u, str) and u.startswith(('http://', 'https://'))]
	host = (urlsplit(urls_here[0]).hostname or '').lower() if urls_here else ''
	valid_status = is_valid_observation_status(data)
	resp_bin = jfile.parent / 'response.bin'
	has_resp_bin = resp_bin.is_file()
	ext_files = list(jfile.parent.glob('extracted-*.json'))
	state = {'has_ext': bool(ext_files), 'recheck': False, 'shell_reason': None, 'titles': [], 'anchors': set(), 'texts': [], 'has_html_anchors': False, 'json_payload': None}
	_scan_ext_files(ext_files, has_resp_bin, state)
	if has_resp_bin:
		_inspect_resp_bin(resp_bin, data, urls_here, host, max_bytes, valid_status, state)
	ok = valid_status and (not state['shell_reason'])
	reason = state['shell_reason'] or f"error={data.get('error')} status={data.get('status')}"
	r = {'urls': urls_here, 'host': host, 'valid': ok, 'reason': None if ok else reason, 'titles': state['titles'], 'anchors': state['anchors'], 'has_html_anchors': state['has_html_anchors'], 'texts': state['texts'], 'json_payload': state['json_payload']}
	return r
def load_observation_content(root, observation_ref: str, meta: dict, *, fragment: str='') -> dict:
	from .evidence import local_file, resolve_pointer
	body = (local_file(root, observation_ref).parent / 'response.bin').read_bytes()
	charset = meta.get('charset') or 'utf-8'
	ct_low = (meta.get('content_type') or '').split(';', 1)[0].strip().lower()
	raw_str, frag = (body.decode(charset, errors='replace'), unquote(fragment))
	if ct_low in _HTML_CTYPES + _MD_CTYPES:
		data = extract_bytes(body, meta['content_type'], 'html', charset, status=meta.get('status'))
		r = {'kind': 'html', 'data': data, 'raw': raw_str, 'fragment': frag, 'meta': meta}
		if ct_low in _MD_CTYPES:
			r['is_markdown'] = True
	elif 'application/json' == ct_low or ct_low.endswith('+json'):
		value = resolve_pointer(json.loads(raw_str), fragment)
		r = {'kind': 'json', 'text': value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2), 'fragment': frag, 'meta': meta}
	elif fragment:
		raise ValueError('This source format does not support a verified fragment locator')
	else:
		r = {'kind': 'text', 'text': raw_str, 'fragment': frag, 'meta': meta}
	return r
def probe_observation_status(root, meta: dict, base_url: str, fragment: str='') -> str:
	ct_low = (meta.get('content_type') or '').split(';', 1)[0].strip().lower()
	if not is_valid_observation_status(meta):
		r = 'unavailable'
	elif urldefrag(meta['final_url'])[0] != base_url:
		r = 'redirect-unverified'
	elif ct_low not in _HTML_CTYPES + _MD_CTYPES:
		r = 'anchor-unverified' if fragment else 'http-ok'
	else:
		from .evidence import local_file
		body = local_file(root, meta['observation']).with_name('response.bin').read_bytes()
		data = extract_bytes(body, meta['content_type'], 'html', meta.get('charset') or 'utf-8', status=meta.get('status'))
		frag = unquote(fragment)
		if data.get('browser_check_required'):
			r = 'browser-check-required'
		elif fragment and (frag not in data['anchors'] or frag in data.get('ambiguous_anchors', [])):
			r = 'anchor-unverified'
		else:
			r = 'http-ok'
	return r
def resolve_http_observation(root, base_url: str, observation: str | None=None) -> tuple[str, dict]:
	if not observation:
		from .path_registry import project_paths
		index = project_paths(root, exact_root=True).http_index_json
		candidates = json.loads(index.read_text(encoding='utf-8')).values() if index.exists() else []
		for candidate in candidates:
			meta = load_observation(root, candidate['observation'])
			if base_url in (meta['url'], meta['final_url']):
				observation = candidate['observation']
				break
	if not observation:
		raise FileNotFoundError('No saved HTTP/DOM observation; use saved primary evidence or collect the required source once')
	meta = load_observation(root, observation)
	if base_url not in (meta['url'], meta['final_url']):
		raise ValueError('Observation belongs to a different URL')
	if not is_valid_observation_status(meta):
		raise ValueError('Saved HTTP result is unavailable; use a different verification method')
	r = (observation, meta)
	return r
