# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
# https://github.com/dmitry-ai/harness/issues/38
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import hashlib
import json
import re
import socket
import ssl
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile
from .storage import create_bytes, locked, replace_bytes
MAX_BYTES = 16 * 1024 * 1024
PROFILES = ('html', 'shopify', 'tracking', 'document')
BROWSER_MODES = ('auto', 'always', 'never')
VOID_ELEMENTS = ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr')
_CHALLENGE_RE = re.compile('(?i)verify you are human|checking your browser|__LS_SEQ_LOADER__|enable javascript and cookies|name=["\\\'](?:js_challenge|jsc_token)["\\\']|cf-browser-verification|cf_chl_opt|challenge-platform|<noscript>[^<]*enable javascript')
def classify_network_error(exc):
	cause = exc.reason if isinstance(exc, URLError) and None is not getattr(exc, 'reason', None) else exc
	if isinstance(cause, socket.gaierror):
		r = ('dns_error', False)
	elif isinstance(cause, (TimeoutError, socket.timeout)):
		r = ('tcp_timeout', None)
	elif isinstance(cause, ConnectionRefusedError):
		r = ('connection_refused', True)
	elif isinstance(cause, ssl.SSLError):
		r = ('tls_error', True)
	elif isinstance(exc, ValueError):
		r = ('value_error', None)
	else:
		r = ('network_error', None)
	return r
def json_data(value):
	return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
def _fingerprint(value):
	return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
def inside(root, relative):
	root = Path(root).resolve()
	target = (root / relative).resolve()
	if not target.is_relative_to(root):
		raise ValueError(f'Path escapes project: {relative}')
	r = target
	return r
@dataclass(frozen=True)
class Response:
	url: str
	status: int
	content_type: str
	body: bytes
	charset: str = 'utf-8'
	redirects: tuple = ()
class SafeRedirects(HTTPRedirectHandler):
	def __init__(self):
		self.chain = []
	def redirect_request(self, req, fp, code, msg, headers, newurl):
		redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
		if redirected:
			self.chain.append({'from': req.full_url, 'to': redirected.full_url, 'status': code})
			def origin(url):
				value = urlsplit(url)
				r = (value.scheme, value.hostname, value.port or (443 if 'https' == value.scheme else 80))
				return r
			if origin(req.full_url) != origin(redirected.full_url):
				for key in list(redirected.headers):
					if key.lower() in ('authorization', 'cookie', 'proxy-authorization'):
						redirected.remove_header(key)
		r = redirected
		return r
def fetch(url, headers, timeout):
	redirects = SafeRedirects()
	try:
		response = build_opener(redirects).open(Request(url, headers=headers), timeout=timeout)
	except HTTPError as error:
		response = error
	with response:
		data = response.read(MAX_BYTES + 1)
		if len(data) > MAX_BYTES:
			raise ValueError('Response exceeds 16 MiB')
		r = Response(response.url, response.status, response.headers.get_content_type(), data, response.headers.get_content_charset() or 'utf-8', tuple(redirects.chain))
	return r
def request_context(value=None):
	if None is value:
		r = {'session': {'mode': 'unknown', 'verification': 'unverified'}, 'egress': {'country': None, 'verification': 'unverified'}}
	else:
		if not isinstance(value, dict):
			raise ValueError('Request context must be an object')
		allowed = {'session', 'egress', 'url_country', 'language', 'selected_country', 'currency', 'session_id', 'state_fingerprint'}
		if set(value) - allowed:
			raise ValueError('Context accepts explicit session/geography/state conditions, not credentials')
		result = json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
		session = result.setdefault('session', {'mode': 'unknown', 'verification': 'unverified'})
		egress = result.setdefault('egress', {'country': None, 'verification': 'unverified'})
		if not isinstance(session, dict) or set(session) - {'mode', 'verification', 'evidence'} or session.get('mode') not in ('normal', 'incognito', 'isolated', 'unknown'):
			raise ValueError('Session mode must distinguish normal, incognito, isolated and unknown')
		if not isinstance(egress, dict) or set(egress) - {'country', 'verification', 'evidence'} or (None is not egress.get('country') and (not re.fullmatch('[A-Z]{2}', str(egress.get('country'))))):
			raise ValueError('Egress country must be an explicit ISO country or null; URL country is separate')
		for condition in (session, egress):
			if condition.get('verification', 'unverified') not in ('verified', 'unverified'):
				raise ValueError('Context verification must be verified or unverified')
			if 'verified' == condition.get('verification') and (not condition.get('evidence')):
				raise ValueError('Verified conditions require recorded evidence; empty cookies prove no browser mode')
		for key in allowed - {'session', 'egress'}:
			if key in result and (not isinstance(result[key], str) or not result[key].strip()):
				raise ValueError('Explicit context fields must be nonempty strings')
		r = result
	return r
def request_key(url, headers, scope, context=None):
	url = urldefrag(url)[0]
	parsed = urlsplit(url)
	if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or any((c.isspace() for c in url)):
		raise ValueError('A valid HTTP(S) URL without embedded credentials is required')
	_ = parsed.port
	normalized = {k.lower(): str(v) for k, v in headers.items()}
	r = (url, _fingerprint({'url': url, 'method': 'GET', 'headers': normalized, 'scope': scope, 'context': request_context(context)}))
	return r
def observation_capabilities(meta):
	if meta.get('error'):
		r = set()
	elif 'http' == meta.get('kind') and 'GET' == meta.get('method') and (200 <= (meta.get('status') or 0) < 300):
		r = {'content', 'markup', 'platform_capability'}
	elif 'dom' == meta.get('kind') and 'READ_DOM' == meta.get('method'):
		r = {'content', 'markup', 'dom', 'platform_capability'}
	else:
		r = set()
	return r
