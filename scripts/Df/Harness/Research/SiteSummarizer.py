# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit
import json
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SiteSummarizer:
	# @used-by :func:`agent_tools.research.compute_site_summary()`
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__build_batch_result()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_batch_http_and_browser_collectors_and_site_summarizer()`
	def __init__(self, root, results) -> None:
		self.__root = root
		self.__results = results
	# @used-by :meth:`SiteSummarizer.summarize()`
	@staticmethod
	def __load_html_ext(kb_dir: Path, item) -> tuple[str, dict] | None:
		r: tuple[str, dict] | None = None
		ok_item = isinstance(item, dict) and (not item.get('error')) and ('dom' == item.get('kind') or 200 <= (item.get('status') or 0) < 300)
		url = (item.get('url') or '') if ok_item else ''
		ext_rel = item.get('extraction') if ok_item else None
		if ok_item and ext_rel and (not urlsplit(url).path.lower().endswith(('.xml', '.txt', '.json'))):
			ext_file = kb_dir / ext_rel
			if ext_file.is_file():
				try:
					ext = json.loads(ext_file.read_text(encoding='utf-8'))
					if isinstance(ext, dict) and None is ext.get('sitemap') and 'headings' in ext:
						r = (url, ext)
				except (OSError, ValueError):
					r = None
		return r
	# @used-by :meth:`SiteSummarizer.summarize()`
	@classmethod
	def __record_page(cls, url: str, ext: dict, state: dict) -> None:
		state['html_pages'] += 1
		cls.__record_title_and_desc(url, ext, state)
		h1s = [h for h in ext.get('headings') or [] if isinstance(h, dict) and 1 == h.get('level')]
		if 0 == len(h1s):
			state['missing_h1'].append(url)
		elif 1 < len(h1s):
			state['multiple_h1'].append(url)
		wc = ext.get('word_count')
		if isinstance(wc, int) and 100 > wc:
			state['thin_urls'].append({'url': url, 'word_count': wc})
		ts = ext.get('tracking_summary') or {}
		state['all_identifiers'].update(ts.get('identifiers') or [])
		state['cms_domains'].update(ts.get('cms_technical_domains') or [])
	# @used-by :meth:`SiteSummarizer.__record_page()`
	@staticmethod
	def __record_title_and_desc(url: str, ext: dict, state: dict) -> None:
		title = (ext.get('title') or '').strip()
		if title:
			state['titles'].setdefault(title, []).append(url)
			if 65 < len(title):
				state['overlong_titles'].append({'url': url, 'title': title, 'length': len(title)})
		desc = ((ext.get('meta') or {}).get('description') or '').strip()
		if desc:
			state['descriptions'].setdefault(desc, []).append(url)
	# @used-by :func:`agent_tools.research.compute_site_summary()`
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__build_batch_result()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_batch_http_and_browser_collectors_and_site_summarizer()`
	def summarize(self) -> dict:
		from agent_tools.path_registry import project_paths
		kb_dir = project_paths(self.__root, exact_root=True).kb_dir
		state: dict = {'titles': {}, 'descriptions': {}, 'missing_h1': [], 'multiple_h1': [], 'overlong_titles': [], 'thin_urls': [], 'all_identifiers': set(), 'cms_domains': set(), 'html_pages': 0}
		for item in self.__results or []:
			loaded = self.__load_html_ext(kb_dir, item)
			if None is not loaded:
				self.__record_page(loaded[0], loaded[1], state)
		return {'inspected_html_pages': state['html_pages'], 'missing_h1_urls': state['missing_h1'], 'multiple_h1_urls': state['multiple_h1'], 'overlong_title_urls': state['overlong_titles'], 'duplicate_titles': {k: v for k, v in state['titles'].items() if 1 < len(v)}, 'duplicate_meta_descriptions': {k: v for k, v in state['descriptions'].items() if 1 < len(v)}, 'thin_content_urls': state['thin_urls'], 'all_tracking_identifiers': sorted(state['all_identifiers']), 'cms_technical_domains': sorted(state['cms_domains'])}
