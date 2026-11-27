# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urlsplit
from Df.Harness.Text.Browser.CdpSession import CdpSession
from Df.Harness.Text.Browser.DomPoller import DomPoller
from Df.Harness.Text.Browser.HeadlessShell import HeadlessShell
from Df.Harness.lib.browser import dfh_save_cdp_identity
from agent_tools.runtime import settings
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class HeadlessDomCollector:
	# @used-by :func:`agent_tools.text_browser.collect_headless_dom()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.collect()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_preflight_guarded_cdp_tab_broker_and_collectors()`
	def __init__(self, root, url, *, timeout=15, config=None, headless_shell=None):
		self.__root = root
		self.__url = url
		self.__timeout = timeout
		self.__config = config
		self.__shell = headless_shell
	# @used-by :meth:`HeadlessDomCollector.collect()`
	def __capture_in_shell(self, shell, cfg: dict) -> tuple[object, str, bool]:
		with CdpSession(shell.browser_ws, cfg) as mux:
			ctx_id, target_id = (None, None)
			try:
				ctx_id = self.__create_context(mux)
				create_params = {'url': self.__url, 'background': True, **({'browserContextId': ctx_id} if ctx_id else {})}
				created = mux.send('Target.createTarget', create_params)
				target_id = created.get('targetId') if isinstance(created, dict) else None
				if not isinstance(target_id, str) or not target_id:
					raise RuntimeError('chrome-headless-shell did not return a targetId')
				page_sid = mux.attach_target(target_id)
				try:
					data = DomPoller(mux, page_sid, self.__timeout).poll()
				finally:
					mux.detach_target(page_sid)
			finally:
				closed = self.__dispose_target(mux, target_id, ctx_id)
		return (data, target_id, closed)
	# @used-by :meth:`HeadlessDomCollector.__capture_in_shell()`
	def __create_context(self, mux) -> str | None:
		try:
			ctx_res = mux.send('Target.createBrowserContext', {'disposeOnDetach': True})
			r = ctx_res.get('browserContextId') if isinstance(ctx_res, dict) else None
		except Exception:
			r = None
		return r
	# @used-by :meth:`HeadlessDomCollector.__capture_in_shell()`
	def __dispose_target(self, mux, target_id: str | None, ctx_id: str | None) -> bool:
		closed = False
		if target_id:
			try:
				close_res = mux.send('Target.closeTarget', {'targetId': target_id})
				closed = bool(isinstance(close_res, dict) and close_res.get('success', True))
			except Exception:
				closed = False
		if ctx_id:
			try:
				mux.send('Target.disposeBrowserContext', {'browserContextId': ctx_id})
			except Exception:
				pass
		return closed
	# @used-by :meth:`HeadlessDomCollector.collect()`
	@contextmanager
	def __shell_ctx(self, cfg: dict):
		if None is not self.__shell:
			yield self.__shell
		else:
			with HeadlessShell(cfg) as launched:
				yield launched
	# @used-by :func:`agent_tools.text_browser.collect_headless_dom()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.collect()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_preflight_guarded_cdp_tab_broker_and_collectors()`
	def collect(self) -> dict:
		if None is self.__root or not str(self.__root).strip():
			raise ValueError('An explicit project root is required')
		root_path = Path(self.__root).resolve()
		if not root_path.is_dir():
			raise ValueError('Project root is not a directory')
		cfg = settings() if None is self.__config else deepcopy(self.__config)
		parsed_req = urlsplit(urldefrag(self.__url)[0])
		if parsed_req.scheme not in ('http', 'https') or not parsed_req.hostname:
			raise ValueError('A valid HTTP(S) URL is required for headless DOM collection')
		with self.__shell_ctx(cfg) as shell:
			data, target_id, closed = self.__capture_in_shell(shell, cfg)
			if not isinstance(data, dict) or not isinstance(data.get('html'), str) or (not data['html'].strip()):
				raise RuntimeError('Headless DOM capture returned empty or invalid HTML')
			profile_meta = {'status': 'verified', 'mode': 'ephemeral_headless_shell', 'evidence_method': 'DevToolsActivePort+Target.createBrowserContext', 'executable': str(shell.executable)}
			id_ref, id_hash = dfh_save_cdp_identity(root_path, {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'endpoint': shell.endpoint, 'browser': (shell.version or {}).get('Browser'), 'browser_websocket': shell.browser_ws, 'target_id': target_id, 'target_mode': 'ephemeral_headless_context', 'closed_after_capture': closed, 'profile': profile_meta})
			r = {'url': data.get('url') or self.__url, 'html': data['html'], 'title': data.get('title') or '', 'target_id': target_id, 'target_mode': 'ephemeral_headless_context', 'closed_after_capture': closed, 'cdp_identity': id_ref, 'cdp_identity_sha256': id_hash, 'endpoint': shell.endpoint}
		return r
