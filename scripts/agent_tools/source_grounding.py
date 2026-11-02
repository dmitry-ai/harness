# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urldefrag, urlsplit
from markdown_it import MarkdownIt
from .claims import standalone_numbers
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
RELATIONAL_MOD_RE = re.compile(
	'(?i)(?:'
	'modified\\s+directly\\s+inside|'
	'unofficial\\s+core\\s+modification|'
	'custom\\s+modification\\s+in\\s+`?vendor/|'
	'was\\s+modified\\s+in\\s+`?vendor/|'
	'differs\\s+from\\s+(?:the\\s+)?(?:clean|standard|default)\\s+distribution|'
	'\\u0432\\u043d\\u0435\\u0441\\u0435\\u043d\\u0430\\s+(?:\\u0441\\u0442\\u043e\\u0440\\u043e\\u043d\\u043d\\u044f\\u044f|\\u043a\\u0430\\u0441\\u0442\\u043e\\u043c\\u043d\\u0430\\u044f)\\s+\\u043f\\u0440\\u0430\\u0432\\u043a\\u0430|'
	'\\u043d\\u0435\\u0441\\u0442\\u0430\\u043d\\u0434\\u0430\\u0440\\u0442\\u043d\\w+\\s+(?:\\u043c\\u043e\\u0434\\u0438\\u0444\\u0438\\u043a\\u0430\\u0446\\w+|\\u043f\\u0440\\u0430\\u0432\\u043a\\w+|\\u0438\\u0437\\u043c\\u0435\\u043d\\w+)'
	')'
)
EN_FUNCTION_WORDS = {
	'the', 'and', 'for', 'that', 'with', 'this', 'from', 'not', 'are', 'was', 'were', 'have', 'has', 'had',
	'but', 'when', 'where', 'which', 'while', 'into', 'only', 'also', 'after', 'before', 'because', 'between',
	'through', 'during', 'without', 'under', 'within', 'should', 'would', 'could', 'cannot', 'does', 'did',
	'will', 'can', 'may', 'each', 'every', 'both', 'either', 'neither', 'instead', 'however', 'therefore',
	'although', 'whether', 'if', 'in', 'on', 'at', 'to', 'of', 'by', 'as', 'is', 'be', 'or', 'an', 'it',
	'via', 'per', 'fix', 'use', 'add', 'remove', 'update', 'check', 'verify', 'ensure', 'cause', 'issue',
	'error', 'file', 'line', 'lines', 'code', 'method', 'function', 'class', 'problem', 'solution', 'summary',
	'root', 'work', 'across', 'seconds', 'valid', 'test', 'title', 'body', 'page', 'pages', 'request',
}
NON_EN_LATIN_STOPWORDS = {
	'und', 'der', 'die', 'das', 'nicht', 'ist', 'mit', 'auf', 'eine', 'einem', 'wird', 'wurde', 'sind', 'oder',
	'que', 'para', 'con', 'una', 'por', 'los', 'las', 'del', 'como', 'pero', 'esta', 'este', 'son', 'fue',
	'les', 'des', 'une', 'dans', 'pour', 'sur', 'avec', 'pas', 'sont', 'plus', 'cette', 'mais', 'ont',
	'non', 'della', 'delle', 'degli', 'nella', 'sono', 'anche', 'questo', 'questa', 'come',
	'jest', 'nie', 'oraz', 'czy', 'jak', 'przy', 'tylko', 'przez', 'jego', 'tego',
	'bir', 'veya', 'olarak', 'ancak', 'sonra', 'kadar', 'gibi', 'daha', 'चूंकि',
}
ALLOWED_MATH_GREEK = {'α', 'β', 'γ', 'δ', 'ε', 'λ', 'μ', 'π', 'σ', 'τ', 'φ', 'ω', 'Δ', 'Σ', 'Ω'}
def _char_script(ch: str) -> str:
	name = unicodedata.name(ch, '')
	if not name:
		return 'UNKNOWN'
	head = name.split()[0]
	if head in ('CJK', 'IDEOGRAPHIC', 'HIRAGANA', 'KATAKANA', 'HANGUL'):
		return 'CJK'
	return head
