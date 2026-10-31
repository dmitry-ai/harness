# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
import re
from .links import markdown_link, readable_reference
def normalize_job_id(url_or_id: str) -> str:
	match = re.search('(~0[12][0-9a-zA-Z]+)', url_or_id.strip())
	if not match:
		raise ValueError(f'Cannot extract Upwork job ID (~02...) from: {url_or_id}')
	r = match.group(1)
	return r
def canonical_job_url(url_or_id: str) -> str:
	return f'https://upwork.com/jobs/{normalize_job_id(url_or_id)}'
def resolve_nuxt_devalue(arr: list, idx: int=0, seen: set[int] | None=None):
	if None is seen:
		seen = set()
	if not isinstance(idx, int) or idx < 0 or idx >= len(arr) or (idx in seen):
		r = arr[idx] if isinstance(idx, int) and 0 <= idx < len(arr) else idx
	else:
		seen = seen | {idx}
		val = arr[idx]
		if isinstance(val, list):
			if 2 == len(val) and isinstance(val[0], str) and (val[0] in ('Reactive', 'ShallowReactive', 'Ref', 'EmptyRef', 'Set', 'ShallowRef')):
				r = resolve_nuxt_devalue(arr, val[1], seen)
			else:
				r = [resolve_nuxt_devalue(arr, x, seen) if isinstance(x, int) else x for x in val]
		elif not isinstance(val, dict):
			r = val
		else:
			r = {k: resolve_nuxt_devalue(arr, v, seen) if isinstance(v, int) else v for k, v in val.items()}
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
	r = [{'name': k, 'mentions': v} for k, v in sorted(found.items(), key=lambda x: -len(x[1]))]
	return r
def extract_candidate_domains(texts: list[str]) -> list[str]:
	pattern = '(?<![\\w.-])((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z]{2,63})(?![\\w.-])'
	domains = (m[4:] if m.startswith('www.') else m for text in texts for m in re.findall(pattern, text.lower()))
	r = list(dict.fromkeys(domains))
	return r
def markdown_fence(text: str, marker: str='~') -> str:
	return marker * max(3, 1 + max((len(m[0]) for m in re.finditer(re.escape(marker) + '+', text)), default=0))
_SENTENCE_SPLIT_RE = re.compile('(?<!\\be\\.g)(?<!\\bi\\.e)(?<!\\bvs)(?<!\\betc)(?<!\\bMr)(?<!\\bDr)(?<!\\bSt)(?<!\\bNB)(?<=[.!?])\\s+(?=[A-Z\\u0410-\\u042f\\u0401"«(])')
def split_sentences_one_per_line(text: str) -> list[str]:
	parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(text.strip()) if p.strip()]
	r = parts or ([text.strip()] if text.strip() else [])
	return r
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
			body = bullet_match.group(1).strip()
			sentences = split_sentences_one_per_line(body)
			if sentences:
				out_lines.append(f'- {sentences[0]}')
				for extra in sentences[1:]:
					out_lines.append(extra)
			continue
		prev_empty = 0 == idx or not lines[idx - 1]
		words = line.split()
		is_heading = prev_empty and 1 <= len(words) <= 8 and (len(line) <= 70) and line[0].isupper() and (not line.startswith(('http://', 'https://', '#', '-'))) and (not re.match('^\\d+[.)]\\s', line)) and (line.endswith(':') or (not line.endswith(('.', '!', '?', ';', ',')) and idx + 1 < len(lines)))
		if is_heading and words[0].lower() in ('we', "we're", 'i', 'the', 'this', 'there', 'please', 'see', 'as', 'and', 'so', 'if', 'in', 'for', 'most', 'all'):
			if not line.endswith(':'):
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
	r = '\n'.join(out_lines)
	return r
def collect_unique_public_past_jobs(data: dict) -> list[dict]:
	current_cid = data.get('job_id')
	rel_descs = data.get('related_descriptions') or {}
	seen_cids: set[str] = set()
	public_jobs: list[dict] = []
	for item in data.get('work_history') or []:
		ji = item.get('jobInfo') or {}
		cid = ji.get('ciphertext')
		if not cid or cid == current_cid or cid in seen_cids:
			continue
		rel = rel_descs.get(cid) or {}
		desc = (rel.get('description') or '').strip()
		title = (ji.get('title') or rel.get('title') or '').strip()
		if not desc:
			continue
		seen_cids.add(cid)
		public_jobs.append({'ciphertext': cid, 'url': canonical_job_url(cid), 'title': title, 'description': desc})
	for o_item in data.get('open_jobs') or []:
		cid = o_item.get('ciphertext')
		if not cid or cid == current_cid or cid in seen_cids:
			continue
		rel = rel_descs.get(cid) or {}
		desc = (rel.get('description') or '').strip()
		title = (o_item.get('title') or rel.get('title') or '').strip()
		if not desc:
			continue
		seen_cids.add(cid)
		public_jobs.append({'ciphertext': cid, 'url': canonical_job_url(cid), 'title': title, 'description': desc})
	r = public_jobs
	return r
# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
def format_kb_project_md(data: dict) -> str:
	buyer = data.get('buyer') or {}
	loc = buyer.get('location') or {}
	client_names = data.get('client_names') or []
	if client_names:
		name_str = 'unresolved; names from reviews require verification'
	else:
		name_str = 'unknown'
	country = (loc.get('country') or 'unknown').strip()
	city = (loc.get('city') or '').strip()
	loc_lines = [country]
	if city:
		loc_lines.append(city)
	site_str = 'unresolved; domain mentions and folder names do not prove ownership'
	if data.get('site_hypothesis'):
		h = data['site_hypothesis']
		from .knowledge import validate_analysis, SECTIONS
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
		fence = markdown_fence(p_structured)
		lines.extend(['', f'## 3.{idx}', pjob['url'], fence + 'markdown', pjob['title'], '#', p_structured, fence])
	r = '\n'.join(lines) + '\n'
	return r
TEXT_DOC_EXTENSIONS = {'.pdf', '.docx', '.doc', '.rtf', '.odt', '.txt', '.md', '.markdown', '.rst', '.log', '.ini', '.cfg', '.conf', '.html', '.htm', '.xhtml', '.xml', '.svg', '.json', '.yaml', '.yml', '.toml', '.csv', '.tsv', '.xlsx', '.xls', '.xlsm', '.ods', '.js', '.ts', '.jsx', '.tsx', '.py', '.php', '.rb', '.java', '.cs', '.go', '.rs', '.c', '.cpp', '.h', '.css', '.scss', '.less', '.liquid', '.sql', '.sh', '.ps1', '.bat', '.har'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff', '.tif', '.avif', '.heic'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v', '.wmv', '.flv', '.mpeg', '.mpg'}
LIGATURE_MAP = str.maketrans({'ﬀ': 'ff', 'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬃ': 'ffi', 'ﬄ': 'ffl', 'ﬅ': 'st', 'ﬆ': 'st'})
def classify_attachment(filename_or_path, raw_bytes: bytes | None=None) -> str:
	from pathlib import Path
	suffix = Path(str(filename_or_path)).suffix.lower()
	if suffix in IMAGE_EXTENSIONS:
		return 'image'
	if suffix in VIDEO_EXTENSIONS:
		return 'video'
	if suffix in TEXT_DOC_EXTENSIONS:
		return 'document'
	if None is not raw_bytes:
		if raw_bytes.startswith(b'%PDF'):
			return 'document'
		if b'\x00' not in raw_bytes[:4096]:
			try:
				raw_bytes.decode('utf-8')
				return 'document'
			except UnicodeDecodeError:
				pass
	return 'binary'
def normalize_pdf_ligatures(text: str, repairs: dict[str, str] | None=None) -> str:
	out = (text or '').translate(LIGATURE_MAP)
	if repairs:
		for bad, good in repairs.items():
			out = out.replace(bad, good)
	out = re.sub('(?<=[A-Za-z])\\u01af(?=[A-Za-z])', 'ff', out)
	r = out
	return r
def discover_pdf_ligature_repairs(pdf_bytes: bytes) -> dict[str, str]:
	import zlib
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
		elif 'BT' in dec and ('TJ' in dec or 'Tj' in dec):
			content_streams.append(dec)
	unmapped_ligatures: dict[int, str] = {}
	for cid, ch in list(cid_to_uni.items()):
		if 'ﬁ' == ch and 'ﬂ' == cid_to_uni.get(cid + 1):
			for offset, lig_char in ((-2, 'ﬀ'), (-1, 'ﬃ'), (2, 'ﬄ')):
				if cid + offset not in cid_to_uni:
					unmapped_ligatures[cid + offset] = lig_char
	repairs: dict[str, str] = {}
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
							s_broken.append(cid_to_uni.get(c, '�'))
			full_text = ''.join(s_full)
			broken_text = ''.join(s_broken)
			for m in re.finditer('[A-Za-z\\ufb00-\\ufb06]+', full_text):
				w = m.group(0)
				b = broken_text[m.start():m.end()]
				if '�' in b:
					clean_w = w.translate(LIGATURE_MAP)
					repairs[b.replace('�', ' ').translate(LIGATURE_MAP)] = clean_w
					repairs[b.replace('�', 'Ư').translate(LIGATURE_MAP)] = clean_w
	r = repairs
	return r
