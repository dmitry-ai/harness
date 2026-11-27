# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Research.BrowserCollector import BrowserCollector
from Df.Harness.Research.HttpCollector import HttpCollector
from Df.Harness.Research.SiteSummarizer import SiteSummarizer
from Df.Harness.lib.research import BROWSER_MODES, PROFILES
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class BatchCollector:
	# @used-by :func:`agent_tools.research.collect_plan()`
	# @used-by :meth:`BatchCollector.collect_http_batch()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_batch_http_and_browser_collectors_and_site_summarizer()`
	def __init__(self, root, plan: dict, *, fetcher=None, browser: str='auto', cdp_port=None, session_id=None, cdp_fetcher=None, http_get=None, cdp_call=None) -> None:
		self.__root = root
		self.__plan = plan
		self.__fetcher = fetcher
		self.__browser = browser
		self.__cdp_port = cdp_port
		self.__session_id = session_id
		self.__cdp_fetcher = cdp_fetcher
		self.__http_get = http_get
		self.__cdp_call = cdp_call
	# @used-by :meth:`BatchCollector.collect_browser_batch()`
	# @used-by :meth:`BatchCollector.run()`
	@staticmethod
	def __build_batch_result(root, results: list[dict], *, include_detail: bool) -> dict:
		out = {
			'results': results,
			'site_summary': SiteSummarizer(root, results).summarize(),
			'complete': all((not x.get('error') and ('dom' == x.get('kind') or 0 < (x.get('status') or 0)) for x in results)),
			'content_available_for_all': all((not x.get('error') and (not x.get('extraction_error')) and ('dom' == x.get('kind') or 200 <= (x.get('status') or 0) < 300) and (not x.get('browser_check_required')) for x in results)),
		}
		if include_detail:
			out['detail'] = 'A saved HTTP 403/404 is a completed observation, not a reason to repeat the same request blindly'
		return out
	# @used-by :meth:`BatchCollector.__run_plan_entry()`
	@staticmethod
	def __lazy_headless_fetch(shared_shell: dict, proj_root, target: str, *, cdp_port=None, timeout: float=15, config=None, http_get=None, cdp_call=None) -> dict:
		from Df.Harness.Text.Browser.CdpDomCollector import CdpDomCollector
		from Df.Harness.Text.Browser.HeadlessShell import HeadlessShell
		from Df.Harness.lib.browser import dfh_browser_seam
		if None is shared_shell['instance']:
			shared_shell['instance'] = HeadlessShell(config).__enter__()
		fn = dfh_browser_seam('collect_cdp_dom', lambda r, t, **kw: CdpDomCollector(r, t, **kw).collect())
		return fn(proj_root, target, cdp_port=cdp_port, timeout=timeout, config=config, headless_shell=shared_shell['instance'])
	# @used-by :meth:`BatchCollector.collect_browser_batch()`
	@staticmethod
	def __run_browser_url(root, url: str, opts: dict, shared_shell: dict, use_lazy: bool) -> dict:
		try:
			if use_lazy and None is shared_shell['instance']:
				from Df.Harness.Text.Browser.HeadlessShell import HeadlessShell
				shared_shell['instance'] = HeadlessShell(opts['config']).__enter__()
			r = BrowserCollector(root, url, headless_shell=shared_shell['instance'], **opts).collect()
		except (OSError, ValueError, KeyError, TypeError) as exc:
			r = {'url': url, 'error': type(exc).__name__, 'detail': str(exc)}
		return r
	# @used-by :meth:`BatchCollector.run()`
	def __run_plan_entry(self, entry, idx: int, shared_shell: dict, use_lazy: bool) -> dict:
		try:
			if not isinstance(entry, dict):
				raise ValueError('Each request must be an object')
			profile = entry.get('profile', 'html')
			if profile not in PROFILES and 'auto' != profile:
				raise ValueError('Unknown extraction profile')
			entry_sid = entry.get('session_id', self.__session_id)
			eff_cdp = (lambda pr, t, **kw: self.__lazy_headless_fetch(shared_shell, pr, t, **kw)) if use_lazy and (not entry_sid) else self.__cdp_fetcher
			r = HttpCollector(self.__root, entry['url'], profile=profile, scope=entry.get('scope', 'public'), session_id=entry_sid, refresh_reason=entry.get('refresh_reason'), max_age=entry.get('max_age', 86400), headers=entry.get('headers'), context=entry.get('context'), fetcher=self.__fetcher, browser=entry.get('browser', self.__browser), cdp_port=self.__cdp_port, cdp_fetcher=eff_cdp, http_get=self.__http_get, cdp_call=self.__cdp_call).collect()
		except (OSError, ValueError, KeyError, TypeError) as exc:
			r = {'error': type(exc).__name__, 'detail': 'Invalid or unavailable input; check this plan entry', 'request_index': idx}
		return r
	# @used-by :func:`agent_tools.research.collect_browser_batch()`
	# @used-by :meth:`Df.Harness.Research.BrowserCollector.BrowserCollector.collect()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_batch_http_and_browser_collectors_and_site_summarizer()`
	@classmethod
	def collect_browser_batch(cls, root, urls, *, profile: str='html', scope: str='public', session_id=None, refresh_reason=None, max_age: float=86400, cdp_port=None, timeout: float=15, context=None, config=None, http_get=None, cdp_call=None, cdp_fetcher=None) -> dict:
		cleaned = [str(u).strip() for u in (urls or ()) if str(u).strip()]
		if not cleaned:
			raise ValueError('Provide at least one HTTP(S) URL')
		opts = {'profile': profile, 'scope': scope, 'session_id': session_id, 'refresh_reason': refresh_reason, 'max_age': max_age, 'cdp_port': cdp_port, 'timeout': timeout, 'context': context, 'config': config, 'http_get': http_get, 'cdp_call': cdp_call, 'cdp_fetcher': cdp_fetcher}
		shared_shell: dict = {'instance': None}
		use_lazy = None is cdp_fetcher and None is http_get and None is cdp_call and None is cdp_port and (not session_id)
		results: list[dict] = []
		try:
			for u in cleaned:
				results.append(cls.__run_browser_url(root, u, opts, shared_shell, use_lazy))
		finally:
			if None is not shared_shell['instance']:
				shared_shell['instance'].close()
		return cls.__build_batch_result(root, results, include_detail=False)
	# @used-by :func:`agent_tools.research.collect_http_batch()`
	# @used-by :meth:`Df.Harness.Research.HttpCollector.HttpCollector.collect()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_batch_http_and_browser_collectors_and_site_summarizer()`
	@classmethod
	def collect_http_batch(cls, root, urls, *, profile: str='auto', scope: str='public', session_id=None, refresh_reason=None, max_age: float=86400, headers=None, context=None, fetcher=None, browser: str='auto', cdp_port=None, cdp_fetcher=None, http_get=None, cdp_call=None) -> dict:
		cleaned = [str(u).strip() for u in (urls or ()) if str(u).strip()]
		if not cleaned:
			raise ValueError('Provide at least one HTTP(S) URL')
		plan = {'requests': [{'url': u, 'profile': profile, 'scope': scope, 'session_id': session_id, 'refresh_reason': refresh_reason, 'max_age': max_age, 'headers': headers, 'context': context, 'browser': browser} for u in cleaned]}
		return cls(root, plan, fetcher=fetcher, browser=browser, cdp_port=cdp_port, session_id=session_id, cdp_fetcher=cdp_fetcher, http_get=http_get, cdp_call=cdp_call).run()
	# @used-by :func:`agent_tools.research.collect_plan()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_batch_http_and_browser_collectors_and_site_summarizer()`
	def run(self) -> dict:
		if self.__browser not in BROWSER_MODES:
			raise ValueError(f'Unknown browser mode: {self.__browser}; choose {BROWSER_MODES}')
		if not isinstance(self.__plan, dict) or not isinstance(self.__plan.get('requests'), list) or (not self.__plan['requests']):
			raise ValueError('Plan needs a nonempty requests list')
		shared_shell: dict = {'instance': None}
		use_lazy = None is self.__cdp_fetcher and None is self.__http_get and None is self.__cdp_call and None is self.__cdp_port
		results: list[dict] = []
		try:
			for idx, entry in enumerate(self.__plan['requests']):
				results.append(self.__run_plan_entry(entry, idx, shared_shell, use_lazy))
		finally:
			if None is not shared_shell['instance']:
				shared_shell['instance'].close()
		return self.__build_batch_result(self.__root, results, include_detail=True)