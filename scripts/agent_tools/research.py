"""Project-owned, immutable HTTP observations and batch extraction. GET only."""

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
import hashlib
import json
import re
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile

from .storage import create_bytes, locked, replace_bytes

MAX_BYTES = 16 * 1024 * 1024
PROFILES = ('html', 'shopify', 'tracking', 'document')


def json_data(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


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


def request_key(url, headers, scope):
    url = urldefrag(url)[0]
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in url):
        raise ValueError('A valid HTTP(S) URL without embedded credentials is required')
    _ = parsed.port
    normalized = {k.lower(): str(v) for k, v in headers.items()}
    return url, hashlib.sha256(json_data({'url': url, 'method': 'GET', 'headers': normalized, 'scope': scope})).hexdigest()


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


def collect(root, url, *, headers=None, scope='public', max_age=86400, refresh_reason=None, timeout=15, fetcher=None, observation_kind='http'):
    root = Path(root).resolve()
    if max_age < 0 or timeout <= 0 or not isinstance(scope, str) or not scope.strip():
        raise ValueError('Nonnegative max_age, positive timeout and explicit request scope required')
    headers = {'User-Agent': 'UpworkResearch/2.0', **(headers or {})}
    if observation_kind not in ('http', 'dom') or (observation_kind == 'dom' and fetcher is None):
        raise ValueError('DOM observation needs an explicit read-only browser capture')
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items()):
        raise ValueError('Request headers must contain string keys and values')
    url, key = request_key(url, headers, scope + ':' + observation_kind)
    data_dir = root / 'ꘖ/data'
    index_file = data_dir / 'http-index.json'
    with locked(data_dir / ('http-' + key[:24] + '.lock'), timeout=max(30, timeout + 15)):
        index = json.loads(index_file.read_text(encoding='utf-8')) if index_file.exists() else {}
        entry = index.get(key)
        if entry and not refresh_reason:
            meta = load_observation(root, entry['observation'])
            ttl = min(max_age, 300) if meta.get('error') or (meta.get('status') is not None and meta.get('status', 0) >= 400) else max_age
            if time.time() - datetime.fromisoformat(meta['observed_at']).timestamp() <= ttl:
                return observed_use(root, {'cached': True, 'observation': entry['observation'], **meta})
        if refresh_reason is not None and not refresh_reason.strip():
            raise ValueError('Refresh needs a reason for the new measurement')
        when = datetime.now(timezone.utc).isoformat(timespec='microseconds')
        error = None
        try:
            response = (fetcher or fetch)(url, headers, timeout)
            if len(response.body) > MAX_BYTES:
                raise ValueError('Response exceeds 16 MiB')
        except (OSError, ValueError) as exc:
            response = Response(url, 0, 'application/octet-stream', b'')
            # Do not persist exception strings that may echo request credentials.
            error = type(exc).__name__
        folder = root / 'ꘖ/KB/Evidence/HTTP' / key[:24] / uuid.uuid4().hex
        folder.mkdir(parents=True, exist_ok=False)
        create_bytes(folder / 'response.bin', response.body)
        meta = {'schema_version': 1, 'kind': observation_kind, 'request_key': key, 'url': url, 'final_url': response.url,
                'method': 'GET' if observation_kind == 'http' else 'READ_DOM', 'request_scope': scope,
                'observed_at': when, 'status': response.status if observation_kind == 'http' else None,
                'http_status_verified': observation_kind == 'http' and response.status > 0,
                'content_type': response.content_type, 'charset': response.charset, 'redirects': list(response.redirects),
                'body_sha256': hashlib.sha256(response.body).hexdigest(), 'body_bytes': len(response.body),
                'refresh_reason': refresh_reason, 'error': error,
                'conditions': {'header_names': sorted(k.lower() for k in headers), 'values_fingerprint': key}}
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
        self.anchor_ranges, self.section_ranges = {}, []
        self.position = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        anchor = attrs.get('id') or (attrs.get('name') if tag == 'a' else None)
        if anchor:
            self.anchors.append(anchor)
            self.anchor_ranges.setdefault(anchor, []).append({'start': self.position, 'end': None})
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
        if not tags.intersection(('script', 'style', 'head')):
            self.text.append(value)
            self.position += len(value)

    def result(self):
        plain = ''.join(self.text)
        sections = [{**h, 'content': plain[h['start']:h['end']]} for h in self.section_ranges]
        return {'title': ' '.join(self.title.split()), 'meta': self.meta, 'meta_all': self.meta_all, 'canonical': self.canonical,
                'headings': self.headings, 'anchors': sorted(set(self.anchors)), 'scripts': self.scripts,
                'json_ld': self.json_ld, 'sections': sections,
                'anchor_content': {anchor: [plain[x['start']:x['end']] for x in ranges] for anchor, ranges in self.anchor_ranges.items()},
                'ambiguous_anchors': sorted(anchor for anchor, ranges in self.anchor_ranges.items() if len(ranges) > 1),
                'text': '\n'.join(x.strip() for x in plain.splitlines() if x.strip())}


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
        return {'data': value, 'text': text, 'scope': 'public JSON response; not Merchant Center feed or admin configuration'}
    if profile == 'document' and content_type not in ('text/html', 'application/xhtml+xml'):
        return {'paragraphs': text.splitlines(), 'text': text, 'layout_checked': False}
    parser = HTMLData(); parser.feed(text)
    result = parser.result()
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


def capture_dom(root, url, tab_id, *, port=9222, refresh_reason=None, reader=None):
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
    observation = collect(root, url, scope=f'CDP:{port}:tab:{tab_id}', max_age=300,
        refresh_reason=refresh_reason, fetcher=read_dom, observation_kind='dom')
    if observation['error']:
        return observation
    return {**observation, **extract_observation(root, observation['observation'])}


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
                max_age=entry.get('max_age', 86400), refresh_reason=entry.get('refresh_reason'), fetcher=fetcher)
            item = {k: observation[k] for k in ('url', 'cached', 'observation', 'status', 'observed_at', 'error')}
            if not observation['error'] and 200 <= observation['status'] < 300:
                try:
                    item.update(extract_observation(root, observation['observation'], profile))
                except (OSError, ValueError, KeyError, TypeError, LookupError) as exc:
                    item['extraction_error'] = type(exc).__name__
                    item['detail'] = 'Response saved; inspect the source or choose another extraction profile, without fetching it again'
            results.append(item)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            results.append({'error': type(exc).__name__, 'detail': 'Invalid or unavailable input; check this plan entry', 'request_index': len(results)})
    return {'results': results, 'complete': all(not x.get('error') and x.get('status', 0) > 0 for x in results),
            'content_available_for_all': all(not x.get('error') and not x.get('extraction_error') and 200 <= x.get('status', 0) < 300 for x in results),
            'detail': 'A saved HTTP 403/404 is a completed observation, not a reason to repeat the same request blindly'}
