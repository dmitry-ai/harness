# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
_DICT_SECTIONS = ('notes', 'sources')
_LIST_SECTIONS = ('facts', 'identity', 'concerns', 'misconceptions', 'causes', 'methods')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class CandidateMerger:
	# @used-by :func:`agent_tools.analysis_merge.merge_analysis_candidate()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.save()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def __init__(self, base: dict, patch: dict) -> None:
		self.__base = base
		self.__patch = patch
	# @used-by :meth:`CandidateMerger.__index_existing()`
	# @used-by :meth:`CandidateMerger.__merge_claim_list()`
	def __claim_id(self, item) -> str | None:
		cid = item.get('id') if isinstance(item, dict) else None
		return cid if isinstance(cid, str) and cid else None
	# @used-by :meth:`CandidateMerger.__merge_claim_list()`
	def __index_existing(self, existing, remove_ids: set[str]) -> tuple[list, dict[str, int]]:
		out: list = []
		idx_by_id: dict[str, int] = {}
		for item in existing if isinstance(existing, list) else ():
			cid = self.__claim_id(item)
			if None is not cid and cid in remove_ids:
				continue
			if None is not cid:
				idx_by_id[cid] = len(out)
			out.append(item)
		return (out, idx_by_id)
	# @used-by :meth:`CandidateMerger.merge()`
	def __merge_claim_list(self, existing, incoming, remove_ids: set[str]) -> list:
		out, idx_by_id = self.__index_existing(existing, remove_ids)
		for item in incoming if isinstance(incoming, list) else ():
			cid = self.__claim_id(item)
			if None is not cid and cid in idx_by_id:
				out[idx_by_id[cid]] = item
			else:
				if None is not cid:
					idx_by_id[cid] = len(out)
				out.append(item)
		return out
	# @used-by :meth:`CandidateMerger.merge()`
	def __merge_extra(self, merged: dict) -> None:
		for sec in _DICT_SECTIONS:
			if sec in self.__patch and isinstance(self.__patch[sec], dict):
				prev = self.__base.get(sec) if isinstance(self.__base.get(sec), dict) else {}
				merged[sec] = {**prev, **self.__patch[sec]}
		skip = set(_LIST_SECTIONS) | set(_DICT_SECTIONS) | {'remove_claim_ids'}
		for key, val in self.__patch.items():
			if key not in skip:
				merged[key] = val
	# @used-by :func:`agent_tools.analysis_merge.merge_analysis_candidate()`
	# @used-by :meth:`Df.Harness.Analysis.Merger.Merger.save()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_analysis_merger_and_lifecycle_classes()`
	def merge(self) -> dict:
		if not isinstance(self.__patch, dict):
			raise ValueError('Analysis merge candidate must be a JSON object')
		remove_ids = {x for x in (self.__patch.get('remove_claim_ids') or ()) if isinstance(x, str)}
		merged = dict(self.__base)
		for sec in _LIST_SECTIONS:
			merged[sec] = self.__merge_claim_list(self.__base.get(sec), self.__patch.get(sec) if sec in self.__patch else (), remove_ids)
		self.__merge_extra(merged)
		merged.setdefault('schema_version', 3)
		return merged