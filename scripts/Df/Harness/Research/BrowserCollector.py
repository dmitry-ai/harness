# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Research.Collector import Collector
from Df.Harness.Research.Extractor import Extractor
from Df.Harness.Research.Response import Response
from Df.Harness.lib.research import PROFILES
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_BASE_KEYS = ('url', 'final_url', 'cached', 'observation', 'status', 'kind', 'collector', 'content_type', 'observed_at', 'error', 'error_kind', 'dns_resolved')
_OPT_KEYS = ('cdp_identity', 'cdp_identity_sha256')
_CDP_KEYS = ('cdp_identity', 'cdp_identity_sha256', 'target_id', 'target_mode', 'closed_after_capture', 'endpoint')
class BrowserCollector:
	# @used-by :func:`agent_tools.research.collect_browser()`
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__run_browser_url()`
	# @used-by :meth:`Df.Harness.Research.HttpCollector.HttpCollector.__collect_single()`
	# @used-by :meth:`Df.Harness.Research.HttpCollector.HttpCollector.__run_browser_fallback()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_batch_http_and_browser_collectors_and_site_summarizer()`
	def __init__(self, root, url, *, profile: str='html', scope: str='public', session_id=None, refresh_reason=None, max_age: float=86400, cdp_port=None, timeout: float=15, context=None, config=None, http_get=None, cdp_call=None, cdp_fetcher=None, headless_shell=None) -> None:
		self.__root = root
		self.__url = url
		self.__profile = profile
		self.__scope = scope
		self.__session_id = session_id
		self.__refresh_reason = refresh_reason
		self.__max_age = max_age
		self.__cdp_port = cdp_port
		self.__timeout = timeout
		self.__context = context
		self.__config = config
		self.__http_get = http_get
		self.__cdp_call = cdp_call
		self.__cdp_fetcher = cdp_fetcher
		self.__headless_shell = headless_shell
	# @used-by :meth:`BrowserCollector.__collect_single()`
	def __build_item(self, observation: dict, cdp_meta: dict, eff_profile: str) -> dict:
		item = {k: observation.get(k) for k in (*_BASE_KEYS, *_OPT_KEYS) if None is not observation.get(k) or k in _BASE_KEYS}
		for key in _CDP_KEYS:
			if key in cdp_meta:
				item[key] = cdp_meta[key]
		if not observation.get('error'):
			try:
				item.update(Extractor.extract_observation(self.__root, observation['observation'], eff_profile))
			except (OSError, ValueError, KeyError, TypeError, LookupError) as exc:
				item['extraction_error'] = type(exc).__name__
				item['detail'] = 'DOM observation saved; inspect the source or choose another extraction profile'
		return item
	# @used-by :meth:`BrowserCollector.collect()`
	def __collect_single(self, url: str) -> dict:
		eff_profile = 'document' if 'auto' == self.__profile else self.__profile
		if eff_profile not in PROFILES:
			raise ValueError(f'Unknown extraction profile: {self.__profile}')
		has_sid = isinstance(self.__session_id, str) and bool(self.__session_id.strip())
		eff_scope = f'CDP-session:{self.__session_id.strip()}' if has_sid and 'public' == self.__scope else self.__scope
		obs_ctx = dict(self.__context or {})
		if has_sid:
			obs_ctx.setdefault('session_id', self.__session_id.strip())
		cdp_meta: dict = {}
		obs = Collector(self.__root, url, scope=eff_scope, max_age=self.__max_age, refresh_reason=self.__refresh_reason, timeout=self.__timeout, fetcher=lambda target, _h, ft: self.__read_dom(target, ft, cdp_meta), observation_kind='dom', context=obs_ctx or None, extra_meta=cdp_meta).collect()
		return self.__build_item(obs, cdp_meta, eff_profile)
	# @used-by :meth:`BrowserCollector.__collect_single()`
	def __read_dom(self, target: str, fetch_timeout: float, cdp_meta: dict) -> Response:
		if None is not self.__cdp_fetcher:
			capture = self.__cdp_fetcher(self.__root, target, cdp_port=self.__cdp_port, timeout=fetch_timeout, config=self.__config, http_get=self.__http_get, cdp_call=self.__cdp_call)
		else:
			from agent_tools.text_browser import collect_cdp_dom
			capture = collect_cdp_dom(self.__root, target, cdp_port=self.__cdp_port, session_id=self.__session_id, timeout=fetch_timeout, config=self.__config, http_get=self.__http_get, cdp_call=self.__cdp_call, headless_shell=self.__headless_shell)
		if not isinstance(capture, dict) or not isinstance(capture.get('html'), str):
			raise ValueError('CDP DOM capture did not return HTML payload')
		cdp_meta.update(capture)
		return Response(capture.get('url') or target, 0, 'text/html', capture['html'].encode('utf-8'))
	# @used-by :func:`agent_tools.research.collect_browser()`
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__run_browser_url()`
	# @used-by :meth:`Df.Harness.Research.HttpCollector.HttpCollector.__collect_single()`
	# @used-by :meth:`Df.Harness.Research.HttpCollector.HttpCollector.__run_browser_fallback()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_batch_http_and_browser_collectors_and_site_summarizer()`
	def collect(self) -> dict:
		if isinstance(self.__url, (list, tuple)) and 1 != len(self.__url):
			from Df.Harness.Research.BatchCollector import BatchCollector
			r = BatchCollector.collect_browser_batch(self.__root, self.__url, profile=self.__profile, scope=self.__scope, session_id=self.__session_id, refresh_reason=self.__refresh_reason, max_age=self.__max_age, cdp_port=self.__cdp_port, timeout=self.__timeout, context=self.__context, config=self.__config, http_get=self.__http_get, cdp_call=self.__cdp_call, cdp_fetcher=self.__cdp_fetcher)
		else:
			url = self.__url[0] if isinstance(self.__url, (list, tuple)) else self.__url
			r = self.__collect_single(url)
		return r