def extract_authored_prose(text: str, *, is_title: bool = False) -> str:
	if not isinstance(text, str) or not text.strip():
		return ''
	if is_title:
		clean = re.sub('`[^`]*`', ' ', text)
		clean = re.sub('\\u00ab[^\\u00bb]*\\u00bb|\u201c[^\u201d]*\u201d|"[^"]*"', ' ', clean)
		clean = re.sub('https?://\\S+|file://\\S+', ' ', clean)
		return ' '.join(clean.split())
	parser = MarkdownIt('commonmark', {'html': True})
	quote_depth = 0
	chunks = []
	for token in parser.parse(text):
		if 'blockquote_open' == token.type:
			quote_depth += 1
			continue
		if 'blockquote_close' == token.type:
			quote_depth = max(0, quote_depth - 1)
			continue
		if quote_depth > 0 or token.type in ('fence', 'code_block', 'html_block'):
			continue
		if 'inline' == token.type and token.children:
			in_link = 0
			for child in token.children:
				if 'link_open' == child.type:
					in_link += 1
					continue
				if 'link_close' == child.type:
					in_link = max(0, in_link - 1)
					continue
				if 'text' == child.type:
					val = child.content or ''
					if in_link and re.match('^(?:https?://|file://|[A-Za-z]:/|/)', val.strip()):
						continue
					chunks.append(val)
	joined = ' '.join(chunks)
	joined = re.sub('\\u00ab[^\\u00bb]*\\u00bb|\u201c[^\u201d]*\u201d|"[^"\\n]{8,}"', ' ', joined)
	joined = re.sub('https?://\\S+|file://\\S+', ' ', joined)
	joined = re.sub('(?<![A-Za-z0-9])[A-Za-z]:/[^\\s)\\]>]+', ' ', joined)
	return ' '.join(joined.split())
def detect_prose_locale(prose: str) -> dict:
	script_counts: dict[str, int] = {}
	for ch in prose or '':
		if ch.isalpha():
			if ch in ALLOWED_MATH_GREEK:
				continue
			sc = _char_script(ch)
			script_counts[sc] = script_counts.get(sc, 0) + 1
	total_alpha = sum(script_counts.values())
	if 0 == total_alpha:
		return {'dominant_script': 'NONE', 'dominant_ratio': 1.0, 'total_alpha': 0, 'script_counts': {}, 'locale_family': 'und'}
	dominant_script = max(script_counts.items(), key=lambda item: item[1])[0]
	dominant_ratio = script_counts[dominant_script] / total_alpha
	words = [w.lower() for w in re.findall('[[:alpha:]]{2,}' if False else '[^\\W\\d_]{2,}', prose, flags=re.UNICODE)]
	en_hits = sum((1 for w in words if w in EN_FUNCTION_WORDS))
	non_en_hits = sum((1 for w in words if w in NON_EN_LATIN_STOPWORDS))
	diacritic_words = sum((1 for w in words if any((ord(c) > 127 and 'LATIN' == _char_script(c) for c in w))))
	if 'LATIN' != dominant_script:
		locale_family = dominant_script.lower()
	elif len(words) >= 6 and (non_en_hits > en_hits or (0 == en_hits and diacritic_words >= 2)):
		locale_family = 'latin-non-en'
	else:
		locale_family = 'en'
	return {
		'dominant_script': dominant_script,
		'dominant_ratio': dominant_ratio,
		'total_alpha': total_alpha,
		'script_counts': script_counts,
		'word_count': len(words),
		'en_hits': en_hits,
		'non_en_hits': non_en_hits,
		'diacritic_words': diacritic_words,
		'locale_family': locale_family,
	}
