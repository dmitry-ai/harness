"""Markdown-aware structural checks, plus opt-in HTTP/source-HTML checks."""

from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
import json
from urllib.parse import unquote, urldefrag, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def _readable_escapes(value: str) -> str:
    """Decode display characters once; preserve escaped delimiters and literal %."""
    def decode(match):
        encoded = match.group()
        raw = bytes.fromhex(encoded.replace('%', ''))
        result, offset = [], 0
        for char in raw.decode('utf-8', errors='surrogateescape'):
            size = len(char.encode('utf-8', errors='surrogateescape')) * 3
            original = encoded[offset:offset + size]
            offset += size
            safe_ascii = char.isascii() and (char.isalnum() or char in ' -._~')
            safe_unicode = 0xA0 <= ord(char) < 0xD800 or 0xE000 <= ord(char) <= 0x10FFFF
            result.append(char if safe_ascii or safe_unicode else original)
        return ''.join(result)
    return re.sub(r'(?:%[0-9a-fA-F]{2})+', decode, value)


def readable_reference(value: str | Path) -> str:
    """Human-readable document reference, without changing opaque query parameters."""
    value = value.as_posix() if isinstance(value, Path) else value
    base, fragment_sep, fragment = value.partition('#')
    path, query_sep, query = base.partition('?')
    if path.lower().startswith('file:'):
        parsed = urlsplit(path)
        path = parsed.path
        if parsed.netloc and parsed.netloc != 'localhost':
            path = '//' + parsed.netloc + path
        elif re.match(r'^/[A-Za-z]:/', path):
            path = path[1:]
    return (_readable_escapes(path) + query_sep + query
            + fragment_sep + _readable_escapes(fragment))


def markdown_link(label: str | None, target: str | Path) -> str:
    """Write readable Markdown source; the viewer handles URI serialization."""
    target = readable_reference(target)
    if any(char in target for char in '\r\n<>'):
        raise ValueError('A document link cannot contain line endings or literal angle brackets')
    text = target if label is None else label
    text = text.replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')
    destination = f'<{target}>' if any(char.isspace() or char in '()' for char in target) else target
    return f'[{text}]({destination})'


def readable_link_issues(content: str) -> list[str]:
    """Inspect original authored references, not a renderer's encoded href output."""
    from markdown_it import MarkdownIt
    parser = MarkdownIt('commonmark', {'html': True})
    parser.normalizeLink = lambda value: value
    parser.validateLink = lambda value: True  # Parsing data only, including legacy file: links.
    targets, quote_depth = [], 0
    html = HTMLReferences(authored_only=True)
    for block in parser.parse(content):
        if block.type == 'blockquote_open':
            quote_depth += 1
        elif block.type == 'blockquote_close':
            quote_depth -= 1
        if quote_depth:
            continue  # Exact quotations and fenced source copies retain their original bytes.
        if block.type == 'html_block':
            html.feed(block.content)
        for token in block.children or []:
            if token.type == 'link_open':
                targets.append(token.attrGet('href'))
            elif token.type == 'image':
                targets.append(token.attrGet('src'))
            elif token.type == 'html_inline':
                html.feed(token.content)
            elif token.type == 'text':
                targets.extend(_document_urls(token.content))
    errors = []
    for target in dict.fromkeys(targets + html.links):
        readable = readable_reference(target)
        if target != readable:
            errors.append(f'LINK-5: Use a readable document link: {readable} (instead of {target})')
    return errors


class HTMLReferences(HTMLParser):
    def __init__(self, *, authored_only=False):
        super().__init__(convert_charrefs=True)
        self.anchors = []
        self.links = []
        self.authored_only = authored_only
        self.literal_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.authored_only and tag in ('pre', 'code', 'blockquote'):
            self.literal_depth += 1
        if self.authored_only and self.literal_depth:
            return
        values = dict(attrs)
        if values.get('id'):
            self.anchors.append(values['id'])
        if tag == 'a':
            if values.get('name') and values['name'] != values.get('id'):
                self.anchors.append(values['name'])
            if values.get('href'):
                self.links.append(values['href'])
        elif tag == 'img' and values.get('src'):
            self.links.append(values['src'])

    def handle_endtag(self, tag):
        if self.authored_only and tag in ('pre', 'code', 'blockquote'):
            self.literal_depth = max(0, self.literal_depth - 1)

    def handle_data(self, data):
        if self.authored_only and not self.literal_depth:
            self.links.extend(_document_urls(data))


