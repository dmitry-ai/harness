# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Research.BrowserCollector import BrowserCollector
from Df.Harness.Research.Collector import Collector
from Df.Harness.Research.Extractor import Extractor
from Df.Harness.lib.research import BROWSER_MODES, PROFILES
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_HTTP_KEYS = ('url', 'final_url', 'cached', 'observation', 'status', 'kind', 'collector', 'content_type', 'observed_at', 'error', 'error_kind', 'dns_resolved')
_STATIC_PREFIXES = ('application/json', 'application/xml', 'text/xml', 'application/pdf', 'application/zip', 'application/vnd.openxmlformats')
class HttpCollector:
	# @used-by :func:`agent_tools.research.collect_http()`
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__run_plan_entry()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_batch_http_and_browser_collectors_and_site_summarizer()`
	def __init__(self, root, url, *, profile: str='html', scope: str='public', session_id=None, refresh_reason=None, max_age: float=86400, headers=None, context=None, fetcher=None, browser: str='auto', cdp_port=None, cdp_fetcher=None, http_get=None, cdp_call=None, headless_shell=None) -> None:
		self.__root = root
		self.__url = url
		self.__profile = profile
		self.__scope = scope
		self.__session_id = session_id
		self.__refresh_reason = refresh_reason
		self.__max_age = max_age
		self.__headers = headers
		self.__context = context
		self.__fetcher = fetcher
		self.__browser = browser
		self.__cdp_port = cdp_port
		self.__cdp_fetcher = cdp_fetcher
		self.__http_get = http_get
		self.__cdp_call = cdp_call
		self.__headless_shell = headless_shell
	# @used-by :meth:`HttpCollector.__collect_single()`
	def __collect_http_and_fallback(self, url: str, eff_profile: str) -> dict:
		obs = Collector(self.__root, url, headers=self.__headers, scope=self.__scope, max_age=self.__max_age, refresh_reason=self.__refresh_reason, fetcher=self.__fetcher, context=self.__context).collect()
		r = {k: obs.get(k) for k in _HTTP_KEYS}
		ct_low = (obs.get('content_type') or '').lower()
		self.__try_extract(r, obs, ct_low, eff_profile)
		if self.__should_fallback(obs, r, ct_low):
			r = self.__run_browser_fallback(url, r)
		return r
	# @used-by :meth:`HttpCollector.collect()`
	def __collect_single(self, url: str) -> dict:
		if self.__browser not in BROWSER_MODES:
			raise ValueError(f'Unknown browser mode: {self.__browser}; choose {BROWSER_MODES}')
		eff_profile = 'document' if 'auto' == self.__profile else self.__profile
		if eff_profile not in PROFILES:
			raise ValueError(f'Unknown extraction profile: {self.__profile}')
		if 'always' == self.__browser:
			r = BrowserCollector(self.__root, url, profile=self.__profile, scope=self.__scope, session_id=self.__session_id, refresh_reason=self.__refresh_reason, max_age=self.__max_age, cdp_port=self.__cdp_port, context=self.__context, cdp_fetcher=self.__cdp_fetcher, http_get=self.__http_get, cdp_call=self.__cdp_call, headless_shell=self.__headless_shell).collect()
		else:
			r = self.__collect_http_and_fallback(url, eff_profile)
		return r
	# @used-by :meth:`HttpCollector.__collect_http_and_fallback()`
	def __run_browser_fallback(self, url: str, r: dict) -> dict:
		try:
			dom_item = BrowserCollector(self.__root, url, profile=self.__profile, scope=self.__scope, session_id=self.__session_id, refresh_reason=self.__refresh_reason or 'browser fallback after HTTP challenge or empty body', max_age=self.__max_age, cdp_port=self.__cdp_port, context=self.__context, cdp_fetcher=self.__cdp_fetcher, http_get=self.__http_get, cdp_call=self.__cdp_call, headless_shell=self.__headless_shell).collect()
		except PermissionError as exc:
			dom_item = {'error': 'PermissionError', 'detail': str(exc)}
		if dom_item.get('error') or dom_item.get('extraction_error'):
			r['browser_fallback_attempted'] = True
			r['browser_fallback_error'] = dom_item.get('error') or dom_item.get('extraction_error')
			out = r
		else:
			dom_item['http_observation'] = r.get('observation')
			dom_item['http_status'] = r.get('status')
			dom_item['browser_fallback'] = True
			dom_item['browser_fallback_from_http'] = True
			out = dom_item
		return out
	# @used-by :meth:`HttpCollector.__collect_http_and_fallback()`
	def __should_fallback(self, obs: dict, r: dict, ct_low: str) -> bool:
		status = obs.get('status') or 0
		is_static = 200 <= status < 300 and any((ct_low.startswith(p) for p in _STATIC_PREFIXES))
		needs_browser = (not is_static) and (obs.get('status') in (401, 403, 429) or bool(r.get('browser_check_required')))
		can_fallback = None is self.__fetcher or any((None is not x for x in (self.__cdp_fetcher, self.__http_get, self.__cdp_call)))
		return 'auto' == self.__browser and needs_browser and can_fallback
	# @used-by :meth:`HttpCollector.__collect_http_and_fallback()`
	def __try_extract(self, r: dict, obs: dict, ct_low: str, eff_profile: str) -> None:
		if not obs.get('error') and 200 <= (obs.get('status') or 0) < 300:
			chosen = 'document' if self.__profile in ('html', 'auto') and 'application/json' == ct_low else eff_profile
			try:
				r.update(Extractor.extract_observation(self.__root, obs['observation'], chosen))
			except (OSError, ValueError, KeyError, TypeError, LookupError) as exc:
				r['extraction_error'] = type(exc).__name__
				r['detail'] = 'Response saved; inspect the source or choose another extraction profile, without fetching it again'
	# @used-by :func:`agent_tools.research.collect_http()`
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__run_plan_entry()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_batch_http_and_browser_collectors_and_site_summarizer()`
	def collect(self) -> dict:
		if isinstance(self.__url, (list, tuple)) and 1 != len(self.__url):
			from Df.Harness.Research.BatchCollector import BatchCollector
			r = BatchCollector.collect_http_batch(self.__root, self.__url, profile=self.__profile, scope=self.__scope, session_id=self.__session_id, refresh_reason=self.__refresh_reason, max_age=self.__max_age, headers=self.__headers, context=self.__context, fetcher=self.__fetcher, browser=self.__browser, cdp_port=self.__cdp_port, cdp_fetcher=self.__cdp_fetcher, http_get=self.__http_get, cdp_call=self.__cdp_call)
		else:
			url = self.__url[0] if isinstance(self.__url, (list, tuple)) else self.__url
			r = self.__collect_single(url)
		return r