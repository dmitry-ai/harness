# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Grounding.BlockLineAuditor import BlockLineAuditor
from Df.Harness.Grounding.Tier0Index import Tier0Index
from Df.Harness.lib.grounding import META_REFUTATION_RE, RELATIONAL_MOD_RE, TIER2_NUMERIC_DOMAIN_RE, dfh_classify_provenance_tier, dfh_extract_block_links, dfh_filter_primary_sources, dfh_is_normative_harness_doc, dfh_is_primary_local_source, dfh_load_fact_ledger, dfh_markdown_parser
from agent_tools.claims import standalone_numbers
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class LocalSourceAuditor:
	# @used-by :func:`agent_tools.source_grounding.local_source_grounding_issues()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_local_grounding()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_touched_markdown()`
	# @used-by :meth:`Df.Harness.Issue.CommentGrounder.CommentGrounder.check_grounding()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__check_comments_evidence()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__lint_saved_issue_obj()`
	# @used-by :meth:`LocalSourceAuditor.__audit_linked_analyses()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_active_corpus_builder_and_block_line_auditor()`
	def __init__(self, root: Path, content: str, *, doc_path: Path | None=None, observed_texts: dict | None=None, cache: dict | None=None, visited: set | None=None) -> None:
		self.root = Path(root).resolve()
		self.content = content
		self.doc_path = Path(doc_path).resolve() if None is not doc_path else None
		self.observed_texts = observed_texts
		self.cache = cache if None is not cache else {}
		self.visited = visited if None is not visited else set()
		self.index = Tier0Index.for_root(self.root)
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
	# @used-by :meth:`LocalSourceAuditor.__load_ledger_tuples()`
	@staticmethod
	def __append_unique_tuple(tup: dict, seen_keys: set[tuple], out: list[dict]) -> None:
		tkey = (tup.get('entity'), tup.get('attribute'), tup.get('value'), tup.get('source_locator'))
		if tkey not in seen_keys:
			seen_keys.add(tkey)
			out.append(tup)
	# @used-by :meth:`LocalSourceAuditor.run()`
	def __audit_block(self, block) -> None:
		if 'heading_open' == block.type or ('list_item_open' == block.type and 1 == self.list_depth):
			self.__reset_section_scope()
		elif block.type in ('bullet_list_open', 'ordered_list_open'):
			self.list_depth += 1
		elif block.type in ('bullet_list_close', 'ordered_list_close'):
			self.list_depth = max(0, self.list_depth - 1)
		elif 'blockquote_open' == block.type:
			self.quote_depth += 1
		elif 'blockquote_close' == block.type:
			self.quote_depth = max(0, self.quote_depth - 1)
		elif 'inline' == block.type and block.content:
			self.__audit_inline_block(block)
	# @used-by :meth:`LocalSourceAuditor.__audit_block()`
	def __audit_inline_block(self, block) -> None:
		local_all, ext_urls, filtered_locals, primary_here, orphan_analyses = self.__resolve_block_sources(block)
		self.__check_tier2_sole_evidence(block.content, local_all, orphan_analyses, primary_here, ext_urls)
		if not primary_here:
			if ext_urls and (not self.section_ext_urls):
				self.section_ext_urls = list(ext_urls)
		else:
			self.section_sources = primary_here
			self.section_all_locals = list(dict.fromkeys(filtered_locals + primary_here))
			self.section_ext_urls = list(ext_urls)
		self.__check_relational_operands(block.content, filtered_locals, ext_urls)
		active_primary = primary_here or self.section_sources or self.default_sources
		BlockLineAuditor(self, block, filtered_locals, ext_urls, active_primary).audit()
	# @used-by :meth:`LocalSourceAuditor.run()`
	def __audit_linked_analyses(self) -> None:
		for ap in self.linked_analyses:
			try:
				a_text = ap.read_text(encoding='utf-8')
			except OSError:
				a_text = None
			if None is not a_text:
				sub_errs = LocalSourceAuditor(self.root, a_text, doc_path=ap, observed_texts=self.observed_texts, cache=self.cache, visited=self.visited).run()
				for se in sub_errs[:5]:
					self.errors.append(f'Linked {ap.parent.parent.name}/{ap.name} -> {se}')
	# @used-by :meth:`LocalSourceAuditor.__audit_inline_block()`
	def __check_relational_operands(self, text: str, filtered_locals: list[Path], ext_urls: list[str]) -> None:
		if RELATIONAL_MOD_RE.search(text) and (not META_REFUTATION_RE.search(text)):
			rel_operands = list(dict.fromkeys(filtered_locals + self.section_all_locals))
			if 2 > len(rel_operands) + len(ext_urls):
				self.errors.append('VERIFY-1 / LINK-1: Relational modification claim requires at least two distinct primary source operands (observed file and baseline reference), but fewer than 2 sources are linked')
			elif 2 <= len(rel_operands):
				op_hashes = {self.index.load_source_info(p, self.cache)['sha256'] for p in rel_operands if self.index.load_source_info(p, self.cache)['sha256']}
				if 1 == len(op_hashes):
					self.errors.append('VERIFY-1 / LINK-1: Relational modification claim is refuted because the linked local source operands are byte-identical (matching SHA-256)')
	# @used-by :meth:`LocalSourceAuditor.__audit_inline_block()`
	def __check_tier2_sole_evidence(self, text: str, local_all: list[Path], orphan_analyses: list[Path], primary_here: list[Path], ext_urls: list[str]) -> None:
		tier2_here = [p for p in local_all if 'tier_2' == dfh_classify_provenance_tier(p, self.root)] + orphan_analyses
		if tier2_here and (not primary_here) and (not ext_urls) and (not META_REFUTATION_RE.search(text)):
			non_analysis = [p for p in tier2_here if ('analysis.md' != p.name.lower() or p in orphan_analyses) and (not dfh_is_normative_harness_doc(p))]
			if non_analysis and TIER2_NUMERIC_DOMAIN_RE.search(text) and standalone_numbers(text):
				self.errors.append(f'VERIFY-1 / SCOPE-1: Tier 2 file ({non_analysis[0].name}) cannot serve as sole primary evidence for factual or numeric claims; cite a Tier 0 primary observation')
				for disc in self.index.discover_entities(text):
					dp = (self.root / disc['path']).resolve()
					if dp.is_file() and dp not in primary_here:
						primary_here.append(dp)
	# @used-by :meth:`LocalSourceAuditor.__resolve_block_sources()`
	def __collect_analysis_siblings(self, local_all: list[Path]) -> tuple[list[Path], list[Path]]:
		sibling_tier0: list[Path] = []
		orphan_analyses: list[Path] = []
		for lp in local_all:
			if 'analysis.md' == lp.name.lower():
				if not (lp.parent / 'source.md').is_file():
					orphan_analyses.append(lp)
				else:
					if lp not in self.linked_analyses:
						self.linked_analyses.append(lp)
					sib = (lp.parent / 'source.md').resolve()
					if sib not in sibling_tier0:
						sibling_tier0.append(sib)
		return (sibling_tier0, orphan_analyses)
	# @used-by :meth:`LocalSourceAuditor.run()`
	def __load_ledger_tuples(self) -> list[dict]:
		r: list[dict] = []
		seen_keys: set[tuple] = set()
		for tup in dfh_load_fact_ledger(self.root):
			self.__append_unique_tuple(tup, seen_keys, r)
		for disc in self.index.discover_entities(self.content):
			dp = (self.root / disc['path']).resolve()
			if dp.is_file():
				for tup in self.index.load_source_info(dp, self.cache).get('fact_tuples') or []:
					self.__append_unique_tuple(tup, seen_keys, r)
		return r
	# @used-by :meth:`LocalSourceAuditor.__audit_block()`
	def __reset_section_scope(self) -> None:
		self.section_sources = list(self.default_sources)
		self.section_all_locals = list(self.default_sources)
		self.section_ext_urls = []
	# @used-by :meth:`LocalSourceAuditor.__audit_inline_block()`
	def __resolve_block_sources(self, block) -> tuple[list[Path], list[str], list[Path], list[Path], list[Path]]:
		local_all, ext_urls = dfh_extract_block_links(block, self.root, self.doc_path)
		sibling_tier0, orphan_analyses = self.__collect_analysis_siblings(local_all)
		filtered_locals = dfh_filter_primary_sources(local_all)
		primary_here = [p for p in filtered_locals if dfh_is_primary_local_source(p)]
		for sib in sibling_tier0:
			if sib not in primary_here:
				primary_here.append(sib)
		return (local_all, ext_urls, filtered_locals, primary_here, orphan_analyses)
	# @used-by :func:`agent_tools.source_grounding.local_source_grounding_issues()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_local_grounding()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_touched_markdown()`
	# @used-by :meth:`Df.Harness.Issue.CommentGrounder.CommentGrounder.check_grounding()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__check_comments_evidence()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__lint_saved_issue_obj()`
	# @used-by :meth:`LocalSourceAuditor.__audit_linked_analyses()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_active_corpus_builder_and_block_line_auditor()`
	def run(self) -> list[str]:
		r: list[str] = []
		if self.content and isinstance(self.content, str):
			skip = False
			if None is not self.doc_path:
				if dfh_is_normative_harness_doc(self.doc_path) or str(self.doc_path) in self.visited:
					skip = True
				else:
					self.visited.add(str(self.doc_path))
			if not skip:
				self.ledger_tuples = self.__load_ledger_tuples()
				for block in dfh_markdown_parser().parse(self.content):
					self.__audit_block(block)
				self.__audit_linked_analyses()
				r = list(dict.fromkeys(self.errors))
		return r