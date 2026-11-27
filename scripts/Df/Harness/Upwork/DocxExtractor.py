# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.links import markdown_link
from Df.Harness.Upwork.MarkdownTableSanitizer import MarkdownTableSanitizer
import io
import re
import xml.etree.ElementTree as ET
import zipfile
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class DocxExtractor:
	R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
	W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
	# @used-by :func:`agent_tools.upwork_data.extract_docx_markdown()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.__extract_zip_doc()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_docx_pdf_xlsx_odt_and_loom_extractors()`
	# @used-by :meth:`test_upwork_data.UpworkDataExtractorTests.test_docx_extractor_tables_fields_numbering_and_heading_normalization()`
	def __init__(self, raw_bytes: bytes) -> None:
		self.raw_bytes = raw_bytes
	# @used-by :meth:`DocxExtractor.__parse_paragraph()`
	def __extract_paragraph_text(self, elem, rels: dict[str, str], state: dict) -> str:
		parts: list[str] = []
		field_buf: list[str] = []
		for child in elem:
			if f'{self.W}hyperlink' == child.tag:
				rid = child.attrib.get(f'{self.R}id', '')
				htext = ''.join((t.text for t in child.findall(f'.//{self.W}t') if t.text))
				if htext.strip():
					parts.append(self.__render_link(htext, rels.get(rid, '')))
			elif f'{self.W}r' == child.tag:
				self.__process_run(child, parts, field_buf, state)
		if state['in_field_result'] and field_buf:
			parts.append(self.__render_link(''.join(field_buf), state['active_field_url'] or ''))
		return re.sub('[ \\t]+', ' ', ''.join(parts)).strip()
	# @used-by :meth:`DocxExtractor.__process_run()`
	def __handle_fld_char(self, ftype: str, parts: list[str], field_buf: list[str], state: dict) -> None:
		if 'separate' == ftype:
			state['in_field_result'] = True
		elif ftype in ('begin', 'end'):
			if field_buf and ('end' == ftype or state['in_field_result']):
				parts.append(self.__render_link(''.join(field_buf), state['active_field_url'] or ''))
			state['active_field_url'] = None
			state['in_field_result'] = False
			field_buf.clear()
	# @used-by :meth:`DocxExtractor.extract()`
	def __load_numbering(self, zf: zipfile.ZipFile) -> dict[str, dict[str, str]]:
		r: dict[str, dict[str, str]] = {}
		if 'word/numbering.xml' in zf.namelist():
			num_root = ET.fromstring(zf.read('word/numbering.xml'))
			abstract_map = self.__read_abstract_nums(num_root)
			for num in num_root.findall(f'.//{self.W}num'):
				num_id = num.attrib.get(f'{self.W}numId')
				abs_ref = num.find(f'./{self.W}abstractNumId')
				if None is not num_id and None is not abs_ref:
					r[num_id] = abstract_map.get(abs_ref.attrib.get(f'{self.W}val'), {})
		return r
	# @used-by :meth:`DocxExtractor.extract()`
	def __load_relationships(self, zf: zipfile.ZipFile) -> dict[str, str]:
		r: dict[str, str] = {}
		if 'word/_rels/document.xml.rels' in zf.namelist():
			for rel in ET.fromstring(zf.read('word/_rels/document.xml.rels')):
				rid, target = (rel.attrib.get('Id'), rel.attrib.get('Target'))
				if rid and target:
					r[rid] = target
		return r
	# @used-by :meth:`DocxExtractor.extract()`
	@staticmethod
	def __normalize_heading_levels(items: list[dict]) -> None:
		heading_levels = [it['level'] for it in items if 'heading' == it['kind']]
		min_lvl = min(heading_levels) if heading_levels else 1
		if 1 < min_lvl:
			first_h_seen = False
			for it in items:
				if 'heading' != it['kind']:
					continue
				if not first_h_seen and items[0] is it and (1 < heading_levels.count(min_lvl)):
					it['level'] = 1
					first_h_seen = True
				else:
					it['level'] = max(1, it['level'] - (min_lvl - 2 if first_h_seen else min_lvl - 1))
	# @used-by :meth:`DocxExtractor.__parse_paragraph()`
	def __num_props(self, elem) -> tuple[str | None, int]:
		num_pr = elem.find(f'./{self.W}pPr/{self.W}numPr')
		num_id, ilvl = (None, 0)
		if None is not num_pr:
			nid_el = num_pr.find(f'./{self.W}numId')
			ilvl_el = num_pr.find(f'./{self.W}ilvl')
			num_id = nid_el.attrib.get(f'{self.W}val') if None is not nid_el else None
			if None is not ilvl_el:
				try:
					ilvl = int(ilvl_el.attrib.get(f'{self.W}val', '0'))
				except ValueError:
					ilvl = 0
		return (num_id, ilvl)
	# @used-by :meth:`DocxExtractor.extract()`
	def __parse_paragraph(self, elem, rels: dict[str, str], num_formats: dict[str, dict[str, str]], list_counters: dict[tuple[str, int], int], state: dict) -> dict | None:
		text = self.__extract_paragraph_text(elem, rels, state)
		if not text:
			r = None
		else:
			pstyle_el = elem.find(f'./{self.W}pPr/{self.W}pStyle')
			style = pstyle_el.attrib.get(f'{self.W}val', '') if None is not pstyle_el else ''
			num_id, ilvl = self.__num_props(elem)
			h_match = re.match('^Heading(\\d+)$', style, re.I)
			if 'title' == style.lower():
				r = {'kind': 'heading', 'level': 1, 'text': text}
			elif h_match:
				r = {'kind': 'heading', 'level': min(int(h_match.group(1)), 6), 'text': text}
			elif None is not num_id and '0' != num_id:
				r = self.__render_list_item(text, num_id, ilvl, num_formats, list_counters)
			else:
				r = {'kind': 'para', 'text': text}
		return r
	# @used-by :meth:`DocxExtractor.extract()`
	def __parse_table(self, elem) -> list[dict]:
		rows_data: list[list[str]] = []
		for row in elem.findall(f'./{self.W}tr'):
			cells_data = [' '.join((''.join((t.text for t in p.findall(f'.//{self.W}t') if t.text)).strip() for p in cell.findall(f'.//{self.W}p'))).strip() for cell in row.findall(f'./{self.W}tc')]
			if any(cells_data):
				rows_data.append(cells_data)
		if not rows_data:
			r: list[dict] = []
		else:
			headers = rows_data[0] if 1 < len(rows_data) else []
			data_rows = rows_data[1:] if 1 < len(rows_data) else rows_data
			r = [{'kind': 'list', 'text': line} for line in MarkdownTableSanitizer.format_table_bullet_rows(data_rows, headers)]
		return r
	# @used-by :meth:`DocxExtractor.__extract_paragraph_text()`
	def __process_run(self, child, parts: list[str], field_buf: list[str], state: dict) -> None:
		for sub in child:
			if f'{self.W}instrText' == sub.tag and sub.text:
				m = re.search('HYPERLINK\\s+"([^"]+)"', sub.text)
				if m:
					state['active_field_url'] = m.group(1)
			elif f'{self.W}t' == sub.tag and sub.text:
				(field_buf if state['in_field_result'] and state['active_field_url'] else parts).append(sub.text)
			elif f'{self.W}fldChar' == sub.tag:
				self.__handle_fld_char(sub.attrib.get(f'{self.W}fldCharType', ''), parts, field_buf, state)
	# @used-by :meth:`DocxExtractor.__load_numbering()`
	def __read_abstract_nums(self, num_root) -> dict[str, dict[str, str]]:
		r: dict[str, dict[str, str]] = {}
		for abs_num in num_root.findall(f'.//{self.W}abstractNum'):
			abs_id = abs_num.attrib.get(f'{self.W}abstractNumId')
			lvl_map: dict[str, str] = {}
			for lvl in abs_num.findall(f'./{self.W}lvl'):
				nf = lvl.find(f'./{self.W}numFmt')
				lvl_map[lvl.attrib.get(f'{self.W}ilvl', '0')] = nf.attrib.get(f'{self.W}val', 'bullet') if None is not nf else 'bullet'
			if None is not abs_id:
				r[abs_id] = lvl_map
		return r
	# @used-by :meth:`DocxExtractor.extract()`
	@staticmethod
	def __render_items(items: list[dict]) -> str:
		out_lines: list[str] = []
		for it in items:
			if 'heading' == it['kind']:
				out_lines.append(f"{'#' * it['level']} {it['text']}")
			elif 'list' == it['kind']:
				out_lines.append(it['text'])
			else:
				out_lines.extend(MarkdownTableSanitizer.split_sentences_one_per_line(it['text']))
		return MarkdownTableSanitizer.sanitize_kb_markdown('\n'.join(out_lines))
	# @used-by :meth:`DocxExtractor.__extract_paragraph_text()`
	# @used-by :meth:`DocxExtractor.__handle_fld_char()`
	@staticmethod
	def __render_link(text: str, url: str) -> str:
		t = text.strip()
		if not t:
			r = ''
		elif not url:
			r = text
		else:
			m = re.match('^(.*?\\s+-\\s+)(Watch\\s+Video.*)$', t, re.I)
			r = m.group(1) + markdown_link(m.group(2), url) if m else markdown_link(t, url)
		return r
	# @used-by :meth:`DocxExtractor.__parse_paragraph()`
	@staticmethod
	def __render_list_item(text: str, num_id: str, ilvl: int, num_formats: dict[str, dict[str, str]], list_counters: dict[tuple[str, int], int]) -> dict:
		fmt = num_formats.get(num_id, {}).get(str(ilvl), 'bullet')
		indent = '  ' * ilvl
		if fmt not in ('decimal', 'lowerLetter', 'upperLetter', 'lowerRoman', 'upperRoman'):
			r = {'kind': 'list', 'text': f'{indent}- {text}'}
		else:
			key = (num_id, ilvl)
			list_counters[key] = list_counters.get(key, 0) + 1
			r = {'kind': 'list', 'text': f'{indent}{list_counters[key]}. {text}'}
		return r
	# @used-by :func:`agent_tools.upwork_data.extract_docx_markdown()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.__extract_zip_doc()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_docx_pdf_xlsx_odt_and_loom_extractors()`
	# @used-by :meth:`test_upwork_data.UpworkDataExtractorTests.test_docx_extractor_tables_fields_numbering_and_heading_normalization()`
	def extract(self) -> str:
		with zipfile.ZipFile(io.BytesIO(self.raw_bytes)) as zf:
			rels, num_formats = (self.__load_relationships(zf), self.__load_numbering(zf))
			body = ET.fromstring(zf.read('word/document.xml')).find(f'./{self.W}body')
			if None is body:
				r = ''
			else:
				raw_items: list[dict] = []
				list_counters: dict[tuple[str, int], int] = {}
				state = {'active_field_url': None, 'in_field_result': False}
				for elem in body:
					if f'{self.W}tbl' == elem.tag:
						raw_items.extend(self.__parse_table(elem))
					elif f'{self.W}p' == elem.tag:
						item = self.__parse_paragraph(elem, rels, num_formats, list_counters, state)
						if None is not item:
							raw_items.append(item)
				self.__normalize_heading_levels(raw_items)
				r = self.__render_items(raw_items)
		return r
