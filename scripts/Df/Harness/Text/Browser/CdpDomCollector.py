# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urlsplit
from Df.Harness.Text.Browser.CdpSession import CdpSession
from Df.Harness.Text.Browser.DomPoller import DomPoller
from Df.Harness.Text.Browser.GuardedCdp import GuardedCdp
from Df.Harness.Text.Browser.HeadlessDomCollector import HeadlessDomCollector
from Df.Harness.lib.browser import dfh_argument_values, dfh_checked_ws, dfh_discover_cdp_browser, dfh_endpoint, dfh_endpoint_lock, dfh_http_json, dfh_probe_cdp_arguments, dfh_resolve_cdp_port, dfh_save_cdp_identity, dfh_transport
from agent_tools.runtime import settings
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CdpDomCollector:
	# @used-by :func:`agent_tools.text_browser.collect_cdp_dom()`
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__lazy_headless_fetch()`
	# @used-by :meth:`Df.Harness.Research.BrowserCollector.BrowserCollector.__read_dom()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_preflight_guarded_cdp_tab_broker_and_collectors()`
	def __init__(self, root, url, *, cdp_port=None, session_id=None, timeout=15, config=None, http_get=None, cdp_call=None, headless_shell=None):
		self.__root = root
		self.__url = url
		self.__cdp_port = cdp_port
		self.__session_id = session_id
		self.__timeout = timeout
		self.__config = config
		self.__http_get = http_get
		self.__cdp_call = cdp_call
		self.__shell = headless_shell
	# @used-by :meth:`CdpDomCollector.__collect_direct_port()`
	def __capture_via_cdp(self, browser_ws: str, endpoint: str, existing_ids: set, get, cfg: dict) -> tuple[object, str, bool]:
		single_pass = None is not self.__cdp_call
		with CdpSession(browser_ws, cfg, cdp_call=self.__cdp_call) as mux:
			created_res = mux.send('Target.createTarget', {'url': self.__url, 'background': True, 'hidden': True})
			target_id = created_res.get('targetId') if isinstance(created_res, dict) else None
			if not isinstance(target_id, str) or not target_id or target_id in existing_ids:
				raise RuntimeError('Browser did not return a distinct created hidden target ID')
			closed = False
			try:
				fb_ws = self.__fallback_ws(endpoint, target_id, get) if single_pass else None
				page_sid = mux.attach_target(target_id, fallback_ws=fb_ws)
				try:
					data = DomPoller(mux, page_sid, self.__timeout, single_pass=single_pass).poll()
				finally:
					mux.detach_target(page_sid)
			finally:
				closed = self.__close_target(mux, target_id)
		return (data, target_id, closed)
	# @used-by :meth:`CdpDomCollector.__capture_via_cdp()`
	def __close_target(self, mux, target_id: str) -> bool:
		try:
			close_res = mux.send('Target.closeTarget', {'targetId': target_id})
			r = bool(isinstance(close_res, dict) and close_res.get('success', True))
		except Exception:
			r = False
		return r
	# @used-by :meth:`CdpDomCollector.collect()`
	def __collect_direct_port(self, root_path: Path, cfg: dict) -> dict:
		port = dfh_resolve_cdp_port(cfg, self.__cdp_port)
		endpoint = dfh_endpoint({'endpoint': f'http://127.0.0.1:{port}'})
		get, call = (self.__http_get or dfh_http_json, dfh_transport(cfg, self.__cdp_call))
		parsed_req = urlsplit(urldefrag(self.__url)[0])
		if parsed_req.scheme not in ('http', 'https') or not parsed_req.hostname:
			raise ValueError('A valid HTTP(S) URL is required for CDP DOM collection')
		with dfh_endpoint_lock(endpoint, cfg):
			version, targets, browser_ws = dfh_discover_cdp_browser(endpoint, get)
			udd = dfh_argument_values(dfh_probe_cdp_arguments(browser_ws, call), '--user-data-dir')
			if not udd:
				raise PermissionError('CDP endpoint profile cannot be verified (--user-data-dir absent); refusing unverified DOM capture')
			profile_info = {'status': 'verified', 'argument': '--user-data-dir', 'observed': udd[0], 'evidence_method': 'Browser.getBrowserCommandLine'}
			existing_ids = {t.get('id') for t in targets if isinstance(t, dict) and t.get('id')}
			data, target_id, closed = self.__capture_via_cdp(browser_ws, endpoint, existing_ids, get, cfg)
			if not isinstance(data, dict) or not isinstance(data.get('html'), str) or (not data['html'].strip()):
				raise RuntimeError('CDP DOM capture returned empty or invalid HTML')
			id_ref, id_hash = dfh_save_cdp_identity(root_path, {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'endpoint': endpoint, 'browser': version.get('Browser'), 'browser_websocket': browser_ws, 'target_id': target_id, 'target_mode': 'hidden_session_target', 'closed_after_capture': closed, 'profile': profile_info})
			r = {'url': data.get('url') or self.__url, 'html': data['html'], 'title': data.get('title') or '', 'target_id': target_id, 'target_mode': 'hidden_session_target', 'closed_after_capture': closed, 'cdp_identity': id_ref, 'cdp_identity_sha256': id_hash, 'endpoint': endpoint}
		return r
	# @used-by :meth:`CdpDomCollector.__capture_via_cdp()`
	def __fallback_ws(self, endpoint: str, target_id: str, get) -> str | None:
		current_targets = get(endpoint + '/json/list')
		matches = [t for t in current_targets if isinstance(t, dict) and t.get('id') == target_id and t.get('webSocketDebuggerUrl')] if isinstance(current_targets, list) else []
		return dfh_checked_ws(matches[0].get('webSocketDebuggerUrl'), endpoint) if matches else None
	# @used-by :func:`agent_tools.text_browser.collect_cdp_dom()`
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__lazy_headless_fetch()`
	# @used-by :meth:`Df.Harness.Research.BrowserCollector.BrowserCollector.__read_dom()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_preflight_guarded_cdp_tab_broker_and_collectors()`
	def collect(self) -> dict:
		if None is self.__root or not str(self.__root).strip():
			raise ValueError('An explicit project root is required')
		root_path = Path(self.__root).resolve()
		if not root_path.is_dir():
			raise ValueError('Project root is not a directory')
		cfg = settings() if None is self.__config else deepcopy(self.__config)
		if isinstance(self.__session_id, str) and self.__session_id.strip():
			r = GuardedCdp(root_path, {'session_id': self.__session_id.strip()}, config=cfg, http_get=self.__http_get, cdp_call=self.__cdp_call).capture_authenticated_dom(self.__url, timeout=self.__timeout)
		elif None is self.__http_get and None is self.__cdp_call and (None is self.__cdp_port or int(self.__cdp_port) == dfh_resolve_cdp_port(cfg)):
			if None is not self.__cdp_port:
				raise PermissionError('Public DOM collection cannot connect to the user Chrome CDP port; omit --cdp-port to use managed chrome-headless-shell or pass --session-id for authenticated capture')
			r = HeadlessDomCollector(root_path, self.__url, timeout=self.__timeout, config=cfg, headless_shell=self.__shell).collect()
		else:
			r = self.__collect_direct_port(root_path, cfg)
		return r
