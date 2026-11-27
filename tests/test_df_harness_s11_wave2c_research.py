# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
import re
import sys
import tempfile
import unittest
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPTS_DIR))
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DfHarnessS11Wave2CResearchTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_batch_http_and_browser_collectors_and_site_summarizer(self) -> None:
		from Df.Harness.Research.BatchCollector import BatchCollector
		from Df.Harness.Research.BrowserCollector import BrowserCollector
		from Df.Harness.Research.HttpCollector import HttpCollector
		from Df.Harness.Research.Response import Response
		from Df.Harness.Research.SiteSummarizer import SiteSummarizer
		html = b'<html><head><title>Sample Page</title><meta name="description" content="Desc"></head><body><h1>Main</h1><p>Enough body words to make a valid non-challenge page for testing extraction and site summaries cleanly.</p></body></html>'
		fake_fetch = lambda url, headers, timeout: Response(url, 200, 'text/html', html)
		fake_cdp = lambda root, target, **kw: {'url': target, 'html': html.decode('utf-8'), 'target_id': 't1'}
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			http_res = HttpCollector(root, 'https://example.com/a', fetcher=fake_fetch, browser='never').collect()
			self.assertEqual(200, http_res['status'])
			self.assertIn('extraction', http_res)
			dom_res = BrowserCollector(root, 'https://example.com/b', cdp_fetcher=fake_cdp).collect()
			self.assertEqual('dom', dom_res['kind'])
			plan_res = BatchCollector(root, {'requests': [{'url': 'https://example.com/a', 'browser': 'never'}]}, fetcher=fake_fetch, browser='never').run()
			self.assertTrue(plan_res['complete'])
			self.assertEqual(1, plan_res['site_summary']['inspected_html_pages'])
			batch_http = BatchCollector.collect_http_batch(root, ['https://example.com/a'], fetcher=fake_fetch, browser='never')
			self.assertTrue(batch_http['complete'])
			batch_dom = BatchCollector.collect_browser_batch(root, ['https://example.com/b'], cdp_fetcher=fake_cdp)
			self.assertTrue(batch_dom['complete'])
			summary = SiteSummarizer(root, [http_res, dom_res]).summarize()
			self.assertEqual(2, summary['inspected_html_pages'])
	# @used-by :mod:`unittest`
	def test_evidence_querier_and_grepper(self) -> None:
		from Df.Harness.Research.Collector import Collector
		from Df.Harness.Research.EvidenceGrepper import EvidenceGrepper
		from Df.Harness.Research.EvidenceQuerier import EvidenceQuerier
		from Df.Harness.Research.Extractor import Extractor
		from Df.Harness.Research.Response import Response
		html = b'<html><head><title>Docs</title></head><body><h1 id="intro">Intro</h1><p>Target alpha keyword appears in this section with enough text to avoid challenge detection.</p></body></html>'
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			obs = Collector(root, 'https://docs.example.com/guide', fetcher=lambda u, h, t: Response(u, 200, 'text/html', html)).collect()
			Extractor.extract_observation(root, obs['observation'], 'html')
			q_res = EvidenceQuerier(root, urls=['https://docs.example.com/guide'], include_anchors=True, grep_pattern='alpha').query()
			self.assertTrue(q_res['valid'])
			self.assertEqual(1, q_res['observation_count'])
			self.assertIn('intro', q_res['observations'][0]['anchors'])
			self.assertEqual(1, q_res['observations'][0]['match_count'])
			blob_hits = EvidenceGrepper(re.compile('beta')).grep_blob(['line 1', 'beta line', 'line 3'], has_lc_anchors=True)
			self.assertEqual('#LC2', blob_hits[0]['anchor'])
	# @used-by :mod:`unittest`
	def test_extractor_json_summarizer_and_challenge_classifier(self) -> None:
		from Df.Harness.Research.ChallengeClassifier import ChallengeClassifier
		from Df.Harness.Research.Extractor import Extractor
		from Df.Harness.Research.JsonCollectionSummarizer import JsonCollectionSummarizer
		from Df.Harness.Research.MarkdownExtractor import MarkdownExtractor
		from Df.Harness.Research.SitemapExtractor import SitemapExtractor
		data = {'products': [{'id': 1, 'title': 'A', 'created_at': '2026-01-01T00:00:00Z', 'status': 'active', 'tags': ['sale']}, {'id': 2, 'title': 'B', 'created_at': '2026-01-02T00:00:00Z', 'status': 'active', 'tags': ['sale']}]}
		summ = JsonCollectionSummarizer(data).summarize()
		self.assertEqual(2, summ['products']['record_count'])
		shop = Extractor(json.dumps(data).encode('utf-8'), 'application/json', 'shopify').extract()
		self.assertEqual(2, shop['summary']['products']['record_count'])
		md_res = MarkdownExtractor('# Title {#top}\nBody text here.\n').extract()
		self.assertIn('top', md_res['anchors'])
		xml_str = '<?xml version="1.0"?><urlset><url><loc>https://example.com/</loc></url></urlset>'
		self.assertEqual(1, SitemapExtractor(xml_str).extract()['url_count'])
		self.assertTrue(ChallengeClassifier('<html><head><title>Just a moment...</title></head><body><p>Checking your browser</p></body></html>').is_challenge())
		self.assertFalse(ChallengeClassifier('<html><head><title>Home</title></head><body><p>Normal readable article content with plenty of visible words.</p></body></html>').is_challenge())
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			src = root / 'doc.md'
			src.write_text('# Heading\nHello world text.\n', encoding='utf-8')
			ef = Extractor.extract_file(root, 'doc.md', 'document')
			self.assertIn('extraction', ef)
	# @used-by :mod:`unittest`
	def test_links_markdown_lib_and_network_checker(self) -> None:
		from Df.Harness.Research.HtmlReferences import HtmlReferences
		from Df.Harness.Research.LinkAuditor import LinkAuditor
		from Df.Harness.Research.NetworkLinkChecker import NetworkLinkChecker
		from Df.Harness.Research.Page import Page
		from Df.Harness.lib.markdown import dfh_decode_file_uri, dfh_display_address, dfh_inline_links, dfh_markdown_it_parser, dfh_numeric_text, dfh_technical_label
		self.assertEqual('C:/a/b.md', dfh_decode_file_uri('file:///C:/a/b.md#x'))
		self.assertEqual('example.com/a', dfh_display_address('https://www.example.com/a'))
		self.assertTrue(dfh_technical_label('example.com/a', 'https://www.example.com/a'))
		self.assertEqual('Cost 42 ', dfh_numeric_text('Cost 42 [example.com/99](https://example.com/99)'))
		toks = dfh_markdown_it_parser().parseInline('[Doc](https://example.com)', {})[0].children
		self.assertEqual([('https://example.com', 'Doc')], list(dfh_inline_links(toks)))
		self.assertEqual([], LinkAuditor.readable_link_issues('[Ok](a/b.md)'))
		self.assertTrue(LinkAuditor.readable_link_issues('[Bad](a%20b.md)'))
		hr = HtmlReferences()
		hr.feed('<a id="sec" href="https://example.com">x</a>')
		self.assertEqual(['sec'], hr.anchors)
		chk = NetworkLinkChecker(['https://example.com/#sec'], anchors=True, fetcher=lambda u, t: Page(u, 200, 'text/html', '<h2 id="sec">S</h2>')).check()
		self.assertEqual('found-in-source', chk[0]['status'])
if '__main__' == __name__:
	unittest.main()