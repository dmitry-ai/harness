# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import glob
import hashlib
import json
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.error import URLError
from urllib.parse import urldefrag, urlsplit
from urllib.request import urlopen
import uuid
# 2026-11-16
# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
# https://github.com/dmitry-ai/harness/issues/81
from .research import classify_html_challenge
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-11-18
# "Externalize agent environments and per-instance system paths into runtime.json":
# https://github.com/dmitry-ai/harness/issues/86
from .runtime import HARNESS_META, extract_platform_homes, platform_settings, settings
# 2026-11-13
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
from .storage import locked, write_immutable_bytes
_LOCKS, _LOCKS_GUARD = ({}, threading.Lock())
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_READ = frozenset({'DOM.getDocument', 'DOM.getOuterHTML', 'DOM.describeNode', 'DOM.querySelector', 'DOM.querySelectorAll', 'DOM.getAttributes', 'DOM.getBoxModel', 'Page.getFrameTree', 'Page.getLayoutMetrics', 'Page.getResourceTree', 'Page.getNavigationHistory', 'Network.getResponseBody', 'Runtime.getProperties', 'Accessibility.getFullAXTree', 'Accessibility.getPartialAXTree', 'Browser.getWindowForTarget'})
_NAVIGATE = frozenset({'Page.navigate', 'Page.reload', 'Page.navigateToHistoryEntry'})
_CLOSE = frozenset({'Target.closeTarget', 'Page.close'})
_NEVER = frozenset({'Browser.close', 'Target.createTarget', 'Target.disposeBrowserContext', 'Target.createBrowserContext', 'Target.attachToTarget', 'Target.sendMessageToTarget', 'Browser.crash', 'Page.crash'})
_LOCAL_HOSTS = {'127.0.0.1', 'localhost', '::1'}
# 2026-11-23
# "Replace getElementById with querySelector in read-only CDP registry and verify on live headless Chromium":
# https://github.com/dmitry-ai/harness/issues/130
DOM_CAPTURE_EXPR = '({url:location.href,html:document.documentElement?document.documentElement.outerHTML:"",title:document.title||"",readyState:document.readyState||"",textLen:document.body?(document.body.innerText||"").trim().length:0})'
MINIMAL_DOM_CAPTURE_EXPR = '({url:location.href,html:document.documentElement.outerHTML})'
UPWORK_PAGE_STATE_EXPR = '({nuxt:document.querySelector("#__NUXT_DATA__")?.textContent||"",title:document.title||"",heading:document.querySelector("h1")?.textContent||"",body:(document.body?.innerText||"").slice(0,1000),readyState:document.readyState||""})'
USER_AGENT_EXPR = 'navigator.userAgent'
READ_ONLY_CDP_EXPRESSIONS = {
	'dom_capture': DOM_CAPTURE_EXPR,
	'minimal_dom_capture': MINIMAL_DOM_CAPTURE_EXPR,
	'upwork_page_state': UPWORK_PAGE_STATE_EXPR,
	'user_agent': USER_AGENT_EXPR,
}
_DOM_CAPTURE_EXPR = DOM_CAPTURE_EXPR
_NODE_CLIENT = "\nlet input='';for await(const chunk of process.stdin) input+=chunk;\nconst {url,method,params,sessionId}=JSON.parse(input);\nconst result=await new Promise((resolve,reject)=>{\n const socket=new WebSocket(url);const timer=setTimeout(()=>{socket.close();reject(new Error('CDP timeout'));},12000);\n socket.onopen=()=>socket.send(JSON.stringify({id:1,method,params:params||{},...(sessionId?{sessionId}:{})}));\n socket.onerror=()=>{clearTimeout(timer);reject(new Error('CDP connection failed'));};\n socket.onmessage=event=>{const message=JSON.parse(event.data);if(message.id!==1)return;\n  clearTimeout(timer);socket.close();if(message.error)reject(new Error(JSON.stringify(message.error)));else resolve(message.result);};\n socket.onclose=()=>{clearTimeout(timer);reject(new Error('CDP socket closed before its response'));};\n});process.stdout.write(JSON.stringify(result));\n"
_NODE_MUX_SESSION = "\nimport readline from 'node:readline';\nconst browserUrl=process.env.HARNESS_CDP_WS;\nconst pending=new Map();\nconst socket=new WebSocket(browserUrl);\nawait new Promise((resolve,reject)=>{\n const timer=setTimeout(()=>{try{socket.close();}catch{}reject(new Error('CDP browser connect timeout'));},10000);\n socket.onopen=()=>{clearTimeout(timer);resolve();};\n socket.onerror=()=>{clearTimeout(timer);reject(new Error('CDP browser connection failed'));};\n});\nprocess.stdout.write(JSON.stringify({ready:true})+'\\n');\nsocket.onmessage=event=>{\n let msg;try{msg=JSON.parse(event.data);}catch{return;}\n if(typeof msg.id!=='number'||!pending.has(msg.id))return;\n const entry=pending.get(msg.id);pending.delete(msg.id);clearTimeout(entry.timer);\n const out=msg.error?{req_id:msg.id,error:msg.error}:{req_id:msg.id,result:msg.result||{}};\n process.stdout.write(JSON.stringify(out)+'\\n');\n};\nsocket.onclose=()=>{\n for(const [id,entry] of pending.entries()){clearTimeout(entry.timer);process.stdout.write(JSON.stringify({req_id:id,error:{message:'CDP socket closed'}})+'\\n');}\n pending.clear();process.exit(0);\n};\nconst rl=readline.createInterface({input:process.stdin,crlfDelay:Infinity});\nrl.on('line',line=>{\n if(!line.trim())return;\n let req;try{req=JSON.parse(line);}catch{return;}\n if(req.close){try{socket.close();}catch{}rl.close();return;}\n const id=req.req_id;const timeoutMs=Math.max(1000,Number(req.timeout_ms||12000));\n const timer=setTimeout(()=>{if(pending.has(id)){pending.delete(id);process.stdout.write(JSON.stringify({req_id:id,error:{message:'CDP request timeout'}})+'\\n');}},timeoutMs);\n pending.set(id,{timer});\n const payload={id,method:req.method,params:req.params||{}};\n if(req.sessionId)payload.sessionId=req.sessionId;\n socket.send(JSON.stringify(payload));\n});\nrl.on('close',()=>{try{socket.close();}catch{}});\n"
# @used-by :func:`browser_anchor_status()`
# @used-by :func:`collect_cdp_dom()`
# @used-by :func:`preflight()`
# @used-by :meth:`GuardedCDP.__init__()`
# @used-by :meth:`ManagedHeadlessShell.__enter__()`
def _http_json(url):
	with urlopen(url, timeout=8) as response:
		r = json.load(response)
	return r
# @used-by :func:`preflight()`
def _normal_path(value):
	return str(value).strip('"\'').replace('\\', '/').rstrip('/').casefold()
# @used-by :func:`_endpoint_with_meta()`
# @used-by :meth:`ManagedHeadlessShell.__enter__()`
def _read_active_port_file(path_value):
	lines = Path(path_value).expanduser().read_text(encoding='utf-8-sig').splitlines()
	if not lines:
		raise ValueError('Empty DevToolsActivePort')
	port = int(lines[0].strip())
	if not 0 < port < 65536:
		raise ValueError('Invalid DevToolsActivePort')
	ws_path = lines[1].strip() if 1 < len(lines) and lines[1].strip() else None
	return (port, ws_path)
