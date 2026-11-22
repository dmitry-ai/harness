# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace getElementById with querySelector in read-only CDP registry and verify on live headless Chromium":
# https://github.com/dmitry-ai/harness/issues/130
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
# https://github.com/dmitry-ai/harness/issues/113
# 2026-11-21 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add compact evidence-query command and unify collect-http CLI flags":
# https://github.com/dmitry-ai/harness/issues/118
# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
# 2026-11-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
# https://github.com/dmitry-ai/harness/issues/81
# 2026-11-16 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Deduplicate HTTP/CDP collection pipeline with browser fallback, extraction cache, and CDP primitives across research.py and text_browser.py":
# https://github.com/dmitry-ai/harness/issues/66
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
import html as html_lib
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
HTTP_DEFAULT_ACCEPT = 'text/html,application/xhtml+xml,text/markdown;q=0.9,*/*;q=0.8'
_CHALLENGE_RE = re.compile('(?i)__LS_SEQ_LOADER__|name=["\\\']?(?:js_challenge|jsc_token|cf_captcha_kind|md_challenge)\\b|id=["\\\']?(?:challenge-form|challenge-running|cf-challenge-running|challenge-error-text|trk_jschal_js)\\b|class=["\\\'][^"\\\']*\\bcf-browser-verification\\b')
_CHALLENGE_DOM_RE = re.compile('(?is)__LS_SEQ_LOADER__|<[^>]+\\b(?:name=["\\\']?(?:js_challenge|jsc_token|cf_captcha_kind|md_challenge)\\b|id=["\\\']?(?:challenge-form|challenge-running|cf-challenge-running|challenge-error-text|trk_jschal_js)\\b|class=["\\\'][^"\\\']*\\bcf-browser-verification\\b)')
_CHALLENGE_ACTIVE_SCRIPT_RE = re.compile('(?is)<script\\b[^>]*>[^<]*\\b_cf_chl_opt\\s*=|<iframe\\b[^>]*\\bsrc=["\\\'][^"\\\']*challenges\\.cloudflare\\.com/cdn-cgi/challenge-platform/')
_PASSIVE_JSD_SCRIPT_RE = re.compile('(?is)<script\\b[^>]*\\bsrc=["\\\'][^"\\\']*/cdn-cgi/challenge-platform/[^"\\\']*/(?:jsd|precursor)/[^"\\\']*["\\\'][^>]*>\\s*</script>')
_CHALLENGE_TITLE_RE = re.compile('(?i)^(?:just a moment\\.{0,3}|attention required!\\s*\\|\\s*cloudflare|verify you are human|checking your (?:browser|site connection)(?:\\.{0,3}| before accessing.*)|one more step|ddos-guard|security check|access denied)$')
_CHALLENGE_COPY_RE = re.compile('(?i)verify you are human|checking your browser|checking if the site connection is secure|enable javascript and cookies to continue|please stand by,? while we are checking your browser')
_CHALLENGE_TOKEN_RE = re.compile('(?i)_cf_chl_opt|challenge-platform|challenges\\.cloudflare\\.com/turnstile|cf-chl-bypass|ray id')
def extractor_version():
	return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
def classify_html_challenge(raw_html: str, *, parsed: dict | None=None, status: int | None=None) -> bool:
	if not isinstance(raw_html, str):
		return False
	if None is not parsed and None is not parsed.get('sitemap'):
		return False
	stripped = raw_html.lstrip()
	if None is parsed and (stripped.startswith('<?xml') or '<urlset' in stripped[:1500] or '<sitemapindex' in stripped[:1500]) and (None is not _extract_sitemap(raw_html)):
		return False
	no_comments = re.sub('<!--.*?-->', ' ', raw_html, flags=re.S)
	visible_html = re.sub('(?is)<(?:script|style|noscript|template)\\b[^>]*>.*?</(?:script|style|noscript|template)>', ' ', no_comments)
	visible_plain = re.sub('(?is)<(?:head|title)\\b[^>]*>.*?</(?:head|title)>|<[^>]+>', ' ', visible_html)
	visible_words = len(re.findall('\\w+', html_lib.unescape(visible_plain)))
	if 0 == visible_words or (None is not parsed and None is parsed.get('sitemap') and (0 == parsed.get('word_count', 0))):
		return True
	non_code_raw = _PASSIVE_JSD_SCRIPT_RE.sub(' ', re.sub('(?is)<(?:code|pre)\\b[^>]*>.*?</(?:code|pre)>', ' ', no_comments))
	if _CHALLENGE_ACTIVE_SCRIPT_RE.search(non_code_raw):
		return True
	non_code_html = re.sub('(?is)<(?:script|style|noscript|template)\\b[^>]*>.*?</(?:script|style|noscript|template)>', ' ', non_code_raw)
	non_code_plain = re.sub('(?is)<(?:head|title)\\b[^>]*>.*?</(?:head|title)>|<[^>]+>', ' ', non_code_html)
	if _CHALLENGE_DOM_RE.search(non_code_html) or ('__LS_SEQ_LOADER__' in non_code_raw and visible_words < 200):
		return True
	title_str = (parsed.get('title') or '').strip() if isinstance(parsed, dict) else ''
	if not title_str:
		m_title = re.search('<title\\b[^>]*>(.*?)</title>', no_comments[:16000], flags=re.I | re.S)
		if m_title:
			title_str = ' '.join(html_lib.unescape(re.sub('<[^>]+>', ' ', m_title.group(1))).split())
	if title_str and _CHALLENGE_TITLE_RE.fullmatch(title_str):
		return True
	if status in (401, 403, 429, 503) and (_CHALLENGE_TOKEN_RE.search(non_code_raw) or _CHALLENGE_COPY_RE.search(non_code_plain)):
		return True
	if visible_words < 160 and _CHALLENGE_COPY_RE.search(non_code_plain) and (_CHALLENGE_TOKEN_RE.search(non_code_raw) or visible_words < 60):
		return True
	return False
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
		rel_p = Path(relative)
		if rel_p.is_absolute() and (not target.exists()):
			from .path_registry import _path_key, load_registry, same_project_root
			reg = load_registry()
			for anc in target.parents:
				if _path_key(anc) in reg.relocations and same_project_root(anc, root, registry=reg):
					tail = target.relative_to(anc)
					if 2 <= len(tail.parts) and '_' == tail.parts[0] and '\ua616' == tail.parts[1] and (not (root / '_').exists()):
						tail = Path(*tail.parts[1:])
					mapped = (root / tail).resolve()
					if mapped.is_relative_to(root):
						return mapped
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
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	directory = pp.data_dir
	path = pp.metrics_json
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
def collect(root, url, *, headers=None, scope='public', max_age=86400, refresh_reason=None, timeout=15, fetcher=None, observation_kind='http', context=None, extra_meta=None):
	root = Path(root).resolve()
	if max_age < 0 or timeout <= 0 or (not isinstance(scope, str)) or (not scope.strip()):
		raise ValueError('Nonnegative max_age, positive timeout and explicit request scope required')
	caller_headers = dict(headers or {})
	if not all((isinstance(k, str) and isinstance(v, str) for k, v in caller_headers.items())):
		raise ValueError('Request headers must contain string keys and values')
	has_accept = any(('accept' == k.lower() for k in caller_headers))
	headers = {'User-Agent': 'UpworkResearch/2.0', **caller_headers}
	legacy_headers = dict(headers) if 'http' == observation_kind and (not has_accept) else None
	if 'http' == observation_kind and (not has_accept):
		headers['Accept'] = HTTP_DEFAULT_ACCEPT
	if observation_kind not in ('http', 'dom') or ('dom' == observation_kind and None is fetcher):
		raise ValueError('DOM observation needs an explicit read-only browser capture')
	context = request_context(context)
	url, key = request_key(url, headers, scope + ':' + observation_kind, context)
	legacy_key = request_key(url, legacy_headers, scope + ':' + observation_kind, context)[1] if None is not legacy_headers else None
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	root = pp.root
	data_dir = pp.data_dir
	index_file = pp.http_index_json
	with locked(data_dir / ('http-' + key[:24] + '.lock'), timeout=max(30, timeout + 15)):
		index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {}
		entry = index.get(key) or (index.get(legacy_key) if legacy_key else None)
		if entry and (not refresh_reason) and (max_age > 0):
			meta = load_observation(root, entry['observation'])
			needs_dom_identity = 'dom' == observation_kind and isinstance(extra_meta, dict) and (not meta.get('cdp_identity'))
			ttl = min(max_age, 300) if meta.get('error') or (None is not meta.get('status') and meta.get('status', 0) >= 400) else max_age
			if (not needs_dom_identity) and time.time() - datetime.fromisoformat(meta['observed_at']).timestamp() <= ttl:
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
		except PermissionError:
			raise
		except (OSError, ValueError, RuntimeError) as exc:
			response = Response(url, 0, 'application/octet-stream', b'')
			error = type(exc).__name__
			error_kind, dns_resolved = classify_network_error(exc)
		folder = pp.evidence_dir / 'HTTP' / key[:24] / uuid.uuid4().hex
		folder.mkdir(parents=True, exist_ok=False)
		create_bytes(folder / 'response.bin', response.body)
		meta = {'schema_version': 1, 'kind': observation_kind, 'request_key': key, 'url': url, 'final_url': response.url, 'method': 'GET' if 'http' == observation_kind else 'READ_DOM', 'request_scope': scope, 'observed_at': when, 'status': response.status if 'http' == observation_kind else None, 'http_status_verified': 'http' == observation_kind and response.status > 0, 'content_type': response.content_type, 'charset': response.charset, 'redirects': list(response.redirects), 'body_sha256': hashlib.sha256(response.body).hexdigest(), 'body_bytes': len(response.body), 'refresh_reason': refresh_reason, 'error': error, 'error_kind': error_kind, 'dns_resolved': dns_resolved, 'conditions': {'header_names': sorted((k.lower() for k in headers)), 'values_fingerprint': key, 'reported_context': context, 'context_fingerprint': _fingerprint(context)}, 'collector': 'read-only-http' if 'http' == observation_kind else 'read-only-dom', 'interaction_checked': False}
		if isinstance(extra_meta, dict):
			for k in ('cdp_identity', 'cdp_identity_sha256'):
				if isinstance(extra_meta.get(k), str) and extra_meta[k]:
					meta[k] = extra_meta[k]
		create_bytes(folder / 'observation.json', json_data(meta))
		reference = (folder / 'observation.json').relative_to(pp.kb_dir).as_posix()
		with locked(data_dir / 'http-index.lock'):
			index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {}
			index[key] = {'observation': reference}
			replace_bytes(index_file, json_data(index))
		return observed_use(root, {'cached': False, 'observation': reference, **meta})