def _bare_urls(text: str):
    # Only plain-text tokens reach this lexer; Markdown is parsed by markdown-it.
    for match in re.finditer(r'https?://[^\s<>`"\x00-\x1f]+', text):
        url = match.group().rstrip('.,;!?')
        for left, right in [('(', ')'), ('[', ']')]:
            while url.endswith(right) and url.count(right) > url.count(left):
                url = url[:-1]
        yield url


def _document_urls(text: str):
    yield from _bare_urls(text)
    for match in re.finditer(r'(?:file://|[A-Za-z]:[/\\])[^\s<>`"\x00-\x1f]+', text):
        yield match.group().rstrip('.,;!?)')


def references(content: str, include_code: bool = False) -> tuple[list[str], list[str]]:
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        requirements = Path(__file__).resolve().parents[1] / 'requirements-agent-tools.txt'
        raise RuntimeError(f'Install {requirements} with this Python interpreter') from exc
    parser = MarkdownIt('commonmark', {'html': True})
    validate_uri = parser.validateLink
    parser.validateLink = lambda value: value.lower().startswith('file:') or validate_uri(value)
    links = []
    html = HTMLReferences()
    for block in parser.parse(content):
        if block.type == 'html_block':
            html.feed(block.content)
        depth = 0
        for token in block.children or []:
            if token.type == 'link_open':
                depth += 1
                links.append(token.attrGet('href'))
            elif token.type == 'link_close':
                depth -= 1
            elif token.type == 'html_inline':
                html.feed(token.content)
            elif token.type == 'text' and depth == 0:
                links.extend(_bare_urls(token.content))
            elif token.type == 'code_inline' and include_code:
                links.extend(_bare_urls(token.content))
    return links + html.links, html.anchors


def validate_content(content: str, *, local_anchors: bool = False,
                     unique_urls: bool = False, include_code: bool = False,
                     readable_links: bool = False) -> list[str]:
    links, anchors = references(content, include_code)
    errors = []
    for anchor, count in Counter(anchors).items():
        if count > 1:
            errors.append(f'Duplicate explicit HTML anchor: {anchor}')
    available_anchors = set(anchors) | heading_anchors(content)
    for url in links:
        try:
            parsed = urlsplit(url)
            if parsed.scheme.lower() in ('http', 'https'):
                if not parsed.hostname or any(c.isspace() for c in url):
                    errors.append(f'Invalid HTTP URL: {url}')
                _ = parsed.port  # Validate invalid ports and bracketed hosts.
            elif local_anchors and url.startswith('#') and unquote(url[1:]) not in available_anchors:
                errors.append(f'Missing local anchor: {url}')
        except ValueError as exc:
            errors.append(f'Invalid URL {url}: {exc}')
    if unique_urls:
        for url, count in Counter(links).items():
            if count > 1 and url.startswith(('http://', 'https://')):
                errors.append(f'Repeated URL ({count}): {url}')
    if readable_links:
        errors.extend(readable_link_issues(content))
    return errors


def heading_anchors(content: str) -> set[str]:
    """GitHub-style Markdown heading IDs; stable ID-only headings need no HTML tags."""
    from markdown_it import MarkdownIt
    tokens = MarkdownIt('commonmark').parse(content)
    used = set()
    for index, token in enumerate(tokens):
        if token.type != 'heading_open':
            continue
        inline = tokens[index + 1]
        text = ''.join(t.content for t in inline.children or []
                       if t.type in ('text', 'code_inline', 'image'))
        slug = re.sub(r'[^\w\- ]', '', text.lower()).replace(' ', '-')
        anchor, number = slug, 0
        while anchor in used:
            number += 1
            anchor = f'{slug}-{number}'
        used.add(anchor)
    return used