METRIC_KEYS = ('uses', 'cache_hits', 'fresh_attempts', 'failed_attempts', 'http_unavailable')
def metric_counts(events):
	return dict(zip(METRIC_KEYS, (len(events), sum((True is x.get('cached') for x in events)), sum((False is x.get('cached') for x in events)), sum((bool(x.get('error')) for x in events)), sum(('http' == x.get('kind') and (x.get('status') or 0) >= 400 for x in events)))))
def bounded_metrics(value):
	if isinstance(value, list):
		r = {'version': 2, 'totals': metric_counts(value), 'recent': value[-32:]}
	else:
		if not isinstance(value, dict) or 2 != value.get('version') or set(value.get('totals', {})) != set(METRIC_KEYS):
			raise ValueError('Unknown collector metrics format; preserve and inspect')
		r = value
	return r
def observed_use(root, result):
	directory = Path(root) / 'ꘖ/data'
	path = directory / 'research-metrics.json'
	event = {k: result.get(k) for k in ('url', 'cached', 'observation', 'status', 'error', 'kind', 'request_key')}
	event['time'] = datetime.now(timezone.utc).isoformat(timespec='microseconds')
	with locked(directory / 'research-metrics.lock'):
		value = bounded_metrics(json.loads(path.read_text(encoding='utf-8')) if path.exists() else [])
		counts = metric_counts([event])
		value['totals'] = {key: value['totals'][key] + counts[key] for key in METRIC_KEYS}
		value['recent'] = (value['recent'] + [event])[-32:]
		replace_bytes(path, json_data(value))
	r = result
	return r
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
def collect(root, url, *, headers=None, scope='public', max_age=86400, refresh_reason=None, timeout=15, fetcher=None, observation_kind='http', context=None):
	root = Path(root).resolve()
	if max_age < 0 or timeout <= 0 or (not isinstance(scope, str)) or (not scope.strip()):
		raise ValueError('Nonnegative max_age, positive timeout and explicit request scope required')
	headers = {'User-Agent': 'UpworkResearch/2.0', **(headers or {})}
	if observation_kind not in ('http', 'dom') or ('dom' == observation_kind and None is fetcher):
		raise ValueError('DOM observation needs an explicit read-only browser capture')
	if not all((isinstance(k, str) and isinstance(v, str) for k, v in headers.items())):
		raise ValueError('Request headers must contain string keys and values')
	context = request_context(context)
	url, key = request_key(url, headers, scope + ':' + observation_kind, context)
	data_dir = root / 'ꘖ/data'
	index_file = data_dir / 'http-index.json'
	with locked(data_dir / ('http-' + key[:24] + '.lock'), timeout=max(30, timeout + 15)):
		index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {}
		entry = index.get(key)
		if entry and (not refresh_reason) and (max_age > 0):
			meta = load_observation(root, entry['observation'])
			ttl = min(max_age, 300) if meta.get('error') or (None is not meta.get('status') and meta.get('status', 0) >= 400) else max_age
			if time.time() - datetime.fromisoformat(meta['observed_at']).timestamp() <= ttl:
				return observed_use(root, {'cached': True, 'observation': entry['observation'], **meta})
		if None is not refresh_reason and (not refresh_reason.strip()):
			raise ValueError('Refresh needs a reason for the new measurement')
		when = datetime.now(timezone.utc).isoformat(timespec='microseconds')
		error, error_kind, dns_resolved = (None, None, None)
		try:
			response = (fetcher or fetch)(url, headers, timeout)
			if len(response.body) > MAX_BYTES:
				raise ValueError('Response exceeds 16 MiB')
			dns_resolved = True if 'http' == observation_kind and (response.status or 0) > 0 else None
		except (OSError, ValueError, RuntimeError) as exc:
			response = Response(url, 0, 'application/octet-stream', b'')
			error = type(exc).__name__
			error_kind, dns_resolved = classify_network_error(exc)
		folder = root / 'ꘖ/KB/Evidence/HTTP' / key[:24] / uuid.uuid4().hex
		folder.mkdir(parents=True, exist_ok=False)
		create_bytes(folder / 'response.bin', response.body)
		meta = {'schema_version': 1, 'kind': observation_kind, 'request_key': key, 'url': url, 'final_url': response.url, 'method': 'GET' if 'http' == observation_kind else 'READ_DOM', 'request_scope': scope, 'observed_at': when, 'status': response.status if 'http' == observation_kind else None, 'http_status_verified': 'http' == observation_kind and response.status > 0, 'content_type': response.content_type, 'charset': response.charset, 'redirects': list(response.redirects), 'body_sha256': hashlib.sha256(response.body).hexdigest(), 'body_bytes': len(response.body), 'refresh_reason': refresh_reason, 'error': error, 'error_kind': error_kind, 'dns_resolved': dns_resolved, 'conditions': {'header_names': sorted((k.lower() for k in headers)), 'values_fingerprint': key, 'reported_context': context, 'context_fingerprint': _fingerprint(context)}, 'collector': 'read-only-http' if 'http' == observation_kind else 'read-only-dom', 'interaction_checked': False}
		create_bytes(folder / 'observation.json', json_data(meta))
		reference = (folder / 'observation.json').relative_to(root / 'ꘖ/KB').as_posix()
		with locked(data_dir / 'http-index.lock'):
			index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {}
			index[key] = {'observation': reference}
			replace_bytes(index_file, json_data(index))
		return observed_use(root, {'cached': False, 'observation': reference, **meta})
def load_observation(root, reference):
	file = inside(Path(root).resolve() / 'ꘖ/KB', urldefrag(reference)[0])
	meta = json.loads(file.read_text(encoding='utf-8'))
	if 1 != meta.get('schema_version') or not isinstance(meta.get('body_sha256'), str):
		raise ValueError('Invalid observation metadata')
	body = (file.parent / 'response.bin').read_bytes()
	if len(body) != meta.get('body_bytes') or hashlib.sha256(body).hexdigest() != meta['body_sha256']:
		raise ValueError('Observation body differs from its saved hash/size')
	r = meta
	return r
