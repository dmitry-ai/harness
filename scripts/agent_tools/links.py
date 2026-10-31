# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
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
	def decode(match):
		encoded = match.group()
		raw = bytes.fromhex(encoded.replace('%', ''))
		result, offset = ([], 0)
		for char in raw.decode('utf-8', errors='surrogateescape'):
			size = len(char.encode('utf-8', errors='surrogateescape')) * 3
			original = encoded[offset:offset + size]
			offset += size
			safe_ascii = char.isascii() and (char.isalnum() or char in ' -._~')
			safe_unicode = 160 <= ord(char) < 55296 or 57344 <= ord(char) <= 1114111
			result.append(char if safe_ascii or safe_unicode else original)
		r = ''.join(result)
		return r
	return re.sub('(?:%[0-9a-fA-F]{2})+', decode, value)
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
# https://github.com/dmitry-ai/harness/issues/9
def readable_reference(value: str | Path) -> str:
	value = value.as_posix() if isinstance(value, Path) else value
	base, fragment_sep, fragment = value.partition('#')
	path, query_sep, query = base.partition('?')
	if path.lower().startswith('file:'):
		parsed = urlsplit(path)
		path = parsed.path
		if parsed.netloc and 'localhost' != parsed.netloc:
			path = '//' + parsed.netloc + path
		elif re.match('^/[A-Za-z]:/', path):
			path = path[1:]
	r = _readable_escapes(path) + query_sep + query + fragment_sep + _readable_escapes(fragment)
	return r
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
# https://github.com/dmitry-ai/harness/issues/9
def markdown_link(label: str | None, target: str | Path) -> str:
	target = readable_reference(target)
	if any((char in target for char in '\r\n<>')):
		raise ValueError('A document link cannot contain line endings or literal angle brackets')
	text = target if None is label else label
	text = text.replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')
	destination = f'<{target}>' if any((char.isspace() or char in '()' for char in target)) else target
	r = f'[{text}]({destination})'
	return r
# 2026-10-18 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
# https://github.com/dmitry-ai/harness/issues/9
def readable_link_issues(content: str, *, allow_unencoded_file_uri: bool=False) -> list[str]:
	from markdown_it import MarkdownIt
	parser = MarkdownIt('commonmark', {'html': True})
	parser.normalizeLink = lambda value: value
	parser.validateLink = lambda value: True
	targets, quote_depth = ([], 0)
	html = HTMLReferences(authored_only=True)
	for block in parser.parse(content):
		if 'blockquote_open' == block.type:
			quote_depth += 1
		elif 'blockquote_close' == block.type:
			quote_depth -= 1
		if quote_depth:
			continue
		if 'html_block' == block.type:
			html.feed(block.content)
		for token in block.children or []:
			if 'link_open' == token.type:
				targets.append(token.attrGet('href'))
			elif 'image' == token.type:
				targets.append(token.attrGet('src'))
			elif 'html_inline' == token.type:
				html.feed(token.content)
			elif 'text' == token.type:
				targets.extend(_document_urls(token.content))
	errors = []
	for target in dict.fromkeys(targets + html.links):
		if allow_unencoded_file_uri and target.lower().startswith('file:///') and ('%' not in target):
			target_check = re.sub('^file:///+(?=[A-Za-z]:/)', '', target, flags=re.IGNORECASE)
			if readable_reference(target_check) == target_check:
				continue
		readable = readable_reference(target)
		if target != readable:
			errors.append(f'LINK-5: Use a readable document link: {readable} (instead of {target})')
	r = errors
	return r
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
		if 'a' == tag:
			if values.get('name') and values['name'] != values.get('id'):
				self.anchors.append(values['name'])
			if values.get('href'):
				self.links.append(values['href'])
		elif 'img' == tag and values.get('src'):
			self.links.append(values['src'])
	def handle_endtag(self, tag):
		if self.authored_only and tag in ('pre', 'code', 'blockquote'):
			self.literal_depth = max(0, self.literal_depth - 1)
	def handle_data(self, data):
		if self.authored_only and (not self.literal_depth):
			self.links.extend(_document_urls(data))
def _bare_urls(text: str):
	for match in re.finditer('https?://[^\\s<>`"\\x00-\\x1f]+', text):
		url = match.group().rstrip('.,;!?')
		for left, right in [('(', ')'), ('[', ']')]:
			while url.endswith(right) and url.count(right) > url.count(left):
				url = url[:-1]
		yield url
def _document_urls(text: str):
	yield from _bare_urls(text)
	for match in re.finditer('(?:file://|[A-Za-z]:[/\\\\])[^\\s<>`"\\x00-\\x1f]+', text):
		yield match.group().rstrip('.,;!?)')
