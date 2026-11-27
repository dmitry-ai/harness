# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
import glob
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from urllib.parse import urlsplit
from urllib.request import urlopen
from agent_tools.runtime import extract_platform_homes, platform_settings, settings
from agent_tools.storage import locked, write_immutable_bytes
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
DOM_CAPTURE_EXPR = '({url:location.href,html:document.documentElement?document.documentElement.outerHTML:"",title:document.title||"",readyState:document.readyState||"",textLen:document.body?(document.body.innerText||"").trim().length:0})'
MINIMAL_DOM_CAPTURE_EXPR = '({url:location.href,html:document.documentElement.outerHTML})'
NODE_CLIENT = "\nlet input='';for await(const chunk of process.stdin) input+=chunk;\nconst {url,method,params,sessionId}=JSON.parse(input);\nconst result=await new Promise((resolve,reject)=>{\n const socket=new WebSocket(url);const timer=setTimeout(()=>{socket.close();reject(new Error('CDP timeout'));},12000);\n socket.onopen=()=>socket.send(JSON.stringify({id:1,method,params:params||{},...(sessionId?{sessionId}:{})}));\n socket.onerror=()=>{clearTimeout(timer);reject(new Error('CDP connection failed'));};\n socket.onmessage=event=>{const message=JSON.parse(event.data);if(message.id!==1)return;\n  clearTimeout(timer);socket.close();if(message.error)reject(new Error(JSON.stringify(message.error)));else resolve(message.result);};\n socket.onclose=()=>{clearTimeout(timer);reject(new Error('CDP socket closed before its response'));};\n});process.stdout.write(JSON.stringify(result));\n"
NODE_MUX_SESSION = "\nimport readline from 'node:readline';\nconst browserUrl=process.env.HARNESS_CDP_WS;\nconst pending=new Map();\nconst socket=new WebSocket(browserUrl);\nawait new Promise((resolve,reject)=>{\n const timer=setTimeout(()=>{try{socket.close();}catch{}reject(new Error('CDP browser connect timeout'));},10000);\n socket.onopen=()=>{clearTimeout(timer);resolve();};\n socket.onerror=()=>{clearTimeout(timer);reject(new Error('CDP browser connection failed'));};\n});\nprocess.stdout.write(JSON.stringify({ready:true})+'\\n');\nsocket.onmessage=event=>{\n let msg;try{msg=JSON.parse(event.data);}catch{return;}\n if(typeof msg.id!=='number'||!pending.has(msg.id))return;\n const entry=pending.get(msg.id);pending.delete(msg.id);clearTimeout(entry.timer);\n const out=msg.error?{req_id:msg.id,error:msg.error}:{req_id:msg.id,result:msg.result||{}};\n process.stdout.write(JSON.stringify(out)+'\\n');\n};\nsocket.onclose=()=>{\n for(const [id,entry] of pending.entries()){clearTimeout(entry.timer);process.stdout.write(JSON.stringify({req_id:id,error:{message:'CDP socket closed'}})+'\\n');}\n pending.clear();process.exit(0);\n};\nconst rl=readline.createInterface({input:process.stdin,crlfDelay:Infinity});\nrl.on('line',line=>{\n if(!line.trim())return;\n let req;try{req=JSON.parse(line);}catch{return;}\n if(req.close){try{socket.close();}catch{}rl.close();return;}\n const id=req.req_id;const timeoutMs=Math.max(1000,Number(req.timeout_ms||12000));\n const timer=setTimeout(()=>{if(pending.has(id)){pending.delete(id);process.stdout.write(JSON.stringify({req_id:id,error:{message:'CDP request timeout'}})+'\\n');}},timeoutMs);\n pending.set(id,{timer});\n const payload={id,method:req.method,params:req.params||{}};\n if(req.sessionId)payload.sessionId=req.sessionId;\n socket.send(JSON.stringify(payload));\n});\nrl.on('close',()=>{try{socket.close();}catch{}});\n"
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
READ_ONLY_CDP_EXPRESSIONS = {
	'dom_capture': DOM_CAPTURE_EXPR,
	'minimal_dom_capture': MINIMAL_DOM_CAPTURE_EXPR,
	'upwork_page_state': '({nuxt:document.querySelector("#__NUXT_DATA__")?.textContent||"",title:document.title||"",heading:document.querySelector("h1")?.textContent||"",body:(document.body?.innerText||"").slice(0,1000),readyState:document.readyState||""})',
	'user_agent': 'navigator.userAgent',
}
UPWORK_PAGE_STATE_EXPR = READ_ONLY_CDP_EXPRESSIONS['upwork_page_state']
USER_AGENT_EXPR = READ_ONLY_CDP_EXPRESSIONS['user_agent']
_CLOSE = frozenset({'Target.closeTarget', 'Page.close'})
_LOCAL_HOSTS = {'127.0.0.1', 'localhost', '::1'}
_LOCKS, _LOCKS_GUARD = ({}, threading.Lock())
_NAVIGATE = frozenset({'Page.navigate', 'Page.reload', 'Page.navigateToHistoryEntry'})
_NEVER = frozenset({'Browser.close', 'Target.createTarget', 'Target.disposeBrowserContext', 'Target.createBrowserContext', 'Target.attachToTarget', 'Target.sendMessageToTarget', 'Browser.crash', 'Page.crash'})
_READ = frozenset({'DOM.getDocument', 'DOM.getOuterHTML', 'DOM.describeNode', 'DOM.querySelector', 'DOM.querySelectorAll', 'DOM.getAttributes', 'DOM.getBoxModel', 'Page.getFrameTree', 'Page.getLayoutMetrics', 'Page.getResourceTree', 'Page.getNavigationHistory', 'Network.getResponseBody', 'Runtime.getProperties', 'Accessibility.getFullAXTree', 'Accessibility.getPartialAXTree', 'Browser.getWindowForTarget'})
_STATIC_OPS = {**{m: 'forbidden' for m in _NEVER}, **{m: 'read' for m in _READ}, 'Page.captureScreenshot': 'screenshot', **{m: 'navigate' for m in _NAVIGATE}, **{m: 'close' for m in _CLOSE}}
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__collect_direct_port()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__check_additional_args()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__check_cmdline()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
def dfh_argument_values(arguments, flag):
	values = []
	for index, argument in enumerate(arguments):
		if not isinstance(argument, str):
			raise ValueError('Native browser command line contains a non-string argument')
		if argument.startswith(flag + '='):
			values.append(argument[len(flag) + 1:])
		elif argument == flag and index + 1 < len(arguments):
			values.append(arguments[index + 1])
	return values