# @used-by :func:`_endpoint()`
# @used-by :func:`preflight()`
def _endpoint_with_meta(session):
	endpoint = session.get('endpoint')
	ws_path = None
	used_active_port = False
	if session.get('devtools_active_port'):
		if endpoint:
			raise ValueError('Choose endpoint or devtools_active_port, not both')
		active_path = Path(session['devtools_active_port']).expanduser()
		if active_path.is_file():
			port, ws_path = _read_active_port_file(active_path)
			endpoint = f"http://{session.get('host', '127.0.0.1')}:{port}"
			used_active_port = True
		elif session.get('fallback_endpoint'):
			endpoint = session['fallback_endpoint']
		else:
			port, ws_path = _read_active_port_file(active_path)
			endpoint = f"http://{session.get('host', '127.0.0.1')}:{port}"
			used_active_port = True
	parsed = urlsplit(endpoint or '')
	if parsed.scheme not in ('http', 'https') or parsed.hostname not in _LOCAL_HOSTS or parsed.username or parsed.password or parsed.query or parsed.fragment or (parsed.path not in ('', '/')):
		raise ValueError('A configured loopback CDP endpoint is required')
	return (endpoint.rstrip('/'), ws_path, used_active_port)
# @used-by :func:`browser_anchor_status()`
# @used-by :func:`collect_cdp_dom()`
# @used-by :func:`preflight()`
# @used-by :meth:`GuardedCDP._lock()`
def _endpoint(session):
	endpoint, _, _ = _endpoint_with_meta(session)
	return endpoint
# @used-by :func:`_verify_context_anchor()`
# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
# @used-by :func:`browser_anchor_status()`
# @used-by :func:`collect_cdp_dom()`
# @used-by :func:`discover_cdp_browser()`
# @used-by :func:`preflight()`
# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
# @used-by :meth:`ManagedHeadlessShell.__enter__()`
def _checked_ws(value, endpoint):
	actual, expected = (urlsplit(value or ''), urlsplit(endpoint))
	if actual.scheme not in ('ws', 'wss') or actual.hostname != expected.hostname or actual.port != expected.port or actual.username or actual.password or actual.query or actual.fragment:
		raise ValueError('Discovered CDP websocket does not belong to the configured endpoint')
	return value
# @used-by :func:`browser_anchor_status()`
# @used-by :func:`preflight()`
# @used-by :meth:`GuardedCDP.__init__()`
def _session(spec, config):
	identifier = spec.get('session_id')
	sessions = config.get('text', {}).get('browser', {}).get('sessions', {})
	if not isinstance(identifier, str) or identifier not in sessions:
		raise ValueError('Select an explicitly authorized runtime text.browser.sessions session_id')
	value = deepcopy(sessions[identifier])
	if value.get('surface') not in ('browser', 'codex', 'antigravity'):
		raise ValueError('Session surface must distinguish browser, codex or antigravity')
	return value
# @used-by :func:`preflight()`
def _profile(session, config):
	value = session.get('profile', {})
	if value.get('path') and (value.get('platform') or value.get('name')):
		raise ValueError('Use one profile path or one runtime profile reference')
	path = value.get('path')
	if not path and value.get('platform') and value.get('name'):
		# 2026-11-18
		# "Externalize agent environments and per-instance system paths into runtime.json":
		# https://github.com/dmitry-ai/harness/issues/86
		plat_cfg = config.get('platforms', {}).get(value['platform'], {})
		path = extract_platform_homes(plat_cfg, platform=value['platform'], include_disabled=True).get(value['name'])
	argument = value.get('argument')
	if not isinstance(path, str) or not path.strip() or (not isinstance(argument, str)) or (not argument.startswith('--')):
		raise ValueError('Session needs a profile path/reference and its observable command-line argument')
	return (path, argument)
# @used-by :func:`collect_cdp_dom()`
# @used-by :func:`preflight()`
def _argument_values(arguments, flag):
	values = []
	for index, argument in enumerate(arguments):
		if not isinstance(argument, str):
			raise ValueError('Native browser command line contains a non-string argument')
		if argument.startswith(flag + '='):
			values.append(argument[len(flag) + 1:])
		elif argument == flag and index + 1 < len(arguments):
			values.append(arguments[index + 1])
	return values
# @used-by :func:`_transport()`
# @used-by :meth:`CDPSession.__enter__()`
def _node_binary(config):
	return config.get('text', {}).get('browser', {}).get('node') or config.get('platforms', {}).get('codex', {}).get('node')
