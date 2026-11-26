# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from urllib.parse import unquote, urldefrag
from Df.Harness.Analysis.LocalSourceResolver import LocalSourceResolver
from Df.Harness.Analysis.ObservationHtmlResolver import ObservationHtmlResolver
_HTML_CTYPES = ('text/html', 'application/xhtml+xml')
_MD_CTYPES = ('text/markdown', 'text/x-markdown')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ObservationProber:
	# @used-by :func:`agent_tools.evidence_loader.probe_observation_status()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def __init__(self, root, meta: dict, base_url: str, fragment: str='', *, extract_fn=None) -> None:
		self.__root = root
		self.__meta = meta
		self.__base_url = base_url
		self.__fragment = fragment
		self.__extract_fn = extract_fn
	# @used-by :meth:`ObservationProber.probe()`
	def __probe_html(self) -> str:
		obs_dir = LocalSourceResolver(self.__root, self.__meta['observation']).resolve().parent
		data = ObservationHtmlResolver(obs_dir, None, self.__meta, need_sections=False, extract_fn=self.__extract_fn).resolve()
		frag = unquote(self.__fragment)
		if data.get('browser_check_required'):
			r = 'browser-check-required'
		elif self.__fragment and (frag not in data['anchors'] or frag in data.get('ambiguous_anchors', [])):
			r = 'anchor-unverified'
		else:
			r = 'http-ok'
		return r
	# @used-by :func:`agent_tools.evidence_loader.probe_observation_status()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def probe(self) -> str:
		ct_low = (self.__meta.get('content_type') or '').split(';', 1)[0].strip().lower()
		valid = (not self.__meta.get('error')) and ('dom' == self.__meta.get('kind') or 200 <= (self.__meta.get('status') or 0) < 300)
		if not valid:
			r = 'unavailable'
		elif urldefrag(self.__meta['final_url'])[0] != self.__base_url:
			r = 'redirect-unverified'
		elif ct_low not in _HTML_CTYPES + _MD_CTYPES:
			r = 'anchor-unverified' if self.__fragment else 'http-ok'
		else:
			r = self.__probe_html()
		return r