# @used-by :meth:`Df.Harness.Research.BatchCollector.BatchCollector.__lazy_headless_fetch()`
# @used-by :meth:`Df.Harness.Research.BrowserCollector.BrowserCollector.__read_dom()`
# @used-by :meth:`test_df_harness_s11_wave2c_cov_browser.DfHarnessS11Wave2CCovBrowserTests.test_anchor_status_preflight_ext_sentinel_and_lib_helpers()`
def dfh_browser_seam(name: str, default):
	mod = sys.modules.get('agent_tools.text_browser')
	cand = getattr(mod, name, None) if None is not mod else None
	return cand if callable(cand) and True is not getattr(cand, '_df_default_browser_facade', False) else default
# @used-by :func:`dfh_discover_cdp_browser()`
# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.__init_sentinel()`
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__fallback_ws()`
# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__fallback_ws()`
# @used-by :meth:`Df.Harness.Text.Browser.HeadlessShell.HeadlessShell.__wait_version()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__probe_sentinel_page()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__verify_target_ws()`
# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__resolve_target()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
def dfh_checked_ws(value, endpoint):
	actual, expected = (urlsplit(value or ''), urlsplit(endpoint))
	if actual.scheme not in ('ws', 'wss') or actual.hostname != expected.hostname or actual.port != expected.port or actual.username or actual.password or actual.query or actual.fragment:
		raise ValueError('Discovered CDP websocket does not belong to the configured endpoint')
	return value
# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.__init_sentinel()`
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__collect_direct_port()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__discover()`
# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__run_mux()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
def dfh_discover_cdp_browser(endpoint, get):
	version, targets = (get(endpoint + '/json/version'), get(endpoint + '/json/list'))
	if not isinstance(version, dict) or not isinstance(targets, list):
		raise ValueError('Invalid CDP discovery response')
	browser_ws = dfh_checked_ws(version.get('webSocketDebuggerUrl'), endpoint)
	if not urlsplit(browser_ws).path.startswith('/devtools/browser/'):
		raise ValueError('Discovery did not expose a browser endpoint')
	return (version, targets, browser_ws)
# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.__init_sentinel()`
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__collect_direct_port()`
# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__lock()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__discover()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
def dfh_endpoint(session):
	endpoint, _, _ = dfh_endpoint_with_meta(session)
	return endpoint
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__collect_direct_port()`
# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__lock()`
@contextmanager
def dfh_endpoint_lock(endpoint, config):
	key = hashlib.sha256(endpoint.encode()).hexdigest()
	with _LOCKS_GUARD:
		lock = _LOCKS.setdefault(key, threading.Lock())
	from agent_tools.path_registry import project_paths, workspace_override
	cfg_ws = Path(config['workspace_root']).resolve()
	ovr_locks = workspace_override(cfg_ws, 'browser_locks_dir')
	lock_dir = Path(ovr_locks) if ovr_locks else project_paths(cfg_ws).data_dir / 'browser-locks'
	with lock, locked(lock_dir / f'{key}.lock'):
		yield
# @used-by :func:`dfh_endpoint()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__discover()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
def dfh_endpoint_with_meta(session):
	endpoint, ws_path, used_active_port = (session.get('endpoint'), None, False)
	if session.get('devtools_active_port'):
		if endpoint:
			raise ValueError('Choose endpoint or devtools_active_port, not both')
		active_path = Path(session['devtools_active_port']).expanduser()
		if not active_path.is_file() and session.get('fallback_endpoint'):
			endpoint = session['fallback_endpoint']
		else:
			port, ws_path = dfh_read_active_port_file(active_path)
			endpoint = f"http://{session.get('host', '127.0.0.1')}:{port}"
			used_active_port = True
	parsed = urlsplit(endpoint or '')
	if parsed.scheme not in ('http', 'https') or parsed.hostname not in _LOCAL_HOSTS or parsed.username or parsed.password or parsed.query or parsed.fragment or (parsed.path not in ('', '/')):
		raise ValueError('A configured loopback CDP endpoint is required')
	return (endpoint.rstrip('/'), ws_path, used_active_port)
# @used-by :func:`Df.Harness.lib.native_ag_plan._rewrite_mcp_chrome_servers()`
# @used-by :meth:`test_df_harness_s11_wave2c_cov_browser.DfHarnessS11Wave2CCovBrowserTests.test_anchor_status_preflight_ext_sentinel_and_lib_helpers()`
def dfh_headless_mcp_args(config=None):
	exe = dfh_resolve_headless_shell(config)
	return ['--headless', '--isolated', f'--executablePath={exe.as_posix()}']
