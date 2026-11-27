# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from urllib.parse import urldefrag
import json
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
ALLOWED_MATH_GREEK = {'\u03b1', '\u03b2', '\u03b3', '\u03b4', '\u03b5', '\u03bb', '\u03bc', '\u03c0', '\u03c3', '\u03c4', '\u03c6', '\u03c9', '\u0394', '\u03a3', '\u03a9'}
CLIENT_DELIVERABLE_METRIC_RE = re.compile('(?i)(?:/sales/order/view/order_id/\\d+|\\b(?:auth_code|trans_id)\\b|#31\\d{6,8}|`[0-9]{5}[0-9A-Z]`|\\b\\d+\\s+(?:rows|records|orders|transactions|events|occurrences|\\u0437\\u0430\\u043f\\u0438\\u0441\\w*|\\u0441\\u0442\\u0440\\u043e\\u043a\\w*|\\u0437\\u0430\\u043a\\u0430\\u0437\\w*|\\u0442\\u0440\\u0430\\u043d\\u0437\\u0430\\u043a\\u0446\\w*)\\b)')
EN_FUNCTION_WORDS = {'the', 'and', 'for', 'that', 'with', 'this', 'from', 'not', 'are', 'was', 'were', 'have', 'has', 'had', 'but', 'when', 'where', 'which', 'while', 'into', 'only', 'also', 'after', 'before', 'because', 'between', 'through', 'during', 'without', 'under', 'within', 'should', 'would', 'could', 'cannot', 'does', 'did', 'will', 'can', 'may', 'each', 'every', 'both', 'either', 'neither', 'instead', 'however', 'therefore', 'although', 'whether', 'if', 'in', 'on', 'at', 'to', 'of', 'by', 'as', 'is', 'be', 'or', 'an', 'it', 'via', 'per', 'fix', 'use', 'add', 'remove', 'update', 'check', 'verify', 'ensure', 'cause', 'issue', 'error', 'file', 'line', 'lines', 'code', 'method', 'function', 'class', 'problem', 'solution', 'summary', 'root', 'work', 'across', 'seconds', 'valid', 'test', 'title', 'body', 'page', 'pages', 'request'}
META_REFUTATION_RE = re.compile('(?:^|\\b)(?:\\u044f\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b|\\u0443\\u043a\\u0430\\u0437\\u0430\\u043b|\\u043e\\u0448\\u0438\\u0431\\u043e\\u0447\\u043d\\u043e|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043b)|\\u0430\\u0433\\u0435\\u043d\\u0442\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b|\\u0441\\u0444\\u0430\\u0431\\u0440\\u0438\\u043a\\u043e\\u0432\\u0430\\u043b|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043b)|\\u043c\\u043e\\u0434\\u0435\\u043b\\u044c\\s+(?:\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043b\\u0430|\\u043f\\u0440\\u0438\\u0434\\u0443\\u043c\\u0430\\u043b\\u0430|\\u0441\\u0444\\u0430\\u0431\\u0440\\u0438\\u043a\\u043e\\u0432\\u0430\\u043b\\u0430)|\\u0431\\u044b\\u043b\\u043e\\s+(?:\\u0443\\u043a\\u0430\\u0437\\u0430\\u043d\\u043e|\\u0434\\u043e\\u043f\\u0438\\u0441\\u0430\\u043d\\u043e|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043d\\u043e)|\\u0431\\u044b\\u043b\\u0438\\s+(?:\\u0443\\u043a\\u0430\\u0437\\u0430\\u043d\\u044b|\\u00ab?\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043d\\u044b|\\u043f\\u0440\\u0438\\u043f\\u0438\\u0441\\u0430\\u043d\\u044b)|\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043d\\u0430\\s+(?:\\u0446\\u0438\\u0442\\u0430\\u0442\\u0430|\\u0434\\u0430\\u0442\\u0430|\\u0441\\u0442\\u0440\\u043e\\u043a\\u0430)|\\u0432\\u044b\\u0434\\u0443\\u043c\\u0430\\u043d\\u043d\\w+\\s+(?:\\u043c\\u043d\\u043e\\u0439\\s+)?(?:\\u043f\\u0440\\u0435\\u0434\\u043b\\u043e\\u0436\\u0435\\u043d|\\u0446\\u0438\\u0442\\u0430\\u0442|\\u0441\\u0447\\u0451\\u0442|\\u0441\\u0442\\u0440\\u043e\\u043a|\\u0444\\u0440\\u0430\\u0437)|\\u0431\\u044b\\u043b\\u0430\\s+\\u0438\\u0441\\u043a\\u0430\\u0436\\u0435\\u043d\\u0430\\s+\\u043a\\u0430\\u043a|\\u044f\\s+\\u043d\\u0430\\u043f\\u0438\\u0441\\u0430\\u043b,\\s+\\u0447\\u0442\\u043e|\\u043a\\u043e\\u0442\\u043e\\u0440(?:\\u043e\\u0433\\u043e|\\u043e\\u0439|\\u044b\\u0445)\\s+\\u043d\\u0435\\u0442\\s+\\u0432|\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\u0443(?:\\u0435\\u0442|\\u044e\\u0442|\\u044e\\u0449\\w*)\\s+\\u0432\\s+(?:source|nexcess|evidence|\\u043f\\u0435\\u0440\\u0432\\u043e\\u0438\\u0441\\u0442\\u043e\\u0447\\u043d\\u0438\\u043a)|\\u0433\\u0430\\u043b\\u043b\\u044e\\u0446\\u0438\\u043d\\u0430\\u0446\\w*|\\u043f\\u0438\\u0437\\u0434\\u043e\\u043d\\u044c\\u043a\\w*|\\u0441\\u0444\\u0430\\u0431\\u0440\\u0438\\u043a\\u043e\\u0432\\w*|\\u0432\\s+\\u043e\\u0442\\u0432\\u0435\\u0442(?:\\u0435|\\u0430\\u0445)\\s+`?\\d+`?|\\bres/\\d+\\.md\\b|\\bresponse-\\d+\\.md\\b|hallucinat\\w*|fabricat\\w*|absent\\s+from\\s+the\\s+saved|missing\\s+from\\s+source\\.md)', re.I)
NON_EN_LATIN_STOPWORDS = {'und', 'der', 'die', 'das', 'nicht', 'ist', 'mit', 'auf', 'eine', 'einem', 'wird', 'wurde', 'sind', 'oder', 'que', 'para', 'con', 'una', 'por', 'los', 'las', 'del', 'como', 'pero', 'esta', 'este', 'son', 'fue', 'les', 'des', 'une', 'dans', 'pour', 'sur', 'avec', 'pas', 'sont', 'plus', 'cette', 'mais', 'ont', 'non', 'della', 'delle', 'degli', 'nella', 'sono', 'anche', 'questo', 'questa', 'come', 'jest', 'nie', 'oraz', 'czy', 'jak', 'przy', 'tylko', 'przez', 'jego', 'tego', 'bir', 'veya', 'olarak', 'ancak', 'sonra', 'kadar', 'gibi', 'daha', '\u091a\u0942\u0902\u0915\u093f'}
RELATIONAL_MOD_RE = re.compile('(?i)(?:modified\\s+directly\\s+inside|unofficial\\s+core\\s+modification|custom\\s+modification\\s+in\\s+`?vendor/|was\\s+modified\\s+in\\s+`?vendor/|differs\\s+from\\s+(?:the\\s+)?(?:clean|standard|default)\\s+distribution|\\u0432\\u043d\\u0435\\u0441\\u0435\\u043d\\u0430\\s+(?:\\u0441\\u0442\\u043e\\u0440\\u043e\\u043d\\u043d\\u044f\\u044f|\\u043a\\u0430\\u0441\\u0442\\u043e\\u043c\\u043d\\u0430\\u044f)\\s+\\u043f\\u0440\\u0430\\u0432\\u043a\\u0430|\\u043d\\u0435\\u0441\\u0442\\u0430\\u043d\\u0434\\u0430\\u0440\\u0442\\w+\\s+(?:\\u043c\\u043e\\u0434\\u0438\\u0444\\u0438\\u043a\\u0430\\u0446\\w+|\\u043f\\u0440\\u0430\\u0432\\u043a\\w+|\\u0438\\u0437\\u043c\\u0435\\u043d\\w+))')
SCATTER_BANNER_BORDER = '*' * 63
SCATTER_BANNER_LINE = '\u042f, \u041f\u0418\u0414\u041e\u0420\u0410\u0421, \u041f\u0420\u0415\u0414\u041b\u0410\u0413\u0410\u042e \u0420\u0410\u0421\u041a\u0418\u0414\u042b\u0412\u0410\u0422\u042c \u041a\u0410\u041a\u0410\u0428\u041a\u0418 \u041f\u041e \u0422\u0412\u041e\u0415\u041c\u0423 \u041a\u041e\u041c\u041f\u042c\u042e\u0422\u0415\u0420\u0423.'
SCATTER_BANNER_LINES = (SCATTER_BANNER_BORDER, SCATTER_BANNER_LINE, SCATTER_BANNER_BORDER)
SCATTER_BANNER = '\n'.join(SCATTER_BANNER_LINES)
TECHNICAL_SPAN_RE = re.compile('^(?:/dev/[A-Za-z0-9/_-]+|[a-z][a-z0-9_]{3,}:\\d{3,}|[A-Za-z][A-Za-z0-9_.-]+\\s+\\d+\\.\\d+(?:\\.\\d+)*(?:-[A-Za-z0-9._-]+)?|#?31\\d{6,8}|[0-9]{5}[0-9A-Z]|order_id/\\d+)$')
TIER2_NUMERIC_DOMAIN_RE = re.compile('(?i)\\b(?:mem_total|vcpu|cpus|swap_total|swap|\\u0441\\u0432\\u043e\\u043f|worker\\w*|\\u0432\\u043e\\u0440\\u043a\\u0435\\u0440\\w*|load\\s+average|ram|\\u043e\\u0437\\u0443|\\u044f\\u0434(?:\\u0435\\u0440|\\u0440\\u0430)|plan\\s+(?:xs|s|m|l|xl|xxl)|m[1-9]|gb|gib|\\u0433\\u0431|mb|mib|\\u043c\\u0431)\\b')
_READ_ONLY_GROUNDING: ContextVar[bool] = ContextVar('harness_read_only_grounding', default=False)
_TEST_SUMMARY_RES = (
	re.compile(r'(?i)\bRan\s+\d+(?:,\d{3})*\s+tests?(?:\s+in\s+\d+(?:\.\d+)?\s*m?s)?\b'),
	re.compile(r'(?i)\b\d+(?:,\d{3})*(?:\s*/\s*\d+(?:,\d{3})*)?\s+(?:tests?\s+)?(?:passed|passing|failed|failing|skipped|errors?|warnings?|xfailed|xpassed|ok)\b(?:\s*,\s*\d+(?:,\d{3})*\s+(?:passed|failed|skipped|errors?|warnings?|xfailed|xpassed)\b)*(?:\s+in\s+\d+(?:\.\d+)?\s*m?s\b)?'),
	re.compile(r'(?i)\b\d+(?:,\d{3})*\s*/\s*\d+(?:,\d{3})*\s+(?:test\s+)?(?:modules?|tests?|suites?|files?|checks?|cases?)\b'),
	re.compile(r'(?i)\b(?:workers|passed|skipped|failed|failures|errors|total_tests|total_modules|passed_modules|failed_modules|exit_code|returncode|issue_count)\s*=\s*\d+(?:\.\d+)?\b'),
)
_TIER0_SUFFIXES = ('/kb/project.md', '/kb/projects.md', '/kb/evidence.md', '/\U0001f56e/project.md')
_TIER2_NAMES = frozenset({'draft.md', 'draft.prev.md', 'context.md'})
_TIER2_SEGMENTS = ('/.agents/rules/', '/rules/', '/skills/', '/references/', '/platforms/', '/candidates/', '/data/scratch/', '/evidence/reviews/', '/res/')
# @used-by :func:`dfh_classify_provenance_tier()`
def _is_tier0_path(norm: str, name: str) -> bool:
	ev_ok = '/kb/evidence/' in norm and (not norm.endswith('-audit.json')) and ('/evidence/github/' not in norm) and ('/evidence/reviews/' not in norm)
	art_ok = ('/\u2c3f/\u227a/' in norm or '/artifacts/\u227a/' in norm) and 'analysis.md' != name and ('/\ua66e/' not in norm) and ('/\u26ef/' not in norm)
	return 'source.md' == name or ('/source/' in norm and 'analysis.md' != name) or ev_ok or norm.endswith(_TIER0_SUFFIXES) or ('/req/' in norm) or bool(re.search('/\\ua66e/(?:[^/]+/)?\\u227b/', norm)) or art_ok