def verify_target_locale(text: str, *, target_locale: str = 'en-US', container_text: str | None = None, is_title: bool = False) -> list[dict]:
	errors: list[dict] = []
	eff_target = (target_locale or 'en-US').strip()
	if container_text and isinstance(container_text, str) and container_text.strip():
		c_prose = extract_authored_prose(container_text, is_title=False)
		c_info = detect_prose_locale(c_prose)
		if c_info['total_alpha'] >= 12 and 'NONE' != c_info['dominant_script']:
			if 'LATIN' == c_info['dominant_script'] and 'en' == c_info['locale_family']:
				eff_target = 'en-US'
			elif 'LATIN' != c_info['dominant_script']:
				eff_target = c_info['dominant_script'].lower()
	prose = extract_authored_prose(text, is_title=is_title)
	info = detect_prose_locale(prose)
	if 0 == info['total_alpha']:
		return errors
	if eff_target.lower().startswith('en'):
		non_latin = {sc: cnt for sc, cnt in info['script_counts'].items() if 'LATIN' != sc and cnt >= 2}
		if non_latin:
			bad_scripts = ', '.join((f'{sc} ({cnt} chars)' for sc, cnt in sorted(non_latin.items())))
			errors.append({
				'code': 'LOCALE_MISMATCH',
				'target_locale': eff_target,
				'detected_scripts': non_latin,
				'message': f'TEXT-1: Authored prose contains non-Latin script characters [{bad_scripts}] in a target "{eff_target}" container; write in {eff_target} and place foreign logs/quotes inside fenced code blocks or blockquotes',
			})
		elif 'latin-non-en' == info['locale_family'] and info['word_count'] >= 6:
			errors.append({
				'code': 'LOCALE_MISMATCH',
				'target_locale': eff_target,
				'detected_locale': info['locale_family'],
				'message': f'TEXT-1: Authored prose is in a non-English Latin language (en_hits={info["en_hits"]}, non_en_hits={info["non_en_hits"]}, diacritic_words={info["diacritic_words"]}) in a target "{eff_target}" container',
			})
	else:
		expected_script = eff_target.upper()
		target_chars = info['script_counts'].get(expected_script, 0)
		if info['total_alpha'] >= 15 and target_chars / info['total_alpha'] < 0.35:
			errors.append({
				'code': 'LOCALE_MISMATCH',
				'target_locale': eff_target,
				'detected_script': info['dominant_script'],
				'message': f'TEXT-1: Target container/request script is {expected_script}, but authored prose is predominantly {info["dominant_script"]} ({target_chars}/{info["total_alpha"]} target script chars)',
			})
	return errors
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
	elif '/source/' in norm and 'analysis.md' != path.name.lower():
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
def _source_numeric_tokens(raw_text: str) -> set[str]:
	nums = set()
	for tok in re.findall('\\d+(?:[.,]\\d+)*', raw_text or ''):
		norm_dot = tok.replace(',', '.')
		no_comma = tok.replace(',', '')
		nums.add(norm_dot)
		nums.add(no_comma)
		nums.update(norm_dot.split('.'))
		nums.update(no_comma.split('.'))
		if '.' in no_comma:
			nums.add(no_comma.rstrip('0').rstrip('.') or '0')
	return nums
def _load_local_source_info(path: Path, cache: dict) -> dict:
	key = str(path)
	if key in cache:
		return cache[key]
	try:
		raw_bytes = path.read_bytes()
		raw = raw_bytes.decode('utf-8', errors='replace')
		sha256 = hashlib.sha256(raw_bytes).hexdigest()
	except OSError:
		raw_bytes = b''
		raw = ''
		sha256 = ''
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
	info = {
		'path': path,
		'sha256': sha256,
		'raw': combined_raw,
		'norm': norm_quote_text(combined_raw),
		'nums': _source_numeric_tokens(combined_raw),
		'is_ticket_source': is_ticket_source,
		'msg_nums': msg_nums,
		'has_cyrillic': has_cyrillic,
		'ticket_id': ticket_id,
	}
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
	line_locator_nums = set()
	for tok in block.children or []:
		if 'link_open' == tok.type:
			href = tok.attrGet('href') or ''
			frag = urldefrag(href)[1]
			for ln in re.findall('\\d+', frag):
				line_locator_nums.add(ln)
			if href.startswith(('http://', 'https://')):
				ext_urls.append(href)
			else:
				rp = resolve_local_href(root, href, doc_path)
				if None is not rp and rp not in local_all:
					local_all.append(rp)
	return (local_all, ext_urls)
