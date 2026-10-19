"""Project-owned, immutable HTTP observations and batch extraction. GET only."""

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


def classify_network_error(exc):
    """Distinguish DNS failure (gaierror) from TCP timeout, connection refused, or TLS error."""
    cause = exc.reason if isinstance(exc, URLError) and getattr(exc, 'reason', None) is not None else exc
    if isinstance(cause, socket.gaierror):
        return 'dns_error', False
    if isinstance(cause, (TimeoutError, socket.timeout)):
        return 'tcp_timeout', None
    if isinstance(cause, ConnectionRefusedError):
        return 'connection_refused', True
    if isinstance(cause, ssl.SSLError):
        return 'tls_error', True
    if isinstance(exc, ValueError):
        return 'value_error', None
    return 'network_error', None


def json_data(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def inside(root, relative):
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f'Path escapes project: {relative}')
    return target


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
                return value.scheme, value.hostname, value.port or (443 if value.scheme == 'https' else 80)
            if origin(req.full_url) != origin(redirected.full_url):
                for key in list(redirected.headers):
                    if key.lower() in ('authorization', 'cookie', 'proxy-authorization'):
                        redirected.remove_header(key)
        return redirected


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
        return Response(response.url, response.status, response.headers.get_content_type(), data,
                        response.headers.get_content_charset() or 'utf-8', tuple(redirects.chain))


def request_context(value=None):
    """Explicit cache conditions, never a proof of private mode or IP geography.

    Do not persist cookies, authorization headers or profile secrets. A caller
    supplies a state fingerprint when the same browser tab changes its state.
    """
    if value is None:
        return {'session': {'mode': 'unknown', 'verification': 'unverified'},
                'egress': {'country': None, 'verification': 'unverified'}}
    if not isinstance(value, dict):
        raise ValueError('Request context must be an object')
    allowed = {'session', 'egress', 'url_country', 'language', 'selected_country',
               'currency', 'session_id', 'state_fingerprint'}
    if set(value) - allowed:
        raise ValueError('Context accepts explicit session/geography/state conditions, not credentials')
    result = json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    session = result.setdefault('session', {'mode': 'unknown', 'verification': 'unverified'})
    egress = result.setdefault('egress', {'country': None, 'verification': 'unverified'})
    if (not isinstance(session, dict) or set(session) - {'mode', 'verification', 'evidence'} or
            session.get('mode') not in ('normal', 'incognito', 'isolated', 'unknown')):
        raise ValueError('Session mode must distinguish normal, incognito, isolated and unknown')
    if (not isinstance(egress, dict) or set(egress) - {'country', 'verification', 'evidence'} or
            egress.get('country') is not None and not re.fullmatch(r'[A-Z]{2}', str(egress.get('country')))):
        raise ValueError('Egress country must be an explicit ISO country or null; URL country is separate')
    for condition in (session, egress):
        if condition.get('verification', 'unverified') not in ('verified', 'unverified'):
            raise ValueError('Context verification must be verified or unverified')
        if condition.get('verification') == 'verified' and not condition.get('evidence'):
            raise ValueError('Verified conditions require recorded evidence; empty cookies prove no browser mode')
    for key in allowed - {'session', 'egress'}:
        if key in result and (not isinstance(result[key], str) or not result[key].strip()):
            raise ValueError('Explicit context fields must be nonempty strings')
    return result


def request_key(url, headers, scope, context=None):
    url = urldefrag(url)[0]
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in url):
        raise ValueError('A valid HTTP(S) URL without embedded credentials is required')
    _ = parsed.port
    normalized = {k.lower(): str(v) for k, v in headers.items()}
    return url, _fingerprint({'url': url, 'method': 'GET', 'headers': normalized,
        'scope': scope, 'context': request_context(context)})


def observation_capabilities(meta):
    """Read-only measurements cannot establish a click, configuration or IP."""
    if meta.get('error'):
        return set()
    if meta.get('kind') == 'http' and meta.get('method') == 'GET' and 200 <= (meta.get('status') or 0) < 300:
        return {'content', 'markup', 'platform_capability'}
    if meta.get('kind') == 'dom' and meta.get('method') == 'READ_DOM':
        return {'content', 'markup', 'dom', 'platform_capability'}
    return set()


METRIC_KEYS = ('uses', 'cache_hits', 'fresh_attempts', 'failed_attempts', 'http_unavailable')