# @used-by :func:`collect_cdp_dom()`
# @used-by :func:`preflight()`
# @used-by :meth:`GuardedCDP.__init__()`
# @used-by :meth:`GuardedCDP._check()`
def _transport(config, override):
	if None is not override:
		return override
	node = _node_binary(config)
	# @used-by :func:`_transport()`
	def call(url, method, params, session_id=None):
		if not node:
			raise ValueError('Configure a Node runtime for the built-in CDP transport')
		payload = {'url': url, 'method': method, 'params': params or {}}
		if session_id:
			payload['sessionId'] = session_id
		result = subprocess.run([node, '--input-type=module', '-e', _NODE_CLIENT], input=json.dumps(payload), capture_output=True, text=True, timeout=16, creationflags=_NO_WINDOW)
		if result.returncode:
			raise RuntimeError('CDP request failed: ' + (result.stderr.strip() or 'no native response'))
		return json.loads(result.stdout)
	return call
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
class CDPSession:
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :func:`browser_anchor_status()`
	# @used-by :func:`collect_cdp_dom()`
	# @used-by :func:`collect_headless_dom()`
	# @used-by :func:`preflight()`
	# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`GuardedCDP.create_target()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __init__(self, browser_ws, config=None, *, cdp_call=None):
		self.browser_ws = browser_ws
		self.config = settings() if None is config else config
		self._override = cdp_call
		self._proc = None
		self._req_id = 0
		self._session_targets = {}
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :func:`browser_anchor_status()`
	# @used-by :func:`collect_cdp_dom()`
	# @used-by :func:`collect_headless_dom()`
	# @used-by :func:`preflight()`
	# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`GuardedCDP.create_target()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __enter__(self):
		if None is self._override:
			node = _node_binary(self.config)
			if not node:
				raise ValueError('Configure a Node runtime for the persistent CDP session')
			self._proc = subprocess.Popen([node, '--input-type=module', '-e', _NODE_MUX_SESSION], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1, env={**os.environ, 'HARNESS_CDP_WS': self.browser_ws}, creationflags=_NO_WINDOW)
			ready_line = self._proc.stdout.readline() if self._proc.stdout else ''
			if not ready_line.strip():
				err = self._proc.stderr.read().strip() if self._proc.stderr else 'no ready signal'
				self.close()
				raise RuntimeError('CDP session startup failed: ' + err)
			ready_obj = json.loads(ready_line)
			if not isinstance(ready_obj, dict) or not ready_obj.get('ready'):
				self.close()
				raise RuntimeError('CDP session did not report ready')
		return self
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :func:`browser_anchor_status()`
	# @used-by :func:`collect_cdp_dom()`
	# @used-by :func:`collect_headless_dom()`
	# @used-by :func:`preflight()`
	# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`GuardedCDP.create_target()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __exit__(self, exc_type, exc, tb):
		self.close()
		return False
	# @used-by :func:`_verify_context_anchor()`
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :func:`browser_anchor_status()`
	# @used-by :func:`collect_cdp_dom()`
	# @used-by :func:`collect_headless_dom()`
	# @used-by :meth:`GuardedCDP._broker_create_tab()`
	# @used-by :meth:`GuardedCDP._broker_remove_tab()`
	# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def attach_target(self, target_id, *, fallback_ws=None):
		res = self.send('Target.attachToTarget', {'targetId': target_id, 'flatten': True})
		sid = res.get('sessionId') if isinstance(res, dict) else None
		if isinstance(sid, str) and sid:
			self._session_targets[sid] = fallback_ws or f'{self.browser_ws}#session={sid}'
			r = sid
		elif None is not self._override and fallback_ws:
			fake_sid = f'compat:{target_id}'
			self._session_targets[fake_sid] = fallback_ws
			r = fake_sid
		else:
			raise RuntimeError(f'CDP Target.attachToTarget did not return a sessionId for {target_id}')
		return r
	# @used-by :meth:`CDPSession.__enter__()`
	# @used-by :meth:`CDPSession.__exit__()`
	def close(self):
		proc = self._proc
		self._proc = None
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
			for stream in (proc.stdin, proc.stdout, proc.stderr):
				if None is not stream:
					try:
						stream.close()
					except OSError:
						pass
	# @used-by :func:`_verify_context_anchor()`
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :func:`browser_anchor_status()`
	# @used-by :func:`collect_cdp_dom()`
	# @used-by :func:`collect_headless_dom()`
	# @used-by :meth:`GuardedCDP._broker_create_tab()`
	# @used-by :meth:`GuardedCDP._broker_remove_tab()`
	# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def detach_target(self, session_id):
		if isinstance(session_id, str) and session_id and (not session_id.startswith('compat:')):
			try:
				self.send('Target.detachFromTarget', {'sessionId': session_id})
			except Exception:
				pass
		self._session_targets.pop(session_id, None)
	# @used-by :func:`_poll_dom_on_session()`
	# @used-by :func:`_query_target_infos()`
	# @used-by :func:`_verify_context_anchor()`
	# @used-by :func:`agent_tools.upwork_extract._eval_session()`
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :func:`browser_anchor_status()`
	# @used-by :func:`collect_cdp_dom()`
	# @used-by :func:`collect_headless_dom()`
	# @used-by :meth:`CDPSession.attach_target()`
	# @used-by :meth:`CDPSession.detach_target()`
	# @used-by :meth:`GuardedCDP._broker_create_tab()`
	# @used-by :meth:`GuardedCDP._broker_remove_tab()`
	# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def send(self, method, params=None, *, session_id=None, timeout_ms=12000):
		params = deepcopy(params or {})
		if None is not self._override:
			target_url = self._session_targets.get(session_id, self.browser_ws) if session_id else self.browser_ws
			r = self._override(target_url, method, params)
		else:
			if None is self._proc or None is self._proc.stdin or None is self._proc.stdout:
				raise RuntimeError('Persistent CDP session is not open')
			self._req_id += 1
			rid = self._req_id
			wire = {'req_id': rid, 'method': method, 'params': params, 'timeout_ms': int(timeout_ms)}
			if session_id:
				wire['sessionId'] = session_id
			self._proc.stdin.write(json.dumps(wire) + '\n')
			self._proc.stdin.flush()
			while True:
				line = self._proc.stdout.readline()
				if not line:
					err_tail = self._proc.stderr.read().strip() if self._proc.stderr else ''
					raise RuntimeError(f'CDP session closed during {method}: {err_tail or "EOF"}')
				msg = json.loads(line)
				if isinstance(msg, dict) and msg.get('req_id') == rid:
					if 'error' in msg:
						raise RuntimeError(f'CDP {method} error: ' + json.dumps(msg['error']))
					r = msg.get('result', {})
					break
		return r
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
class ManagedHeadlessShell:
	# @used-by :func:`agent_tools.research.collect_browser_batch()`
	# @used-by :func:`agent_tools.research.collect_plan()`
	# @used-by :func:`collect_headless_dom()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __init__(self, config=None, *, executable=None):
		self.config = settings() if None is config else config
		self.executable = Path(executable) if executable else resolve_headless_shell(self.config)
		self._temp_dir = None
		self._proc = None
		self.endpoint = None
		self.browser_ws = None
		self.version = None
	# @used-by :func:`agent_tools.research.collect_browser_batch()`
	# @used-by :func:`agent_tools.research.collect_plan()`
	# @used-by :func:`collect_headless_dom()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __enter__(self):
		if not self.executable.is_file():
			raise FileNotFoundError(f'Configured chrome-headless-shell executable does not exist: {self.executable}')
		self._temp_dir = tempfile.TemporaryDirectory(prefix='harness-chs-')
		udd = Path(self._temp_dir.name)
		argv = [str(self.executable), '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--disable-sync', '--remote-debugging-port=0', f'--user-data-dir={udd}']
		self._proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=_NO_WINDOW)
		active_file = udd / 'DevToolsActivePort'
		deadline = time.time() + 10.0
		port = None
		while time.time() < deadline:
			if None is not self._proc.poll():
				err = self._proc.stderr.read().decode('utf-8', errors='replace').strip() if self._proc.stderr else ''
				self.close()
				raise RuntimeError(f'chrome-headless-shell exited prematurely: {err}')
			if active_file.is_file():
				try:
					port, _ = _read_active_port_file(active_file)
					break
				except (OSError, ValueError):
					pass
			time.sleep(0.05)
		if None is port:
			self.close()
			raise RuntimeError('Timed out waiting for chrome-headless-shell DevToolsActivePort')
		self.endpoint = f'http://127.0.0.1:{port}'
		ver_deadline = time.time() + 5.0
		while time.time() < ver_deadline:
			try:
				self.version = _http_json(self.endpoint + '/json/version')
				self.browser_ws = _checked_ws(self.version.get('webSocketDebuggerUrl'), self.endpoint)
				break
			except Exception:
				time.sleep(0.05)
		if not self.browser_ws:
			self.close()
			raise RuntimeError('chrome-headless-shell /json/version did not become ready')
		return self
	# @used-by :func:`collect_headless_dom()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
	def __exit__(self, exc_type, exc, tb):
		self.close()
		return False
	# @used-by :meth:`ManagedHeadlessShell.__enter__()`
	# @used-by :meth:`ManagedHeadlessShell.__exit__()`
	def close(self):
		proc = self._proc
		self._proc = None
		if None is not proc:
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
		temp_dir = self._temp_dir
		self._temp_dir = None
		if None is not temp_dir:
			try:
				temp_dir.cleanup()
			except OSError:
				pass
# @used-by :func:`headless_mcp_args()`
# @used-by :meth:`ManagedHeadlessShell.__init__()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m1_live_headless_shell_public_isolation_and_h_chs_6_static_skip()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
def resolve_headless_shell(config=None):
	cfg = settings() if None is config else config
	hs_cfg = cfg.get('text', {}).get('browser', {}).get('headless_shell') or {}
	candidates = []
	if isinstance(hs_cfg, str) and hs_cfg.strip():
		candidates.append(Path(hs_cfg.strip()))
	elif isinstance(hs_cfg, dict):
		if isinstance(hs_cfg.get('executable'), str) and hs_cfg['executable'].strip():
			candidates.append(Path(hs_cfg['executable'].strip()))
		if isinstance(hs_cfg.get('fallback_glob'), str) and hs_cfg['fallback_glob'].strip():
			candidates.extend((Path(p) for p in sorted(glob.glob(hs_cfg['fallback_glob'].strip()), reverse=True)))
	for plat_cfg in (cfg.get('platforms') or {}).values():
		if isinstance(plat_cfg, dict) and isinstance(plat_cfg.get('browser'), dict):
			plat_hs = plat_cfg['browser'].get('headless_shell')
			if isinstance(plat_hs, str) and plat_hs.strip():
				candidates.append(Path(plat_hs.strip()))
	which_hs = shutil.which('chrome-headless-shell')
	if which_hs:
		candidates.append(Path(which_hs))
	for cand in candidates:
		if cand.is_file():
			return cand.resolve()
	raise FileNotFoundError('chrome-headless-shell executable not found; configure text.browser.headless_shell.executable in runtime.json')
