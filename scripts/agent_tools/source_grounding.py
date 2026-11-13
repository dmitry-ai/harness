# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate dual Tier 0 source caches into Tier0SourceIndex, extract LocalSourceGroundingAuditor, and isolate hosting domain rules in source_grounding.py":
# https://github.com/dmitry-ai/harness/issues/54
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
from urllib.parse import unquote, urldefrag
from markdown_it import MarkdownIt
from .claims import extract_verified_inline_calc_numbers, source_numeric_tokens, standalone_numbers
from .grounding_domains import (
	CLIENT_DELIVERABLE_METRIC_RE,
	META_REFUTATION_RE,
	TECHNICAL_SPAN_RE,
	TIER2_NUMERIC_DOMAIN_RE,
	_collect_json_fact_tuples,
	extract_domain_entities,
	extract_fact_tuples,
	extract_ticket_metadata,
	fact_tuple_contradictions,
	order_url_issues,
	ticket_author_issues,
	ticket_message_issues,
)
ALLOWED_MATH_GREEK = {'\u03b1', '\u03b2', '\u03b3', '\u03b4', '\u03b5', '\u03bb', '\u03bc', '\u03c0', '\u03c3', '\u03c4', '\u03c6', '\u03c9', '\u0394', '\u03a3', '\u03a9'}
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
	'bir', 'veya', 'olarak', 'ancak', 'sonra', 'kadar', 'gibi', 'daha', '\u091a\u0942\u0902\u0915\u093f',
}
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
_SOURCE_INFO_CACHE: dict[tuple[str, int, int], dict] = {}
_TIER0_INDEX_CACHE: dict[str, dict[str, dict]] = {}
_TIER0_MAX_FILE_BYTES = 512 * 1024
_TIER0_TEXT_SUFFIXES = {'.md', '.txt', '.json', '.yaml', '.yml', '.xml', '.csv', '.ini', '.conf', '.env', '.log', ''}
class LocalSourceGroundingAuditor:
	def __init__(self, root: Path, content: str, *, doc_path: Path | None=None, observed_texts: dict | None=None, cache: dict | None=None, visited: set | None=None):
		self.root = Path(root).resolve()
		self.content = content
		self.doc_path = Path(doc_path).resolve() if None is not doc_path else None
		self.observed_texts = observed_texts
		self.cache = cache if None is not cache else {}
		self.visited = visited if None is not visited else set()
		self.index = Tier0SourceIndex.for_root(self.root)
		self.errors: list[str] = []
		self.default_sources: list[Path] = []
		if None is not self.doc_path and (self.doc_path.parent / 'source.md').is_file() and 'source.md' != self.doc_path.name.lower():
			self.default_sources = [(self.doc_path.parent / 'source.md').resolve()]
		self.section_sources: list[Path] = list(self.default_sources)
		self.section_all_locals: list[Path] = list(self.default_sources)
		self.section_ext_urls: list[str] = []
		self.quote_depth = 0
		self.list_depth = 0
		self.linked_analyses: list[Path] = []
		self.ledger_tuples: list[dict] = []
	def _audit_block(self, block) -> None:
		if 'heading_open' == block.type:
			self._reset_section_scope()
		elif block.type in ('bullet_list_open', 'ordered_list_open'):
			self.list_depth += 1
		elif block.type in ('bullet_list_close', 'ordered_list_close'):
			self.list_depth = max(0, self.list_depth - 1)
		elif 'list_item_open' == block.type and 1 == self.list_depth:
			self._reset_section_scope()
		elif 'blockquote_open' == block.type:
			self.quote_depth += 1
		elif 'blockquote_close' == block.type:
			self.quote_depth = max(0, self.quote_depth - 1)
		elif 'inline' == block.type and block.content:
			local_all, ext_urls, filtered_locals, primary_here, orphan_analyses = self._resolve_block_sources(block)
			self._check_tier2_sole_evidence(block.content, local_all, orphan_analyses, primary_here, ext_urls)
			if not primary_here:
				if ext_urls and (not self.section_ext_urls):
					self.section_ext_urls = list(ext_urls)
			else:
				self.section_sources = primary_here
				self.section_all_locals = list(dict.fromkeys(filtered_locals + primary_here))
				self.section_ext_urls = list(ext_urls)
			self._check_relational_operands(block.content, filtered_locals, ext_urls)
			active_primary = primary_here or self.section_sources or self.default_sources
			if not active_primary:
				self._check_unlinked_deliverable_metrics(block.content)
			else:
				infos, combined_raw, combined_norm, ev_nums, src_label = self._build_active_corpus(filtered_locals, ext_urls, active_primary)
				if 0 < self.quote_depth:
					self._check_blockquote(block.content, combined_norm, src_label)
				else:
					ticket_infos = [inf for inf in infos if inf['is_ticket_source']]
					valid_msg_nums = {n for inf in ticket_infos for n in inf['msg_nums']}
					bound_ticket_ids = {inf['ticket_id'] for inf in ticket_infos if inf['ticket_id']}
					any_cyrillic_source = any((inf['has_cyrillic'] for inf in infos))
					for line in block.content.split('\n'):
						self._check_prose_line(line.strip(), infos, combined_raw, combined_norm, ev_nums, src_label, ticket_infos, valid_msg_nums, bound_ticket_ids, any_cyrillic_source)
	def _audit_linked_analyses(self) -> None:
		for ap in self.linked_analyses:
			try:
				a_text = ap.read_text(encoding='utf-8')
			except OSError:
				a_text = None
			if None is not a_text:
				sub_errs = LocalSourceGroundingAuditor(self.root, a_text, doc_path=ap, observed_texts=self.observed_texts, cache=self.cache, visited=self.visited).run()
				for se in sub_errs[:5]:
					self.errors.append(f'Linked {ap.parent.parent.name}/{ap.name} -> {se}')
	def _build_active_corpus(self, filtered_locals: list[Path], ext_urls: list[str], active_primary: list[Path]) -> tuple[list[dict], str, str, set[str], str]:
		active_locals = _filter_primary_sources(list(dict.fromkeys(filtered_locals + self.section_all_locals + active_primary)))
		active_exts = list(dict.fromkeys(ext_urls + self.section_ext_urls))
		infos = [self.index.load_source_info(p, self.cache) for p in active_locals]
		ext_blobs: list[str] = []
		if self.observed_texts:
			for u in active_exts:
				nu = urldefrag(u.strip())[0].rstrip('/')
				for t in self.observed_texts.get(nu) or []:
					ext_blobs.append(t)
		combined_raw = '\n'.join([inf['raw'] for inf in infos] + ext_blobs)
		combined_norm = norm_quote_text(combined_raw)
		ev_nums = set().union(*(inf['nums'] for inf in infos)) if infos else set()
		if ext_blobs:
			ev_nums.update(_source_numeric_tokens('\n'.join(ext_blobs)))
		return (infos, combined_raw, combined_norm, ev_nums, ', '.join((p.name for p in active_primary[:2])))
	def _check_blockquote(self, text: str, combined_norm: str, src_label: str) -> None:
		if not META_REFUTATION_RE.search(text):
			for bq in extract_blockquote_quotes(text):
				if not quote_segments_present(bq, combined_norm, 12):
					preview = ' '.join(bq.split())[:80]
					self.errors.append(f'VERIFY-1 / LINK-1: Blockquote \u00ab{preview}\u00bb attributed to {src_label} is absent from the primary source')
	def _check_prose_line(self, sline: str, infos: list[dict], combined_raw: str, combined_norm: str, ev_nums: set[str], src_label: str, ticket_infos: list[dict], valid_msg_nums: set[int], bound_ticket_ids: set[str], any_cyrillic_source: bool) -> None:
		if sline and (not META_REFUTATION_RE.search(sline)):
			for bq_str in re.findall('`["\\u201c]([^"\\u201d`]{8,})["\\u201d]`', sline):
				if 2 <= len(re.findall('[A-Za-z0-9]{2,}', bq_str)) and (not _quote_segments_present(bq_str, combined_norm, 8)):
					preview = ' '.join(bq_str.split())[:80]
					self.errors.append(f'VERIFY-1 / LINK-1: Quoted literal "{preview}" attributed to {src_label} is absent from the primary source')
			sline_for_quotes = re.sub('\\(\\u0430\\s+\\u043d\\u0435\\s+\\u00ab[^\\u00bb]+\\u00bb\\)', ' ', sline, flags=re.I)
			for gq in re.findall('\\u00ab([^\\u00bb]{10,})\\u00bb', sline_for_quotes):
				has_cyr = bool(re.search('[\\u0400-\\u04ff]', gq))
				if not has_cyr:
					if 2 <= len(re.findall('[A-Za-z0-9]{2,}', gq)) and (not _quote_segments_present(gq, combined_norm, 12)):
						preview = ' '.join(gq.split())[:80]
						self.errors.append(f'VERIFY-1 / LINK-1: Verbatim quote \u00ab{preview}\u00bb attributed to {src_label} is absent from the primary source')
				elif any_cyrillic_source and 25 <= len(gq.strip()) and re.search('(?:\\u043f\\u0438\\u0448\\u0435\\u0442|\\u043d\\u0430\\u043f\\u0438\\u0441\\u0430\\u043b\\w*|\\u0437\\u0430\\u044f\\u0432\\u0438\\u043b\\w*|\\u0441\\u043a\\u0430\\u0437\\u0430\\u043d\\u043e|\\u0446\\u0438\\u0442\\u0430\\u0442\\u0430)\\s*:\\s*\\u00ab', sline, re.I):
					if not _quote_segments_present(gq, combined_norm, 15):
						preview = ' '.join(gq.split())[:80]
						self.errors.append(f'VERIFY-1 / LINK-1: Verbatim quote \u00ab{preview}\u00bb attributed to {src_label} is absent from the primary source')
			if ticket_infos:
				self.errors.extend(ticket_author_issues(sline, combined_norm, src_label))
			for ungrounded_num in _line_grounded_numbers_check(sline, ev_nums, valid_msg_nums, bound_ticket_ids, bool(ticket_infos)):
				self.errors.append(f'VERIFY-1 / DOC-1: Unverified numeric figure or identifier ({ungrounded_num}) attributed to {src_label} is absent from the primary source')
			self.errors.extend(order_url_issues(sline, ev_nums, combined_raw, src_label))
			self.errors.extend(fact_tuple_contradictions(sline, infos, ledger_tuples=self.ledger_tuples))
			for code_span in re.findall('`([^`\\n]{3,60})`', sline):
				c_strip = code_span.strip()
				if TECHNICAL_SPAN_RE.match(c_strip):
					c_lookup = c_strip.lstrip('#')
					if norm_quote_text(c_strip) not in combined_norm and c_strip.lower() not in combined_raw.lower() and c_lookup.lower() not in combined_raw.lower():
						self.errors.append(f'VERIFY-1 / DOC-1: Technical literal `{c_strip}` attributed to {src_label} is absent from the primary source')
	def _check_relational_operands(self, text: str, filtered_locals: list[Path], ext_urls: list[str]) -> None:
		if RELATIONAL_MOD_RE.search(text) and (not META_REFUTATION_RE.search(text)):
			rel_operands = list(dict.fromkeys(filtered_locals + self.section_all_locals))
			if 2 > len(rel_operands) + len(ext_urls):
				self.errors.append('VERIFY-1 / LINK-1: Relational modification claim requires at least two distinct primary source operands (observed file and baseline reference), but fewer than 2 sources are linked')
			elif 2 <= len(rel_operands):
				op_hashes = {self.index.load_source_info(p, self.cache)['sha256'] for p in rel_operands if self.index.load_source_info(p, self.cache)['sha256']}
				if 1 == len(op_hashes):
					self.errors.append('VERIFY-1 / LINK-1: Relational modification claim is refuted because the linked local source operands are byte-identical (matching SHA-256)')
	def _check_tier2_sole_evidence(self, text: str, local_all: list[Path], orphan_analyses: list[Path], primary_here: list[Path], ext_urls: list[str]) -> None:
		tier2_here = [p for p in local_all if 'tier_2' == classify_provenance_tier(p, self.root)] + orphan_analyses
		if tier2_here and (not primary_here) and (not ext_urls) and (not META_REFUTATION_RE.search(text)):
			non_analysis_tier2 = [p for p in tier2_here if ('analysis.md' != p.name.lower() or p in orphan_analyses) and (not _is_normative_harness_doc(p))]
			if non_analysis_tier2 and TIER2_NUMERIC_DOMAIN_RE.search(text) and standalone_numbers(text):
				self.errors.append(f'VERIFY-1 / SCOPE-1: Tier 2 file ({non_analysis_tier2[0].name}) cannot serve as sole primary evidence for factual or numeric claims; cite a Tier 0 primary observation')
				for disc in self.index.discover_entities(text):
					dp = (self.root / disc['path']).resolve()
					if dp.is_file() and dp not in primary_here:
						primary_here.append(dp)
	def _check_unlinked_deliverable_metrics(self, text: str) -> None:
		if _is_client_deliverable_doc(self.doc_path) and 0 == self.quote_depth and (not META_REFUTATION_RE.search(text)):
			if CLIENT_DELIVERABLE_METRIC_RE.search(text):
				self.errors.append('VERIFY-1 / LINK-1: Client deliverable block asserts quantitative metrics or transaction/order identifiers without linking to a Tier 0 primary source in \ua616/KB/Evidence/')
	def _load_ledger_tuples(self) -> list[dict]:
		r: list[dict] = []
		seen_keys: set[tuple] = set()
		for tup in load_fact_ledger(self.root):
			tkey = (tup.get('entity'), tup.get('attribute'), tup.get('value'), tup.get('source_locator'))
			if tkey not in seen_keys:
				seen_keys.add(tkey)
				r.append(tup)
		for disc in self.index.discover_entities(self.content):
			dp = (self.root / disc['path']).resolve()
			if dp.is_file():
				for tup in self.index.load_source_info(dp, self.cache).get('fact_tuples') or []:
					tkey = (tup.get('entity'), tup.get('attribute'), tup.get('value'), tup.get('source_locator'))
					if tkey not in seen_keys:
						seen_keys.add(tkey)
						r.append(tup)
		return r
	def _reset_section_scope(self) -> None:
		self.section_sources = list(self.default_sources)
		self.section_all_locals = list(self.default_sources)
		self.section_ext_urls = []
	def _resolve_block_sources(self, block) -> tuple[list[Path], list[str], list[Path], list[Path], list[Path]]:
		local_all, ext_urls = _extract_block_links(block, self.root, self.doc_path)
		sibling_tier0_for_analysis: list[Path] = []
		orphan_analyses: list[Path] = []
		for lp in local_all:
			if 'analysis.md' == lp.name.lower():
				if not (lp.parent / 'source.md').is_file():
					orphan_analyses.append(lp)
				else:
					if lp not in self.linked_analyses:
						self.linked_analyses.append(lp)
					sib_src = (lp.parent / 'source.md').resolve()
					if sib_src not in sibling_tier0_for_analysis:
						sibling_tier0_for_analysis.append(sib_src)
		filtered_locals = _filter_primary_sources(local_all)
		primary_here = [p for p in filtered_locals if is_primary_local_source(p)]
		for sib_src in sibling_tier0_for_analysis:
			if sib_src not in primary_here:
				primary_here.append(sib_src)
		return (local_all, ext_urls, filtered_locals, primary_here, orphan_analyses)
	def run(self) -> list[str]:
		r: list[str] = []
		if self.content and isinstance(self.content, str):
			skip = False
			if None is not self.doc_path:
				if _is_normative_harness_doc(self.doc_path) or str(self.doc_path) in self.visited:
					skip = True
				else:
					self.visited.add(str(self.doc_path))
			if not skip:
				self.ledger_tuples = self._load_ledger_tuples()
				for block in markdown_parser().parse(self.content):
					self._audit_block(block)
				self._audit_linked_analyses()
				r = list(dict.fromkeys(self.errors))
		return r