def _find_poppler_tool(name: str) -> str | None:
	from pathlib import Path
	import shutil
	found = shutil.which(name)
	if found:
		return found
	for folder in ('C:\\tools\\poppler\\Library\\bin', 'C:\\Program Files\\poppler\\bin'):
		cand = Path(folder) / (name if name.endswith('.exe') else f'{name}.exe')
		if cand.is_file():
			return str(cand)
	return None
def sanitize_kb_markdown(text: str) -> str:
	lines = (text or '').replace('\r\n', '\n').replace('\r', '\n').split('\n')
	out: list[str] = []
	i = 0
	while i < len(lines):
		line = lines[i]
		if i + 1 < len(lines) and re.match('^\\s*\\|.*\\|\\s*$', line) and re.match('^\\s*\\|?\\s*:?-{3,}(?:\\s*\\|\\s*:?-{3,})+\\s*\\|?\\s*$', lines[i + 1]):
			headers = [c.strip() for c in line.strip().strip('|').split('|')]
			i += 2
			while i < len(lines) and re.match('^\\s*\\|.*\\|\\s*$', lines[i]):
				cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
				pairs = [f'{headers[idx]}: {val}' if idx < len(headers) and headers[idx] else val for idx, val in enumerate(cells) if val]
				if pairs:
					out.append('- ' + '; '.join(pairs))
				i += 1
			continue
		cleaned = re.sub('(?i)<a\\s+[^>]*(?:name|id)\\s*=\\s*["\\\'][^"\\\']*["\\\'][^>]*>(.*?)</a>', '\\1', line)
		out.append(cleaned)
		i += 1
	r = '\n'.join(out).strip()
	return r
def _join_wrapped_lines(prev: str, nxt: str) -> str:
	if prev.endswith('-') and nxt and nxt[0].islower():
		r = prev + nxt
	else:
		r = (prev + ' ' + nxt).strip()
	return r