class HTMLData(HTMLParser):
	def __init__(self):
		super().__init__(convert_charrefs=True)
		self.stack, self.text, self.headings, self.anchors, self.scripts, self.json_ld = ([], [], [], [], [], [])
		self.title, self.meta, self.meta_all, self.canonical, self.heading, self.script = ('', {}, {}, [], None, None)
		self.links, self.link = ([], None)
		self.images, self.embeds = ([], [])
		self.anchor_ranges, self.section_ranges = ({}, [])
		self.position = 0
	def handle_starttag(self, tag, attrs):
		attrs = dict(attrs)
		is_void = tag in VOID_ELEMENTS
		anchor = attrs.get('id') or (attrs.get('name') if 'a' == tag else None)
		if anchor:
			self.anchors.append(anchor)
			self.anchor_ranges.setdefault(anchor, []).append({'start': self.position, 'end': self.position if is_void else None})
		if 'a' == tag and attrs.get('href'):
			self.link = {'href': attrs['href'], 'text': ''}
		if 'img' == tag:
			self.images.append({'src': attrs.get('src') or attrs.get('data-src') or '', 'alt': attrs.get('alt', ''), 'has_alt_attr': 'alt' in attrs, 'width': attrs.get('width'), 'height': attrs.get('height')})
		if tag in ('iframe', 'video') and (attrs.get('src') or attrs.get('data-src')):
			self.embeds.append({'tag': tag, 'src': attrs.get('src') or attrs.get('data-src')})
		if 'meta' == tag:
			name = attrs.get('name') or attrs.get('property')
			if name:
				self.meta[name] = attrs.get('content', '')
				self.meta_all.setdefault(name, []).append(attrs.get('content', ''))
		if 'link' == tag and 'canonical' in attrs.get('rel', '').split():
			self.canonical.append(attrs.get('href'))
		if 'script' == tag:
			self.script = {'src': attrs.get('src'), 'type': attrs.get('type'), 'text': ''}
			if attrs.get('src'):
				self.scripts.append(attrs['src'])
		if re.fullmatch('h[1-6]', tag):
			position = self.position
			for section in self.section_ranges:
				if None is section['end'] and section['level'] >= int(tag[1]):
					section['end'] = position
			self.heading = {'level': int(tag[1]), 'text': '', 'anchor': attrs.get('id'), 'ancestor_anchors': [x[1] for x in self.stack if x[1]], 'start': position, 'end': None}
			self.section_ranges.append(self.heading)
		if not is_void:
			self.stack.append((tag, anchor))
	def handle_endtag(self, tag):
		if 'a' == tag and None is not self.link:
			self.link['text'] = ' '.join(self.link['text'].split())
			self.links.append(self.link)
			self.link = None
		if self.heading and re.fullmatch('h[1-6]', tag):
			self.heading['text'] = ' '.join(self.heading['text'].split())
			self.headings.append(self.heading)
			self.heading = None
		if 'script' == tag and self.script:
			if 'application/ld+json' == self.script['type']:
				try:
					self.json_ld.append(json.loads(self.script['text']))
				except ValueError:
					self.json_ld.append({'parse_error': True, 'raw': self.script['text']})
			self.script = None
		for i in range(len(self.stack) - 1, -1, -1):
			if self.stack[i][0] == tag:
				for _, anchor in self.stack[i:]:
					if anchor:
						for span in self.anchor_ranges.get(anchor, []):
							if None is span['end']:
								span['end'] = self.position
				del self.stack[i:]
				break
		if tag in ('p', 'div', 'section', 'li', 'br') or re.fullmatch('h[1-6]', tag):
			self.text.append('\n')
			self.position += 1
	def handle_data(self, value):
		tags = {tag for tag, _ in self.stack}
		if self.script:
			self.script['text'] += value
		if 'title' in tags:
			self.title += value
		if self.heading:
			self.heading['text'] += value
		if None is not self.link and (not tags.intersection(('script', 'style'))):
			self.link['text'] += value
		if not tags.intersection(('script', 'style', 'head')):
			self.text.append(value)
			self.position += len(value)
	def result(self):
		plain = ''.join(self.text)
		plain_len = len(plain)
		clean_text = '\n'.join((x.strip() for x in plain.splitlines() if x.strip()))
		title_str = ' '.join(self.title.split())
		sections = [{**h, 'end': plain_len if None is h['end'] else h['end'], 'content': plain[h['start']:h['end']]} for h in self.section_ranges]
		anchor_ranges = {anchor: [[x['start'], plain_len if None is x['end'] else x['end']] for x in ranges] for anchor, ranges in self.anchor_ranges.items()}
		word_count = len(re.findall('\\w+', clean_text))
		site_name = (self.meta.get('og:site_name') or '').strip()
		total_imgs = len(self.images)
		empty_alt = sum((1 for img in self.images if not (img.get('alt') or '').strip()))
		filename_alt = sum((1 for img in self.images if (img.get('alt') or '').strip() and re.search('(?i)\\.(?:jpe?g|png|gif|webp|avif|svg|bmp|tiff?)\\b', (img.get('alt') or '').strip())))
		repeated_site_alt = sum((1 for img in self.images if site_name and (img.get('alt') or '').strip().lower() == site_name.lower()))
		descriptive_alt = max(0, total_imgs - empty_alt - filename_alt - repeated_site_alt)
		h1_count = sum((1 for h in self.headings if 1 == h.get('level')))
		meta_desc = self.meta.get('description', '')
		spaced_brand = bool(re.search('\\b(?:[A-Za-z]\\s+){3,}[A-Za-z]\\b', (self.meta.get('og:site_name') or '') + ' ' + json.dumps(self.json_ld, ensure_ascii=False)))
		json_ld_types = [item.get('@type') for item in self.json_ld if isinstance(item, dict) and item.get('@type')]
		empty_json_ld_desc = any((isinstance(item, dict) and 'description' in item and (not str(item.get('description') or '').strip()) for item in self.json_ld))
		insecure_json_ld_img = any((isinstance(item, dict) and isinstance(item.get('image'), str) and (item['image'].startswith('http://') or item['image'].startswith('//') or item['image'].startswith('/')) for item in self.json_ld))
		r = {'title': title_str, 'meta': self.meta, 'meta_all': self.meta_all, 'canonical': self.canonical, 'headings': self.headings, 'anchors': sorted(set(self.anchors)), 'links': self.links, 'scripts': self.scripts, 'images': self.images, 'image_alt_summary': {'total': total_imgs, 'empty_alt': empty_alt, 'filename_like_alt': filename_alt, 'repeated_site_name_alt': repeated_site_alt, 'descriptive_alt': descriptive_alt}, 'embeds': self.embeds, 'word_count': word_count, 'seo_diagnostics': {'h1_count': h1_count, 'missing_h1': 0 == h1_count, 'multiple_h1': h1_count > 1, 'title_length': len(title_str), 'overlong_title': len(title_str) > 65, 'meta_description_length': len(meta_desc), 'missing_meta_description': not bool(meta_desc.strip()), 'spaced_brand_name': spaced_brand, 'json_ld_types': json_ld_types, 'empty_json_ld_description': empty_json_ld_desc, 'insecure_or_relative_json_ld_image': insecure_json_ld_img}, 'json_ld': self.json_ld, 'sections': sections, 'anchor_ranges': anchor_ranges, 'anchor_content': {anchor: [plain[x['start']:x['end']] for x in ranges] for anchor, ranges in self.anchor_ranges.items()}, 'ambiguous_anchors': sorted((anchor for anchor, ranges in self.anchor_ranges.items() if len(ranges) > 1)), 'text': clean_text}
		return r