def metric_counts(events):
    return dict(zip(METRIC_KEYS, (len(events), sum(x.get('cached') is True for x in events),
        sum(x.get('cached') is False for x in events), sum(bool(x.get('error')) for x in events),
        sum(x.get('kind') == 'http' and (x.get('status') or 0) >= 400 for x in events))))


def bounded_metrics(value):
    """Migrate only observed totals; retain at most 32 diagnostic events."""
    if isinstance(value, list):
        return {'version': 2, 'totals': metric_counts(value), 'recent': value[-32:]}
    if not isinstance(value, dict) or value.get('version') != 2 or set(value.get('totals', {})) != set(METRIC_KEYS):
        raise ValueError('Unknown collector metrics format; preserve and inspect')
    return value


def observed_use(root, result):
    """Count actual collector uses, including cache hits; do not infer earlier activity."""
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
    return result


def collect(root, url, *, headers=None, scope='public', max_age=86400, refresh_reason=None, timeout=15, fetcher=None, observation_kind='http', context=None):
    root = Path(root).resolve()
    if max_age < 0 or timeout <= 0 or not isinstance(scope, str) or not scope.strip():
        raise ValueError('Nonnegative max_age, positive timeout and explicit request scope required')
    headers = {'User-Agent': 'UpworkResearch/2.0', **(headers or {})}
    if observation_kind not in ('http', 'dom') or (observation_kind == 'dom' and fetcher is None):
        raise ValueError('DOM observation needs an explicit read-only browser capture')
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items()):
        raise ValueError('Request headers must contain string keys and values')
    context = request_context(context)
    url, key = request_key(url, headers, scope + ':' + observation_kind, context)
    data_dir = root / 'ꘖ/data'
    index_file = data_dir / 'http-index.json'
    with locked(data_dir / ('http-' + key[:24] + '.lock'), timeout=max(30, timeout + 15)):
        index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {}
        entry = index.get(key)
        if entry and not refresh_reason and max_age > 0:
            meta = load_observation(root, entry['observation'])
            ttl = min(max_age, 300) if meta.get('error') or (meta.get('status') is not None and meta.get('status', 0) >= 400) else max_age
            if time.time() - datetime.fromisoformat(meta['observed_at']).timestamp() <= ttl:
                return observed_use(root, {'cached': True, 'observation': entry['observation'], **meta})
        if refresh_reason is not None and not refresh_reason.strip():
            raise ValueError('Refresh needs a reason for the new measurement')
        when = datetime.now(timezone.utc).isoformat(timespec='microseconds')
        error, error_kind, dns_resolved = None, None, None
        try:
            response = (fetcher or fetch)(url, headers, timeout)
            if len(response.body) > MAX_BYTES:
                raise ValueError('Response exceeds 16 MiB')
            dns_resolved = True if observation_kind == 'http' and (response.status or 0) > 0 else None
        except (OSError, ValueError) as exc:
            response = Response(url, 0, 'application/octet-stream', b'')
            # Do not persist exception strings that may echo request credentials.
            error = type(exc).__name__
            error_kind, dns_resolved = classify_network_error(exc)
        folder = root / 'ꘖ/KB/Evidence/HTTP' / key[:24] / uuid.uuid4().hex
        folder.mkdir(parents=True, exist_ok=False)
        create_bytes(folder / 'response.bin', response.body)
        meta = {'schema_version': 1, 'kind': observation_kind, 'request_key': key, 'url': url, 'final_url': response.url,
                'method': 'GET' if observation_kind == 'http' else 'READ_DOM', 'request_scope': scope,
                'observed_at': when, 'status': response.status if observation_kind == 'http' else None,
                'http_status_verified': observation_kind == 'http' and response.status > 0,
                'content_type': response.content_type, 'charset': response.charset, 'redirects': list(response.redirects),
                'body_sha256': hashlib.sha256(response.body).hexdigest(), 'body_bytes': len(response.body),
                'refresh_reason': refresh_reason, 'error': error, 'error_kind': error_kind, 'dns_resolved': dns_resolved,
                'conditions': {'header_names': sorted(k.lower() for k in headers), 'values_fingerprint': key,
                               'reported_context': context, 'context_fingerprint': _fingerprint(context)},
                'collector': 'read-only-http' if observation_kind == 'http' else 'read-only-dom',
                'interaction_checked': False}
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
    if meta.get('schema_version') != 1 or not isinstance(meta.get('body_sha256'), str):
        raise ValueError('Invalid observation metadata')
    body = (file.parent / 'response.bin').read_bytes()
    if len(body) != meta.get('body_bytes') or hashlib.sha256(body).hexdigest() != meta['body_sha256']:
        raise ValueError('Observation body differs from its saved hash/size')
    return meta