class Tier0SourceIndex:
	CACHE_SCHEMA_VERSION = 2
	_INDICES: dict[str, 'Tier0SourceIndex'] = {}
	def __init__(self, root: Path):
		self.root = Path(root).resolve()
		self.root_key = str(self.root)
		self.cache_file = self.root / '\ua616' / 'data' / 'grounding-cache.json'
		self.entries: dict[str, dict] = {}
		self._disk_loaded = False
	def _build_hydrated_info(self, path: Path, rp: Path, stat_key: tuple[str, int, int] | None, raw: str, sha256: str, tuples: list[dict]) -> dict:
		extra = [raw]
		if '.json' == path.suffix.lower() and raw.strip():
			try:
				_json_scalar_strings(json.loads(raw), extra)
			except ValueError:
				pass
		combined_raw = '\n'.join(extra)
		is_ticket_source, msg_nums, ticket_id = extract_ticket_metadata(path, raw)
		r = {'path': path, 'sha256': sha256, 'raw': combined_raw, 'norm': norm_quote_text(combined_raw), 'nums': _source_numeric_tokens(combined_raw), 'is_ticket_source': is_ticket_source, 'msg_nums': msg_nums, 'has_cyrillic': bool(re.search('[\\u0400-\\u04ff]{3,}', raw)), 'ticket_id': ticket_id, 'tier': classify_provenance_tier(path, self.root), 'fact_tuples': tuples, '_raw_source': raw}
		if None is not stat_key:
			_SOURCE_INFO_CACHE[stat_key] = r
		return r
	def _candidate_files(self, tickets: list[str] | tuple[str, ...]=()) -> list[Path]:
		r: list[Path] = []
		seen: set[Path] = set()
		for sub in ('\ua616/KB/Evidence', 'source', 'KB', 'tickets'):
			base = self.root / sub
			if base.is_dir():
				for dirpath, dirs, filenames in os.walk(base):
					dirs[:] = sorted((d for d in dirs if d.lower() not in ('http', 'reviews', 'github')))
					dpath = Path(dirpath)
					for fname in sorted(filenames):
						pname = fname.lower()
						p = dpath / fname
						if p.suffix.lower() in _TIER0_TEXT_SUFFIXES and (not pname.startswith('extracted-')) and ('observation.json' != pname):
							try:
								ok_size = _TIER0_MAX_FILE_BYTES >= p.stat().st_size
							except OSError:
								ok_size = False
							if ok_size and 'tier_0' == classify_provenance_tier(p, self.root):
								rp = p.resolve()
								if rp not in seen:
									seen.add(rp)
									r.append(rp)
		for p in sorted(self.root.glob('*/KB/source.md')):
			if p.is_file():
				rp = p.resolve()
				if rp not in seen:
					seen.add(rp)
					r.append(rp)
		for tid in tickets:
			for t_cand in (self.root / tid / 'KB' / 'source.md', self.root / tid / 'source.md', self.root / 'tickets' / tid / 'KB' / 'source.md', self.root / 'tickets' / tid / 'source.md'):
				if t_cand.is_file():
					rp = t_cand.resolve()
					if rp not in seen:
						seen.add(rp)
						r.append(rp)
		return r
	def _ensure_disk_loaded(self) -> None:
		if not self._disk_loaded:
			self._disk_loaded = True
			existing = _TIER0_INDEX_CACHE.get(self.root_key)
			if isinstance(existing, dict) and existing:
				self.entries = existing
			else:
				if self.cache_file.is_file():
					try:
						loaded = json.loads(self.cache_file.read_text(encoding='utf-8'))
						if isinstance(loaded, dict) and self.CACHE_SCHEMA_VERSION == loaded.get('version') and isinstance(loaded.get('files'), dict):
							self.entries = loaded['files']
					except (OSError, ValueError):
						self.entries = {}
				_TIER0_INDEX_CACHE[self.root_key] = self.entries
	def _persist_if_dirty(self, dirty: bool) -> None:
		if (dirty or (self.entries and (not self.cache_file.is_file()))) and (self.cache_file.parent.is_dir() or (self.root / '\ua616').is_dir()):
			try:
				self.cache_file.parent.mkdir(parents=True, exist_ok=True)
				self.cache_file.write_text(json.dumps({'version': self.CACHE_SCHEMA_VERSION, 'files': self.entries}, ensure_ascii=False) + '\n', encoding='utf-8')
			except OSError:
				pass
	def discover_entities(self, text: str) -> list[dict]:
		r: list[dict] = []
		if text and isinstance(text, str):
			dom = extract_domain_entities(text)
			tickets, plans, metrics = (dom['tickets'], dom['plans'], dom['metrics'])
			if tickets or plans or metrics:
				candidates, mem_idx = self.load_index(tickets)
				for rp in candidates:
					rel = self.locator_for(rp)
					entry = mem_idx.get(rel)
					if isinstance(entry, dict):
						file_tickets = set(entry.get('tickets') or ())
						file_plans = set(entry.get('plans_norm') or ())
						file_metrics = set(entry.get('metrics') or ())
						rp_posix = rp.as_posix()
						matched_entities: list[str] = []
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
							r.append({'path': rel, 'sha256': entry['sha256'], 'tier': 'tier_0', 'matched_entities': matched_entities})
		return r
	def ensure_entry(self, rp: Path) -> tuple[str, dict | None, bool]:
		self._ensure_disk_loaded()
		r: tuple[str, dict | None, bool] = ('', None, False)
		try:
			st = rp.stat()
			mtime_ns, size = (st.st_mtime_ns, st.st_size)
		except OSError:
			mtime_ns, size = (-1, -1)
		if 0 <= mtime_ns:
			rel = self.locator_for(rp)
			cached = self.entries.get(rel)
			if isinstance(cached, dict) and cached.get('mtime_ns') == mtime_ns and (cached.get('size') == size) and isinstance(cached.get('sha256'), str):
				r = (rel, cached, False)
			else:
				stat_key = (str(rp), mtime_ns, size)
				hydrated = _SOURCE_INFO_CACHE.get(stat_key)
				if isinstance(hydrated, dict) and hydrated.get('sha256') and (None is not hydrated.get('_raw_source')):
					raw = hydrated['_raw_source']
					dom = extract_domain_entities(raw, include_substring_metrics=True)
					entry = {'mtime_ns': mtime_ns, 'size': size, 'sha256': hydrated['sha256'], 'tickets': dom['tickets'], 'plans_norm': dom['plans_norm'], 'metrics': dom['metrics'], 'fact_tuples': hydrated['fact_tuples']}
					self.entries[rel] = entry
					r = (rel, entry, True)
				else:
					try:
						raw_bytes = rp.read_bytes()
						raw = raw_bytes.decode('utf-8', errors='replace')
						ok_read = True
					except OSError:
						raw_bytes, raw, ok_read = (b'', '', False)
					if not ok_read:
						r = (rel, None, False)
					else:
						sha256 = hashlib.sha256(raw_bytes).hexdigest()
						dom = extract_domain_entities(raw, include_substring_metrics=True)
						tuples = extract_fact_tuples(rp, raw, root=self.root)
						entry = {'mtime_ns': mtime_ns, 'size': size, 'sha256': sha256, 'tickets': dom['tickets'], 'plans_norm': dom['plans_norm'], 'metrics': dom['metrics'], 'fact_tuples': tuples}
						self.entries[rel] = entry
						self._build_hydrated_info(rp, rp, stat_key, raw, sha256, tuples)
						r = (rel, entry, True)
		return r
	@classmethod
	def for_root(cls, root: Path) -> 'Tier0SourceIndex':
		resolved = Path(root).resolve()
		rkey = str(resolved)
		r = cls._INDICES.get(rkey)
		if None is r:
			r = cls(resolved)
			cls._INDICES[rkey] = r
		return r
	def load_index(self, tickets: list[str] | tuple[str, ...]=()) -> tuple[list[Path], dict[str, dict]]:
		self._ensure_disk_loaded()
		candidates = self._candidate_files(tickets)
		dirty = False
		for rp in candidates:
			_, _, changed = self.ensure_entry(rp)
			if changed:
				dirty = True
		self._persist_if_dirty(dirty)
		return (candidates, self.entries)
	def load_source_info(self, path: Path, cache: dict | None=None) -> dict:
		key = str(path)
		if None is not cache and key in cache:
			r = cache[key]
		else:
			self._ensure_disk_loaded()
			stat_key = None
			try:
				rp = path.resolve()
				st = rp.stat()
				stat_key = (str(rp), st.st_mtime_ns, st.st_size)
			except OSError:
				rp = path
			if None is not stat_key and stat_key in _SOURCE_INFO_CACHE:
				r = _SOURCE_INFO_CACHE[stat_key]
			else:
				rel = self.locator_for(rp) if None is not stat_key else ''
				cached_entry = self.entries.get(rel) if rel else None
				try:
					raw_bytes = rp.read_bytes() if None is not stat_key else b''
					raw = raw_bytes.decode('utf-8', errors='replace') if None is not stat_key else ''
				except OSError:
					raw_bytes, raw = (b'', '')
				if isinstance(cached_entry, dict) and None is not stat_key and cached_entry.get('mtime_ns') == stat_key[1] and (cached_entry.get('size') == stat_key[2]) and isinstance(cached_entry.get('sha256'), str):
					sha256 = cached_entry['sha256']
					tuples = cached_entry.get('fact_tuples') or []
				else:
					sha256 = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes or None is not stat_key else ''
					tuples = extract_fact_tuples(rp, raw, root=self.root)
					if None is not stat_key and 'tier_0' == classify_provenance_tier(rp, self.root) and (not rel.startswith('/')) and (':' not in rel):
						dom = extract_domain_entities(raw, include_substring_metrics=True)
						self.entries[rel] = {'mtime_ns': stat_key[1], 'size': stat_key[2], 'sha256': sha256, 'tickets': dom['tickets'], 'plans_norm': dom['plans_norm'], 'metrics': dom['metrics'], 'fact_tuples': tuples}
				r = self._build_hydrated_info(path, rp, stat_key, raw, sha256, tuples)
			if None is not cache:
				cache[key] = r
		return r
	def locator_for(self, path: Path) -> str:
		try:
			r = path.resolve().relative_to(self.root).as_posix()
		except ValueError:
			r = path.as_posix()
		return r
	def sync_ledger(self) -> dict:
		candidates, mem_idx = self.load_index()
		tuples: list[dict] = []
		for rp in candidates:
			entry = mem_idx.get(self.locator_for(rp))
			if isinstance(entry, dict) and isinstance(entry.get('fact_tuples'), list):
				tuples.extend(entry['fact_tuples'])
		r = {'version': 1, 'tuple_count': len(tuples), 'tuples': tuples}
		data_dir = self.root / '\ua616' / 'data'
		if tuples or data_dir.is_dir() or (self.root / '\ua616').is_dir():
			data_dir.mkdir(parents=True, exist_ok=True)
			(data_dir / 'facts.json').write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
		return r