def _extract_sitemap(text):
	stripped = text.lstrip()
	if not (stripped.startswith('<?xml') or '<urlset' in stripped[:1500] or '<sitemapindex' in stripped[:1500]):
		return None
	try:
		root_el = ET.fromstring(text.encode('utf-8'))
	except ET.ParseError:
		return None
	root_name = root_el.tag.rsplit('}', 1)[-1].lower()
	if root_name not in ('urlset', 'sitemapindex'):
		return None
	urls = []
	img_to_pages = {}
	polluted_titles = set()
	for child in root_el:
		tag_name = child.tag.rsplit('}', 1)[-1].lower()
		if tag_name not in ('url', 'sitemap'):
			continue
		entry = {'loc': '', 'lastmod': None, 'changefreq': None, 'priority': None, 'images': []}
		for field_el in child:
			fname = field_el.tag.rsplit('}', 1)[-1].lower()
			val = (field_el.text or '').strip()
			if fname in ('loc', 'lastmod', 'changefreq', 'priority'):
				entry[fname] = val
			elif 'image' == fname:
				img_item = {'loc': '', 'title': None, 'caption': None}
				for img_child in field_el:
					iname = img_child.tag.rsplit('}', 1)[-1].lower()
					if iname in ('loc', 'title', 'caption'):
						img_item[iname] = (img_child.text or '').strip()
				if img_item['loc']:
					entry['images'].append(img_item)
					if img_item['title'] and 'select to expand' in img_item['title'].lower():
						polluted_titles.add(img_item['title'])
		if entry['loc']:
			urls.append(entry)
			for img_item in entry['images']:
				img_to_pages.setdefault(img_item['loc'], []).append(entry['loc'])
	unescaped_spaces = [u['loc'] for u in urls if ' ' in u['loc'] or '%20' in u['loc']]
	template_slugs = [u['loc'] for u in urls if re.search('(?i)(?:blog-post-title|new-page|sample-page|copy-of|lorem-ispum|lorem-ipsum|/home$)', u['loc'])]
	paths = [urlsplit(u['loc']).path for u in urls]
	root_missing = any(('/home' == p.rstrip('/') for p in paths)) and (not any((p in ('', '/') for p in paths)))
	duplicate_images = {k: v for k, v in sorted(img_to_pages.items()) if len(v) > 1}
	return {'type': root_name, 'url_count': len(urls), 'urls': urls, 'sitemap_issues': {'unescaped_spaces_in_loc': unescaped_spaces, 'template_slug_urls': template_slugs, 'root_url_missing': root_missing, 'polluted_image_titles': sorted(polluted_titles), 'duplicate_image_locs': duplicate_images}}
def _summarize_json_collections(value):
	arrays = {}
	def walk(node, path='', depth=0):
		if depth > 4:
			return
		if isinstance(node, list) and node and all((isinstance(x, dict) for x in node)):
			key = path or '/items'
			arrays[key] = node
			if path.startswith('/') and '/' not in path[1:]:
				arrays[path[1:]] = node
			return
		if isinstance(node, dict):
			for k, v in node.items():
				escaped = str(k).replace('~', '~0').replace('/', '~1')
				walk(v, f'{path}/{escaped}', depth + 1)
	walk(value)
	summary = {}
	iso_re = re.compile('^\\d{4}-\\d{2}-\\d{2}(?:[T ]\\d{2}:\\d{2}:\\d{2})?')
	for name, items in arrays.items():
		ts_fields, cat_fields = ({}, {})
		for item in items:
			label = next((str(item[k]) for k in ('title', 'name', 'handle', 'slug', 'id') if None is not item.get(k)), None)
			for k, v in item.items():
				if isinstance(v, str) and iso_re.match(v):
					ts_fields.setdefault(k, []).append((v, item.get('id'), label))
				elif 'id' != k and isinstance(v, (str, bool)) and (len(str(v)) <= 120):
					cat_fields.setdefault(k, {})[str(v)] = cat_fields.get(k, {}).get(str(v), 0) + 1
				elif isinstance(v, list) and v and all((isinstance(elem, str) and len(elem) <= 80 for elem in v)):
					for elem in v:
						cat_fields.setdefault(k, {})[elem] = cat_fields.get(k, {}).get(elem, 0) + 1
		ts_summary = {}
		for k, entries in ts_fields.items():
			ordered = sorted(entries, key=lambda x: x[0])
			by_date = {}
			for val, _, _ in ordered:
				day = val[:10]
				by_date[day] = by_date.get(day, 0) + 1
			earliest, latest = (ordered[0], ordered[-1])
			ts_summary[k] = {'min': earliest[0], 'max': latest[0], 'count': len(ordered), 'by_date': dict(sorted(by_date.items())), 'earliest_record': {'id': earliest[1], 'label': earliest[2], k: earliest[0]}, 'latest_record': {'id': latest[1], 'label': latest[2], k: latest[0]}}
		filtered_cats = {k: dict(sorted(counts.items())) for k, counts in sorted(cat_fields.items()) if len(counts) <= 50 and (1 == len(items) or len(counts) < len(items) or any((c > 1 for c in counts.values())))}
		summary[name] = {'record_count': len(items), 'timestamp_ranges': ts_summary, 'field_counts': filtered_cats}
	return summary