class HTMLData(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.text, self.headings, self.anchors, self.scripts, self.json_ld = [], [], [], [], [], []
        self.title, self.meta, self.meta_all, self.canonical, self.heading, self.script = '', {}, {}, [], None, None
        self.links, self.link = [], None
        self.images, self.embeds = [], []
        self.anchor_ranges, self.section_ranges = {}, []
        self.position = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        anchor = attrs.get('id') or (attrs.get('name') if tag == 'a' else None)
        if anchor:
            self.anchors.append(anchor)
            self.anchor_ranges.setdefault(anchor, []).append({'start': self.position, 'end': None})
        if tag == 'a' and attrs.get('href'):
            self.link = {'href': attrs['href'], 'text': ''}
        if tag == 'img':
            self.images.append({
                'src': attrs.get('src') or attrs.get('data-src') or '',
                'alt': attrs.get('alt', ''),
                'has_alt_attr': 'alt' in attrs,
                'width': attrs.get('width'),
                'height': attrs.get('height'),
            })
        if tag in ('iframe', 'video') and (attrs.get('src') or attrs.get('data-src')):
            self.embeds.append({'tag': tag, 'src': attrs.get('src') or attrs.get('data-src')})
        if tag == 'meta':
            name = attrs.get('name') or attrs.get('property')
            if name:
                self.meta[name] = attrs.get('content', '')
                self.meta_all.setdefault(name, []).append(attrs.get('content', ''))
        if tag == 'link' and 'canonical' in attrs.get('rel', '').split():
            self.canonical.append(attrs.get('href'))
        if tag == 'script':
            self.script = {'src': attrs.get('src'), 'type': attrs.get('type'), 'text': ''}
            if attrs.get('src'):
                self.scripts.append(attrs['src'])
        if re.fullmatch('h[1-6]', tag):
            position = self.position
            for section in self.section_ranges:
                if section['end'] is None and section['level'] >= int(tag[1]):
                    section['end'] = position
            self.heading = {'level': int(tag[1]), 'text': '', 'anchor': attrs.get('id'),
                            'ancestor_anchors': [x[1] for x in self.stack if x[1]], 'start': position, 'end': None}
            self.section_ranges.append(self.heading)
        if tag not in ('meta', 'link', 'img', 'input', 'br', 'hr', 'source', 'area', 'base', 'embed', 'param', 'wbr'):
            self.stack.append((tag, anchor))

    def handle_endtag(self, tag):
        if tag == 'a' and self.link is not None:
            self.link['text'] = ' '.join(self.link['text'].split())
            self.links.append(self.link)
            self.link = None
        if self.heading and re.fullmatch('h[1-6]', tag):
            self.heading['text'] = ' '.join(self.heading['text'].split())
            self.headings.append(self.heading); self.heading = None
        if tag == 'script' and self.script:
            if self.script['type'] == 'application/ld+json':
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
                            if span['end'] is None:
                                span['end'] = self.position
                del self.stack[i:]; break
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
        if self.link is not None and not tags.intersection(('script', 'style')):
            self.link['text'] += value
        if not tags.intersection(('script', 'style', 'head')):
            self.text.append(value)
            self.position += len(value)

    def result(self):
        plain = ''.join(self.text)
        clean_text = '\n'.join(x.strip() for x in plain.splitlines() if x.strip())
        title_str = ' '.join(self.title.split())
        sections = [{**h, 'content': plain[h['start']:h['end']]} for h in self.section_ranges]
        word_count = len(re.findall(r'\w+', clean_text))
        site_name = (self.meta.get('og:site_name') or '').strip()
        total_imgs = len(self.images)
        empty_alt = sum(1 for img in self.images if not (img.get('alt') or '').strip())
        filename_alt = sum(
            1 for img in self.images
            if (img.get('alt') or '').strip()
            and re.search(r'(?i)\.(?:jpe?g|png|gif|webp|avif|svg|bmp|tiff?)\b', (img.get('alt') or '').strip())
        )
        repeated_site_alt = sum(
            1 for img in self.images
            if site_name and (img.get('alt') or '').strip().lower() == site_name.lower()
        )
        descriptive_alt = max(0, total_imgs - empty_alt - filename_alt - repeated_site_alt)
        h1_count = sum(1 for h in self.headings if h.get('level') == 1)
        meta_desc = self.meta.get('description', '')
        spaced_brand = bool(re.search(
            r'\b(?:[A-Za-z]\s+){3,}[A-Za-z]\b',
            (self.meta.get('og:site_name') or '') + ' ' + json.dumps(self.json_ld, ensure_ascii=False),
        ))
        json_ld_types = [item.get('@type') for item in self.json_ld if isinstance(item, dict) and item.get('@type')]
        empty_json_ld_desc = any(
            isinstance(item, dict) and 'description' in item and not str(item.get('description') or '').strip()
            for item in self.json_ld
        )
        insecure_json_ld_img = any(
            isinstance(item, dict) and isinstance(item.get('image'), str)
            and (item['image'].startswith('http://') or item['image'].startswith('//') or item['image'].startswith('/'))
            for item in self.json_ld
        )
        return {'title': title_str, 'meta': self.meta, 'meta_all': self.meta_all, 'canonical': self.canonical,
                'headings': self.headings, 'anchors': sorted(set(self.anchors)), 'links': self.links, 'scripts': self.scripts,
                'images': self.images,
                'image_alt_summary': {
                    'total': total_imgs,
                    'empty_alt': empty_alt,
                    'filename_like_alt': filename_alt,
                    'repeated_site_name_alt': repeated_site_alt,
                    'descriptive_alt': descriptive_alt,
                },
                'embeds': self.embeds,
                'word_count': word_count,
                'seo_diagnostics': {
                    'h1_count': h1_count,
                    'missing_h1': h1_count == 0,
                    'multiple_h1': h1_count > 1,
                    'title_length': len(title_str),
                    'overlong_title': len(title_str) > 65,
                    'meta_description_length': len(meta_desc),
                    'missing_meta_description': not bool(meta_desc.strip()),
                    'spaced_brand_name': spaced_brand,
                    'json_ld_types': json_ld_types,
                    'empty_json_ld_description': empty_json_ld_desc,
                    'insecure_or_relative_json_ld_image': insecure_json_ld_img,
                },
                'json_ld': self.json_ld, 'sections': sections,
                'anchor_content': {anchor: [plain[x['start']:x['end']] for x in ranges] for anchor, ranges in self.anchor_ranges.items()},
                'ambiguous_anchors': sorted(anchor for anchor, ranges in self.anchor_ranges.items() if len(ranges) > 1),
                'text': clean_text}


def _extract_sitemap(text):
    """Parse XML <urlset>/<sitemapindex> and compute deterministic sitemap diagnostics."""
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
            elif fname == 'image':
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
    template_slugs = [
        u['loc'] for u in urls
        if re.search(r'(?i)(?:blog-post-title|new-page|sample-page|copy-of|lorem-ispum|lorem-ipsum|/home$)', u['loc'])
    ]
    paths = [urlsplit(u['loc']).path for u in urls]
    root_missing = any(p.rstrip('/') == '/home' for p in paths) and not any(p in ('', '/') for p in paths)
    duplicate_images = {k: v for k, v in sorted(img_to_pages.items()) if len(v) > 1}
    return {
        'type': root_name,
        'url_count': len(urls),
        'urls': urls,
        'sitemap_issues': {
            'unescaped_spaces_in_loc': unescaped_spaces,
            'template_slug_urls': template_slugs,
            'root_url_missing': root_missing,
            'polluted_image_titles': sorted(polluted_titles),
            'duplicate_image_locs': duplicate_images,
        },
    }


def _summarize_json_collections(value):
    """Compute deterministic counts, timestamp ranges and categorical distributions over JSON object arrays."""
    arrays = {}
    def walk(node, path='', depth=0):
        if depth > 4:
            return
        if isinstance(node, list) and node and all(isinstance(x, dict) for x in node):
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
    iso_re = re.compile(r'^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2})?')
    for name, items in arrays.items():
        ts_fields, cat_fields = {}, {}
        for item in items:
            label = next((str(item[k]) for k in ('title', 'name', 'handle', 'slug', 'id') if item.get(k) is not None), None)
            for k, v in item.items():
                if isinstance(v, str) and iso_re.match(v):
                    ts_fields.setdefault(k, []).append((v, item.get('id'), label))
                elif k != 'id' and isinstance(v, (str, bool)) and len(str(v)) <= 120:
                    cat_fields.setdefault(k, {})[str(v)] = cat_fields.get(k, {}).get(str(v), 0) + 1
                elif isinstance(v, list) and v and all(isinstance(elem, str) and len(elem) <= 80 for elem in v):
                    for elem in v:
                        cat_fields.setdefault(k, {})[elem] = cat_fields.get(k, {}).get(elem, 0) + 1
        ts_summary = {}
        for k, entries in ts_fields.items():
            ordered = sorted(entries, key=lambda x: x[0])
            by_date = {}
            for val, _, _ in ordered:
                day = val[:10]
                by_date[day] = by_date.get(day, 0) + 1
            earliest, latest = ordered[0], ordered[-1]
            ts_summary[k] = {
                'min': earliest[0],
                'max': latest[0],
                'count': len(ordered),
                'by_date': dict(sorted(by_date.items())),
                'earliest_record': {'id': earliest[1], 'label': earliest[2], k: earliest[0]},
                'latest_record': {'id': latest[1], 'label': latest[2], k: latest[0]},
            }
        filtered_cats = {
            k: dict(sorted(counts.items()))
            for k, counts in sorted(cat_fields.items())
            if len(counts) <= 50 and (len(items) == 1 or len(counts) < len(items) or any(c > 1 for c in counts.values()))
        }
        summary[name] = {
            'record_count': len(items),
            'timestamp_ranges': ts_summary,
            'field_counts': filtered_cats,
        }
    return summary


def extract_bytes(body, content_type, profile, charset='utf-8'):
    if profile not in PROFILES:
        raise ValueError(f'Unknown profile: {profile}; choose {PROFILES}')
    if profile == 'document' and body.startswith(b'%PDF-'):
        from .upwork_data import extract_pdf_markdown
        md = extract_pdf_markdown(body)
        paragraphs = [line for line in md.splitlines() if line.strip()]
        return {'paragraphs': paragraphs, 'text': md, 'markdown': md, 'layout_checked': True}
    if profile == 'document' and body.startswith(b'PK'):
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
        return {'paragraphs': paragraphs, 'text': '\n'.join(paragraphs), 'markdown': md, 'layout_checked': False, 'non_text_parts': non_text}
    text = body.decode(charset, errors='replace')
    if profile == 'shopify':
        value = json.loads(text)
        if not isinstance(value, dict) or not any(k in value for k in ('product', 'products', 'variants', 'id')):
            raise ValueError('Expected Shopify product/collection JSON')
        return {'data': value, 'summary': _summarize_json_collections(value), 'text': text,
                'scope': 'public JSON response; not Merchant Center feed or admin configuration'}
    if profile == 'document' and content_type not in ('text/html', 'application/xhtml+xml'):
        out = {'paragraphs': text.splitlines(), 'text': text, 'layout_checked': False}
        if content_type == 'application/json' or text.lstrip().startswith(('{', '[')):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, (dict, list)):
                    out['summary'] = _summarize_json_collections(parsed)
            except ValueError:
                pass
        return out
    parser = HTMLData(); parser.feed(text)
    result = parser.result()
    result['tracking_summary'] = {
        'identifiers': sorted(set(re.findall(r'\b(?:GTM-[A-Z0-9]+|G-[A-Z0-9]+|UA-\d+-\d+|AW-\d+)\b', text))),
        'gsc_verification': bool(result['meta'].get('google-site-verification')),
        'cms_technical_domains': sorted(set(re.findall(r'\b[a-z0-9-]+\.(?:squarespace\.com|myshopify\.com|webflow\.io|wixsite\.com|wpengine\.com)\b', text, flags=re.I))),
    }
    sitemap = _extract_sitemap(text)
    if sitemap is not None:
        result['sitemap'] = sitemap
    if profile == 'tracking':
        result['identifiers'] = sorted(set(re.findall(r'\b(?:GTM-[A-Z0-9]+|G-[A-Z0-9]+|AW-\d+)\b', text)))
        configs, parse_failures = {}, []
        for key in ('webPixelsConfigList', 'wpmLoader', 'resource'):
            for match in re.finditer(r'[\"\']?\b' + key + r'\b[\"\']?\s*[:=]\s*', text):
                try:
                    value, _ = json.JSONDecoder().raw_decode(text[match.end():])
                    if isinstance(value, str):
                        try: value = json.loads(value)
                        except ValueError: pass
                    configs.setdefault(key, []).append(value)
                except ValueError:
                    parse_failures.append({'key': key, 'offset': match.end(), 'reason': 'Not literal JSON; inspect saved source without evaluating JavaScript'})
        result['embedded_json'] = configs
        result['embedded_json_unparsed'] = parse_failures
        result['execution_checked'] = False
    result['browser_check_required'] = bool(re.search(r'(?i)verify you are human|checking your browser|__LS_SEQ_LOADER__|enable javascript and cookies', result['text'] + text[:8000]))
    return result


