# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import subprocess
import tempfile
import time
from Df.Harness.lib.browser import NO_WINDOW, dfh_checked_ws, dfh_http_json, dfh_read_active_port_file, dfh_resolve_headless_shell
from agent_tools.runtime import settings
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class HeadlessShell:
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__lazy_headless_fetch()`
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__run_browser_url()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__shell_ctx()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_cdp_session_headless_shell_and_dom_poller()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __init__(self, config=None, *, executable=None):
		self.config = settings() if None is config else config
		self.executable = Path(executable) if executable else dfh_resolve_headless_shell(self.config)
		self.__temp_dir = None
		self.__proc = None
		self.endpoint = None
		self.browser_ws = None
		self.version = None
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__lazy_headless_fetch()`
	# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__run_browser_url()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__shell_ctx()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_cdp_session_headless_shell_and_dom_poller()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __enter__(self):
		if not self.executable.is_file():
			raise FileNotFoundError(f'Configured chrome-headless-shell executable does not exist: {self.executable}')
		self.__temp_dir = tempfile.TemporaryDirectory(prefix='harness-chs-')
		udd = Path(self.__temp_dir.name)
		argv = [str(self.executable), '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--disable-sync', '--remote-debugging-port=0', f'--user-data-dir={udd}']
		self.__proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=NO_WINDOW)
		port = self.__wait_active_port(udd / 'DevToolsActivePort')
		self.endpoint = f'http://127.0.0.1:{port}'
		self.__wait_version()
		return self
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__shell_ctx()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __exit__(self, exc_type, exc, tb):
		self.close()
		return False
	# @used-by :meth:`HeadlessShell.close()`
	def __stop_process(self, proc) -> None:
		try:
			proc.terminate()
			proc.wait(timeout=3)
		except Exception:
			try:
				proc.kill()
				proc.wait(timeout=2)
			except Exception:
				pass
		if None is not proc.stderr:
			try:
				proc.stderr.close()
			except OSError:
				pass
	# @used-by :meth:`HeadlessShell.__enter__()`
	def __wait_active_port(self, active_file: Path) -> int:
		deadline, port = (time.time() + 10.0, None)
		while time.time() < deadline:
			if None is not self.__proc.poll():
				err = self.__proc.stderr.read().decode('utf-8', errors='replace').strip() if self.__proc.stderr else ''
				self.close()
				raise RuntimeError(f'chrome-headless-shell exited prematurely: {err}')
			if active_file.is_file():
				try:
					port, _ = dfh_read_active_port_file(active_file)
					break
				except (OSError, ValueError):
					pass
			time.sleep(0.05)
		if None is port:
			self.close()
			raise RuntimeError('Timed out waiting for chrome-headless-shell DevToolsActivePort')
		return port
	# @used-by :meth:`HeadlessShell.__enter__()`
	def __wait_version(self) -> None:
		ver_deadline = time.time() + 5.0
		while time.time() < ver_deadline:
			try:
				self.version = dfh_http_json(self.endpoint + '/json/version')
				self.browser_ws = dfh_checked_ws(self.version.get('webSocketDebuggerUrl'), self.endpoint)
				break
			except Exception:
				time.sleep(0.05)
		if not self.browser_ws:
			self.close()
			raise RuntimeError('chrome-headless-shell /json/version did not become ready')
	# @used-by :meth:`HeadlessShell.__exit__()`
	# @used-by :meth:`HeadlessShell.__wait_active_port()`
	# @used-by :meth:`HeadlessShell.__wait_version()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_cdp_session_headless_shell_and_dom_poller()`
	def close(self):
		proc = self.__proc
		self.__proc = None
		if None is not proc:
			self.__stop_process(proc)
		temp_dir = self.__temp_dir
		self.__temp_dir = None
		if None is not temp_dir:
			try:
				temp_dir.cleanup()
			except OSError:
				pass
