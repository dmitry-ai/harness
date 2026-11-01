# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
import json
from pathlib import Path
import re
from urllib.parse import unquote, urldefrag, urlsplit
from markdown_it import MarkdownIt
META_REFUTATION_RE = re.compile(
	'(?:^|\\b)(?:'
	'\\u044f\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b|\\u0443\\u043a\\u0430\\u0437\\u0430\\u043b|\\u043e\\u0448\\u0438\\u0431\\u043e\\u0447\\u043d\\u043e|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043b)|'
	'\\u0430\\u0433\\u0435\\u043d\\u0442\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b|\\u0441\\u0444\\u0430\\u0431\\u0440\\u0438\\u043a\\u043e\\u0432\\u0430\\u043b|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043b)|'
	'\\u043c\\u043e\\u0434\\u0435\\u043b\\u044c\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b\\u0430|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b\\u0430|\\u0441\\u0444\\u0430\\u0431\\u0440\\u0438\\u043a\\u043e\\u0432\\u0430\\u043b\\u0430)|'
	'\\u0431\\u044b\\u043b\\u043e\\s+(?:\\u0443\\u043a\\u0430\\u0437\\u0430\\u043d\\u043e|\\u0434\\u043e\\u043f\\u0438\\u0441\\u0430\\u043d\\u043e|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043d\\u043e)|'
	'\\u0431\\u044b\\u043b\\u0438\\s+(?:\\u0443\\u043a\\u0430\\u0437\\u0430\\u043d\\u044b|\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043d\\u044b|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043d\\u044b)|'
	'\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043d\\u0430\\s+(?:\\u0446\\u0438\\u0442\\u0430\\u0442\\u0430|\\u0434\\u0430\\u0442\\u0430|\\u0441\\u0442\\u0440\\u043e\\u043a\\u0430)|'
	'\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043d\\u043d\\w+\\s+(?:\\u043c\\u043d\\u043e\\u0439\\s+)?(?:\\u043f\\u0440\\u0435\\u0434\\u043b\\u043e\\u0436\\u0435\\u043d|\\u0446\\u0438\\u0442\\u0430\\u0442|\\u0441\\u0447\\u0451\\u0442|\\u0441\\u0442\\u0440\\u043e\\u043a|\\u0444\\u0440\\u0430\\u0437)|'
	'\\u0431\\u044b\\u043b\\u0430\\s+\\u0438\\u0441\\u043a\\u0430\\u0436\\u0435\\u043d\\u0430\\s+\\u043a\\u0430\\u043a|\\u044f\\s+\\u043d\\u0430\\u043f\\u0438\\u0441\\u0430\\u043b,\\s+\\u0447\\u0442\\u043e|'
	'\\u043a\\u043e\\u0442\\u043e\\u0440(?:\\u043e\\u0433\\u043e|\\u043e\\u0439|\\u044b\\u0445)\\s+\\u043d\\u0435\\u0442\\s+\\u0432|'
	'\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\u0443(?:\\u0435\\u0442|\\u044e\\u0442|\\u044e\\u0449\\w*)\\s+\\u0432\\s+(?:source|nexcess|evidence|\\u043f\\u0435\\u0440\\u0432\\u043e\\u0438\\u0441\\u0442\\u043e\\u0447\\u043d\\u0438\\u043a)|'
	'\\u0433\\u0430\\u043b\\u043b\\u044e\\u0446\\u0438\\u043d\\u0430\\u0446\\w*|'
	'\\u043f\\u0438\\u0437\\u0434\\u043e\\u043d\\u044c\\u043a\\w*|'
	'\\u0441\\u0444\\u0430\\u0431\\u0440\\u0438\\u043a\\u043e\\u0432\\w*|'
	'\\u0432\\s+\\u043e\\u0442\\u0432\\u0435\\u0442(?:\\u0435|\\u0430\\u0445)\\s+`?\\d+`?|'
	'\\bres/\\d+\\.md\\b|\\bresponse-\\d+\\.md\\b|'
	'hallucinat\\w*|fabricat\\w*|absent\\s+from\\s+the\\s+saved|missing\\s+from\\s+source\\.md'
	')',
	re.I,
)
MSG_NUM_RE = re.compile('(?:\\u0441\\u043e\\u043e\\u0431\\u0449\\u0435\\u043d\\u0438[\\u0435\\u044f\\u0438\\u0439\\u044f\\u0445\\u043c]+\\s*(?:\\u2116|#)?\\s*(\\d+)(?:\\s*(?:\\u0438|,|-)\\s*(?:\\u2116|#)?\\s*(\\d+))?|\\bMessage\\s*#?(\\d+)\\b)', re.I)
PAREN_AUTHOR_RE = re.compile('[\\u0410-\\u042f\\u0401][\\u0430-\\u044f\\u0451]+(?:\\s+[\\u0410-\\u042f\\u0401][\\u0430-\\u044f\\u0451]+)+\\s*\\(`([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)+)`\\)')
HASH_ID_RE = re.compile('(?<![/\\w&#])#(\\d{4,})\\b')
DOLLAR_CENT_RE = re.compile('(?<!\\\\)\\$\\s*(\\d[\\d,]*\\.\\d{2})\\b')
SW_VER_RE = re.compile('^((?:PHP|MariaDB|MySQL|Redis|Varnish|Apache|Nginx|OpenSearch|Elasticsearch)\\s+\\d+\\.\\d+\\.\\d+)$')
KERNEL_RE = re.compile('^(\\d+\\.\\d+\\.\\d+-\\d+[\\w.-]+\\.x86_64)$')
DEV_PATH_RE = re.compile('^(/dev/[a-zA-Z0-9/_-]+)$')
METRIC_KV_RE = re.compile('^([a-z][a-z0-9_]{3,}:\\d{3,})$')
def norm_quote_text(value: str) -> str:
	cleaned = re.sub('[`*_~]+', '', value or '')
	cleaned = cleaned.replace('\u00a0', ' ').replace('\u2014', '-').replace('\u2013', '-').replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
	cleaned = re.sub('(?m)^>\\s*', '', cleaned)
	r = ' '.join(cleaned.split()).lower()
	return r