def extract_bytes(body, content_type, profile, charset='utf-8'):
	if profile not in PROFILES:
		raise ValueError(f'Unknown profile: {profile}; choose {PROFILES}')
	if 'document' == profile and body.startswith(b'%PDF-'):
		from .upwork_data import extract_pdf_markdown
		md = extract_pdf_markdown(body)
		paragraphs = [line for line in md.splitlines() if line.strip()]
		r = {'paragraphs': paragraphs, 'text': md, 'markdown': md, 'layout_checked': True}
	elif not ('document' == profile and body.startswith(b'PK')):
		text = body.decode(charset, errors='replace')
		if 'shopify' == profile:
			value = json.loads(text)
			if not isinstance(value, dict) or not any((k in value for k in ('product', 'products', 'variants', 'id'))):
				raise ValueError('Expected Shopify product/collection JSON')
			r = {'data': value, 'summary': _summarize_json_collections(value), 'text': text, 'scope': 'public JSON response; not Merchant Center feed or admin configuration'}
		elif 'document' == profile and content_type not in ('text/html', 'application/xhtml+xml'):
			out = {'paragraphs': text.splitlines(), 'text': text, 'layout_checked': False}
			if 'application/json' == content_type or text.lstrip().startswith(('{', '[')):
				try:
					parsed = json.loads(text)
					if isinstance(parsed, (dict, list)):
						out['summary'] = _summarize_json_collections(parsed)
				except ValueError:
					pass
			r = out
		else:
			parser = HTMLData()
			parser.feed(text)
			result = parser.result()
			result['tracking_summary'] = {'identifiers': sorted(set(re.findall('\\b(?:GTM-[A-Z0-9]+|G-[A-Z0-9]+|UA-\\d+-\\d+|AW-\\d+)\\b', text))), 'gsc_verification': bool(result['meta'].get('google-site-verification')), 'cms_technical_domains': sorted(set(re.findall('\\b[a-z0-9-]+\\.(?:squarespace\\.com|myshopify\\.com|webflow\\.io|wixsite\\.com|wpengine\\.com)\\b', text, flags=re.I)))}
			sitemap = _extract_sitemap(text)
			if None is not sitemap:
				result['sitemap'] = sitemap
			if 'tracking' == profile:
				result['identifiers'] = sorted(set(re.findall('\\b(?:GTM-[A-Z0-9]+|G-[A-Z0-9]+|AW-\\d+)\\b', text)))
				configs, parse_failures = ({}, [])
				for key in ('webPixelsConfigList', 'wpmLoader', 'resource'):
					for match in re.finditer('[\\"\\\']?\\b' + key + '\\b[\\"\\\']?\\s*[:=]\\s*', text):
						try:
							value, _ = json.JSONDecoder().raw_decode(text[match.end():])
							if isinstance(value, str):
								try:
									value = json.loads(value)
								except ValueError:
									pass
							configs.setdefault(key, []).append(value)
						except ValueError:
							parse_failures.append({'key': key, 'offset': match.end(), 'reason': 'Not literal JSON; inspect saved source without evaluating JavaScript'})
				result['embedded_json'] = configs
				result['embedded_json_unparsed'] = parse_failures
				result['execution_checked'] = False
			result['browser_check_required'] = bool(_CHALLENGE_RE.search(result['text'] + '\n' + text) or (None is result.get('sitemap') and 0 == result.get('word_count', 0)))
			r = result
	else:
		import io
		from .upwork_data import extract_docx_markdown
		with zipfile.ZipFile(io.BytesIO(body)) as doc:
			item = doc.getinfo('word/document.xml')
			if item.file_size > MAX_BYTES:
				raise ValueError('Document XML exceeds 16 MiB')
			xml = ET.fromstring(doc.read(item))
			non_text = [name for name in doc.namelist() if name.startswith(('word/media/', 'word/charts/', 'word/embeddings/'))]
		ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
		paragraphs = [''.join(p.itertext()) for p in xml.findall('.//w:p', ns)]
		try:
			md = extract_docx_markdown(body)
		except Exception:
			md = '\n'.join(paragraphs)
		r = {'paragraphs': paragraphs, 'text': '\n'.join(paragraphs), 'markdown': md, 'layout_checked': False, 'non_text_parts': non_text}
	return r
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
# https://github.com/dmitry-ai/harness/issues/38
def compact_extraction_for_disk(data):
	out = {k: v for k, v in data.items() if 'anchor_content' != k}
	if isinstance(out.get('sections'), list):
		out['sections'] = [{k: v for k, v in h.items() if 'content' != k} for h in out['sections'] if isinstance(h, dict)]
	if 'paragraphs' in out and isinstance(out.get('text'), str) and (out.get('paragraphs') == out['text'].splitlines()):
		del out['paragraphs']
	r = out
	return r