def _char_script(ch: str) -> str:
	name = unicodedata.name(ch, '')
	if not name:
		r = 'UNKNOWN'
	else:
		head = name.split()[0]
		r = 'CJK' if head in ('CJK', 'IDEOGRAPHIC', 'HIRAGANA', 'KATAKANA', 'HANGUL') else head
	return r
def _extract_block_links(block, root: Path, doc_path: Path | None):
	return extract_block_links(block, root, doc_path)
def _filter_primary_sources(paths: list[Path]) -> list[Path]:
	src_dirs = {p.parent for p in paths if 'source.md' == p.name.lower()}
	r = [p for p in paths if not ('analysis.md' == p.name.lower() and p.parent in src_dirs)]
	if any(('tier_2' != classify_provenance_tier(p) for p in r)):
		r = [p for p in r if 'tier_2' != classify_provenance_tier(p)]
	return r
def _get_tier0_file_entry(root: Path, rp: Path, mem_idx: dict[str, dict]) -> tuple[str, dict | None, bool]:
	idx = Tier0SourceIndex.for_root(root)
	idx.entries = mem_idx
	_TIER0_INDEX_CACHE[idx.root_key] = mem_idx
	idx._disk_loaded = True
	return idx.ensure_entry(rp)
def _infer_source_root(path: Path) -> Path | None:
	r = None
	try:
		rp = path.resolve()
	except OSError:
		rp = None
	if None is not rp:
		for inst in Tier0SourceIndex._INDICES.values():
			try:
				rp.relative_to(inst.root)
				if None is r or len(str(inst.root)) > len(str(r)):
					r = inst.root
			except ValueError:
				pass
	return r
