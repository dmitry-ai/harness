# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import urldefrag
from Df.Harness.lib.grounding import dfh_norm_quote_text
from agent_tools.claims import source_numeric_tokens
import sys
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ActiveCorpusBuilder:
	# @used-by :func:`agent_tools.grounding_helpers.build_active_corpus_cached()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.audit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_active_corpus_builder_and_block_line_auditor()`
	def __init__(self, auditor, active_locals: list[Path], active_exts: list[str], active_primary: list[Path], norm_fn=None, num_fn=None) -> None:
		self.__auditor = auditor
		self.__active_locals = active_locals
		self.__active_exts = active_exts
		self.__active_primary = active_primary
		self.__norm_fn, self.__num_fn = self.resolve_text_helpers(norm_fn, num_fn)
	# @used-by :meth:`ActiveCorpusBuilder.build()`
	@staticmethod
	def __load_ext_url_entry(bucket: dict, nu: str, norm_fn, num_fn) -> tuple[str, str, set[str]]:
		r = bucket['urls'].get(nu)
		if None is r:
			blobs = [str(t) for t in ((bucket['obs'] or {}).get(nu) or ()) if t]
			raw = '\n'.join(blobs)
			r = (raw, norm_fn(raw) if raw else '', num_fn(raw) if raw else set())
			bucket['urls'][nu] = r
		return r
	# @used-by :meth:`ActiveCorpusBuilder.build()`
	@staticmethod
	def __norm_ext_urls(active_exts: list[str]) -> tuple[str, ...]:
		seen: list[str] = []
		for u in active_exts:
			s = (u or '').strip()
			if s:
				nu = urldefrag(s)[0].rstrip('/')
				if nu not in seen:
					seen.append(nu)
		return tuple(seen)
	# @used-by :meth:`ActiveCorpusBuilder.build()`
	@staticmethod
	def __obs_bucket(cache: dict, observed_texts: dict | None) -> dict:
		store = cache.setdefault('__obs_buckets__', {})
		oid = 0 if None is observed_texts else id(observed_texts)
		bucket = store.get(oid)
		if None is bucket or bucket['obs'] is not observed_texts:
			bucket = {'obs': observed_texts, 'urls': {}, 'corpora': {}}
			store[oid] = bucket
		return bucket
	# @used-by :func:`agent_tools.grounding_helpers._assemble_corpus()`
	# @used-by :meth:`ActiveCorpusBuilder.build()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.audit()`
	@staticmethod
	def assemble(infos: list[dict], ext_entries: list[tuple[str, str, set[str]]]) -> tuple[list[dict], str, str, set[str]]:
		raw_parts: list[str] = []
		norm_parts: list[str] = []
		ev_nums: set[str] = set()
		for inf in infos:
			raw_parts.append(inf['raw'])
			if inf['norm']:
				norm_parts.append(inf['norm'])
			ev_nums.update(inf['nums'])
		for raw, norm, nums in ext_entries:
			if raw:
				raw_parts.append(raw)
			if norm:
				norm_parts.append(norm)
			ev_nums.update(nums)
		return (infos, '\n'.join(raw_parts), ' '.join(norm_parts), ev_nums)
	# @used-by :func:`agent_tools.grounding_helpers.build_active_corpus_cached()`
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.audit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_active_corpus_builder_and_block_line_auditor()`
	def build(self) -> tuple[list[dict], str, str, set[str], str]:
		norm_exts = self.__norm_ext_urls(self.__active_exts)
		bucket = self.__obs_bucket(self.__auditor.cache, self.__auditor.observed_texts)
		ckey = (tuple(self.__active_locals), norm_exts)
		cached = bucket['corpora'].get(ckey)
		if None is cached:
			infos = [self.__auditor.index.load_source_info(p, self.__auditor.cache) for p in self.__active_locals]
			ext_entries = [self.__load_ext_url_entry(bucket, nu, self.__norm_fn, self.__num_fn) for nu in norm_exts] if self.__auditor.observed_texts else []
			cached = self.assemble(infos, ext_entries)
			bucket['corpora'][ckey] = cached
		infos, combined_raw, combined_norm, ev_nums = cached
		label = ', '.join((self.__auditor.index.locator_for(p) for p in self.__active_primary[:2]))
		return (infos, combined_raw, combined_norm, ev_nums, label)
	# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.audit()`
	@classmethod
	def collect_local_repo_entries(cls, root: Path, active_exts: list[str], norm_fn=None, num_fn=None) -> tuple[list[tuple[str, str, set[str]]], list[str]]:
		from agent_tools.repo_link_gate import resolve_local_github_blob
		n_fn, t_fn = cls.resolve_text_helpers(norm_fn, num_fn)
		entries: list[tuple[str, str, set[str]]] = []
		labels: list[str] = []
		for url in active_exts:
			if url.lower().startswith('https://github.com/'):
				resolved = resolve_local_github_blob(root, url)
				if None is not resolved:
					label, raw = resolved
					labels.append(label)
					entries.append((raw, n_fn(raw) if raw else '', t_fn(raw) if raw else set()))
		return (entries, labels)
	# @used-by :meth:`ActiveCorpusBuilder.__init__()`
	# @used-by :meth:`ActiveCorpusBuilder.collect_local_repo_entries()`
	@staticmethod
	def resolve_text_helpers(norm_fn=None, num_fn=None):
		mod = sys.modules.get('agent_tools.source_grounding')
		eff_norm = norm_fn if None is not norm_fn else (getattr(mod, 'norm_quote_text', dfh_norm_quote_text) if None is not mod else dfh_norm_quote_text)
		eff_num = num_fn if None is not num_fn else (getattr(mod, '_source_numeric_tokens', source_numeric_tokens) if None is not mod else source_numeric_tokens)
		return (eff_norm, eff_num)