def references(content: str, include_code: bool=False) -> tuple[list[str], list[str]]:
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
		if 'html_block' == block.type:
			html.feed(block.content)
		depth = 0
		for token in block.children or []:
			if 'link_open' == token.type:
				depth += 1
				links.append(token.attrGet('href'))
			elif 'link_close' == token.type:
				depth -= 1
			elif 'html_inline' == token.type:
				html.feed(token.content)
			elif 'text' == token.type and 0 == depth:
				links.extend(_bare_urls(token.content))
			elif 'code_inline' == token.type and include_code:
				links.extend(_bare_urls(token.content))
	r = (links + html.links, html.anchors)
	return r
def validate_content(content: str, *, local_anchors: bool=False, unique_urls: bool=False, include_code: bool=False, readable_links: bool=False) -> list[str]:
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
				if not parsed.hostname or any((c.isspace() for c in url)):
					errors.append(f'Invalid HTTP URL: {url}')
				_ = parsed.port
			elif local_anchors and url.startswith('#') and (unquote(url[1:]) not in available_anchors):
				errors.append(f'Missing local anchor: {url}')
		except ValueError as exc:
			errors.append(f'Invalid URL {url}: {exc}')
	if unique_urls:
		for url, count in Counter(links).items():
			if count > 1 and url.startswith(('http://', 'https://')):
				errors.append(f'Repeated URL ({count}): {url}')
	if readable_links:
		errors.extend(readable_link_issues(content))
	r = errors
	return r
def heading_anchors(content: str) -> set[str]:
	from markdown_it import MarkdownIt
	tokens = MarkdownIt('commonmark').parse(content)
	used = set()
	for index, token in enumerate(tokens):
		if 'heading_open' != token.type:
			continue
		inline = tokens[index + 1]
		text = ''.join((t.content for t in inline.children or [] if t.type in ('text', 'code_inline', 'image')))
		slug = re.sub('[^\\w\\- ]', '', text.lower()).replace(' ', '-')
		anchor, number = (slug, 0)
		while anchor in used:
			number += 1
			anchor = f'{slug}-{number}'
		used.add(anchor)
	r = used
	return r
# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
def validate_file(file_path: Path, **options) -> list[str]:
	try:
		file_path = Path(file_path).resolve()
		content = file_path.read_text(encoding='utf-8')
		errors = validate_content(content, **options)
		for href in references(content, options.get('include_code', False))[0]:
			parsed = urlsplit(href)
			windows_path = bool(re.match('^[A-Za-z]:[/\\\\]', href))
			if parsed.scheme and 'file' != parsed.scheme and (not windows_path) or href.startswith('#'):
				continue
			path_text = unquote(urldefrag(href)[0] if windows_path else parsed.path)
			if 'file' == parsed.scheme:
				if parsed.netloc and 'localhost' != parsed.netloc:
					path_text = parsed.netloc + path_text if re.fullmatch('[A-Za-z]:', parsed.netloc) else f'//{parsed.netloc}{path_text}'
				if re.match('^/[A-Za-z]:/', path_text):
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
			elif fragment and '.json' == target.suffix.lower():
				value = json.loads(target.read_text(encoding='utf-8'))
				try:
					from .evidence import resolve_pointer
					resolve_pointer(value, fragment)
				except (KeyError, ValueError, IndexError, TypeError):
					errors.append(f'Missing JSON pointer: {href}')
		r = errors
	except (OSError, UnicodeError, ValueError) as exc:
		r = [f'{file_path}: {exc}']
	return r
@dataclass(frozen=True)
class Page:
	url: str
	status: int
	content_type: str
	text: str
def fetch_page(url: str, timeout: float=15) -> Page:
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
		r = Page(response.url, response.status, response.headers.get_content_type(), data.decode(charset, errors='replace'))
	return r
def check_network(urls: list[str], *, anchors: bool=False, timeout: float=15, fetcher=None) -> list[dict]:
	fetcher = fetcher or fetch_page
	cache = {}
	results = []
	for url in dict.fromkeys(urls):
		base, fragment = urldefrag(url)
		if not base.startswith(('http://', 'https://')):
			continue
		if anchors and (not fragment):
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
				if 'not-found-in-source' == status:
					details = {'available_anchors': html.anchors[:100], 'anchor_count': len(html.anchors), 'source_bytes': len(page.text.encode('utf-8'))}
		results.append({'url': url, 'status': status, 'http_status': page.status, 'final_url': page.url, **details})
	r = results
	return r