def resolve_local_href(root: Path, href: str, doc_path: Path | None = None) -> Path | None:
	raw = urldefrag((href or '').strip())[0].split('?', 1)[0].strip()
	if not raw or raw.lower().startswith(('http://', 'https://', 'mailto:', 'javascript:', 'conversation://', '#')):
		return None
	if raw.lower().startswith('file://'):
		raw = unquote(raw[7:])
		if re.match('^/[A-Za-z]:/', raw):
			raw = raw[1:]
	else:
		raw = unquote(raw)
	candidates = []
	p = Path(raw)
	if p.is_absolute():
		candidates.append(p)
	else:
		if None is not doc_path:
			candidates.append(doc_path.parent / p)
		candidates.append(Path(root) / p)
	for cand in candidates:
		try:
			res = cand.resolve()
			if res.is_file():
				if None is not doc_path and res == doc_path.resolve():
					return None
				return res
		except OSError:
			continue
	return None
def is_primary_local_source(path: Path) -> bool:
	norm = path.as_posix().lower()
	if 'source.md' == path.name.lower():
		r = True
	elif '/kb/evidence/' in norm and (not norm.endswith('-audit.json')) and ('/evidence/github/' not in norm) and ('/evidence/reviews/' not in norm):
		r = True
	elif norm.endswith(('/kb/project.md', '/kb/projects.md', '/kb/evidence.md')):
		r = True
	else:
		r = False
	return r
def _json_scalar_strings(obj, out: list[str]):
	if isinstance(obj, dict):
		for k, v in obj.items():
			out.append(str(k))
			_json_scalar_strings(v, out)
	elif isinstance(obj, list):
		for item in obj:
			_json_scalar_strings(item, out)
	elif isinstance(obj, float):
		out.append(f'{obj:.2f}')
		out.append(str(obj))
	elif None is not obj:
		out.append(str(obj))