# @used-by :func:`agent_tools.native_profiles._antigravity_plan()`
def headless_mcp_args(config=None):
	exe = resolve_headless_shell(config)
	return ['--headless', '--isolated', f'--executablePath={exe.as_posix()}']
# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
# @used-by :func:`preflight()`
# @used-by :meth:`GuardedCDP._broker_create_tab()`
def _query_target_infos(cdp_sess, fallback_targets):
	infos = []
	try:
		res = cdp_sess.send('Target.getTargets', {})
		raw = res.get('targetInfos') if isinstance(res, dict) else None
		if isinstance(raw, list):
			infos = [item for item in raw if isinstance(item, dict)]
	except Exception:
		infos = []
	if not infos and isinstance(fallback_targets, list):
		infos = [{'targetId': t.get('id') or t.get('targetId'), 'type': t.get('type'), 'url': t.get('url'), 'title': t.get('title'), 'browserContextId': t.get('browserContextId')} for t in fallback_targets if isinstance(t, dict)]
	return infos
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# @used-by :func:`preflight()`
def _verify_context_anchor(prof_cfg, target_infos, targets, endpoint, cdp_sess, report):
	ext_id = prof_cfg.get('extension_id')
	sentinel_origin = prof_cfg.get('sentinel_origin')
	sentinel_cookie = prof_cfg.get('sentinel_cookie_name') or '__harness_primary_profile'
	ws_by_id = {t.get('id'): t.get('webSocketDebuggerUrl') for t in (targets or []) if isinstance(t, dict) and t.get('id') and t.get('webSocketDebuggerUrl')}
	if isinstance(ext_id, str) and ext_id.strip():
		prefix = f'chrome-extension://{ext_id.strip()}/'
		offscreen_url = prefix + 'offscreen.html'
		ext_targets = [t for t in target_infos if str(t.get('url') or '').startswith(prefix)]
		ext_contexts = {t.get('browserContextId') for t in ext_targets if isinstance(t.get('browserContextId'), str) and t.get('browserContextId')}
		if 1 < len(ext_contexts):
			report['profile']['status'] = 'mismatch'
			report['issues'].append('Anchor extension is loaded in multiple browser contexts; load it exclusively in Default')
			return
		if 1 == len(ext_contexts):
			ctx_id = next(iter(ext_contexts))
			chosen = next((t for t in ext_targets if t.get('url') == offscreen_url), ext_targets[0])
			tid = chosen.get('targetId') or chosen.get('id')
			report['profile'].update(status='verified', evidence_method='M-2A:extension-offscreen-anchor', browser_context_id=ctx_id, anchor_target_id=tid, extension_id=ext_id.strip())
			return
	if isinstance(sentinel_origin, str) and sentinel_origin.strip():
		origin = sentinel_origin.strip().rstrip('/')
		by_ctx = {}
		for t in target_infos:
			tid = t.get('targetId') or t.get('id')
			ctx = t.get('browserContextId')
			if 'page' == t.get('type') and isinstance(tid, str) and tid and isinstance(ctx, str) and ctx and (not str(t.get('url') or '').startswith('devtools://')):
				by_ctx.setdefault(ctx, []).append(tid)
		matched_contexts = set()
		for ctx_id, page_ids in by_ctx.items():
			for pid in page_ids:
				fb_ws = None
				if pid in ws_by_id:
					try:
						fb_ws = _checked_ws(ws_by_id[pid], endpoint)
					except ValueError:
						fb_ws = None
				sid = None
				try:
					sid = cdp_sess.attach_target(pid, fallback_ws=fb_ws)
					quota = cdp_sess.send('Storage.getUsageAndQuota', {'origin': origin}, session_id=sid)
					usage = quota.get('usage', 0) if isinstance(quota, dict) else 0
					has_marker = isinstance(usage, (int, float)) and 0 < usage
					if not has_marker:
						ck_res = cdp_sess.send('Network.getCookies', {'urls': [origin + '/']}, session_id=sid)
						cks = ck_res.get('cookies') if isinstance(ck_res, dict) else []
						has_marker = isinstance(cks, list) and any((isinstance(c, dict) and c.get('name') == sentinel_cookie for c in cks))
					if has_marker:
						matched_contexts.add(ctx_id)
					break
				except Exception:
					continue
				finally:
					if sid:
						cdp_sess.detach_target(sid)
		if 1 < len(matched_contexts):
			report['profile']['status'] = 'mismatch'
			report['issues'].append('Sentinel origin marker found in multiple browser contexts')
			return
		if 1 == len(matched_contexts):
			ctx_id = next(iter(matched_contexts))
			report['profile'].update(status='verified', evidence_method='M-2B:sentinel-origin', browser_context_id=ctx_id, sentinel_origin=origin)
			return
	if 'verified' != report['profile'].get('status'):
		report['issues'].append('Primary Chrome profile Default could not be verified via M-2A offscreen extension anchor or M-2B sentinel origin')
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
# @used-by :func:`browser_anchor_status()`
# @used-by :meth:`GuardedCDP._check()`
# @used-by :meth:`GuardedCDP.call()`
# @used-by :meth:`GuardedCDP.create_target()`
# @used-by :meth:`test_text_browser.TextBrowserTests.check()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_live_account_marker_is_separate_from_profile_and_caller_assertion()`
def preflight(spec, *, config=None, http_get=None, cdp_call=None, require_target=True, cdp_session=None):
	config = settings() if None is config else config
	report = {'schema_version': 1, 'session_id': spec.get('session_id'), 'valid': False, 'profile': {'status': 'unknown'}, 'target': {'status': 'unknown'}, 'account': {'status': 'unknown'}, 'issues': [], 'independent_http_allowed': True, 'limitation': 'Cooperative check of the configured live CDP endpoint; it does not prove server internals, model reading, or ownership of external calls'}
	try:
		session = _session(spec, config)
		report['surface'] = session['surface']
		endpoint, active_ws_path, used_active_port = _endpoint_with_meta(session)
		get = http_get or _http_json
		try:
			version, targets, browser_ws = discover_cdp_browser(endpoint, get)
		except (URLError, OSError, ValueError) as first_exc:
			fb_ep = session.get('fallback_endpoint')
			if used_active_port and fb_ep and fb_ep.rstrip('/') != endpoint:
				endpoint = _endpoint({'endpoint': fb_ep})
				active_ws_path, used_active_port = (None, False)
				version, targets, browser_ws = discover_cdp_browser(endpoint, get)
			else:
				raise first_exc
		report['endpoint'] = endpoint
		call = _transport(config, cdp_call)
		report['browser'] = {'product': version.get('Browser'), 'websocket_url': browser_ws}
		report['inventory'] = [{key: item.get(key) for key in ('id', 'type', 'url', 'title')} for item in targets if isinstance(item, dict)]
		expected, argument = _profile(session, config)
		prof_cfg = session.get('profile', {})
		needs_context_isolation = bool(prof_cfg.get('extension_id') or prof_cfg.get('sentinel_origin'))
		report['profile'].update(expected=expected, argument=argument)
		cmdline_exc = None
		try:
			arguments = probe_cdp_arguments(browser_ws, call)
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
			constraints = prof_cfg.get('additional_arguments', {})
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
			cmdline_exc = exc
			if not needs_context_isolation:
				report['issues'].append('Profile cannot be verified: ' + str(exc))
		target_infos = []
		if needs_context_isolation and 'mismatch' != report['profile']['status']:
			if None is not cmdline_exc and used_active_port and active_ws_path and (urlsplit(browser_ws).path != active_ws_path):
				report['profile']['status'] = 'mismatch'
				report['issues'].append('DevToolsActivePort websocket path does not match discovered browser endpoint')
			else:
				if 'verified' == report['profile']['status']:
					report['profile']['status'] = 'unknown'
				# @used-by :func:`preflight()`
				@contextmanager
				def _mux():
					if None is not cdp_session:
						yield cdp_session
					else:
						with CDPSession(browser_ws, config, cdp_call=cdp_call) as opened:
							yield opened
				with _mux() as mux:
					target_infos = _query_target_infos(mux, targets)
					_verify_context_anchor(prof_cfg, target_infos, targets, endpoint, mux, report)
					if 'verified' == report['profile']['status'] and None is not cmdline_exc and used_active_port:
						report['profile']['devtools_active_port_verified'] = True
		identifier = spec.get('target_id')
		matches = [item for item in targets if isinstance(item, dict) and item.get('id') == identifier]
		if not require_target and (not isinstance(identifier, str) or not identifier):
			report['target'] = {'status': 'omitted'}
		elif not isinstance(identifier, str) or not identifier or 1 != len(matches):
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
				verified_ctx = report['profile'].get('browser_context_id')
				if verified_ctx:
					t_info = next((ti for ti in target_infos if (ti.get('targetId') or ti.get('id')) == identifier), None)
					actual_ctx = (t_info or {}).get('browserContextId') or target.get('browserContextId')
					if actual_ctx != verified_ctx:
						report['issues'].append('Selected target belongs to a secondary browser profile (browserContextId mismatch)')
					else:
						target_ws = _checked_ws(target.get('webSocketDebuggerUrl'), endpoint)
						if not urlsplit(target_ws).path.startswith('/devtools/page/'):
							raise ValueError('Selected target has no page websocket')
						report['target'].update(status='verified', websocket_url=target_ws, browser_context_id=actual_ctx)
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
		target_ok = ('verified' == report['target']['status']) if require_target else (report['target']['status'] in ('verified', 'omitted'))
		report['valid'] = 'verified' == report['profile']['status'] and target_ok and (not report['issues'])
	except (ValueError, OSError, RuntimeError, TypeError, KeyError, IndexError) as exc:
		report['issues'].append(str(exc))
	return report