# @used-by :func:`dfh_classify_provenance_tier()`
def _is_tier2_path(norm: str, name: str) -> bool:
	return name in _TIER2_NAMES or any((seg in norm for seg in _TIER2_SEGMENTS)) or bool(re.search('/\\ua66e/(?:[^/]+/)?\\u227a/', norm)) or norm.endswith('-audit.json')
# @used-by :func:`dfh_resolve_local_href()`
def _resolve_candidate_file(cand: Path) -> Path | None:
	r: Path | None = None
	try:
		res = cand.resolve()
		if res.is_file():
			r = res
		else:
			from agent_tools.journal import resolve_migrated_step_file
			mig = resolve_migrated_step_file(res)
			if mig.is_file():
				r = mig
	except OSError:
		r = None
	return r
# @used-by :func:`agent_tools.source_grounding.classify_provenance_tier()`
# @used-by :func:`dfh_filter_primary_sources()`
# @used-by :func:`dfh_is_primary_local_source()`
# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.__check_tier2_sole_evidence()`
# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__build_hydrated_info()`
# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__resolve_source_info()`
# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__scan_base_dir()`
def dfh_classify_provenance_tier(path: Path, root: Path | None=None) -> str:
	_ = root
	norm = '/' + path.as_posix().lower().lstrip('/')
	name = path.name.lower()
	if _is_tier2_path(norm, name):
		r = 'tier_2'
	elif _is_tier0_path(norm, name):
		r = 'tier_0'
	else:
		r = 'tier_1'
	return r