def extract_observation(root, reference, profile='html'):
    meta = load_observation(root, reference)
    folder = inside(Path(root) / 'ꘖ/KB', urldefrag(reference)[0]).parent
    if meta.get('error') or (meta.get('kind', 'http') == 'http' and not 200 <= meta['status'] < 300):
        raise ValueError('Observation is unavailable; preserve it and choose a different check method')
    version = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
    target = folder / f'extracted-{profile}-{version}.json'
    if not target.exists():
        data = extract_bytes((folder / 'response.bin').read_bytes(), meta['content_type'], profile, meta.get('charset') or 'utf-8')
        create_bytes(target, json_data({'profile': profile, 'extractor_version': version,
            'observation': reference, 'body_sha256': meta['body_sha256'], 'observed_at': meta['observed_at'], **data}))
    return {'extraction': target.relative_to(Path(root).resolve() / 'ꘖ/KB').as_posix(),
            'observation': reference, 'profile': profile, 'observed_at': meta['observed_at']}


def extract_file(root, file, profile='document'):
    file = inside(root, file)
    body = file.read_bytes()
    if len(body) > MAX_BYTES:
        raise ValueError('Source file exceeds 16 MiB')
    import mimetypes
    kind = mimetypes.guess_type(file.name)[0] or 'text/plain'
    data = extract_bytes(body, kind, profile)
    version = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
    target = Path(root) / 'ꘖ/KB/Evidence/Extracted' / hashlib.sha256(body).hexdigest() / f'{profile}-{version}.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        create_bytes(target, json_data({'profile': profile, 'source': file.relative_to(Path(root).resolve()).as_posix(),
            'source_sha256': hashlib.sha256(body).hexdigest(), 'extractor_version': version, **data}))
    return {'extraction': target.relative_to(Path(root).resolve() / 'ꘖ/KB').as_posix(), 'source_sha256': hashlib.sha256(body).hexdigest()}