def load_observation(root, reference):
	from .path_registry import project_paths
	kb_dir = project_paths(root, exact_root=True).kb_dir.resolve()
	file = inside(kb_dir, urldefrag(reference)[0])
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
		hidden_ctx = bool({f['tag'] for f in self.stack} & {'head', 'script', 'style', 'noscript', 'template', 'svg'}) or tag in ('head', 'script', 'style', 'noscript', 'template', 'svg')
		parent_frame = self.stack[-1] if self.stack else None
		anchor = attrs.get('id') or (attrs.get('name') if 'a' == tag else None)
		if anchor:
			self.anchors.append(anchor)
			self.anchor_ranges.setdefault(anchor, []).append({'start': self.position, 'end': self.position if is_void else None, 'tag': tag, 'parent': parent_frame, 'hidden': hidden_ctx})
			if not hidden_ctx:
				for frame in self.stack:
					if not frame['hidden']:
						frame['anchors'].append(anchor)
				if self.heading:
					self.heading['_child_anchors'].append(anchor)
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
		if re.fullmatch('h[1-6]', tag) and (not hidden_ctx):
			position = self.position
			for section in self.section_ranges:
				if None is section['end'] and section['level'] >= int(tag[1]):
					section['end'] = position
			self.heading = {'level': int(tag[1]), 'text': '', 'anchor': attrs.get('id'), 'ancestor_anchors': [x['anchor'] for x in self.stack if x['anchor'] and (not x['hidden'])], 'start': position, 'end': None, '_head_end': None, '_frames': list(self.stack), '_child_anchors': [anchor] if anchor else []}
			self.section_ranges.append(self.heading)
		if not is_void:
			self.stack.append({'tag': tag, 'anchor': anchor if not hidden_ctx else None, 'raw_anchor': anchor, 'hidden': hidden_ctx, 'start': self.position, 'end': None, 'anchors': [anchor] if anchor and (not hidden_ctx) else []})
	def handle_endtag(self, tag):
		if 'a' == tag and None is not self.link:
			self.link['text'] = ' '.join(self.link['text'].split())
			self.links.append(self.link)
			self.link = None
		if self.heading and re.fullmatch('h[1-6]', tag):
			self.heading['text'] = ' '.join(self.heading['text'].split())
			self.heading['_head_end'] = self.position
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
			if self.stack[i]['tag'] == tag:
				for frame in self.stack[i:]:
					frame['end'] = self.position
					anchor = frame['raw_anchor']
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
		tags = {frame['tag'] for frame in self.stack}
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
		raw_anchor_ranges = {anchor: [[x['start'], plain_len if None is x['end'] else x['end']] for x in ranges] for anchor, ranges in self.anchor_ranges.items()}
		ambiguous_set = {anchor for anchor, ranges in raw_anchor_ranges.items() if len(ranges) > 1}
		def _strip_glyphs(seg):
			return re.sub('[#\u00b6\u00a7\U0001f517\\s]+', '', seg)
		sec_anchor_lists = [[] for _ in self.section_ranges]
		container_anchor_lists = [[] for _ in self.section_ranges]
		claimed_anchors = set()
		for idx, h in enumerate(self.section_ranges):
			head_end = h['start'] if None is h.get('_head_end') else h['_head_end']
			sec_end = plain_len if None is h['end'] else h['end']
			cands = []
			cont_cands = []
			if h.get('anchor'):
				cands.append(h['anchor'])
				claimed_anchors.add(h['anchor'])
			for ca in h.get('_child_anchors') or []:
				if ca not in cands:
					cands.append(ca)
				claimed_anchors.add(ca)
			for frame in h.get('_frames') or []:
				if frame.get('hidden') or not frame.get('anchor'):
					continue
				f_start = frame['start']
				f_end = plain_len if None is frame['end'] else frame['end']
				top_heading_only = all((oh is h or oh['level'] > h['level'] for oh in self.section_ranges if f_start <= oh['start'] and (oh['start'] if None is oh.get('_head_end') else oh['_head_end']) <= f_end))
				is_full_doc = '' == _strip_glyphs(plain[:f_start]) and '' == _strip_glyphs(plain[f_end:])
				if top_heading_only and frame['tag'] not in ('html', 'body', 'main', 'footer', 'nav', 'aside') and (not (is_full_doc and frame['tag'] not in ('section', 'article'))) and ('' == _strip_glyphs(plain[f_start:h['start']])) and ('' == _strip_glyphs(plain[head_end:f_end])):
					if frame['anchor'] not in cands:
						cands.append(frame['anchor'])
					claimed_anchors.add(frame['anchor'])
				elif top_heading_only and (frame['tag'] not in ('html', 'body', 'main', 'header', 'footer', 'nav', 'aside')) and (not (is_full_doc and frame['tag'] not in ('section', 'article'))) and ('' == _strip_glyphs(plain[f_start:h['start']])):
					if '' == _strip_glyphs(plain[min(f_end, sec_end):max(f_end, sec_end)]):
						if frame['anchor'] not in cands:
							cands.append(frame['anchor'])
						claimed_anchors.add(frame['anchor'])
					elif head_end < f_end <= sec_end:
						if frame['anchor'] not in cont_cands:
							cont_cands.append(frame['anchor'])
			sec_anchor_lists[idx] = cands
			container_anchor_lists[idx] = cont_cands
		for anchor, span_objs in self.anchor_ranges.items():
			if anchor in ambiguous_set or anchor in claimed_anchors or 1 != len(span_objs):
				continue
			sp = span_objs[0]
			if sp.get('hidden') or sp.get('tag') not in ('a', 'span'):
				continue
			a_start = sp['start']
			a_end = plain_len if None is sp['end'] else sp['end']
			seg = plain[a_start:a_end]
			if '' != _strip_glyphs(seg):
				continue
			has_glyph = '' != seg.strip()
			if has_glyph:
				prev_idx = next((idx for idx in range(len(self.section_ranges) - 1, -1, -1) if (self.section_ranges[idx]['start'] if None is self.section_ranges[idx].get('_head_end') else self.section_ranges[idx]['_head_end']) <= a_start and '' == plain[self.section_ranges[idx]['start'] if None is self.section_ranges[idx].get('_head_end') else self.section_ranges[idx]['_head_end']:a_start].strip() and (sp.get('parent') is (self.section_ranges[idx]['_frames'][-1] if self.section_ranges[idx].get('_frames') else None))), None)
				if None is not prev_idx and anchor not in sec_anchor_lists[prev_idx]:
					sec_anchor_lists[prev_idx].append(anchor)
				continue
			next_idx = next((idx for idx, h in enumerate(self.section_ranges) if a_end <= h['start'] and '' == plain[a_end:h['start']].strip() and (sp.get('parent') is (h['_frames'][-1] if h.get('_frames') else None))), None)
			if None is not next_idx:
				if anchor not in sec_anchor_lists[next_idx]:
					sec_anchor_lists[next_idx].append(anchor)
				continue
			for idx, h in enumerate(self.section_ranges):
				head_end = h['start'] if None is h.get('_head_end') else h['_head_end']
				sec_end = plain_len if None is h['end'] else h['end']
				if head_end <= a_start < sec_end and '' == plain[head_end:a_start].strip() and (sp.get('parent') is (h['_frames'][-1] if h.get('_frames') else None)):
					if anchor not in sec_anchor_lists[idx]:
						sec_anchor_lists[idx].append(anchor)
					break
		anchor_ranges = dict(raw_anchor_ranges)
		anchor_content = {anchor: [plain[s:e] for s, e in ranges] for anchor, ranges in raw_anchor_ranges.items()}
		all_anchors = set(self.anchors)
		gh_aliases = {}
		for anchor in sorted(set(self.anchors)):
			if anchor.startswith('user-content-') and len(anchor) > 13:
				gh_aliases.setdefault(anchor[13:], []).append(anchor)
		for alias, sources in gh_aliases.items():
			if alias not in raw_anchor_ranges:
				all_anchors.add(alias)
				merged_ranges = [rng for src in sources for rng in raw_anchor_ranges.get(src, [])]
				anchor_ranges[alias] = merged_ranges
				anchor_content[alias] = [plain[s:e] for s, e in merged_ranges]
				if len(merged_ranges) > 1 or any((src in ambiguous_set for src in sources)):
					ambiguous_set.add(alias)
		sections = []
		clean_headings = []
		for idx, h in enumerate(self.section_ranges):
			sec_end = plain_len if None is h['end'] else h['end']
			expanded = []
			for a in sec_anchor_lists[idx]:
				if a not in ambiguous_set and a not in expanded:
					expanded.append(a)
				if a.startswith('user-content-') and len(a) > 13:
					alias = a[13:]
					if (alias not in raw_anchor_ranges or alias in sec_anchor_lists[idx]) and alias not in ambiguous_set and (alias not in expanded):
						expanded.append(alias)
			cont_valid = [a for a in container_anchor_lists[idx] if a not in ambiguous_set]
			base_h = {k: v for k, v in h.items() if not k.startswith('_')}
			clean_headings.append({**base_h, 'end': sec_end, 'section_anchors': expanded, 'container_anchors': cont_valid})
			sections.append({**base_h, 'end': sec_end, 'section_anchors': expanded, 'container_anchors': cont_valid, 'content': plain[h['start']:sec_end]})
		word_count = len(re.findall('\\w+', clean_text))
		site_name = (self.meta.get('og:site_name') or '').strip()
		total_imgs = len(self.images)
		empty_alt = sum((1 for img in self.images if not (img.get('alt') or '').strip()))
		filename_alt = sum((1 for img in self.images if (img.get('alt') or '').strip() and re.search('(?i)\\.(?:jpe?g|png|gif|webp|avif|svg|bmp|tiff?)\\b', (img.get('alt') or '').strip())))
		repeated_site_alt = sum((1 for img in self.images if site_name and (img.get('alt') or '').strip().lower() == site_name.lower()))
		descriptive_alt = max(0, total_imgs - empty_alt - filename_alt - repeated_site_alt)
		h1_count = sum((1 for h in clean_headings if 1 == h.get('level')))
		meta_desc = self.meta.get('description', '')
		spaced_brand = bool(re.search('\\b(?:[A-Za-z]\\s+){3,}[A-Za-z]\\b', (self.meta.get('og:site_name') or '') + ' ' + json.dumps(self.json_ld, ensure_ascii=False)))
		json_ld_types = [item.get('@type') for item in self.json_ld if isinstance(item, dict) and item.get('@type')]
		empty_json_ld_desc = any((isinstance(item, dict) and 'description' in item and (not str(item.get('description') or '').strip()) for item in self.json_ld))
		insecure_json_ld_img = any((isinstance(item, dict) and isinstance(item.get('image'), str) and (item['image'].startswith('http://') or item['image'].startswith('//') or item['image'].startswith('/')) for item in self.json_ld))
		r = {'title': title_str, 'meta': self.meta, 'meta_all': self.meta_all, 'canonical': self.canonical, 'headings': clean_headings, 'anchors': sorted(all_anchors), 'links': self.links, 'scripts': self.scripts, 'images': self.images, 'image_alt_summary': {'total': total_imgs, 'empty_alt': empty_alt, 'filename_like_alt': filename_alt, 'repeated_site_name_alt': repeated_site_alt, 'descriptive_alt': descriptive_alt}, 'embeds': self.embeds, 'word_count': word_count, 'seo_diagnostics': {'h1_count': h1_count, 'missing_h1': 0 == h1_count, 'multiple_h1': h1_count > 1, 'title_length': len(title_str), 'overlong_title': len(title_str) > 65, 'meta_description_length': len(meta_desc), 'missing_meta_description': not bool(meta_desc.strip()), 'spaced_brand_name': spaced_brand, 'json_ld_types': json_ld_types, 'empty_json_ld_description': empty_json_ld_desc, 'insecure_or_relative_json_ld_image': insecure_json_ld_img}, 'json_ld': self.json_ld, 'sections': sections, 'anchor_ranges': anchor_ranges, 'anchor_content': anchor_content, 'ambiguous_anchors': sorted(ambiguous_set), 'text': clean_text}
		return r