def extract_pdf_markdown(raw_bytes: bytes, pdf_path=None) -> str:
	from pathlib import Path
	import subprocess
	import tempfile
	import xml.etree.ElementTree as ET
	import zlib
	repairs = discover_pdf_ligature_repairs(raw_bytes)
	def clean_txt(s: str) -> str:
		return re.sub('\\s+', ' ', normalize_pdf_ligatures(s, repairs)).strip()
	pdftohtml = _find_poppler_tool('pdftohtml')
	xml_stdout = None
	if pdftohtml:
		tmp_path = None
		try:
			if pdf_path and Path(pdf_path).is_file():
				target_str = str(pdf_path)
			else:
				with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tf:
					tf.write(raw_bytes)
					tmp_path = Path(tf.name)
				target_str = str(tmp_path)
			res = subprocess.run([pdftohtml, '-xml', '-stdout', target_str], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
			if 0 == res.returncode and '<pdf2xml' in res.stdout:
				xml_stdout = res.stdout
		except Exception:
			xml_stdout = None
		finally:
			if tmp_path and tmp_path.exists():
				try:
					tmp_path.unlink()
				except OSError:
					pass
	if xml_stdout:
		try:
			root = ET.fromstring(xml_stdout)
			bold_fonts: set[str] = set()
			font_sizes: dict[str, int] = {}
			font_chars: dict[str, int] = {}
			for fs in root.findall('.//fontspec'):
				fid = fs.attrib.get('id', '')
				fam = (fs.attrib.get('family') or '').lower()
				try:
					font_sizes[fid] = int(float(fs.attrib.get('size', '12')))
				except ValueError:
					font_sizes[fid] = 12
				if 'bold' in fam:
					bold_fonts.add(fid)
			for page in root.findall('page'):
				for t in page.findall('text'):
					fid = t.attrib.get('font', '')
					txt = ''.join(t.itertext()).strip()
					if len(txt) > 1:
						font_chars[fid] = font_chars.get(fid, 0) + len(txt)
			dominant_body_font = max(font_chars, key=font_chars.get) if font_chars else None
			for page in root.findall('page'):
				for t in page.findall('text'):
					fid = t.attrib.get('font', '')
					if fid == dominant_body_font:
						continue
					txt = ''.join(t.itertext()).strip()
					if txt.endswith(':') and 1 <= len(txt.split()) <= 5 or re.match('^(?:Phase|Step|Part|Section)\\s+\\d+\\b', txt):
						bold_fonts.add(fid)
			visual_lines: list[dict] = []
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
							label = clean_txt(ctext)
							parts.append(markdown_link(label, href) if label else readable_reference(href))
						if child.tail:
							parts.append(child.tail)
					raw_txt = ''.join(parts)
					if not raw_txt.strip():
						continue
					is_bold = has_b or font in bold_fonts
					if page_lines and abs(page_lines[-1]['top'] - top) <= 4:
						page_lines[-1]['spans'].append((left, is_bold, raw_txt))
					else:
						page_lines.append({'page': page_num, 'top': top, 'left': left, 'height': max(height, 12), 'spans': [(left, is_bold, raw_txt)]})
				visual_lines.extend(page_lines)
			blocks: list[dict] = []
			for ln in visual_lines:
				spans = sorted(ln['spans'], key=lambda x: x[0])
				first_txt = clean_txt(spans[0][2])
				is_bullet = first_txt in ('\uf0b7', '•', '●', '○', '▪', '▫', '-')
				is_num = bool(re.match('^\\d+[.)]$', first_txt)) and len(spans) > 1
				if is_bullet or is_num:
					marker = '-' if is_bullet else first_txt
					rest_spans = [s for s in spans[1:] if clean_txt(s[2])]
					body_left = rest_spans[0][0] if rest_spans else ln['left'] + 25
					if not (rest_spans and rest_spans[0][1] and (len(rest_spans) > 1)):
						text = clean_txt(' '.join((s[2] for s in rest_spans)))
					else:
						label = clean_txt(rest_spans[0][2])
						tail = clean_txt(' '.join((s[2] for s in rest_spans[1:])))
						text = f'**{label}** {tail}'.strip()
					blocks.append({'kind': 'list', 'marker': marker, 'text': text, 'page': ln['page'], 'top': ln['top'], 'left': ln['left'], 'body_left': body_left, 'height': ln['height']})
					continue
				all_bold = all((s[1] for s in spans if clean_txt(s[2])))
				full_line = clean_txt(' '.join((s[2] for s in spans)))
				if all_bold and len(full_line) <= 100:
					blocks.append({'kind': 'heading', 'text': full_line, 'page': ln['page'], 'top': ln['top'], 'left': ln['left'], 'body_left': ln['left'], 'height': ln['height']})
					continue
				if not (spans[0][1] and len(spans) > 1):
					line_text = full_line
					starts_bold = False
				else:
					label = clean_txt(spans[0][2])
					tail = clean_txt(' '.join((s[2] for s in spans[1:])))
					line_text = f'**{label}** {tail}'.strip()
					starts_bold = True
				if blocks and (not starts_bold):
					prev = blocks[-1]
					same_page_cont = prev['page'] == ln['page'] and ln['top'] - prev['top'] <= prev['height'] * 1.65 and (abs(ln['left'] - prev['body_left']) <= 10) and (prev['kind'] in ('para', 'list'))
					cross_page_cont = prev['page'] + 1 == ln['page'] and abs(ln['left'] - prev['body_left']) <= 10 and (prev['kind'] in ('para', 'list')) and (not prev['text'].endswith(('.', '!', '?', ':')))
					if same_page_cont or cross_page_cont:
						prev['text'] = _join_wrapped_lines(prev['text'], line_text)
						prev['page'] = ln['page']
						prev['top'] = ln['top']
						continue
				blocks.append({'kind': 'para', 'text': line_text, 'page': ln['page'], 'top': ln['top'], 'left': ln['left'], 'body_left': ln['left'], 'height': ln['height']})
			out_lines: list[str] = []
			for b in blocks:
				if 'heading' == b['kind']:
					htext = b['text'][:-1].strip() if b['text'].endswith(':') else b['text']
					level = '##' if re.match('^(?:Phase|Step|Part)\\s+\\d+\\b', htext, re.I) else '#'
					if out_lines and '' != out_lines[-1]:
						out_lines.append('')
					out_lines.append(f'{level} {htext}')
				elif 'list' == b['kind']:
					out_lines.append(f"{b['marker']} {b['text']}")
				else:
					for sent in split_sentences_one_per_line(b['text']):
						out_lines.append(sent)
			if out_lines:
				return sanitize_kb_markdown('\n'.join(out_lines))
		except Exception:
			pass
	pdftotext = _find_poppler_tool('pdftotext')
	if pdftotext:
		tmp_path = None
		try:
			if pdf_path and Path(pdf_path).is_file():
				target_str = str(pdf_path)
			else:
				with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tf:
					tf.write(raw_bytes)
					tmp_path = Path(tf.name)
				target_str = str(tmp_path)
			res = subprocess.run([pdftotext, target_str, '-'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
			if 0 == res.returncode and res.stdout.strip():
				cleaned = normalize_pdf_ligatures(res.stdout.replace('\x0c', '\n\n'), repairs)
				return sanitize_kb_markdown(structure_job_description(cleaned))
		except Exception:
			pass
		finally:
			if tmp_path and tmp_path.exists():
				try:
					tmp_path.unlink()
				except OSError:
					pass
	cid_to_uni: dict[int, str] = {}
	streams: list[str] = []
	for m in re.finditer(b'stream\\s*(.*?)\\s*endstream', raw_bytes, re.S):
		raw = m.group(1)
		try:
			dec = zlib.decompress(raw).decode('latin1', errors='ignore')
		except Exception:
			dec = raw.decode('latin1', errors='ignore')
		if 'begincmap' in dec:
			for cid_hex, uni_hex in re.findall('<([0-9A-Fa-f]{4})>\\s*<([0-9A-Fa-f]{4,8})>', dec):
				chars = ''.join((chr(int(uni_hex[i:i + 4], 16)) for i in range(0, len(uni_hex), 4)))
				cid_to_uni[int(cid_hex, 16)] = chars
		elif 'BT' in dec:
			streams.append(dec)
	for cid, ch in list(cid_to_uni.items()):
		if 'ﬁ' == ch and 'ﬂ' == cid_to_uni.get(cid + 1):
			cid_to_uni.setdefault(cid - 2, 'ff')
			cid_to_uni.setdefault(cid - 1, 'ffi')
			cid_to_uni.setdefault(cid + 2, 'ffl')
	extracted_chunks: list[str] = []
	for dec in streams:
		for tj in re.findall('\\[(.*?)\\]\\s*TJ|\\((.*?)\\)\\s*Tj', dec, re.S):
			hex_part, lit_part = tj
			if hex_part:
				chars = []
				for h in re.findall('<([0-9A-Fa-f]+)>', hex_part):
					for i in range(0, len(h), 4):
						if i + 4 <= len(h):
							chars.append(cid_to_uni.get(int(h[i:i + 4], 16), ' '))
				extracted_chunks.append(''.join(chars))
			elif lit_part:
				extracted_chunks.append(lit_part)
	joined = normalize_pdf_ligatures(' '.join(extracted_chunks), repairs)
	return sanitize_kb_markdown(structure_job_description(joined))
def extract_docx_markdown(raw_bytes: bytes) -> str:
	import io
	import zipfile
	import xml.etree.ElementTree as ET
	W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
	R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
	W = f'{{{W_NS}}}'
	R = f'{{{R_NS}}}'
	def render_link(text: str, url: str) -> str:
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
	with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
		rels: dict[str, str] = {}
		if 'word/_rels/document.xml.rels' in zf.namelist():
			rel_root = ET.fromstring(zf.read('word/_rels/document.xml.rels'))
			for rel in rel_root:
				rid = rel.attrib.get('Id')
				target = rel.attrib.get('Target')
				if rid and target:
					rels[rid] = target
		num_formats: dict[str, dict[str, str]] = {}
		if 'word/numbering.xml' in zf.namelist():
			num_root = ET.fromstring(zf.read('word/numbering.xml'))
			abstract_map: dict[str, dict[str, str]] = {}
			for abs_num in num_root.findall(f'.//{W}abstractNum'):
				abs_id = abs_num.attrib.get(f'{W}abstractNumId')
				lvl_map: dict[str, str] = {}
				for lvl in abs_num.findall(f'./{W}lvl'):
					ilvl = lvl.attrib.get(f'{W}ilvl', '0')
					nf = lvl.find(f'./{W}numFmt')
					lvl_map[ilvl] = nf.attrib.get(f'{W}val', 'bullet') if None is not nf else 'bullet'
				if None is not abs_id:
					abstract_map[abs_id] = lvl_map
			for num in num_root.findall(f'.//{W}num'):
				num_id = num.attrib.get(f'{W}numId')
				abs_ref = num.find(f'./{W}abstractNumId')
				if None is not num_id and None is not abs_ref:
					abs_id = abs_ref.attrib.get(f'{W}val')
					num_formats[num_id] = abstract_map.get(abs_id, {})
		doc_root = ET.fromstring(zf.read('word/document.xml'))
		body = doc_root.find(f'./{W}body')
		if None is body:
			return ''
		raw_items: list[dict] = []
		list_counters: dict[tuple[str, int], int] = {}
		active_field_url: str | None = None
		in_field_result = False
		for elem in body:
			if elem.tag == f'{W}tbl':
				rows_data: list[list[str]] = []
				for row in elem.findall(f'./{W}tr'):
					cells_data: list[str] = []
					for cell in row.findall(f'./{W}tc'):
						cell_txt = ' '.join((''.join((t.text for t in p.findall(f'.//{W}t') if t.text)).strip() for p in cell.findall(f'.//{W}p'))).strip()
						cells_data.append(cell_txt)
					if any(cells_data):
						rows_data.append(cells_data)
				if rows_data:
					headers = rows_data[0] if len(rows_data) > 1 else []
					start_idx = 1 if len(rows_data) > 1 else 0
					for r_cells in rows_data[start_idx:]:
						pairs = [f'{headers[idx]}: {val}' if idx < len(headers) and headers[idx] else val for idx, val in enumerate(r_cells) if val]
						if pairs:
							raw_items.append({'kind': 'list', 'text': '- ' + '; '.join(pairs)})
				continue
			if elem.tag != f'{W}p':
				continue
			pstyle_el = elem.find(f'./{W}pPr/{W}pStyle')
			style = pstyle_el.attrib.get(f'{W}val', '') if None is not pstyle_el else ''
			num_pr = elem.find(f'./{W}pPr/{W}numPr')
			num_id = None
			ilvl = 0
			if None is not num_pr:
				nid_el = num_pr.find(f'./{W}numId')
				ilvl_el = num_pr.find(f'./{W}ilvl')
				if None is not nid_el:
					num_id = nid_el.attrib.get(f'{W}val')
				if None is not ilvl_el:
					try:
						ilvl = int(ilvl_el.attrib.get(f'{W}val', '0'))
					except ValueError:
						ilvl = 0
			parts: list[str] = []
			field_buf: list[str] = []
			for child in elem:
				if child.tag == f'{W}hyperlink':
					rid = child.attrib.get(f'{R}id', '')
					url = rels.get(rid, '')
					htext = ''.join((t.text for t in child.findall(f'.//{W}t') if t.text))
					if htext.strip():
						parts.append(render_link(htext, url))
				elif child.tag == f'{W}r':
					for sub in child:
						if sub.tag == f'{W}fldChar':
							ftype = sub.attrib.get(f'{W}fldCharType', '')
							if 'begin' == ftype:
								if in_field_result and field_buf:
									parts.append(render_link(''.join(field_buf), active_field_url or ''))
								active_field_url = None
								in_field_result = False
								field_buf = []
							elif 'separate' == ftype:
								in_field_result = True
							elif 'end' == ftype:
								if field_buf:
									parts.append(render_link(''.join(field_buf), active_field_url or ''))
								active_field_url = None
								in_field_result = False
								field_buf = []
						elif sub.tag == f'{W}instrText' and sub.text:
							m = re.search('HYPERLINK\\s+"([^"]+)"', sub.text)
							if m:
								active_field_url = m.group(1)
						elif sub.tag == f'{W}t' and sub.text:
							if in_field_result and active_field_url:
								field_buf.append(sub.text)
							else:
								parts.append(sub.text)
			if in_field_result and field_buf:
				parts.append(render_link(''.join(field_buf), active_field_url or ''))
				field_buf = []
			text = re.sub('[ \\t]+', ' ', ''.join(parts)).strip()
			if not text:
				continue
			h_match = re.match('^Heading(\\d+)$', style, re.I)
			if 'title' == style.lower():
				raw_items.append({'kind': 'heading', 'level': 1, 'text': text})
			elif h_match:
				raw_items.append({'kind': 'heading', 'level': min(int(h_match.group(1)), 6), 'text': text})
			elif not (None is not num_id and '0' != num_id):
				raw_items.append({'kind': 'para', 'text': text})
			else:
				fmt = num_formats.get(num_id, {}).get(str(ilvl), 'bullet')
				indent = '  ' * ilvl
				if fmt not in ('decimal', 'lowerLetter', 'upperLetter', 'lowerRoman', 'upperRoman'):
					raw_items.append({'kind': 'list', 'text': f'{indent}- {text}'})
				else:
					key = (num_id, ilvl)
					list_counters[key] = list_counters.get(key, 0) + 1
					raw_items.append({'kind': 'list', 'text': f'{indent}{list_counters[key]}. {text}'})
		heading_levels = [it['level'] for it in raw_items if 'heading' == it['kind']]
		if heading_levels:
			min_lvl = min(heading_levels)
			if min_lvl > 1:
				first_h_seen = False
				for it in raw_items:
					if 'heading' == it['kind']:
						if not (not first_h_seen and raw_items[0] is it and (heading_levels.count(min_lvl) > 1)):
							it['level'] = max(1, it['level'] - (min_lvl - 2 if first_h_seen else min_lvl - 1))
						else:
							it['level'] = 1
							first_h_seen = True
		out_lines: list[str] = []
		for it in raw_items:
			if 'heading' == it['kind']:
				out_lines.append(f"{'#' * it['level']} {it['text']}")
			elif 'list' == it['kind']:
				out_lines.append(it['text'])
			else:
				for sent in split_sentences_one_per_line(it['text']):
					out_lines.append(sent)
		return sanitize_kb_markdown('\n'.join(out_lines))
def extract_attachment_markdown(path_or_name, raw_bytes: bytes | None=None) -> str:
	from pathlib import Path
	import csv
	import io
	import json
	import zipfile
	import xml.etree.ElementTree as ET
	path = Path(str(path_or_name))
	if None is raw_bytes:
		raw_bytes = path.read_bytes()
	suffix = path.suffix.lower()
	if '.pdf' == suffix or raw_bytes.startswith(b'%PDF'):
		return extract_pdf_markdown(raw_bytes, pdf_path=path if path.is_file() else None)
	if '.docx' == suffix or (raw_bytes.startswith(b'PK') and suffix in ('.docx', '.docm')):
		return extract_docx_markdown(raw_bytes)
	if '.odt' == suffix and raw_bytes.startswith(b'PK'):
		with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
			root = ET.fromstring(zf.read('content.xml'))
			paras = [''.join(p.itertext()).strip() for p in root.iter() if p.tag.endswith('}p')]
			return sanitize_kb_markdown('\n'.join((s for p in paras if p for s in split_sentences_one_per_line(p))))
	if suffix in ('.xlsx', '.xlsm') and raw_bytes.startswith(b'PK'):
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
			return sanitize_kb_markdown('\n'.join(lines))
	text = raw_bytes.decode('utf-8-sig', errors='replace')
	if suffix in ('.csv', '.tsv'):
		delim = '\t' if '.tsv' == suffix else ','
		reader = list(csv.reader(io.StringIO(text), delimiter=delim))
		if not reader:
			return ''
		headers = [h.strip() for h in reader[0]] if len(reader) > 1 else []
		rows = reader[1:] if len(reader) > 1 else reader
		lines = []
		for r in rows:
			pairs = [f'{headers[i]}: {v.strip()}' if i < len(headers) and headers[i] else v.strip() for i, v in enumerate(r) if v.strip()]
			if pairs:
				lines.append('- ' + '; '.join(pairs))
		return '\n'.join(lines)
	if '.json' == suffix:
		try:
			return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
		except ValueError:
			return sanitize_kb_markdown(text)
	if '.rtf' == suffix:
		plain = re.sub('\\\\par[d]?\\b', '\n', text)
		plain = re.sub('\\\\[a-zA-Z]+-?\\d*\\s?', '', plain).replace('{', '').replace('}', '')
		return sanitize_kb_markdown(structure_job_description(plain))
	if suffix in ('.md', '.markdown', '.txt'):
		return sanitize_kb_markdown(structure_job_description(text) if '.txt' == suffix else text)
	return sanitize_kb_markdown(text)
_VIDEO_URL_RE = re.compile('https?://(?:www\\.)?(?:loom\\.com/(?:share|embed)/[A-Za-z0-9_-]+|youtube\\.com/(?:watch\\?[^\\s)"\\\'>]+|embed/[A-Za-z0-9_-]+|shorts/[A-Za-z0-9_-]+)|youtu\\.be/[A-Za-z0-9_-]+|vimeo\\.com/\\d+|player\\.vimeo\\.com/video/\\d+|[^\\s)"\\\'>]+\\.(?:mp4|mov|webm|m4v)(?:\\?[^\\s)"\\\'>]*)?)', re.I)
def canonical_video_url(url: str) -> str:
	u = url.strip().rstrip('.,;!?')
	m = re.match('^https?://(?:www\\.)?loom\\.com/(?:share|embed)/([A-Za-z0-9]+)', u, re.I)
	if m:
		r = f'https://loom.com/share/{m.group(1)}'
	else:
		r = u
	return r
def detect_client_videos(description: str='', document_markdowns: list[str] | tuple[str, ...]=(), saved_attachments: list[dict] | tuple[dict, ...]=()) -> list[dict]:
	from pathlib import Path
	videos: list[dict] = []
	seen_keys: set[str] = set()
	for text in [description or '', *(document_markdowns or ())]:
		for match in _VIDEO_URL_RE.finditer(text or ''):
			raw_url = match.group(0).rstrip('.,;!)')
			canon = canonical_video_url(raw_url)
			if canon in seen_keys:
				continue
			seen_keys.add(canon)
			loom_m = re.match('^https?://(?:www\\.)?loom\\.com/share/([A-Za-z0-9]+)', canon, re.I)
			videos.append({'kind': 'loom' if loom_m else 'url', 'video_id': loom_m.group(1) if loom_m else None, 'url': canon, 'raw_url': raw_url, 'label': canon, 'heading': f'Description in {canon}'})
	for item in saved_attachments or []:
		name = Path(item.get('filename') or item.get('name') or item.get('file') or '').name
		if not name:
			continue
		if 'video' == classify_attachment(name):
			key = f'file:{name}'
			if key in seen_keys:
				continue
			seen_keys.add(key)
			videos.append({'kind': 'file', 'video_id': item.get('sha256'), 'filename': name, 'sha256': item.get('sha256'), 'label': f'`{name}`', 'heading': f'Description in `{name}`'})
	r = videos
	return r
def format_duration_ru(seconds: int | float | None) -> str:
	if not seconds or seconds <= 0:
		r = 'duration not specified'
	else:
		total = int(round(float(seconds)))
		mm, ss = divmod(total, 60)
		if mm > 0 and ss > 0:
			r = f'{mm} min {ss} sec'
		elif mm > 0:
			r = f'{mm} min'
		else:
			r = f'{ss} sec'
	return r
def parse_webvtt_phrases(vtt_text: str) -> list[dict]:
	phrases: list[dict] = []
	blocks = re.split('\\r?\\n\\r?\\n', (vtt_text or '').strip())
	for block in blocks:
		lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
		if not lines or lines[0].startswith('WEBVTT'):
			continue
		ts_line = next((ln for ln in lines if '-->' in ln), None)
		if not ts_line:
			continue
		m = re.match('^(?:(\\d+):)?(\\d{2}):(\\d{2})[.,]\\d+\\s*-->', ts_line)
		if not m:
			continue
		hh = int(m.group(1) or 0)
		mm = int(m.group(2)) + hh * 60
		ss = int(m.group(3))
		idx = lines.index(ts_line)
		txt = ' '.join((re.sub('<[^>]+>', '', ln).strip() for ln in lines[idx + 1:] if ln.strip())).strip()
		if txt:
			phrases.append({'ts': f'[{mm:02d}:{ss:02d}]', 'seconds': mm * 60 + ss, 'text': txt})
	r = phrases
	return r
def extract_loom_video(url: str, timeout: float=15.0, opener=None) -> dict:
	import json
	from urllib.request import Request, urlopen
	open_fn = opener or (lambda req, tm: urlopen(req, timeout=tm))
	canon = canonical_video_url(url)
	loom_m = re.search('loom\\.com/(?:share|embed)/([A-Za-z0-9]+)', canon, re.I)
	if not loom_m:
		raise ValueError(f'Not a Loom video URL: {url}')
	vid_id = loom_m.group(1)
	share_url = f'https://www.loom.com/share/{vid_id}'
	req = Request(share_url, headers={'User-Agent': 'Mozilla/5.0'})
	with open_fn(req, timeout) as resp:
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
	if tdetails.get('source_url'):
		with open_fn(Request(tdetails['source_url'], headers={'User-Agent': 'Mozilla/5.0'}), timeout) as tresp:
			tdata = json.loads(tresp.read().decode('utf-8', errors='replace'))
		for p in tdata.get('phrases') or []:
			val = (p.get('value') or '').strip()
			if not val:
				continue
			sec = int(float(p.get('ts') or 0))
			mm, ss = divmod(sec, 60)
			phrases.append({'ts': f'[{mm:02d}:{ss:02d}]', 'seconds': sec, 'text': val})
	elif tdetails.get('captions_source_url'):
		with open_fn(Request(tdetails['captions_source_url'], headers={'User-Agent': 'Mozilla/5.0'}), timeout) as vresp:
			vtt_text = vresp.read().decode('utf-8', errors='replace')
		phrases = parse_webvtt_phrases(vtt_text)
	transcript_lines = [f"{p['ts']} {p['text']}" for p in phrases]
	dur_str = format_duration_ru(duration_sec)
	speaker_str = f'Speaker: {speaker} ({dur_str}).' if speaker else f'Recording duration: {dur_str}.'
	title_str = f' Recording title: «{title}».' if title else ''
	mode_str = ' Recording format: screen share and speaker webcam (screen_cam).' if 'screen_cam' == screen_type else ''
	video_header = f'{speaker_str}{title_str}{mode_str}'.strip()
	key_points = [f"- ({p['ts'].strip('[]')}) {p['text']}" for p in phrases[:8]] or ['- Spoken commentary is recorded in the full transcript below.']
	md_lines = ['# Video:', video_header, '', '# Key Spoken Commentary Points (Additions to Document Text):', *key_points, '', '# Full Audio Transcript:', *(transcript_lines or ['[00:00] (audio track is absent or contains no speech)'])]
	r = {'kind': 'loom', 'video_id': vid_id, 'url': canon, 'title': title, 'speaker': speaker, 'duration_seconds': duration_sec, 'duration_human': dur_str, 'screen_type': screen_type, 'phrases': phrases, 'markdown': '\n'.join(md_lines)}
	return r
