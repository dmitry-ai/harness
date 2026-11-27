# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from Df.Harness.Text.Browser.AnchorStatusChecker import AnchorStatusChecker
from Df.Harness.Text.Browser.CdpDomCollector import CdpDomCollector
from Df.Harness.Text.Browser.CdpSession import CdpSession
from Df.Harness.Text.Browser.GuardedCdp import GuardedCdp
from Df.Harness.Text.Browser.HeadlessDomCollector import HeadlessDomCollector
from Df.Harness.Text.Browser.PreflightChecker import PreflightChecker
from Df.Harness.Text.Browser.TabCreator import TabCreator
from Df.Harness.Text.Browser.TabRemover import TabRemover
from Df.Harness.lib.browser import dfh_browser_seam, dfh_headless_mcp_args, dfh_http_json
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :meth:`DfHarnessS11Wave2CCovBrowserTests.test_guarded_cdp_create_select_call_and_tab_broker()`
def _make_broker_sess():
	state = {'placeholder': ''}
	# @used-by :func:`_make_broker_sess()`
	def _send(method, params, session_id=None):
		if 'Runtime.evaluate' == method:
			expr = params['expression']
			if 'createBackgroundTab' in expr:
				state['placeholder'] = expr.split('"url": "')[1].split('"')[0]
				r: dict = {'result': {'value': {'ok': True, 'tabId': 77}}}
			else:
				r = {'result': {'value': {'ok': True}}}
		elif 'Target.getTargets' == method:
			r = {'targetInfos': [{'targetId': 't3', 'type': 'page', 'browserContextId': 'ctx1', 'url': state['placeholder']}]}
		else:
			r = {'ok': True}
		return r
	return SimpleNamespace(attach_target=lambda tid, **_k: f's-{tid}', detach_target=lambda _sid: None, send=_send)
