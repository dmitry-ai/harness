# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Grounding.DomainFactExtractor import DomainFactExtractor
from Df.Harness.lib.grounding import dfh_classify_provenance_tier, dfh_is_read_only_grounding, dfh_norm_quote_text
from agent_tools.claims import source_numeric_tokens
import hashlib
import json
import os
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_SOURCE_INFO_CACHE: dict[tuple[str, int, int], dict] = {}
_TIER0_INDEX_CACHE: dict[str, dict[str, dict]] = {}
_TIER0_MAX_FILE_BYTES = 512 * 1024
_TIER0_TEXT_SUFFIXES = {'.md', '.txt', '.json', '.yaml', '.yml', '.xml', '.csv', '.ini', '.conf', '.env', '.log', ''}
class Tier0Index:
	CACHE_SCHEMA_VERSION = 2
	_INDICES: dict[str, Tier0Index] = {}
	# @used-by :meth:`Tier0Index.for_root()`
	# @uses :meth:`agent_tools.path_registry.ProjectPaths.grounding_cache_json()`
	def __init__(self, root: Path) -> None:
		from agent_tools.path_registry import project_paths
		self.pp = project_paths(root, exact_root=True)
		self.root, self.root_key, self.cache_file = (self.pp.root, str(self.pp.root), self.pp.grounding_cache_json)
		self.entries: dict[str, dict] = {}
		self._disk_loaded = False
	# @used-by :meth:`Tier0Index.__add_ticket_candidates()`
	# @used-by :meth:`Tier0Index.__scan_base_dir()`
	# @used-by :meth:`Tier0Index.candidate_files()`
	@staticmethod
	def __add_if_new(p: Path, seen: set[Path], out: list[Path]) -> None:
		rp = p.resolve()
		if rp not in seen:
			seen.add(rp)
			out.append(rp)
	# @used-by :meth:`Tier0Index.candidate_files()`
	def __add_ticket_candidates(self, tickets: list[str] | tuple[str, ...], seen: set[Path], out: list[Path]) -> None:
		for tid in tickets:
			for t_cand in (self.root / tid / 'KB' / 'source.md', self.root / tid / 'source.md', self.root / 'tickets' / tid / 'KB' / 'source.md', self.root / 'tickets' / tid / 'source.md'):
				if t_cand.is_file():
					self.__add_if_new(t_cand, seen, out)
	# @used-by :meth:`Tier0Index.__read_and_index_entry()`
	# @used-by :meth:`Tier0Index.__resolve_source_info()`
	# @used-by :meth:`Tier0Index.hydrate_standalone()`
	@classmethod
	def __build_hydrated_info(cls, path: Path, rp: Path, stat_key: tuple[str, int, int] | None, raw: str, sha256: str, tuples: list[dict], root: Path | None=None) -> dict:
		_ = rp
		extra = [raw]
		if '.json' == path.suffix.lower() and raw.strip():
			try:
				cls.__json_scalar_strings(json.loads(raw), extra)
			except ValueError:
				pass
		combined_raw = '\n'.join(extra)
		is_ticket_source, msg_nums, ticket_id = DomainFactExtractor.extract_ticket_metadata(path, raw)
		r = {'path': path, 'sha256': sha256, 'raw': combined_raw, 'norm': dfh_norm_quote_text(combined_raw), 'nums': source_numeric_tokens(combined_raw), 'is_ticket_source': is_ticket_source, 'msg_nums': msg_nums, 'has_cyrillic': bool(re.search('[\\u0400-\\u04ff]{3,}', raw)), 'ticket_id': ticket_id, 'tier': dfh_classify_provenance_tier(path, root), 'fact_tuples': tuples, '_raw_source': raw}
		if None is not stat_key:
			_SOURCE_INFO_CACHE[stat_key] = r
		return r
	# @used-by :meth:`Tier0Index.ensure_entry()`
	# @used-by :meth:`Tier0Index.load_index()`
	# @used-by :meth:`Tier0Index.load_source_info()`
	def __ensure_disk_loaded(self) -> None:
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
	# @used-by :meth:`Tier0Index.ensure_entry()`
	def __entry_from_disk(self, rp: Path, rel: str, mtime_ns: int, size: int) -> tuple[str, dict | None, bool]:
		stat_key = (str(rp), mtime_ns, size)
		hydrated = _SOURCE_INFO_CACHE.get(stat_key)
		if isinstance(hydrated, dict) and hydrated.get('sha256') and (None is not hydrated.get('_raw_source')):
			dom = DomainFactExtractor.extract_domain_entities(hydrated['_raw_source'], include_substring_metrics=True)
			entry = {'mtime_ns': mtime_ns, 'size': size, 'sha256': hydrated['sha256'], 'tickets': dom['tickets'], 'plans_norm': dom['plans_norm'], 'metrics': dom['metrics'], 'fact_tuples': hydrated['fact_tuples']}
			self.entries[rel] = entry
			r: tuple[str, dict | None, bool] = (rel, entry, True)
		else:
			r = self.__read_and_index_entry(rp, rel, stat_key, mtime_ns, size)
		return r
	# @used-by :meth:`Tier0Index.__build_hydrated_info()`
	@classmethod
	def __json_scalar_strings(cls, obj, out: list[str]) -> None:
		if None is not obj and (not isinstance(obj, (dict, list, float))):
			out.append(str(obj))
		elif isinstance(obj, float):
			out.extend((f'{obj:.2f}', str(obj)))
		elif isinstance(obj, list):
			for item in obj:
				cls.__json_scalar_strings(item, out)
		elif isinstance(obj, dict):
			for k, v in obj.items():
				out.append(str(k))
				cls.__json_scalar_strings(v, out)
	# @used-by :meth:`Tier0Index.discover_entities()`
	@staticmethod
	def __match_entry_entities(rp: Path, entry: dict, tickets: list[str], plans: list[str], metrics: list[str]) -> list[str]:
		ft, fp, fm, rp_posix = (set(entry.get('tickets') or ()), set(entry.get('plans_norm') or ()), set(entry.get('metrics') or ()), rp.as_posix())
		return [*(f'ticket:{tid}' for tid in tickets if tid in rp_posix or tid in ft), *(f'plan:{pl}' for pl in plans if ' '.join(pl.split()).upper() in fp), *(f'metric:{mt}' for mt in metrics if mt in fm)]
	# @used-by :meth:`Tier0Index.load_index()`
	def __persist_if_dirty(self, dirty: bool) -> None:
		if (not dfh_is_read_only_grounding()) and (dirty or (self.entries and (not self.cache_file.is_file()))) and (self.cache_file.parent.is_dir() or self.pp.agent_dir.is_dir()):
			try:
				self.cache_file.parent.mkdir(parents=True, exist_ok=True)
				self.cache_file.write_text(json.dumps({'version': self.CACHE_SCHEMA_VERSION, 'files': self.entries}, ensure_ascii=False) + '\n', encoding='utf-8')
			except OSError:
				pass
	# @used-by :meth:`Tier0Index.__entry_from_disk()`
	def __read_and_index_entry(self, rp: Path, rel: str, stat_key: tuple[str, int, int], mtime_ns: int, size: int) -> tuple[str, dict | None, bool]:
		try:
			raw_bytes = rp.read_bytes()
			raw = raw_bytes.decode('utf-8', errors='replace')
		except OSError:
			r: tuple[str, dict | None, bool] = (rel, None, False)
		else:
			sha256, dom, tuples = (hashlib.sha256(raw_bytes).hexdigest(), DomainFactExtractor.extract_domain_entities(raw, include_substring_metrics=True), DomainFactExtractor(rp, raw, root=self.root).extract())
			entry = {'mtime_ns': mtime_ns, 'size': size, 'sha256': sha256, 'tickets': dom['tickets'], 'plans_norm': dom['plans_norm'], 'metrics': dom['metrics'], 'fact_tuples': tuples}
			self.entries[rel] = entry
			self.__build_hydrated_info(rp, rp, stat_key, raw, sha256, tuples, root=self.root)
			r = (rel, entry, True)
		return r
	# @used-by :meth:`Tier0Index.__resolve_source_info()`
	# @used-by :meth:`Tier0Index.__stat_and_read()`
	@staticmethod
	def __read_raw_for_stat(rp: Path, stat_key: tuple[str, int, int] | None) -> tuple[bytes, str]:
		try:
			raw_bytes = rp.read_bytes() if None is not stat_key else b''
			raw = raw_bytes.decode('utf-8', errors='replace') if None is not stat_key else ''
		except OSError:
			raw_bytes, raw = (b'', '')
		return (raw_bytes, raw)
	# @used-by :meth:`Tier0Index.load_source_info()`
	def __resolve_source_info(self, path: Path, rp: Path, stat_key: tuple[str, int, int] | None) -> dict:
		rel = self.locator_for(rp) if None is not stat_key else ''
		cached_entry = self.entries.get(rel) if rel else None
		raw_bytes, raw = self.__read_raw_for_stat(rp, stat_key)
		if isinstance(cached_entry, dict) and None is not stat_key and cached_entry.get('mtime_ns') == stat_key[1] and (cached_entry.get('size') == stat_key[2]) and isinstance(cached_entry.get('sha256'), str):
			sha256, tuples = (cached_entry['sha256'], cached_entry.get('fact_tuples') or [])
		else:
			sha256, tuples = (hashlib.sha256(raw_bytes).hexdigest() if raw_bytes or None is not stat_key else '', DomainFactExtractor(rp, raw, root=self.root).extract())
			if None is not stat_key and 'tier_0' == dfh_classify_provenance_tier(rp, self.root) and (not rel.startswith('/')) and (':' not in rel):
				dom = DomainFactExtractor.extract_domain_entities(raw, include_substring_metrics=True)
				self.entries[rel] = {'mtime_ns': stat_key[1], 'size': stat_key[2], 'sha256': sha256, 'tickets': dom['tickets'], 'plans_norm': dom['plans_norm'], 'metrics': dom['metrics'], 'fact_tuples': tuples}
		return self.__build_hydrated_info(path, rp, stat_key, raw, sha256, tuples, root=self.root)
	# @used-by :meth:`Tier0Index.candidate_files()`
	def __scan_base_dir(self, base: Path, seen: set[Path], out: list[Path]) -> None:
		for dirpath, dirs, filenames in os.walk(base):
			dirs[:] = sorted((d for d in dirs if d.lower() not in ('http', 'reviews', 'github')))
			dpath = Path(dirpath)
			for fname in sorted(filenames):
				p = dpath / fname
				if p.suffix.lower() in _TIER0_TEXT_SUFFIXES and (not fname.lower().startswith('extracted-')) and ('observation.json' != fname.lower()):
					try:
						ok_size = _TIER0_MAX_FILE_BYTES >= p.stat().st_size
					except OSError:
						ok_size = False
					if ok_size and 'tier_0' == dfh_classify_provenance_tier(p, self.root):
						self.__add_if_new(p, seen, out)
	# @used-by :meth:`Tier0Index.hydrate_standalone()`
	@classmethod
	def __stat_and_read(cls, path: Path) -> tuple[Path, tuple[str, int, int] | None, bytes, str]:
		stat_key = None
		try:
			rp = path.resolve()
			st = rp.stat()
			stat_key = (str(rp), st.st_mtime_ns, st.st_size)
		except OSError:
			rp = path
		return (rp, stat_key, *cls.__read_raw_for_stat(rp, stat_key))
	# @used-by :func:`agent_tools.source_grounding._tier0_candidate_files()`
	# @used-by :meth:`Tier0Index.load_index()`
	def candidate_files(self, tickets: list[str] | tuple[str, ...]=()) -> list[Path]:
		r: list[Path] = []
		seen: set[Path] = set()
		art_in = self.pp.path('artifacts_in_dir')
		for base in (self.pp.evidence_dir, self.pp.source_dir, self.pp.manual_kb_dir, *([art_in] if None is not art_in else []), self.root / 'tickets', *self.pp.source_dirs):
			if base.is_dir():
				self.__scan_base_dir(base, seen, r)
		for p in sorted(self.root.glob('*/KB/source.md')):
			if p.is_file():
				self.__add_if_new(p, seen, r)
		self.__add_ticket_candidates(tickets, seen, r)
		return r
	# @used-by :func:`agent_tools.source_grounding.discover_entity_tier0_sources()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_response_auditor_ingestor_and_tier0_index()`
	# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_tier0_source_index_schema_upgrade_and_single_read()`
	def discover_entities(self, text: str) -> list[dict]:
		r: list[dict] = []
		if text and isinstance(text, str):
			dom = DomainFactExtractor.extract_domain_entities(text)
			tickets, plans, metrics = (dom['tickets'], dom['plans'], dom['metrics'])
			if tickets or plans or metrics:
				candidates, mem_idx = self.load_index(tickets)
				for rp in candidates:
					rel = self.locator_for(rp)
					entry = mem_idx.get(rel)
					if isinstance(entry, dict):
						matched = self.__match_entry_entities(rp, entry, tickets, plans, metrics)
						if matched:
							r.append({'path': rel, 'sha256': entry['sha256'], 'tier': 'tier_0', 'matched_entities': matched})
		return r
	# @used-by :func:`agent_tools.source_grounding._get_tier0_file_entry()`
	# @used-by :meth:`Tier0Index.load_index()`
	def ensure_entry(self, rp: Path) -> tuple[str, dict | None, bool]:
		self.__ensure_disk_loaded()
		r: tuple[str, dict | None, bool] = ('', None, False)
		try:
			st = rp.stat()
			mtime_ns, size = (st.st_mtime_ns, st.st_size)
		except OSError:
			mtime_ns, size = (-1, -1)
		if 0 <= mtime_ns:
			rel = self.locator_for(rp)
			cached = self.entries.get(rel)
			r = (rel, cached, False) if isinstance(cached, dict) and cached.get('mtime_ns') == mtime_ns and (cached.get('size') == size) and isinstance(cached.get('sha256'), str) else self.__entry_from_disk(rp, rel, mtime_ns, size)
		return r
	# @used-by :func:`agent_tools.source_grounding._get_tier0_file_entry()`
	# @used-by :func:`agent_tools.source_grounding._load_local_source_info()`
	# @used-by :func:`agent_tools.source_grounding._load_tier0_index()`
	# @used-by :func:`agent_tools.source_grounding._tier0_candidate_files()`
	# @used-by :func:`agent_tools.source_grounding.discover_entity_tier0_sources()`
	# @used-by :func:`agent_tools.source_grounding.sync_fact_ledger()`
	# @used-by :meth:`Df.Harness.Grounding.LocalSourceAuditor.LocalSourceAuditor.__init__()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_response_auditor_ingestor_and_tier0_index()`
	# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_tier0_source_index_schema_upgrade_and_single_read()`
	@classmethod
	def for_root(cls, root: Path) -> Tier0Index:
		resolved = Path(root).resolve()
		rkey = str(resolved)
		r = cls._INDICES.get(rkey)
		if None is r:
			r = cls(resolved)
			cls._INDICES[rkey] = r
		return r
	# @used-by :func:`agent_tools.source_grounding._load_local_source_info()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_response_auditor_ingestor_and_tier0_index()`
	# @used-by :meth:`test_evidence_unification.EvidenceUnificationTests.test_standalone_source_hydration_uses_tier0_index()`
	@classmethod
	def hydrate_standalone(cls, path: Path, cache: dict | None=None) -> dict:
		key = str(path)
		if None is not cache and key in cache:
			r = cache[key]
		else:
			rp, stat_key, raw_bytes, raw = cls.__stat_and_read(path)
			r = _SOURCE_INFO_CACHE[stat_key] if None is not stat_key and stat_key in _SOURCE_INFO_CACHE else cls.__build_hydrated_info(path, rp, stat_key, raw, hashlib.sha256(raw_bytes).hexdigest() if None is not stat_key else '', DomainFactExtractor(path, raw).extract())
			if None is not cache:
				cache[key] = r
		return r
	# @used-by :func:`agent_tools.source_grounding._infer_source_root()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_response_auditor_ingestor_and_tier0_index()`
	@classmethod
	def infer_source_root(cls, path: Path) -> Path | None:
		r: Path | None = None
		try:
			rp = path.resolve()
		except OSError:
			rp = None
		if None is not rp:
			for inst in cls._INDICES.values():
				try:
					rp.relative_to(inst.root)
					if None is r or len(str(inst.root)) > len(str(r)):
						r = inst.root
				except ValueError:
					pass
		return r
	# @used-by :func:`agent_tools.source_grounding._load_tier0_index()`
	# @used-by :meth:`Tier0Index.discover_entities()`
	# @used-by :meth:`Tier0Index.sync_ledger()`
	def load_index(self, tickets: list[str] | tuple[str, ...]=()) -> tuple[list[Path], dict[str, dict]]:
		self.__ensure_disk_loaded()
		candidates = self.candidate_files(tickets)
		dirty = False
		for rp in candidates:
			if self.ensure_entry(rp)[2]:
				dirty = True
		self.__persist_if_dirty(dirty)
		return (candidates, self.entries)
	# @used-by :func:`agent_tools.source_grounding._load_local_source_info()`
	# @used-by :meth:`Df.Harness.Grounding.ActiveCorpusBuilder.ActiveCorpusBuilder.build()`
	# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_tier0_source_index_schema_upgrade_and_single_read()`
	def load_source_info(self, path: Path, cache: dict | None=None) -> dict:
		key = str(path)
		if None is not cache and key in cache:
			r = cache[key]
		else:
			self.__ensure_disk_loaded()
			stat_key = None
			try:
				rp = path.resolve()
				st = rp.stat()
				stat_key = (str(rp), st.st_mtime_ns, st.st_size)
			except OSError:
				rp = path
			r = _SOURCE_INFO_CACHE[stat_key] if None is not stat_key and stat_key in _SOURCE_INFO_CACHE else self.__resolve_source_info(path, rp, stat_key)
			if None is not cache:
				cache[key] = r
		return r
	# @used-by :meth:`Df.Harness.Grounding.ActiveCorpusBuilder.ActiveCorpusBuilder.build()`
	# @used-by :meth:`Tier0Index.__resolve_source_info()`
	# @used-by :meth:`Tier0Index.discover_entities()`
	# @used-by :meth:`Tier0Index.ensure_entry()`
	# @used-by :meth:`Tier0Index.sync_ledger()`
	def locator_for(self, path: Path) -> str:
		try:
			r = path.resolve().relative_to(self.root).as_posix()
		except ValueError:
			r = path.as_posix()
		return r
	# @used-by :func:`agent_tools.source_grounding._get_tier0_file_entry()`
	def seed_entries(self, mem_idx: dict[str, dict]) -> None:
		self.entries = mem_idx
		_TIER0_INDEX_CACHE[self.root_key] = mem_idx
		self._disk_loaded = True
	# @used-by :func:`agent_tools.source_grounding.sync_fact_ledger()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_response_auditor_ingestor_and_tier0_index()`
	# @used-by :meth:`test_source_grounding.SourceGroundingRefactorTests.test_tier0_source_index_schema_upgrade_and_single_read()`
	def sync_ledger(self) -> dict:
		candidates, mem_idx = self.load_index()
		tuples = [t for rp in candidates if isinstance(mem_idx.get(self.locator_for(rp)), dict) and isinstance(mem_idx[self.locator_for(rp)].get('fact_tuples'), list) for t in mem_idx[self.locator_for(rp)]['fact_tuples']]
		r = {'version': 1, 'tuple_count': len(tuples), 'tuples': tuples}
		facts_file = self.pp.facts_json
		if tuples or facts_file.parent.is_dir() or self.pp.agent_dir.is_dir():
			facts_file.parent.mkdir(parents=True, exist_ok=True)
			facts_file.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
		return r