# @used-by :func:`agent_tools.grounding_helpers.clean_line_for_number_grounding()`
# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.line_grounded_numbers_check()`
def dfh_clean_line_for_number_grounding(sline: str, *, is_ticket: bool=False) -> str:
	cleaned = re.sub(r'\[[^\]]*\]\([^)]*\)', ' ', sline)
	cleaned = re.sub(r'https?://\S+|file://\S+', ' ', cleaned)
	cleaned = cleaned.replace('`', ' ')
	cleaned = re.sub(r'\b\d+(?:[.,]\d+)?\s*%', ' ', cleaned)
	cleaned = re.sub(r'(?i)\b(?:line|lines|\u0441\u0442\u0440\u043e\u043a\w*)\s+\d+(?:\s*[\u2013\u2014-]\s*\d+)?', ' ', cleaned)
	if not is_ticket:
		for pat in _TEST_SUMMARY_RES:
			cleaned = pat.sub(' ', cleaned)
	return cleaned
# @used-by :func:`agent_tools.source_grounding._extract_block_links()`
# @used-by :func:`agent_tools.source_grounding.extract_block_links()`
# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.__resolve_block_sources()`
def dfh_extract_block_links(block, root: Path, doc_path: Path | None) -> tuple[list[Path], list[str]]:
	local_all: list[Path] = []
	ext_urls: list[str] = []
	for tok in block.children or []:
		if 'link_open' == tok.type:
			href = tok.attrGet('href') or ''
			if href.startswith(('http://', 'https://')):
				ext_urls.append(href)
			else:
				rp = dfh_resolve_local_href(root, href, doc_path)
				if None is not rp and rp not in local_all:
					local_all.append(rp)
	return (local_all, ext_urls)
