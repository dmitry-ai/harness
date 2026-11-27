# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import zipfile
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from Df.Harness.Research.BatchCollector import BatchCollector
from Df.Harness.Research.DomCapturer import DomCapturer
from Df.Harness.Research.Extractor import Extractor
from Df.Harness.Research.LinkAuditor import LinkAuditor
from Df.Harness.Research.NetworkLinkChecker import NetworkLinkChecker
from Df.Harness.Research.ObservationBundleScanner import ObservationBundleScanner
from Df.Harness.Research.Response import Response
from Df.Harness.Research.SitemapExtractor import SitemapExtractor
from Df.Harness.Text.Browser.GuardedCdp import GuardedCdp
from Df.Harness.lib.research import dfh_classify_network_error, dfh_extract_github_blob_lines, dfh_inside, dfh_select_dom_tab
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DfHarnessS11Wave2CCovResearchTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_batch_lazy_headless_and_http_browser_fallback(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			fake_shell = SimpleNamespace(__enter__=lambda: fake_shell, close=lambda: None)
			dom_payload = {'url': 'https://example.com/ch', 'final_url': 'https://example.com/ch', 'html': '<html><head><title>OK</title></head><body><p>Loaded body text</p></body></html>'}
			with patch('Df.Harness.Text.Browser.HeadlessShell.HeadlessShell', return_value=fake_shell), patch('Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.collect', return_value=dom_payload):
				out = BatchCollector(root, {'requests': [{'url': 'https://example.com/ch'}]}, fetcher=lambda u, _h, _t: Response(u, 403, 'text/html', b'blocked'), browser='auto').run()
			self.assertTrue(out['results'][0]['browser_fallback'])
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_dom_capturer_and_network_link_checker_fetch(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			cfg = {'workspace_root': str(root), 'text': {'browser': {'sessions': {'s1': {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222', 'profile': {'path': '/tmp/p', 'argument': '--user-data-dir'}, 'allowed_operations': ['read'], 'target_url_patterns': ['https://example.com/*']}}}}}
			guard = GuardedCdp(root, {'session_id': 's1', 'target_id': 't1'}, config=cfg)
			ident = {'browser': {'websocket_url': 'ws://1'}, 'profile': 'p', 'account': 'a', 'target': {'id': 't1', 'url': 'https://example.com/dom'}}
			native = {'result': {'value': {'url': 'https://example.com/dom', 'html': '<html><head><title>DOM</title></head><body><p>Body text</p></body></html>'}}}
			with patch.object(GuardedCdp, 'inspect', return_value=ident), patch.object(GuardedCdp, 'call', return_value=(native, ident)):
				cap = DomCapturer(root, 'https://example.com/dom', 't1', session_id='s1', guard=guard).capture()
			self.assertIn('extraction', cap)
			headers = SimpleNamespace(get_content_charset=lambda: 'utf-8', get_content_type=lambda: 'text/html')
			resp_cm = MagicMock(url='https://example.com', status=200, headers=headers)
			resp_cm.__enter__.return_value = resp_cm
			resp_cm.read.return_value = b'<html>ok</html>'
			with patch('Df.Harness.Research.NetworkLinkChecker.urlopen', return_value=resp_cm):
				page = NetworkLinkChecker.fetch_page('https://example.com')
			self.assertEqual(200, page.status)
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_extractor_docx_pdf_tracking_and_sitemap_images(self) -> None:
		buf = io.BytesIO()
		with zipfile.ZipFile(buf, 'w') as zf:
			zf.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Hello Docx</w:t></w:r></w:p></w:body></w:document>')
		docx_res = Extractor(buf.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'document', status=200).extract()
		self.assertIn('Hello Docx', docx_res['text'])
		with patch('agent_tools.upwork_data.extract_pdf_markdown', return_value='PDF line one'):
			pdf_res = Extractor(b'%PDF-1.4', 'application/pdf', 'document', status=200).extract()
		self.assertEqual(['PDF line one'], pdf_res['paragraphs'])
		tr_res = Extractor(b'<html><script>webPixelsConfigList = [{"id":"1"}]; wpmLoader = bad;</script></html>', 'text/html', 'tracking', status=200).extract()
		self.assertIn('webPixelsConfigList', tr_res['embedded_json'])
		self.assertTrue(bool(tr_res['embedded_json_unparsed']))
		sm_xml = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"><url><loc>https://example.com/p</loc><image:image><image:loc>https://example.com/i.png</image:loc><image:title>Select to expand</image:title></image:image></url></urlset>'
		sm = SitemapExtractor(sm_xml).extract()
		self.assertEqual(1, len(sm['urls'][0]['images']))
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_link_auditor_and_observation_bundle_scanner(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'target.md').write_text('# Section One\nText\n', encoding='utf-8')
			(root / 'data.json').write_text('{"a": {"b": 1}}', encoding='utf-8')
			doc = root / 'doc.md'
			doc.write_text('See [T](target.md#section-one), [J](data.json#/a/b), [E](https://example.com/x).\n', encoding='utf-8')
			self.assertEqual([], LinkAuditor(doc, local_anchors=True, readable_links=True).validate_file())
			j_dir, m_dir = (root / 'obs_j', root / 'obs_m')
			j_dir.mkdir()
			m_dir.mkdir()
			(j_dir / 'response.bin').write_text(json.dumps({'title': 'Json Title'}), encoding='utf-8')
			(m_dir / 'response.bin').write_text('# Md Title\nSome markdown content here.\n', encoding='utf-8')
			j_state = ObservationBundleScanner(j_dir / 'obs.json', {'url': 'https://example.com/j', 'status': 200, 'content_type': 'application/json'}, True).scan()[0]
			m_state = ObservationBundleScanner(m_dir / 'obs.json', {'url': 'https://example.com/m', 'status': 200, 'content_type': 'text/markdown'}, True).scan()[0]
			self.assertEqual('Json Title', j_state['title'])
			self.assertEqual('Md Title', m_state['title'])
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_research_lib_blob_errors_relocation_and_tab(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td) / 'new_root'
			old_root = Path(td) / 'old_root'
			root.mkdir()
			old_root.mkdir()
			self.assertEqual(['a', 'b'], dfh_extract_github_blob_lines('<script data-target="react-app.embeddedData">{"payload":{"blob":{"rawLines":["a","b"]}}}</script>'))
			self.assertEqual(['first', 'second'], dfh_extract_github_blob_lines('<td id="LC1">first</td><td id="LC2">second</td>'))
			self.assertEqual(('dns_error', False), dfh_classify_network_error(socket.gaierror('nx')))
			self.assertEqual(('tcp_timeout', None), dfh_classify_network_error(TimeoutError('to')))
			self.assertEqual(('connection_refused', True), dfh_classify_network_error(ConnectionRefusedError('ref')))
			self.assertEqual(('value_error', None), dfh_classify_network_error(ValueError('val')))
			self.assertEqual('t1', dfh_select_dom_tab([{'type': 'page', 'id': 't1', 'url': 'https://example.com/p#a'}], 'https://example.com/p', 't1')['id'])
			from agent_tools.path_registry import _path_key
			reg = SimpleNamespace(relocations={_path_key(old_root.resolve()): str(root.resolve())})
			with patch('agent_tools.path_registry.load_registry', return_value=reg), patch('agent_tools.path_registry.same_project_root', return_value=True):
				mapped = dfh_inside(root, old_root / 'a.txt')
			self.assertEqual((root / 'a.txt').resolve(), mapped)
if '__main__' == __name__:
	unittest.main()