def _is_client_deliverable_doc(doc_path: Path | None) -> bool:
	if None is doc_path or is_normative_harness_doc(doc_path):
		r = False
	else:
		norm_p = '/' + doc_path.as_posix().lower().lstrip('/')
		r = False if '/\ua616/' in norm_p or '/\ua66e/' in norm_p else any((seg in norm_p for seg in ('/letters/', '/result/', '/defects/')))
	return r
def _is_normative_harness_doc(path: Path) -> bool:
	return is_normative_harness_doc(path)
def _json_scalar_strings(obj, out: list[str]) -> None:
	if None is not obj and (not isinstance(obj, (dict, list, float))):
		out.append(str(obj))
	elif isinstance(obj, float):
		out.append(f'{obj:.2f}')
		out.append(str(obj))
	elif isinstance(obj, list):
		for item in obj:
			_json_scalar_strings(item, out)
	elif isinstance(obj, dict):
		for k, v in obj.items():
			out.append(str(k))
			_json_scalar_strings(v, out)
def _line_grounded_numbers_check(sline: str, ev_nums: set[str], valid_msg_nums: set[int], bound_ticket_ids: set[str], is_ticket: bool) -> list[str]:
	r: list[str] = []
	if is_ticket:
		r.extend(ticket_message_issues(sline, valid_msg_nums, bound_ticket_ids))
	verified_calc_nums, calc_errors = extract_verified_inline_calc_numbers(sline, ev_nums)
	ev_with_calc = set(ev_nums) | set(verified_calc_nums)
	for calc_err in calc_errors:
		r.append(f'{calc_err} (inline arithmetic mismatch)')
	cleaned = re.sub('\\[[^\\]]*\\]\\([^)]*\\)', ' ', sline)
	cleaned = re.sub('https?://\\S+|file://\\S+', ' ', cleaned)
	cleaned = cleaned.replace('`', ' ')
	cleaned = re.sub('\\b\\d+(?:[.,]\\d+)?\\s*%', ' ', cleaned)
	cleaned = re.sub('(?i)\\b(?:line|lines|\\u0441\\u0442\\u0440\\u043e\\u043a\\w*)\\s+\\d+(?:\\s*[\\u2013\\u2014-]\\s*\\d+)?', ' ', cleaned)
	for num in sorted(standalone_numbers(cleaned)):
		norm_num = num.replace(',', '')
		if not (1 == len(norm_num) and norm_num.isdigit()):
			if num not in ev_with_calc and norm_num not in ev_with_calc:
				r.append(num)
	return r