# @used-by :func:`dfh_resolve_headless_shell()`
def dfh_headless_shell_candidates(cfg):
	hs_cfg = cfg.get('text', {}).get('browser', {}).get('headless_shell') or {}
	r = [Path(hs_cfg.strip())] if isinstance(hs_cfg, str) and hs_cfg.strip() else []
	if isinstance(hs_cfg, dict):
		exe, fb_glob = (hs_cfg.get('executable'), hs_cfg.get('fallback_glob'))
		if isinstance(exe, str) and exe.strip():
			r.append(Path(exe.strip()))
		if isinstance(fb_glob, str) and fb_glob.strip():
			r.extend((Path(p) for p in sorted(glob.glob(fb_glob.strip()), reverse=True)))
	r.extend((Path(p['browser']['headless_shell'].strip()) for p in (cfg.get('platforms') or {}).values() if isinstance(p, dict) and isinstance(p.get('browser'), dict) and isinstance(p['browser'].get('headless_shell'), str) and p['browser']['headless_shell'].strip()))
	which_hs = shutil.which('chrome-headless-shell')
	if which_hs:
		r.append(Path(which_hs))
	return r
# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.__init_sentinel()`
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__collect_direct_port()`
# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__init__()`
# @used-by :meth:`Df.Harness.Text.Browser.HeadlessShell.HeadlessShell.__wait_version()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__run_checks()`
# @used-by :meth:`test_df_harness_s11_wave2c_cov_browser.DfHarnessS11Wave2CCovBrowserTests.test_anchor_status_preflight_ext_sentinel_and_lib_helpers()`
def dfh_http_json(url):
	with urlopen(url, timeout=8) as response:
		r = json.load(response)
	return r
# @used-by :func:`dfh_transport()`
# @used-by :meth:`Df.Harness.Text.Browser.CdpSession.CdpSession.__enter__()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
def dfh_node_binary(config):
	return config.get('text', {}).get('browser', {}).get('node') or config.get('platforms', {}).get('codex', {}).get('node')
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__check_cmdline()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
def dfh_normal_path(value):
	return str(value).strip('"\'').replace('\\', '/').rstrip('/').casefold()
# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.call()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_javascript_read_requires_v8_side_effect_guard()`
def dfh_operation(method, params=None):
	if method in _STATIC_OPS:
		r = _STATIC_OPS[method]
	elif method in ('Runtime.evaluate', 'Runtime.callFunctionOn'):
		r = 'read' if True is (params or {}).get('throwOnSideEffect') else 'write'
	elif method.startswith(('Input.', 'DOM.set', 'DOM.remove', 'Runtime.')):
		r = 'write'
	else:
		r = 'forbidden'
	return r
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__collect_direct_port()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__check_cmdline()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
def dfh_probe_cdp_arguments(browser_ws, call):
	observed = call(browser_ws, 'Browser.getBrowserCommandLine', {})
	r = observed.get('arguments') if isinstance(observed, dict) else None
	if not isinstance(r, list):
		raise ValueError('Native browser command-line arguments are unavailable')
	return r
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__run_checks()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
def dfh_profile(session, config):
	value = session.get('profile', {})
	if value.get('path') and (value.get('platform') or value.get('name')):
		raise ValueError('Use one profile path or one runtime profile reference')
	path = value.get('path')
	if not path and value.get('platform') and value.get('name'):
		plat_cfg = config.get('platforms', {}).get(value['platform'], {})
		path = extract_platform_homes(plat_cfg, platform=value['platform'], include_disabled=True).get(value['name'])
	argument = value.get('argument')
	if not isinstance(path, str) or not path.strip() or (not isinstance(argument, str)) or (not argument.startswith('--')):
		raise ValueError('Session needs a profile path/reference and its observable command-line argument')
	return (path, argument)
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__check_context_isolation()`
# @used-by :meth:`Df.Harness.Text.Browser.TabCreator.TabCreator.__wait_target_id()`
# @used-by :meth:`Df.Harness.Upwork.JobExtractor.JobExtractor.__resolve_target()`
def dfh_query_target_infos(cdp_sess, fallback_targets):
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
# @used-by :func:`dfh_endpoint_with_meta()`
# @used-by :meth:`Df.Harness.Text.Browser.HeadlessShell.HeadlessShell.__wait_active_port()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
def dfh_read_active_port_file(path_value):
	lines = Path(path_value).expanduser().read_text(encoding='utf-8-sig').splitlines()
	if not lines:
		raise ValueError('Empty DevToolsActivePort')
	port = int(lines[0].strip())
	if not 0 < port < 65536:
		raise ValueError('Invalid DevToolsActivePort')
	ws_path = lines[1].strip() if 1 < len(lines) and lines[1].strip() else None
	return (port, ws_path)
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__collect_direct_port()`
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.collect()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
def dfh_resolve_cdp_port(config=None, explicit_port=None):
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
# @used-by :func:`dfh_headless_mcp_args()`
# @used-by :meth:`Df.Harness.Text.Browser.HeadlessShell.HeadlessShell.__init__()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m1_live_headless_shell_public_isolation_and_h_chs_6_static_skip()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_read_only_cdp_expressions_live_headless_shell_contract()`
def dfh_resolve_headless_shell(config=None):
	cfg = settings() if None is config else config
	r = next((cand.resolve() for cand in dfh_headless_shell_candidates(cfg) if cand.is_file()), None)
	if None is r:
		raise FileNotFoundError('chrome-headless-shell executable not found; configure text.browser.headless_shell.executable in runtime.json')
	return r
# @used-by :meth:`Df.Harness.Research.DomCapturer.DomCapturer.capture()`
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__collect_direct_port()`
# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.capture_authenticated_dom()`
# @used-by :meth:`Df.Harness.Text.Browser.HeadlessDomCollector.HeadlessDomCollector.collect()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
# @used-by :meth:`test_source_admission.SourceAdmissionTests.test_m4_collect_browser_public_and_authenticated_cdp_identity_provenance()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_collect_plan_delegates_to_collect_http_and_shared_cdp_primitives()`
def dfh_save_cdp_identity(root, observed_identity):
	from agent_tools.path_registry import project_paths
	pp = project_paths(root)
	identity_bytes = (json.dumps(observed_identity, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
	identity_hash = hashlib.sha256(identity_bytes).hexdigest()
	identity_path = write_immutable_bytes(pp.evidence_dir / 'CDPSessions' / f'{identity_hash}.json', identity_bytes, diff_error='Immutable CDP session identity changed')
	return (identity_path.relative_to(pp.kb_dir).as_posix(), identity_hash)
# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.check()`
# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__init__()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__run_checks()`
# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_browser_lib_helpers_validate_endpoints_ports_and_operations()`
def dfh_session(spec, config):
	identifier = spec.get('session_id')
	sessions = config.get('text', {}).get('browser', {}).get('sessions', {})
	if not isinstance(identifier, str) or identifier not in sessions:
		raise ValueError('Select an explicitly authorized runtime text.browser.sessions session_id')
	value = deepcopy(sessions[identifier])
	if value.get('surface') not in ('browser', 'codex', 'antigravity'):
		raise ValueError('Session surface must distinguish browser, codex or antigravity')
	return value
# @used-by :meth:`Df.Harness.Text.Browser.CdpDomCollector.CdpDomCollector.__collect_direct_port()`
# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__check()`
# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__init__()`
# @used-by :meth:`Df.Harness.Text.Browser.PreflightChecker.PreflightChecker.__run_checks()`
def dfh_transport(config, override):
	if None is not override:
		r = override
	else:
		node = dfh_node_binary(config)
		# @used-by :func:`dfh_transport()`
		def call(url, method, params, session_id=None):
			if not node:
				raise ValueError('Configure a Node runtime for the built-in CDP transport')
			payload = {'url': url, 'method': method, 'params': params or {}}
			if session_id:
				payload['sessionId'] = session_id
			result = subprocess.run([node, '--input-type=module', '-e', NODE_CLIENT], input=json.dumps(payload), capture_output=True, text=True, timeout=16, creationflags=NO_WINDOW)
			if result.returncode:
				raise RuntimeError('CDP request failed: ' + (result.stderr.strip() or 'no native response'))
			return json.loads(result.stdout)
		r = call
	return r
