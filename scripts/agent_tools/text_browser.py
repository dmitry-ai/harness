# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import re
import subprocess
import threading
import time
from urllib.parse import urldefrag, urlsplit
from urllib.request import urlopen
from .runtime import HARNESS_META, platform_settings, settings
from .storage import locked, write_immutable_bytes
_LOCKS, _LOCKS_GUARD = ({}, threading.Lock())
_READ = frozenset({'DOM.getDocument', 'DOM.getOuterHTML', 'DOM.describeNode', 'DOM.querySelector', 'DOM.querySelectorAll', 'DOM.getAttributes', 'DOM.getBoxModel', 'Page.getFrameTree', 'Page.getLayoutMetrics', 'Page.getResourceTree', 'Page.getNavigationHistory', 'Network.getResponseBody', 'Runtime.getProperties', 'Accessibility.getFullAXTree', 'Accessibility.getPartialAXTree', 'Browser.getWindowForTarget'})
_NAVIGATE = frozenset({'Page.navigate', 'Page.reload', 'Page.navigateToHistoryEntry'})
_CLOSE = frozenset({'Target.closeTarget', 'Page.close'})
_NEVER = frozenset({'Browser.close', 'Target.createTarget', 'Target.disposeBrowserContext', 'Target.createBrowserContext', 'Target.attachToTarget', 'Target.sendMessageToTarget', 'Browser.crash', 'Page.crash'})
_LOCAL_HOSTS = {'127.0.0.1', 'localhost', '::1'}
_NODE_CLIENT = "\nlet input='';for await(const chunk of process.stdin) input+=chunk;\nconst {url,method,params}=JSON.parse(input);\nconst result=await new Promise((resolve,reject)=>{\n const socket=new WebSocket(url);const timer=setTimeout(()=>{socket.close();reject(new Error('CDP timeout'));},12000);\n socket.onopen=()=>socket.send(JSON.stringify({id:1,method,params}));\n socket.onerror=()=>{clearTimeout(timer);reject(new Error('CDP connection failed'));};\n socket.onmessage=event=>{const message=JSON.parse(event.data);if(message.id!==1)return;\n  clearTimeout(timer);socket.close();if(message.error)reject(new Error(JSON.stringify(message.error)));else resolve(message.result);};\n socket.onclose=()=>{clearTimeout(timer);reject(new Error('CDP socket closed before its response'));};\n});process.stdout.write(JSON.stringify(result));\n"
def _http_json(url):
	with urlopen(url, timeout=8) as response:
		r = json.load(response)
	return r
def _normal_path(value):
	return str(value).strip('"\'').replace('\\', '/').rstrip('/').casefold()
def _endpoint(session):
	endpoint = session.get('endpoint')
	if session.get('devtools_active_port'):
		if endpoint:
			raise ValueError('Choose endpoint or devtools_active_port, not both')
		first = Path(session['devtools_active_port']).expanduser().read_text(encoding='utf-8-sig').splitlines()[0]
		port = int(first)
		if not 0 < port < 65536:
			raise ValueError('Invalid DevToolsActivePort')
		endpoint = f"http://{session.get('host', '127.0.0.1')}:{port}"
	parsed = urlsplit(endpoint or '')
	if parsed.scheme not in ('http', 'https') or parsed.hostname not in _LOCAL_HOSTS or parsed.username or parsed.password or parsed.query or parsed.fragment or (parsed.path not in ('', '/')):
		raise ValueError('A configured loopback CDP endpoint is required')
	r = endpoint.rstrip('/')
	return r
def _checked_ws(value, endpoint):
	actual, expected = (urlsplit(value or ''), urlsplit(endpoint))
	if actual.scheme not in ('ws', 'wss') or actual.hostname != expected.hostname or actual.port != expected.port or actual.username or actual.password or actual.query or actual.fragment:
		raise ValueError('Discovered CDP websocket does not belong to the configured endpoint')
	r = value
	return r
def _session(spec, config):
	identifier = spec.get('session_id')
	sessions = config.get('text', {}).get('browser', {}).get('sessions', {})
	if not isinstance(identifier, str) or identifier not in sessions:
		raise ValueError('Select an explicitly authorized runtime text.browser.sessions session_id')
	value = deepcopy(sessions[identifier])
	if value.get('surface') not in ('browser', 'codex', 'antigravity'):
		raise ValueError('Session surface must distinguish browser, codex or antigravity')
	r = value
	return r