def _load_local_source_info(path: Path, cache: dict | None=None, *, root: Path | None=None) -> dict:
	eff_root = root if None is not root else _infer_source_root(path)
	if None is not eff_root:
		r = Tier0SourceIndex.for_root(eff_root).load_source_info(path, cache)
	else:
		key = str(path)
		if None is not cache and key in cache:
			r = cache[key]
		else:
			stat_key = None
			try:
				rp = path.resolve()
				st = rp.stat()
				stat_key = (str(rp), st.st_mtime_ns, st.st_size)
			except OSError:
				rp = path
			if None is not stat_key and stat_key in _SOURCE_INFO_CACHE:
				r = _SOURCE_INFO_CACHE[stat_key]
			else:
				try:
					raw_bytes = rp.read_bytes() if None is not stat_key else b''
					raw = raw_bytes.decode('utf-8', errors='replace') if None is not stat_key else ''
					sha256 = hashlib.sha256(raw_bytes).hexdigest() if None is not stat_key else ''
				except OSError:
					raw, sha256 = ('', '')
				extra = [raw]
				if '.json' == path.suffix.lower() and raw.strip():
					try:
						_json_scalar_strings(json.loads(raw), extra)
					except ValueError:
						pass
				combined_raw = '\n'.join(extra)
				is_ticket_source, msg_nums, ticket_id = extract_ticket_metadata(path, raw)
				r = {'path': path, 'sha256': sha256, 'raw': combined_raw, 'norm': norm_quote_text(combined_raw), 'nums': _source_numeric_tokens(combined_raw), 'is_ticket_source': is_ticket_source, 'msg_nums': msg_nums, 'has_cyrillic': bool(re.search('[\\u0400-\\u04ff]{3,}', raw)), 'ticket_id': ticket_id, 'tier': classify_provenance_tier(path), 'fact_tuples': extract_fact_tuples(path, raw), '_raw_source': raw}
				if None is not stat_key:
					_SOURCE_INFO_CACHE[stat_key] = r
			if None is not cache:
				cache[key] = r
	return r
