# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PdfMarkdownExtractor and DocxMarkdownExtractor classes with shared table/file pipeline in upwork_data.py":
# https://github.com/dmitry-ai/harness/issues/65
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile
import zlib
SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPT_DIR) not in sys.path:
	sys.path.insert(0, str(SCRIPT_DIR))
from agent_tools.upwork_data import DocxMarkdownExtractor, PdfMarkdownExtractor, discover_pdf_ligature_repairs, extract_attachment_markdown, format_table_bullet_rows, sanitize_kb_markdown
class UpworkDataExtractorTests(unittest.TestCase):
	def test_docx_extractor_tables_fields_numbering_and_heading_normalization(self):
		stream = io.BytesIO()
		doc_xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body><w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Audit Scope</w:t></w:r></w:p><w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>Tracking Goals</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Metric</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Target</w:t></w:r></w:p></w:tc></w:tr><w:tr><w:tc><w:p><w:r><w:t>Purchase</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>100%</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="2"/></w:numPr></w:pPr><w:r><w:t>Intro - </w:t></w:r><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText>HYPERLINK "https://loom.com/share/abc123"</w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>Watch Video Overview</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:body></w:document>'
		num_xml = '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:abstractNum w:abstractNumId="7"><w:lvl w:ilvl="0"><w:numFmt w:val="decimal"/></w:lvl></w:abstractNum><w:num w:numId="2"><w:abstractNumId w:val="7"/></w:num></w:numbering>'
		with zipfile.ZipFile(stream, 'w') as archive:
			archive.writestr('word/document.xml', doc_xml)
			archive.writestr('word/numbering.xml', num_xml)
		md = DocxMarkdownExtractor(stream.getvalue()).extract()
		self.assertIn('# Audit Scope', md)
		self.assertIn('## Tracking Goals', md)
		self.assertIn('- Metric: Purchase; Target: 100%', md)
		self.assertIn('1. Intro - [Watch Video Overview](https://loom.com/share/abc123)', md)
	def test_pdf_extractor_xml_layout_and_raw_stream_ligature_fallback(self):
		xml_sample = '<pdf2xml><page number="1"><fontspec id="0" size="12" family="Helvetica"/><fontspec id="1" size="16" family="Helvetica-Bold"/><text top="40" left="50" height="18" font="1">Phase 1: Overview</text><text top="80" left="50" height="14" font="0">•</text><text top="80" left="70" height="14" font="1">Goal:</text><text top="80" left="115" height="14" font="0">Fix <a href="https://example.org/checkout">checkout</a> server-</text><text top="98" left="70" height="14" font="0">side pipeline.</text></page></pdf2xml>'
		with patch.object(PdfMarkdownExtractor, '_run_poppler', return_value=xml_sample):
			md_xml = PdfMarkdownExtractor(b'%PDF-1.4').extract()
		self.assertIn('## Phase 1: Overview', md_xml)
		self.assertIn('- **Goal:** Fix [checkout](https://example.org/checkout) server-side pipeline.', md_xml)
		cmap = b'begincmap\n<0010> <FB01>\n<0011> <FB02>\n<0020> <006F>\n<0021> <0065>\n<0022> <0072>\nendcmap'
		bt = b'BT [<0020000E00210022>] TJ ET'
		raw_pdf = b'%PDF-1.4\nstream\n' + zlib.compress(cmap) + b'\nendstream\nstream\n' + zlib.compress(bt) + b'\nendstream'
		repairs = discover_pdf_ligature_repairs(raw_pdf)
		self.assertEqual('offer', repairs.get('o er'))
		with patch('agent_tools.upwork_data._find_poppler_tool', return_value=None):
			md_raw = PdfMarkdownExtractor(raw_pdf).extract()
		self.assertEqual('offer', md_raw)
	def test_shared_table_bullet_rows_across_markdown_and_csv(self):
		self.assertEqual(['- Channel: Web; Events: 42'], format_table_bullet_rows([[' Web ', ' 42 ']], ['Channel', 'Events']))
		self.assertEqual('- Channel: Web; Events: 42', sanitize_kb_markdown('| Channel | Events |\n| --- | --- |\n| Web | 42 |'))
		self.assertEqual('- Channel: Web; Events: 42', extract_attachment_markdown('report.csv', b'Channel,Events\nWeb,42\n'))
if '__main__' == __name__:
	unittest.main()
