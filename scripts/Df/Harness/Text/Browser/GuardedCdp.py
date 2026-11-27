# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from pathlib import Path
from urllib.parse import urldefrag, urlsplit
from Df.Harness.Text.Browser.CdpSession import CdpSession
from Df.Harness.Text.Browser.DomPoller import DomPoller
from Df.Harness.Text.Browser.PreflightChecker import PreflightChecker
from Df.Harness.Text.Browser.TabCreator import TabCreator
from Df.Harness.Text.Browser.TabRemover import TabRemover
from Df.Harness.lib.browser import dfh_checked_ws, dfh_endpoint, dfh_endpoint_lock, dfh_http_json, dfh_operation, dfh_save_cdp_identity, dfh_session, dfh_transport
from agent_tools.runtime import settings
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class GuardedCdp:
	# @used-by :func:`test_text_browser.dom_fixture()`
	# @used-by :meth:`Df.Harness.Research.DomCapturer.DomCapturer.__resolve_guard()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.collect()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.extract()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_preflight_guarded_cdp_tab_broker_and_collectors()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cross_wave.DfHarnessS11Wave2CCrossWaveTests.test_link_audit_accepts_wave2c_call_sites_and_guarded_cdp_class_seam()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.guard()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_m2a_extension_manifest_key_and_multi_profile_tab_broker_isolation()`
	def __init__(self, root, spec, *, config=None, http_get=None, cdp_call=None):
		if None is root or not str(root).strip():
			raise ValueError('An explicit project root is required')
		self.root = Path(root).resolve()
		if not self.root.is_dir():
			raise ValueError('Project root is not a directory')
		self.config = settings() if None is config else deepcopy(config)
		self.spec = deepcopy(spec)
		self.session = dfh_session(spec, self.config)
		self.get = http_get or dfh_http_json
		self.__cdp_override = cdp_call
		self.call_native = dfh_transport(self.config, cdp_call)
		self.__owned = {}
	# @used-by unused
	def __getattr__(self, name: str):
		compat = {'_lock': self.__lock, '_broker_create_tab': self.__broker_create_tab, '_broker_remove_tab': self.__broker_remove_tab}
		if name not in compat:
			raise AttributeError(name)
		return compat[name]
	# @used-by :meth:`GuardedCdp.__create_auth_target()`
	# @used-by :meth:`GuardedCdp.__create_target_id()`
	# @used-by :meth:`GuardedCdp.__getattr__()`
	def __broker_create_tab(self, cdp_sess, anchor_target_id, verified_ctx, url, endpoint):
		return TabCreator(cdp_sess, self.get, anchor_target_id, verified_ctx, url, endpoint).create()
	# @used-by :meth:`GuardedCdp.__getattr__()`
	# @used-by :meth:`GuardedCdp.capture_authenticated_dom()`
	def __broker_remove_tab(self, cdp_sess, anchor_target_id, ext_tab_id, target_id):
		return TabRemover(cdp_sess, anchor_target_id, ext_tab_id, target_id).remove()
	# @used-by :meth:`GuardedCdp.call()`
	# @used-by :meth:`GuardedCdp.capture_authenticated_dom()`
	# @used-by :meth:`GuardedCdp.create_target()`
	# @used-by :meth:`GuardedCdp.inspect()`
	def __check(self, *, require_target=True, cdp_session=None):
		override = None if self.call_native is dfh_transport(self.config, self.__cdp_override) and None is self.__cdp_override else self.call_native
		report = PreflightChecker(self.spec, config=self.config, http_get=self.get, cdp_call=override, require_target=require_target, cdp_session=cdp_session).check()
		if not report['valid']:
			raise PermissionError('; '.join(report['issues']) or 'CDP profile/target is unknown')
		return report
	# @used-by :meth:`GuardedCdp.capture_authenticated_dom()`
	def __create_auth_target(self, mux, report: dict, url: str) -> tuple[str, object, str]:
		verified_ctx, anchor_tid = (report['profile'].get('browser_context_id'), report['profile'].get('anchor_target_id'))
		create_params = {'url': url, 'background': True, 'hidden': True, **({'browserContextId': verified_ctx} if verified_ctx else {})}
		ext_tab_id, target_mode = (None, 'hidden_session_target')
		try:
			res = mux.send('Target.createTarget', create_params)
			target_id = res.get('targetId') if isinstance(res, dict) else None
		except RuntimeError as exc:
			if not verified_ctx:
				raise
			if not anchor_tid:
				raise PermissionError('Primary Chrome profile Default is verified via M-2B, but a secondary Chrome profile window was focused last; focus a Default window or load code/browser_extension (M-2A) in Default') from exc
			target_id, ext_tab_id = self.__broker_create_tab(mux, anchor_tid, verified_ctx, url, report['endpoint'])
			target_mode = 'm2a_extension_background_tab'
		if not isinstance(target_id, str) or not target_id:
			raise RuntimeError('Browser did not return a created target ID for authenticated capture')
		return (target_id, ext_tab_id, target_mode)
	# @used-by :meth:`GuardedCdp.__create_target_id()`
	def __create_params(self, url: str, background: bool, hidden: bool, verified_ctx: str | None) -> dict:
		r = {'url': url, 'background': True} if (background or hidden) else {'url': url, 'newWindow': True}
		if hidden:
			r['hidden'] = True
		if verified_ctx:
			r['browserContextId'] = verified_ctx
		return r
	# @used-by :meth:`GuardedCdp.create_target()`
	def __create_target_id(self, report: dict, url: str, background: bool, hidden: bool) -> tuple[str, object]:
		browser_ws, verified_ctx, anchor_tid = (report['browser']['websocket_url'], report['profile'].get('browser_context_id'), report['profile'].get('anchor_target_id'))
		ext_tab_id = None
		try:
			result = self.call_native(browser_ws, 'Target.createTarget', self.__create_params(url, background, hidden, verified_ctx))
			identifier = result.get('targetId') if isinstance(result, dict) else None
		except RuntimeError as exc:
			if not verified_ctx:
				raise
			if not anchor_tid or (not background and (not hidden)):
				raise PermissionError('Cannot create tab in primary profile Default while another Chrome profile is focused without M-2A anchor extension loaded') from exc
			with CdpSession(browser_ws, self.config, cdp_call=self.__cdp_override) as mux:
				identifier, ext_tab_id = self.__broker_create_tab(mux, anchor_tid, verified_ctx, url, report['endpoint'])
		if not isinstance(identifier, str) or not identifier or identifier == report['target'].get('id'):
			raise RuntimeError('Browser did not return a distinct created target ID; no ownership is assigned')
		return (identifier, ext_tab_id)
	# @used-by :meth:`GuardedCdp.__poll_target()`
	def __fallback_ws(self, endpoint: str, target_id: str) -> str | None:
		cur_list = self.get(endpoint + '/json/list')
		found = next((t for t in cur_list if isinstance(t, dict) and t.get('id') == target_id and t.get('webSocketDebuggerUrl')), None)
		return dfh_checked_ws(found['webSocketDebuggerUrl'], endpoint) if found else None
	# @used-by :meth:`GuardedCdp.__getattr__()`
	# @used-by :meth:`GuardedCdp.call()`
	# @used-by :meth:`GuardedCdp.capture_authenticated_dom()`
	# @used-by :meth:`GuardedCdp.create_target()`
	# @used-by :meth:`GuardedCdp.inspect()`
	# @used-by :meth:`GuardedCdp.select_owned()`
	@contextmanager
	def __lock(self):
		with dfh_endpoint_lock(dfh_endpoint(self.session), self.config):
			yield
	# @used-by :meth:`GuardedCdp.__validate_auth_url()`
	# @used-by :meth:`GuardedCdp.call()`
	# @used-by :meth:`GuardedCdp.create_target()`
	def __permitted(self, op: str) -> None:
		allowed = set(self.session.get('allowed_operations', []))
		if 'allowed_operations' in self.spec:
			allowed &= set(self.spec['allowed_operations'])
		if op not in allowed:
			raise PermissionError(f'CDP {op} is not authorized for this session')
	# @used-by :meth:`GuardedCdp.capture_authenticated_dom()`
	def __poll_target(self, mux, target_id: str, endpoint: str, timeout: float, single_pass: bool):
		fb_ws = self.__fallback_ws(endpoint, target_id) if single_pass else None
		page_sid = mux.attach_target(target_id, fallback_ws=fb_ws)
		try:
			r = DomPoller(mux, page_sid, timeout, single_pass=single_pass).poll()
		finally:
			mux.detach_target(page_sid)
		return r
	# @used-by :meth:`GuardedCdp.call()`
	def __refresh_owned(self, op: str, target: dict, owned: dict | None) -> None:
		if owned:
			if 'close' == op:
				self.__owned.pop(target['id'], None)
			else:
				after = PreflightChecker(self.spec, config=self.config, http_get=self.get, cdp_call=self.__cdp_override).check()
				if after['valid']:
					owned['url'] = after['target']['url']
	# @used-by :meth:`GuardedCdp.capture_authenticated_dom()`
	def __validate_auth_url(self, url: str) -> None:
		if 'browser' != self.session['surface']:
			raise PermissionError('Authenticated DOM capture requires a browser session surface')
		for op in ('create', 'read', 'close'):
			self.__permitted(op)
		parsed_req = urlsplit(urldefrag(url)[0])
		if parsed_req.scheme not in ('http', 'https') or not parsed_req.hostname:
			raise ValueError('A valid HTTP(S) URL is required for CDP DOM collection')
		if not any((fnmatchcase(url, pattern) for pattern in self.session.get('target_url_patterns', []))):
			raise PermissionError('Target URL is outside the authorized session patterns')
	# @used-by :meth:`GuardedCdp.call()`
	def __validate_call(self, method: str, params: dict, op: str, target: dict, browser: dict, owned: dict | None) -> None:
		if op in ('navigate', 'write', 'close'):
			if 'browser' != self.session['surface'] or not owned:
				raise PermissionError('Existing user/app targets permit only authorized reads and screenshots')
			if owned['browser'] != browser['websocket_url'] or owned['url'] != target['url']:
				raise PermissionError('Owned target changed outside this guard; inspect ownership again')
		if 'targetId' in params and params['targetId'] != target['id']:
			raise PermissionError('CDP targetId differs from the verified selection')
		if any((key in params for key in ('sessionId', 'browserContextId'))):
			raise PermissionError('Caller-supplied CDP context/session routing is unsupported')
		if 'navigate' == op and 'Page.navigate' == method and (not any((fnmatchcase(params.get('url', ''), p) for p in self.session['target_url_patterns']))):
			raise PermissionError('Navigation URL is outside the authorized session')
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_m2a_extension_manifest_key_and_multi_profile_tab_broker_isolation()`
	def call(self, method, params=None, *, include_identity=False):
		params = deepcopy(params or {})
		op = dfh_operation(method, params)
		if 'forbidden' == op:
			raise PermissionError(f'Unsupported or unsafe CDP method: {method}')
		self.__permitted(op)
		with self.__lock():
			report = self.__check()
			target, browser = (report['target'], report['browser'])
			owned = self.__owned.get(target['id'])
			self.__validate_call(method, params, op, target, browser, owned)
			endpoint = browser['websocket_url'] if method.startswith(('Target.', 'Browser.')) else target['websocket_url']
			if method in ('Target.closeTarget', 'Browser.getWindowForTarget'):
				params['targetId'] = target['id']
			result = self.call_native(endpoint, method, params)
			self.__refresh_owned(op, target, owned)
			r = (result, deepcopy(report)) if include_identity else result
		return r
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.collect()`
	def capture_authenticated_dom(self, url, *, timeout=15):
		self.__validate_auth_url(url)
		with self.__lock():
			report = self.__check(require_target=False)
			browser_ws, endpoint, anchor_tid, single_pass = (report['browser']['websocket_url'], report['endpoint'], report['profile'].get('anchor_target_id'), None is not self.__cdp_override)
			with CdpSession(browser_ws, self.config, cdp_call=self.__cdp_override) as mux:
				target_id, ext_tab_id, target_mode = self.__create_auth_target(mux, report, url)
				try:
					data = self.__poll_target(mux, target_id, endpoint, timeout, single_pass)
				finally:
					closed = self.__broker_remove_tab(mux, anchor_tid, ext_tab_id, target_id)
			if not isinstance(data, dict) or not isinstance(data.get('html'), str) or (not data['html'].strip()):
				raise RuntimeError('Authenticated CDP DOM capture returned empty or invalid HTML')
			id_ref, id_hash = dfh_save_cdp_identity(self.root, {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'session_id': self.spec['session_id'], 'endpoint': endpoint, 'browser': report['browser']['product'], 'browser_websocket': browser_ws, 'target_id': target_id, 'target_mode': target_mode, 'closed_after_capture': closed, 'profile': report['profile']})
			r = {'url': data.get('url') or url, 'html': data['html'], 'title': data.get('title') or '', 'target_id': target_id, 'target_mode': target_mode, 'closed_after_capture': closed, 'cdp_identity': id_ref, 'cdp_identity_sha256': id_hash, 'endpoint': endpoint}
		return r
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_only_real_created_target_can_be_mutated_and_ownership_change_stops_close()`
	def create_target(self, url, *, background=False, hidden=False):
		if 'browser' != self.session['surface']:
			raise PermissionError('Desktop application window creation is unsupported')
		self.__permitted('create')
		if not any((fnmatchcase(url, pattern) for pattern in self.session.get('target_url_patterns', []))):
			raise PermissionError('New target URL is outside the authorized session')
		with self.__lock():
			report = self.__check(require_target=bool(self.spec.get('target_id')))
			browser_ws = report['browser']['websocket_url']
			identifier, ext_tab_id = self.__create_target_id(report, url, background, hidden)
			created = PreflightChecker({**self.spec, 'target_id': identifier, 'target_url': url}, config=self.config, http_get=self.get, cdp_call=self.__cdp_override).check()
			if not created['valid'] or created['browser']['websocket_url'] != browser_ws:
				raise RuntimeError('Created target could not be verified in the same browser; it was left open without ownership')
			self.__owned[identifier] = {'browser': browser_ws, 'url': url, 'ext_tab_id': ext_tab_id}
			r = {'target_id': identifier, 'owner': 'this-guard', 'session_id': self.spec['session_id'], 'new_window': not (background or hidden), 'background': bool(background or hidden), 'browser': browser_ws}
		return r
	# @used-by :meth:`Df.Harness.Research.DomCapturer.DomCapturer.capture()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_preflight_guarded_cdp_tab_broker_and_collectors()`
	def inspect(self, *, require_target=True):
		with self.__lock():
			r = self.__check(require_target=require_target)
		return r
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_only_real_created_target_can_be_mutated_and_ownership_change_stops_close()`
	def select_owned(self, identifier):
		with self.__lock():
			if identifier not in self.__owned:
				raise PermissionError('Target was not created by this guard')
			self.spec['target_id'] = identifier
			self.spec.pop('target_url', None)
