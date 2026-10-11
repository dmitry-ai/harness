"""Markdown-aware structural checks, plus opt-in HTTP/source-HTML checks."""

from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urldefrag, urlsplit
from urllib.request import Request, urlopen


class HTMLReferences(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get('id'):
            self.anchors.append(values['id'])
        if tag == 'a':
            if values.get('name') and values['name'] != values.get('id'):
                self.anchors.append(values['name'])
            if values.get('href'):
                self.links.append(values['href'])


def _bare_urls(text: str):
    # Only plain-text tokens reach this lexer; Markdown is parsed by markdown-it.
    for match in re.finditer(r'https?://[^\s<>`"\x00-\x1f]+', text):
        url = match.group().rstrip('.,;!?')
        for left, right in [('(', ')'), ('[', ']')]:
            while url.endswith(right) and url.count(right) > url.count(left):
                url = url[:-1]
        yield url


def references(content: str, include_code: bool = False) -> tuple[list[str], list[str]]:
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        requirements = Path(__file__).resolve().parents[1] / 'requirements-agent-tools.txt'
        raise RuntimeError(f'Install {requirements} with this Python interpreter') from exc
    parser = MarkdownIt('commonmark', {'html': True})
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
                     unique_urls: bool = False, include_code: bool = False) -> list[str]:
    links, anchors = references(content, include_code)
    errors = []
    for anchor, count in Counter(anchors).items():
        if count > 1:
            errors.append(f'Duplicate explicit HTML anchor: {anchor}')
    for url in links:
        try:
            parsed = urlsplit(url)
            if parsed.scheme.lower() in ('http', 'https'):
                if not parsed.hostname or any(c.isspace() for c in url):
                    errors.append(f'Invalid HTTP URL: {url}')
                _ = parsed.port  # Validate invalid ports and bracketed hosts.
            elif local_anchors and url.startswith('#') and unquote(url[1:]) not in anchors:
                errors.append(f'No explicit HTML anchor for {url}; renderer-generated IDs need separate verification')
        except ValueError as exc:
            errors.append(f'Invalid URL {url}: {exc}')
    if unique_urls:
        for url, count in Counter(links).items():
            if count > 1 and url.startswith(('http://', 'https://')):
                errors.append(f'Repeated URL ({count}): {url}')
    return errors


def validate_file(file_path: Path, **options) -> list[str]:
    try:
        return validate_content(Path(file_path).read_text(encoding='utf-8'), **options)
    except (OSError, UnicodeError) as exc:
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
    with urlopen(request, timeout=timeout) as response:
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
        results.append({'url': url, 'status': status, 'http_status': page.status,
                        'final_url': page.url})
    return results