def validate_file(file_path: Path, **options) -> list[str]:
    try:
        file_path = Path(file_path).resolve()
        content = file_path.read_text(encoding='utf-8')
        errors = validate_content(content, **options)
        for href in references(content, options.get('include_code', False))[0]:
            parsed = urlsplit(href)
            windows_path = bool(re.match(r'^[A-Za-z]:[/\\]', href))
            if (parsed.scheme and parsed.scheme != 'file' and not windows_path) or href.startswith('#'):
                continue
            path_text = unquote(urldefrag(href)[0] if windows_path else parsed.path)
            if parsed.scheme == 'file':
                if parsed.netloc and parsed.netloc != 'localhost':
                    path_text = (parsed.netloc + path_text if re.fullmatch(r'[A-Za-z]:', parsed.netloc)
                                 else f'//{parsed.netloc}{path_text}')
                if re.match(r'^/[A-Za-z]:/', path_text):
                    path_text = path_text[1:]
            if not path_text:
                continue
            target = (file_path.parent / path_text).resolve()
            if not target.exists():
                errors.append(f'Missing local file: {href}')
                continue
            fragment = unquote(parsed.fragment)
            if target.is_dir():
                if fragment:
                    errors.append(f'A directory link cannot have a document anchor: {href}')
                continue
            if fragment and target.suffix.lower() in ('.md', '.html', '.htm'):
                other = target.read_text(encoding='utf-8')
                ids = set(references(other)[1]) | heading_anchors(other)
                if fragment not in ids:
                    errors.append(f'Missing cross-file anchor: {href}')
            elif fragment and target.suffix.lower() == '.json':
                value = json.loads(target.read_text(encoding='utf-8'))
                try:
                    from .evidence import resolve_pointer
                    resolve_pointer(value, fragment)
                except (KeyError, ValueError, IndexError, TypeError):
                    errors.append(f'Missing JSON pointer: {href}')
        return errors
    except (OSError, UnicodeError, ValueError) as exc:
        return [f'{file_path}: {exc}']


@dataclass(frozen=True)
class Page:
    url: str
    status: int
    content_type: str
    text: str


def fetch_page(url: str, timeout: float = 15) -> Page:
    if urlsplit(url).scheme not in ('http', 'https'):
        raise ValueError('Only HTTP(S) fetching is supported')
    request = Request(url, headers={'User-Agent': 'ProjectLinkCheck/1.0'})
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as exc:
        exc.close()
        raise
    with response:
        data = response.read(16 * 1024 * 1024 + 1)
        if len(data) > 16 * 1024 * 1024:
            raise ValueError('Response exceeds 16 MiB')
        charset = response.headers.get_content_charset() or 'utf-8'
        return Page(response.url, response.status, response.headers.get_content_type(),
                    data.decode(charset, errors='replace'))


def check_network(urls: list[str], *, anchors: bool = False, timeout: float = 15,
                  fetcher=None) -> list[dict]:
    """Report source evidence only; absence in HTML is not absence from a JS-rendered DOM."""
    fetcher = fetcher or fetch_page
    cache = {}
    results = []
    for url in dict.fromkeys(urls):
        base, fragment = urldefrag(url)
        if not base.startswith(('http://', 'https://')):
            continue
        if anchors and not fragment:
            continue
        if base not in cache:
            try:
                cache[base] = fetcher(base, timeout)
            except Exception as exc:
                cache[base] = exc
        page = cache[base]
        if isinstance(page, Exception):
            results.append({'url': url, 'status': 'fetch-error', 'detail': str(page)})
            continue
        status = 'http-ok'
        details = {}
        if not 200 <= page.status < 300:
            status = 'http-error'
        elif anchors:
            if page.content_type not in ('text/html', 'application/xhtml+xml'):
                status = 'not-html'
            elif ':~:text=' in fragment:
                status = 'browser-check-required'
            else:
                html = HTMLReferences()
                html.feed(page.text)
                status = 'found-in-source' if unquote(fragment) in html.anchors else 'not-found-in-source'
                if status == 'not-found-in-source':
                    details = {'available_anchors': html.anchors[:100],
                               'anchor_count': len(html.anchors), 'source_bytes': len(page.text.encode('utf-8'))}
        results.append({'url': url, 'status': status, 'http_status': page.status,
                        'final_url': page.url, **details})
    return results