# @used-by :meth:`GuardedCDP.call()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_javascript_read_requires_v8_side_effect_guard()`
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
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# @used-by :func:`collect_cdp_dom()`
# @used-by :func:`collect_headless_dom()`
# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
def _poll_dom_on_session(cdp_sess, session_id, timeout, *, single_pass=False):
	deadline = time.time() + max(1.0, float(timeout))
	data = None
	challenge_seen_at = None
	while True:
		try:
			native = cdp_sess.send('Runtime.evaluate', {'expression': _DOM_CAPTURE_EXPR, 'throwOnSideEffect': True, 'returnByValue': True}, session_id=session_id)
			val = native.get('result', {}).get('value') if isinstance(native, dict) and (not native.get('exceptionDetails')) else None
			if isinstance(val, dict) and isinstance(val.get('html'), str) and val['html'].strip():
				data = val
				html_str = val['html']
				cur_url = val.get('url') or ''
				ready = val.get('readyState') in ('complete', 'interactive') and cur_url not in ('', 'about:blank') and (not cur_url.startswith('about:blank#'))
				has_text = 0 < (val.get('textLen') or 0) or bool(re.sub('(?is)<(?:script|style|head|title)[^>]*>.*?</(?:script|style|head|title)>|<[^>]+>', '', html_str).strip())
				# 2026-11-16
				# "Resolve HTML heading-wrapper/Markdown fragment scopes, structural anti-bot challenge classification, and unified DOM/intake source-check provenance":
				# https://github.com/dmitry-ai/harness/issues/81
				is_challenge = classify_html_challenge(html_str)
				if single_pass or (ready and has_text and (not is_challenge)):
					break
				if is_challenge and 'complete' == val.get('readyState'):
					if None is challenge_seen_at:
						challenge_seen_at = time.time()
					elif 1.5 <= time.time() - challenge_seen_at:
						break
		except Exception:
			if single_pass:
				raise
		if single_pass or time.time() >= deadline:
			break
		time.sleep(0.3)
	return data