# @used-by :func:`agent_tools.source_grounding.extract_blockquote_quotes()`
# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_blockquote()`
# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__extract_blockquote_refs()`
def dfh_extract_blockquote_quotes(content: str, *, min_guillemet_len: int=8, allow_backtick_quotes: bool=False, min_orig_len: int=12) -> list[str]:
	r = list(re.findall(f'\\u00ab([^\\u00bb]{{{min_guillemet_len},}})\\u00bb', content or ''))
	if allow_backtick_quotes:
		r.extend(re.findall(f'`"([^"\\n]{{{min_guillemet_len},}})"`', content or ''))
	if not r:
		m_orig = re.search(f'(?:\\u041e\\u0440\\u0438\\u0433\\u0438\\u043d\\u0430\\u043b|Original)\\s*:\\s*["\\u00ab]?(.{{{min_orig_len},}})["\\u00bb]?$', (content or '').strip(), re.I | re.S)
		if m_orig:
			r.append(m_orig.group(1).strip(' "\u00ab\u00bb'))
	return r
# @used-by :func:`agent_tools.source_grounding._filter_primary_sources()`
# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.audit()`
# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.__resolve_block_sources()`
def dfh_filter_primary_sources(paths: list[Path]) -> list[Path]:
	src_dirs = {p.parent for p in paths if 'source.md' == p.name.lower()}
	r = [p for p in paths if not ('analysis.md' == p.name.lower() and p.parent in src_dirs)]
	if any(('tier_2' != dfh_classify_provenance_tier(p) for p in r)):
		r = [p for p in r if 'tier_2' != dfh_classify_provenance_tier(p)]
	return r