def _load_tier0_index(root: Path, tickets: list[str] | tuple[str, ...]=()) -> tuple[list[Path], dict[str, dict]]:
	return Tier0SourceIndex.for_root(root).load_index(tickets)
def _quote_segments_present(q_raw: str, obs_norm: str, min_seg_len: int=12) -> bool:
	return quote_segments_present(q_raw, obs_norm, min_seg_len)
_source_numeric_tokens = source_numeric_tokens
def _tier0_candidate_files(root: Path, tickets: list[str] | tuple[str, ...]=()) -> list[Path]:
	return Tier0SourceIndex.for_root(root)._candidate_files(tickets)
def classify_provenance_tier(path: Path, root: Path | None=None) -> str:
	norm = '/' + path.as_posix().lower().lstrip('/')
	name = path.name.lower()
	if name in {'draft.md', 'draft.prev.md', 'context.md'} or '/.agents/rules/' in norm or '/rules/' in norm or ('/skills/' in norm) or ('/references/' in norm) or ('/platforms/' in norm) or ('/candidates/' in norm) or ('/data/scratch/' in norm) or ('/evidence/reviews/' in norm) or ('/res/' in norm) or norm.endswith('-audit.json'):
		r = 'tier_2'
	elif 'source.md' == name or ('/source/' in norm and 'analysis.md' != name) or ('/kb/evidence/' in norm and (not norm.endswith('-audit.json')) and ('/evidence/github/' not in norm) and ('/evidence/reviews/' not in norm)) or norm.endswith(('/kb/project.md', '/kb/projects.md', '/kb/evidence.md')) or ('/req/' in norm):
		r = 'tier_0'
	else:
		r = 'tier_1'
	return r
