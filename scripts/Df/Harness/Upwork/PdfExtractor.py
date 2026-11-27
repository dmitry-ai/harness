# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.links import markdown_link, readable_reference
from Df.Harness.Upwork.MarkdownTableSanitizer import MarkdownTableSanitizer
from Df.Harness.Upwork.PdfLigatureRepairer import PdfLigatureRepairer
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PdfExtractor:
	# @used-by :func:`agent_tools.upwork_data.extract_pdf_markdown()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.extract_markdown()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_docx_pdf_xlsx_odt_and_loom_extractors()`
	# @used-by :meth:`test_upwork_data.UpworkDataExtractorTests.test_pdf_extractor_xml_layout_and_raw_stream_ligature_fallback()`
	def __init__(self, raw_bytes: bytes, pdf_path=None, *, poppler_finder=None) -> None:
		self.pdf_path = pdf_path
		self.raw_bytes = raw_bytes
		self.repairs = PdfLigatureRepairer.discover_repairs(raw_bytes)
		self.__poppler_finder = poppler_finder
	# @used-by :meth:`PdfExtractor.__build_blocks()`
	def __append_para_or_continue(self, ln: dict, spans: list, full_line: str, blocks: list[dict]) -> None:
		if spans[0][1] and 1 < len(spans):
			label, tail = (self.__clean_txt(spans[0][2]), self.__clean_txt(' '.join((s[2] for s in spans[1:]))))
			line_text, starts_bold = (f'**{label}** {tail}'.strip(), True)
		else:
			line_text, starts_bold = (full_line, False)
		merged = False
		if blocks and (not starts_bold):
			prev = blocks[-1]
			same = prev['page'] == ln['page'] and ln['top'] - prev['top'] <= prev['height'] * 1.65 and (10 >= abs(ln['left'] - prev['body_left'])) and (prev['kind'] in ('para', 'list'))
			cross = prev['page'] + 1 == ln['page'] and 10 >= abs(ln['left'] - prev['body_left']) and (prev['kind'] in ('para', 'list')) and (not prev['text'].endswith(('.', '!', '?', ':')))
			if same or cross:
				prev['text'] = self.join_wrapped_lines(prev['text'], line_text)
				prev['page'], prev['top'] = (ln['page'], ln['top'])
				merged = True
		if not merged:
			blocks.append({'kind': 'para', 'text': line_text, 'page': ln['page'], 'top': ln['top'], 'left': ln['left'], 'body_left': ln['left'], 'height': ln['height']})
	# @used-by :meth:`PdfExtractor.__extract_from_xml()`
	def __build_blocks(self, visual_lines: list[dict]) -> list[dict]:
		r: list[dict] = []
		for ln in visual_lines:
			spans = sorted(ln['spans'], key=lambda x: x[0])
			first_txt = self.__clean_txt(spans[0][2])
			is_bullet = first_txt in ('\uf0b7', '•', '●', '○', '▪', '▫', '-')
			is_num = bool(re.match('^\\d+[.)]$', first_txt)) and 1 < len(spans)
			if is_bullet or is_num:
				r.append(self.__build_list_block(ln, spans, '-' if is_bullet else first_txt))
			else:
				all_bold = all((s[1] for s in spans if self.__clean_txt(s[2])))
				full_line = self.__clean_txt(' '.join((s[2] for s in spans)))
				if all_bold and 100 >= len(full_line):
					r.append({'kind': 'heading', 'text': full_line, 'page': ln['page'], 'top': ln['top'], 'left': ln['left'], 'body_left': ln['left'], 'height': ln['height']})
				else:
					self.__append_para_or_continue(ln, spans, full_line, r)
		return r
	# @used-by :meth:`PdfExtractor.__build_blocks()`
	def __build_list_block(self, ln: dict, spans: list, marker: str) -> dict:
		rest = [s for s in spans[1:] if self.__clean_txt(s[2])]
		body_left = rest[0][0] if rest else ln['left'] + 25
		if rest and rest[0][1] and (1 < len(rest)):
			text = f"**{self.__clean_txt(rest[0][2])}** {self.__clean_txt(' '.join((s[2] for s in rest[1:])))}".strip()
		else:
			text = self.__clean_txt(' '.join((s[2] for s in rest)))
		return {'kind': 'list', 'marker': marker, 'text': text, 'page': ln['page'], 'top': ln['top'], 'left': ln['left'], 'body_left': body_left, 'height': ln['height']}
	# @used-by :meth:`PdfExtractor.__append_para_or_continue()`
	# @used-by :meth:`PdfExtractor.__build_blocks()`
	# @used-by :meth:`PdfExtractor.__build_list_block()`
	# @used-by :meth:`PdfExtractor.__text_element_raw()`
	def __clean_txt(self, text: str) -> str:
		return re.sub('\\s+', ' ', PdfLigatureRepairer.normalize_ligatures(text, self.repairs)).strip()
	# @used-by :meth:`PdfExtractor.__extract_from_xml()`
	def __collect_visual_lines(self, root, bold_fonts: set[str]) -> list[dict]:
		r: list[dict] = []
		for page in root.findall('page'):
			page_num, page_lines = (int(page.attrib.get('number', 1)), [])
			for t in page.findall('text'):
				raw_txt = self.__text_element_raw(t)
				if not raw_txt.strip():
					continue
				top, left, height = (int(float(t.attrib.get('top', 0))), int(float(t.attrib.get('left', 0))), int(float(t.attrib.get('height', 20))))
				is_bold = None is not t.find('.//b') or None is not t.find('.//B') or t.attrib.get('font', '') in bold_fonts
				if page_lines and 4 >= abs(page_lines[-1]['top'] - top):
					page_lines[-1]['spans'].append((left, is_bold, raw_txt))
				else:
					page_lines.append({'page': page_num, 'top': top, 'left': left, 'height': max(height, 12), 'spans': [(left, is_bold, raw_txt)]})
			r.extend(page_lines)
		return r
	# @used-by :meth:`PdfExtractor.__extract_from_xml()`
	@staticmethod
	def __detect_bold_fonts(root) -> set[str]:
		r = {fs.attrib.get('id', '') for fs in root.findall('.//fontspec') if 'bold' in (fs.attrib.get('family') or '').lower()}
		font_chars: dict[str, int] = {}
		texts = [(t.attrib.get('font', ''), ''.join(t.itertext()).strip()) for page in root.findall('page') for t in page.findall('text')]
		for fid, txt in texts:
			if 1 < len(txt):
				font_chars[fid] = font_chars.get(fid, 0) + len(txt)
		dominant = max(font_chars, key=font_chars.get) if font_chars else None
		for fid, txt in texts:
			if fid != dominant and (txt.endswith(':') and 1 <= len(txt.split()) <= 5 or re.match('^(?:Phase|Step|Part|Section)\\s+\\d+\\b', txt)):
				r.add(fid)
		return r
	# @used-by :meth:`PdfExtractor.extract()`
	def __extract_from_pdftotext(self) -> str | None:
		stdout = self._run_poppler('pdftotext', lambda tool, target: [tool, target, '-'])
		if not (stdout and stdout.strip()):
			r = None
		else:
			cleaned = PdfLigatureRepairer.normalize_ligatures(stdout.replace('\x0c', '\n\n'), self.repairs)
			r = MarkdownTableSanitizer.sanitize_kb_markdown(MarkdownTableSanitizer.structure_job_description(cleaned))
		return r
	# @used-by :meth:`PdfExtractor.extract()`
	def __extract_from_raw_streams(self) -> str:
		cid_to_uni, streams, unmapped = PdfLigatureRepairer.parse_streams(self.raw_bytes)
		for cid, lig_char in unmapped.items():
			cid_to_uni.setdefault(cid, lig_char.translate(PdfLigatureRepairer.LIGATURE_MAP))
		chunks: list[str] = []
		for dec in streams:
			for hex_part, lit_part in re.findall('\\[(.*?)\\]\\s*TJ|\\((.*?)\\)\\s*Tj', dec, re.S):
				if lit_part:
					chunks.append(lit_part)
				elif hex_part:
					chunks.append(''.join((cid_to_uni.get(int(h[i:i + 4], 16), ' ') for h in re.findall('<([0-9A-Fa-f]+)>', hex_part) for i in range(0, len(h) - 3, 4))))
		joined = PdfLigatureRepairer.normalize_ligatures(' '.join(chunks), self.repairs)
		return MarkdownTableSanitizer.sanitize_kb_markdown(MarkdownTableSanitizer.structure_job_description(joined))
	# @used-by :meth:`PdfExtractor.extract()`
	def __extract_from_xml(self, xml_stdout: str) -> str | None:
		try:
			root = ET.fromstring(xml_stdout)
			r = self.__render_blocks(self.__build_blocks(self.__collect_visual_lines(root, self.__detect_bold_fonts(root))))
		except Exception:
			r = None
		return r
	# @used-by :meth:`PdfExtractor.__extract_from_xml()`
	@staticmethod
	def __render_blocks(blocks: list[dict]) -> str | None:
		out_lines: list[str] = []
		for b in blocks:
			if 'list' == b['kind']:
				out_lines.append(f"{b['marker']} {b['text']}")
			elif 'heading' != b['kind']:
				out_lines.extend(MarkdownTableSanitizer.split_sentences_one_per_line(b['text']))
			else:
				htext = b['text'][:-1].strip() if b['text'].endswith(':') else b['text']
				level = '##' if re.match('^(?:Phase|Step|Part)\\s+\\d+\\b', htext, re.I) else '#'
				if out_lines and '' != out_lines[-1]:
					out_lines.append('')
				out_lines.append(f'{level} {htext}')
		return MarkdownTableSanitizer.sanitize_kb_markdown('\n'.join(out_lines)) if out_lines else None
	# @used-by :meth:`PdfExtractor.__collect_visual_lines()`
	def __text_element_raw(self, t) -> str:
		parts: list[str] = [t.text] if t.text else []
		for child in t:
			ctext = ''.join(child.itertext())
			if 'a' == child.tag.lower() and child.attrib.get('href'):
				href, label = (child.attrib['href'].strip(), self.__clean_txt(ctext))
				parts.append(markdown_link(label, href) if label else readable_reference(href))
			else:
				parts.append(ctext)
			if child.tail:
				parts.append(child.tail)
		return ''.join(parts)
	# @used-by :meth:`PdfExtractor.__extract_from_pdftotext()`
	# @used-by :meth:`PdfExtractor.extract()`
	def _run_poppler(self, tool_name: str, args_builder) -> str | None:
		finder = self.find_poppler_tool if None is self.__poppler_finder else self.__poppler_finder
		tool, r, tmp_path = (finder(tool_name), None, None)
		if tool:
			try:
				if self.pdf_path and Path(self.pdf_path).is_file():
					target_str = str(self.pdf_path)
				else:
					with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tf:
						tf.write(self.raw_bytes)
						tmp_path = Path(tf.name)
					target_str = str(tmp_path)
				res = subprocess.run(args_builder(tool, target_str), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
				r = res.stdout if 0 == res.returncode else None
			except Exception:
				r = None
			finally:
				if tmp_path and tmp_path.exists():
					tmp_path.unlink(missing_ok=True)
		return r
	# @used-by :func:`agent_tools.upwork_data.extract_pdf_markdown()`
	# @used-by :meth:`Df.Harness.Upwork.AttachmentExtractor.AttachmentExtractor.extract_markdown()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_docx_pdf_xlsx_odt_and_loom_extractors()`
	# @used-by :meth:`test_upwork_data.UpworkDataExtractorTests.test_pdf_extractor_xml_layout_and_raw_stream_ligature_fallback()`
	def extract(self) -> str:
		r = None
		xml_stdout = self._run_poppler('pdftohtml', lambda tool, target: [tool, '-xml', '-stdout', target])
		if xml_stdout and '<pdf2xml' in xml_stdout:
			r = self.__extract_from_xml(xml_stdout)
		if None is r:
			r = self.__extract_from_pdftotext()
		if None is r:
			r = self.__extract_from_raw_streams()
		return r
	# @used-by :func:`agent_tools.upwork_data._find_poppler_tool()`
	# @used-by :meth:`PdfExtractor._run_poppler()`
	@staticmethod
	def find_poppler_tool(name: str) -> str | None:
		from agent_tools.path_registry import tool_list
		r = shutil.which(name)
		if not r:
			for folder in tool_list('poppler_bin_dirs'):
				cand = Path(folder) / (name if name.endswith('.exe') else f'{name}.exe')
				if cand.is_file():
					r = str(cand)
					break
		return r
	# @used-by :func:`agent_tools.upwork_data._join_wrapped_lines()`
	# @used-by :meth:`PdfExtractor.__append_para_or_continue()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_docx_pdf_xlsx_odt_and_loom_extractors()`
	@staticmethod
	def join_wrapped_lines(prev: str, nxt: str) -> str:
		return prev + nxt if prev.endswith('-') and nxt and nxt[0].islower() else (prev + ' ' + nxt).strip()