def extract_observation(root, reference, profile='html'):
	meta = load_observation(root, reference)
	folder = inside(Path(root) / 'ꘖ/KB', urldefrag(reference)[0]).parent
	if meta.get('error') or ('http' == meta.get('kind', 'http') and (not 200 <= meta['status'] < 300)):
		raise ValueError('Observation is unavailable; preserve it and choose a different check method')
	version = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
	target = folder / f'extracted-{profile}.json'
	data = None
	if target.is_file():
		try:
			cached = json.loads(target.read_text(encoding='utf-8'))
			if isinstance(cached, dict) and cached.get('extractor_version') == version and (cached.get('body_sha256') == meta['body_sha256']):
				data = cached
		except (OSError, ValueError):
			data = None
	if None is data:
		raw_data = extract_bytes((folder / 'response.bin').read_bytes(), meta['content_type'], profile, meta.get('charset') or 'utf-8')
		data = {'profile': profile, 'extractor_version': version, 'observation': reference, 'body_sha256': meta['body_sha256'], 'observed_at': meta['observed_at'], **compact_extraction_for_disk(raw_data)}
		payload = json_data(data)
		if len(payload) > MAX_BYTES:
			raise ValueError('Extracted JSON exceeds 16 MiB')
		if not target.exists():
			create_bytes(target, payload)
		else:
			replace_bytes(target, payload)
		for legacy in folder.glob(f'extracted-{profile}-*.json'):
			try:
				legacy.unlink()
			except OSError:
				pass
	r = {'extraction': target.relative_to(Path(root).resolve() / 'ꘖ/KB').as_posix(), 'observation': reference, 'profile': profile, 'observed_at': meta['observed_at']}
	if 'browser_check_required' in data:
		r['browser_check_required'] = bool(data['browser_check_required'])
	if 'word_count' in data:
		r['word_count'] = data['word_count']
	return r
def extract_file(root, file, profile='document'):
	file = inside(root, file)
	body = file.read_bytes()
	if len(body) > MAX_BYTES:
		raise ValueError('Source file exceeds 16 MiB')
	import mimetypes
	kind = mimetypes.guess_type(file.name)[0] or 'text/plain'
	version = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
	source_sha = hashlib.sha256(body).hexdigest()
	target = Path(root) / 'ꘖ/KB/Evidence/Extracted' / source_sha / f'{profile}.json'
	target.parent.mkdir(parents=True, exist_ok=True)
	need_write = True
	if target.is_file():
		try:
			cached = json.loads(target.read_text(encoding='utf-8'))
			if isinstance(cached, dict) and cached.get('extractor_version') == version and (cached.get('source_sha256') == source_sha):
				need_write = False
		except (OSError, ValueError):
			need_write = True
	if need_write:
		data = compact_extraction_for_disk(extract_bytes(body, kind, profile))
		payload = json_data({'profile': profile, 'source': file.relative_to(Path(root).resolve()).as_posix(), 'source_sha256': source_sha, 'extractor_version': version, **data})
		if len(payload) > MAX_BYTES:
			raise ValueError('Extracted JSON exceeds 16 MiB')
		if not target.exists():
			create_bytes(target, payload)
		else:
			replace_bytes(target, payload)
		for legacy in target.parent.glob(f'{profile}-*.json'):
			try:
				legacy.unlink()
			except OSError:
				pass
	r = {'extraction': target.relative_to(Path(root).resolve() / 'ꘖ/KB').as_posix(), 'source_sha256': source_sha}
	return r
def select_dom_tab(tabs, url, tab_id):
	matches = [t for t in tabs if 'page' == t.get('type') and t.get('id') == tab_id and (urldefrag(t.get('url', ''))[0] == urldefrag(url)[0])]
	if 1 != len(matches):
		raise ValueError('Explicit tab ID must match the exact requested URL; no navigation or account fallback')
	r = matches[0]
	return r
def capture_dom(root, url, tab_id, *, session_id=None, refresh_reason=None, context=None, config=None, guard=None):
	from .text_browser import GuardedCDP
	if not isinstance(session_id, str) or not session_id or (not isinstance(tab_id, str)) or (not tab_id):
		raise ValueError('Explicit authorized CDP session_id and exact tab ID required')
	if None is guard:
		guard = GuardedCDP(root, {'session_id': session_id, 'target_id': tab_id}, config=config)
	elif not isinstance(guard, GuardedCDP) or guard.root != Path(root).resolve():
		raise ValueError('DOM reader needs a GuardedCDP instance for this exact project')
	if guard.spec.get('session_id') != session_id or guard.spec.get('target_id') != tab_id:
		raise ValueError('DOM session/target differs from the explicitly selected guard')
	identity = guard.inspect()
	if urldefrag(identity['target'].get('url', ''))[0] != urldefrag(url)[0]:
		raise ValueError('Explicit tab ID must match the requested URL; no navigation or account fallback')
	observed_identity = {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'session_id': session_id, 'target_id': tab_id, 'browser_websocket': identity['browser']['websocket_url'], 'profile': identity['profile'], 'account': identity['account']}
	identity_bytes = json_data(observed_identity)
	identity_hash = hashlib.sha256(identity_bytes).hexdigest()
	identity_path = Path(root).resolve() / 'ꘖ/KB/Evidence/CDPSessions' / f'{identity_hash}.json'
	identity_path.parent.mkdir(parents=True, exist_ok=True)
	if not identity_path.exists():
		create_bytes(identity_path, identity_bytes)
	identity_ref = identity_path.relative_to(Path(root).resolve() / 'ꘖ/KB').as_posix()
	observed_context = dict(context or {})
	observed_context.setdefault('session_id', session_id)
	def read_dom(target, headers, timeout):
		native, actual_identity = guard.call('Runtime.evaluate', {'expression': '({url:location.href,html:document.documentElement.outerHTML})', 'throwOnSideEffect': True, 'returnByValue': True}, include_identity=True)
		if actual_identity['browser']['websocket_url'] != identity['browser']['websocket_url'] or actual_identity['profile'] != identity['profile'] or actual_identity['account'] != identity['account'] or (actual_identity['target']['id'] != tab_id):
			raise ValueError('CDP identity changed during DOM capture; no content proof is issued')
		if not isinstance(native, dict) or native.get('exceptionDetails'):
			raise ValueError('Native DOM evaluation did not complete without side effects')
		data = native.get('result', {}).get('value')
		if not isinstance(data, dict) or not isinstance(data.get('html'), str) or urldefrag(data.get('url', ''))[0] != urldefrag(target)[0]:
			raise ValueError('Tab navigated or DOM capture does not match the intended resource')
		r = Response(data['url'], 0, 'text/html', data['html'].encode('utf-8'))
		return r
	observation = collect(root, url, scope=f'CDP-session:{session_id}:tab:{tab_id}:identity:{identity_ref}', max_age=0, refresh_reason=refresh_reason, fetcher=read_dom, observation_kind='dom', context=observed_context)
	if observation['error']:
		return {**observation, 'cdp_identity': identity_ref, 'cdp_identity_sha256': identity_hash}
	return {**observation, **extract_observation(root, observation['observation']), 'cdp_identity': identity_ref, 'cdp_identity_sha256': identity_hash}
