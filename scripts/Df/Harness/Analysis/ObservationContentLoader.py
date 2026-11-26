# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from urllib.parse import unquote
from Df.Harness.Analysis.JsonPointer import JsonPointer
from Df.Harness.Analysis.LocalSourceResolver import LocalSourceResolver
from Df.Harness.Analysis.ObservationHtmlResolver import ObservationHtmlResolver
import json
_HTML_CTYPES = ('text/html', 'application/xhtml+xml')
_MD_CTYPES = ('text/markdown', 'text/x-markdown')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ObservationContentLoader:
	# @used-by :func:`agent_tools.evidence_loader.load_observation_content()`
	# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.load()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def __init__(self, root, observation_ref: str, meta: dict, *, fragment: str='', need_sections: bool=True, extract_fn=None) -> None:
		self.__root = root
		self.__observation_ref = observation_ref
		self.__meta = meta
		self.__fragment = fragment
		self.__need_sections = need_sections
		self.__extract_fn = extract_fn
	# @used-by :func:`agent_tools.evidence_loader.load_observation_content()`
	# @used-by :meth:`Df.Harness.Analysis.SavedSourceLoader.SavedSourceLoader.load()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def load(self) -> dict:
		obs_dir = LocalSourceResolver(self.__root, self.__observation_ref).resolve().parent
		body = (obs_dir / 'response.bin').read_bytes()
		charset = self.__meta.get('charset') or 'utf-8'
		ct_low = (self.__meta.get('content_type') or '').split(';', 1)[0].strip().lower()
		raw_str, frag = (body.decode(charset, errors='replace'), unquote(self.__fragment))
		if ct_low in _HTML_CTYPES + _MD_CTYPES:
			data = ObservationHtmlResolver(obs_dir, body, self.__meta, need_sections=bool(self.__need_sections or frag), extract_fn=self.__extract_fn).resolve()
			r: dict = {'kind': 'html', 'data': data, 'raw': raw_str, 'fragment': frag, 'meta': self.__meta, 'challenge_checked': True}
			if ct_low in _MD_CTYPES:
				r['is_markdown'] = True
		elif 'application/json' == ct_low or ct_low.endswith('+json'):
			value = JsonPointer(json.loads(raw_str), self.__fragment).resolve()
			r = {'kind': 'json', 'text': value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2), 'fragment': frag, 'meta': self.__meta}
		elif self.__fragment:
			raise ValueError('This source format does not support a verified fragment locator')
		else:
			r = {'kind': 'text', 'text': raw_str, 'fragment': frag, 'meta': self.__meta}
		return r