# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PdfMarkdownExtractor and DocxMarkdownExtractor classes with shared table/file pipeline in upwork_data.py":
# https://github.com/dmitry-ai/harness/issues/65
# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
import csv
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile
import zlib
from .links import markdown_link, readable_reference
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff', '.tif', '.avif', '.heic'}
LIGATURE_MAP = str.maketrans({'\ufb00': 'ff', '\ufb01': 'fi', '\ufb02': 'fl', '\ufb03': 'ffi', '\ufb04': 'ffl', '\ufb05': 'st', '\ufb06': 'st'})
TEXT_DOC_EXTENSIONS = {'.pdf', '.docx', '.doc', '.rtf', '.odt', '.txt', '.md', '.markdown', '.rst', '.log', '.ini', '.cfg', '.conf', '.html', '.htm', '.xhtml', '.xml', '.svg', '.json', '.yaml', '.yml', '.toml', '.csv', '.tsv', '.xlsx', '.xls', '.xlsm', '.ods', '.js', '.ts', '.jsx', '.tsx', '.py', '.php', '.rb', '.java', '.cs', '.go', '.rs', '.c', '.cpp', '.h', '.css', '.scss', '.less', '.liquid', '.sql', '.sh', '.ps1', '.bat', '.har'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v', '.wmv', '.flv', '.mpeg', '.mpg'}
_SENTENCE_SPLIT_RE = re.compile('(?<!\\be\\.g)(?<!\\bi\\.e)(?<!\\bvs)(?<!\\betc)(?<!\\bMr)(?<!\\bDr)(?<!\\bSt)(?<!\\bNB)(?<=[.!?])\\s+(?=[A-Z\\u0410-\\u042f\\u0401"«(])')
_VIDEO_URL_RE = re.compile('https?://(?:www\\.)?(?:loom\\.com/(?:share|embed)/[A-Za-z0-9_-]+|youtube\\.com/(?:watch\\?[^\\s)"\\\'>]+|embed/[A-Za-z0-9_-]+|shorts/[A-Za-z0-9_-]+)|youtu\\.be/[A-Za-z0-9_-]+|vimeo\\.com/\\d+|player\\.vimeo\\.com/video/\\d+|[^\\s)"\\\'>]+\\.(?:mp4|mov|webm|m4v)(?:\\?[^\\s)"\\\'>]*)?)', re.I)
class DocxMarkdownExtractor:
	R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
	W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
	def __init__(self, raw_bytes: bytes):
		self.raw_bytes = raw_bytes
	def _extract_paragraph_text(self, elem, rels: dict[str, str], state: dict) -> str:
		parts: list[str] = []
		field_buf: list[str] = []
		for child in elem:
			if f'{self.W}hyperlink' == child.tag:
				rid = child.attrib.get(f'{self.R}id', '')
				htext = ''.join((t.text for t in child.findall(f'.//{self.W}t') if t.text))
				if htext.strip():
					parts.append(self._render_link(htext, rels.get(rid, '')))
			elif f'{self.W}r' == child.tag:
				for sub in child:
					if f'{self.W}instrText' == sub.tag and sub.text:
						m = re.search('HYPERLINK\\s+"([^"]+)"', sub.text)
						if m:
							state['active_field_url'] = m.group(1)
					elif f'{self.W}t' == sub.tag and sub.text:
						if state['in_field_result'] and state['active_field_url']:
							field_buf.append(sub.text)
						else:
							parts.append(sub.text)
					elif f'{self.W}fldChar' == sub.tag:
						ftype = sub.attrib.get(f'{self.W}fldCharType', '')
						if 'separate' == ftype:
							state['in_field_result'] = True
						elif 'begin' == ftype:
							if state['in_field_result'] and field_buf:
								parts.append(self._render_link(''.join(field_buf), state['active_field_url'] or ''))
							state['active_field_url'] = None
							state['in_field_result'] = False
							field_buf = []
						elif 'end' == ftype:
							if field_buf:
								parts.append(self._render_link(''.join(field_buf), state['active_field_url'] or ''))
							state['active_field_url'] = None
							state['in_field_result'] = False
							field_buf = []
		if state['in_field_result'] and field_buf:
			parts.append(self._render_link(''.join(field_buf), state['active_field_url'] or ''))
		return re.sub('[ \\t]+', ' ', ''.join(parts)).strip()
	def _load_numbering(self, zf: zipfile.ZipFile) -> dict[str, dict[str, str]]:
		r: dict[str, dict[str, str]] = {}
		if 'word/numbering.xml' in zf.namelist():
			num_root = ET.fromstring(zf.read('word/numbering.xml'))
			abstract_map: dict[str, dict[str, str]] = {}
			for abs_num in num_root.findall(f'.//{self.W}abstractNum'):
				abs_id = abs_num.attrib.get(f'{self.W}abstractNumId')
				lvl_map: dict[str, str] = {}
				for lvl in abs_num.findall(f'./{self.W}lvl'):
					ilvl = lvl.attrib.get(f'{self.W}ilvl', '0')
					nf = lvl.find(f'./{self.W}numFmt')
					lvl_map[ilvl] = nf.attrib.get(f'{self.W}val', 'bullet') if None is not nf else 'bullet'
				if None is not abs_id:
					abstract_map[abs_id] = lvl_map
			for num in num_root.findall(f'.//{self.W}num'):
				num_id = num.attrib.get(f'{self.W}numId')
				abs_ref = num.find(f'./{self.W}abstractNumId')
				if None is not num_id and None is not abs_ref:
					r[num_id] = abstract_map.get(abs_ref.attrib.get(f'{self.W}val'), {})
		return r
	def _load_relationships(self, zf: zipfile.ZipFile) -> dict[str, str]:
		r: dict[str, str] = {}
		if 'word/_rels/document.xml.rels' in zf.namelist():
			rel_root = ET.fromstring(zf.read('word/_rels/document.xml.rels'))
			for rel in rel_root:
				rid = rel.attrib.get('Id')
				target = rel.attrib.get('Target')
				if rid and target:
					r[rid] = target
		return r
	def _normalize_heading_levels(self, items: list[dict]) -> None:
		heading_levels = [it['level'] for it in items if 'heading' == it['kind']]
		if heading_levels:
			min_lvl = min(heading_levels)
			if 1 < min_lvl:
				first_h_seen = False
				for it in items:
					if 'heading' == it['kind']:
						if not (not first_h_seen and items[0] is it and (1 < heading_levels.count(min_lvl))):
							it['level'] = max(1, it['level'] - (min_lvl - 2 if first_h_seen else min_lvl - 1))
						else:
							it['level'] = 1
							first_h_seen = True
	def _parse_paragraph(self, elem, rels: dict[str, str], num_formats: dict[str, dict[str, str]], list_counters: dict[tuple[str, int], int], state: dict) -> dict | None:
		text = self._extract_paragraph_text(elem, rels, state)
		if not text:
			r = None
		else:
			pstyle_el = elem.find(f'./{self.W}pPr/{self.W}pStyle')
			style = pstyle_el.attrib.get(f'{self.W}val', '') if None is not pstyle_el else ''
			num_pr = elem.find(f'./{self.W}pPr/{self.W}numPr')
			num_id = None
			ilvl = 0
			if None is not num_pr:
				nid_el = num_pr.find(f'./{self.W}numId')
				ilvl_el = num_pr.find(f'./{self.W}ilvl')
				if None is not nid_el:
					num_id = nid_el.attrib.get(f'{self.W}val')
				if None is not ilvl_el:
					try:
						ilvl = int(ilvl_el.attrib.get(f'{self.W}val', '0'))
					except ValueError:
						ilvl = 0
			h_match = re.match('^Heading(\\d+)$', style, re.I)
			if 'title' == style.lower():
				r = {'kind': 'heading', 'level': 1, 'text': text}
			elif h_match:
				r = {'kind': 'heading', 'level': min(int(h_match.group(1)), 6), 'text': text}
			elif not (None is not num_id and '0' != num_id):
				r = {'kind': 'para', 'text': text}
			else:
				fmt = num_formats.get(num_id, {}).get(str(ilvl), 'bullet')
				indent = '  ' * ilvl
				if fmt not in ('decimal', 'lowerLetter', 'upperLetter', 'lowerRoman', 'upperRoman'):
					r = {'kind': 'list', 'text': f'{indent}- {text}'}
				else:
					key = (num_id, ilvl)
					list_counters[key] = list_counters.get(key, 0) + 1
					r = {'kind': 'list', 'text': f'{indent}{list_counters[key]}. {text}'}
		return r
	def _parse_table(self, elem) -> list[dict]:
		rows_data: list[list[str]] = []
		for row in elem.findall(f'./{self.W}tr'):
			cells_data: list[str] = []
			for cell in row.findall(f'./{self.W}tc'):
				cell_txt = ' '.join((''.join((t.text for t in p.findall(f'.//{self.W}t') if t.text)).strip() for p in cell.findall(f'.//{self.W}p'))).strip()
				cells_data.append(cell_txt)
			if any(cells_data):
				rows_data.append(cells_data)
		if not rows_data:
			r = []
		else:
			headers = rows_data[0] if 1 < len(rows_data) else []
			data_rows = rows_data[1:] if 1 < len(rows_data) else rows_data
			r = [{'kind': 'list', 'text': line} for line in format_table_bullet_rows(data_rows, headers)]
		return r
	def _render_items(self, items: list[dict]) -> str:
		out_lines: list[str] = []
		for it in items:
			if 'heading' == it['kind']:
				out_lines.append(f"{'#' * it['level']} {it['text']}")
			elif 'list' == it['kind']:
				out_lines.append(it['text'])
			else:
				for sent in split_sentences_one_per_line(it['text']):
					out_lines.append(sent)
		return sanitize_kb_markdown('\n'.join(out_lines))
	def _render_link(self, text: str, url: str) -> str:
		t = text.strip()
		if not t:
			r = ''
		elif not url:
			r = text
		else:
			m = re.match('^(.*?\\s+-\\s+)(Watch\\s+Video.*)$', t, re.I)
			if not m:
				r = markdown_link(t, url)
			else:
				r = m.group(1) + markdown_link(m.group(2), url)
		return r
	def extract(self) -> str:
		with zipfile.ZipFile(io.BytesIO(self.raw_bytes)) as zf:
			rels = self._load_relationships(zf)
			num_formats = self._load_numbering(zf)
			doc_root = ET.fromstring(zf.read('word/document.xml'))
			body = doc_root.find(f'./{self.W}body')
			if None is body:
				r = ''
			else:
				raw_items: list[dict] = []
				list_counters: dict[tuple[str, int], int] = {}
				state = {'active_field_url': None, 'in_field_result': False}
				for elem in body:
					if f'{self.W}tbl' == elem.tag:
						raw_items.extend(self._parse_table(elem))
					elif f'{self.W}p' == elem.tag:
						item = self._parse_paragraph(elem, rels, num_formats, list_counters, state)
						if None is not item:
							raw_items.append(item)
				self._normalize_heading_levels(raw_items)
				r = self._render_items(raw_items)
		return r
class PdfMarkdownExtractor:
	def __init__(self, raw_bytes: bytes, pdf_path=None):
		self.pdf_path = pdf_path
		self.raw_bytes = raw_bytes
		self.repairs = discover_pdf_ligature_repairs(raw_bytes)
	def _build_blocks(self, visual_lines: list[dict]) -> list[dict]:
		r: list[dict] = []
		for ln in visual_lines:
			spans = sorted(ln['spans'], key=lambda x: x[0])
			first_txt = self._clean_txt(spans[0][2])
			is_bullet = first_txt in ('\uf0b7', '•', '●', '○', '▪', '▫', '-')
			is_num = bool(re.match('^\\d+[.)]$', first_txt)) and 1 < len(spans)
			if is_bullet or is_num:
				marker = '-' if is_bullet else first_txt
				rest_spans = [s for s in spans[1:] if self._clean_txt(s[2])]
				body_left = rest_spans[0][0] if rest_spans else ln['left'] + 25
				if not (rest_spans and rest_spans[0][1] and (1 < len(rest_spans))):
					text = self._clean_txt(' '.join((s[2] for s in rest_spans)))
				else:
					label = self._clean_txt(rest_spans[0][2])
					tail = self._clean_txt(' '.join((s[2] for s in rest_spans[1:])))
					text = f'**{label}** {tail}'.strip()
				r.append({'kind': 'list', 'marker': marker, 'text': text, 'page': ln['page'], 'top': ln['top'], 'left': ln['left'], 'body_left': body_left, 'height': ln['height']})
				continue
			all_bold = all((s[1] for s in spans if self._clean_txt(s[2])))
			full_line = self._clean_txt(' '.join((s[2] for s in spans)))
			if all_bold and 100 >= len(full_line):
				r.append({'kind': 'heading', 'text': full_line, 'page': ln['page'], 'top': ln['top'], 'left': ln['left'], 'body_left': ln['left'], 'height': ln['height']})
				continue
			if not (spans[0][1] and 1 < len(spans)):
				line_text = full_line
				starts_bold = False
			else:
				label = self._clean_txt(spans[0][2])
				tail = self._clean_txt(' '.join((s[2] for s in spans[1:])))
				line_text = f'**{label}** {tail}'.strip()
				starts_bold = True
			if r and (not starts_bold):
				prev = r[-1]
				same_page_cont = prev['page'] == ln['page'] and ln['top'] - prev['top'] <= prev['height'] * 1.65 and (10 >= abs(ln['left'] - prev['body_left'])) and (prev['kind'] in ('para', 'list'))
				cross_page_cont = prev['page'] + 1 == ln['page'] and 10 >= abs(ln['left'] - prev['body_left']) and (prev['kind'] in ('para', 'list')) and (not prev['text'].endswith(('.', '!', '?', ':')))
				if same_page_cont or cross_page_cont:
					prev['text'] = _join_wrapped_lines(prev['text'], line_text)
					prev['page'] = ln['page']
					prev['top'] = ln['top']
					continue
			r.append({'kind': 'para', 'text': line_text, 'page': ln['page'], 'top': ln['top'], 'left': ln['left'], 'body_left': ln['left'], 'height': ln['height']})
		return r
	def _clean_txt(self, text: str) -> str:
		return re.sub('\\s+', ' ', normalize_pdf_ligatures(text, self.repairs)).strip()
	def _collect_visual_lines(self, root, bold_fonts: set[str]) -> list[dict]:
		r: list[dict] = []
		for page in root.findall('page'):
			page_num = int(page.attrib.get('number', 1))
			page_lines: list[dict] = []
			for t in page.findall('text'):
				top = int(float(t.attrib.get('top', 0)))
				left = int(float(t.attrib.get('left', 0)))
				height = int(float(t.attrib.get('height', 20)))
				font = t.attrib.get('font', '')
				has_b = None is not t.find('.//b') or None is not t.find('.//B')
				parts: list[str] = []
				if t.text:
					parts.append(t.text)
				for child in t:
					ctext = ''.join(child.itertext())
					if not ('a' == child.tag.lower() and child.attrib.get('href')):
						parts.append(ctext)
					else:
						href = child.attrib['href'].strip()
						label = self._clean_txt(ctext)
						parts.append(markdown_link(label, href) if label else readable_reference(href))
					if child.tail:
						parts.append(child.tail)
				raw_txt = ''.join(parts)
				if not raw_txt.strip():
					continue
				is_bold = has_b or font in bold_fonts
				if page_lines and 4 >= abs(page_lines[-1]['top'] - top):
					page_lines[-1]['spans'].append((left, is_bold, raw_txt))
				else:
					page_lines.append({'page': page_num, 'top': top, 'left': left, 'height': max(height, 12), 'spans': [(left, is_bold, raw_txt)]})
			r.extend(page_lines)
		return r
	def _detect_bold_fonts(self, root) -> set[str]:
		r: set[str] = set()
		font_chars: dict[str, int] = {}
		for fs in root.findall('.//fontspec'):
			fid = fs.attrib.get('id', '')
			if 'bold' in (fs.attrib.get('family') or '').lower():
				r.add(fid)
		for page in root.findall('page'):
			for t in page.findall('text'):
				fid = t.attrib.get('font', '')
				txt = ''.join(t.itertext()).strip()
				if 1 < len(txt):
					font_chars[fid] = font_chars.get(fid, 0) + len(txt)
		dominant_body_font = max(font_chars, key=font_chars.get) if font_chars else None
		for page in root.findall('page'):
			for t in page.findall('text'):
				fid = t.attrib.get('font', '')
				if fid == dominant_body_font:
					continue
				txt = ''.join(t.itertext()).strip()
				if txt.endswith(':') and 1 <= len(txt.split()) <= 5 or re.match('^(?:Phase|Step|Part|Section)\\s+\\d+\\b', txt):
					r.add(fid)
		return r
	def _extract_from_pdftotext(self) -> str | None:
		stdout = self._run_poppler('pdftotext', lambda tool, target: [tool, target, '-'])
		if not (stdout and stdout.strip()):
			r = None
		else:
			cleaned = normalize_pdf_ligatures(stdout.replace('\x0c', '\n\n'), self.repairs)
			r = sanitize_kb_markdown(structure_job_description(cleaned))
		return r
	def _extract_from_raw_streams(self) -> str:
		cid_to_uni, streams, unmapped = _parse_pdf_streams(self.raw_bytes)
		for cid, lig_char in unmapped.items():
			cid_to_uni.setdefault(cid, lig_char.translate(LIGATURE_MAP))
		extracted_chunks: list[str] = []
		for dec in streams:
			for tj in re.findall('\\[(.*?)\\]\\s*TJ|\\((.*?)\\)\\s*Tj', dec, re.S):
				hex_part, lit_part = tj
				if lit_part:
					extracted_chunks.append(lit_part)
				elif hex_part:
					chars = [cid_to_uni.get(int(h[i:i + 4], 16), ' ') for h in re.findall('<([0-9A-Fa-f]+)>', hex_part) for i in range(0, len(h), 4) if i + 4 <= len(h)]
					extracted_chunks.append(''.join(chars))
		joined = normalize_pdf_ligatures(' '.join(extracted_chunks), self.repairs)
		return sanitize_kb_markdown(structure_job_description(joined))
	def _extract_from_xml(self, xml_stdout: str) -> str | None:
		try:
			root = ET.fromstring(xml_stdout)
			bold_fonts = self._detect_bold_fonts(root)
			visual_lines = self._collect_visual_lines(root, bold_fonts)
			r = self._render_blocks(self._build_blocks(visual_lines))
		except Exception:
			r = None
		return r
	def _render_blocks(self, blocks: list[dict]) -> str | None:
		out_lines: list[str] = []
		for b in blocks:
			if 'list' == b['kind']:
				out_lines.append(f"{b['marker']} {b['text']}")
			elif 'heading' != b['kind']:
				for sent in split_sentences_one_per_line(b['text']):
					out_lines.append(sent)
			else:
				htext = b['text'][:-1].strip() if b['text'].endswith(':') else b['text']
				level = '##' if re.match('^(?:Phase|Step|Part)\\s+\\d+\\b', htext, re.I) else '#'
				if out_lines and '' != out_lines[-1]:
					out_lines.append('')
				out_lines.append(f'{level} {htext}')
		return sanitize_kb_markdown('\n'.join(out_lines)) if out_lines else None
	def _run_poppler(self, tool_name: str, args_builder) -> str | None:
		tool = _find_poppler_tool(tool_name)
		r = None
		if tool:
			tmp_path = None
			try:
				if self.pdf_path and Path(self.pdf_path).is_file():
					target_str = str(self.pdf_path)
				else:
					with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tf:
						tf.write(self.raw_bytes)
						tmp_path = Path(tf.name)
					target_str = str(tmp_path)
				res = subprocess.run(args_builder(tool, target_str), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
				if 0 == res.returncode:
					r = res.stdout
			except Exception:
				r = None
			finally:
				if tmp_path and tmp_path.exists():
					try:
						tmp_path.unlink()
					except OSError:
						pass
		return r
	def extract(self) -> str:
		r = None
		xml_stdout = self._run_poppler('pdftohtml', lambda tool, target: [tool, '-xml', '-stdout', target])
		if xml_stdout and '<pdf2xml' in xml_stdout:
			r = self._extract_from_xml(xml_stdout)
		if None is r:
			r = self._extract_from_pdftotext()
		if None is r:
			r = self._extract_from_raw_streams()
		return r
def _extract_xlsx_markdown(raw_bytes: bytes) -> str:
	with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
		shared: list[str] = []
		if 'xl/sharedStrings.xml' in zf.namelist():
			sroot = ET.fromstring(zf.read('xl/sharedStrings.xml'))
			shared = [''.join(si.itertext()) for si in sroot if si.tag.endswith('}si')]
		lines: list[str] = []
		for name in sorted((n for n in zf.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'))):
			wroot = ET.fromstring(zf.read(name))
			for row in wroot.iter():
				if not row.tag.endswith('}row'):
					continue
				vals: list[str] = []
				for c in row:
					if not c.tag.endswith('}c'):
						continue
					t_attr = c.attrib.get('t', '')
					v_el = next((ch for ch in c if ch.tag.endswith('}v') or ch.tag.endswith('}is')), None)
					if None is v_el:
						continue
					raw_v = ''.join(v_el.itertext()).strip()
					if 's' == t_attr and raw_v.isdigit() and (int(raw_v) < len(shared)):
						vals.append(shared[int(raw_v)].strip())
					elif raw_v:
						vals.append(raw_v)
				if vals:
					lines.append('- ' + '; '.join(vals))
		r = sanitize_kb_markdown('\n'.join(lines))
	return r
def _parse_pdf_streams(pdf_bytes: bytes, *, text_ops_only: bool=False) -> tuple[dict[int, str], list[str], dict[int, str]]:
	cid_to_uni: dict[int, str] = {}
	content_streams: list[str] = []
	for m in re.finditer(b'stream\\s*(.*?)\\s*endstream', pdf_bytes, re.S):
		raw = m.group(1)
		try:
			dec = zlib.decompress(raw).decode('latin1', errors='ignore')
		except Exception:
			dec = raw.decode('latin1', errors='ignore')
		if 'begincmap' in dec:
			for cid_hex, uni_hex in re.findall('<([0-9A-Fa-f]{4})>\\s*<([0-9A-Fa-f]{4,8})>', dec):
				chars = ''.join((chr(int(uni_hex[i:i + 4], 16)) for i in range(0, len(uni_hex), 4)))
				cid_to_uni[int(cid_hex, 16)] = chars
		elif 'BT' in dec and ((not text_ops_only) or 'TJ' in dec or 'Tj' in dec):
			content_streams.append(dec)
	unmapped_ligatures: dict[int, str] = {}
	for cid, ch in list(cid_to_uni.items()):
		if '\ufb01' == ch and '\ufb02' == cid_to_uni.get(cid + 1):
			for offset, lig_char in ((-2, '\ufb00'), (-1, '\ufb03'), (2, '\ufb04')):
				if cid + offset not in cid_to_uni:
					unmapped_ligatures[cid + offset] = lig_char
	return (cid_to_uni, content_streams, unmapped_ligatures)
def normalize_job_id(url_or_id: str) -> str:
	match = re.search('(~0[12][0-9a-zA-Z]+)', url_or_id.strip())
	if not match:
		raise ValueError(f'Cannot extract Upwork job ID (~02...) from: {url_or_id}')
	return match.group(1)
def canonical_job_url(url_or_id: str) -> str:
	return f'https://upwork.com/jobs/{normalize_job_id(url_or_id)}'
def resolve_nuxt_devalue(arr: list, idx: int=0, seen: set[int] | None=None):
	if None is seen:
		seen = set()
	if not isinstance(idx, int) or 0 > idx or idx >= len(arr) or (idx in seen):
		r = arr[idx] if isinstance(idx, int) and 0 <= idx < len(arr) else idx
	else:
		seen = seen | {idx}
		val = arr[idx]
		if not isinstance(val, (list, dict)):
			r = val
		elif isinstance(val, dict):
			r = {k: resolve_nuxt_devalue(arr, v, seen) if isinstance(v, int) else v for k, v in val.items()}
		elif 2 == len(val) and isinstance(val[0], str) and (val[0] in ('Reactive', 'ShallowReactive', 'Ref', 'EmptyRef', 'Set', 'ShallowRef')):
			r = resolve_nuxt_devalue(arr, val[1], seen)
		else:
			r = [resolve_nuxt_devalue(arr, x, seen) if isinstance(x, int) else x for x in val]
	return r
def extract_client_names(work_history: list[dict]) -> list[dict]:
	patterns = ['\\bworking with ([A-Z][a-z]{2,15})\\b', '\\bThank you,? ([A-Z][a-z]{2,15})\\b', '\\b([A-Z][a-z]{2,15}) is (?:a |an )?(?:very |truly |super )?(?:nice|great|wonderful|excellent|good|supportive|easy|clear|amazing|awesome|fantastic|pleasure)', '\\b([A-Z][a-z]{2,15}) was (?:a )?(?:great|wonderful|excellent|very|easy|clear|supportive)', '\\b([A-Z][a-z]{2,15}) has been (?:a )?(?:great|wonderful|excellent|very|supportive)', '\\b([A-Z][a-z]{2,15}) is the best\\b']
	stopwords = {'This', 'That', 'There', 'Client', 'Working', 'Thank', 'Thanks', 'Everything', 'Communication', 'Overall', 'Project', 'Team', 'He', 'She', 'They'}
	found: dict[str, list[dict]] = {}
	for idx, item in enumerate(work_history, start=1):
		comment = ((item.get('feedbackToClient') or {}).get('comment') or '').strip()
		if not comment:
			continue
		seen_in_item: set[str] = set()
		for pat in patterns:
			for match in re.finditer(pat, comment):
				name = match.group(1)
				if name in stopwords or name in seen_in_item:
					continue
				seen_in_item.add(name)
				found.setdefault(name, []).append({'project_index': idx, 'project_title': (item.get('jobInfo') or {}).get('title') or f'Project {idx}', 'quote': comment})
	return [{'name': k, 'mentions': v} for k, v in sorted(found.items(), key=lambda x: -len(x[1]))]
def extract_candidate_domains(texts: list[str]) -> list[str]:
	pattern = '(?<![\\w.-])((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z]{2,63})(?![\\w.-])'
	domains = (m[4:] if m.startswith('www.') else m for text in texts for m in re.findall(pattern, text.lower()))
	return list(dict.fromkeys(domains))
def markdown_fence(text: str, marker: str='~') -> str:
	return marker * max(3, 1 + max((len(m[0]) for m in re.finditer(re.escape(marker) + '+', text)), default=0))
def split_sentences_one_per_line(text: str) -> list[str]:
	parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(text.strip()) if p.strip()]
	return parts or ([text.strip()] if text.strip() else [])
def structure_job_description(description: str, questions: list[str] | None=None) -> str:
	raw = (description or '').replace('\r\n', '\n').replace('\r', '\n').strip()
	lines = [line.strip() for line in raw.split('\n')]
	out_lines: list[str] = []
	for idx, line in enumerate(lines):
		if not line:
			if out_lines and '' != out_lines[-1]:
				out_lines.append('')
			continue
		bullet_match = re.match('^(?:[•*]|\\-(?=[A-Za-z\\u0410-\\u042f\\u0401\\u0430-\\u044f\\u04510-9"\\\'`])|\\-\\s+)\\s*(.+)$', line)
		if bullet_match:
			sentences = split_sentences_one_per_line(bullet_match.group(1).strip())
			if sentences:
				out_lines.append(f'- {sentences[0]}')
				for extra in sentences[1:]:
					out_lines.append(extra)
			continue
		prev_empty = 0 == idx or not lines[idx - 1]
		words = line.split()
		is_heading = prev_empty and 1 <= len(words) <= 8 and (70 >= len(line)) and line[0].isupper() and (not line.startswith(('http://', 'https://', '#', '-'))) and (not re.match('^\\d+[.)]\\s', line)) and (line.endswith(':') or (not line.endswith(('.', '!', '?', ';', ',')) and idx + 1 < len(lines)))
		if is_heading and words[0].lower() in ('we', "we're", 'i', 'the', 'this', 'there', 'please', 'see', 'as', 'and', 'so', 'if', 'in', 'for', 'most', 'all') and (not line.endswith(':')):
			is_heading = False
		if is_heading:
			if out_lines and '' != out_lines[-1]:
				out_lines.append('')
			heading_text = line[:-1].strip() if line.endswith(':') else line
			out_lines.append(f'# {heading_text}')
			continue
		for sentence in split_sentences_one_per_line(line):
			out_lines.append(sentence)
	while out_lines and '' == out_lines[-1]:
		out_lines.pop()
	if questions:
		clean_q = [q.strip() for q in questions if q and q.strip()]
		if clean_q:
			if out_lines:
				out_lines.append('')
			out_lines.append('# Questions')
			for q in clean_q:
				out_lines.append(f'- {q}')
	return '\n'.join(out_lines)
def collect_unique_public_past_jobs(data: dict) -> list[dict]:
	current_cid = data.get('job_id')
	rel_descs = data.get('related_descriptions') or {}
	seen_cids: set[str] = set()
	r: list[dict] = []
	for item in data.get('work_history') or []:
		ji = item.get('jobInfo') or {}
		cid = ji.get('ciphertext')
		if not cid or cid == current_cid or cid in seen_cids:
			continue
		rel = rel_descs.get(cid) or {}
		desc = (rel.get('description') or '').strip()
		title = (ji.get('title') or rel.get('title') or '').strip()
		if desc:
			seen_cids.add(cid)
			r.append({'ciphertext': cid, 'url': canonical_job_url(cid), 'title': title, 'description': desc})
	for o_item in data.get('open_jobs') or []:
		cid = o_item.get('ciphertext')
		if not cid or cid == current_cid or cid in seen_cids:
			continue
		rel = rel_descs.get(cid) or {}
		desc = (rel.get('description') or '').strip()
		title = (o_item.get('title') or rel.get('title') or '').strip()
		if desc:
			seen_cids.add(cid)
			r.append({'ciphertext': cid, 'url': canonical_job_url(cid), 'title': title, 'description': desc})
	return r
# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
def format_kb_project_md(data: dict) -> str:
	buyer = data.get('buyer') or {}
	loc = buyer.get('location') or {}
	name_str = 'unresolved; names from reviews require verification' if data.get('client_names') else 'unknown'
	country = (loc.get('country') or 'unknown').strip()
	city = (loc.get('city') or '').strip()
	loc_lines = [country] + ([city] if city else [])
	site_str = 'unresolved; domain mentions and folder names do not prove ownership'
	if data.get('site_hypothesis'):
		h = data['site_hypothesis']
		from .knowledge import SECTIONS, validate_analysis
		analysis = {key: [h] if 'identity' == key else [] for key in SECTIONS}
		analysis['notes'] = {key: 'Separate analysis stage.' for key in SECTIONS if 'identity' != key}
		validate_analysis(analysis)
		site_str = '\n'.join([h['essence'], 'For: ' + '; '.join((f"{a['argument']} «{a['quote']}» " + markdown_link('Source', a['source']) for a in h['for'])), 'Against: ' + '; '.join((f"{a['argument']} «{a['quote']}» " + markdown_link('Source', a['source']) for a in h['against'])), f"Expert plausibility: {h['probability_percent']}%.", h['assessment_basis']])
	job_url = canonical_job_url(data.get('job_id') or data.get('url') or '')
	job_title = (data.get('title') or '').strip()
	structured_desc = structure_job_description(data.get('description') or '', data.get('questions'))
	extra_sources = data.get('extra_sources') or []
	fence = markdown_fence(structured_desc)
	lines = ['# 1. Client', '## 1.1 Name', name_str, '', '## 1.2 Location', *loc_lines, '', '## 1.3 Website', site_str, '', '# 2. Current Client Project']
	if not extra_sources:
		lines.extend([job_url, fence + 'markdown', job_title, '#', structured_desc, fence])
	else:
		lines.extend(['## 2.1. Upwork Description', job_url, fence + 'markdown', job_title, '#', structured_desc, fence])
		for s_idx, src in enumerate(extra_sources, start=2):
			src_heading = (src.get('heading') or f"Description in `{src.get('name', s_idx)}`").strip()
			src_body = (src.get('body') or '').strip()
			src_fence = markdown_fence(src_body)
			lines.extend(['', f'## 2.{s_idx}. {src_heading}', src_fence + 'markdown', src_body, src_fence])
	lines.extend(['', '# 3. Past Client Projects', '## 3.0', 'Projects were posted by the same account; their connection to the current website is not established.', '##', 'Use these projects to understand context.', 'Working on these projects is outside the scope of the current task.'])
	for idx, pjob in enumerate(collect_unique_public_past_jobs(data), start=1):
		p_structured = structure_job_description(pjob['description'])
		pfence = markdown_fence(p_structured)
		lines.extend(['', f'## 3.{idx}', pjob['url'], pfence + 'markdown', pjob['title'], '#', p_structured, pfence])
	return '\n'.join(lines) + '\n'
def format_table_bullet_rows(rows: list[list[str]], headers: list[str] | None=None) -> list[str]:
	hdrs = [h.strip() for h in headers or ()]
	r: list[str] = []
	for row in rows:
		pairs = [f'{hdrs[idx]}: {val.strip()}' if idx < len(hdrs) and hdrs[idx] else val.strip() for idx, val in enumerate(row) if val and val.strip()]
		if pairs:
			r.append('- ' + '; '.join(pairs))
	return r
def classify_attachment(filename_or_path, raw_bytes: bytes | None=None) -> str:
	suffix = Path(str(filename_or_path)).suffix.lower()
	r = 'binary'
	if suffix in IMAGE_EXTENSIONS:
		r = 'image'
	elif suffix in VIDEO_EXTENSIONS:
		r = 'video'
	elif suffix in TEXT_DOC_EXTENSIONS:
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
def normalize_pdf_ligatures(text: str, repairs: dict[str, str] | None=None) -> str:
	out = (text or '').translate(LIGATURE_MAP)
	if repairs:
		for bad, good in repairs.items():
			out = out.replace(bad, good)
	return re.sub('(?<=[A-Za-z])\\u01af(?=[A-Za-z])', 'ff', out)
def discover_pdf_ligature_repairs(pdf_bytes: bytes) -> dict[str, str]:
	cid_to_uni, content_streams, unmapped_ligatures = _parse_pdf_streams(pdf_bytes, text_ops_only=True)
	r: dict[str, str] = {}
	if unmapped_ligatures:
		full_map = {**cid_to_uni, **unmapped_ligatures}
		for dec in content_streams:
			s_full: list[str] = []
			s_broken: list[str] = []
			for tj in re.findall('\\[(.*?)\\]\\s*TJ', dec, re.S):
				for h in re.findall('<([0-9A-Fa-f]+)>', tj):
					for i in range(0, len(h), 4):
						if i + 4 <= len(h):
							c = int(h[i:i + 4], 16)
							s_full.append(full_map.get(c, ' '))
							s_broken.append(cid_to_uni.get(c, '\ufffd'))
			full_text = ''.join(s_full)
			broken_text = ''.join(s_broken)
			for m in re.finditer('[A-Za-z\\ufb00-\\ufb06]+', full_text):
				w = m.group(0)
				b = broken_text[m.start():m.end()]
				if '\ufffd' in b:
					clean_w = w.translate(LIGATURE_MAP)
					r[b.replace('\ufffd', ' ').translate(LIGATURE_MAP)] = clean_w
					r[b.replace('\ufffd', '\u01af').translate(LIGATURE_MAP)] = clean_w
	return r
def _find_poppler_tool(name: str) -> str | None:
	r = shutil.which(name)
	if not r:
		for folder in ('C:\\tools\\poppler\\Library\\bin', 'C:\\Program Files\\poppler\\bin'):
			cand = Path(folder) / (name if name.endswith('.exe') else f'{name}.exe')
			if cand.is_file():
				r = str(cand)
				break
	return r
def sanitize_kb_markdown(text: str) -> str:
	lines = (text or '').replace('\r\n', '\n').replace('\r', '\n').split('\n')
	out: list[str] = []
	i = 0
	while i < len(lines):
		line = lines[i]
		if not (i + 1 < len(lines) and re.match('^\\s*\\|.*\\|\\s*$', line) and re.match('^\\s*\\|?\\s*:?-{3,}(?:\\s*\\|\\s*:?-{3,})+\\s*\\|?\\s*$', lines[i + 1])):
			out.append(re.sub('(?i)<a\\s+[^>]*(?:name|id)\\s*=\\s*["\\\'][^"\\\']*["\\\'][^>]*>(.*?)</a>', '\\1', line))
			i += 1
		else:
			headers = [c.strip() for c in line.strip().strip('|').split('|')]
			i += 2
			table_rows: list[list[str]] = []
			while i < len(lines) and re.match('^\\s*\\|.*\\|\\s*$', lines[i]):
				table_rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
				i += 1
			out.extend(format_table_bullet_rows(table_rows, headers))
	return '\n'.join(out).strip()
def _join_wrapped_lines(prev: str, nxt: str) -> str:
	return prev + nxt if prev.endswith('-') and nxt and nxt[0].islower() else (prev + ' ' + nxt).strip()
def extract_pdf_markdown(raw_bytes: bytes, pdf_path=None) -> str:
	return PdfMarkdownExtractor(raw_bytes, pdf_path=pdf_path).extract()
def extract_docx_markdown(raw_bytes: bytes) -> str:
	return DocxMarkdownExtractor(raw_bytes).extract()
def extract_attachment_markdown(path_or_name, raw_bytes: bytes | None=None) -> str:
	path = Path(str(path_or_name))
	if None is raw_bytes:
		raw_bytes = path.read_bytes()
	suffix = path.suffix.lower()
	if '.pdf' == suffix or raw_bytes.startswith(b'%PDF'):
		r = extract_pdf_markdown(raw_bytes, pdf_path=path if path.is_file() else None)
	elif '.docx' == suffix or (raw_bytes.startswith(b'PK') and suffix in ('.docx', '.docm')):
		r = extract_docx_markdown(raw_bytes)
	elif suffix in ('.xlsx', '.xlsm') and raw_bytes.startswith(b'PK'):
		r = _extract_xlsx_markdown(raw_bytes)
	elif '.odt' == suffix and raw_bytes.startswith(b'PK'):
		with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
			root = ET.fromstring(zf.read('content.xml'))
			paras = [''.join(p.itertext()).strip() for p in root.iter() if p.tag.endswith('}p')]
			r = sanitize_kb_markdown('\n'.join((s for p in paras if p for s in split_sentences_one_per_line(p))))
	else:
		text = raw_bytes.decode('utf-8-sig', errors='replace')
		if suffix in ('.md', '.markdown', '.txt'):
			r = sanitize_kb_markdown(structure_job_description(text) if '.txt' == suffix else text)
		elif '.rtf' == suffix:
			plain = re.sub('\\\\par[d]?\\b', '\n', text)
			plain = re.sub('\\\\[a-zA-Z]+-?\\d*\\s?', '', plain).replace('{', '').replace('}', '')
			r = sanitize_kb_markdown(structure_job_description(plain))
		elif '.json' == suffix:
			try:
				r = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
			except ValueError:
				r = sanitize_kb_markdown(text)
		elif suffix not in ('.csv', '.tsv'):
			r = sanitize_kb_markdown(text)
		else:
			reader = list(csv.reader(io.StringIO(text), delimiter='\t' if '.tsv' == suffix else ','))
			headers = [h.strip() for h in reader[0]] if 1 < len(reader) else []
			rows = reader[1:] if 1 < len(reader) else reader
			r = '\n'.join(format_table_bullet_rows(rows, headers)) if reader else ''
	return r
def canonical_video_url(url: str) -> str:
	u = url.strip().rstrip('.,;!?')
	m = re.match('^https?://(?:www\\.)?loom\\.com/(?:share|embed)/([A-Za-z0-9]+)', u, re.I)
	return f'https://loom.com/share/{m.group(1)}' if m else u
def detect_client_videos(description: str='', document_markdowns: list[str] | tuple[str, ...]=(), saved_attachments: list[dict] | tuple[dict, ...]=()) -> list[dict]:
	r: list[dict] = []
	seen_keys: set[str] = set()
	for text in [description or '', *(document_markdowns or ())]:
		for match in _VIDEO_URL_RE.finditer(text or ''):
			raw_url = match.group(0).rstrip('.,;!)')
			canon = canonical_video_url(raw_url)
			if canon in seen_keys:
				continue
			seen_keys.add(canon)
			loom_m = re.match('^https?://(?:www\\.)?loom\\.com/share/([A-Za-z0-9]+)', canon, re.I)
			r.append({'kind': 'loom' if loom_m else 'url', 'video_id': loom_m.group(1) if loom_m else None, 'url': canon, 'raw_url': raw_url, 'label': canon, 'heading': f'Description in {canon}'})
	for item in saved_attachments or []:
		name = Path(item.get('filename') or item.get('name') or item.get('file') or '').name
		if name and 'video' == classify_attachment(name):
			key = f'file:{name}'
			if key not in seen_keys:
				seen_keys.add(key)
				r.append({'kind': 'file', 'video_id': item.get('sha256'), 'filename': name, 'sha256': item.get('sha256'), 'label': f'`{name}`', 'heading': f'Description in `{name}`'})
	return r
def format_duration_ru(seconds: int | float | None) -> str:
	if not seconds or 0 >= seconds:
		r = 'duration not specified'
	else:
		mm, ss = divmod(int(round(float(seconds))), 60)
		if 0 < mm and 0 < ss:
			r = f'{mm} min {ss} sec'
		elif 0 < mm:
			r = f'{mm} min'
		else:
			r = f'{ss} sec'
	return r
def parse_webvtt_phrases(vtt_text: str) -> list[dict]:
	r: list[dict] = []
	for block in re.split('\\r?\\n\\r?\\n', (vtt_text or '').strip()):
		lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
		if not lines or lines[0].startswith('WEBVTT'):
			continue
		ts_line = next((ln for ln in lines if '-->' in ln), None)
		if not ts_line:
			continue
		m = re.match('^(?:(\\d+):)?(\\d{2}):(\\d{2})[.,]\\d+\\s*-->', ts_line)
		if not m:
			continue
		mm = int(m.group(2)) + int(m.group(1) or 0) * 60
		ss = int(m.group(3))
		idx = lines.index(ts_line)
		txt = ' '.join((re.sub('<[^>]+>', '', ln).strip() for ln in lines[idx + 1:] if ln.strip())).strip()
		if txt:
			r.append({'ts': f'[{mm:02d}:{ss:02d}]', 'seconds': mm * 60 + ss, 'text': txt})
	return r
def extract_loom_video(url: str, timeout: float=15.0, opener=None) -> dict:
	open_fn = opener or (lambda req, tm: urlopen(req, timeout=tm))
	canon = canonical_video_url(url)
	loom_m = re.search('loom\\.com/(?:share|embed)/([A-Za-z0-9]+)', canon, re.I)
	if not loom_m:
		raise ValueError(f'Not a Loom video URL: {url}')
	vid_id = loom_m.group(1)
	share_url = f'https://www.loom.com/share/{vid_id}'
	with open_fn(Request(share_url, headers={'User-Agent': 'Mozilla/5.0'}), timeout) as resp:
		html = resp.read().decode('utf-8', errors='ignore')
	state_m = re.search('window\\.__APOLLO_STATE__\\s*=\\s*(\\{.*?\\});\\s*\\n', html, re.S)
	if not state_m:
		raise ValueError(f'Loom __APOLLO_STATE__ not found for {share_url}')
	state = json.loads(state_m.group(1))
	video_obj = state.get(f'RegularUserVideo:{vid_id}') or next((v for k, v in state.items() if k.startswith('RegularUserVideo:') and isinstance(v, dict)), {})
	title = (video_obj.get('name') or '').strip()
	owner_ref = (video_obj.get('owner') or {}).get('__ref') if isinstance(video_obj.get('owner'), dict) else None
	owner_obj = state.get(owner_ref, {}) if owner_ref else next((v for k, v in state.items() if k.startswith('RegularUser:') and isinstance(v, dict)), {})
	speaker = (owner_obj.get('display_name') or owner_obj.get('first_name') or '').strip()
	vprops = video_obj.get('video_properties') or {}
	duration_sec = vprops.get('duration')
	screen_type = vprops.get('screen_type') or vprops.get('recording_type') or ''
	tdetails = next((v for k, v in state.items() if k.startswith('VideoTranscriptDetails:') and isinstance(v, dict)), {})
	phrases: list[dict] = []
	if tdetails.get('captions_source_url') and (not tdetails.get('source_url')):
		with open_fn(Request(tdetails['captions_source_url'], headers={'User-Agent': 'Mozilla/5.0'}), timeout) as vresp:
			phrases = parse_webvtt_phrases(vresp.read().decode('utf-8', errors='replace'))
	elif tdetails.get('source_url'):
		with open_fn(Request(tdetails['source_url'], headers={'User-Agent': 'Mozilla/5.0'}), timeout) as tresp:
			tdata = json.loads(tresp.read().decode('utf-8', errors='replace'))
		for p in tdata.get('phrases') or []:
			val = (p.get('value') or '').strip()
			if val:
				sec = int(float(p.get('ts') or 0))
				mm, ss = divmod(sec, 60)
				phrases.append({'ts': f'[{mm:02d}:{ss:02d}]', 'seconds': sec, 'text': val})
	transcript_lines = [f"{p['ts']} {p['text']}" for p in phrases]
	dur_str = format_duration_ru(duration_sec)
	speaker_str = f'Speaker: {speaker} ({dur_str}).' if speaker else f'Recording duration: {dur_str}.'
	title_str = f' Recording title: «{title}».' if title else ''
	mode_str = ' Recording format: screen share and speaker webcam (screen_cam).' if 'screen_cam' == screen_type else ''
	video_header = f'{speaker_str}{title_str}{mode_str}'.strip()
	key_points = [f"- ({p['ts'].strip('[]')}) {p['text']}" for p in phrases[:8]] or ['- Spoken commentary is recorded in the full transcript below.']
	md_lines = ['# Video:', video_header, '', '# Key Spoken Commentary Points (Additions to Document Text):', *key_points, '', '# Full Audio Transcript:', *(transcript_lines or ['[00:00] (audio track is absent or contains no speech)'])]
	return {'kind': 'loom', 'video_id': vid_id, 'url': canon, 'title': title, 'speaker': speaker, 'duration_seconds': duration_sec, 'duration_human': dur_str, 'screen_type': screen_type, 'phrases': phrases, 'markdown': '\n'.join(md_lines)}
