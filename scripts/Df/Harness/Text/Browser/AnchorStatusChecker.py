# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
import time
from urllib.parse import urlsplit
from Df.Harness.Text.Browser.CdpSession import CdpSession
from Df.Harness.Text.Browser.PreflightChecker import PreflightChecker
from Df.Harness.lib.browser import dfh_checked_ws, dfh_discover_cdp_browser, dfh_endpoint, dfh_http_json, dfh_session
from agent_tools.runtime import settings
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class AnchorStatusChecker:
	# @used-by :func:`agent_tools.text_browser.browser_anchor_status()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_preflight_guarded_cdp_tab_broker_and_collectors()`
	def __init__(self, *, session_id=None, init_sentinel_tab=None, config=None, http_get=None, cdp_call=None):
		self.__cfg = settings() if None is config else deepcopy(config)
		self.__sid = session_id or self.__cfg.get('text', {}).get('browser', {}).get('primary_session_id') or 'chrome-default'
		self.__init_tab = init_sentinel_tab
		self.__http_get = http_get
		self.__cdp_call = cdp_call
	# @used-by :meth:`AnchorStatusChecker.check()`
	def __init_sentinel(self, session: dict, sentinel_origin: str, sentinel_cookie: str) -> bool:
		endpoint = dfh_endpoint(session)
		_, targets, browser_ws = dfh_discover_cdp_browser(endpoint, self.__http_get or dfh_http_json)
		tab_id = self.__init_tab.strip()
		match = next((t for t in targets if isinstance(t, dict) and 'page' == t.get('type') and t.get('id') == tab_id), None)
		if not match:
			raise ValueError(f'Explicit Default profile tab_id not found: {self.__init_tab}')
		fb_ws = dfh_checked_ws(match['webSocketDebuggerUrl'], endpoint) if match.get('webSocketDebuggerUrl') else None
		with CdpSession(browser_ws, self.__cfg, cdp_call=self.__cdp_call) as mux:
			attach_sid = mux.attach_target(tab_id, fallback_ws=fb_ws)
			try:
				set_res = mux.send('Network.setCookie', {'name': sentinel_cookie, 'value': 'default-verified', 'url': sentinel_origin + '/', 'domain': urlsplit(sentinel_origin).hostname, 'path': '/', 'secure': True, 'httpOnly': True, 'sameSite': 'Strict', 'expires': int(time.time()) + 315360000}, session_id=attach_sid)
				r = bool(isinstance(set_res, dict) and set_res.get('success', True))
			finally:
				mux.detach_target(attach_sid)
		return r
	# @used-by :func:`agent_tools.text_browser.browser_anchor_status()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_preflight_guarded_cdp_tab_broker_and_collectors()`
	def check(self) -> dict:
		session = dfh_session({'session_id': self.__sid}, self.__cfg)
		prof_cfg = session.get('profile', {})
		sentinel_origin = (prof_cfg.get('sentinel_origin') or 'https://harness-profile.invalid').rstrip('/')
		sentinel_cookie = prof_cfg.get('sentinel_cookie_name') or '__harness_primary_profile'
		sentinel_initialized = self.__init_sentinel(session, sentinel_origin, sentinel_cookie) if isinstance(self.__init_tab, str) and self.__init_tab.strip() else False
		report = PreflightChecker({'session_id': self.__sid}, config=self.__cfg, http_get=self.__http_get, cdp_call=self.__cdp_call, require_target=False).check()
		return {'valid': report['valid'], 'session_id': self.__sid, 'extension_id': prof_cfg.get('extension_id'), 'extension_path': prof_cfg.get('extension_path'), 'sentinel_origin': sentinel_origin, 'sentinel_initialized': sentinel_initialized, 'profile': report['profile'], 'endpoint': report.get('endpoint'), 'issues': report['issues']}