def extract_markdown(text: str) -> dict:
	from collections import Counter
	from markdown_it import MarkdownIt
	from .links import parse_markdown_headings, references
	headings_meta, md_anchors, md_ambiguous, doc_title = parse_markdown_headings(text)
	doc_links, html_anchors = references(text)
	raw_lines = text.splitlines(keepends=True)
	line_offsets = [0]
	for ln in raw_lines:
		line_offsets.append(line_offsets[-1] + len(ln))
	masked_lines = list(raw_lines)
	for tok in MarkdownIt('commonmark', {'html': True}).parse(text):
		if tok.type in ('fence', 'code_block') and tok.map:
			for li in range(max(0, tok.map[0]), min(len(masked_lines), tok.map[1])):
				masked_lines[li] = ' ' * len(masked_lines[li])
	masked_text = re.sub('`+[^`]*`+', lambda m: ' ' * len(m.group(0)), ''.join(masked_lines))
	html_counts = Counter(html_anchors)
	ambiguous_set = set(md_ambiguous) | {a for a, cnt in html_counts.items() if 1 < cnt} | (set(html_anchors) & set(md_anchors))
	all_anchors = set(md_anchors) | set(html_anchors)
	clean_headings = []
	sections = []
	anchor_ranges = {}
	anchor_content = {}
	for idx, h in enumerate(headings_meta):
		start_line = h['start_line']
		end_line = next((nh['start_line'] for nh in headings_meta[idx + 1:] if nh['level'] <= h['level']), len(raw_lines))
		c_start = line_offsets[min(start_line, len(raw_lines))]
		c_end = line_offsets[min(end_line, len(raw_lines))]
		raw_sec = ''.join(raw_lines[start_line:end_line])
		unesc_sec = html_lib.unescape(raw_sec)
		sec_text = raw_sec if unesc_sec == raw_sec else raw_sec + '\n' + unesc_sec
		sec_anchors = [a for a in h['section_anchors'] if a not in ambiguous_set]
		entry = {'level': h['level'], 'text': h['text'], 'anchor': h['anchor'] if h['anchor'] not in ambiguous_set else None, 'ancestor_anchors': [], 'section_anchors': sec_anchors, 'container_anchors': [], 'start': c_start, 'end': c_end}
		clean_headings.append(entry)
		sections.append({**entry, 'content': sec_text})
		for a in h['section_anchors']:
			anchor_ranges.setdefault(a, []).append([c_start, c_end])
			anchor_content.setdefault(a, []).append(sec_text)
	for ha in sorted(set(html_anchors)):
		if ha not in md_anchors:
			pat = re.compile('\\b(?:id|name)=["\\\']' + re.escape(ha) + '["\\\']')
			for m in pat.finditer(masked_text):
				pos = m.start()
				enclosing = next((s for s in reversed(sections) if s['start'] <= pos < s['end']), None)
				s_end = enclosing['end'] if enclosing else len(text)
				seg = text[pos:s_end]
				unesc_seg = html_lib.unescape(seg)
				anchor_ranges.setdefault(ha, []).append([pos, s_end])
				anchor_content.setdefault(ha, []).append(seg if unesc_seg == seg else seg + '\n' + unesc_seg)
			if 1 < len(anchor_ranges.get(ha, [])):
				ambiguous_set.add(ha)
	unesc_full = html_lib.unescape(text)
	word_count = len(re.findall('\\w+', unesc_full))
	h1_count = sum((1 for h in clean_headings if 1 == h.get('level')))
	return {'title': doc_title, 'meta': {}, 'meta_all': {}, 'canonical': [], 'headings': clean_headings, 'anchors': sorted(all_anchors), 'links': [{'href': u, 'text': ''} for u in doc_links], 'scripts': [], 'images': [], 'image_alt_summary': {'total': 0, 'empty_alt': 0, 'filename_like_alt': 0, 'repeated_site_name_alt': 0, 'descriptive_alt': 0}, 'embeds': [], 'word_count': word_count, 'seo_diagnostics': {'h1_count': h1_count, 'missing_h1': 0 == h1_count, 'multiple_h1': h1_count > 1, 'title_length': len(doc_title), 'overlong_title': len(doc_title) > 65, 'meta_description_length': 0, 'missing_meta_description': True, 'spaced_brand_name': False, 'json_ld_types': [], 'empty_json_ld_description': False, 'insecure_or_relative_json_ld_image': False}, 'json_ld': [], 'sections': sections, 'anchor_ranges': anchor_ranges, 'anchor_content': anchor_content, 'ambiguous_anchors': sorted(ambiguous_set), 'browser_check_required': 0 == word_count, 'text': unesc_full}
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
def _write_cached_extraction(target, legacy_pattern, sha_key, sha_value, build_fn):
	version = extractor_version()
	target.parent.mkdir(parents=True, exist_ok=True)
	r = None
	if target.is_file():
		try:
			cached = json.loads(target.read_text(encoding='utf-8'))
			if isinstance(cached, dict) and version == cached.get('extractor_version') and (sha_value == cached.get(sha_key)):
				r = cached
		except (OSError, ValueError):
			r = None
	if None is r:
		r = build_fn(version)
		payload = json_data(r)
		if MAX_BYTES < len(payload):
			raise ValueError('Extracted JSON exceeds 16 MiB')
		if not target.exists():
			create_bytes(target, payload)
		else:
			replace_bytes(target, payload)
		for legacy in target.parent.glob(legacy_pattern):
			try:
				legacy.unlink()
			except OSError:
				pass
	return r