# 2026-10-20
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
class GuardedCDP:
	# @used-by :func:`agent_tools.research.capture_dom()`
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :func:`collect_cdp_dom()`
	# @used-by :func:`test_text_browser.dom_fixture()`
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
		self.session = _session(spec, self.config)
		self.get = http_get or _http_json
		self._cdp_override = cdp_call
		self.call_native = _transport(self.config, cdp_call)
		self._owned = {}
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :meth:`GuardedCDP.call()`
	# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`GuardedCDP.create_target()`
	# @used-by :meth:`GuardedCDP.inspect()`
	# @used-by :meth:`GuardedCDP.select_owned()`
	@contextmanager
	def _lock(self):
		with _endpoint_lock(_endpoint(self.session), self.config):
			yield
	# @used-by :meth:`GuardedCDP.call()`
	# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`GuardedCDP.create_target()`
	# @used-by :meth:`GuardedCDP.inspect()`
	def _check(self, *, require_target=True, cdp_session=None):
		override = None if self.call_native is _transport(self.config, self._cdp_override) and None is self._cdp_override else self.call_native
		report = preflight(self.spec, config=self.config, http_get=self.get, cdp_call=override, require_target=require_target, cdp_session=cdp_session)
		if not report['valid']:
			raise PermissionError('; '.join(report['issues']) or 'CDP profile/target is unknown')
		return report
	# @used-by :meth:`GuardedCDP.call()`
	# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`GuardedCDP.create_target()`
	def _permitted(self, op):
		allowed = set(self.session.get('allowed_operations', []))
		if 'allowed_operations' in self.spec:
			allowed &= set(self.spec['allowed_operations'])
		if op not in allowed:
			raise PermissionError(f'CDP {op} is not authorized for this session')
	# 2026-11-16
	# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
	# https://github.com/dmitry-ai/harness/issues/80
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
	# @used-by :meth:`GuardedCDP.create_target()`
	def _broker_create_tab(self, cdp_sess, anchor_target_id, verified_ctx, url, endpoint):
		nonce = uuid.uuid4().hex
		placeholder = f'about:blank#{nonce}'
		anchor_sid = cdp_sess.attach_target(anchor_target_id)
		ext_tab_id = None
		try:
			eval_res = cdp_sess.send('Runtime.evaluate', {'expression': f'globalThis.__harnessBroker({json.dumps({"action": "createBackgroundTab", "url": placeholder})})', 'awaitPromise': True, 'returnByValue': True}, session_id=anchor_sid)
			broker_val = eval_res.get('result', {}).get('value') if isinstance(eval_res, dict) and (not eval_res.get('exceptionDetails')) else None
			if not isinstance(broker_val, dict) or not broker_val.get('ok'):
				err_msg = (broker_val or {}).get('error') or 'M-2A anchor extension broker failed to create background tab'
				raise PermissionError(err_msg)
			ext_tab_id = broker_val.get('tabId')
			target_id = None
			deadline = time.time() + 5.0
			while time.time() < deadline:
				infos = _query_target_infos(cdp_sess, self.get(endpoint + '/json/list'))
				matches = [ti for ti in infos if 'page' == ti.get('type') and ti.get('browserContextId') == verified_ctx and (ti.get('url') == placeholder)]
				if 1 == len(matches):
					target_id = matches[0].get('targetId') or matches[0].get('id')
					break
				time.sleep(0.05)
			if not isinstance(target_id, str) or not target_id:
				raise RuntimeError('M-2A broker created tab could not be uniquely correlated in Target.getTargets')
			page_sid = cdp_sess.attach_target(target_id)
			try:
				cdp_sess.send('Page.navigate', {'url': url}, session_id=page_sid)
			finally:
				cdp_sess.detach_target(page_sid)
			return (target_id, ext_tab_id)
		except Exception:
			if None is not ext_tab_id:
				try:
					cdp_sess.send('Runtime.evaluate', {'expression': f'globalThis.__harnessBroker({json.dumps({"action": "removeTab", "tabId": ext_tab_id})})', 'awaitPromise': True, 'returnByValue': True}, session_id=anchor_sid)
				except Exception:
					pass
			raise
		finally:
			cdp_sess.detach_target(anchor_sid)
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
	def _broker_remove_tab(self, cdp_sess, anchor_target_id, ext_tab_id, target_id):
		closed = False
		if anchor_target_id and None is not ext_tab_id:
			anchor_sid = None
			try:
				anchor_sid = cdp_sess.attach_target(anchor_target_id)
				res = cdp_sess.send('Runtime.evaluate', {'expression': f'globalThis.__harnessBroker({json.dumps({"action": "removeTab", "tabId": ext_tab_id})})', 'awaitPromise': True, 'returnByValue': True}, session_id=anchor_sid)
				val = res.get('result', {}).get('value') if isinstance(res, dict) else None
				closed = bool(isinstance(val, dict) and val.get('ok'))
			except Exception:
				closed = False
			finally:
				if anchor_sid:
					cdp_sess.detach_target(anchor_sid)
		if not closed and target_id:
			try:
				close_res = cdp_sess.send('Target.closeTarget', {'targetId': target_id})
				closed = bool(isinstance(close_res, dict) and close_res.get('success', True))
			except Exception:
				closed = False
		return closed
	# @used-by :func:`agent_tools.research.capture_dom()`
	def inspect(self, *, require_target=True):
		with self._lock():
			r = self._check(require_target=require_target)
		return r
	# @used-by :func:`agent_tools.research.capture_dom()`
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_m2a_extension_manifest_key_and_multi_profile_tab_broker_isolation()`
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
					after = preflight(self.spec, config=self.config, http_get=self.get, cdp_call=self._cdp_override)
					if after['valid']:
						owned['url'] = after['target']['url']
			r = (result, deepcopy(report)) if include_identity else result
		return r
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_only_real_created_target_can_be_mutated_and_ownership_change_stops_close()`
	def create_target(self, url, *, background=False, hidden=False):
		if 'browser' != self.session['surface']:
			raise PermissionError('Desktop application window creation is unsupported')
		self._permitted('create')
		if not any((fnmatchcase(url, pattern) for pattern in self.session.get('target_url_patterns', []))):
			raise PermissionError('New target URL is outside the authorized session')
		with self._lock():
			req_target = bool(self.spec.get('target_id'))
			report = self._check(require_target=req_target)
			browser_ws = report['browser']['websocket_url']
			verified_ctx = report['profile'].get('browser_context_id')
			anchor_tid = report['profile'].get('anchor_target_id')
			create_params = {'url': url, 'background': True} if (background or hidden) else {'url': url, 'newWindow': True}
			if hidden:
				create_params['hidden'] = True
			if verified_ctx:
				create_params['browserContextId'] = verified_ctx
			ext_tab_id = None
			try:
				result = self.call_native(browser_ws, 'Target.createTarget', create_params)
				identifier = result.get('targetId') if isinstance(result, dict) else None
			except RuntimeError as exc:
				if not verified_ctx:
					raise
				if not anchor_tid or (not background and (not hidden)):
					raise PermissionError('Cannot create tab in primary profile Default while another Chrome profile is focused without M-2A anchor extension loaded') from exc
				with CDPSession(browser_ws, self.config, cdp_call=self._cdp_override) as mux:
					identifier, ext_tab_id = self._broker_create_tab(mux, anchor_tid, verified_ctx, url, report['endpoint'])
			if not isinstance(identifier, str) or not identifier or identifier == report['target'].get('id'):
				raise RuntimeError('Browser did not return a distinct created target ID; no ownership is assigned')
			check_spec = {**self.spec, 'target_id': identifier, 'target_url': url}
			created = preflight(check_spec, config=self.config, http_get=self.get, cdp_call=self._cdp_override)
			if not created['valid'] or created['browser']['websocket_url'] != browser_ws:
				raise RuntimeError('Created target could not be verified in the same browser; it was left open without ownership')
			self._owned[identifier] = {'browser': browser_ws, 'url': url, 'ext_tab_id': ext_tab_id}
			r = {'target_id': identifier, 'owner': 'this-guard', 'session_id': self.spec['session_id'], 'new_window': not (background or hidden), 'background': bool(background or hidden), 'browser': browser_ws}
		return r
	# 2026-11-16
	# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
	# https://github.com/dmitry-ai/harness/issues/80
	# @used-by :func:`collect_cdp_dom()`
	def capture_authenticated_dom(self, url, *, timeout=15):
		if 'browser' != self.session['surface']:
			raise PermissionError('Authenticated DOM capture requires a browser session surface')
		self._permitted('create')
		self._permitted('read')
		self._permitted('close')
		clean_url = urldefrag(url)[0]
		parsed_req = urlsplit(clean_url)
		if parsed_req.scheme not in ('http', 'https') or not parsed_req.hostname:
			raise ValueError('A valid HTTP(S) URL is required for CDP DOM collection')
		if not any((fnmatchcase(url, pattern) for pattern in self.session.get('target_url_patterns', []))):
			raise PermissionError('Target URL is outside the authorized session patterns')
		with self._lock():
			report = self._check(require_target=False)
			browser_ws = report['browser']['websocket_url']
			endpoint = report['endpoint']
			verified_ctx = report['profile'].get('browser_context_id')
			anchor_tid = report['profile'].get('anchor_target_id')
			single_pass = None is not self._cdp_override
			with CDPSession(browser_ws, self.config, cdp_call=self._cdp_override) as mux:
				target_id = None
				ext_tab_id = None
				target_mode = 'hidden_session_target'
				closed = False
				create_params = {'url': url, 'background': True, 'hidden': True}
				if verified_ctx:
					create_params['browserContextId'] = verified_ctx
				try:
					res = mux.send('Target.createTarget', create_params)
					target_id = res.get('targetId') if isinstance(res, dict) else None
				except RuntimeError as exc:
					if not verified_ctx:
						raise
					if not anchor_tid:
						raise PermissionError('Primary Chrome profile Default is verified via M-2B, but a secondary Chrome profile window was focused last; focus a Default window or load code/browser_extension (M-2A) in Default') from exc
					target_id, ext_tab_id = self._broker_create_tab(mux, anchor_tid, verified_ctx, url, endpoint)
					target_mode = 'm2a_extension_background_tab'
				if not isinstance(target_id, str) or not target_id:
					raise RuntimeError('Browser did not return a created target ID for authenticated capture')
				try:
					fb_ws = None
					if single_pass:
						cur_list = self.get(endpoint + '/json/list')
						found = next((t for t in cur_list if isinstance(t, dict) and t.get('id') == target_id and t.get('webSocketDebuggerUrl')), None)
						if found:
							fb_ws = _checked_ws(found['webSocketDebuggerUrl'], endpoint)
					page_sid = mux.attach_target(target_id, fallback_ws=fb_ws)
					try:
						data = _poll_dom_on_session(mux, page_sid, timeout, single_pass=single_pass)
					finally:
						mux.detach_target(page_sid)
				finally:
					closed = self._broker_remove_tab(mux, anchor_tid, ext_tab_id, target_id)
			if not isinstance(data, dict) or not isinstance(data.get('html'), str) or (not data['html'].strip()):
				raise RuntimeError('Authenticated CDP DOM capture returned empty or invalid HTML')
			identity_ref, identity_hash = save_cdp_identity(self.root, {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'session_id': self.spec['session_id'], 'endpoint': endpoint, 'browser': report['browser']['product'], 'browser_websocket': browser_ws, 'target_id': target_id, 'target_mode': target_mode, 'closed_after_capture': closed, 'profile': report['profile']})
			return {'url': data.get('url') or url, 'html': data['html'], 'title': data.get('title') or '', 'target_id': target_id, 'target_mode': target_mode, 'closed_after_capture': closed, 'cdp_identity': identity_ref, 'cdp_identity_sha256': identity_hash, 'endpoint': endpoint}
	# @used-by :meth:`test_text_browser.TextBrowserTests.test_only_real_created_target_can_be_mutated_and_ownership_change_stops_close()`
	def select_owned(self, identifier):
		with self._lock():
			if identifier not in self._owned:
				raise PermissionError('Target was not created by this guard')
			self.spec['target_id'] = identifier
			self.spec.pop('target_url', None)