def detect_prose_locale(prose: str) -> dict:
	script_counts: dict[str, int] = {}
	for ch in prose or '':
		if ch.isalpha() and ch not in ALLOWED_MATH_GREEK:
			sc = _char_script(ch)
			script_counts[sc] = script_counts.get(sc, 0) + 1
	total_alpha = sum(script_counts.values())
	if 0 == total_alpha:
		r = {'dominant_script': 'NONE', 'dominant_ratio': 1.0, 'total_alpha': 0, 'script_counts': {}, 'locale_family': 'und'}
	else:
		dominant_script = max(script_counts.items(), key=lambda item: item[1])[0]
		dominant_ratio = script_counts[dominant_script] / total_alpha
		words = [w.lower() for w in re.findall('[^\\W\\d_]{2,}', prose, flags=re.UNICODE)]
		en_hits = sum((1 for w in words if w in EN_FUNCTION_WORDS))
		non_en_hits = sum((1 for w in words if w in NON_EN_LATIN_STOPWORDS))
		diacritic_words = sum((1 for w in words if any((127 < ord(c) and 'LATIN' == _char_script(c) for c in w))))
		if 'LATIN' != dominant_script:
			locale_family = dominant_script.lower()
		elif 6 <= len(words) and (non_en_hits > en_hits or (0 == en_hits and 2 <= diacritic_words)):
			locale_family = 'latin-non-en'
		else:
			locale_family = 'en'
		r = {'dominant_script': dominant_script, 'dominant_ratio': dominant_ratio, 'total_alpha': total_alpha, 'script_counts': script_counts, 'word_count': len(words), 'en_hits': en_hits, 'non_en_hits': non_en_hits, 'diacritic_words': diacritic_words, 'locale_family': locale_family}
	return r
def discover_entity_tier0_sources(root: Path, text: str) -> list[dict]:
	return Tier0SourceIndex.for_root(root).discover_entities(text)
def extract_authored_prose(text: str, *, is_title: bool=False) -> str:
	if not isinstance(text, str) or (not text.strip()):
		r = ''
	elif is_title:
		clean = re.sub('`[^`]*`', ' ', text)
		clean = re.sub('\\u00ab[^\\u00bb]*\\u00bb|\\u201c[^\\u201d]*\\u201d|"[^"]*"', ' ', clean)
		clean = re.sub('https?://\\S+|file://\\S+', ' ', clean)
		r = ' '.join(clean.split())
	else:
		parser = markdown_parser()
		quote_depth = 0
		chunks: list[str] = []
		for token in parser.parse(text):
			if 'blockquote_open' == token.type:
				quote_depth += 1
			elif 'blockquote_close' == token.type:
				quote_depth = max(0, quote_depth - 1)
			elif 0 == quote_depth and token.type not in ('fence', 'code_block', 'html_block') and ('inline' == token.type) and token.children:
				in_link = 0
				for child in token.children:
					if 'link_open' == child.type:
						in_link += 1
					elif 'link_close' == child.type:
						in_link = max(0, in_link - 1)
					elif 'text' == child.type:
						val = child.content or ''
						if not (0 < in_link and re.match('^(?:https?://|file://|[A-Za-z]:/|/)', val.strip())):
							chunks.append(val)
		joined = ' '.join(chunks)
		joined = re.sub('\\u00ab[^\\u00bb]*\\u00bb|\\u201c[^\\u201d]*\\u201d|"[^"\\n]{8,}"', ' ', joined)
		joined = re.sub('https?://\\S+|file://\\S+', ' ', joined)
		joined = re.sub('(?<![A-Za-z0-9])[A-Za-z]:/[^\\s)\\]>]+', ' ', joined)
		r = ' '.join(joined.split())
	return r