def _profile(session, config):
	value = session.get('profile', {})
	if value.get('path') and (value.get('platform') or value.get('name')):
		raise ValueError('Use one profile path or one runtime profile reference')
	path = value.get('path')
	if not path and value.get('platform') and value.get('name'):
		path = config.get('platforms', {}).get(value['platform'], {}).get('homes', {}).get(value['name'])
	argument = value.get('argument')
	if not isinstance(path, str) or not path.strip() or (not isinstance(argument, str)) or (not argument.startswith('--')):
		raise ValueError('Session needs a profile path/reference and its observable command-line argument')
	r = (path, argument)
	return r
def _argument_values(arguments, flag):
	values = []
	for index, argument in enumerate(arguments):
		if not isinstance(argument, str):
			raise ValueError('Native browser command line contains a non-string argument')
		if argument.startswith(flag + '='):
			values.append(argument[len(flag) + 1:])
		elif argument == flag and index + 1 < len(arguments):
			values.append(arguments[index + 1])
	r = values
	return r
def _transport(config, override):
	if None is not override:
		return override
	node = config.get('text', {}).get('browser', {}).get('node') or config.get('platforms', {}).get('codex', {}).get('node')
	def call(url, method, params):
		if not node:
			raise ValueError('Configure a Node runtime for the built-in CDP transport')
		result = subprocess.run([node, '--input-type=module', '-e', _NODE_CLIENT], input=json.dumps({'url': url, 'method': method, 'params': params}), capture_output=True, text=True, timeout=16, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
		if result.returncode:
			raise RuntimeError('CDP request failed: ' + (result.stderr.strip() or 'no native response'))
		r = json.loads(result.stdout)
		return r
	return call
def preflight(spec, *, config=None, http_get=None, cdp_call=None):
	config = settings() if None is config else config
	report = {'schema_version': 1, 'session_id': spec.get('session_id'), 'valid': False, 'profile': {'status': 'unknown'}, 'target': {'status': 'unknown'}, 'account': {'status': 'unknown'}, 'issues': [], 'independent_http_allowed': True, 'limitation': 'Cooperative check of the configured live CDP endpoint; it does not prove server internals, model reading, or ownership of external calls'}
	try:
		session = _session(spec, config)
		report['surface'] = session['surface']
		endpoint = _endpoint(session)
		report['endpoint'] = endpoint
		get, call = (http_get or _http_json, _transport(config, cdp_call))
		version, targets = (get(endpoint + '/json/version'), get(endpoint + '/json/list'))
		if not isinstance(version, dict) or not isinstance(targets, list):
			raise ValueError('Invalid CDP discovery response')
		browser_ws = _checked_ws(version.get('webSocketDebuggerUrl'), endpoint)
		if not urlsplit(browser_ws).path.startswith('/devtools/browser/'):
			raise ValueError('Discovery did not expose a browser endpoint')
		report['browser'] = {'product': version.get('Browser'), 'websocket_url': browser_ws}
		report['inventory'] = [{key: item.get(key) for key in ('id', 'type', 'url', 'title')} for item in targets if isinstance(item, dict)]
		expected, argument = _profile(session, config)
		report['profile'].update(expected=expected, argument=argument)
		try:
			observed = call(browser_ws, 'Browser.getBrowserCommandLine', {})
			arguments = observed.get('arguments') if isinstance(observed, dict) else None
			if not isinstance(arguments, list):
				raise ValueError('Native browser command-line arguments are unavailable')
			values = _argument_values(arguments, argument)
			if not values:
				report['issues'].append('Expected profile argument is absent from the native browser command line')
			elif 1 != len({_normal_path(value) for value in values}):
				report['profile']['status'] = 'mismatch'
				report['issues'].append('Native browser command line has conflicting profile arguments')
			else:
				report['profile'].update(observed=values[0], evidence_method='Browser.getBrowserCommandLine', status='verified' if _normal_path(values[0]) == _normal_path(expected) else 'mismatch')
				if 'mismatch' == report['profile']['status']:
					report['issues'].append('Observed profile does not match the authorized profile')
			constraints = session.get('profile', {}).get('additional_arguments', {})
			if not isinstance(constraints, dict):
				raise ValueError('Profile additional_arguments must map observed flags to expected values')
			details = []
			for flag, expected_value in constraints.items():
				if not isinstance(flag, str) or not flag.startswith('--') or (not isinstance(expected_value, str)):
					raise ValueError('Profile additional_arguments needs string flags and values')
				actual_values = _argument_values(arguments, flag)
				status = 'unknown' if not actual_values else 'verified' if actual_values == [expected_value] else 'mismatch'
				details.append({'argument': flag, 'expected': expected_value, 'observed': actual_values, 'status': status})
				if 'verified' != status:
					report['profile']['status'] = status
					report['issues'].append(f'Additional profile argument {flag} is {status}')
			if details:
				report['profile']['additional_arguments'] = details
		except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
			report['issues'].append('Profile cannot be verified: ' + str(exc))
		identifier = spec.get('target_id')
		matches = [item for item in targets if isinstance(item, dict) and item.get('id') == identifier]
		if not isinstance(identifier, str) or not identifier or 1 != len(matches):
			report['issues'].append('Select one explicit current target_id; no arbitrary target is chosen')
		else:
			target = matches[0]
			patterns = session.get('target_url_patterns', [])
			report['target'] = {key: target.get(key) for key in ('id', 'type', 'url', 'title')}
			report['target']['status'] = 'mismatch'
			if 'page' != target.get('type'):
				report['issues'].append('Selected target is not a shell/browser page')
			elif not patterns or not all((isinstance(pattern, str) and pattern for pattern in patterns)):
				report['issues'].append('Session needs explicit target_url_patterns')
			elif not any((fnmatchcase(target.get('url', ''), pattern) for pattern in patterns)):
				report['issues'].append('Current target URL is outside the authorized session patterns')
			elif None is not spec.get('target_url') and target.get('url') != spec['target_url']:
				report['issues'].append('Current target URL differs from the explicitly selected URL')
			else:
				target_ws = _checked_ws(target.get('webSocketDebuggerUrl'), endpoint)
				if not urlsplit(target_ws).path.startswith('/devtools/page/'):
					raise ValueError('Selected target has no page websocket')
				report['target'].update(status='verified', websocket_url=target_ws)
		account = session.get('account')
		if None is not account:
			if not isinstance(account, dict) or not isinstance(account.get('expected'), str) or (not account['expected']) or (not isinstance(account.get('expression'), str)) or (not account['expression']):
				raise ValueError('Configured account needs expected identity and a specific read-only observation expression')
			report['account']['expected'] = account['expected']
			if 'verified' == report['profile']['status'] and 'verified' == report['target']['status']:
				try:
					native = call(report['target']['websocket_url'], 'Runtime.evaluate', {'expression': account['expression'], 'throwOnSideEffect': True, 'returnByValue': True})
					if not isinstance(native, dict) or native.get('exceptionDetails'):
						raise ValueError('Native account observation did not complete without side effects')
					value = native.get('result', {}).get('value')
					report['account'].update(observed=value, status='unknown' if not isinstance(value, str) or not value else 'verified' if value == account['expected'] else 'mismatch', evidence_method='Runtime.evaluate(throwOnSideEffect:true)', limitation='This establishes only the configured application account marker, not server authorization internals')
				except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
					report['issues'].append('Account cannot be verified: ' + str(exc))
			if 'verified' != report['account']['status']:
				report['issues'].append('Observed account is unknown or differs from the authorized account')
		report['valid'] = 'verified' == report['profile']['status'] and 'verified' == report['target']['status'] and (not report['issues'])
	except (ValueError, OSError, RuntimeError, TypeError, KeyError, IndexError) as exc:
		report['issues'].append(str(exc))
	r = report
	return r
def operation(method, params=None):
	params = params or {}
	if method in _NEVER:
		r = 'forbidden'
	elif method in _READ:
		r = 'read'
	elif 'Page.captureScreenshot' == method:
		r = 'screenshot'
	elif method in _NAVIGATE:
		r = 'navigate'
	elif method in _CLOSE:
		r = 'close'
	elif method in ('Runtime.evaluate', 'Runtime.callFunctionOn'):
		r = 'read' if True is params.get('throwOnSideEffect') else 'write'
	elif method.startswith(('Input.', 'DOM.set', 'DOM.remove', 'Runtime.')):
		r = 'write'
	else:
		r = 'forbidden'
	return r
class GuardedCDP:
	def __init__(self, root, spec, *, config=None, http_get=None, cdp_call=None):
		if None is root or not str(root).strip():
			raise ValueError('An explicit project root is required')
		self.root = Path(root).resolve()
		if not self.root.is_dir():
			raise ValueError('Project root is not a directory')
		self.config = settings() if None is config else deepcopy(config)
		self.spec = deepcopy(spec)
		self.session = _session(spec, self.config)
		self.get = http_get or _http_json
		self.call_native = _transport(self.config, cdp_call)
		self._owned = {}
	@contextmanager
	def _lock(self):
		endpoint = _endpoint(self.session)
		key = hashlib.sha256(endpoint.encode()).hexdigest()
		with _LOCKS_GUARD:
			lock = _LOCKS.setdefault(key, threading.Lock())
		cfg_ws = Path(self.config['workspace_root']).resolve()
		default_ws = Path(settings()['workspace_root']).resolve()
		lock_dir = HARNESS_META / 'ꘖ/data/browser-locks' if cfg_ws == default_ws else cfg_ws / 'ꘖ/data/browser-locks'
		path = lock_dir / f'{key}.lock'
		with lock, locked(path):
			yield
	def _check(self):
		report = preflight(self.spec, config=self.config, http_get=self.get, cdp_call=self.call_native)
		if not report['valid']:
			raise PermissionError('; '.join(report['issues']) or 'CDP profile/target is unknown')
		r = report
		return r
	def _permitted(self, op):
		allowed = set(self.session.get('allowed_operations', []))
		if 'allowed_operations' in self.spec:
			allowed &= set(self.spec['allowed_operations'])
		if op not in allowed:
			raise PermissionError(f'CDP {op} is not authorized for this session')
	def inspect(self):
		with self._lock():
			r = self._check()
		return r
	def call(self, method, params=None, *, include_identity=False):
		params = deepcopy(params or {})
		op = operation(method, params)
		if 'forbidden' == op:
			raise PermissionError(f'Unsupported or unsafe CDP method: {method}')
		self._permitted(op)
		with self._lock():
			report = self._check()
			target, browser = (report['target'], report['browser'])
			owned = self._owned.get(target['id'])
			if op in ('navigate', 'write', 'close'):
				if 'browser' != self.session['surface'] or not owned:
					raise PermissionError('Existing user/app targets permit only authorized reads and screenshots')
				if owned['browser'] != browser['websocket_url'] or owned['url'] != target['url']:
					raise PermissionError('Owned target changed outside this guard; inspect ownership again')
			if 'targetId' in params and params['targetId'] != target['id']:
				raise PermissionError('CDP targetId differs from the verified selection')
			if any((key in params for key in ('sessionId', 'browserContextId'))):
				raise PermissionError('Caller-supplied CDP context/session routing is unsupported')
			if 'navigate' == op and 'Page.navigate' == method:
				url = params.get('url', '')
				if not any((fnmatchcase(url, pattern) for pattern in self.session['target_url_patterns'])):
					raise PermissionError('Navigation URL is outside the authorized session')
			endpoint = browser['websocket_url'] if method.startswith(('Target.', 'Browser.')) else target['websocket_url']
			if method in ('Target.closeTarget', 'Browser.getWindowForTarget'):
				params['targetId'] = target['id']
			result = self.call_native(endpoint, method, params)
			if owned:
				if 'close' == op:
					self._owned.pop(target['id'], None)
				else:
					after = preflight(self.spec, config=self.config, http_get=self.get, cdp_call=self.call_native)
					if after['valid']:
						owned['url'] = after['target']['url']
			r = (result, deepcopy(report)) if include_identity else result
		return r
	def create_target(self, url, *, background=False):
		if 'browser' != self.session['surface']:
			raise PermissionError('Desktop application window creation is unsupported')
		self._permitted('create')
		if not any((fnmatchcase(url, pattern) for pattern in self.session.get('target_url_patterns', []))):
			raise PermissionError('New target URL is outside the authorized session')
		with self._lock():
			report = self._check()
			create_params = {'url': url, 'background': True} if background else {'url': url, 'newWindow': True}
			result = self.call_native(report['browser']['websocket_url'], 'Target.createTarget', create_params)
			identifier = result.get('targetId') if isinstance(result, dict) else None
			if not isinstance(identifier, str) or not identifier or identifier == report['target']['id']:
				raise RuntimeError('Browser did not return a distinct created target ID; no ownership is assigned')
			check_spec = {**self.spec, 'target_id': identifier, 'target_url': url}
			created = preflight(check_spec, config=self.config, http_get=self.get, cdp_call=self.call_native)
			if not created['valid'] or created['browser']['websocket_url'] != report['browser']['websocket_url']:
				raise RuntimeError('Created target could not be verified in the same browser; it was left open without ownership')
			self._owned[identifier] = {'browser': report['browser']['websocket_url'], 'url': url}
			r = {'target_id': identifier, 'owner': 'this-guard', 'session_id': self.spec['session_id'], 'new_window': not background, 'background': bool(background), 'browser': report['browser']['websocket_url']}
		return r
	def select_owned(self, identifier):
		with self._lock():
			if identifier not in self._owned:
				raise PermissionError('Target was not created by this guard')
			self.spec['target_id'] = identifier
			self.spec.pop('target_url', None)
_CDP_CHALLENGE_RE = re.compile('(?i)verify you are human|checking your browser|__LS_SEQ_LOADER__|enable javascript and cookies|name=["\\\'](?:js_challenge|jsc_token)["\\\']|cf-browser-verification|cf_chl_opt|challenge-platform|<noscript>[^<]*enable javascript')
@contextmanager
def _endpoint_lock(endpoint, config):
	key = hashlib.sha256(endpoint.encode()).hexdigest()
	with _LOCKS_GUARD:
		lock = _LOCKS.setdefault(key, threading.Lock())
	cfg_ws = Path(config['workspace_root']).resolve()
	default_ws = Path(settings()['workspace_root']).resolve()
	lock_dir = HARNESS_META / 'ꘖ/data/browser-locks' if cfg_ws == default_ws else cfg_ws / 'ꘖ/data/browser-locks'
	path = lock_dir / f'{key}.lock'
	with lock, locked(path):
		yield
def resolve_cdp_port(config=None, explicit_port=None):
	if None is not explicit_port:
		r = int(explicit_port)
	else:
		cfg = settings() if None is config else config
		try:
			plat_port = platform_settings().get('browser', {}).get('cdp_port')
		except Exception:
			plat_port = None
		if not plat_port:
			for plat_cfg in (cfg.get('platforms') or {}).values():
				if isinstance(plat_cfg, dict) and isinstance(plat_cfg.get('browser'), dict) and plat_cfg['browser'].get('cdp_port'):
					plat_port = plat_cfg['browser']['cdp_port']
					break
		r = int(plat_port or 9222)
	return r
def collect_cdp_dom(root, url, *, cdp_port=None, timeout=15, config=None, http_get=None, cdp_call=None):
	if None is root or not str(root).strip():
		raise ValueError('An explicit project root is required')
	root_path = Path(root).resolve()
	if not root_path.is_dir():
		raise ValueError('Project root is not a directory')
	cfg = settings() if None is config else deepcopy(config)
	port = resolve_cdp_port(cfg, cdp_port)
	endpoint = _endpoint({'endpoint': f'http://127.0.0.1:{port}'})
	get, call = (http_get or _http_json, _transport(cfg, cdp_call))
	clean_url = urldefrag(url)[0]
	parsed_req = urlsplit(clean_url)
	if parsed_req.scheme not in ('http', 'https') or not parsed_req.hostname:
		raise ValueError('A valid HTTP(S) URL is required for CDP DOM collection')
	with _endpoint_lock(endpoint, cfg):
		version, targets = (get(endpoint + '/json/version'), get(endpoint + '/json/list'))
		if not isinstance(version, dict) or not isinstance(targets, list):
			raise ValueError('Invalid CDP discovery response')
		browser_ws = _checked_ws(version.get('webSocketDebuggerUrl'), endpoint)
		if not urlsplit(browser_ws).path.startswith('/devtools/browser/'):
			raise ValueError('Discovery did not expose a browser endpoint')
		profile_info = {'status': 'unverified'}
		try:
			observed_cmd = call(browser_ws, 'Browser.getBrowserCommandLine', {})
			arguments = observed_cmd.get('arguments') if isinstance(observed_cmd, dict) else None
			if isinstance(arguments, list):
				udd = _argument_values(arguments, '--user-data-dir')
				if udd:
					profile_info = {'status': 'observed', 'argument': '--user-data-dir', 'observed': udd[0], 'evidence_method': 'Browser.getBrowserCommandLine'}
		except Exception:
			pass
		existing_matches = [t for t in targets if isinstance(t, dict) and 'page' == t.get('type') and (urldefrag(t.get('url', ''))[0] == clean_url) and t.get('webSocketDebuggerUrl')]
		expr = '({url:location.href,html:document.documentElement?document.documentElement.outerHTML:"",title:document.title||"",readyState:document.readyState||"",textLen:document.body?(document.body.innerText||"").trim().length:0})'
		data = None
		closed = False
		if existing_matches:
			target = existing_matches[0]
			target_id = target.get('id')
			target_mode = 'existing_readonly_tab'
			target_ws = _checked_ws(target.get('webSocketDebuggerUrl'), endpoint)
			if not urlsplit(target_ws).path.startswith('/devtools/page/'):
				raise ValueError('Selected existing tab has no page websocket')
			native = call(target_ws, 'Runtime.evaluate', {'expression': expr, 'throwOnSideEffect': True, 'returnByValue': True})
			if not isinstance(native, dict) or native.get('exceptionDetails'):
				raise RuntimeError('Native DOM evaluation on existing tab failed')
			val = native.get('result', {}).get('value')
			if not isinstance(val, dict) or not isinstance(val.get('html'), str):
				raise RuntimeError('Existing tab DOM evaluation returned invalid payload')
			data = val
		else:
			existing_ids = {t.get('id') for t in targets if isinstance(t, dict) and t.get('id')}
			created_res = call(browser_ws, 'Target.createTarget', {'url': url, 'background': True})
			target_id = created_res.get('targetId') if isinstance(created_res, dict) else None
			if not isinstance(target_id, str) or not target_id or target_id in existing_ids:
				raise RuntimeError('Browser did not return a distinct created background target ID')
			target_mode = 'temporary_background_tab'
			deadline = time.time() + max(1.0, float(timeout))
			try:
				while True:
					current_targets = get(endpoint + '/json/list')
					matches = [t for t in current_targets if isinstance(t, dict) and t.get('id') == target_id and t.get('webSocketDebuggerUrl')] if isinstance(current_targets, list) else []
					if matches:
						target_ws = _checked_ws(matches[0].get('webSocketDebuggerUrl'), endpoint)
						if urlsplit(target_ws).path.startswith('/devtools/page/'):
							try:
								native = call(target_ws, 'Runtime.evaluate', {'expression': expr, 'throwOnSideEffect': True, 'returnByValue': True})
								val = native.get('result', {}).get('value') if isinstance(native, dict) and (not native.get('exceptionDetails')) else None
								if isinstance(val, dict) and isinstance(val.get('html'), str) and val['html'].strip():
									data = val
									html_str = val['html']
									cur_url = val.get('url') or ''
									ready = val.get('readyState') in ('complete', 'interactive') and cur_url not in ('', 'about:blank')
									has_text = (val.get('textLen') or 0) > 0 or bool(re.sub('<(?is)(?:script|style|head|title)[^>]*>.*?</(?:script|style|head|title)>|<[^>]+>', '', html_str).strip())
									is_challenge = bool(_CDP_CHALLENGE_RE.search(html_str))
									if None is not cdp_call or (ready and has_text and (not is_challenge)):
										break
							except Exception:
								if None is not cdp_call:
									raise
					if None is not cdp_call or time.time() >= deadline:
						break
					time.sleep(0.35)
			finally:
				try:
					close_res = call(browser_ws, 'Target.closeTarget', {'targetId': target_id})
					closed = bool(isinstance(close_res, dict) and close_res.get('success', True))
				except Exception:
					pass
		if not isinstance(data, dict) or not isinstance(data.get('html'), str) or (not data['html'].strip()):
			raise RuntimeError('CDP DOM capture returned empty or invalid HTML')
		observed_identity = {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'endpoint': endpoint, 'browser': version.get('Browser'), 'browser_websocket': browser_ws, 'target_id': target_id, 'target_mode': target_mode, 'closed_after_capture': closed, 'profile': profile_info}
		identity_bytes = (json.dumps(observed_identity, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
		identity_hash = hashlib.sha256(identity_bytes).hexdigest()
		identity_path = write_immutable_bytes(root_path / 'ꘖ/KB/Evidence/CDPSessions' / f'{identity_hash}.json', identity_bytes, diff_error='Immutable CDP session identity changed')
		identity_ref = identity_path.relative_to(root_path / 'ꘖ/KB').as_posix()
		r = {'url': data.get('url') or url, 'html': data['html'], 'title': data.get('title') or '', 'target_id': target_id, 'target_mode': target_mode, 'closed_after_capture': closed, 'cdp_identity': identity_ref, 'cdp_identity_sha256': identity_hash, 'endpoint': endpoint}
	return r