def _load_local_source_info(path: Path, cache: dict) -> dict:
	key = str(path)
	if key in cache:
		return cache[key]
	try:
		raw = path.read_text(encoding='utf-8', errors='replace')
	except OSError:
		raw = ''
	extra = [raw]
	if '.json' == path.suffix.lower() and raw.strip():
		try:
			parsed = json.loads(raw)
			_json_scalar_strings(parsed, extra)
		except ValueError:
			pass
	combined_raw = '\n'.join(extra)
	msg_nums = set()
	is_ticket_source = False
	if 'source.md' == path.name.lower():
		for m in re.finditer('(?m)^##\\s+(\\d+)\\s+[\\u2014\\u2013-]\\s+(.+?)\\s+\\(', raw):
			msg_nums.add(int(m.group(1)))
			is_ticket_source = True
		for m in re.finditer('(?m)^###\\s+Message\\s+#?(\\d+)\\b', raw, re.I):
			msg_nums.add(int(m.group(1)))
			is_ticket_source = True
	has_cyrillic = bool(re.search('[\\u0400-\\u04ff]{3,}', raw))
	ticket_id = path.parent.parent.name if 'kb' == path.parent.name.lower() and re.fullmatch('\\d{6,10}', path.parent.parent.name) else None
	info = {'path': path, 'raw': combined_raw, 'norm': norm_quote_text(combined_raw), 'is_ticket_source': is_ticket_source, 'msg_nums': msg_nums, 'has_cyrillic': has_cyrillic, 'ticket_id': ticket_id}
	cache[key] = info
	return info
def _quote_segments_present(q_raw: str, obs_norm: str, min_seg_len: int = 12) -> bool:
	parts = [norm_quote_text(s) for s in re.split('\\[\\.\\.\\.\\]|\\(\\.\\.\\.\\)|\\[\\u2026\\]|\\(\\u2026\\)|\\.{3,}|\\u2026', q_raw)]
	segs = [s for s in parts if len(s) >= min_seg_len]
	if not segs:
		whole = norm_quote_text(q_raw)
		r = len(whole) < 8 or whole in obs_norm
	else:
		r = all((s in obs_norm for s in segs))
	return r
def _filter_primary_sources(paths: list[Path]) -> list[Path]:
	src_dirs = {p.parent for p in paths if 'source.md' == p.name.lower()}
	r = [p for p in paths if not ('analysis.md' == p.name.lower() and p.parent in src_dirs)]
	return r
def _extract_block_links(block, root: Path, doc_path: Path | None):
	local_all = []
	ext_urls = []
	for tok in block.children or []:
		if 'link_open' == tok.type:
			href = tok.attrGet('href') or ''
			if href.startswith(('http://', 'https://')):
				ext_urls.append(href)
			else:
				rp = resolve_local_href(root, href, doc_path)
				if None is not rp and rp not in local_all:
					local_all.append(rp)
	return (local_all, ext_urls)
