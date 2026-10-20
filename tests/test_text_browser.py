"""Offline CDP regressions. Tests never connect to or launch a real application."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from agent_tools.text_browser import GuardedCDP, operation, preflight


class NativeFixture:
    def __init__(self):
        self.calls = []
        self.arguments = ['browser', '--user-data-dir=C:/authorized', '--profile-directory=Default']
        self.targets = [{'id': 'selected', 'type': 'page', 'url': 'https://example.invalid/start',
                         'title': 'Selected', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/selected'}]
        self.browser = 'ws://127.0.0.1:9222/devtools/browser/live'
        self.unavailable = False

    def get(self, url):
        if url.endswith('/json/version'):
            return {'Browser': 'Fixture/1', 'webSocketDebuggerUrl': self.browser}
        if url.endswith('/json/list'):
            return deepcopy(self.targets)
        raise AssertionError(url)

    def call(self, url, method, params):
        self.calls.append((url, method, deepcopy(params)))
        if method == 'Browser.getBrowserCommandLine':
            if self.unavailable:
                raise RuntimeError('Command line unavailable without automation flag')
            return {'arguments': self.arguments}
        if method == 'Target.createTarget':
            self.targets.append({'id': 'owned', 'type': 'page', 'url': params['url'], 'title': 'New',
                'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/owned'})
            return {'targetId': 'owned'}
        if method == 'Page.navigate':
            self.targets[-1]['url'] = params['url']
            return {'frameId': 'main'}
        return {'ok': True}


def dom_fixture(root, url, tab_id, html):
    """A controlled offline endpoint for collector tests, never a real profile."""
    native = NativeFixture()
    native.targets[0].update(id=tab_id, url=url,
        webSocketDebuggerUrl=f'ws://127.0.0.1:9222/devtools/page/{tab_id}')
    config = {'workspace_root': str(root), 'platforms': {}, 'text': {'browser': {'sessions': {
        'offline-dom': {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222',
            'profile': {'path': 'C:/authorized', 'argument': '--user-data-dir'},
            'target_url_patterns': [url], 'allowed_operations': ['read']}}}}}
    def call(endpoint, method, params):
        if method == 'Runtime.evaluate':
            native.calls.append((endpoint, method, deepcopy(params)))
            return {'result': {'type': 'object', 'value': {'url': url, 'html': html}}}
        return native.call(endpoint, method, params)
    guard = GuardedCDP(root, {'session_id': 'offline-dom', 'target_id': tab_id},
                       config=config, http_get=native.get, cdp_call=call)
    return guard, native


class TextBrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {'workspace_root': str(self.root), 'platforms': {'codex': {'homes': {'C1': 'C:/authorized'}}},
            'text': {'browser': {'sessions': {'approved': {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222',
                'profile': {'path': 'C:/authorized', 'argument': '--user-data-dir'},
                'target_url_patterns': ['https://example.invalid/*'],
                'allowed_operations': ['read', 'screenshot', 'create', 'navigate', 'write', 'close']}}}}}
        self.spec = {'session_id': 'approved', 'target_id': 'selected'}
        self.native = NativeFixture()

    def check(self, spec=None):
        return preflight(spec or self.spec, config=self.config, http_get=self.native.get, cdp_call=self.native.call)

    def guard(self):
        return GuardedCDP(self.root, self.spec, config=self.config, http_get=self.native.get, cdp_call=self.native.call)

    def test_port_and_caller_profile_do_not_prove_identity(self):
        self.native.unavailable = True
        spec = {**self.spec, 'profile': {'status': 'verified', 'path': 'C:/authorized'}, 'owner': 'agent'}
        report = self.check(spec)
        self.assertFalse(report['valid'])
        self.assertEqual(report['profile']['status'], 'unknown')
        self.assertTrue(report['independent_http_allowed'])
        with self.assertRaises(PermissionError):
            self.guard().call('DOM.getDocument')
        self.assertFalse(any(call[1] == 'DOM.getDocument' for call in self.native.calls))

    def test_actual_profile_mismatch_rejected_before_content_read(self):
        self.native.arguments = ['browser', '--user-data-dir=C:/private']
        self.assertEqual(self.check()['profile']['status'], 'mismatch')
        with self.assertRaises(PermissionError):
            self.guard().call('Page.captureScreenshot')
        self.assertEqual({call[1] for call in self.native.calls}, {'Browser.getBrowserCommandLine'})

    def test_explicit_current_page_and_url_are_required(self):
        self.assertFalse(self.check({'session_id': 'approved'})['valid'])
        self.native.targets[0]['type'] = 'iframe'
        self.assertFalse(self.check()['valid'])
        self.native.targets[0]['type'] = 'page'
        self.native.targets[0]['url'] = 'https://signin.invalid/'
        self.assertFalse(self.check()['valid'])
        self.assertEqual(len(self.native.calls), 3)

    def test_user_target_read_and_screenshot_work_but_mutation_does_not(self):
        guard = self.guard()
        self.assertEqual(guard.call('DOM.getDocument'), {'ok': True})
        self.assertEqual(guard.call('Page.captureScreenshot'), {'ok': True})
        for method, params in [('Page.navigate', {'url': 'https://example.invalid/new'}),
                               ('Page.reload', {}), ('Target.closeTarget', {'targetId': 'selected'}),
                               ('Runtime.evaluate', {'expression': 'document.body.remove()'})]:
            with self.assertRaises(PermissionError):
                guard.call(method, params)
        substantive = [method for _, method, _ in self.native.calls if method != 'Browser.getBrowserCommandLine']
        self.assertEqual(substantive, ['DOM.getDocument', 'Page.captureScreenshot'])

    def test_javascript_read_requires_v8_side_effect_guard(self):
        guard = self.guard()
        guard.call('Runtime.evaluate', {'expression': 'document.title', 'throwOnSideEffect': True})
        self.assertEqual(operation('Runtime.evaluate', {'expression': 'document.title'}), 'write')
        with self.assertRaises(PermissionError):
            guard.call('Runtime.evaluate', {'expression': 'document.title'})
        with self.assertRaises(PermissionError):
            guard.call('Runtime.evaluate', {'throwOnSideEffect': True, 'sessionId': 'other'})

    def test_preflight_is_repeated_and_cannot_use_stale_target(self):
        guard = self.guard()
        guard.call('DOM.getDocument')
        self.native.targets[0]['url'] = 'https://other.invalid/'
        with self.assertRaises(PermissionError):
            guard.call('DOM.getDocument')
        self.assertEqual([method for _, method, _ in self.native.calls].count('DOM.getDocument'), 1)

    def test_runtime_profile_reference_uses_single_home_configuration(self):
        self.config['text']['browser']['sessions']['approved']['profile'] = {
            'platform': 'codex', 'name': 'C1', 'argument': '--user-data-dir'}
        self.assertTrue(self.check()['valid'])

    def test_dynamic_antigravity_port_read_each_time_without_launch(self):
        active = self.root / 'DevToolsActivePort'
        active.write_text('9222\n/devtools/browser/live\n', encoding='utf-8')
        session = self.config['text']['browser']['sessions']['approved']
        session.pop('endpoint')
        session.update(surface='antigravity', devtools_active_port=str(active))
        self.assertTrue(self.check()['valid'])
        active.write_text('9333\n/devtools/browser/new\n', encoding='utf-8')
        self.native.browser = self.native.browser.replace('9222', '9333')
        self.native.targets[0]['webSocketDebuggerUrl'] = self.native.targets[0]['webSocketDebuggerUrl'].replace('9222', '9333')
        self.assertEqual(self.check()['endpoint'], 'http://127.0.0.1:9333')
        with self.assertRaises(PermissionError):
            self.guard().create_target('https://example.invalid/test')
        self.assertFalse(any(method == 'Target.createTarget' for _, method, _ in self.native.calls))

    def test_only_real_created_target_can_be_mutated_and_ownership_change_stops_close(self):
        guard = self.guard()
        receipt = guard.create_target('https://example.invalid/test')
        creation = next(call for call in self.native.calls if call[1] == 'Target.createTarget')
        self.assertTrue(creation[2]['newWindow'])
        guard.select_owned(receipt['target_id'])
        guard.call('Page.navigate', {'url': 'https://example.invalid/next'})
        guard.call('Runtime.evaluate', {'expression': 'window.test = 1'})
        self.native.targets[-1]['url'] = 'https://example.invalid/user-work'
        with self.assertRaises(PermissionError):
            guard.call('Target.closeTarget')
        with self.assertRaises(PermissionError):
            self.guard().select_owned(receipt['target_id'])

    def test_target_routing_and_application_shutdown_are_denied(self):
        guard = self.guard()
        for method, params in [('Browser.close', {}), ('Target.createTarget', {}),
                               ('Target.attachToTarget', {'targetId': 'other'}),
                               ('Browser.getWindowForTarget', {'targetId': 'other'})]:
            with self.assertRaises(PermissionError):
                guard.call(method, params)
        self.assertEqual({method for _, method, _ in self.native.calls}, {'Browser.getBrowserCommandLine'})

    def test_browser_window_read_is_bound_to_the_exact_target_and_cookies_are_unsupported(self):
        self.guard().call('Browser.getWindowForTarget')
        self.assertEqual(self.native.calls[-1][2], {'targetId': 'selected'})
        with self.assertRaises(PermissionError):
            self.guard().call('Network.getCookies', {'urls': ['https://private.invalid/']})

    def test_common_user_data_directory_does_not_override_selected_profile(self):
        self.config['text']['browser']['sessions']['approved']['profile']['additional_arguments'] = {
            '--profile-directory': 'Default'}
        self.assertTrue(self.check()['valid'])
        self.native.arguments[-1] = '--profile-directory=Private'
        self.assertFalse(self.check()['valid'])
        self.native.arguments.pop()
        report = self.check()
        self.assertFalse(report['valid'])
        self.assertEqual(report['profile']['status'], 'unknown')

    def test_live_account_marker_is_separate_from_profile_and_caller_assertion(self):
        self.assertEqual(self.check()['account']['status'], 'unknown')
        self.config['text']['browser']['sessions']['approved']['account'] = {
            'expected': 'authorized@example.invalid', 'expression': 'document.querySelector("#account").textContent'}
        observed_account = 'wrong@example.invalid'
        def call(url, method, params):
            if method == 'Runtime.evaluate':
                self.assertIs(params['throwOnSideEffect'], True)
                return {'result': {'type': 'string', 'value': observed_account}}
            return self.native.call(url, method, params)
        report = preflight({**self.spec, 'account': 'authorized@example.invalid'}, config=self.config,
                           http_get=self.native.get, cdp_call=call)
        self.assertFalse(report['valid'])
        self.assertEqual(report['account']['status'], 'mismatch')
        observed_account = 'authorized@example.invalid'
        report = preflight(self.spec, config=self.config, http_get=self.native.get, cdp_call=call)
        self.assertTrue(report['valid'])
        self.assertEqual(report['account']['status'], 'verified')

    def test_dom_collector_requires_verified_profile_before_native_dom_evaluation(self):
        from agent_tools.research import capture_dom
        guard, native = dom_fixture(self.root, 'https://example.invalid/a', 'tab-A', '<p>Fixture DOM</p>')
        native.unavailable = True
        with self.assertRaises(PermissionError):
            capture_dom(self.root, 'https://example.invalid/a', 'tab-A', session_id='offline-dom', guard=guard)
        self.assertFalse(any(method == 'Runtime.evaluate' for _, method, _ in native.calls))
        with self.assertRaises(ValueError):
            capture_dom(self.root, 'https://example.invalid/a', 'tab-A')
        native.unavailable = False
        result = capture_dom(self.root, 'https://example.invalid/a', 'tab-A', session_id='offline-dom', guard=guard)
        self.assertEqual(result['kind'], 'dom')
        self.assertIsNone(result['status'])
        self.assertFalse(result['http_status_verified'])
        saved = json.loads((self.root / 'ꘖ/KB' / result['cdp_identity']).read_text(encoding='utf-8'))
        self.assertEqual(saved['profile']['status'], 'verified')
        self.assertEqual(saved['account']['status'], 'unknown')
        self.assertTrue(next(params for _, method, params in native.calls
                             if method == 'Runtime.evaluate')['throwOnSideEffect'])

    def test_dom_collector_exact_url_and_guard_project_cannot_be_substituted(self):
        from agent_tools.research import capture_dom
        guard, native = dom_fixture(self.root, 'https://example.invalid/a', 'tab-A', '<p>Fixture DOM</p>')
        with self.assertRaises(ValueError):
            capture_dom(self.root, 'https://example.invalid/other', 'tab-A', session_id='offline-dom', guard=guard)
        with self.assertRaises(ValueError):
            capture_dom(self.root, 'https://example.invalid/a', 'foreign', session_id='offline-dom', guard=guard)
        other = self.root / 'other'
        other.mkdir()
        with self.assertRaises(ValueError):
            capture_dom(other, 'https://example.invalid/a', 'tab-A', session_id='offline-dom', guard=guard)
        self.assertFalse(any(method == 'Runtime.evaluate' for _, method, _ in native.calls))

    def test_dom_collector_does_not_issue_content_proof_if_browser_identity_changes(self):
        from agent_tools.research import capture_dom, observation_capabilities
        guard, native = dom_fixture(self.root, 'https://example.invalid/a', 'tab-A', '<p>Fixture DOM</p>')
        versions = []
        def get(url):
            if url.endswith('/json/version'):
                versions.append(url)
                if len(versions) == 2:
                    native.browser = 'ws://127.0.0.1:9222/devtools/browser/restarted'
            return native.get(url)
        guard.get = get
        result = capture_dom(self.root, 'https://example.invalid/a', 'tab-A', session_id='offline-dom', guard=guard)
        self.assertEqual(result['error'], 'ValueError')
        self.assertEqual(observation_capabilities(result), set())

    def test_session_lock_serializes_preflight_with_its_action(self):
        first, second = self.guard(), self.guard()
        active, maximum = 0, 0
        mutex = threading.Lock()
        def delayed(url, method, params):
            nonlocal active, maximum
            with mutex:
                active += 1
                maximum = max(maximum, active)
            time.sleep(.015)
            result = self.native.call(url, method, params)
            with mutex:
                active -= 1
            return result
        first.call_native = second.call_native = delayed
        errors = []
        def run(guard):
            try:
                guard.call('DOM.getDocument')
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=run, args=(guard,)) for guard in (first, second)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=3)
        self.assertFalse(errors)
        self.assertEqual(maximum, 1)
        self.assertEqual([method for _, method, _ in self.native.calls],
                         ['Browser.getBrowserCommandLine', 'DOM.getDocument'] * 2)


if __name__ == '__main__':
    unittest.main()