# 2026-10-31
# "Extract universal harness.py CLI, add CDP browser fallback on port 9222, and harden source/quote/anchor verification in answer-prepare":
# https://github.com/dmitry-ai/harness/issues/27
# @used-by :func:`collect_cdp_dom()`
# @used-by :meth:`GuardedCDP._lock()`
@contextmanager
def _endpoint_lock(endpoint, config):
	key = hashlib.sha256(endpoint.encode()).hexdigest()
	with _LOCKS_GUARD:
		lock = _LOCKS.setdefault(key, threading.Lock())
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths, workspace_override
	cfg_ws = Path(config['workspace_root']).resolve()
	ovr_locks = workspace_override(cfg_ws, 'browser_locks_dir')
	lock_dir = Path(ovr_locks) if ovr_locks else project_paths(cfg_ws).data_dir / 'browser-locks'
	path = lock_dir / f'{key}.lock'
	with lock, locked(path):
		yield
# 2026-10-31
# "Extract universal harness.py CLI, add CDP browser fallback on port 9222, and harden source/quote/anchor verification in answer-prepare":
# https://github.com/dmitry-ai/harness/issues/27
# @used-by :func:`collect_cdp_dom()`
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
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# @used-by :func:`collect_cdp_dom()`
def collect_headless_dom(root, url, *, timeout=15, config=None, headless_shell=None):
	if None is root or not str(root).strip():
		raise ValueError('An explicit project root is required')
	root_path = Path(root).resolve()
	if not root_path.is_dir():
		raise ValueError('Project root is not a directory')
	cfg = settings() if None is config else deepcopy(config)
	clean_url = urldefrag(url)[0]
	parsed_req = urlsplit(clean_url)
	if parsed_req.scheme not in ('http', 'https') or not parsed_req.hostname:
		raise ValueError('A valid HTTP(S) URL is required for headless DOM collection')
	# @used-by :func:`collect_headless_dom()`
	@contextmanager
	def _shell_ctx():
		if None is not headless_shell:
			yield headless_shell
		else:
			with ManagedHeadlessShell(cfg) as launched:
				yield launched
	with _shell_ctx() as shell:
		with CDPSession(shell.browser_ws, cfg) as mux:
			ctx_id = None
			target_id = None
			closed = False
			try:
				try:
					ctx_res = mux.send('Target.createBrowserContext', {'disposeOnDetach': True})
					ctx_id = ctx_res.get('browserContextId') if isinstance(ctx_res, dict) else None
				except Exception:
					ctx_id = None
				create_params = {'url': url, 'background': True}
				if ctx_id:
					create_params['browserContextId'] = ctx_id
				created = mux.send('Target.createTarget', create_params)
				target_id = created.get('targetId') if isinstance(created, dict) else None
				if not isinstance(target_id, str) or not target_id:
					raise RuntimeError('chrome-headless-shell did not return a targetId')
				page_sid = mux.attach_target(target_id)
				try:
					data = _poll_dom_on_session(mux, page_sid, timeout)
				finally:
					mux.detach_target(page_sid)
			finally:
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
		if not isinstance(data, dict) or not isinstance(data.get('html'), str) or (not data['html'].strip()):
			raise RuntimeError('Headless DOM capture returned empty or invalid HTML')
		profile_meta = {'status': 'verified', 'mode': 'ephemeral_headless_shell', 'evidence_method': 'DevToolsActivePort+Target.createBrowserContext', 'executable': str(shell.executable)}
		identity_ref, identity_hash = save_cdp_identity(root_path, {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'endpoint': shell.endpoint, 'browser': (shell.version or {}).get('Browser'), 'browser_websocket': shell.browser_ws, 'target_id': target_id, 'target_mode': 'ephemeral_headless_context', 'closed_after_capture': closed, 'profile': profile_meta})
		return {'url': data.get('url') or url, 'html': data['html'], 'title': data.get('title') or '', 'target_id': target_id, 'target_mode': 'ephemeral_headless_context', 'closed_after_capture': closed, 'cdp_identity': identity_ref, 'cdp_identity_sha256': identity_hash, 'endpoint': shell.endpoint}
