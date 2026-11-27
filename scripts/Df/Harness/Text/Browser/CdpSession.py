# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
import json
import os
import subprocess
from Df.Harness.lib.browser import NODE_MUX_SESSION, NO_WINDOW, dfh_node_binary
from agent_tools.runtime import settings
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CdpSession:
	# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.__init_sentinel()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__capture_via_cdp()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__create_target_id()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.capture_authenticated_dom()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__capture_in_shell()`
	# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__mux()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__run_mux()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_cdp_session_headless_shell_and_dom_poller()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_browser.DfHarnessS11Wave2CCovBrowserTests.test_cdp_dom_collector_and_cdp_session_pipe_lifecycle()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __init__(self, browser_ws, config=None, *, cdp_call=None):
		self.browser_ws = browser_ws
		self.config = settings() if None is config else config
		self.__override = cdp_call
		self.__proc = None
		self.__req_id = 0
		self.__session_targets = {}
	# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.__init_sentinel()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__capture_via_cdp()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__create_target_id()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.capture_authenticated_dom()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__capture_in_shell()`
	# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__mux()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__run_mux()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_cdp_session_headless_shell_and_dom_poller()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_browser.DfHarnessS11Wave2CCovBrowserTests.test_cdp_dom_collector_and_cdp_session_pipe_lifecycle()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __enter__(self):
		if None is self.__override:
			node = dfh_node_binary(self.config)
			if not node:
				raise ValueError('Configure a Node runtime for the persistent CDP session')
			self.__proc = subprocess.Popen([node, '--input-type=module', '-e', NODE_MUX_SESSION], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1, env={**os.environ, 'HARNESS_CDP_WS': self.browser_ws}, creationflags=NO_WINDOW)
			ready_line = self.__proc.stdout.readline() if self.__proc.stdout else ''
			if not ready_line.strip():
				err = self.__proc.stderr.read().strip() if self.__proc.stderr else 'no ready signal'
				self.close()
				raise RuntimeError('CDP session startup failed: ' + err)
			ready_obj = json.loads(ready_line)
			if not isinstance(ready_obj, dict) or not ready_obj.get('ready'):
				self.close()
				raise RuntimeError('CDP session did not report ready')
		return self
	# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.__init_sentinel()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__capture_via_cdp()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__create_target_id()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.capture_authenticated_dom()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__capture_in_shell()`
	# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__mux()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__run_mux()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_cdp_session_headless_shell_and_dom_poller()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_browser.DfHarnessS11Wave2CCovBrowserTests.test_cdp_dom_collector_and_cdp_session_pipe_lifecycle()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __exit__(self, exc_type, exc, tb):
		self.close()
		return False
	# @used-by :meth:`CdpSession.close()`
	def __close_streams(self, proc) -> None:
		for stream in (proc.stdin, proc.stdout, proc.stderr):
			if None is not stream:
				try:
					stream.close()
				except OSError:
					pass
	# @used-by :meth:`CdpSession.send()`
	def __read_reply(self, method: str, rid: int):
		while True:
			line = self.__proc.stdout.readline()
			if not line:
				err_tail = self.__proc.stderr.read().strip() if self.__proc.stderr else ''
				tail = err_tail or 'EOF'
				raise RuntimeError(f'CDP session closed during {method}: {tail}')
			msg = json.loads(line)
			if isinstance(msg, dict) and msg.get('req_id') == rid:
				if 'error' in msg:
					raise RuntimeError(f'CDP {method} error: ' + json.dumps(msg['error']))
				r = msg.get('result', {})
				break
		return r
	# @used-by :func:`test_df_harness_s11_wave2c_cov_browser._make_headless_mux()`
	# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.__init_sentinel()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__capture_via_cdp()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__poll_target()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__capture_in_shell()`
	# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__probe_sentinel_page()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__run_mux()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_cdp_session_headless_shell_and_dom_poller()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def attach_target(self, target_id, *, fallback_ws=None):
		res = self.send('Target.attachToTarget', {'targetId': target_id, 'flatten': True})
		sid = res.get('sessionId') if isinstance(res, dict) else None
		if isinstance(sid, str) and sid:
			self.__session_targets[sid] = fallback_ws or f'{self.browser_ws}#session={sid}'
			r = sid
		elif None is not self.__override and fallback_ws:
			fake_sid = f'compat:{target_id}'
			self.__session_targets[fake_sid] = fallback_ws
			r = fake_sid
		else:
			raise RuntimeError(f'CDP Target.attachToTarget did not return a sessionId for {target_id}')
		return r
	# @used-by :meth:`CdpSession.__enter__()`
	# @used-by :meth:`CdpSession.__exit__()`
	def close(self):
		proc = self.__proc
		self.__proc = None
		if None is not proc:
			if None is proc.poll():
				try:
					if proc.stdin and (not proc.stdin.closed):
						proc.stdin.write(json.dumps({'close': True}) + '\n')
						proc.stdin.flush()
				except OSError:
					pass
			try:
				proc.wait(timeout=3)
			except subprocess.TimeoutExpired:
				proc.kill()
				proc.wait(timeout=2)
			self.__close_streams(proc)
	# @used-by :func:`test_df_harness_s11_wave2c_cov_browser._make_headless_mux()`
	# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.__init_sentinel()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__capture_via_cdp()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__poll_target()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__capture_in_shell()`
	# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__probe_sentinel_page()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__run_mux()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_cdp_session_headless_shell_and_dom_poller()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def detach_target(self, session_id):
		if isinstance(session_id, str) and session_id and (not session_id.startswith('compat:')):
			try:
				self.send('Target.detachFromTarget', {'sessionId': session_id})
			except Exception:
				pass
		self.__session_targets.pop(session_id, None)
	# @used-by :func:`Df.Harness.lib.browser.dfh_query_target_infos()`
	# @used-by :func:`test_df_harness_s11_wave2c_cov_browser._make_headless_mux()`
	# @used-by :meth:`CdpSession.attach_target()`
	# @used-by :meth:`CdpSession.detach_target()`
	# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.__init_sentinel()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__capture_via_cdp()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__close_target()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__create_auth_target()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__capture_in_shell()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__create_context()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__dispose_target()`
	# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__page_has_marker()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__create_temp_tab()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__download_assets()`
	# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.eval_session()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_browser.DfHarnessS11Wave2CCovBrowserTests.test_cdp_dom_collector_and_cdp_session_pipe_lifecycle()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def send(self, method, params=None, *, session_id=None, timeout_ms=12000):
		params = deepcopy(params or {})
		if None is not self.__override:
			target_url = self.__session_targets.get(session_id, self.browser_ws) if session_id else self.browser_ws
			r = self.__override(target_url, method, params)
		else:
			if None is self.__proc or None is self.__proc.stdin or None is self.__proc.stdout:
				raise RuntimeError('Persistent CDP session is not open')
			self.__req_id += 1
			wire = {'req_id': self.__req_id, 'method': method, 'params': params, 'timeout_ms': int(timeout_ms)}
			if session_id:
				wire['sessionId'] = session_id
			self.__proc.stdin.write(json.dumps(wire) + '\n')
			self.__proc.stdin.flush()
			r = self.__read_reply(method, self.__req_id)
		return r
