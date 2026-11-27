# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from urllib.error import HTTPError
from urllib.parse import unquote, urldefrag, urlsplit
from urllib.request import Request, urlopen
from Df.Harness.Research.HtmlReferences import HtmlReferences
from Df.Harness.Research.Page import Page
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class NetworkLinkChecker:
	# @used-by :func:`Df.Harness.lib.text_sources.dfh_check_source_links()`
	# @used-by :func:`agent_tools.links.check_network()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_links_markdown_lib_and_network_checker()`
	def __init__(self, urls: list[str], *, anchors: bool=False, timeout: float=15, fetcher=None) -> None:
		self.__urls = urls
		self.__anchors = anchors
		self.__timeout = timeout
		self.__fetcher = fetcher or self.fetch_page
	# @used-by :meth:`NetworkLinkChecker.__evaluate_page()`
	@classmethod
	def __check_anchor_status(cls, page: Page, fragment: str) -> tuple[str, dict]:
		if page.content_type in ('text/markdown', 'text/x-markdown'):
			from Df.Harness.Research.MarkdownExtractor import MarkdownExtractor
			md_info = MarkdownExtractor(page.text).extract()
			avail = sorted(set(md_info['anchors']) - set(md_info['ambiguous_anchors']))
			r = cls.__match_anchor(fragment, avail, page.text)
		elif page.content_type not in ('text/html', 'application/xhtml+xml'):
			r = ('not-html', {})
		elif ':~:text=' in fragment:
			r = ('browser-check-required', {})
		else:
			html = HtmlReferences()
			html.feed(page.text)
			r = cls.__match_anchor(fragment, html.anchors, page.text)
		return r
	# @used-by :meth:`NetworkLinkChecker.check()`
	def __evaluate_page(self, url: str, page: Page, fragment: str) -> dict:
		details: dict = {}
		if not 200 <= page.status < 300:
			status = 'http-error'
		elif self.__anchors:
			status, details = self.__check_anchor_status(page, fragment)
		else:
			status = 'http-ok'
		return {'url': url, 'status': status, 'http_status': page.status, 'final_url': page.url, **details}
	# @used-by :meth:`NetworkLinkChecker.check()`
	def __fetch_cached(self, base: str, cache: dict) -> Page | Exception:
		if base not in cache:
			try:
				cache[base] = self.__fetcher(base, self.__timeout)
			except Exception as exc:
				cache[base] = exc
		return cache[base]
	# @used-by :meth:`NetworkLinkChecker.__check_anchor_status()`
	@staticmethod
	def __match_anchor(fragment: str, anchors: list[str], text: str) -> tuple[str, dict]:
		if unquote(fragment) in anchors:
			r: tuple[str, dict] = ('found-in-source', {})
		else:
			r = ('not-found-in-source', {'available_anchors': anchors[:100], 'anchor_count': len(anchors), 'source_bytes': len(text.encode('utf-8'))})
		return r
	# @used-by :func:`Df.Harness.lib.text_sources.dfh_check_source_links()`
	# @used-by :func:`agent_tools.links.check_network()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_links_markdown_lib_and_network_checker()`
	def check(self) -> list[dict]:
		cache: dict = {}
		results: list[dict] = []
		for url in dict.fromkeys(self.__urls):
			base, fragment = urldefrag(url)
			if base.startswith(('http://', 'https://')) and (not (self.__anchors and (not fragment))):
				page = self.__fetch_cached(base, cache)
				if isinstance(page, Exception):
					results.append({'url': url, 'status': 'fetch-error', 'detail': str(page)})
				else:
					results.append(self.__evaluate_page(url, page, fragment))
		return results
	# @used-by :func:`agent_tools.links.fetch_page()`
	# @used-by :meth:`NetworkLinkChecker.__init__()`
	@staticmethod
	def fetch_page(url: str, timeout: float=15) -> Page:
		if urlsplit(url).scheme not in ('http', 'https'):
			raise ValueError('Only HTTP(S) fetching is supported')
		request = Request(url, headers={'User-Agent': 'ProjectLinkCheck/1.0', 'Accept': 'text/html,application/xhtml+xml,text/markdown;q=0.9,*/*;q=0.8'})
		try:
			response = urlopen(request, timeout=timeout)
		except HTTPError as exc:
			exc.close()
			raise
		with response:
			data = response.read(16 * 1024 * 1024 + 1)
			if 16 * 1024 * 1024 < len(data):
				raise ValueError('Response exceeds 16 MiB')
			charset = response.headers.get_content_charset() or 'utf-8'
			r = Page(response.url, response.status, response.headers.get_content_type(), data.decode(charset, errors='replace'))
		return r