# 2026-10-31
# "Extract universal harness.py CLI, add CDP browser fallback on port 9222, and harden source/quote/anchor verification in answer-prepare":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# @used-by :func:`agent_tools.research.collect_browser()`
# @used-by :func:`agent_tools.research.collect_plan()`
def collect_cdp_dom(root, url, *, cdp_port=None, session_id=None, timeout=15, config=None, http_get=None, cdp_call=None, headless_shell=None):
	if None is root or not str(root).strip():
		raise ValueError('An explicit project root is required')
	root_path = Path(root).resolve()
	if not root_path.is_dir():
		raise ValueError('Project root is not a directory')
	cfg = settings() if None is config else deepcopy(config)
	if isinstance(session_id, str) and session_id.strip():
		guard = GuardedCDP(root_path, {'session_id': session_id.strip()}, config=cfg, http_get=http_get, cdp_call=cdp_call)
		return guard.capture_authenticated_dom(url, timeout=timeout)
	if None is http_get and None is cdp_call:
		user_port = resolve_cdp_port(cfg)
		if None is not cdp_port and int(cdp_port) == user_port:
			raise PermissionError('Public DOM collection cannot connect to the user Chrome CDP port; omit --cdp-port to use managed chrome-headless-shell or pass --session-id for authenticated capture')
		if None is cdp_port:
			return collect_headless_dom(root_path, url, timeout=timeout, config=cfg, headless_shell=headless_shell)
	port = resolve_cdp_port(cfg, cdp_port)
	endpoint = _endpoint({'endpoint': f'http://127.0.0.1:{port}'})
	get, call = (http_get or _http_json, _transport(cfg, cdp_call))
	clean_url = urldefrag(url)[0]
	parsed_req = urlsplit(clean_url)
	if parsed_req.scheme not in ('http', 'https') or not parsed_req.hostname:
		raise ValueError('A valid HTTP(S) URL is required for CDP DOM collection')
	with _endpoint_lock(endpoint, cfg):
		version, targets, browser_ws = discover_cdp_browser(endpoint, get)
		arguments = probe_cdp_arguments(browser_ws, call)
		udd = _argument_values(arguments, '--user-data-dir')
		if not udd:
			raise PermissionError('CDP endpoint profile cannot be verified (--user-data-dir absent); refusing unverified DOM capture')
		profile_info = {'status': 'verified', 'argument': '--user-data-dir', 'observed': udd[0], 'evidence_method': 'Browser.getBrowserCommandLine'}
		existing_ids = {t.get('id') for t in targets if isinstance(t, dict) and t.get('id')}
		single_pass = None is not cdp_call
		with CDPSession(browser_ws, cfg, cdp_call=cdp_call) as mux:
			created_res = mux.send('Target.createTarget', {'url': url, 'background': True, 'hidden': True})
			target_id = created_res.get('targetId') if isinstance(created_res, dict) else None
			if not isinstance(target_id, str) or not target_id or target_id in existing_ids:
				raise RuntimeError('Browser did not return a distinct created hidden target ID')
			target_mode = 'hidden_session_target'
			closed = False
			try:
				fb_ws = None
				if single_pass:
					current_targets = get(endpoint + '/json/list')
					matches = [t for t in current_targets if isinstance(t, dict) and t.get('id') == target_id and t.get('webSocketDebuggerUrl')] if isinstance(current_targets, list) else []
					if matches:
						fb_ws = _checked_ws(matches[0].get('webSocketDebuggerUrl'), endpoint)
				page_sid = mux.attach_target(target_id, fallback_ws=fb_ws)
				try:
					data = _poll_dom_on_session(mux, page_sid, timeout, single_pass=single_pass)
				finally:
					mux.detach_target(page_sid)
			finally:
				try:
					close_res = mux.send('Target.closeTarget', {'targetId': target_id})
					closed = bool(isinstance(close_res, dict) and close_res.get('success', True))
				except Exception:
					closed = False
		if not isinstance(data, dict) or not isinstance(data.get('html'), str) or (not data['html'].strip()):
			raise RuntimeError('CDP DOM capture returned empty or invalid HTML')
		identity_ref, identity_hash = save_cdp_identity(root_path, {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'endpoint': endpoint, 'browser': version.get('Browser'), 'browser_websocket': browser_ws, 'target_id': target_id, 'target_mode': target_mode, 'closed_after_capture': closed, 'profile': profile_info})
		r = {'url': data.get('url') or url, 'html': data['html'], 'title': data.get('title') or '', 'target_id': target_id, 'target_mode': target_mode, 'closed_after_capture': closed, 'cdp_identity': identity_ref, 'cdp_identity_sha256': identity_hash, 'endpoint': endpoint}
	return r
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# @used-by :func:`agent_tools.upwork_project.run()`
def browser_anchor_status(*, session_id=None, init_sentinel_tab=None, config=None, http_get=None, cdp_call=None):
	cfg = settings() if None is config else deepcopy(config)
	sid = session_id or cfg.get('text', {}).get('browser', {}).get('primary_session_id') or 'chrome-default'
	session = _session({'session_id': sid}, cfg)
	prof_cfg = session.get('profile', {})
	ext_id = prof_cfg.get('extension_id')
	ext_path = prof_cfg.get('extension_path')
	sentinel_origin = (prof_cfg.get('sentinel_origin') or 'https://harness-profile.invalid').rstrip('/')
	sentinel_cookie = prof_cfg.get('sentinel_cookie_name') or '__harness_primary_profile'
	sentinel_initialized = False
	if isinstance(init_sentinel_tab, str) and init_sentinel_tab.strip():
		endpoint = _endpoint(session)
		get = http_get or _http_json
		_, targets, browser_ws = discover_cdp_browser(endpoint, get)
		match = next((t for t in targets if isinstance(t, dict) and 'page' == t.get('type') and t.get('id') == init_sentinel_tab.strip()), None)
		if not match:
			raise ValueError(f'Explicit Default profile tab_id not found: {init_sentinel_tab}')
		fb_ws = _checked_ws(match['webSocketDebuggerUrl'], endpoint) if match.get('webSocketDebuggerUrl') else None
		with CDPSession(browser_ws, cfg, cdp_call=cdp_call) as mux:
			attach_sid = mux.attach_target(init_sentinel_tab.strip(), fallback_ws=fb_ws)
			try:
				set_res = mux.send('Network.setCookie', {'name': sentinel_cookie, 'value': 'default-verified', 'url': sentinel_origin + '/', 'domain': urlsplit(sentinel_origin).hostname, 'path': '/', 'secure': True, 'httpOnly': True, 'sameSite': 'Strict', 'expires': int(time.time()) + 315360000}, session_id=attach_sid)
				sentinel_initialized = bool(isinstance(set_res, dict) and set_res.get('success', True))
			finally:
				mux.detach_target(attach_sid)
	report = preflight({'session_id': sid}, config=cfg, http_get=http_get, cdp_call=cdp_call, require_target=False)
	return {'valid': report['valid'], 'session_id': sid, 'extension_id': ext_id, 'extension_path': ext_path, 'sentinel_origin': sentinel_origin, 'sentinel_initialized': sentinel_initialized, 'profile': report['profile'], 'endpoint': report.get('endpoint'), 'issues': report['issues']}
# 2026-11-13
# "Deduplicate HTTP/CDP collection pipeline with browser fallback, extraction cache, and CDP primitives across research.py and text_browser.py":
# https://github.com/dmitry-ai/harness/issues/66
# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
# @used-by :func:`browser_anchor_status()`
# @used-by :func:`collect_cdp_dom()`
# @used-by :func:`preflight()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
def discover_cdp_browser(endpoint, get):
	version, targets = (get(endpoint + '/json/version'), get(endpoint + '/json/list'))
	if not isinstance(version, dict) or not isinstance(targets, list):
		raise ValueError('Invalid CDP discovery response')
	browser_ws = _checked_ws(version.get('webSocketDebuggerUrl'), endpoint)
	if not urlsplit(browser_ws).path.startswith('/devtools/browser/'):
		raise ValueError('Discovery did not expose a browser endpoint')
	return (version, targets, browser_ws)
# 2026-11-13
# "Deduplicate HTTP/CDP collection pipeline with browser fallback, extraction cache, and CDP primitives across research.py and text_browser.py":
# https://github.com/dmitry-ai/harness/issues/66
# @used-by :func:`collect_cdp_dom()`
# @used-by :func:`preflight()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
def probe_cdp_arguments(browser_ws, call):
	observed = call(browser_ws, 'Browser.getBrowserCommandLine', {})
	r = observed.get('arguments') if isinstance(observed, dict) else None
	if not isinstance(r, list):
		raise ValueError('Native browser command-line arguments are unavailable')
	return r
# 2026-11-13
# "Deduplicate HTTP/CDP collection pipeline with browser fallback, extraction cache, and CDP primitives across research.py and text_browser.py":
# https://github.com/dmitry-ai/harness/issues/66
# @used-by :func:`agent_tools.research.capture_dom()`
# @used-by :func:`collect_cdp_dom()`
# @used-by :func:`collect_headless_dom()`
# @used-by :meth:`GuardedCDP.capture_authenticated_dom()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
def save_cdp_identity(root, observed_identity):
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	pp = project_paths(root)
	identity_bytes = (json.dumps(observed_identity, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
	identity_hash = hashlib.sha256(identity_bytes).hexdigest()
	# 2026-11-13
	# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
	# https://github.com/dmitry-ai/harness/issues/63
	identity_path = write_immutable_bytes(pp.evidence_dir / 'CDPSessions' / f'{identity_hash}.json', identity_bytes, diff_error='Immutable CDP session identity changed')
	return (identity_path.relative_to(pp.kb_dir).as_posix(), identity_hash)