def _line_grounded_numbers_check(sline: str, ev_nums: set[str], valid_msg_nums: set[int], bound_ticket_ids: set[str], is_ticket: bool) -> list[str]:
	missing = []
	if is_ticket:
		for m_msg in re.finditer('(?:\\u0441\\u043e\\u043e\\u0431\\u0449\\u0435\\u043d\\u0438[\\u0435\\u044f\\u0438\\u0439\\u044f\\u0445\\u043c]+\\s*(?:\\u2116|#)?\\s*(\\d+)(?:\\s*(?:\\u0438|,|-)\\s*(?:\\u2116|#)?\\s*(\\d+))?|\\bMessage\\s*#?(\\d+)\\b)', sline, re.I):
			prefix = sline[max(0, m_msg.start() - 45):m_msg.start()]
			other_tickets = [tid for tid in re.findall('\\b(\\d{7,8})\\b', prefix) if tid not in bound_ticket_ids]
			if other_tickets:
				continue
			for g_idx in (1, 2, 3):
				val = m_msg.group(g_idx)
				if val and int(val) not in valid_msg_nums:
					missing.append(f'message #{val} (available: {sorted(valid_msg_nums)})')
	cleaned = re.sub('\\[[^\\]]*\\]\\([^)]*\\)', ' ', sline)
	cleaned = re.sub('https?://\\S+|file://\\S+', ' ', cleaned)
	cleaned = cleaned.replace('`', ' ')
	cleaned = re.sub('\\b\\d+(?:[.,]\\d+)?\\s*%', ' ', cleaned)
	cleaned = re.sub('(?i)\\b(?:line|lines|\\u0441\\u0442\\u0440\\u043e\\u043a\\w*)\\s+\\d+(?:\\s*[\\u2013\\u2014-]\\s*\\d+)?', ' ', cleaned)
	for num in sorted(standalone_numbers(cleaned)):
		norm_num = num.replace(',', '')
		if len(norm_num) == 1 and norm_num.isdigit():
			continue
		if num not in ev_nums and norm_num not in ev_nums:
			missing.append(num)
	return missing
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
	if None is not doc_path and (doc_path.parent / 'source.md').is_file() and 'source.md' != doc_path.name.lower():
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
		if RELATIONAL_MOD_RE.search(block.content) and (not META_REFUTATION_RE.search(block.content)):
			rel_operands = list(dict.fromkeys(filtered_locals + section_all_locals))
			if len(rel_operands) + len(ext_urls) < 2:
				errors.append('VERIFY-1 / LINK-1: Relational modification claim requires at least two distinct primary source operands (observed file and baseline reference), but fewer than 2 sources are linked')
			elif len(rel_operands) >= 2:
				op_hashes = {_load_local_source_info(p, cache)['sha256'] for p in rel_operands if _load_local_source_info(p, cache)['sha256']}
				if 1 == len(op_hashes):
					errors.append('VERIFY-1 / LINK-1: Relational modification claim is refuted because the linked local source operands are byte-identical (matching SHA-256)')
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
		ev_nums = set().union(*(inf['nums'] for inf in infos)) if infos else set()
		if ext_blobs:
			ev_nums.update(_source_numeric_tokens('\n'.join(ext_blobs)))
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
				for m_auth in re.finditer('[\\u0410-\\u042f\\u0401][\\u0430-\\u044f\\u0451]+(?:\\s+[\\u0410-\\u042f\\u0401][\\u0430-\\u044f\\u0451]+)+\\s*\\(`([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)+)`\\)', sline):
					author_name = m_auth.group(1).strip()
					if author_name.lower() not in combined_norm:
						errors.append(f'VERIFY-1 / LINK-1: Cited person "{author_name}" is absent from {src_label}')
			for ungrounded_num in _line_grounded_numbers_check(sline, ev_nums, valid_msg_nums, bound_ticket_ids, bool(ticket_infos)):
				errors.append(f'VERIFY-1 / DOC-1: Unverified numeric figure or identifier ({ungrounded_num}) attributed to {src_label} is absent from the primary source')
			for code_span in re.findall('`([^`\\n]{3,60})`', sline):
				c_strip = code_span.strip()
				if re.match('^(?:/dev/[A-Za-z0-9/_-]+|[a-z][a-z0-9_]{3,}:\\d{3,}|[A-Za-z][A-Za-z0-9_.-]+\\s+\\d+\\.\\d+(?:\\.\\d+)*(?:-[A-Za-z0-9._-]+)?)$', c_strip):
					if norm_quote_text(c_strip) not in combined_norm and c_strip.lower() not in combined_raw.lower():
						errors.append(f'VERIFY-1 / DOC-1: Technical literal `{c_strip}` attributed to {src_label} is absent from the primary source')
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
