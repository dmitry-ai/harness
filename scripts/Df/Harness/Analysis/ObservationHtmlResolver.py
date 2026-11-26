# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
from Df.Core.lib.fs import df_stat_sig
from agent_tools.research import extractor_version
import json
import os
_OBS_HTML_CACHE: OrderedDict[tuple, dict] = OrderedDict()
_OBS_HTML_CACHE_LIMIT = 64
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ObservationHtmlResolver:
	# @used-by :meth:`Df.Harness.Analysis.ObservationContentLoader.ObservationContentLoader.load()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationProber.ObservationProber.__probe_html()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
	def __init__(self, obs_dir: Path, body: bytes | None, meta: dict, *, need_sections: bool, extract_fn=None) -> None:
		self.__obs_dir = Path(obs_dir)
		self.__body = body
		self.__meta = meta
		self.__need_sections = need_sections
		self.__extract_fn = extract_fn
	# @used-by :meth:`ObservationHtmlResolver.__load_saved()`
	def __has_full_sections(self, ext: dict) -> bool:
		secs = ext.get('sections')
		return isinstance(ext.get('anchor_content'), dict) and isinstance(secs, list) and all((isinstance(s, dict) and 'content' in s for s in secs))
	# @used-by :meth:`ObservationHtmlResolver.resolve()`
	def __load_saved(self) -> dict | None:
		r = None
		ext_path = self.__obs_dir / 'extracted-html.json'
		if ext_path.is_file():
			try:
				ext = json.loads(ext_path.read_text(encoding='utf-8'))
				valid = isinstance(ext, dict) and ext.get('body_sha256') == self.__meta.get('body_sha256') and ext.get('extractor_version') == extractor_version()
				if valid and all((k in ext for k in ('anchors', 'browser_check_required', 'text'))) and ((not self.__need_sections) or self.__has_full_sections(ext)):
					r = ext
			except (OSError, ValueError):
				r = None
		return r
	# @used-by :meth:`ObservationHtmlResolver.resolve()`
	def __put(self, key: tuple, data: dict) -> dict:
		_OBS_HTML_CACHE[key] = data
		_OBS_HTML_CACHE.move_to_end(key)
		while _OBS_HTML_CACHE_LIMIT < len(_OBS_HTML_CACHE):
			_OBS_HTML_CACHE.popitem(last=False)
		return data
	# @used-by :meth:`Df.Harness.Analysis.ObservationContentLoader.ObservationContentLoader.load()`
	# @used-by :meth:`Df.Harness.Analysis.ObservationProber.ObservationProber.__probe_html()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_remaining_edge_paths()`
	def resolve(self) -> dict:
		st_ext = df_stat_sig(self.__obs_dir / 'extracted-html.json') or (0, 0)
		st_bin = df_stat_sig(self.__obs_dir / 'response.bin') or (0, 0)
		base_key = (os.path.normcase(str(self.__obs_dir.resolve())), self.__meta.get('body_sha256'), self.__meta.get('content_type'), self.__meta.get('charset') or 'utf-8', self.__meta.get('status'), extractor_version(), st_ext, st_bin)
		hit = _OBS_HTML_CACHE.get((base_key, True)) or (None if self.__need_sections else _OBS_HTML_CACHE.get((base_key, False)))
		if None is not hit:
			r = hit
		else:
			saved = self.__load_saved()
			if None is not saved:
				r = self.__put((base_key, bool(self.__need_sections)), saved)
			else:
				from agent_tools.research import extract_bytes
				fn = extract_bytes if None is self.__extract_fn else self.__extract_fn
				raw = (self.__obs_dir / 'response.bin').read_bytes() if None is self.__body else self.__body
				parsed = fn(raw, self.__meta['content_type'], 'html', self.__meta.get('charset') or 'utf-8', status=self.__meta.get('status'))
				r = self.__put((base_key, True), parsed)
		return r