def extract_bytes(body, content_type, profile, charset='utf-8', *, status=None):
	if profile not in PROFILES:
		raise ValueError(f'Unknown profile: {profile}; choose {PROFILES}')
	ct_low = (content_type or '').split(';', 1)[0].strip().lower()
	is_md = ct_low in ('text/markdown', 'text/x-markdown')
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
		elif is_md and 'html' == profile:
			r = extract_markdown(text)
		elif 'document' == profile and ct_low not in ('text/html', 'application/xhtml+xml'):
			out = {'paragraphs': text.splitlines(), 'text': text, 'layout_checked': False}
			if is_md:
				md_info = extract_markdown(text)
				for k in ('title', 'headings', 'anchors', 'ambiguous_anchors', 'word_count', 'browser_check_required'):
					out[k] = md_info[k]
			elif 'application/json' == ct_low or text.lstrip().startswith(('{', '[')):
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
			result['browser_check_required'] = classify_html_challenge(text, parsed=result, status=status)
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
	from .path_registry import project_paths
	kb_dir = project_paths(root, exact_root=True).kb_dir.resolve()
	meta = load_observation(root, reference)
	folder = inside(kb_dir, urldefrag(reference)[0]).parent
	if meta.get('error') or ('http' == meta.get('kind', 'http') and (not 200 <= meta['status'] < 300)):
		raise ValueError('Observation is unavailable; preserve it and choose a different check method')
	target = folder / f'extracted-{profile}.json'
	data = _write_cached_extraction(target, f'extracted-{profile}-*.json', 'body_sha256', meta['body_sha256'], lambda version: {'profile': profile, 'extractor_version': version, 'observation': reference, 'body_sha256': meta['body_sha256'], 'observed_at': meta['observed_at'], **compact_extraction_for_disk(extract_bytes((folder / 'response.bin').read_bytes(), meta['content_type'], profile, meta.get('charset') or 'utf-8', status=meta.get('status')))})
	r = {'extraction': target.relative_to(kb_dir).as_posix(), 'observation': reference, 'profile': profile, 'observed_at': meta['observed_at']}
	if 'browser_check_required' in data:
		r['browser_check_required'] = bool(data['browser_check_required'])
	if 'word_count' in data:
		r['word_count'] = data['word_count']
	return r
def extract_file(root, file, profile='document'):
	import mimetypes
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	file = inside(pp.root, file)
	body = file.read_bytes()
	if MAX_BYTES < len(body):
		raise ValueError('Source file exceeds 16 MiB')
	kind = mimetypes.guess_type(file.name)[0] or 'text/plain'
	source_sha = hashlib.sha256(body).hexdigest()
	target = pp.evidence_dir / 'Extracted' / source_sha / f'{profile}.json'
	_write_cached_extraction(target, f'{profile}-*.json', 'source_sha256', source_sha, lambda version: {'profile': profile, 'source': file.relative_to(pp.root).as_posix(), 'source_sha256': source_sha, 'extractor_version': version, **compact_extraction_for_disk(extract_bytes(body, kind, profile))})
	return {'extraction': target.relative_to(pp.kb_dir.resolve()).as_posix(), 'source_sha256': source_sha}
def select_dom_tab(tabs, url, tab_id):
	matches = [t for t in tabs if 'page' == t.get('type') and t.get('id') == tab_id and (urldefrag(t.get('url', ''))[0] == urldefrag(url)[0])]
	if 1 != len(matches):
		raise ValueError('Explicit tab ID must match the exact requested URL; no navigation or account fallback')
	r = matches[0]
	return r
