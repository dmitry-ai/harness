# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.research import load_observation
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ObservationResolver:
	# @used-by :func:`agent_tools.evidence_loader.resolve_http_observation()`
	# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.load()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def __init__(self, root, base_url: str, observation: str | None=None) -> None:
		self.__root = root
		self.__base_url = base_url
		self.__observation = observation
	# @used-by :meth:`ObservationResolver.resolve()`
	def __lookup_index(self) -> str | None:
		from agent_tools.path_registry import project_paths
		index = project_paths(self.__root, exact_root=True).http_index_json
		candidates = json.loads(index.read_text(encoding='utf-8')).values() if index.exists() else []
		r = None
		for candidate in candidates:
			meta = load_observation(self.__root, candidate['observation'])
			if self.__base_url in (meta['url'], meta['final_url']):
				r = candidate['observation']
				break
		return r
	# @used-by :func:`agent_tools.evidence_loader.resolve_http_observation()`
	# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.load()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def resolve(self) -> tuple[str, dict]:
		obs = self.__observation or self.__lookup_index()
		if not obs:
			raise FileNotFoundError('No saved HTTP/DOM observation; use saved primary evidence or collect the required source once')
		meta = load_observation(self.__root, obs)
		if self.__base_url not in (meta['url'], meta['final_url']):
			raise ValueError('Observation belongs to a different URL')
		if meta.get('error') or ('dom' != meta.get('kind') and not 200 <= (meta.get('status') or 0) < 300):
			raise ValueError('Saved HTTP result is unavailable; use a different verification method')
		return (obs, meta)