# @used-by :meth:`DfHarnessS11Wave2CCovBrowserTests.test_anchor_status_preflight_ext_sentinel_and_lib_helpers()`
# @used-by :meth:`DfHarnessS11Wave2CCovBrowserTests.test_cdp_dom_collector_and_cdp_session_pipe_lifecycle()`
# @used-by :meth:`DfHarnessS11Wave2CCovBrowserTests.test_guarded_cdp_create_select_call_and_tab_broker()`
def _make_cfg(root: Path, *, ext_id: str | None=None, sentinel: str | None=None, account: dict | None=None) -> dict:
	prof: dict = {'path': '/tmp/p', 'argument': '--user-data-dir'}
	if ext_id:
		prof['extension_id'] = ext_id
	if sentinel:
		prof['sentinel_origin'] = sentinel
	sess: dict = {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222', 'profile': prof, 'allowed_operations': ['read', 'create', 'navigate', 'write', 'close'], 'target_url_patterns': ['https://example.com/*']}
	if account:
		sess['account'] = account
	return {'workspace_root': str(root), 'text': {'browser': {'primary_session_id': 's1', 'node': 'node', 'sessions': {'s1': sess}}}}
# @used-by :meth:`DfHarnessS11Wave2CCovBrowserTests.test_headless_shell_and_headless_dom_collector()`
def _make_headless_mux(dom_val: dict):
	table = {'Target.createBrowserContext': {'browserContextId': 'ctx1'}, 'Target.createTarget': {'targetId': 'th1'}, 'Runtime.evaluate': {'result': {'value': dom_val}}, 'Target.closeTarget': {'success': True}, 'Target.disposeBrowserContext': {}}
	mux = MagicMock()
	mux.__enter__.return_value = mux
	mux.__exit__.return_value = False
	mux.attach_target.side_effect = lambda _t, **_k: 'ps1'
	mux.detach_target.side_effect = lambda _s: None
	mux.send.side_effect = lambda method, _params, **_k: table.get(method, {})
	return mux
class DfHarnessS11Wave2CCovBrowserTests(unittest.TestCase):
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_anchor_status_preflight_ext_sentinel_and_lib_helpers(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			ver = {'Browser': 'Chrome/130', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/browser/b1'}
			targets = [{'id': 't1', 'type': 'page', 'url': 'https://example.com/a', 'title': 'A', 'browserContextId': 'ctx1', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/t1'}]
			t_infos = [
				{'targetId': 't1', 'type': 'page', 'url': 'https://example.com/a', 'browserContextId': 'ctx1'},
				{'targetId': 'anc1', 'type': 'background_page', 'url': 'chrome-extension://ext123/offscreen.html', 'browserContextId': 'ctx1'},
			]
			get = lambda u: ver if u.endswith('/version') else targets
			table = {'Browser.getBrowserCommandLine': {'arguments': ['--user-data-dir=/tmp/p']}, 'Target.getTargets': {'targetInfos': t_infos}, 'Target.attachToTarget': {'sessionId': 'as1'}, 'Target.detachFromTarget': {}, 'Network.setCookie': {'success': True}, 'Storage.getUsageAndQuota': {'usage': 0}, 'Network.getCookies': {'cookies': [{'name': '__harness_primary_profile'}]}, 'Runtime.evaluate': {'result': {'value': 'me'}}}
			cdp = lambda _ws, m, _p: table.get(m, {})
			cfg_no_acc = _make_cfg(root, ext_id='ext123')
			cfg_ext = _make_cfg(root, ext_id='ext123', account={'expression': '"me"', 'expected': 'me'})
			st = AnchorStatusChecker(session_id='s1', init_sentinel_tab='t1', config=cfg_no_acc, http_get=get, cdp_call=cdp).check()
			self.assertTrue(st['valid'] and st['sentinel_initialized'])
			self.assertTrue(PreflightChecker({'session_id': 's1', 'target_id': 't1'}, config=cfg_ext, http_get=get, cdp_call=cdp).check()['valid'])
			cfg_sent = _make_cfg(root, sentinel='https://sentinel.invalid')
			self.assertTrue(PreflightChecker({'session_id': 's1', 'target_id': 't1'}, config=cfg_sent, http_get=get, cdp_call=cdp).check()['valid'])
			exe = root / 'chs.exe'
			exe.write_bytes(b'MZ')
			self.assertTrue(any(('executablePath' in a for a in dfh_headless_mcp_args({'text': {'browser': {'headless_shell': {'executable': str(exe), 'fallback_glob': str(root / '*.exe')}}}}))))
			self.assertTrue(callable(dfh_browser_seam('collect_cdp_dom', lambda: None)))
			cm = io.BytesIO(b'{"ok": true}')
			with patch('Df.Harness.lib.browser.urlopen', return_value=cm):
				self.assertEqual({'ok': True}, dfh_http_json('http://127.0.0.1:9222/json/version'))
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_cdp_dom_collector_and_cdp_session_pipe_lifecycle(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			ver = {'Browser': 'Chrome/130', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9333/devtools/browser/b1'}
			t_list = [{'id': 'tnew', 'type': 'page', 'url': 'https://example.com/p', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9333/devtools/page/tnew'}]
			seen_lists: list[int] = []
			get = lambda u: ver if u.endswith('/version') else (seen_lists.append(1) or ([] if 1 == len(seen_lists) else t_list))
			dom_val = {'readyState': 'complete', 'url': 'https://example.com/p', 'html': '<html><body>Loaded</body></html>', 'title': 'T'}
			table = {'Browser.getBrowserCommandLine': {'arguments': ['--user-data-dir=/tmp/p']}, 'Target.createTarget': {'targetId': 'tnew'}, 'Target.attachToTarget': {'sessionId': 'ps1'}, 'Runtime.evaluate': {'result': {'value': dom_val}}, 'Target.detachFromTarget': {}, 'Target.closeTarget': {'success': True}}
			cfg = _make_cfg(root)
			out = CdpDomCollector(root, 'https://example.com/p', cdp_port=9333, config=cfg, http_get=get, cdp_call=lambda _ws, m, _p: table.get(m, {})).collect()
			self.assertEqual('tnew', out['target_id'])
			fake_proc = SimpleNamespace(stdin=io.StringIO(), stdout=io.StringIO('{"ready": true}\n' + json.dumps({'req_id': 1, 'result': {'ok': True}}) + '\n'), stderr=io.StringIO(''), poll=lambda: None, terminate=lambda: None, wait=lambda timeout=None: 0)
			with patch('Df.Harness.Text.Browser.CdpSession.subprocess.Popen', return_value=fake_proc):
				with CdpSession('ws://127.0.0.1:9222/devtools/browser/b1', cfg) as mux:
					self.assertEqual({'ok': True}, mux.send('Browser.getVersion', {}))
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_guarded_cdp_create_select_call_and_tab_broker(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			ver = {'Browser': 'Chrome/130', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/browser/b1'}
			targets = [
				{'id': 't1', 'type': 'page', 'url': 'https://example.com/a', 'title': 'A', 'browserContextId': 'ctx1', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/t1'},
				{'id': 't2', 'type': 'page', 'url': 'https://example.com/new', 'title': 'N', 'browserContextId': 'ctx1', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/t2'},
			]
			t_infos = [
				{'targetId': 't1', 'type': 'page', 'url': 'https://example.com/a', 'browserContextId': 'ctx1'},
				{'targetId': 't2', 'type': 'page', 'url': 'https://example.com/new', 'browserContextId': 'ctx1'},
				{'targetId': 'anc1', 'type': 'background_page', 'url': 'chrome-extension://ext123/offscreen.html', 'browserContextId': 'ctx1'},
			]
			get = lambda u: ver if u.endswith('/version') else targets
			table = {'Browser.getBrowserCommandLine': {'arguments': ['--user-data-dir=/tmp/p']}, 'Target.getTargets': {'targetInfos': t_infos}, 'Target.createTarget': {'targetId': 't2'}, 'Page.navigate': {'frameId': 'f1'}, 'Target.closeTarget': {'success': True}}
			cdp = lambda _ws, m, _p: table.get(m, {})
			guard = GuardedCdp(root, {'session_id': 's1', 'target_id': 't1'}, config=_make_cfg(root, ext_id='ext123'), http_get=get, cdp_call=cdp)
			self.assertEqual('t2', guard.create_target('https://example.com/new', background=True, hidden=True)['target_id'])
			guard.select_owned('t2')
			self.assertEqual({'frameId': 'f1'}, guard.call('Page.navigate', {'url': 'https://example.com/new'}))
			self.assertEqual({'success': True}, guard.call('Target.closeTarget', {}))
			sess = _make_broker_sess()
			self.assertEqual(('t3', 77), TabCreator(sess, lambda _u: [], 'anc1', 'ctx1', 'https://example.com/b', 'http://127.0.0.1:9222').create())
			self.assertTrue(TabRemover(sess, 'anc1', 77, 't3').remove())
			bad_sess = SimpleNamespace(attach_target=lambda _t, **_k: 's1', detach_target=lambda _s: None, send=lambda m, _p, **_k: {'result': {'value': {'ok': True, 'tabId': 88}}} if 'Runtime.evaluate' == m else (_ for _ in ()).throw(RuntimeError('boom')))
			with self.assertRaises(RuntimeError):
				TabCreator(bad_sess, lambda _u: [], 'anc1', 'ctx1', 'https://example.com/fail', 'http://127.0.0.1:9222').create()
			fail_cdp = lambda ws, m, p: (_ for _ in ()).throw(RuntimeError('wrong win')) if 'Target.createTarget' == m else cdp(ws, m, p)
			guard2 = GuardedCdp(root, {'session_id': 's1', 'target_id': 't1'}, config=_make_cfg(root, ext_id='ext123'), http_get=get, cdp_call=fail_cdp)
			with patch('Df.Harness.Text.Browser.TabCreator.TabCreator.create', return_value=('t2', 99)):
				self.assertEqual('t2', guard2.create_target('https://example.com/new', background=True)['target_id'])
	# @used-by :mod:`unittest`
	# @used-by pytest
	def test_headless_shell_and_headless_dom_collector(self) -> None:
		with tempfile.TemporaryDirectory() as td:
			root = Path(td)
			(root / 'ꘖ/data').mkdir(parents=True)
			exe = root / 'chs.exe'
			exe.write_bytes(b'MZ')
			cfg = {'workspace_root': str(root), 'text': {'browser': {'headless_shell': {'executable': str(exe)}}}}
			# @used-by :meth:`DfHarnessS11Wave2CCovBrowserTests.test_headless_shell_and_headless_dom_collector()`
			def fake_popen(argv, **_kw):
				udd = Path([a.split('=', 1)[1] for a in argv if a.startswith('--user-data-dir=')][0])
				(udd / 'DevToolsActivePort').write_text('9555\n/devtools/browser/b1\n', encoding='utf-8')
				return SimpleNamespace(poll=lambda: None, terminate=lambda: None, wait=lambda timeout=None: 0, stderr=io.BytesIO(b''))
			ver = {'Browser': 'HeadlessChrome/130', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9555/devtools/browser/b1'}
			dom_val = {'readyState': 'complete', 'url': 'https://example.com/hl', 'html': '<html><body>HL</body></html>', 'title': 'HL'}
			with patch('Df.Harness.Text.Browser.HeadlessShell.subprocess.Popen', side_effect=fake_popen), patch('Df.Harness.Text.Browser.HeadlessShell.dfh_http_json', return_value=ver), patch('Df.Harness.Text.Browser.HeadlessDomCollector.CdpSession', return_value=_make_headless_mux(dom_val)):
				res = HeadlessDomCollector(root, 'https://example.com/hl', config=cfg).collect()
			self.assertEqual('th1', res['target_id'])
			self.assertTrue(res['closed_after_capture'])
if '__main__' == __name__:
	unittest.main()