def capture_dom(root, url, tab_id, *, session_id=None, refresh_reason=None, context=None, config=None, guard=None):
	from .text_browser import GuardedCDP, MINIMAL_DOM_CAPTURE_EXPR, save_cdp_identity
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
	identity_ref, identity_hash = save_cdp_identity(root, {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'session_id': session_id, 'target_id': tab_id, 'browser_websocket': identity['browser']['websocket_url'], 'profile': identity['profile'], 'account': identity['account']})
	observed_context = dict(context or {})
	observed_context.setdefault('session_id', session_id)
	def read_dom(target, headers, timeout):
		native, actual_identity = guard.call('Runtime.evaluate', {'expression': MINIMAL_DOM_CAPTURE_EXPR, 'throwOnSideEffect': True, 'returnByValue': True}, include_identity=True)
		if actual_identity['browser']['websocket_url'] != identity['browser']['websocket_url'] or actual_identity['profile'] != identity['profile'] or actual_identity['account'] != identity['account'] or (actual_identity['target']['id'] != tab_id):
			raise ValueError('CDP identity changed during DOM capture; no content proof is issued')
		if not isinstance(native, dict) or native.get('exceptionDetails'):
			raise ValueError('Native DOM evaluation did not complete without side effects')
		data = native.get('result', {}).get('value')
		if not isinstance(data, dict) or not isinstance(data.get('html'), str) or urldefrag(data.get('url', ''))[0] != urldefrag(target)[0]:
			raise ValueError('Tab navigated or DOM capture does not match the intended resource')
		return Response(data['url'], 0, 'text/html', data['html'].encode('utf-8'))
	observation = collect(root, url, scope=f'CDP-session:{session_id}:tab:{tab_id}:identity:{identity_ref}', max_age=0, refresh_reason=refresh_reason, fetcher=read_dom, observation_kind='dom', context=observed_context, extra_meta={'cdp_identity': identity_ref, 'cdp_identity_sha256': identity_hash})
	extra = {} if observation['error'] else extract_observation(root, observation['observation'])
	return {**observation, **extra, 'cdp_identity': identity_ref, 'cdp_identity_sha256': identity_hash}
def collect_browser(root, url, *, profile='html', scope='public', session_id=None, refresh_reason=None, max_age=86400, cdp_port=None, timeout=15, context=None, config=None, http_get=None, cdp_call=None, cdp_fetcher=None, headless_shell=None):
	if isinstance(url, (list, tuple)):
		if 1 == len(url):
			url = url[0]
		else:
			return collect_browser_batch(root, url, profile=profile, scope=scope, session_id=session_id, refresh_reason=refresh_reason, max_age=max_age, cdp_port=cdp_port, timeout=timeout, context=context, config=config, http_get=http_get, cdp_call=cdp_call, cdp_fetcher=cdp_fetcher)
	from .text_browser import collect_cdp_dom
	effective_profile = 'document' if 'auto' == profile else profile
	if effective_profile not in PROFILES:
		raise ValueError(f'Unknown extraction profile: {profile}')
	effective_scope = f'CDP-session:{session_id.strip()}' if isinstance(session_id, str) and session_id.strip() and ('public' == scope) else scope
	observed_context = dict(context or {})
	if isinstance(session_id, str) and session_id.strip():
		observed_context.setdefault('session_id', session_id.strip())
	cdp_meta = {}
	def read_dom(target, headers, fetch_timeout):
		if None is not cdp_fetcher:
			capture = cdp_fetcher(root, target, cdp_port=cdp_port, timeout=fetch_timeout, config=config, http_get=http_get, cdp_call=cdp_call)
		else:
			capture = collect_cdp_dom(root, target, cdp_port=cdp_port, session_id=session_id, timeout=fetch_timeout, config=config, http_get=http_get, cdp_call=cdp_call, headless_shell=headless_shell)
		if not isinstance(capture, dict) or not isinstance(capture.get('html'), str):
			raise ValueError('CDP DOM capture did not return HTML payload')
		cdp_meta.update(capture)
		r = Response(capture.get('url') or target, 0, 'text/html', capture['html'].encode('utf-8'))
		return r
	observation = collect(root, url, scope=effective_scope, max_age=max_age, refresh_reason=refresh_reason, timeout=timeout, fetcher=read_dom, observation_kind='dom', context=observed_context or None, extra_meta=cdp_meta)
	item = {k: observation.get(k) for k in ('url', 'final_url', 'cached', 'observation', 'status', 'kind', 'collector', 'content_type', 'observed_at', 'error', 'error_kind', 'dns_resolved', 'cdp_identity', 'cdp_identity_sha256') if None is not observation.get(k) or k in ('url', 'final_url', 'cached', 'observation', 'status', 'kind', 'collector', 'content_type', 'observed_at', 'error', 'error_kind', 'dns_resolved')}
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
	from .path_registry import project_paths
	kb_dir = project_paths(root, exact_root=True).kb_dir
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
def collect_http(root, url, *, profile='html', scope='public', session_id=None, refresh_reason=None, max_age=86400, headers=None, context=None, fetcher=None, browser='auto', cdp_port=None, cdp_fetcher=None, http_get=None, cdp_call=None, headless_shell=None):
	if isinstance(url, (list, tuple)):
		if 1 == len(url):
			url = url[0]
		else:
			return collect_http_batch(root, url, profile=profile, scope=scope, session_id=session_id, refresh_reason=refresh_reason, max_age=max_age, headers=headers, context=context, fetcher=fetcher, browser=browser, cdp_port=cdp_port, cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call)
	if browser not in BROWSER_MODES:
		raise ValueError(f'Unknown browser mode: {browser}; choose {BROWSER_MODES}')
	effective_profile = 'document' if 'auto' == profile else profile
	if effective_profile not in PROFILES:
		raise ValueError(f'Unknown extraction profile: {profile}')
	if 'always' == browser:
		r = collect_browser(root, url, profile=profile, scope=scope, session_id=session_id, refresh_reason=refresh_reason, max_age=max_age, cdp_port=cdp_port, context=context, cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call, headless_shell=headless_shell)
	else:
		observation = collect(root, url, headers=headers, scope=scope, max_age=max_age, refresh_reason=refresh_reason, fetcher=fetcher, context=context)
		r = {k: observation.get(k) for k in ('url', 'final_url', 'cached', 'observation', 'status', 'kind', 'collector', 'content_type', 'observed_at', 'error', 'error_kind', 'dns_resolved')}
		ct_low = (observation.get('content_type') or '').lower()
		if not observation.get('error') and 200 <= (observation.get('status') or 0) < 300:
			chosen = 'document' if profile in ('html', 'auto') and 'application/json' == ct_low else effective_profile
			try:
				r.update(extract_observation(root, observation['observation'], chosen))
			except (OSError, ValueError, KeyError, TypeError, LookupError) as exc:
				r['extraction_error'] = type(exc).__name__
				r['detail'] = 'Response saved; inspect the source or choose another extraction profile, without fetching it again'
		is_static_non_html = 200 <= (observation.get('status') or 0) < 300 and any((ct_low.startswith(p) for p in ('application/json', 'application/xml', 'text/xml', 'application/pdf', 'application/zip', 'application/vnd.openxmlformats')))
		needs_browser = (not is_static_non_html) and (observation.get('status') in (401, 403, 429) or bool(r.get('browser_check_required')))
		if 'auto' == browser and needs_browser and (None is fetcher or any((None is not x for x in (cdp_fetcher, http_get, cdp_call)))):
			try:
				dom_item = collect_browser(root, url, profile=profile, scope=scope, session_id=session_id, refresh_reason=refresh_reason or 'browser fallback after HTTP challenge or empty body', max_age=max_age, cdp_port=cdp_port, context=context, cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call, headless_shell=headless_shell)
			except PermissionError as exc:
				dom_item = {'error': 'PermissionError', 'detail': str(exc)}
			if dom_item.get('error') or dom_item.get('extraction_error'):
				r['browser_fallback_attempted'] = True
				r['browser_fallback_error'] = dom_item.get('error') or dom_item.get('extraction_error')
			else:
				dom_item['http_observation'] = r.get('observation')
				dom_item['http_status'] = r.get('status')
				dom_item['browser_fallback'] = True
				dom_item['browser_fallback_from_http'] = True
				r = dom_item
	return r
# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
def collect_plan(root, plan, *, fetcher=None, browser='auto', cdp_port=None, session_id=None, cdp_fetcher=None, http_get=None, cdp_call=None):
	if browser not in BROWSER_MODES:
		raise ValueError(f'Unknown browser mode: {browser}; choose {BROWSER_MODES}')
	if not isinstance(plan, dict) or not isinstance(plan.get('requests'), list) or (not plan['requests']):
		raise ValueError('Plan needs a nonempty requests list')
	results = []
	shared_shell = {'instance': None}
	def _lazy_headless_fetcher(proj_root, target, *, cdp_port=None, timeout=15, config=None, http_get=None, cdp_call=None):
		from .text_browser import ManagedHeadlessShell, collect_cdp_dom
		if None is shared_shell['instance']:
			shared_shell['instance'] = ManagedHeadlessShell(config).__enter__()
		return collect_cdp_dom(proj_root, target, cdp_port=cdp_port, timeout=timeout, config=config, headless_shell=shared_shell['instance'])
	use_lazy_shell = None is cdp_fetcher and None is http_get and (None is cdp_call) and (None is cdp_port)
	try:
		for entry in plan['requests']:
			try:
				if not isinstance(entry, dict):
					raise ValueError('Each request must be an object')
				profile = entry.get('profile', 'html')
				if profile not in PROFILES and 'auto' != profile:
					raise ValueError('Unknown extraction profile')
				entry_sid = entry.get('session_id', session_id)
				eff_cdp_fetcher = _lazy_headless_fetcher if use_lazy_shell and (not entry_sid) else cdp_fetcher
				results.append(collect_http(root, entry['url'], profile=profile, scope=entry.get('scope', 'public'), session_id=entry_sid, refresh_reason=entry.get('refresh_reason'), max_age=entry.get('max_age', 86400), headers=entry.get('headers'), context=entry.get('context'), fetcher=fetcher, browser=entry.get('browser', browser), cdp_port=cdp_port, cdp_fetcher=eff_cdp_fetcher, http_get=http_get, cdp_call=cdp_call))
			except (OSError, ValueError, KeyError, TypeError) as exc:
				results.append({'error': type(exc).__name__, 'detail': 'Invalid or unavailable input; check this plan entry', 'request_index': len(results)})
	finally:
		if None is not shared_shell['instance']:
			shared_shell['instance'].close()
	return {'results': results, 'site_summary': compute_site_summary(root, results), 'complete': all((not x.get('error') and ('dom' == x.get('kind') or 0 < (x.get('status') or 0)) for x in results)), 'content_available_for_all': all((not x.get('error') and (not x.get('extraction_error')) and ('dom' == x.get('kind') or 200 <= (x.get('status') or 0) < 300) and (not x.get('browser_check_required')) for x in results)), 'detail': 'A saved HTTP 403/404 is a completed observation, not a reason to repeat the same request blindly'}
def collect_http_batch(root, urls, *, profile='auto', scope='public', session_id=None, refresh_reason=None, max_age=86400, headers=None, context=None, fetcher=None, browser='auto', cdp_port=None, cdp_fetcher=None, http_get=None, cdp_call=None):
	cleaned = [str(u).strip() for u in (urls or ()) if str(u).strip()]
	if not cleaned:
		raise ValueError('Provide at least one HTTP(S) URL')
	plan = {'requests': [{'url': u, 'profile': profile, 'scope': scope, 'session_id': session_id, 'refresh_reason': refresh_reason, 'max_age': max_age, 'headers': headers, 'context': context, 'browser': browser} for u in cleaned]}
	return collect_plan(root, plan, fetcher=fetcher, browser=browser, cdp_port=cdp_port, session_id=session_id, cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call)
def collect_browser_batch(root, urls, *, profile='html', scope='public', session_id=None, refresh_reason=None, max_age=86400, cdp_port=None, timeout=15, context=None, config=None, http_get=None, cdp_call=None, cdp_fetcher=None):
	cleaned = [str(u).strip() for u in (urls or ()) if str(u).strip()]
	if not cleaned:
		raise ValueError('Provide at least one HTTP(S) URL')
	results = []
	shared_shell = {'instance': None}
	use_lazy_shell = None is cdp_fetcher and None is http_get and (None is cdp_call) and (None is cdp_port) and (not session_id)
	try:
		for u in cleaned:
			try:
				if use_lazy_shell and None is shared_shell['instance']:
					from .text_browser import ManagedHeadlessShell
					shared_shell['instance'] = ManagedHeadlessShell(config).__enter__()
				results.append(collect_browser(root, u, profile=profile, scope=scope, session_id=session_id, refresh_reason=refresh_reason, max_age=max_age, cdp_port=cdp_port, timeout=timeout, context=context, config=config, http_get=http_get, cdp_call=cdp_call, cdp_fetcher=cdp_fetcher, headless_shell=shared_shell['instance']))
			except (OSError, ValueError, KeyError, TypeError) as exc:
				results.append({'url': u, 'error': type(exc).__name__, 'detail': str(exc)})
	finally:
		if None is not shared_shell['instance']:
			shared_shell['instance'].close()
	return {'results': results, 'site_summary': compute_site_summary(root, results), 'complete': all((not x.get('error') and ('dom' == x.get('kind') or 0 < (x.get('status') or 0)) for x in results)), 'content_available_for_all': all((not x.get('error') and (not x.get('extraction_error')) and ('dom' == x.get('kind') or 200 <= (x.get('status') or 0) < 300) and (not x.get('browser_check_required')) for x in results))}
def _norm_query_url(url: str) -> str:
	return urldefrag(str(url or '').strip())[0].rstrip('/')
def extract_github_blob_lines(raw_text: str) -> list[str]:
	if not raw_text:
		return []
	if 'react-app.embeddedData' in raw_text:
		for m in re.finditer('<script[^>]*data-target=["\\\']react-app\\.embeddedData["\\\'][^>]*>(.*?)</script>', raw_text, re.I | re.S):
			try:
				emb = json.loads(m.group(1))
			except ValueError:
				continue
			payload = emb.get('payload') if isinstance(emb, dict) else None
			if not isinstance(payload, dict):
				continue
			for cand in (payload.get('blob'), (payload.get('codeViewBlobLayoutRoute') or {}).get('blob') if isinstance(payload.get('codeViewBlobLayoutRoute'), dict) else None):
				if isinstance(cand, dict) and isinstance(cand.get('rawLines'), list):
					return [str(ln) for ln in cand['rawLines']]
	if 'LC' in raw_text:
		by_ln: dict[int, str] = {}
		for pat in ('<(td|div)\\b[^>]*\\bid=["\\\']LC(\\d+)["\\\'][^>]*>(.*?)</\\1>', '<(span)\\b[^>]*\\bid=["\\\']LC(\\d+)["\\\'][^>]*>(.*?)</\\1>'):
			for m_lc in re.finditer(pat, raw_text, re.I | re.S):
				ln_no = int(m_lc.group(2))
				if 1 <= ln_no <= 200000 and ln_no not in by_ln:
					by_ln[ln_no] = html_lib.unescape(re.sub('<[^>]+>', '', m_lc.group(3))).replace('\xa0', ' ').rstrip('\r\n')
			if by_ln:
				break
		if by_ln:
			max_ln = max(by_ln)
			return [by_ln.get(idx, '') for idx in range(1, max_ln + 1)]
	return []
