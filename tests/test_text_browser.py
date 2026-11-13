# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Deduplicate HTTP/CDP collection pipeline with browser fallback, extraction cache, and CDP primitives across research.py and text_browser.py":
# https://github.com/dmitry-ai/harness/issues/66
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce browser CDP DOM collection for JS/anti-bot pages, block search-snippet citation substitution, and extract universal harness.py CLI":
# https://github.com/dmitry-ai/harness/issues/27
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
		self.targets = [{'id': 'selected', 'type': 'page', 'url': 'https://example.invalid/start', 'title': 'Selected', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/selected'}]
		self.browser = 'ws://127.0.0.1:9222/devtools/browser/live'
		self.unavailable = False
	def get(self, url):
		if url.endswith('/json/version'):
			r = {'Browser': 'Fixture/1', 'webSocketDebuggerUrl': self.browser}
		elif url.endswith('/json/list'):
			r = deepcopy(self.targets)
		else:
			raise AssertionError(url)
		return r
	def call(self, url, method, params):
		self.calls.append((url, method, deepcopy(params)))
		if 'Browser.getBrowserCommandLine' == method:
			if self.unavailable:
				raise RuntimeError('Command line unavailable without automation flag')
			r = {'arguments': self.arguments}
		elif 'Target.createTarget' == method:
			self.targets.append({'id': 'owned', 'type': 'page', 'url': params['url'], 'title': 'New', 'webSocketDebuggerUrl': 'ws://127.0.0.1:9222/devtools/page/owned'})
			r = {'targetId': 'owned'}
		elif 'Target.closeTarget' == method:
			tid = params.get('targetId')
			self.targets = [t for t in self.targets if t.get('id') != tid]
			r = {'success': True}
		elif 'Page.navigate' != method:
			r = {'ok': True}
		else:
			self.targets[-1]['url'] = params['url']
			r = {'frameId': 'main'}
		return r
def dom_fixture(root, url, tab_id, html):
	native = NativeFixture()
	native.targets[0].update(id=tab_id, url=url, webSocketDebuggerUrl=f'ws://127.0.0.1:9222/devtools/page/{tab_id}')
	config = {'workspace_root': str(root), 'platforms': {}, 'text': {'browser': {'sessions': {'offline-dom': {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222', 'profile': {'path': 'C:/authorized', 'argument': '--user-data-dir'}, 'target_url_patterns': [url], 'allowed_operations': ['read']}}}}}
	def call(endpoint, method, params):
		if 'Runtime.evaluate' != method:
			r = native.call(endpoint, method, params)
		else:
			native.calls.append((endpoint, method, deepcopy(params)))
			r = {'result': {'type': 'object', 'value': {'url': url, 'html': html}}}
		return r
	guard = GuardedCDP(root, {'session_id': 'offline-dom', 'target_id': tab_id}, config=config, http_get=native.get, cdp_call=call)
	return (guard, native)
class TextBrowserTests(unittest.TestCase):
	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp.cleanup)
		self.root = Path(self.temp.name)
		self.config = {'workspace_root': str(self.root), 'platforms': {'codex': {'homes': {'C1': 'C:/authorized'}}}, 'text': {'browser': {'sessions': {'approved': {'surface': 'browser', 'endpoint': 'http://127.0.0.1:9222', 'profile': {'path': 'C:/authorized', 'argument': '--user-data-dir'}, 'target_url_patterns': ['https://example.invalid/*'], 'allowed_operations': ['read', 'screenshot', 'create', 'navigate', 'write', 'close']}}}}}
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
		self.assertFalse(any(('DOM.getDocument' == call[1] for call in self.native.calls)))
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
		for method, params in [('Page.navigate', {'url': 'https://example.invalid/new'}), ('Page.reload', {}), ('Target.closeTarget', {'targetId': 'selected'}), ('Runtime.evaluate', {'expression': 'document.body.remove()'})]:
			with self.assertRaises(PermissionError):
				guard.call(method, params)
		substantive = [method for _, method, _ in self.native.calls if 'Browser.getBrowserCommandLine' != method]
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
		self.config['text']['browser']['sessions']['approved']['profile'] = {'platform': 'codex', 'name': 'C1', 'argument': '--user-data-dir'}
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
		self.assertFalse(any(('Target.createTarget' == method for _, method, _ in self.native.calls)))
	def test_only_real_created_target_can_be_mutated_and_ownership_change_stops_close(self):
		guard = self.guard()
		receipt = guard.create_target('https://example.invalid/test')
		creation = next((call for call in self.native.calls if 'Target.createTarget' == call[1]))
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
		for method, params in [('Browser.close', {}), ('Target.createTarget', {}), ('Target.attachToTarget', {'targetId': 'other'}), ('Browser.getWindowForTarget', {'targetId': 'other'})]:
			with self.assertRaises(PermissionError):
				guard.call(method, params)
		self.assertEqual({method for _, method, _ in self.native.calls}, {'Browser.getBrowserCommandLine'})
	def test_browser_window_read_is_bound_to_the_exact_target_and_cookies_are_unsupported(self):
		self.guard().call('Browser.getWindowForTarget')
		self.assertEqual(self.native.calls[-1][2], {'targetId': 'selected'})
		with self.assertRaises(PermissionError):
			self.guard().call('Network.getCookies', {'urls': ['https://private.invalid/']})
	def test_common_user_data_directory_does_not_override_selected_profile(self):
		self.config['text']['browser']['sessions']['approved']['profile']['additional_arguments'] = {'--profile-directory': 'Default'}
		self.assertTrue(self.check()['valid'])
		self.native.arguments[-1] = '--profile-directory=Private'
		self.assertFalse(self.check()['valid'])
		self.native.arguments.pop()
		report = self.check()
		self.assertFalse(report['valid'])
		self.assertEqual(report['profile']['status'], 'unknown')
	def test_live_account_marker_is_separate_from_profile_and_caller_assertion(self):
		self.assertEqual(self.check()['account']['status'], 'unknown')
		self.config['text']['browser']['sessions']['approved']['account'] = {'expected': 'authorized@example.invalid', 'expression': 'document.querySelector("#account").textContent'}
		observed_account = 'wrong@example.invalid'
		def call(url, method, params):
			if 'Runtime.evaluate' != method:
				r = self.native.call(url, method, params)
			else:
				self.assertIs(params['throwOnSideEffect'], True)
				r = {'result': {'type': 'string', 'value': observed_account}}
			return r
		report = preflight({**self.spec, 'account': 'authorized@example.invalid'}, config=self.config, http_get=self.native.get, cdp_call=call)
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
		self.assertFalse(any(('Runtime.evaluate' == method for _, method, _ in native.calls)))
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
		self.assertTrue(next((params for _, method, params in native.calls if 'Runtime.evaluate' == method))['throwOnSideEffect'])
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
		self.assertFalse(any(('Runtime.evaluate' == method for _, method, _ in native.calls)))
	def test_dom_collector_does_not_issue_content_proof_if_browser_identity_changes(self):
		from agent_tools.research import capture_dom, observation_capabilities
		guard, native = dom_fixture(self.root, 'https://example.invalid/a', 'tab-A', '<p>Fixture DOM</p>')
		versions = []
		def get(url):
			if url.endswith('/json/version'):
				versions.append(url)
				if 2 == len(versions):
					native.browser = 'ws://127.0.0.1:9222/devtools/browser/restarted'
			r = native.get(url)
			return r
		guard.get = get
		result = capture_dom(self.root, 'https://example.invalid/a', 'tab-A', session_id='offline-dom', guard=guard)
		self.assertEqual(result['error'], 'ValueError')
		self.assertEqual(observation_capabilities(result), set())
	def test_session_lock_serializes_preflight_with_its_action(self):
		first, second = (self.guard(), self.guard())
		active, maximum = (0, 0)
		mutex = threading.Lock()
		def delayed(url, method, params):
			nonlocal active, maximum
			with mutex:
				active += 1
				maximum = max(maximum, active)
			time.sleep(0.015)
			result = self.native.call(url, method, params)
			with mutex:
				active -= 1
			r = result
			return r
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
		self.assertEqual([method for _, method, _ in self.native.calls], ['Browser.getBrowserCommandLine', 'DOM.getDocument'] * 2)
	def test_collect_browser_reuses_open_user_tab_or_opens_and_closes_background_tab(self):
		from agent_tools.research import collect_browser
		native = NativeFixture()
		reddit_url = 'https://www.reddit.com/r/GoogleGeminiAI/comments/1abc/post/'
		rendered_html = '<html><head><title>Google Antigravity Thread</title></head><body><h1>Google Antigravity Thread</h1><div id="t1_nvz0p8c"><p>I hit a brick wall with Google Antigravity in production.</p></div></body></html>'
		def call(endpoint, method, params):
			if 'Runtime.evaluate' != method:
				return native.call(endpoint, method, params)
			native.calls.append((endpoint, method, deepcopy(params)))
			return {'result': {'type': 'object', 'value': {'readyState': 'complete', 'url': reddit_url, 'title': 'Google Antigravity Thread', 'html': rendered_html, 'textLen': 65}}}
		obs_bg = collect_browser(self.root, reddit_url, cdp_port=9222, http_get=native.get, cdp_call=call)
		self.assertEqual(obs_bg['kind'], 'dom')
		self.assertEqual(obs_bg['collector'], 'read-only-dom')
		self.assertFalse(obs_bg.get('browser_check_required'))
		self.assertGreater(obs_bg.get('word_count', 0), 0)
		create_calls = [params for _, method, params in native.calls if 'Target.createTarget' == method]
		close_calls = [params for _, method, params in native.calls if 'Target.closeTarget' == method]
		self.assertEqual(len(create_calls), 1)
		self.assertTrue(create_calls[0].get('background'))
		self.assertFalse(create_calls[0].get('newWindow', False))
		self.assertEqual(close_calls, [{'targetId': 'owned'}])
		native.calls.clear()
		native.targets[0]['url'] = reddit_url
		obs_user = collect_browser(self.root, reddit_url, cdp_port=9222, http_get=native.get, cdp_call=call, refresh_reason='verify user tab reuse')
		self.assertEqual(obs_user['kind'], 'dom')
		self.assertFalse(any(('Target.createTarget' == m for _, m, _ in native.calls)))
		self.assertFalse(any(('Target.closeTarget' == m for _, m, _ in native.calls)))
	def test_collect_http_auto_fallback_to_browser_on_reddit_js_challenge_shell(self):
		from agent_tools.research import Response, collect_http
		native = NativeFixture()
		reddit_url = 'https://www.reddit.com/r/GoogleGeminiAI/comments/1abc/post/'
		js_shell = ('<!DOCTYPE html><html><head><title>Reddit</title><style>' + ('body{}' * 1400) + '</style></head><body><form><input type="hidden" name="js_challenge" value="1"/></form></body></html>').encode('utf-8')
		self.assertGreater(len(js_shell), 8000)
		rendered_html = '<html><head><title>Google Antigravity Thread</title></head><body><h1>Google Antigravity Thread</h1><div id="t1_nvz0p8c"><p>Verified DOM body from user browser session.</p></div></body></html>'
		def call(endpoint, method, params):
			if 'Runtime.evaluate' != method:
				return native.call(endpoint, method, params)
			native.calls.append((endpoint, method, deepcopy(params)))
			return {'result': {'type': 'object', 'value': {'readyState': 'complete', 'url': reddit_url, 'title': 'Google Antigravity Thread', 'html': rendered_html, 'textLen': 48}}}
		obs_never = collect_http(self.root, reddit_url, fetcher=lambda u, h, t: Response(u, 200, 'text/html', js_shell), browser='never')
		self.assertTrue(obs_never.get('browser_check_required'))
		self.assertEqual(obs_never.get('word_count'), 0)
		obs_auto = collect_http(self.root, reddit_url, fetcher=lambda u, h, t: Response(u, 200, 'text/html', js_shell), browser='auto', cdp_port=9222, http_get=native.get, cdp_call=call, refresh_reason='auto browser fallback')
		self.assertEqual(obs_auto['kind'], 'dom')
		self.assertTrue(obs_auto.get('browser_fallback_from_http'))
		self.assertFalse(obs_auto.get('browser_check_required'))
		self.assertGreater(obs_auto.get('word_count', 0), 0)
	def test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives(self):
		from agent_tools.research import Response, collect_plan, extract_file
		from agent_tools.text_browser import discover_cdp_browser, probe_cdp_arguments, save_cdp_identity
		native = NativeFixture()
		version, targets, browser_ws = discover_cdp_browser('http://127.0.0.1:9222', native.get)
		self.assertEqual('Fixture/1', version['Browser'])
		self.assertEqual(1, len(targets))
		self.assertEqual(native.browser, browser_ws)
		self.assertEqual(native.arguments, probe_cdp_arguments(browser_ws, native.call))
		ref_one, sha_one = save_cdp_identity(self.root, {'schema_version': 1, 'endpoint': 'http://127.0.0.1:9222'})
		ref_two, sha_two = save_cdp_identity(self.root, {'schema_version': 1, 'endpoint': 'http://127.0.0.1:9222'})
		self.assertEqual((ref_one, sha_one), (ref_two, sha_two))
		sample = self.root / 'sample.txt'
		sample.write_text('cached extraction body', encoding='utf-8')
		ext_first = extract_file(self.root, 'sample.txt', profile='document')
		ext_second = extract_file(self.root, 'sample.txt', profile='document')
		self.assertEqual(ext_first, ext_second)
		json_url = 'https://example.invalid/feed.json'
		challenge_url = 'https://example.invalid/protected'
		js_shell = b'<html><body><form><input name="js_challenge" value="1"/></form></body></html>'
		rendered_html = '<html><head><title>Protected</title></head><body><h1>Protected Content</h1><p>Body text.</p></body></html>'
		def fetcher(url, headers, timeout):
			if json_url == url:
				r = Response(url, 200, 'application/json', b'{"items":[{"id":"1","title":"Alpha"}]}')
			else:
				r = Response(url, 403, 'text/html', js_shell)
			return r
		def call(endpoint, method, params):
			if 'Runtime.evaluate' != method:
				r = native.call(endpoint, method, params)
			else:
				native.calls.append((endpoint, method, deepcopy(params)))
				r = {'result': {'type': 'object', 'value': {'readyState': 'complete', 'url': challenge_url, 'title': 'Protected', 'html': rendered_html, 'textLen': 25}}}
			return r
		plan = {'requests': [{'url': json_url, 'profile': 'html'}, {'url': challenge_url, 'profile': 'html'}]}
		batch = collect_plan(self.root, plan, fetcher=fetcher, browser='auto', cdp_port=9222, http_get=native.get, cdp_call=call)
		self.assertTrue(batch['complete'])
		self.assertTrue(batch['content_available_for_all'])
		self.assertEqual('document', batch['results'][0]['profile'])
		self.assertEqual('dom', batch['results'][1]['kind'])
		self.assertTrue(batch['results'][1]['browser_fallback_from_http'])
if '__main__' == __name__:
	unittest.main()