def select_dom_tab(tabs, url, tab_id):
    matches = [t for t in tabs if t.get('type') == 'page' and t.get('id') == tab_id and urldefrag(t.get('url', ''))[0] == urldefrag(url)[0]]
    if len(matches) != 1:
        raise ValueError('Explicit tab ID must match the exact requested URL; no navigation or account fallback')
    return matches[0]


def capture_dom(root, url, tab_id, *, port=9222, refresh_reason=None, reader=None, context=None):
    if not tab_id or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('Explicit local CDP port and exact tab ID required')
    def read_dom(target, headers, timeout):
        if reader:
            data = reader(target, tab_id, port)
        else:
            import asyncio
            import websockets
            from urllib.request import urlopen
            from .upwork_extract import RPC
            async def read():
                with urlopen(f'http://127.0.0.1:{port}/json', timeout=5) as response:
                    tabs = json.loads(response.read(MAX_BYTES))
                tab = select_dom_tab(tabs, target, tab_id)
                ws_url = tab.get('webSocketDebuggerUrl', '')
                parsed = urlsplit(ws_url)
                if parsed.scheme not in ('ws', 'wss') or parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.port != port:
                    raise ValueError('Browser debugger must be the explicitly selected local endpoint')
                async with websockets.connect(ws_url, max_size=MAX_BYTES, open_timeout=10) as socket:
                    rpc = RPC(socket, timeout=timeout)
                    return await rpc.evaluate('({url:location.href,html:document.documentElement.outerHTML})')
            data = asyncio.run(read())
        if not isinstance(data, dict) or not isinstance(data.get('html'), str) or urldefrag(data.get('url', ''))[0] != urldefrag(target)[0]:
            raise ValueError('Tab navigated or DOM capture does not match the intended resource')
        return Response(data['url'], 0, 'text/html', data['html'].encode('utf-8'))
    # The tab may keep its URL while currency, cookies or selected country change.
    # A new DOM scenario is therefore fresh even when a caller omits context.
    observation = collect(root, url, scope=f'CDP:{port}:tab:{tab_id}', max_age=0,
        refresh_reason=refresh_reason, fetcher=read_dom, observation_kind='dom', context=context)
    if observation['error']:
        return observation
    return {**observation, **extract_observation(root, observation['observation'])}


