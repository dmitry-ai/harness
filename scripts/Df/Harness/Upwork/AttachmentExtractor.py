# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import csv
from Df.Harness.Upwork.DocxExtractor import DocxExtractor
from Df.Harness.Upwork.MarkdownTableSanitizer import MarkdownTableSanitizer
from Df.Harness.Upwork.PdfExtractor import PdfExtractor
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class AttachmentExtractor:
	IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff', '.tif', '.avif', '.heic'}
	TEXT_DOC_EXTENSIONS = {'.pdf', '.docx', '.doc', '.rtf', '.odt', '.txt', '.md', '.markdown', '.rst', '.log', '.ini', '.cfg', '.conf', '.html', '.htm', '.xhtml', '.xml', '.svg', '.json', '.yaml', '.yml', '.toml', '.csv', '.tsv', '.xlsx', '.xls', '.xlsm', '.ods', '.js', '.ts', '.jsx', '.tsx', '.py', '.php', '.rb', '.java', '.cs', '.go', '.rs', '.c', '.cpp', '.h', '.css', '.scss', '.less', '.liquid', '.sql', '.sh', '.ps1', '.bat', '.har'}
	VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v', '.wmv', '.flv', '.mpeg', '.mpg'}
	# @used-by :meth:`AttachmentExtractor.__extract_text_like()`
	@staticmethod
	def __extract_csv(suffix: str, text: str) -> str:
		reader = list(csv.reader(io.StringIO(text), delimiter='\t' if '.tsv' == suffix else ','))
		headers = [h.strip() for h in reader[0]] if 1 < len(reader) else []
		rows = reader[1:] if 1 < len(reader) else reader
		return '\n'.join(MarkdownTableSanitizer.format_table_bullet_rows(rows, headers)) if reader else ''
	# @used-by :meth:`AttachmentExtractor.__extract_text_like()`
	@staticmethod
	def __extract_json(text: str) -> str:
		try:
			r = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
		except ValueError:
			r = MarkdownTableSanitizer.sanitize_kb_markdown(text)
		return r
	# @used-by :meth:`AttachmentExtractor.__extract_zip_doc()`
	@staticmethod
	def __extract_odt(raw_bytes: bytes) -> str:
		with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
			root = ET.fromstring(zf.read('content.xml'))
			paras = [''.join(p.itertext()).strip() for p in root.iter() if p.tag.endswith('}p')]
		return MarkdownTableSanitizer.sanitize_kb_markdown('\n'.join((s for p in paras if p for s in MarkdownTableSanitizer.split_sentences_one_per_line(p))))
	# @used-by :meth:`AttachmentExtractor.extract_markdown()`
	@classmethod
	def __extract_text_like(cls, suffix: str, text: str) -> str:
		if suffix in ('.md', '.markdown', '.txt'):
			body = MarkdownTableSanitizer.structure_job_description(text) if '.txt' == suffix else text
			r = MarkdownTableSanitizer.sanitize_kb_markdown(body)
		elif '.rtf' == suffix:
			plain = re.sub('\\\\[a-zA-Z]+-?\\d*\\s?', '', re.sub('\\\\par[d]?\\b', '\n', text)).replace('{', '').replace('}', '')
			r = MarkdownTableSanitizer.sanitize_kb_markdown(MarkdownTableSanitizer.structure_job_description(plain))
		elif '.json' == suffix:
			r = cls.__extract_json(text)
		elif suffix in ('.csv', '.tsv'):
			r = cls.__extract_csv(suffix, text)
		else:
			r = MarkdownTableSanitizer.sanitize_kb_markdown(text)
		return r
	# @used-by :meth:`AttachmentExtractor.extract_markdown()`
	@classmethod
	def __extract_zip_doc(cls, suffix: str, data: bytes, docx_fn) -> str | None:
		if '.docx' == suffix or (data.startswith(b'PK') and suffix in ('.docx', '.docm')):
			r: str | None = DocxExtractor(data).extract() if None is docx_fn else docx_fn(data)
		elif suffix in ('.xlsx', '.xlsm') and data.startswith(b'PK'):
			r = cls.extract_xlsx(data)
		elif '.odt' == suffix and data.startswith(b'PK'):
			r = cls.__extract_odt(data)
		else:
			r = None
		return r
	# @used-by :meth:`AttachmentExtractor.extract_xlsx()`
	@staticmethod
	def __xlsx_row_values(row, shared: list[str]) -> list[str]:
		r: list[str] = []
		for c in row:
			if not c.tag.endswith('}c'):
				continue
			v_el = next((ch for ch in c if ch.tag.endswith('}v') or ch.tag.endswith('}is')), None)
			if None is not v_el:
				raw_v = ''.join(v_el.itertext()).strip()
				if 's' == c.attrib.get('t', '') and raw_v.isdigit() and (int(raw_v) < len(shared)):
					r.append(shared[int(raw_v)].strip())
				elif raw_v:
					r.append(raw_v)
		return r
	# @used-by :func:`agent_tools.upwork_data.classify_attachment()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.__process_asset()`
	# @used-by :meth:`Df.Harness.Upwork.VideoDetector.VideoDetector.__scan_attachments()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.__check_attachment()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_data_parsers_and_formatters()`
	@classmethod
	def classify(cls, filename_or_path, raw_bytes: bytes | None=None) -> str:
		suffix = Path(str(filename_or_path)).suffix.lower()
		r = 'binary'
		if suffix in cls.IMAGE_EXTENSIONS:
			r = 'image'
		elif suffix in cls.VIDEO_EXTENSIONS:
			r = 'video'
		elif suffix in cls.TEXT_DOC_EXTENSIONS:
			r = 'document'
		elif None is not raw_bytes:
			if raw_bytes.startswith(b'%PDF'):
				r = 'document'
			elif b'\x00' not in raw_bytes[:4096]:
				try:
					raw_bytes.decode('utf-8')
					r = 'document'
				except UnicodeDecodeError:
					pass
		return r
	# @used-by :func:`agent_tools.upwork_data.extract_attachment_markdown()`
	# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.__load_document()`
	# @used-by :meth:`Df.Harness.Project.ExtraSourceBuilder.ExtraSourceBuilder.__process_asset()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.__check_attachment()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_docx_pdf_xlsx_odt_and_loom_extractors()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_z_upwork_docx_pdf_csv_and_config_coverage()`
	@classmethod
	def extract_markdown(cls, path_or_name, raw_bytes: bytes | None=None, *, pdf_fn=None, docx_fn=None) -> str:
		path = Path(str(path_or_name))
		data = path.read_bytes() if None is raw_bytes else raw_bytes
		suffix = path.suffix.lower()
		if '.pdf' == suffix or data.startswith(b'%PDF'):
			pdf_target = path if path.is_file() else None
			r = PdfExtractor(data, pdf_path=pdf_target).extract() if None is pdf_fn else pdf_fn(data, pdf_path=pdf_target)
		else:
			zipped = cls.__extract_zip_doc(suffix, data, docx_fn)
			r = cls.__extract_text_like(suffix, data.decode('utf-8-sig', errors='replace')) if None is zipped else zipped
		return r
	# @used-by :func:`agent_tools.upwork_data._extract_xlsx_markdown()`
	# @used-by :meth:`AttachmentExtractor.__extract_zip_doc()`
	@classmethod
	def extract_xlsx(cls, raw_bytes: bytes) -> str:
		with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
			shared = [''.join(si.itertext()) for si in ET.fromstring(zf.read('xl/sharedStrings.xml')) if si.tag.endswith('}si')] if 'xl/sharedStrings.xml' in zf.namelist() else []
			lines: list[str] = []
			for name in sorted((n for n in zf.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'))):
				for row in ET.fromstring(zf.read(name)).iter():
					if row.tag.endswith('}row'):
						vals = cls.__xlsx_row_values(row, shared)
						if vals:
							lines.append('- ' + '; '.join(vals))
			r = MarkdownTableSanitizer.sanitize_kb_markdown('\n'.join(lines))
		return r
