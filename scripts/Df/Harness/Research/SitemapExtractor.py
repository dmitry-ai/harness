# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from urllib.parse import urlsplit
import re
import xml.etree.ElementTree as ET
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SitemapExtractor:
	# @used-by :func:`agent_tools.research._extract_sitemap()`
	# @used-by :meth:`Df.Harness.Research.ChallengeClassifier.ChallengeClassifier.__is_sitemap_input()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_html()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_extractor_docx_pdf_tracking_and_sitemap_images()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_extractor_json_summarizer_and_challenge_classifier()`
	def __init__(self, text: str) -> None:
		self.__text = text
	# @used-by :meth:`SitemapExtractor.extract()`
	@staticmethod
	def __build_issues(urls: list[dict], img_to_pages: dict[str, list[str]], polluted_titles: set[str]) -> dict:
		unescaped = [u['loc'] for u in urls if ' ' in u['loc'] or '%20' in u['loc']]
		templates = [u['loc'] for u in urls if re.search('(?i)(?:blog-post-title|new-page|sample-page|copy-of|lorem-ispum|lorem-ipsum|/home$)', u['loc'])]
		paths = [urlsplit(u['loc']).path for u in urls]
		root_missing = any(('/home' == p.rstrip('/') for p in paths)) and (not any((p in ('', '/') for p in paths)))
		dup_imgs = {k: v for k, v in sorted(img_to_pages.items()) if 1 < len(v)}
		return {'unescaped_spaces_in_loc': unescaped, 'template_slug_urls': templates, 'root_url_missing': root_missing, 'polluted_image_titles': sorted(polluted_titles), 'duplicate_image_locs': dup_imgs}
	# @used-by :meth:`SitemapExtractor.extract()`
	@classmethod
	def __collect_urls(cls, root_el) -> tuple[list[dict], dict[str, list[str]], set[str]]:
		urls: list[dict] = []
		img_to_pages: dict[str, list[str]] = {}
		polluted_titles: set[str] = set()
		for child in root_el:
			if child.tag.rsplit('}', 1)[-1].lower() in ('url', 'sitemap'):
				entry = cls.__parse_entry(child, polluted_titles)
				if None is not entry:
					urls.append(entry)
					for img_item in entry['images']:
						img_to_pages.setdefault(img_item['loc'], []).append(entry['loc'])
		return (urls, img_to_pages, polluted_titles)
	# @used-by :meth:`SitemapExtractor.__collect_urls()`
	@classmethod
	def __parse_entry(cls, child, polluted_titles: set[str]) -> dict | None:
		entry: dict = {'loc': '', 'lastmod': None, 'changefreq': None, 'priority': None, 'images': []}
		for field_el in child:
			fname = field_el.tag.rsplit('}', 1)[-1].lower()
			if fname in ('loc', 'lastmod', 'changefreq', 'priority'):
				entry[fname] = (field_el.text or '').strip()
			elif 'image' == fname:
				img_item = cls.__parse_image(field_el, polluted_titles)
				if None is not img_item:
					entry['images'].append(img_item)
		return entry if entry['loc'] else None
	# @used-by :meth:`SitemapExtractor.__parse_entry()`
	@staticmethod
	def __parse_image(field_el, polluted_titles: set[str]) -> dict | None:
		img_item: dict = {'loc': '', 'title': None, 'caption': None}
		for img_child in field_el:
			iname = img_child.tag.rsplit('}', 1)[-1].lower()
			if iname in ('loc', 'title', 'caption'):
				img_item[iname] = (img_child.text or '').strip()
		if img_item['loc'] and img_item['title'] and 'select to expand' in img_item['title'].lower():
			polluted_titles.add(img_item['title'])
		return img_item if img_item['loc'] else None
	# @used-by :meth:`SitemapExtractor.extract()`
	def __parse_root(self):
		stripped = self.__text.lstrip()
		r = None
		if stripped.startswith('<?xml') or '<urlset' in stripped[:1500] or '<sitemapindex' in stripped[:1500]:
			try:
				root_el = ET.fromstring(self.__text.encode('utf-8'))
				root_name = root_el.tag.rsplit('}', 1)[-1].lower()
				r = (root_el, root_name) if root_name in ('urlset', 'sitemapindex') else None
			except ET.ParseError:
				r = None
		return r
	# @used-by :func:`agent_tools.research._extract_sitemap()`
	# @used-by :meth:`Df.Harness.Research.ChallengeClassifier.ChallengeClassifier.__is_sitemap_input()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_html()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_extractor_docx_pdf_tracking_and_sitemap_images()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_extractor_json_summarizer_and_challenge_classifier()`
	def extract(self) -> dict | None:
		parsed = self.__parse_root()
		if None is parsed:
			r: dict | None = None
		else:
			root_el, root_name = parsed
			urls, img_to_pages, polluted_titles = self.__collect_urls(root_el)
			r = {'type': root_name, 'url_count': len(urls), 'urls': urls, 'sitemap_issues': self.__build_issues(urls, img_to_pages, polluted_titles)}
		return r