def compute_site_summary(root, results):
    """Aggregate cross-page SEO, heading, word count and tracking diagnostics across HTML extractions."""
    root = Path(root).resolve()
    kb_dir = root / 'ꘖ/KB'
    titles, descriptions = {}, {}
    missing_h1, multiple_h1, overlong_titles, thin_urls = [], [], [], []
    all_identifiers, cms_domains = set(), set()
    html_pages = 0
    for item in results or []:
        if not isinstance(item, dict) or item.get('error') or not (200 <= (item.get('status') or 0) < 300):
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
        if ext.get('sitemap') is not None or 'headings' not in ext:
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
        h1s = [h for h in (ext.get('headings') or []) if isinstance(h, dict) and h.get('level') == 1]
        if len(h1s) == 0:
            missing_h1.append(url)
        elif len(h1s) > 1:
            multiple_h1.append(url)
        wc = ext.get('word_count')
        if isinstance(wc, int) and wc < 100:
            thin_urls.append({'url': url, 'word_count': wc})
        ts = ext.get('tracking_summary') or {}
        all_identifiers.update(ts.get('identifiers') or [])
        cms_domains.update(ts.get('cms_technical_domains') or [])
    return {
        'inspected_html_pages': html_pages,
        'missing_h1_urls': missing_h1,
        'multiple_h1_urls': multiple_h1,
        'overlong_title_urls': overlong_titles,
        'duplicate_titles': {k: v for k, v in titles.items() if len(v) > 1},
        'duplicate_meta_descriptions': {k: v for k, v in descriptions.items() if len(v) > 1},
        'thin_content_urls': thin_urls,
        'all_tracking_identifiers': sorted(all_identifiers),
        'cms_technical_domains': sorted(cms_domains),
    }