# @used-by :func:`agent_tools.source_grounding._is_client_deliverable_doc()`
# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_unlinked_deliverable_metrics()`
def dfh_is_client_deliverable_doc(doc_path: Path | None) -> bool:
	if None is doc_path or dfh_is_normative_harness_doc(doc_path):
		r = False
	else:
		norm_p = '/' + doc_path.as_posix().lower().lstrip('/')
		r = False if '/\ua616/' in norm_p or '/\ua66e/' in norm_p else any((seg.lower() in norm_p for seg in ('/letters/', '/result/', '/defects/', '/articles/', '/\u2c0f/\u227b/\u2655/\U0001f582/')))
	return r
# @used-by :func:`agent_tools.source_grounding._is_normative_harness_doc()`
# @used-by :func:`agent_tools.source_grounding.is_normative_harness_doc()`
# @used-by :func:`dfh_is_client_deliverable_doc()`
# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.__check_tier2_sole_evidence()`
# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.run()`
# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_touched_markdown()`
def dfh_is_normative_harness_doc(path: Path) -> bool:
	norm = '/' + path.as_posix().lower().lstrip('/')
	return '/.agents/rules/' not in norm and any((seg in norm for seg in ('/rules/', '/skills/', '/references/', '/platforms/')))
# @used-by :func:`agent_tools.source_grounding.is_primary_local_source()`
# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.__resolve_block_sources()`
def dfh_is_primary_local_source(path: Path) -> bool:
	tier = dfh_classify_provenance_tier(path)
	if 'tier_2' == tier:
		r = False
	elif 'tier_0' == tier:
		r = True
	else:
		r = path.as_posix().lower().endswith(_TIER0_SUFFIXES)
	return r
# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__persist_if_dirty()`
def dfh_is_read_only_grounding() -> bool:
	return bool(_READ_ONLY_GROUNDING.get())
