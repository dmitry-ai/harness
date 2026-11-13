# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify quote normalization, MarkdownIt link/quote traversal, locale checks, numeric corpus tokenization, and Evidence loading across response_grounding.py, completion.py, source_grounding.py, claims.py, and review.py":
# https://github.com/dmitry-ai/harness/issues/59
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Fix Antigravity executor/generation model mismatch in native-review-proof, decouple post-finalize deliverable reviews from initial Analysis.json, cache source grounding, and preserve journal recording on gate failure":
# https://github.com/dmitry-ai/harness/issues/51
# 2026-11-10 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce local_source_grounding_issues across touched client deliverables, require post-compaction re-read of evicted tool outputs, and close A.A review bypass":
# https://github.com/dmitry-ai/harness/issues/50
# 2026-11-01 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate local/external quote, metric, and identifier fabrication via local source grounding, Stop hook, fresh-read provenance, and A.A audit gates":
# https://github.com/dmitry-ai/harness/issues/34
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace special-case grounding/locale regexes with universal locale, relational claim arity, standalone-number, capability, and review gates":
# https://github.com/dmitry-ai/harness/issues/37
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce typed source provenance tiers (Tier 0/1/2), entity Tier 0 auto-discovery, and post-CHECKPOINT re-read gates":
# https://github.com/dmitry-ai/harness/issues/45
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urldefrag, urlsplit
from markdown_it import MarkdownIt
from .claims import extract_verified_inline_calc_numbers, source_numeric_tokens, standalone_numbers
META_REFUTATION_RE = re.compile(
	'(?:^|\\b)(?:'
	'\\u044f\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b|\\u0443\\u043a\\u0430\\u0437\\u0430\\u043b|\\u043e\\u0448\\u0438\\u0431\\u043e\\u0447\\u043d\\u043e|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043b)|'
	'\\u0430\\u0433\\u0435\\u043d\\u0442\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b|\\u0441\\u0444\\u0430\\u0431\\u0440\\u0438\\u043a\\u043e\\u0432\\u0430\\u043b|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043b)|'
	'\\u043c\\u043e\\u0434\\u0435\\u043b\\u044c\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b\\u0430|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b\\u0430|\\u0441\\u0444\\u0430\\u0431\\u0440\\u0438\\u043a\\u043e\\u0432\\u0430\\u043b\\u0430)|'
	'\\u0431\\u044b\\u043b\\u043e\\s+(?:\\u0443\\u043a\\u0430\\u0437\\u0430\\u043d\\u043e|\\u0434\\u043e\\u043f\\u0438\\u0441\\u0430\\u043d\\u043e|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043d\\u043e)|'
	'\\u0431\\u044b\\u043b\\u0438\\s+(?:\\u0443\\u043a\\u0430\\u0437\\u0430\\u043d\\u044b|\\u00ab?\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043d\\u044b|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043d\\u044b)|'
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
	'\\u043d\\u0435\\u0441\\u0442\\u0430\\u043d\\u0434\\u0430\\u0440\\u0442\\w+\\s+(?:\\u043c\\u043e\\u0434\\u0438\\u0444\\u0438\\u043a\\u0430\\u0446\\w+|\\u043f\\u0440\\u0430\\u0432\\u043a\\w+|\\u0438\\u0437\\u043c\\u0435\\u043d\\w+)'
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
	parser = markdown_parser()
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
def verify_target_locale(text: str, *, target_locale: str = 'en-US', container_text: str | None = None, is_title: bool = False, allow_explicit_english_request: bool = False, min_target_ratio: float = 0.35, min_alpha: int = 15) -> list[dict]:
	r: list[dict] = []
	eff_target = (target_locale or 'en-US').strip()
	if container_text and isinstance(container_text, str) and container_text.strip():
		if allow_explicit_english_request and re.search('(?i)\\b(?:in\\s+english|translate\\s+to\\s+english|\\u043d\\u0430\\s+\\u0430\\u043d\\u0433\\u043b\\u0438\\u0439\\u0441\\u043a\\u043e\\u043c|\\u043f\\u043e-\\u0430\\u043d\\u0433\\u043b\\u0438\\u0439\\u0441\\u043a\\u043e\\u043c|\\u043f\\u043e-\\u0430\\u043d\\u0433\\u043b\\u0438\\u0439\\u0441\\u043a\\u0438)\\b', container_text):
			eff_target = 'und'
		else:
			c_info = detect_prose_locale(extract_authored_prose(container_text, is_title=False))
			if 'und' == eff_target.lower():
				c_dom = c_info['dominant_script']
				if c_dom not in ('NONE', 'LATIN') and 6 <= c_info['script_counts'].get(c_dom, 0):
					eff_target = c_dom.lower()
			elif 12 <= c_info['total_alpha'] and 'NONE' != c_info['dominant_script']:
				if 'LATIN' == c_info['dominant_script'] and 'en' == c_info['locale_family']:
					eff_target = 'en-US'
				elif 'LATIN' != c_info['dominant_script']:
					eff_target = c_info['dominant_script'].lower()
	info = detect_prose_locale(extract_authored_prose(text, is_title=is_title))
	if 0 < info['total_alpha'] and 'und' != eff_target.lower():
		if not eff_target.lower().startswith('en'):
			expected_script = eff_target.upper()
			target_chars = info['script_counts'].get(expected_script, 0)
			if min_alpha <= info['total_alpha'] and target_chars / info['total_alpha'] < min_target_ratio:
				r.append({'code': 'LOCALE_MISMATCH', 'target_locale': eff_target, 'detected_script': info['dominant_script'], 'message': f'TEXT-1: Target container/request script is {expected_script}, but authored prose is predominantly {info["dominant_script"]} ({target_chars}/{info["total_alpha"]} target script chars)'})
		else:
			non_latin = {sc: cnt for sc, cnt in info['script_counts'].items() if 'LATIN' != sc and 2 <= cnt}
			if non_latin:
				bad_scripts = ', '.join((f'{sc} ({cnt} chars)' for sc, cnt in sorted(non_latin.items())))
				r.append({'code': 'LOCALE_MISMATCH', 'target_locale': eff_target, 'detected_scripts': non_latin, 'message': f'TEXT-1: Authored prose contains non-Latin script characters [{bad_scripts}] in a target "{eff_target}" container; write in {eff_target} and place foreign logs/quotes inside fenced code blocks or blockquotes'})
			elif 'latin-non-en' == info['locale_family'] and 6 <= info['word_count']:
				r.append({'code': 'LOCALE_MISMATCH', 'target_locale': eff_target, 'detected_locale': info['locale_family'], 'message': f'TEXT-1: Authored prose is in a non-English Latin language (en_hits={info["en_hits"]}, non_en_hits={info["non_en_hits"]}, diacritic_words={info["diacritic_words"]}) in a target "{eff_target}" container'})
	return r
def markdown_parser() -> MarkdownIt:
	r = MarkdownIt('commonmark', {'html': True})
	r.normalizeLink = lambda value: value
	r.validateLink = lambda value: True
	return r
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
def is_normative_harness_doc(path: Path) -> bool:
	norm = '/' + path.as_posix().lower().lstrip('/')
	return '/.agents/rules/' not in norm and any((seg in norm for seg in ('/rules/', '/skills/', '/references/', '/platforms/')))
_is_normative_harness_doc = is_normative_harness_doc
def classify_provenance_tier(path: Path, root: Path | None = None) -> str:
	norm = '/' + path.as_posix().lower().lstrip('/')
	name = path.name.lower()
	if (
		name in {'draft.md', 'draft.prev.md', 'context.md'}
		or '/.agents/rules/' in norm
		or '/rules/' in norm
		or '/skills/' in norm
		or '/references/' in norm
		or '/platforms/' in norm
		or '/candidates/' in norm
		or '/data/scratch/' in norm
		or '/evidence/reviews/' in norm
		or '/res/' in norm
		or norm.endswith('-audit.json')
	):
		return 'tier_2'
	if (
		'source.md' == name
		or ('/source/' in norm and 'analysis.md' != name)
		or ('/kb/evidence/' in norm and (not norm.endswith('-audit.json')) and ('/evidence/github/' not in norm) and ('/evidence/reviews/' not in norm))
		or norm.endswith(('/kb/project.md', '/kb/projects.md', '/kb/evidence.md'))
		or '/req/' in norm
	):
		return 'tier_0'
	return 'tier_1'
def is_primary_local_source(path: Path) -> bool:
	tier = classify_provenance_tier(path)
	if 'tier_2' == tier:
		return False
	norm = path.as_posix().lower()
	if 'tier_0' == tier:
		return True
	return norm.endswith(('/kb/project.md', '/kb/projects.md', '/kb/evidence.md'))
_SOURCE_INFO_CACHE: dict[tuple[str, int, int], dict] = {}
_TIER0_INDEX_CACHE: dict[str, dict[str, dict]] = {}
_TIER0_TEXT_SUFFIXES = {'.md', '.txt', '.json', '.yaml', '.yml', '.xml', '.csv', '.ini', '.conf', '.env', '.log', ''}
_TIER0_MAX_FILE_BYTES = 512 * 1024
def _tier0_candidate_files(root: Path, tickets: list[str] | tuple[str, ...] = ()) -> list[Path]:
	candidates: list[Path] = []
	seen: set[Path] = set()
	for sub in ('ꘖ/KB/Evidence', 'source', 'KB', 'tickets'):
		base = root / sub
		if base.is_dir():
			for dirpath, dirs, filenames in os.walk(base):
				dirs[:] = sorted((d for d in dirs if d.lower() not in ('http', 'reviews', 'github')))
				dpath = Path(dirpath)
				for fname in sorted(filenames):
					pname = fname.lower()
					p = dpath / fname
					if p.suffix.lower() not in _TIER0_TEXT_SUFFIXES or pname.startswith('extracted-') or 'observation.json' == pname:
						continue
					try:
						if p.stat().st_size > _TIER0_MAX_FILE_BYTES:
							continue
					except OSError:
						continue
					if 'tier_0' == classify_provenance_tier(p, root):
						rp = p.resolve()
						if rp not in seen:
							seen.add(rp)
							candidates.append(rp)
	for p in sorted(root.glob('*/KB/source.md')):
		if p.is_file():
			rp = p.resolve()
			if rp not in seen:
				seen.add(rp)
				candidates.append(rp)
	for tid in tickets:
		for t_cand in (
			root / tid / 'KB' / 'source.md',
			root / tid / 'source.md',
			root / 'tickets' / tid / 'KB' / 'source.md',
			root / 'tickets' / tid / 'source.md',
		):
			if t_cand.is_file():
				rp = t_cand.resolve()
				if rp not in seen:
					seen.add(rp)
					candidates.append(rp)
	return candidates
def _get_tier0_file_entry(root: Path, rp: Path, mem_idx: dict[str, dict]) -> tuple[str, dict | None, bool]:
	try:
		st = rp.stat()
		mtime_ns, size = (st.st_mtime_ns, st.st_size)
	except OSError:
		return ('', None, False)
	try:
		rel = rp.relative_to(root).as_posix()
	except ValueError:
		rel = rp.as_posix()
	cached = mem_idx.get(rel)
	if isinstance(cached, dict) and cached.get('mtime_ns') == mtime_ns and cached.get('size') == size and isinstance(cached.get('sha256'), str):
		return (rel, cached, False)
	try:
		raw_bytes = rp.read_bytes()
		raw = raw_bytes.decode('utf-8', errors='replace')
	except OSError:
		return (rel, None, False)
	raw_lower = raw.lower()
	plans_norm = sorted({' '.join(m.group(0).split()).upper() for m in re.finditer('\\b(?:M[1-9]|Plan\\s+(?:XS|S|M|L|XL|XXL))\\b', raw, re.I)})
	metrics_found = sorted({m.group(0).lower() for m in re.finditer('\\b(?:mem_total|vcpu|cpus|swap_total|load\\s+average)\\b', raw, re.I)} | {mt for mt in ('mem_total', 'vcpu', 'cpus', 'swap_total', 'load average') if mt in raw_lower})
	entry = {
		'mtime_ns': mtime_ns,
		'size': size,
		'sha256': hashlib.sha256(raw_bytes).hexdigest(),
		'tickets': sorted(set(re.findall('\\b(\\d{6,10})\\b', raw))),
		'plans_norm': plans_norm,
		'metrics': metrics_found,
		'fact_tuples': extract_fact_tuples(rp, raw, root=root),
	}
	mem_idx[rel] = entry
	return (rel, entry, True)
def _load_tier0_index(root: Path, tickets: list[str] | tuple[str, ...] = ()) -> tuple[list[Path], dict[str, dict]]:
	root = Path(root).resolve()
	rkey = str(root)
	mem_idx = _TIER0_INDEX_CACHE.get(rkey)
	cache_file = root / 'ꘖ' / 'data' / 'grounding-cache.json'
	if None is mem_idx:
		mem_idx = {}
		if cache_file.is_file():
			try:
				loaded = json.loads(cache_file.read_text(encoding='utf-8'))
				if isinstance(loaded, dict) and isinstance(loaded.get('files'), dict):
					mem_idx = loaded['files']
			except (OSError, ValueError):
				mem_idx = {}
		_TIER0_INDEX_CACHE[rkey] = mem_idx
	candidates = _tier0_candidate_files(root, tickets)
	dirty = False
	for rp in candidates:
		_, _, changed = _get_tier0_file_entry(root, rp, mem_idx)
		if changed:
			dirty = True
	if dirty and (cache_file.parent.is_dir() or (root / 'ꘖ').is_dir()):
		try:
			cache_file.parent.mkdir(parents=True, exist_ok=True)
			cache_file.write_text(json.dumps({'version': 1, 'files': mem_idx}, ensure_ascii=False) + '\n', encoding='utf-8')
		except OSError:
			pass
	return (candidates, mem_idx)
def discover_entity_tier0_sources(root: Path, text: str) -> list[dict]:
	if not text or not isinstance(text, str):
		return []
	root = Path(root).resolve()
	tickets = sorted(set(re.findall('\\b(\\d{6,10})\\b', text)))
	plans = sorted({m.group(0).strip() for m in re.finditer('\\b(?:M[1-9]|Plan\\s+(?:XS|S|M|L|XL|XXL))\\b', text, re.I)})
	metrics = sorted({m.group(0).lower() for m in re.finditer('\\b(?:mem_total|vcpu|cpus|swap_total|load\\s+average)\\b', text, re.I)})
	if not (tickets or plans or metrics):
		return []
	candidates, mem_idx = _load_tier0_index(root, tickets)
	discovered = []
	for rp in candidates:
		try:
			rel = rp.relative_to(root).as_posix()
		except ValueError:
			rel = rp.as_posix()
		entry = mem_idx.get(rel)
		if not isinstance(entry, dict):
			continue
		file_tickets = set(entry.get('tickets') or ())
		file_plans = set(entry.get('plans_norm') or ())
		file_metrics = set(entry.get('metrics') or ())
		rp_posix = rp.as_posix()
		matched_entities = []
		for tid in tickets:
			if tid in rp_posix or tid in file_tickets:
				matched_entities.append(f'ticket:{tid}')
		for pl in plans:
			if ' '.join(pl.split()).upper() in file_plans:
				matched_entities.append(f'plan:{pl}')
		for mt in metrics:
			if mt in file_metrics:
				matched_entities.append(f'metric:{mt}')
		if matched_entities:
			discovered.append({
				'path': rel,
				'sha256': entry['sha256'],
				'tier': 'tier_0',
				'matched_entities': matched_entities,
			})
	return discovered
def _collect_json_fact_tuples(obj, default_entity: str, source_loc: str, out: list[dict]):
	attr_keys = {'vcpu', 'cpus', 'cores', 'mem_total', 'ram_gb', 'ram', 'swap_total', 'load_average', 'load_avg', 'disk_gb', 'php_memory_limit'}
	id_keys = ('code', 'id', 'plan', 'name', 'tier', 'server', 'host')
	if isinstance(obj, dict):
		entities = []
		for ik in id_keys:
			val = obj.get(ik)
			if isinstance(val, str) and val.strip():
				v_s = val.strip()
				if v_s not in entities:
					entities.append(v_s)
				if 'tier' == ik and re.fullmatch('(?:XS|S|M|L|XL|XXL)', v_s, re.I):
					plan_alias = f'Plan {v_s.upper()}'
					if plan_alias not in entities:
						entities.append(plan_alias)
		if not entities:
			entities = [default_entity]
		elif default_entity and default_entity not in entities:
			entities.append(default_entity)
		for k, v in obj.items():
			kl = str(k).lower()
			if kl in attr_keys and (None is v or isinstance(v, (int, float, str))):
				for ent in entities:
					out.append({
						'entity': ent,
						'attribute': kl,
						'value': v,
						'unit': 'MB' if kl in {'mem_total', 'swap_total'} else ('GB' if kl in {'ram_gb', 'disk_gb'} else None),
						'source_locator': source_loc,
					})
			elif isinstance(v, (dict, list)):
				next_ent = str(k).strip() if isinstance(v, dict) and re.match('^(?:M[1-9]|Plan\\s+(?:XS|S|M|L|XL|XXL)|server[-_a-z0-9]+)$', str(k).strip(), re.I) else entities[0]
				_collect_json_fact_tuples(v, next_ent, f'{source_loc}/{k}', out)
	elif isinstance(obj, list):
		for idx, item in enumerate(obj):
			_collect_json_fact_tuples(item, default_entity, f'{source_loc}[{idx}]', out)
def extract_fact_tuples(path: Path, raw_text: str | None = None, *, root: Path | None = None) -> list[dict]:
	if None is raw_text:
		try:
			raw_text = path.read_text(encoding='utf-8', errors='replace')
		except OSError:
			return []
	try:
		loc = path.resolve().relative_to(Path(root).resolve()).as_posix() if None is not root else path.name
	except ValueError:
		loc = path.as_posix()
	tuples: list[dict] = []
	default_entity = path.parent.parent.name if 'kb' == path.parent.name.lower() else (path.parent.name if 'source.md' == path.name.lower() else path.stem)
	doc_plans = sorted({m.group(0).strip() for m in re.finditer('\\b(?:M[1-9]|Plan\\s+(?:XS|S|M|L|XL|XXL))\\b', raw_text, re.I)})
	if '.json' == path.suffix.lower() and raw_text.strip():
		try:
			parsed = json.loads(raw_text)
			_collect_json_fact_tuples(parsed, default_entity, loc, tuples)
		except ValueError:
			pass
	else:
		for m_fence in re.finditer('```(?:json)?\\s*\\n(.*?)\\n```', raw_text, re.I | re.S):
			try:
				parsed = json.loads(m_fence.group(1).strip())
				_collect_json_fact_tuples(parsed, default_entity, loc, tuples)
			except ValueError:
				pass
	for m_mem in re.finditer('(?i)["\']?\\b(mem_total|swap_total|cpus|vcpu)\\b["\']?\\s*[:=]\\s*(null|\\d+(?:\\.\\d+)?)\\b', raw_text):
		attr = m_mem.group(1).lower()
		val_raw = m_mem.group(2).lower()
		val = None if 'null' == val_raw else (int(val_raw) if val_raw.isdigit() else float(val_raw))
		line_start = raw_text.rfind('\n', 0, m_mem.start()) + 1
		line_end = raw_text.find('\n', m_mem.end())
		line_slice = raw_text[line_start:len(raw_text) if -1 == line_end else line_end]
		line_plans = [m.group(0).strip() for m in re.finditer('\\b(?:M[1-9]|Plan\\s+(?:XS|S|M|L|XL|XXL))\\b', line_slice, re.I)]
		target_entities = list(dict.fromkeys([default_entity] + (line_plans or (doc_plans if 1 == len(doc_plans) else []))))
		for ent in target_entities:
			tuples.append({
				'entity': ent,
				'attribute': attr,
				'value': val,
				'unit': 'MB' if attr in {'mem_total', 'swap_total'} else None,
				'source_locator': loc,
			})
	for m_la in re.finditer('(?i)load\\s+average\\s*[:=]\\s*(\\d+(?:\\.\\d+)?)', raw_text):
		tuples.append({
			'entity': default_entity,
			'attribute': 'load_average_1m',
			'value': float(m_la.group(1)),
			'unit': 'load',
			'source_locator': loc,
		})
	return tuples
def sync_fact_ledger(root: Path) -> dict:
	root = Path(root).resolve()
	candidates, mem_idx = _load_tier0_index(root)
	tuples: list[dict] = []
	for rp in candidates:
		try:
			rel = rp.relative_to(root).as_posix()
		except ValueError:
			rel = rp.as_posix()
		entry = mem_idx.get(rel)
		if isinstance(entry, dict) and isinstance(entry.get('fact_tuples'), list):
			tuples.extend(entry['fact_tuples'])
	payload = {'version': 1, 'tuple_count': len(tuples), 'tuples': tuples}
	data_dir = root / 'ꘖ' / 'data'
	if tuples or data_dir.is_dir() or (root / 'ꘖ').is_dir():
		data_dir.mkdir(parents=True, exist_ok=True)
		(data_dir / 'facts.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
	return payload
def load_fact_ledger(root: Path) -> list[dict]:
	ledger_path = Path(root).resolve() / 'ꘖ' / 'data' / 'facts.json'
	if ledger_path.is_file():
		try:
			data = json.loads(ledger_path.read_text(encoding='utf-8'))
			if isinstance(data, dict) and isinstance(data.get('tuples'), list):
				return data['tuples']
		except (OSError, ValueError):
			pass
	return []
def fact_tuple_contradictions(sline: str, infos: list[dict], ledger_tuples: list[dict] | None = None) -> list[str]:
	if not sline or META_REFUTATION_RE.search(sline):
		return []
	all_tuples: list[dict] = []
	for inf in infos:
		all_tuples.extend(inf.get('fact_tuples') or [])
	if ledger_tuples:
		all_tuples.extend(ledger_tuples)
	issues: list[str] = []
	null_cpu_entities = {
		str(t['entity']).lower(): t
		for t in all_tuples
		if t.get('attribute') in {'vcpu', 'cpus', 'cores'} and None is t.get('value') and t.get('entity')
	}
	for ent_lower, tup in null_cpu_entities.items():
		ent = str(tup['entity'])
		if re.search(f'\\b{re.escape(ent)}\\b', sline, re.I):
			m_cpu = re.search('(\\d+)\\s*(?:vcpu|cpu|cores?|\\u044f\\u0434(?:\\u0435\\u0440|\\u0440\\u0430|\\u0440\\u043e))', sline, re.I)
			if m_cpu and not re.search('\\b(?:null|\\u043d\\u0435\\s+\\u0443\\u043a\\u0430\\u0437\\u0430\\u043d|unspecified|unknown)\\b', sline, re.I):
				issues.append(
					f'DOC-1 / VERIFY-1: Fact-tuple contradiction for {ent} ({tup["attribute"]}=null in {tup["source_locator"]}): prose asserts {m_cpu.group(0)} for a null attribute'
				)
	mem_tuples = [t for t in all_tuples if 'mem_total' == t.get('attribute') and isinstance(t.get('value'), (int, float)) and t['value'] >= 1024]
	if mem_tuples:
		m_gb = re.search('(?:\\b(?:ram|memory|\\u043e\\u0437\\u0443|\\u043f\\u0430\\u043c\\u044f\\u0442\\w*)\\b[^\\d\\n]{0,25})?(\\d+(?:\\s*[\\u2013\\u2014-]\\s*\\d+)?)\\s*(?:gb|gib|\\u0433\\u0431)\\s*(?:ram|memory|\\u043e\\u0437\\u0443)?', sline, re.I)
		if m_gb and re.search('\\b(?:ram|memory|\\u043e\\u0437\\u0443|mem_total)\\b', sline, re.I):
			stated_raw = m_gb.group(1)
			stated_nums = [int(x) for x in re.findall('\\d+', stated_raw)]
			valid_gb = set()
			for mt in mem_tuples:
				mb_val = float(mt['value'])
				valid_gb.update({round(mb_val / 1024.0), int(mb_val // 1024), round(mb_val / 1000.0), int(mb_val)})
			if stated_nums and not any((sn in valid_gb for sn in stated_nums)):
				mt0 = mem_tuples[0]
				issues.append(
					f'DOC-1 / VERIFY-1: Fact-tuple contradiction for mem_total={mt0["value"]} MB in {mt0["source_locator"]}: prose claims {m_gb.group(0).strip()} (expected ~{round(float(mt0["value"]) / 1024.0, 2)} GiB)'
				)
		if re.search('(?i)\\bburst\\b[^\\n]{0,25}\\b(\\d+(?:[.,]\\d+)?)\\s*(?:gb|gib|\\u0433\\u0431)|(\\d+(?:[.,]\\d+)?)\\s*(?:gb|gib|\\u0433\\u0431)[^\\n]{0,25}\\bburst\\b', sline):
			if not any(('burst' in str(inf.get('raw') or '').lower() for inf in infos)):
				mt0 = mem_tuples[0]
				issues.append(
					f'DOC-1 / VERIFY-1: Fact-tuple contradiction for mem_total={mt0["value"]} MB in {mt0["source_locator"]}: prose characterizes permanent mem_total RAM as "burst" without primary source support'
				)
	if re.search('(?i)(?:\\b\\u0443\\u0445\\u043e\\u0434\\w*\\s+(?:\\u0441\\u0435\\u0440\\u0432\\u0435\\u0440\\u0430\\s+)?\\u0432\\s+(?:swap|\\u0441\\u0432\\u043e\\u043f)|\\u0444\\u0438\\u043a\\u0441\\u0438\\u0440\\u043e\\u0432\\u0430\\u043b\\w*[^\\n]{0,40}\\b(?:swap|\\u0441\\u0432\\u043e\\u043f)|\\bswapping\\b)', sline) and (not re.search('(?i)(?:\\b\\u0431\\u0435\\u0437\\s+(?:swap|\\u0441\\u0432\\u043e\\u043f)|\\bno\\s+swap|\\bswap[_ ]total\\s*[:=]\\s*0|\\b\\u043d\\u0435\\s+\\u0443\\u0445\\u043e\\u0434|\\b\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\w*\\s+(?:swap|\\u0441\\u0432\\u043e\\u043f))', sline)):
		zero_swap = [t for t in all_tuples if 'swap_total' == t.get('attribute') and 0 == t.get('value')]
		tier0_infos = [inf for inf in infos if 'tier_0' == inf.get('tier') and inf.get('raw')]
		if zero_swap:
			zs0 = zero_swap[0]
			issues.append(
				f'DOC-1 / VERIFY-1: Fact-tuple contradiction for swap_total=0 in {zs0["source_locator"]}: prose asserts server swap activity despite swap_total=0'
			)
		elif tier0_infos and not any((re.search('(?i)\\b(?:swap\\w*|\\u0441\\u0432\\u043e\\u043f\\w*)', str(inf.get('raw') or '')) for inf in tier0_infos)):
			src_name = tier0_infos[0]['path'].name
			issues.append(
				f'DOC-1 / VERIFY-1: Fact-tuple contradiction in {src_name}: prose asserts server swap activity ("swap"), which is absent from the Tier 0 primary source'
			)
	la_tuples = [t for t in all_tuples if 'load_average_1m' == t.get('attribute') and isinstance(t.get('value'), (int, float))]
	cpu_tuples = [t for t in all_tuples if t.get('attribute') in {'cpus', 'vcpu'} and isinstance(t.get('value'), (int, float)) and t['value'] > 0]
	if la_tuples and cpu_tuples:
		la_val = float(la_tuples[0]['value'])
		cpu_val = float(cpu_tuples[0]['value'])
		if la_val < cpu_val and re.search('load\\s+average', sline, re.I):
			if re.search('(?:\\u043f\\u0435\\u0440\\u0435\\u0433\\u0440\\u0443\\u0437\\w*|overload\\w*|saturat\\w*|\\u043f\\u0440\\u0435\\u0432\\u044b\\u0448\\u0430\\u0435\\u0442\\s+\\u0435\\u043c\\u043a\\u043e\\u0441\\u0442|exceeds\\s+capacity)', sline, re.I) and (not re.search('(?:\\u043d\\u0435\\s+\\u043f\\u0435\\u0440\\u0435\\u0433\\u0440\\u0443\\u0437|not\\s+overload|below|\\u043c\\u0435\\u043d\\u044c\\u0448\\u0435)', sline, re.I)):
				issues.append(
					f'DOC-1 / VERIFY-3: Unnormalized load average claim ({la_val} on {int(cpu_val)} CPUs = {round(la_val / cpu_val * 100, 1)}% utilization < 100%, below the core count) in {cpu_tuples[0]["source_locator"]}'
				)
	return issues
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
_source_numeric_tokens = source_numeric_tokens
def _load_local_source_info(path: Path, cache: dict | None = None) -> dict:
	key = str(path)
	if None is not cache and key in cache:
		return cache[key]
	stat_key = None
	try:
		rp = path.resolve()
		st = rp.stat()
		stat_key = (str(rp), st.st_mtime_ns, st.st_size)
		if stat_key in _SOURCE_INFO_CACHE:
			info = _SOURCE_INFO_CACHE[stat_key]
			if None is not cache:
				cache[key] = info
			return info
		raw_bytes = rp.read_bytes()
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
		'tier': classify_provenance_tier(path),
		'fact_tuples': extract_fact_tuples(path, raw),
	}
	if None is not stat_key:
		_SOURCE_INFO_CACHE[stat_key] = info
	if None is not cache:
		cache[key] = info
	return info
def quote_segments_present(q_raw: str, obs_norm: str, min_seg_len: int = 12) -> bool:
	raw_parts = [norm_quote_text(s) for s in re.split('\\[\\.\\.\\.\\]|\\(\\.\\.\\.\\)|\\[\\u2026\\]|\\(\\u2026\\)|\\.{3,}|\\u2026', q_raw)]
	segs = [s for s in raw_parts if min_seg_len <= len(s)]
	if segs:
		r = all((s in obs_norm for s in segs))
	elif 1 < len(raw_parts):
		short_segs = [s for s in raw_parts if 4 <= len(s)]
		r = not short_segs or all((s in obs_norm for s in short_segs))
	else:
		whole = raw_parts[0] if raw_parts else ''
		r = len(whole) < 8 or whole in obs_norm
	return r
_quote_segments_present = quote_segments_present
def _filter_primary_sources(paths: list[Path]) -> list[Path]:
	src_dirs = {p.parent for p in paths if 'source.md' == p.name.lower()}
	non_analysis = [p for p in paths if not ('analysis.md' == p.name.lower() and p.parent in src_dirs)]
	if any(('tier_2' != classify_provenance_tier(p) for p in non_analysis)):
		non_analysis = [p for p in non_analysis if 'tier_2' != classify_provenance_tier(p)]
	return non_analysis
def extract_block_links(block, root: Path, doc_path: Path | None):
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
	r = (local_all, ext_urls)
	return r
_extract_block_links = extract_block_links
def extract_blockquote_quotes(content: str, *, min_guillemet_len: int = 8, allow_backtick_quotes: bool = False, min_orig_len: int = 12) -> list[str]:
	r = list(re.findall(f'\\u00ab([^\\u00bb]{{{min_guillemet_len},}})\\u00bb', content or ''))
	if allow_backtick_quotes:
		r.extend(re.findall(f'`"([^"\\n]{{{min_guillemet_len},}})"`', content or ''))
	if not r:
		m_orig = re.search(f'(?:\\u041e\\u0440\\u0438\\u0433\\u0438\\u043d\\u0430\\u043b|Original)\\s*:\\s*["\\u00ab]?(.{{{min_orig_len},}})["\\u00bb]?$', (content or '').strip(), re.I | re.S)
		if m_orig:
			r.append(m_orig.group(1).strip(' "\u00ab\u00bb'))
	return r
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
	verified_calc_nums, calc_errors = extract_verified_inline_calc_numbers(sline, ev_nums)
	ev_with_calc = set(ev_nums) | set(verified_calc_nums)
	for calc_err in calc_errors:
		missing.append(f'{calc_err} (inline arithmetic mismatch)')
	cleaned = re.sub('\\[[^\\]]*\\]\\([^)]*\\)', ' ', sline)
	cleaned = re.sub('https?://\\S+|file://\\S+', ' ', cleaned)
	cleaned = cleaned.replace('`', ' ')
	cleaned = re.sub('\\b\\d+(?:[.,]\\d+)?\\s*%', ' ', cleaned)
	cleaned = re.sub('(?i)\\b(?:line|lines|\\u0441\\u0442\\u0440\\u043e\\u043a\\w*)\\s+\\d+(?:\\s*[\\u2013\\u2014-]\\s*\\d+)?', ' ', cleaned)
	for num in sorted(standalone_numbers(cleaned)):
		norm_num = num.replace(',', '')
		if len(norm_num) == 1 and norm_num.isdigit():
			continue
		if num not in ev_with_calc and norm_num not in ev_with_calc:
			missing.append(num)
	return missing
def _is_client_deliverable_doc(doc_path: Path | None) -> bool:
	if None is doc_path or _is_normative_harness_doc(doc_path):
		return False
	norm_p = '/' + doc_path.as_posix().lower().lstrip('/')
	if '/\ua616/' in norm_p or '/\ua66e/' in norm_p:
		return False
	return any((seg in norm_p for seg in ('/letters/', '/result/', '/defects/')))
def local_source_grounding_issues(root: Path, content: str, *, doc_path: Path | None = None, observed_texts: dict | None = None, cache: dict | None = None, _visited: set | None = None) -> list[str]:
	if not content or not isinstance(content, str):
		return []
	root = Path(root).resolve()
	visited = _visited if None is not _visited else set()
	if None is not doc_path:
		doc_path = Path(doc_path).resolve()
		if _is_normative_harness_doc(doc_path):
			return []
		if str(doc_path) in visited:
			return []
		visited.add(str(doc_path))
	errors = []
	cache = cache if None is not cache else {}
	ledger_tuples = list(load_fact_ledger(root))
	for disc in discover_entity_tier0_sources(root, content):
		dp = (root / disc['path']).resolve()
		if dp.is_file():
			ledger_tuples.extend(_load_local_source_info(dp, cache).get('fact_tuples') or [])
	default_sources = []
	if None is not doc_path and (doc_path.parent / 'source.md').is_file() and 'source.md' != doc_path.name.lower():
		default_sources = [(doc_path.parent / 'source.md').resolve()]
	parser = markdown_parser()
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
		sibling_tier0_for_analysis = []
		orphan_analyses = []
		for lp in local_all:
			if 'analysis.md' == lp.name.lower():
				if (lp.parent / 'source.md').is_file():
					if lp not in linked_analyses:
						linked_analyses.append(lp)
					sib_src = (lp.parent / 'source.md').resolve()
					if sib_src not in sibling_tier0_for_analysis:
						sibling_tier0_for_analysis.append(sib_src)
				else:
					orphan_analyses.append(lp)
		filtered_locals = _filter_primary_sources(local_all)
		primary_here = [p for p in filtered_locals if is_primary_local_source(p)]
		for sib_src in sibling_tier0_for_analysis:
			if sib_src not in primary_here:
				primary_here.append(sib_src)
		tier2_here = [p for p in local_all if 'tier_2' == classify_provenance_tier(p, root)] + orphan_analyses
		if tier2_here and (not primary_here) and (not ext_urls) and (not META_REFUTATION_RE.search(block.content)):
			non_analysis_tier2 = [p for p in tier2_here if ('analysis.md' != p.name.lower() or p in orphan_analyses) and (not _is_normative_harness_doc(p))]
			if non_analysis_tier2 and re.search('(?i)\\b(?:mem_total|vcpu|cpus|swap_total|swap|\\u0441\\u0432\\u043e\\u043f|worker\\w*|\\u0432\\u043e\\u0440\\u043a\\u0435\\u0440\\w*|load\\s+average|ram|\\u043e\\u0437\\u0443|\\u044f\\u0434(?:\\u0435\\u0440|\\u0440\\u0430)|plan\\s+(?:xs|s|m|l|xl|xxl)|m[1-9]|gb|gib|\\u0433\\u0431|mb|mib|\\u043c\\u0431)\\b', block.content) and standalone_numbers(block.content):
				errors.append(f'VERIFY-1 / SCOPE-1: Tier 2 file ({non_analysis_tier2[0].name}) cannot serve as sole primary evidence for factual or numeric claims; cite a Tier 0 primary observation')
				for disc in discover_entity_tier0_sources(root, block.content):
					dp = (root / disc['path']).resolve()
					if dp.is_file() and dp not in primary_here:
						primary_here.append(dp)
		if primary_here:
			section_sources = primary_here
			section_all_locals = list(dict.fromkeys(filtered_locals + primary_here))
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
			if _is_client_deliverable_doc(doc_path) and 0 == quote_depth and (not META_REFUTATION_RE.search(block.content)):
				if re.search('(?i)(?:/sales/order/view/order_id/\\d+|\\b(?:auth_code|trans_id)\\b|#31\\d{6,8}|`[0-9]{5}[0-9A-Z]`|\\b\\d+\\s+(?:rows|records|orders|transactions|events|occurrences|\\u0437\\u0430\\u043f\\u0438\\u0441\\w*|\\u0441\\u0442\\u0440\\u043e\\u043a\\w*|\\u0437\\u0430\\u043a\\u0430\\u0437\\w*|\\u0442\\u0440\\u0430\\u043d\\u0437\\u0430\\u043a\\u0446\\w*)\\b)', block.content):
					errors.append('VERIFY-1 / LINK-1: Client deliverable block asserts quantitative metrics or transaction/order identifiers without linking to a Tier 0 primary source in \ua616/KB/Evidence/')
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
			for bq in extract_blockquote_quotes(block.content):
				if not quote_segments_present(bq, combined_norm, 12):
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
			for m_oid in re.finditer('/sales/order/view/order_id/(\\d+)', sline, re.I):
				oid_val = m_oid.group(1)
				if oid_val not in ev_nums and oid_val not in combined_raw:
					errors.append(f'VERIFY-1 / DOC-1: Order URL identifier (order_id/{oid_val}) attributed to {src_label} is absent from the primary source')
			for ft_err in fact_tuple_contradictions(sline, infos, ledger_tuples=ledger_tuples):
				errors.append(ft_err)
			for code_span in re.findall('`([^`\\n]{3,60})`', sline):
				c_strip = code_span.strip()
				if re.match('^(?:/dev/[A-Za-z0-9/_-]+|[a-z][a-z0-9_]{3,}:\\d{3,}|[A-Za-z][A-Za-z0-9_.-]+\\s+\\d+\\.\\d+(?:\\.\\d+)*(?:-[A-Za-z0-9._-]+)?|#?31\\d{6,8}|[0-9]{5}[0-9A-Z]|order_id/\\d+)$', c_strip):
					c_lookup = c_strip.lstrip('#')
					if norm_quote_text(c_strip) not in combined_norm and c_strip.lower() not in combined_raw.lower() and c_lookup.lower() not in combined_raw.lower():
						errors.append(f'VERIFY-1 / DOC-1: Technical literal `{c_strip}` attributed to {src_label} is absent from the primary source')
	for ap in linked_analyses:
		try:
			a_text = ap.read_text(encoding='utf-8')
		except OSError:
			continue
		sub_errs = local_source_grounding_issues(root, a_text, doc_path=ap, observed_texts=observed_texts, cache=cache, _visited=visited)
		for se in sub_errs[:5]:
			errors.append(f'Linked {ap.parent.parent.name}/{ap.name} -> {se}')
	r = list(dict.fromkeys(errors))
	return r