def collect_browser(root, url, *, profile='html', scope='public', refresh_reason=None, max_age=86400, cdp_port=None, timeout=15, context=None, config=None, http_get=None, cdp_call=None, cdp_fetcher=None):
	from .text_browser import collect_cdp_dom
	effective_profile = 'document' if 'auto' == profile else profile
	if effective_profile not in PROFILES:
		raise ValueError(f'Unknown extraction profile: {profile}')
	cdp_meta = {}
	def read_dom(target, headers, fetch_timeout):
		capture = (cdp_fetcher or collect_cdp_dom)(root, target, cdp_port=cdp_port, timeout=fetch_timeout, config=config, http_get=http_get, cdp_call=cdp_call)
		if not isinstance(capture, dict) or not isinstance(capture.get('html'), str):
			raise ValueError('CDP DOM capture did not return HTML payload')
		cdp_meta.update(capture)
		r = Response(capture.get('url') or target, 0, 'text/html', capture['html'].encode('utf-8'))
		return r
	observation = collect(root, url, scope=scope, max_age=max_age, refresh_reason=refresh_reason, timeout=timeout, fetcher=read_dom, observation_kind='dom', context=context)
	item = {k: observation.get(k) for k in ('url', 'final_url', 'cached', 'observation', 'status', 'kind', 'collector', 'content_type', 'observed_at', 'error', 'error_kind', 'dns_resolved')}
	for key in ('cdp_identity', 'cdp_identity_sha256', 'target_id', 'target_mode', 'closed_after_capture', 'endpoint'):
		if key in cdp_meta:
			item[key] = cdp_meta[key]
	if not observation.get('error'):
		try:
			item.update(extract_observation(root, observation['observation'], effective_profile))
		except (OSError, ValueError, KeyError, TypeError, LookupError) as exc:
			item['extraction_error'] = type(exc).__name__
			item['detail'] = 'DOM observation saved; inspect the source or choose another extraction profile'
	r = item
	return r
