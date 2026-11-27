# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
import time
from Df.Harness.Research.ChallengeClassifier import ChallengeClassifier
from Df.Harness.lib.browser import DOM_CAPTURE_EXPR
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DomPoller:
	# @used-by :func:`agent_tools.text_browser._poll_dom_on_session()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__capture_via_cdp()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__poll_target()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__capture_in_shell()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_cdp_session_headless_shell_and_dom_poller()`
	def __init__(self, cdp_sess, session_id, timeout, *, single_pass=False):
		self.__sess = cdp_sess
		self.__sid = session_id
		self.__timeout = timeout
		self.__single = single_pass
	# @used-by :meth:`DomPoller.poll()`
	def __is_settled(self, val: dict, challenge_seen_at: float | None) -> tuple[bool, float | None]:
		html_str, cur_url = (val['html'], val.get('url') or '')
		ready = val.get('readyState') in ('complete', 'interactive') and cur_url not in ('', 'about:blank') and (not cur_url.startswith('about:blank#'))
		has_text = 0 < (val.get('textLen') or 0) or bool(re.sub('(?is)<(?:script|style|head|title)[^>]*>.*?</(?:script|style|head|title)>|<[^>]+>', '', html_str).strip())
		is_challenge = ChallengeClassifier(html_str).is_challenge()
		if self.__single or (ready and has_text and (not is_challenge)):
			r = (True, challenge_seen_at)
		elif is_challenge and 'complete' == val.get('readyState'):
			seen = time.time() if None is challenge_seen_at else challenge_seen_at
			r = (1.5 <= time.time() - seen, seen)
		else:
			r = (False, challenge_seen_at)
		return r
	# @used-by :meth:`DomPoller.poll()`
	def __read_once(self):
		native = self.__sess.send('Runtime.evaluate', {'expression': DOM_CAPTURE_EXPR, 'throwOnSideEffect': True, 'returnByValue': True}, session_id=self.__sid)
		val = native.get('result', {}).get('value') if isinstance(native, dict) and (not native.get('exceptionDetails')) else None
		return val if isinstance(val, dict) and isinstance(val.get('html'), str) and val['html'].strip() else None
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_wait_repo()`
	# @used-by :func:`agent_tools.text_browser._poll_dom_on_session()`
	# @used-by :func:`test_stdin_detachment._kill_tree()`
	# @used-by :meth:`Df.Harness.TestRunner.ParallelRunner.ParallelRunner.__poll_proc()`
	# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.__poll_module_proc()`
	# @used-by :meth:`Df.Harness.TestRunner.WatchdogRunner.WatchdogRunner.__poll_until_exit()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__capture_via_cdp()`
	# @used-by :meth:`Df.Harness.Text.Browser.CdpSession.CdpSession.close()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__poll_target()`
	# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.__capture_in_shell()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_runner_process_tree_watchdog_semaphore_and_pytest_modes()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_cdp_session_headless_shell_and_dom_poller()`
	def poll(self):
		deadline, data, challenge_seen_at = (time.time() + max(1.0, float(self.__timeout)), None, None)
		while True:
			try:
				val = self.__read_once()
				if None is not val:
					data = val
					done, challenge_seen_at = self.__is_settled(val, challenge_seen_at)
					if done:
						break
			except Exception:
				if self.__single:
					raise
			if self.__single or time.time() >= deadline:
				break
			time.sleep(0.3)
		return data