_extract_github_blob_lines = extract_github_blob_lines
def _grep_blob_windows(blob_lines: list[str], rx: re.Pattern, *, has_lc_anchors: bool, context_lines: int = 2, max_matches: int = 20) -> list[dict]:
	hit_indices = [idx for idx, ln in enumerate(blob_lines) if rx.search(ln)]
	if not hit_indices:
		return []
	windows: list[list[int]] = []
	for idx in hit_indices:
		s = max(0, idx - context_lines)
		e = min(len(blob_lines) - 1, idx + context_lines)
		if windows and s <= windows[-1][1] + 1:
			windows[-1][1] = max(windows[-1][1], e)
		else:
			windows.append([s, e, idx])
		if len(windows) >= max_matches:
			break
	out: list[dict] = []
	for s, e, first_hit in windows[:max_matches]:
		s1, e1, hit1 = (s + 1, e + 1, first_hit + 1)
		range_anchor = f'#L{s1}' if s1 == e1 else f'#L{s1}-L{e1}'
		anchor = f'#LC{hit1}' if has_lc_anchors else range_anchor
		out.append({'line_start': s1, 'line_end': e1, 'hit_line': hit1, 'anchor': anchor, 'line_anchor': f'#LC{hit1}', 'range_anchor': range_anchor, 'heading': None, 'verbatim_context': '\n'.join(blob_lines[s:e + 1])})
	return out
def _grep_section_windows(sections: list[dict], fallback_text: str, rx: re.Pattern, *, context_lines: int = 2, max_matches: int = 20) -> list[dict]:
	out: list[dict] = []
	seen_snippets: set[str] = set()
	raw_units = sections if sections else ([{'level': None, 'text': None, 'section_anchors': [], 'content': fallback_text}] if fallback_text else [])
	units = sorted(raw_units, key=lambda s: (len(str(s.get('content') or '')), -(int(s.get('level') or 0)), -int(bool(s.get('section_anchors') or s.get('anchor')))))
	for sec in units:
		content = str(sec.get('content') or '')
		if not content or (not rx.search(content)):
			continue
		sec_anchors = [str(a) for a in (sec.get('section_anchors') or ()) if a]
		anchor_ref = f'#{sec_anchors[0]}' if sec_anchors else (f"#{sec['anchor']}" if sec.get('anchor') else None)
		heading = sec.get('text')
		lines = content.splitlines()
		hit_indices = [idx for idx, ln in enumerate(lines) if rx.search(ln)]
		if not hit_indices:
			snippet = content[:800].strip()
			if snippet and snippet not in seen_snippets:
				seen_snippets.add(snippet)
				out.append({'heading': heading, 'anchor': anchor_ref, 'line_start': 1, 'line_end': max(1, len(lines)), 'verbatim_context': snippet})
		else:
			windows: list[list[int]] = []
			for idx in hit_indices:
				s = max(0, idx - max(1, context_lines))
				e = min(len(lines) - 1, idx + max(1, context_lines))
				while s > 0 and lines[s - 1].strip() and (idx - s) < max(3, context_lines * 2):
					s -= 1
				while e + 1 < len(lines) and lines[e + 1].strip() and (e - idx) < max(3, context_lines * 2):
					e += 1
				if windows and s <= windows[-1][1] + 1:
					windows[-1][1] = max(windows[-1][1], e)
				else:
					windows.append([s, e])
			for s, e in windows:
				snippet = '\n'.join(lines[s:e + 1]).strip()
				if len(snippet) > 1200:
					m_in = rx.search(snippet)
					pos = m_in.start() if m_in else 0
					half = 550
					ws = max(0, pos - half)
					we = min(len(snippet), ws + 1100)
					snippet = snippet[ws:we].strip()
				if snippet and snippet not in seen_snippets:
					seen_snippets.add(snippet)
					out.append({'heading': heading, 'anchor': anchor_ref, 'line_start': s + 1, 'line_end': e + 1, 'verbatim_context': snippet})
					if len(out) >= max_matches:
						return out
		if len(out) >= max_matches:
			break
	return out