def compute_site_summary(root, results):
	root = Path(root).resolve()
	kb_dir = root / 'ꘖ/KB'
	titles, descriptions = ({}, {})
	missing_h1, multiple_h1, overlong_titles, thin_urls = ([], [], [], [])
	all_identifiers, cms_domains = (set(), set())
	html_pages = 0
	for item in results or []:
		if not isinstance(item, dict) or item.get('error') or ('dom' != item.get('kind') and (not 200 <= (item.get('status') or 0) < 300)):
			continue
		url = item.get('url') or ''
		ext_rel = item.get('extraction')
		if not ext_rel:
			continue
		path_lower = urlsplit(url).path.lower()
		if path_lower.endswith(('.xml', '.txt', '.json')):
			continue
		ext_file = kb_dir / ext_rel
		if not ext_file.is_file():
			continue
		try:
			ext = json.loads(ext_file.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			continue
		if None is not ext.get('sitemap') or 'headings' not in ext:
			continue
		html_pages += 1
		title = (ext.get('title') or '').strip()
		if title:
			titles.setdefault(title, []).append(url)
			if len(title) > 65:
				overlong_titles.append({'url': url, 'title': title, 'length': len(title)})
		desc = ((ext.get('meta') or {}).get('description') or '').strip()
		if desc:
			descriptions.setdefault(desc, []).append(url)
		h1s = [h for h in ext.get('headings') or [] if isinstance(h, dict) and 1 == h.get('level')]
		if 0 == len(h1s):
			missing_h1.append(url)
		elif len(h1s) > 1:
			multiple_h1.append(url)
		wc = ext.get('word_count')
		if isinstance(wc, int) and wc < 100:
			thin_urls.append({'url': url, 'word_count': wc})
		ts = ext.get('tracking_summary') or {}
		all_identifiers.update(ts.get('identifiers') or [])
		cms_domains.update(ts.get('cms_technical_domains') or [])
	r = {'inspected_html_pages': html_pages, 'missing_h1_urls': missing_h1, 'multiple_h1_urls': multiple_h1, 'overlong_title_urls': overlong_titles, 'duplicate_titles': {k: v for k, v in titles.items() if len(v) > 1}, 'duplicate_meta_descriptions': {k: v for k, v in descriptions.items() if len(v) > 1}, 'thin_content_urls': thin_urls, 'all_tracking_identifiers': sorted(all_identifiers), 'cms_technical_domains': sorted(cms_domains)}
	return r
# 2026-10-30 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Harden answer-prepare against CHECKPOINT context compaction data loss, ad-hoc shell HTTP bypasses, and mature-project journal deadlocks":
# https://github.com/dmitry-ai/harness/issues/21
def collect_http(root, url, *, profile='html', scope='public', refresh_reason=None, max_age=86400, headers=None, context=None, fetcher=None, browser='auto', cdp_port=None, cdp_fetcher=None, http_get=None, cdp_call=None):
	if browser not in BROWSER_MODES:
		raise ValueError(f'Unknown browser mode: {browser}; choose {BROWSER_MODES}')
	effective_profile = 'document' if 'auto' == profile else profile
	if effective_profile not in PROFILES:
		raise ValueError(f'Unknown extraction profile: {profile}')
	if 'always' == browser:
		return collect_browser(root, url, profile=profile, scope=scope, refresh_reason=refresh_reason, max_age=max_age, cdp_port=cdp_port, context=context, cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call)
	observation = collect(root, url, headers=headers, scope=scope, max_age=max_age, refresh_reason=refresh_reason, fetcher=fetcher, context=context)
	item = {k: observation.get(k) for k in ('url', 'final_url', 'cached', 'observation', 'status', 'kind', 'collector', 'content_type', 'observed_at', 'error', 'error_kind', 'dns_resolved')}
	if not observation.get('error') and 200 <= (observation.get('status') or 0) < 300:
		chosen = 'document' if profile in ('html', 'auto') and 'application/json' == (observation.get('content_type') or '').lower() else effective_profile
		try:
			item.update(extract_observation(root, observation['observation'], chosen))
		except (OSError, ValueError, KeyError, TypeError, LookupError) as exc:
			item['extraction_error'] = type(exc).__name__
			item['detail'] = 'Response saved; inspect the source or choose another extraction profile, without fetching it again'
	needs_browser = observation.get('status') in (401, 403, 429) or bool(item.get('browser_check_required'))
	if 'auto' == browser and needs_browser and (None is fetcher or any((None is not x for x in (cdp_fetcher, http_get, cdp_call)))):
		dom_item = collect_browser(root, url, profile=profile, scope=scope, refresh_reason=refresh_reason or 'browser fallback after HTTP challenge or empty body', max_age=max_age, cdp_port=cdp_port, context=context, cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call)
		if not dom_item.get('error') and (not dom_item.get('extraction_error')):
			dom_item['http_observation'] = item.get('observation')
			dom_item['http_status'] = item.get('status')
			dom_item['browser_fallback'] = True
			dom_item['browser_fallback_from_http'] = True
			return dom_item
		item['browser_fallback_attempted'] = True
		item['browser_fallback_error'] = dom_item.get('error') or dom_item.get('extraction_error')
	r = item
	return r
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
def collect_plan(root, plan, *, fetcher=None, browser='auto', cdp_port=None, cdp_fetcher=None, http_get=None, cdp_call=None):
	if browser not in BROWSER_MODES:
		raise ValueError(f'Unknown browser mode: {browser}; choose {BROWSER_MODES}')
	if not isinstance(plan, dict) or not isinstance(plan.get('requests'), list) or (not plan['requests']):
		raise ValueError('Plan needs a nonempty requests list')
	results = []
	for entry in plan['requests']:
		try:
			if not isinstance(entry, dict):
				raise ValueError('Each request must be an object')
			profile = entry.get('profile', 'html')
			if profile not in PROFILES:
				raise ValueError('Unknown extraction profile')
			req_browser = entry.get('browser', browser)
			if req_browser not in BROWSER_MODES:
				raise ValueError(f'Unknown browser mode: {req_browser}')
			if 'always' == req_browser:
				item = collect_browser(root, entry['url'], profile=profile, scope=entry.get('scope', 'public'), max_age=entry.get('max_age', 86400), refresh_reason=entry.get('refresh_reason'), cdp_port=cdp_port, context=entry.get('context'), cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call)
			else:
				observation = collect(root, entry['url'], headers=entry.get('headers'), scope=entry.get('scope', 'public'), max_age=entry.get('max_age', 86400), refresh_reason=entry.get('refresh_reason'), fetcher=fetcher, context=entry.get('context'))
				item = {k: observation.get(k) for k in ('url', 'cached', 'observation', 'status', 'kind', 'collector', 'observed_at', 'error', 'error_kind', 'dns_resolved')}
				if not observation['error'] and 200 <= observation['status'] < 300:
					try:
						item.update(extract_observation(root, observation['observation'], profile))
					except (OSError, ValueError, KeyError, TypeError, LookupError) as exc:
						item['extraction_error'] = type(exc).__name__
						item['detail'] = 'Response saved; inspect the source or choose another extraction profile, without fetching it again'
				needs_browser = observation.get('status') in (401, 403, 429) or bool(item.get('browser_check_required'))
				if 'auto' == req_browser and needs_browser and (None is fetcher or any((None is not x for x in (cdp_fetcher, http_get, cdp_call)))):
					dom_item = collect_browser(root, entry['url'], profile=profile, scope=entry.get('scope', 'public'), max_age=entry.get('max_age', 86400), refresh_reason=entry.get('refresh_reason') or 'browser fallback after HTTP challenge or empty body', cdp_port=cdp_port, context=entry.get('context'), cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call)
					if not dom_item.get('error') and (not dom_item.get('extraction_error')):
						dom_item['http_observation'] = item.get('observation')
						dom_item['http_status'] = item.get('status')
						dom_item['browser_fallback'] = True
						dom_item['browser_fallback_from_http'] = True
						item = dom_item
					else:
						item['browser_fallback_attempted'] = True
						item['browser_fallback_error'] = dom_item.get('error') or dom_item.get('extraction_error')
			results.append(item)
		except (OSError, ValueError, KeyError, TypeError) as exc:
			results.append({'error': type(exc).__name__, 'detail': 'Invalid or unavailable input; check this plan entry', 'request_index': len(results)})
	r = {'results': results, 'site_summary': compute_site_summary(root, results), 'complete': all((not x.get('error') and ('dom' == x.get('kind') or (x.get('status') or 0) > 0) for x in results)), 'content_available_for_all': all((not x.get('error') and (not x.get('extraction_error')) and ('dom' == x.get('kind') or 200 <= (x.get('status') or 0) < 300) and (not x.get('browser_check_required')) for x in results)), 'detail': 'A saved HTTP 403/404 is a completed observation, not a reason to repeat the same request blindly'}
	return r