# @used-by :func:`agent_tools.source_grounding.load_fact_ledger()`
# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.__load_ledger_tuples()`
def dfh_load_fact_ledger(root: Path) -> list[dict]:
	from agent_tools.path_registry import project_paths
	r: list[dict] = []
	ledger_path = project_paths(root, exact_root=True).facts_json
	if ledger_path.is_file():
		try:
			data = json.loads(ledger_path.read_text(encoding='utf-8'))
			if isinstance(data, dict) and isinstance(data.get('tuples'), list):
				r = data['tuples']
		except (OSError, ValueError):
			pass
	return r
# @used-by :func:`agent_tools.source_grounding.markdown_parser()`
# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.run()`
# @used-by :meth:`Df.Harness.Grounding.LocaleVerifier.LocaleVerifier.__extract_body_prose()`
# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.extract_markdown_refs()`
def dfh_markdown_parser():
	from agent_tools.markdown_links import parser as md_parser
	return md_parser(preserve_links=True)
# @used-by :func:`agent_tools.source_grounding.norm_quote_text()`
# @used-by :func:`dfh_quote_segments_present()`
# @used-by :meth:`Df.Harness.Grounding.ActiveCorpusBuilder.ActiveCorpusBuilder.resolve_text_helpers()`
# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_technical_spans()`
# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_external_refs()`
# @used-by :meth:`Df.Harness.Grounding.Tier0Index.Tier0Index.__build_hydrated_info()`
def dfh_norm_quote_text(value: str) -> str:
	cleaned = re.sub('[`*_~]+', '', value or '')
	cleaned = cleaned.replace('\u00a0', ' ').replace('\u2014', '-').replace('\u2013', '-').replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
	cleaned = re.sub('(?m)^>\\s*', '', cleaned)
	return ' '.join(cleaned.split()).lower()
# @used-by :func:`agent_tools.source_grounding._quote_segments_present()`
# @used-by :func:`agent_tools.source_grounding.quote_segments_present()`
# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_backtick_and_guillemet_quotes()`
# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_blockquote()`
# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.__check_guillemet_quote()`
# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_external_refs()`
def dfh_quote_segments_present(q_raw: str, obs_norm: str, min_seg_len: int=12) -> bool:
	raw_parts = [dfh_norm_quote_text(s) for s in re.split('\\[\\.\\.\\.\\]|\\(\\.\\.\\.\\)|\\[\\u2026\\]|\\(\\u2026\\)|\\.{3,}|\\u2026', q_raw)]
	segs = [s for s in raw_parts if min_seg_len <= len(s)]
	if segs:
		r = all((s in obs_norm for s in segs))
	elif 1 < len(raw_parts):
		short_segs = [s for s in raw_parts if 4 <= len(s)]
		r = not short_segs or all((s in obs_norm for s in short_segs))
	else:
		whole = raw_parts[0] if raw_parts else ''
		r = 8 > len(whole) or whole in obs_norm
	return r
# @used-by :func:`agent_tools.source_grounding.read_only_grounding()`
# @used-by :meth:`Df.Harness.Issue.CommentGrounder.CommentGrounder.check_grounding()`
# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_response_auditor_ingestor_and_tier0_index()`
@contextmanager
def dfh_read_only_grounding():
	tok = _READ_ONLY_GROUNDING.set(True)
	try:
		yield
	finally:
		_READ_ONLY_GROUNDING.reset(tok)
# @used-by :func:`agent_tools.source_grounding.resolve_local_href()`
# @used-by :func:`dfh_extract_block_links()`
def dfh_resolve_local_href(root: Path, href: str, doc_path: Path | None=None) -> Path | None:
	r: Path | None = None
	raw = urldefrag((href or '').strip())[0].split('?', 1)[0].strip()
	if raw and (not raw.lower().startswith(('http://', 'https://', 'mailto:', 'javascript:', 'conversation://', '#'))):
		from agent_tools.links import decode_file_uri
		p = Path(decode_file_uri(raw))
		cands = [p] if p.is_absolute() else ([doc_path.parent / p, Path(root) / p] if None is not doc_path else [Path(root) / p])
		for cand in cands:
			res = _resolve_candidate_file(cand)
			if None is not res:
				r = None if None is not doc_path and res == doc_path.resolve() else res
				break
	return r