def local_source_grounding_issues(root: Path, content: str, *, doc_path: Path | None = None, observed_texts: dict | None = None, _visited: set | None = None) -> list[str]:
	if not content or not isinstance(content, str):
		return []
	root = Path(root).resolve()
	visited = _visited if None is not _visited else set()
	if None is not doc_path:
		doc_path = Path(doc_path).resolve()
		if str(doc_path) in visited:
			return []
		visited.add(str(doc_path))
	errors = []
	cache = {}
	default_sources = []
	if None is not doc_path and 'analysis.md' == doc_path.name.lower() and (doc_path.parent / 'source.md').is_file():
		default_sources = [(doc_path.parent / 'source.md').resolve()]
	parser = MarkdownIt('commonmark', {'html': True})
	parser.normalizeLink = lambda value: value
	parser.validateLink = lambda value: True
	section_sources = list(default_sources)
	section_all_locals = list(default_sources)
	section_ext_urls = []
	quote_depth = 0
	list_depth = 0
	linked_analyses = []
	for block in parser.parse(content):
		if 'heading_open' == block.type:
			section_sources = list(default_sources)
			section_all_locals = list(default_sources)
			section_ext_urls = []
			continue
		if block.type in ('bullet_list_open', 'ordered_list_open'):
			list_depth += 1
			continue
		if block.type in ('bullet_list_close', 'ordered_list_close'):
			list_depth = max(0, list_depth - 1)
			continue
		if 'list_item_open' == block.type and 1 == list_depth:
			section_sources = list(default_sources)
			section_all_locals = list(default_sources)
			section_ext_urls = []
			continue
		if 'blockquote_open' == block.type:
			quote_depth += 1
			continue
		if 'blockquote_close' == block.type:
			quote_depth = max(0, quote_depth - 1)
			continue
		if 'inline' != block.type or not block.content:
			continue
		local_all, ext_urls = _extract_block_links(block, root, doc_path)
		for lp in local_all:
			if 'analysis.md' == lp.name.lower() and (lp.parent / 'source.md').is_file() and (lp not in linked_analyses):
				linked_analyses.append(lp)
		filtered_locals = _filter_primary_sources(local_all)
		primary_here = [p for p in filtered_locals if is_primary_local_source(p)]
		if primary_here:
			section_sources = primary_here
			section_all_locals = filtered_locals
			section_ext_urls = list(ext_urls)
		elif ext_urls and (not section_ext_urls):
			section_ext_urls = list(ext_urls)
		active_primary = primary_here or section_sources or default_sources
		if not active_primary:
			continue
		active_locals = _filter_primary_sources(list(dict.fromkeys(filtered_locals + section_all_locals + active_primary)))
		active_exts = list(dict.fromkeys(ext_urls + section_ext_urls))
		infos = [_load_local_source_info(p, cache) for p in active_locals]
		ext_blobs = []
		if observed_texts:
			for u in active_exts:
				nu = urldefrag(u.strip())[0].rstrip('/')
				for t in observed_texts.get(nu) or []:
					ext_blobs.append(t)
		combined_raw = '\n'.join([inf['raw'] for inf in infos] + ext_blobs)
		combined_norm = norm_quote_text(combined_raw)
		src_label = ', '.join((p.name for p in active_primary[:2]))
		if quote_depth > 0:
			if META_REFUTATION_RE.search(block.content):
				continue
			bq_quotes = re.findall('\\u00ab([^\\u00bb]{8,})\\u00bb', block.content)
			if not bq_quotes:
				m_orig = re.search('(?:\\u041e\\u0440\\u0438\\u0433\\u0438\\u043d\\u0430\\u043b|Original)\\s*:\\s*["\\u00ab]?(.{12,})["\\u00bb]?$', block.content.strip(), re.I | re.S)
				if m_orig:
					bq_quotes = [m_orig.group(1).strip(' "\u00ab\u00bb')]
			for bq in bq_quotes:
				if not _quote_segments_present(bq, combined_norm, 12):
					preview = ' '.join(bq.split())[:80]
					errors.append(f'VERIFY-1 / LINK-1: Blockquote \u00ab{preview}\u00bb attributed to {src_label} is absent from the primary source')
			continue
		ticket_infos = [inf for inf in infos if inf['is_ticket_source']]
		valid_msg_nums = {n for inf in ticket_infos for n in inf['msg_nums']}
		bound_ticket_ids = {inf['ticket_id'] for inf in ticket_infos if inf['ticket_id']}
		any_cyrillic_source = any((inf['has_cyrillic'] for inf in infos))
		for line in block.content.split('\n'):
			sline = line.strip()
			if not sline or META_REFUTATION_RE.search(sline):
				continue
			for bq_str in re.findall('`["\\u201c]([^"\\u201d`]{8,})["\\u201d]`', sline):
				if len(re.findall('[A-Za-z0-9]{2,}', bq_str)) >= 2 and (not _quote_segments_present(bq_str, combined_norm, 8)):
					preview = ' '.join(bq_str.split())[:80]
					errors.append(f'VERIFY-1 / LINK-1: Quoted literal "{preview}" attributed to {src_label} is absent from the primary source')
			sline_for_quotes = re.sub('\\(\\u0430\\s+\\u043d\\u0435\\s+\\u00ab[^\\u00bb]+\\u00bb\\)', ' ', sline, flags=re.I)
			for gq in re.findall('\\u00ab([^\\u00bb]{10,})\\u00bb', sline_for_quotes):
				has_cyr = bool(re.search('[\\u0400-\\u04ff]', gq))
				if not has_cyr:
					if len(re.findall('[A-Za-z0-9]{2,}', gq)) >= 2 and (not _quote_segments_present(gq, combined_norm, 12)):
						preview = ' '.join(gq.split())[:80]
						errors.append(f'VERIFY-1 / LINK-1: Verbatim quote \u00ab{preview}\u00bb attributed to {src_label} is absent from the primary source')
				elif any_cyrillic_source and len(gq.strip()) >= 25 and re.search('(?:\\u043f\\u0438\\u0448\\u0435\\u0442|\\u043d\\u0430\\u043f\\u0438\\u0441\\u0430\\u043b\\w*|\\u0437\\u0430\\u044f\\u0432\\u0438\\u043b\\w*|\\u0441\\u043a\\u0430\\u0437\\u0430\\u043d\\u043e|\\u0446\\u0438\\u0442\\u0430\\u0442\\u0430)\\s*:\\s*\\u00ab', sline, re.I):
					if not _quote_segments_present(gq, combined_norm, 15):
						preview = ' '.join(gq.split())[:80]
						errors.append(f'VERIFY-1 / LINK-1: Verbatim quote \u00ab{preview}\u00bb attributed to {src_label} is absent from the primary source')
			if ticket_infos:
				for m_msg in MSG_NUM_RE.finditer(sline):
					prefix = sline[max(0, m_msg.start() - 45):m_msg.start()]
					other_tickets = [tid for tid in re.findall('\\b(\\d{7,8})\\b', prefix) if tid not in bound_ticket_ids]
					if other_tickets:
						continue
					for g_idx in (1, 2, 3):
						val = m_msg.group(g_idx)
						if val and int(val) not in valid_msg_nums:
							errors.append(f'VERIFY-1 / LINK-1: Cited message #{val} does not exist in {src_label} (available messages: {sorted(valid_msg_nums)})')
				for m_auth in PAREN_AUTHOR_RE.finditer(sline):
					author_name = m_auth.group(1).strip()
					if author_name.lower() not in combined_norm:
						errors.append(f'VERIFY-1 / LINK-1: Cited person "{author_name}" is absent from {src_label}')
			line_no_urls = re.sub('https?://\\S+|\\([^)]*\\)', ' ', sline)
			for m_id in HASH_ID_RE.finditer(line_no_urls):
				ident = m_id.group(1)
				if ident not in combined_raw:
					errors.append(f'VERIFY-1 / DOC-1: Identifier #{ident} attributed to {src_label} is absent from the primary source')
			for m_amt in DOLLAR_CENT_RE.finditer(line_no_urls):
				amt_raw = m_amt.group(1)
				amt_clean = amt_raw.replace(',', '')
				if amt_raw not in combined_raw and amt_clean not in combined_raw:
					errors.append(f'VERIFY-1 / DOC-1: Currency amount ${amt_raw} attributed to {src_label} is absent from the primary source')
			for code_span in re.findall('`([^`\\n]{3,60})`', sline):
				c_strip = code_span.strip()
				for pat, kind_name in ((SW_VER_RE, 'Version literal'), (KERNEL_RE, 'Kernel version'), (DEV_PATH_RE, 'Device path'), (METRIC_KV_RE, 'Metric literal')):
					m_lit = pat.match(c_strip)
					if m_lit:
						lit_val = m_lit.group(1)
						if norm_quote_text(lit_val) not in combined_norm and lit_val.lower() not in combined_raw.lower():
							errors.append(f'VERIFY-1 / DOC-1: {kind_name} `{lit_val}` attributed to {src_label} is absent from the primary source')
	for ap in linked_analyses:
		try:
			a_text = ap.read_text(encoding='utf-8')
		except OSError:
			continue
		sub_errs = local_source_grounding_issues(root, a_text, doc_path=ap, observed_texts=observed_texts, _visited=visited)
		for se in sub_errs[:5]:
			errors.append(f'Linked {ap.parent.parent.name}/{ap.name} -> {se}')
	r = list(dict.fromkeys(errors))
	return r