def extract_block_links(block, root: Path, doc_path: Path | None):
	local_all: list[Path] = []
	ext_urls: list[str] = []
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
def extract_blockquote_quotes(content: str, *, min_guillemet_len: int=8, allow_backtick_quotes: bool=False, min_orig_len: int=12) -> list[str]:
	r = list(re.findall(f'\\u00ab([^\\u00bb]{{{min_guillemet_len},}})\\u00bb', content or ''))
	if allow_backtick_quotes:
		r.extend(re.findall(f'`"([^"\\n]{{{min_guillemet_len},}})"`', content or ''))
	if not r:
		m_orig = re.search(f'(?:\\u041e\\u0440\\u0438\\u0433\\u0438\\u043d\\u0430\\u043b|Original)\\s*:\\s*["\\u00ab]?(.{{{min_orig_len},}})["\\u00bb]?$', (content or '').strip(), re.I | re.S)
		if m_orig:
			r.append(m_orig.group(1).strip(' "\u00ab\u00bb'))
	return r
def is_normative_harness_doc(path: Path) -> bool:
	norm = '/' + path.as_posix().lower().lstrip('/')
	return '/.agents/rules/' not in norm and any((seg in norm for seg in ('/rules/', '/skills/', '/references/', '/platforms/')))
def is_primary_local_source(path: Path) -> bool:
	tier = classify_provenance_tier(path)
	if 'tier_2' == tier:
		r = False
	elif 'tier_0' == tier:
		r = True
	else:
		r = path.as_posix().lower().endswith(('/kb/project.md', '/kb/projects.md', '/kb/evidence.md'))
	return r
def load_fact_ledger(root: Path) -> list[dict]:
	r: list[dict] = []
	ledger_path = Path(root).resolve() / '\ua616' / 'data' / 'facts.json'
	if ledger_path.is_file():
		try:
			data = json.loads(ledger_path.read_text(encoding='utf-8'))
			if isinstance(data, dict) and isinstance(data.get('tuples'), list):
				r = data['tuples']
		except (OSError, ValueError):
			pass
	return r
def local_source_grounding_issues(root: Path, content: str, *, doc_path: Path | None=None, observed_texts: dict | None=None, cache: dict | None=None, _visited: set | None=None) -> list[str]:
	return LocalSourceGroundingAuditor(root, content, doc_path=doc_path, observed_texts=observed_texts, cache=cache, visited=_visited).run()
def markdown_parser() -> MarkdownIt:
	r = MarkdownIt('commonmark', {'html': True})
	r.normalizeLink = lambda value: value
	r.validateLink = lambda value: True
	return r
def norm_quote_text(value: str) -> str:
	cleaned = re.sub('[`*_~]+', '', value or '')
	cleaned = cleaned.replace('\u00a0', ' ').replace('\u2014', '-').replace('\u2013', '-').replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
	cleaned = re.sub('(?m)^>\\s*', '', cleaned)
	return ' '.join(cleaned.split()).lower()
def quote_segments_present(q_raw: str, obs_norm: str, min_seg_len: int=12) -> bool:
	raw_parts = [norm_quote_text(s) for s in re.split('\\[\\.\\.\\.\\]|\\(\\.\\.\\.\\)|\\[\\u2026\\]|\\(\\u2026\\)|\\.{3,}|\\u2026', q_raw)]
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
def resolve_local_href(root: Path, href: str, doc_path: Path | None=None) -> Path | None:
	r = None
	raw = urldefrag((href or '').strip())[0].split('?', 1)[0].strip()
	if raw and (not raw.lower().startswith(('http://', 'https://', 'mailto:', 'javascript:', 'conversation://', '#'))):
		if not raw.lower().startswith('file://'):
			raw = unquote(raw)
		else:
			raw = unquote(raw[7:])
			if re.match('^/[A-Za-z]:/', raw):
				raw = raw[1:]
		candidates: list[Path] = []
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
				is_valid_file = res.is_file()
			except OSError:
				res, is_valid_file = (None, False)
			if is_valid_file and None is not res:
				r = None if None is not doc_path and res == doc_path.resolve() else res
				break
	return r
def sync_fact_ledger(root: Path) -> dict:
	return Tier0SourceIndex.for_root(root).sync_ledger()
def verify_target_locale(text: str, *, target_locale: str='en-US', container_text: str | None=None, is_title: bool=False, allow_explicit_english_request: bool=False, min_target_ratio: float=0.35, min_alpha: int=15) -> list[dict]:
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
				if 'LATIN' != c_info['dominant_script']:
					eff_target = c_info['dominant_script'].lower()
				elif 'en' == c_info['locale_family']:
					eff_target = 'en-US'
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
				r.append({'code': 'LOCALE_MISMATCH', 'target_locale': eff_target, 'detected_scripts': non_latin, 'message': f'TEXT-1: Authored prose contains non-Latin script characters [{", ".join((f"{sc} ({cnt} chars)" for sc, cnt in sorted(non_latin.items())))}] in a target "{eff_target}" container; write in {eff_target} and place foreign logs/quotes inside fenced code blocks or blockquotes'})
			elif 'latin-non-en' == info['locale_family'] and 6 <= info['word_count']:
				r.append({'code': 'LOCALE_MISMATCH', 'target_locale': eff_target, 'detected_locale': info['locale_family'], 'message': f'TEXT-1: Authored prose is in a non-English Latin language (en_hits={info["en_hits"]}, non_en_hits={info["non_en_hits"]}, diacritic_words={info["diacritic_words"]}) in a target "{eff_target}" container'})
	return r