def collect_plan(root, plan, *, fetcher=None):
    if not isinstance(plan, dict) or not isinstance(plan.get('requests'), list) or not plan['requests']:
        raise ValueError('Plan needs a nonempty requests list')
    results = []
    for entry in plan['requests']:
        try:
            if not isinstance(entry, dict):
                raise ValueError('Each request must be an object')
            profile = entry.get('profile', 'html')
            if profile not in PROFILES:
                raise ValueError('Unknown extraction profile')
            observation = collect(root, entry['url'], headers=entry.get('headers'), scope=entry.get('scope', 'public'),
                max_age=entry.get('max_age', 86400), refresh_reason=entry.get('refresh_reason'), fetcher=fetcher,
                context=entry.get('context'))
            item = {k: observation.get(k) for k in ('url', 'cached', 'observation', 'status', 'observed_at', 'error', 'error_kind', 'dns_resolved')}
            if not observation['error'] and 200 <= observation['status'] < 300:
                try:
                    item.update(extract_observation(root, observation['observation'], profile))
                except (OSError, ValueError, KeyError, TypeError, LookupError) as exc:
                    item['extraction_error'] = type(exc).__name__
                    item['detail'] = 'Response saved; inspect the source or choose another extraction profile, without fetching it again'
            results.append(item)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            results.append({'error': type(exc).__name__, 'detail': 'Invalid or unavailable input; check this plan entry', 'request_index': len(results)})
    return {'results': results, 'site_summary': compute_site_summary(root, results),
            'complete': all(not x.get('error') and x.get('status', 0) > 0 for x in results),
            'content_available_for_all': all(not x.get('error') and not x.get('extraction_error') and 200 <= x.get('status', 0) < 300 for x in results),
            'detail': 'A saved HTTP 403/404 is a completed observation, not a reason to repeat the same request blindly'}
