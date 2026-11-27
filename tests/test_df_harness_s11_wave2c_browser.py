# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
WT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = WT_ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :mod:`unittest`
class DfHarnessS11Wave2CBrowserTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	def test_browser_lib_helpers_validate_endpoints_ports_and_operations(self) -> None:
		from Df.Harness.lib.browser import DOM_CAPTURE_EXPR, READ_ONLY_CDP_EXPRESSIONS, dfh_argument_values, dfh_checked_ws, dfh_discover_cdp_browser, dfh_endpoint, dfh_endpoint_with_meta, dfh_node_binary, dfh_normal_path, dfh_operation, dfh_probe_cdp_arguments, dfh_profile, dfh_read_active_port_file, dfh_resolve_cdp_port, dfh_save_cdp_identity, dfh_session
		self.assertEqual(DOM_CAPTURE_EXPR, READ_ONLY_CDP_EXPRESSIONS['dom_capture'])
		self.assertEqual('read', dfh_operation('Runtime.evaluate', {'throwOnSideEffect': True}))
		self.assertEqual('write', dfh_operation('Runtime.evaluate', {}))
		self.assertEqual('forbidden', dfh_operation('Browser.close'))
		self.assertEqual('screenshot', dfh_operation('Page.captureScreenshot'))
		self.assertEqual('navigate', dfh_operation('Page.navigate'))
		self.assertEqual('close', dfh_operation('Target.closeTarget'))
		self.assertEqual('c:/profile/a', dfh_normal_path('"C:\\Profile\\A\\"'))
		self.assertEqual(['/a', '/b'], dfh_argument_values(['--udd=/a', '--udd', '/b'], '--udd'))
		self.assertEqual('ws://127.0.0.1:9222/devtools/browser/1', dfh_checked_ws('ws://127.0.0.1:9222/devtools/browser/1', 'http://127.0.0.1:9222'))
		with self.assertRaises(ValueError):
			dfh_checked_ws('ws://127.0.0.1:9999/devtools/browser/1', 'http://127.0.0.1:9222')
		self.assertEqual(9333, dfh_resolve_cdp_port({}, 9333))
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			ap = root / 'DevToolsActivePort'
			ap.write_text('9223\n/devtools/browser/abc\n', encoding='utf-8')
			self.assertEqual((9223, '/devtools/browser/abc'), dfh_read_active_port_file(ap))
			ep, ws_path, used = dfh_endpoint_with_meta({'devtools_active_port': str(ap)})
			self.assertEqual(('http://127.0.0.1:9223', '/devtools/browser/abc', True), (ep, ws_path, used))
			self.assertEqual('http://127.0.0.1:9222', dfh_endpoint({'endpoint': 'http://127.0.0.1:9222/'}))
			cfg = {'workspace_root': str(root), 'text': {'browser': {'node': 'node', 'sessions': {'s1': {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222', 'profile': {'path': str(root / 'prof'), 'argument': '--user-data-dir'}, 'target_url_patterns': ['https://example.org/*'], 'allowed_operations': ['read', 'create', 'close']}}}}}
			self.assertEqual('node', dfh_node_binary(cfg))
			sess = dfh_session({'session_id': 's1'}, cfg)
			self.assertEqual((str(root / 'prof'), '--user-data-dir'), dfh_profile(sess, cfg))
			ver, tgs, bws = dfh_discover_cdp_browser('http://127.0.0.1:9222', lambda u: {'Browser': 'Chrome', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/browser/b1'} if u.endswith('/version') else [])
			self.assertEqual(('Chrome', [], 'ws://127.0.0.1:9222/devtools/browser/b1'), (ver['Browser'], tgs, bws))
			self.assertEqual(['--user-data-dir=/p'], dfh_probe_cdp_arguments(bws, lambda _u, _m, _p: {'arguments': ['--user-data-dir=/p']}))
			ref, sha = dfh_save_cdp_identity(root, {'schema_version': 1, 'target_id': 't1'})
			self.assertTrue(ref.startswith('Evidence/CDPSessions/'))
			self.assertEqual(64, len(sha))
	# @used-by :mod:`unittest`
	def test_cdp_session_headless_shell_and_dom_poller(self) -> None:
		from Df.Harness.Text.Browser.CdpSession import CdpSession
		from Df.Harness.Text.Browser.DomPoller import DomPoller
		from Df.Harness.Text.Browser.HeadlessShell import HeadlessShell
		from agent_tools import text_browser
		self.assertIs(CdpSession, text_browser.CDPSession)
		self.assertIs(HeadlessShell, text_browser.ManagedHeadlessShell)
		calls = []
		fake_call = lambda url, method, params: (calls.append((url, method)), {'sessionId': 'sid-1'} if 'Target.attachToTarget' == method else {'result': {'value': {'url': 'https://example.org/p', 'html': '<html><body>Hello world</body></html>', 'title': 'Hi', 'readyState': 'complete', 'textLen': 11}}} if 'Runtime.evaluate' == method else {})[1]
		with CdpSession('ws://127.0.0.1:9222/devtools/browser/b1', {}, cdp_call=fake_call) as mux:
			sid = mux.attach_target('t1', fallback_ws='ws://127.0.0.1:9222/devtools/page/t1')
			self.assertEqual('sid-1', sid)
			data = DomPoller(mux, sid, 5, single_pass=True).poll()
			self.assertEqual('Hi', data['title'])
			mux.detach_target(sid)
		self.assertTrue(any(('Target.detachFromTarget' == m for _, m in calls)))
		with tempfile.TemporaryDirectory() as td:
			shell = HeadlessShell({}, executable=Path(td) / 'missing-shell')
			with self.assertRaises(FileNotFoundError):
				shell.__enter__()
			shell.close()
	# @used-by :mod:`unittest`
	def test_preflight_guarded_cdp_tab_broker_and_collectors(self) -> None:
		from Df.Harness.Text.Browser.AnchorStatusChecker import AnchorStatusChecker
		from Df.Harness.Text.Browser.CdpDomCollector import CdpDomCollector
		from Df.Harness.Text.Browser.GuardedCdp import GuardedCdp
		from Df.Harness.Text.Browser.HeadlessDomCollector import HeadlessDomCollector
		from Df.Harness.Text.Browser.PreflightChecker import PreflightChecker
		from Df.Harness.Text.Browser.TabCreator import TabCreator
		from Df.Harness.Text.Browser.TabRemover import TabRemover
		from agent_tools import text_browser
		self.assertIs(GuardedCdp, text_browser.GuardedCDP)
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			prof = root / 'chrome-default'
			cfg = {'workspace_root': str(root), 'text': {'browser': {'primary_session_id': 's1', 'sessions': {'s1': {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222', 'profile': {'path': str(prof), 'argument': '--user-data-dir'}, 'target_url_patterns': ['https://example.org/*'], 'allowed_operations': ['read', 'create', 'close']}}}}}
			targets = [{'id': 't1', 'type': 'page', 'url': 'https://example.org/home', 'title': 'Home', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/t1'}]
			http_get = lambda u: {'Browser': 'Chrome/130', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/browser/b1'} if u.endswith('/version') else list(targets)
			cdp_call = lambda _u, m, p: {'arguments': [f'--user-data-dir={prof}']} if 'Browser.getBrowserCommandLine' == m else {'targetId': 't2'} if 'Target.createTarget' == m else {'sessionId': 'sid-2'} if 'Target.attachToTarget' == m else {'result': {'value': {'url': 'https://example.org/new', 'html': '<html><body>Captured DOM content</body></html>', 'title': 'New', 'readyState': 'complete', 'textLen': 20}}} if 'Runtime.evaluate' == m else {'success': True}
			report = PreflightChecker({'session_id': 's1', 'target_id': 't1'}, config=cfg, http_get=http_get, cdp_call=cdp_call).check()
			self.assertTrue(report['valid'])
			anchor = AnchorStatusChecker(session_id='s1', config=cfg, http_get=http_get, cdp_call=cdp_call).check()
			self.assertTrue(anchor['valid'])
			guard = GuardedCdp(root, {'session_id': 's1', 'target_id': 't1'}, config=cfg, http_get=http_get, cdp_call=cdp_call)
			self.assertTrue(hasattr(guard, '_lock'))
			self.assertTrue(hasattr(guard, '_broker_create_tab'))
			self.assertTrue(hasattr(guard, '_broker_remove_tab'))
			self.assertTrue(guard.inspect()['valid'])
			dom = CdpDomCollector(root, 'https://example.org/new', session_id='s1', config=cfg, http_get=http_get, cdp_call=cdp_call).collect()
			self.assertEqual('New', dom['title'])
			self.assertTrue(dom['closed_after_capture'])
			with self.assertRaises(ValueError):
				HeadlessDomCollector(root, 'ftp://example.org/bad', config=cfg).collect()
			self.assertTrue(callable(TabCreator))
			self.assertTrue(callable(TabRemover))
if '__main__' == __name__:
	unittest.main()
