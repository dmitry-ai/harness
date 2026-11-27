# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import asyncio
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import urllib.request
import zipfile
import zlib
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
# @used-by :mod:`unittest`
class DfHarnessS11Wave2aUpworkTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_upwork_data_parsers_and_formatters(self) -> None:
		from Df.Harness.Upwork.AttachmentExtractor import AttachmentExtractor
		from Df.Harness.Upwork.ClientMetadataExtractor import ClientMetadataExtractor
		from Df.Harness.Upwork.DocxExtractor import DocxExtractor
		from Df.Harness.Upwork.JobUrlParser import JobUrlParser
		from Df.Harness.Upwork.KbProjectMdFormatter import KbProjectMdFormatter
		from Df.Harness.Upwork.LoomVideoExtractor import LoomVideoExtractor
		from Df.Harness.Upwork.MarkdownTableSanitizer import MarkdownTableSanitizer
		from Df.Harness.Upwork.PdfExtractor import PdfExtractor
		from Df.Harness.Upwork.PdfLigatureRepairer import PdfLigatureRepairer
		from Df.Harness.Upwork.VideoDetector import VideoDetector
		self.assertEqual('~02abc123', JobUrlParser.normalize_job_id('https://www.upwork.com/jobs/~02abc123'))
		self.assertEqual('https://upwork.com/jobs/~02abc123', JobUrlParser.canonical_job_url('~02abc123'))
		self.assertEqual('~02abc123', JobUrlParser.extract_upwork_job_url_id('https://upwork.com/jobs/~02abc123'))
		self.assertEqual({'a': 'hello'}, JobUrlParser.resolve_nuxt_devalue([{'a': 1}, ['Ref', 2], 'hello']))
		names = ClientMetadataExtractor.extract_client_names([{'jobInfo': {'title': 'T'}, 'feedbackToClient': {'comment': 'Loved working with Alice on this.'}}])
		self.assertEqual('Alice', names[0]['name'])
		self.assertEqual(['shop.example.com'], ClientMetadataExtractor.extract_candidate_domains(['Visit www.shop.example.com today']))
		past = ClientMetadataExtractor.collect_unique_public_past_jobs({'job_id': '~02cur', 'work_history': [{'jobInfo': {'ciphertext': '~02old', 'title': 'Old'}}], 'open_jobs': [{'ciphertext': '~02open', 'title': 'Open'}], 'related_descriptions': {'~02old': {'description': 'Past desc.'}, '~02open': {'description': 'Open desc.'}}})
		self.assertEqual(2, len(past))
		self.assertEqual('~~~~', MarkdownTableSanitizer.markdown_fence('~~~'))
		self.assertEqual(['One.', 'Two.'], MarkdownTableSanitizer.split_sentences_one_per_line('One. Two.'))
		self.assertEqual(['- A: 1'], MarkdownTableSanitizer.format_table_bullet_rows([['1']], ['A']))
		self.assertEqual('- A: 1', MarkdownTableSanitizer.sanitize_kb_markdown('| A |\n| --- |\n| 1 |'))
		self.assertIn('# Questions', MarkdownTableSanitizer.structure_job_description('Scope:\n- Fix bug\nMain body.', ['Ready?']))
		self.assertEqual(('image', 'video', 'document', 'document'), (AttachmentExtractor.classify('a.png'), AttachmentExtractor.classify('a.mp4'), AttachmentExtractor.classify('raw.bin', b'%PDF-1.4'), AttachmentExtractor.classify('raw.bin', b'plain text')))
		self.assertEqual('https://loom.com/share/abc123', VideoDetector.canonical_video_url('https://www.loom.com/embed/abc123'))
		self.assertEqual(2, len(VideoDetector.detect('Watch https://www.loom.com/share/abc123', saved_attachments=[{'filename': 'demo.mp4', 'sha256': 's1'}])))
		self.assertEqual(('1 min 5 sec', '2 min', '9 sec', 'duration not specified'), (LoomVideoExtractor.format_duration_ru(65), LoomVideoExtractor.format_duration_ru(120), LoomVideoExtractor.format_duration_ru(9), LoomVideoExtractor.format_duration_ru(0)))
		self.assertEqual('Hello', LoomVideoExtractor.parse_webvtt_phrases('WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<b>Hello</b>\n')[0]['text'])
		md = KbProjectMdFormatter({'job_id': '~02cur', 'title': 'Audit', 'description': 'Fix store.', 'buyer': {'location': {'country': 'US', 'city': 'NY'}}, 'extra_sources': [{'name': 'spec.pdf', 'body': 'Spec.'}], 'work_history': [{'jobInfo': {'ciphertext': '~02old', 'title': 'Old'}}], 'related_descriptions': {'~02old': {'description': 'Old desc.'}}}).render()
		self.assertIn('## 2.2. Description in `spec.pdf`', md)
		self.assertTrue(all((callable(c) for c in (DocxExtractor, PdfExtractor, PdfLigatureRepairer))))
	# @used-by :mod:`unittest`
	def test_upwork_docx_pdf_xlsx_odt_and_loom_extractors(self) -> None:
		from Df.Harness.Upwork.AttachmentExtractor import AttachmentExtractor
		from Df.Harness.Upwork.DocxExtractor import DocxExtractor
		from Df.Harness.Upwork.LoomVideoExtractor import LoomVideoExtractor
		from Df.Harness.Upwork.PdfExtractor import PdfExtractor
		from Df.Harness.Upwork.PdfLigatureRepairer import PdfLigatureRepairer
		docx_buf = io.BytesIO()
		doc_xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body><w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>Main</w:t></w:r></w:p><w:p><w:hyperlink r:id="r1"><w:r><w:t>Site</w:t></w:r></w:hyperlink></w:p><w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>Bullet</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>K</w:t></w:r></w:p></w:tc></w:tr><w:tr><w:tc><w:p><w:r><w:t>V</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
		rels_xml = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="https://example.com"/></Relationships>'
		num_xml = '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/></w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num></w:numbering>'
		with zipfile.ZipFile(docx_buf, 'w') as zf:
			zf.writestr('word/document.xml', doc_xml)
			zf.writestr('word/_rels/document.xml.rels', rels_xml)
			zf.writestr('word/numbering.xml', num_xml)
		self.assertIn('[Site](https://example.com)', DocxExtractor(docx_buf.getvalue()).extract())
		xlsx_buf, odt_buf = (io.BytesIO(), io.BytesIO())
		with zipfile.ZipFile(xlsx_buf, 'w') as zf:
			zf.writestr('xl/sharedStrings.xml', '<sst xmlns="http://x"><si><t>Item</t></si></sst>')
			zf.writestr('xl/worksheets/sheet1.xml', '<ws xmlns="http://x"><sheetData><row><c t="s"><v>0</v></c><c><v>7</v></c></row></sheetData></ws>')
		with zipfile.ZipFile(odt_buf, 'w') as zf:
			zf.writestr('content.xml', '<office:doc xmlns:office="urn:o" xmlns:text="urn:t"><text:p>Hello ODT.</text:p></office:doc>')
		self.assertEqual('- Item; 7', AttachmentExtractor.extract_markdown('a.xlsx', xlsx_buf.getvalue()))
		self.assertEqual('Hello ODT.', AttachmentExtractor.extract_markdown('a.odt', odt_buf.getvalue()))
		self.assertIn('"k": 1', AttachmentExtractor.extract_markdown('a.json', b'{"k":1}'))
		self.assertEqual('Plain text', AttachmentExtractor.extract_markdown('a.rtf', b'{\\rtf1 Plain text}'))
		self.assertEqual('Body', AttachmentExtractor.extract_markdown('a.txt', b'Body'))
		cmap = b'begincmap\n<0010> <FB01>\n<0011> <FB02>\n<0020> <006F>\n<0021> <0065>\n<0022> <0072>\nendcmap'
		bt = b'BT [<0020000E00210022>] TJ ET'
		raw_pdf = b'%PDF-1.4\nstream\n' + zlib.compress(cmap) + b'\nendstream\nstream\n' + zlib.compress(bt) + b'\nendstream'
		self.assertEqual('offer', PdfLigatureRepairer.discover_repairs(raw_pdf).get('o er'))
		self.assertEqual('offer', PdfExtractor(raw_pdf, poppler_finder=lambda _: None).extract())
		self.assertEqual('a-b', PdfExtractor.join_wrapped_lines('a-', 'b'))
		apollo = {'RegularUserVideo:abc1': {'name': 'Demo', 'owner': {'__ref': 'RegularUser:u1'}, 'video_properties': {'duration': 30, 'screen_type': 'screen_cam'}}, 'RegularUser:u1': {'display_name': 'Bob'}, 'VideoTranscriptDetails:t1': {'source_url': 'https://cdn.loom.test/t.json'}}
		html = f'<script>window.__APOLLO_STATE__ = {json.dumps(apollo)};\n</script>'.encode('utf-8')
		tjson = json.dumps({'phrases': [{'ts': 5, 'value': 'Fix checkout.'}]}).encode('utf-8')
		# @used-by :meth:`DfHarnessS11Wave2aUpworkTests.test_upwork_docx_pdf_xlsx_odt_and_loom_extractors()`
		def _fake_open(req, tm):
			cm = mock.MagicMock()
			cm.__enter__.return_value.read.return_value = tjson if 'cdn.loom.test' in req.full_url else html
			return cm
		res = LoomVideoExtractor('https://loom.com/share/abc1', opener=_fake_open).extract()
		self.assertEqual('Bob', res['speaker'])
		self.assertIn('[00:05] Fix checkout.', res['markdown'])
	# @used-by :mod:`unittest`
	def test_upwork_extract_classes(self) -> None:
		from Df.Harness.Upwork.AttachmentDownloader import AttachmentDownloader
		from Df.Harness.Upwork.JobExtractor import JobExtractor
		from Df.Harness.Upwork.PageDecoder import PageDecoder
		from Df.Harness.Upwork.RpcClient import RpcClient
		from Df.Harness.Upwork.SafeRedirect import SafeRedirect
		from Df.Harness.Upwork.TabSelector import TabSelector
		self.assertTrue(AttachmentDownloader.upwork_host('https://www.upwork.com/jobs/~02abc'))
		self.assertFalse(AttachmentDownloader.upwork_host('http://evil.com/x'))
		with tempfile.TemporaryDirectory() as tmp:
			d = Path(tmp).resolve()
			self.assertEqual((d / 'a.txt').resolve(), AttachmentDownloader.attachment_path(d, 'a.txt'))
			req = urllib.request.Request('https://www.upwork.com/a', headers={'Cookie': 'c=1', 'Authorization': 'Bearer x'})
			red = SafeRedirect().redirect_request(req, None, 302, 'Found', {}, 'https://cdn.other.test/b')
			self.assertFalse(red.has_header('Cookie'))
			cm = mock.MagicMock()
			cm.__enter__.return_value.read.return_value = b'hello'
			with mock.patch('urllib.request.OpenerDirector.open', return_value=cm):
				dl = AttachmentDownloader({'fileName': 'a.txt', 'uri': '/att/a.txt'}, d, cookies=[{'domain': '.upwork.com', 'path': '/', 'name': 's', 'value': '1'}]).download()
			self.assertEqual(5, dl['bytes'])
		nuxt = json.dumps([{'vuex': 1}, {'jobDetails': 2}, {'job': 3}, {'ciphertext': '~02abc', 'title': 'T'}])
		self.assertEqual('~02abc', PageDecoder({'nuxt': nuxt}, '~02abc').decode()['job']['ciphertext'])
		tab = TabSelector([{'type': 'page', 'id': 't1', 'url': 'https://www.upwork.com/jobs/~02abc'}], '~02abc').select()
		self.assertEqual('t1', tab['id'])
		class _Ws:
			# @used-by :meth:`DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
			def __init__(self) -> None:
				self.sent: list[dict] = []
			# @used-by :meth:`DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
			async def send(self, txt: str) -> None:
				self.sent.append(json.loads(txt))
			# @used-by :meth:`DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
			async def recv(self) -> str:
				return json.dumps({'id': self.sent[-1]['id'], 'result': {'result': {'value': 42}}})
		val = asyncio.run(RpcClient(_Ws()).evaluate('40+2'))
		self.assertEqual(42, val)
		with self.assertRaises(PermissionError):
			JobExtractor('~02abc', config={'text': {'browser': {'sessions': {}}}}).extract()
	# @used-by :mod:`unittest`
	def test_upwork_project_management_classes(self) -> None:
		from Df.Harness.Upwork.CliRunner import CliRunner
		from Df.Harness.Upwork.ConfigurationChecker import ConfigurationChecker
		from Df.Harness.Upwork.DoctorAuditor import DoctorAuditor
		from Df.Harness.Upwork.GlobalCustomizationManager import GlobalCustomizationManager
		from Df.Harness.Upwork.InstancesReporter import InstancesReporter
		from Df.Harness.Upwork.ProjectConfigurator import ProjectConfigurator
		from Df.Harness.Upwork.ProjectDirResolver import ProjectDirResolver
		from Df.Harness.Upwork.ProjectInitializer import ProjectInitializer
		self.assertIn('sections', ProjectConfigurator.default_context_config())
		self.assertIn('final-turn-gate', GlobalCustomizationManager.canonical_global_hooks())
		self.assertIn('final-turn-gate', GlobalCustomizationManager.legacy_direct_global_hooks())
		self.assertIn('final-turn-gate', GlobalCustomizationManager.legacy_runner_global_hooks())
		self.assertIn('Generated by Harness', GlobalCustomizationManager.harness_hook_runner_source())
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp).resolve()
			daily = root / 'daily'
			pdir = ProjectDirResolver('~02proj1', 'example.test', '2026-11-26', daily).resolve_or_create()
			self.assertEqual(pdir, ProjectDirResolver('~02proj1', 'example.test', '2026-11-26', daily).resolve_or_create())
			cap = {'job_id': '~02proj2', 'title': 'Fix Checkout', 'description': 'Fix cart checkout bug.'}
			res = ProjectInitializer('~02proj2', domain_or_topic='shop.test', date_str='2026-11-26', daily_root=daily, extracted_data=cap, register_native=False).initialize()
			p2 = Path(res['project_dir'])
			self.assertTrue((p2 / '\ua616/project.json').is_file())
			self.assertTrue(ConfigurationChecker(p2).check()['valid'])
		self.assertIn('environments', InstancesReporter(check_exists=False).report())
		self.assertTrue(callable(DoctorAuditor) and callable(CliRunner))
if '__main__' == __name__:
	unittest.main()