def _summarize_observation_bundle(obs_file: Path, kb_dir: Path, *, include_anchors: bool = False, rx: re.Pattern | None = None, context_lines: int = 2, max_matches: int = 20) -> dict | None:
	try:
		data = json.loads(obs_file.read_text(encoding='utf-8'))
	except (OSError, ValueError):
		return None
	if not isinstance(data, dict):
		return None
	url = str(data.get('url') or '').strip()
	final_url = str(data.get('final_url') or url).strip()
	status = data.get('status')
	kind = data.get('kind') or 'get'
	valid_status = not data.get('error') and ('dom' == kind or (isinstance(status, int) and 200 <= status < 300))
	is_shell_or_empty = False
	invalid_reason = None
	title = None
	h1_list: list[str] = []
	word_count = None
	raw_anchors: set[str] = set()
	ambiguous_anchors: set[str] = set()
	sections_list: list[dict] = []
	headings_list: list[dict] = []
	plain_text = ''
	cur_ver = extractor_version()
	resp_bin = obs_file.parent / 'response.bin'
	has_resp_bin = resp_bin.is_file()
	recheck_challenge = False
	ext_files = sorted(obs_file.parent.glob('extracted-*.json'))
	for ext_file in ext_files:
		try:
			ext = json.loads(ext_file.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			continue
		if not isinstance(ext, dict):
			continue
		if ext.get('extractor_version') != cur_ver and has_resp_bin:
			recheck_challenge = True
		elif True is ext.get('browser_check_required'):
			is_shell_or_empty = True
			invalid_reason = 'browser_check_required=True (JS/anti-bot challenge or empty SPA shell)'
		elif 'headings' in ext and None is ext.get('sitemap') and (0 == ext.get('word_count', 0)):
			is_shell_or_empty = True
			invalid_reason = 'word_count=0 (empty HTML shell)'
		t_cand = ' '.join(str(ext.get('title') or '').split())
		if t_cand and not title:
			title = t_cand
		if isinstance(ext.get('word_count'), int) and None is word_count:
			word_count = ext['word_count']
		if isinstance(ext.get('headings'), list):
			if not headings_list:
				headings_list = [h for h in ext['headings'] if isinstance(h, dict)]
			for h in ext['headings']:
				if isinstance(h, dict) and 1 == h.get('level') and h.get('text'):
					ht = ' '.join(str(h['text']).split())
					if ht and ht not in h1_list:
						h1_list.append(ht)
		if isinstance(ext.get('sections'), list) and (not sections_list):
			sections_list = [s for s in ext['sections'] if isinstance(s, dict)]
		if isinstance(ext.get('ambiguous_anchors'), list):
			ambiguous_anchors.update((str(a) for a in ext['ambiguous_anchors'] if a))
		if isinstance(ext.get('anchors'), list):
			for a in ext['anchors']:
				if a:
					a_str = str(a)
					raw_anchors.add(a_str)
					if a_str.startswith('user-content-') and 13 < len(a_str):
						raw_anchors.add(a_str[13:])
		if isinstance(ext.get('text'), str) and ext['text'].strip() and (not plain_text):
			plain_text = ext['text']
	blob_lines: list[str] = []
	raw_text = ''
	if has_resp_bin:
		try:
			if resp_bin.stat().st_size <= MAX_BYTES:
				raw_text = resp_bin.read_bytes().decode(data.get('charset') or 'utf-8', errors='replace')
				ctype = (data.get('content_type') or '').split(';', 1)[0].strip().lower()
				is_md = ctype in ('text/markdown', 'text/x-markdown')
				is_html = (not is_md) and ('html' in ctype or '<title' in raw_text[:4000].lower() or raw_text.lstrip().lower().startswith(('<!doctype html', '<html')))
				if is_md and (not ext_files):
					md_info = extract_markdown(raw_text)
					if 0 == md_info.get('word_count', 0):
						is_shell_or_empty = True
						invalid_reason = 'word_count=0 (empty Markdown response)'
					if md_info.get('title') and (not title):
						title = ' '.join(str(md_info['title']).split())
					if None is word_count:
						word_count = md_info.get('word_count')
					raw_anchors.update((str(a) for a in md_info.get('anchors') or [] if a))
					ambiguous_anchors.update((str(a) for a in md_info.get('ambiguous_anchors') or [] if a))
					sections_list = sections_list or list(md_info.get('sections') or [])
					headings_list = headings_list or list(md_info.get('headings') or [])
					plain_text = plain_text or str(md_info.get('text') or '')
				elif is_html:
					if (not ext_files or recheck_challenge) and classify_html_challenge(raw_text, status=status):
						is_shell_or_empty = True
						invalid_reason = 'unextracted HTML JS challenge or empty shell'
					for m_id in re.finditer('\\b(?:id|name)=["\\\']([^"\\\']+)["\\\']', raw_text, re.I):
						aid = m_id.group(1)
						raw_anchors.add(aid)
						if aid.startswith('user-content-') and 13 < len(aid):
							raw_anchors.add(aid[13:])
					if not title:
						m_t = re.search('<title[^>]*>(.*?)</title>', raw_text[:16000], re.I | re.S)
						if m_t:
							t_raw = html_lib.unescape(' '.join(m_t.group(1).split()))
							if t_raw:
								title = t_raw
					url_host = (urlsplit(final_url or url).hostname or '').lower()
					if 'github.com' == url_host and '/blob/' in (urlsplit(final_url or url).path or ''):
						blob_lines = _extract_github_blob_lines(raw_text)
				elif ('json' in ctype or raw_text.lstrip().startswith('{')) and valid_status and (not title):
					try:
						jbody = json.loads(raw_text)
						if isinstance(jbody, dict) and isinstance(jbody.get('title'), str) and jbody['title'].strip():
							title = ' '.join(jbody['title'].split())
						if not plain_text:
							plain_text = raw_text
					except ValueError:
						pass
				if not plain_text and (not is_html):
					plain_text = raw_text
		except OSError:
			pass
	if not title and h1_list:
		title = h1_list[0]
	lc_nums = sorted({int(m.group(1)) for a in raw_anchors if (m := re.fullmatch('LC(\\d+)', a))})
	has_lc_anchors = bool(lc_nums)
	gh_line_range = f'#LC{lc_nums[0]}..#LC{lc_nums[-1]}' if lc_nums else (f'#LC1..#LC{len(blob_lines)}' if blob_lines else None)
	valid_for_citation = bool(valid_status and (not is_shell_or_empty))
	if not valid_for_citation and (not invalid_reason):
		invalid_reason = f"error={data.get('error')} status={status}"
	rel_obs = obs_file.parent.relative_to(kb_dir).as_posix() if obs_file.parent.is_relative_to(kb_dir) else obs_file.parent.as_posix()
	entry: dict = {
		'url': url,
		'final_url': final_url,
		'observation': rel_obs,
		'kind': kind,
		'status': status,
		'valid_for_citation': valid_for_citation,
		'observed_at': data.get('observed_at'),
		'title': title,
		'h1': h1_list[0] if h1_list else None,
		'h1_headings': h1_list,
		'word_count': word_count,
	}
	if not valid_for_citation:
		entry['invalid_reason'] = invalid_reason
	if gh_line_range:
		entry['github_line_range'] = gh_line_range
		if blob_lines and (not has_lc_anchors):
			entry['line_anchor_hint'] = f'#L1-L{len(blob_lines)}'
	if include_anchors:
		semantic_anchors: list[str] = []
		for a in sorted(raw_anchors):
			if a in ambiguous_anchors or re.fullmatch('L(?:C)?\\d+(?:-L?(?:C)?\\d+)?', a):
				continue
			if a.startswith('user-content-') and 13 < len(a) and (a[13:] in raw_anchors):
				continue
			semantic_anchors.append(a)
		entry['anchors'] = semantic_anchors
		sec_idx = []
		for h in headings_list:
			sa = [str(x) for x in (h.get('section_anchors') or ()) if x and str(x) not in ambiguous_anchors]
			sec_idx.append({'level': h.get('level'), 'heading': h.get('text'), 'anchor': f'#{sa[0]}' if sa else (f"#{h['anchor']}" if h.get('anchor') else None)})
		entry['sections'] = sec_idx
	if None is not rx:
		if blob_lines:
			matches = _grep_blob_windows(blob_lines, rx, has_lc_anchors=has_lc_anchors, context_lines=context_lines, max_matches=max_matches)
		elif not rx.search(plain_text or raw_text):
			matches = []
		else:
			eff_sections = sections_list
			if eff_sections and all(('content' not in s for s in eff_sections)) and has_resp_bin and raw_text:
				try:
					live_html = extract_bytes(resp_bin.read_bytes(), data.get('content_type') or 'text/html', 'html', data.get('charset') or 'utf-8', status=status)
					if isinstance(live_html.get('sections'), list):
						eff_sections = live_html['sections']
				except Exception:
					pass
			matches = _grep_section_windows(eff_sections, plain_text or raw_text, rx, context_lines=context_lines, max_matches=max_matches)
		entry['match_count'] = len(matches)
		entry['matches'] = matches
	return entry
def evidence_query(root, *, urls=None, include_anchors: bool = False, grep_pattern: str | None = None, context_lines: int = 2, max_matches: int = 20) -> dict:
	from .path_registry import project_paths
	pp = project_paths(root, exact_root=True)
	kb_dir = pp.kb_dir.resolve()
	ev_dir = pp.evidence_dir.resolve()
	http_dirs = [d for d in (ev_dir / 'HTTP', pp.root / '_/\ua616/KB/Evidence/HTTP', pp.root / '\ua616/KB/Evidence/HTTP') if d.is_dir()]
	seen_dirs: set[Path] = set()
	obs_files: list[Path] = []
	for hd in http_dirs:
		hd_res = hd.resolve()
		if hd_res in seen_dirs:
			continue
		seen_dirs.add(hd_res)
		obs_files.extend(sorted(hd_res.rglob('observation.json')))
	rx = None
	if None is not grep_pattern and str(grep_pattern).strip():
		try:
			rx = re.compile(str(grep_pattern), re.IGNORECASE)
		except re.error as exc:
			raise ValueError(f'Invalid --grep regular expression: {exc}') from exc
	raw_entries: list[dict] = []
	for obs_f in obs_files:
		item = _summarize_observation_bundle(obs_f, kb_dir, include_anchors=include_anchors, rx=rx, context_lines=context_lines, max_matches=max_matches)
		if None is not item:
			raw_entries.append(item)
	best_by_url: dict[str, dict] = {}
	for item in raw_entries:
		key = _norm_query_url(item.get('url') or item.get('final_url') or item['observation']).lower()
		prev = best_by_url.get(key)
		if None is prev or (bool(item.get('valid_for_citation')), str(item.get('observed_at') or '')) > (bool(prev.get('valid_for_citation')), str(prev.get('observed_at') or '')):
			best_by_url[key] = item
	deduped = list(best_by_url.values())
	query_urls = [str(u).strip() for u in (urls or ()) if str(u).strip()]
	missing_urls: list[str] = []
	if query_urls:
		selected: list[dict] = []
		seen_obs: set[str] = set()
		for qu in query_urls:
			q_norm = _norm_query_url(qu).lower()
			exact = [it for it in deduped if q_norm in {_norm_query_url(it.get('url') or '').lower(), _norm_query_url(it.get('final_url') or '').lower()}]
			matched = exact or [it for it in deduped if q_norm in _norm_query_url(it.get('url') or '').lower() or q_norm in _norm_query_url(it.get('final_url') or '').lower()]
			if not matched:
				missing_urls.append(qu)
			else:
				for it in matched:
					if it['observation'] not in seen_obs:
						seen_obs.add(it['observation'])
						selected.append(it)
	else:
		selected = [it for it in deduped if None is rx or 0 < it.get('match_count', 0)]
	return {
		'valid': not missing_urls,
		'observation_count': len(selected),
		'missing_urls': missing_urls,
		'observations': selected,
	}
