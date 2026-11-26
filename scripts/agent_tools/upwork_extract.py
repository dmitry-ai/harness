# 2026-10-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit
import urllib.request
from .runtime import HARNESS_META, settings
from .storage import create_bytes
# 2026-11-23
# "Replace getElementById with querySelector in read-only CDP registry and verify on live headless Chromium":
# https://github.com/dmitry-ai/harness/issues/130
from .text_browser import UPWORK_PAGE_STATE_EXPR, USER_AGENT_EXPR
from .upwork_data import canonical_job_url, extract_candidate_domains, extract_client_names, normalize_job_id, resolve_nuxt_devalue
# 2026-10-14
# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
# https://github.com/dmitry-ai/harness/issues/3
MAX_ATTACHMENT = 25 * 1024 * 1024
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
# 2026-11-23
# "Replace getElementById with querySelector in read-only CDP registry and verify on live headless Chromium":
# https://github.com/dmitry-ai/harness/issues/130
_PAGE_STATE_EXPR = UPWORK_PAGE_STATE_EXPR
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
def upwork_host(url):
	parsed = urlsplit(url)
	r = 'https' == parsed.scheme and (not parsed.username) and (not parsed.password) and (parsed.port in (None, 443)) and ('upwork.com' == parsed.hostname or (parsed.hostname or '').endswith('.upwork.com'))
	return r
def attachment_path(directory: Path, filename: str) -> Path:
	if not filename or filename in ('.', '..') or re.search('[\\\\/:\\x00-\\x1f<>"|?*]', filename) or filename.endswith((' ', '.')) or re.match('(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\\.|$)', filename):
		raise ValueError(f'Unsafe attachment filename: {filename!r}')
	target = (directory / filename).resolve()
	if target.parent != directory.resolve():
		raise ValueError('Attachment path escapes its directory')
	return target
class SafeRedirect(urllib.request.HTTPRedirectHandler):
	def redirect_request(self, req, fp, code, msg, headers, newurl):
		if 'https' != urlsplit(newurl).scheme:
			raise ValueError('Attachment redirect must use HTTPS')
		result = super().redirect_request(req, fp, code, msg, headers, newurl)
		if result and urlsplit(req.full_url).hostname != urlsplit(newurl).hostname:
			for key in ('Cookie', 'Authorization'):
				result.remove_header(key)
		return result
def download_attachment(attachment, directory: Path, cookies=(), user_agent='UpworkOnboarding/2'):
	target = attachment_path(directory, attachment['fileName'])
	url = urljoin('https://www.upwork.com', attachment['uri'])
	if not upwork_host(url):
		raise ValueError('Initial attachment URL must be an HTTPS Upwork host')
	parsed = urlsplit(url)
	allowed = []
	for cookie in cookies:
		domain = cookie.get('domain', 'www.upwork.com')
		host_matches = parsed.hostname.endswith(domain) or parsed.hostname == domain[1:] if domain.startswith('.') else parsed.hostname == domain
		cookie_path = cookie.get('path') or '/'
		path_matches = parsed.path == cookie_path or parsed.path.startswith(cookie_path if cookie_path.endswith('/') else cookie_path + '/')
		if host_matches and path_matches:
			allowed.append(f"{cookie['name']}={cookie['value']}")
	headers = {'User-Agent': user_agent}
	if allowed:
		headers['Cookie'] = '; '.join(allowed)
	request = urllib.request.Request(url, headers=headers)
	with urllib.request.build_opener(SafeRedirect()).open(request, timeout=25) as response:
		payload = response.read(MAX_ATTACHMENT + 1)
	if len(payload) > MAX_ATTACHMENT:
		raise ValueError('Attachment exceeds 25 MiB')
	directory.mkdir(parents=True, exist_ok=True)
	if not target.exists():
		create_bytes(target, payload)
	elif target.read_bytes() != payload:
		raise FileExistsError(f'Different attachment already exists: {target}')
	return {'path': str(target), 'filename': target.name, 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)}
class RPC:
	def __init__(self, websocket, timeout=30):
		self.websocket, self.timeout, self.next_id = (websocket, timeout, 0)
	async def call(self, method, **params):
		self.next_id += 1
		ident = self.next_id
		await self.websocket.send(json.dumps({'id': ident, 'method': method, 'params': params}))
		async def receive():
			while True:
				message = json.loads(await self.websocket.recv())
				if message.get('id') == ident:
					if 'error' in message:
						raise RuntimeError(f"CDP {method}: {message['error']}")
					return message['result']
		try:
			return await asyncio.wait_for(receive(), timeout=self.timeout)
		except TimeoutError as exc:
			raise TimeoutError(f'CDP {method} did not respond within {self.timeout}s') from exc
	async def evaluate(self, expression):
		result = await self.call('Runtime.evaluate', expression=expression, awaitPromise=True, returnByValue=True)
		if result.get('exceptionDetails'):
			raise RuntimeError(f"Browser evaluation failed: {result['exceptionDetails']}")
		return result.get('result', {}).get('value')
def decode_page(page, job_id):
	if not isinstance(page, dict):
		raise ValueError('Browser page state is unavailable')
	raw = page.get('nuxt') or ''
	decoded = resolve_nuxt_devalue(json.loads(raw)) if raw else {}
	details = (decoded.get('vuex') or {}).get('jobDetails') or {} if isinstance(decoded, dict) else {}
	if (details.get('job') or {}).get('ciphertext') == job_id:
		r = details
	else:
		status = ' '.join((str(page.get(k) or '') for k in ('title', 'heading', 'body')))
		if re.search('access denied|not authorized|no longer available|do not have permission|don.t have permission', status, re.I):
			raise PermissionError('Upwork denies access to this job. No job data captured; do not bypass the restriction.')
		if not raw:
			raise ValueError('Selected tab has no Upwork source data; it may be unloaded or use an unsupported page format')
		raise ValueError('Selected page data does not match the requested job ID')
	return r
def select_tab(tabs, job_id, tab_id=None):
	candidates = [t for t in tabs if 'page' == t.get('type') and upwork_host(t.get('url', ''))]
	if tab_id:
		candidates = [t for t in candidates if t.get('id') == tab_id]
	else:
		def matches(tab):
			path = urlsplit(tab['url']).path
			try:
				r = path.startswith('/jobs/') and normalize_job_id(path) == job_id
			except ValueError:
				r = False
			return r
		candidates = [t for t in candidates if matches(t)]
	if 1 != len(candidates):
		raise ValueError('Select one exact Upwork job tab with --tab-id; no arbitrary account fallback')
	return candidates[0]
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
def _eval_session(mux, session_id, expression, *, await_promise=False, read_only=False, timeout_ms=25000):
	params = {'expression': expression, 'returnByValue': True}
	if await_promise:
		params['awaitPromise'] = True
	if read_only:
		params['throwOnSideEffect'] = True
	result = mux.send('Runtime.evaluate', params, session_id=session_id, timeout_ms=timeout_ms)
	if not isinstance(result, dict) or result.get('exceptionDetails'):
		raise RuntimeError(f"Browser evaluation failed: {(result or {}).get('exceptionDetails')}")
	return result.get('result', {}).get('value')
# 2026-11-16
# "Isolate public DOM captures in chrome-headless-shell, enforce fail-closed primary Chrome profile verification, and block loopback CDP bypasses":
# https://github.com/dmitry-ai/harness/issues/80
def extract_upwork_job(url_or_id, cdp_port=9222, fetch_related=True, attachments_dir=None, tab_id=None, *, session_id=None, config=None, http_get=None, cdp_call=None):
	from .text_browser import CDPSession, GuardedCDP, _checked_ws, _query_target_infos, discover_cdp_browser, preflight
	job_id = normalize_job_id(url_or_id)
	cfg = settings() if None is config else config
	sid = session_id or cfg.get('text', {}).get('browser', {}).get('primary_session_id')
	if not isinstance(sid, str) or sid not in cfg.get('text', {}).get('browser', {}).get('sessions', {}):
		raise PermissionError('Configure text.browser.sessions primary session in runtime.json before Upwork CDP extraction')
	guard_root = HARNESS_META if HARNESS_META.is_dir() else Path.cwd()
	guard = GuardedCDP(guard_root, {'session_id': sid}, config=cfg, http_get=http_get, cdp_call=cdp_call)
	with guard._lock():
		report = preflight({'session_id': sid}, config=cfg, http_get=guard.get, cdp_call=cdp_call, require_target=False)
		if not report['valid']:
			raise PermissionError('; '.join(report['issues']) or 'Primary Chrome profile Default could not be verified')
		endpoint = report['endpoint']
		if None is not cdp_port and urlsplit(endpoint).port != int(cdp_port):
			raise PermissionError(f'Requested CDP port {cdp_port} differs from verified primary session endpoint {endpoint}')
		_, raw_tabs, browser_ws = discover_cdp_browser(endpoint, guard.get)
		verified_ctx = report['profile'].get('browser_context_id')
		anchor_tid = report['profile'].get('anchor_target_id')
		with CDPSession(browser_ws, cfg, cdp_call=cdp_call) as mux:
			target_infos = _query_target_infos(mux, raw_tabs)
			ctx_by_id = {(ti.get('targetId') or ti.get('id')): ti.get('browserContextId') for ti in target_infos if isinstance(ti, dict)}
			if tab_id and verified_ctx and (ctx_by_id.get(tab_id) != verified_ctx):
				raise PermissionError('Selected tab belongs to a secondary Chrome profile (browserContextId mismatch)')
			verified_tabs = [t for t in raw_tabs if isinstance(t, dict) and (not verified_ctx or ctx_by_id.get(t.get('id')) == verified_ctx)]
			created_temp = False
			ext_tab_id = None
			target_id = None
			target_url = canonical_job_url(job_id).replace('https://upwork.com', 'https://www.upwork.com')
			fb_ws = None
			try:
				selected = select_tab(verified_tabs, job_id, tab_id)
				target_id = selected['id']
				target_url = selected['url']
				if selected.get('webSocketDebuggerUrl'):
					fb_ws = _checked_ws(selected['webSocketDebuggerUrl'], endpoint)
			except ValueError:
				if tab_id:
					raise
				created_temp = True
				create_params = {'url': target_url, 'background': True, 'hidden': True}
				if verified_ctx:
					create_params['browserContextId'] = verified_ctx
				try:
					res = mux.send('Target.createTarget', create_params)
					target_id = res.get('targetId') if isinstance(res, dict) else None
				except RuntimeError as exc:
					if not verified_ctx or not anchor_tid:
						raise PermissionError('No open Upwork job tab in Default and cannot open background tab while another Chrome profile is focused without M-2A extension') from exc
					target_id, ext_tab_id = guard._broker_create_tab(mux, anchor_tid, verified_ctx, target_url, endpoint)
				if not isinstance(target_id, str) or not target_id:
					raise RuntimeError('Failed to open temporary Upwork tab in verified Default profile')
			try:
				page_sid = mux.attach_target(target_id, fallback_ws=fb_ws)
				try:
					page = None
					wait_until = time.time() + (15.0 if created_temp and None is cdp_call else 0.0)
					while True:
						page = _eval_session(mux, page_sid, _PAGE_STATE_EXPR, read_only=True)
						if isinstance(page, dict) and (page.get('nuxt') or 'complete' == page.get('readyState')) or time.time() >= wait_until:
							break
						time.sleep(0.35)
					details = decode_page(page or {}, job_id)
					job = details.get('job') or {}
					history, open_jobs = (details.get('workHistory') or [], details.get('openJobs') or [])
					related, failures = ({}, [])
					if fetch_related:
						ids = {(x.get('jobInfo') or {}).get('ciphertext') for x in history}
						ids |= {x.get('ciphertext') for x in open_jobs}
						for ident in sorted(ids - {None, job_id}):
							ident = normalize_job_id(ident)
							rel_url = canonical_job_url(ident).replace('https://upwork.com', 'https://www.upwork.com')
							# 2026-11-23
							# "Replace getElementById with querySelector in read-only CDP registry and verify on live headless Chromium":
							# https://github.com/dmitry-ai/harness/issues/130
							expression = f'(async()=>{{const r=await fetch({json.dumps(rel_url)},{{credentials:"include",signal:AbortSignal.timeout(20000)}});if(!r.ok)throw new Error("HTTP "+r.status);const d=new DOMParser().parseFromString(await r.text(),"text/html");return d.querySelector("#__NUXT_DATA__")?.textContent||"";}})()'
							try:
								text = _eval_session(mux, page_sid, expression, await_promise=True, timeout_ms=25000)
								found = resolve_nuxt_devalue(json.loads(text))['vuex']['jobDetails']['job']
								if found.get('ciphertext') != ident:
									raise ValueError('Related job identity mismatch')
								related[ident] = {k: found.get(k) for k in ('title', 'description')}
							except (ValueError, KeyError, RuntimeError, TimeoutError) as exc:
								failures.append({'job_id': ident, 'error': str(exc)})
					assets, asset_failures = ([], [])
					if None is not attachments_dir and job.get('attachments'):
						cookies_res = mux.send('Network.getCookies', {'urls': ['https://www.upwork.com']}, session_id=page_sid)
						cookies = cookies_res.get('cookies', []) if isinstance(cookies_res, dict) else []
						# 2026-11-23
						# "Replace getElementById with querySelector in read-only CDP registry and verify on live headless Chromium":
						# https://github.com/dmitry-ai/harness/issues/130
						ua = _eval_session(mux, page_sid, USER_AGENT_EXPR, read_only=True) or 'UpworkOnboarding/2'
						for attachment in job['attachments']:
							try:
								assets.append(download_attachment(attachment, Path(attachments_dir), cookies, ua))
							except (OSError, ValueError, KeyError) as exc:
								asset_failures.append({'filename': attachment.get('fileName'), 'error': str(exc)})
				finally:
					mux.detach_target(page_sid)
			finally:
				if created_temp:
					guard._broker_remove_tab(mux, anchor_tid, ext_tab_id, target_id)
		sands = details.get('sands') or {}
		skills = [child['name'] for group in sands.get('ontologySkills') or [] for child in group.get('children') or [] if child.get('name')]
		skills += [x['name'] for x in sands.get('additionalSkills') or [] if x.get('name')]
		texts = [job.get('description') or ''] + [x.get('description') or '' for x in related.values()]
		return {'schema_version': 2, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'source_tab': {'id': target_id, 'url': target_url, 'temporary': created_temp}, 'job_id': job_id, 'url': canonical_job_url(job_id), 'title': job.get('title') or '', 'description': job.get('description') or '', 'buyer': details.get('buyer') or {}, 'work_history': history, 'open_jobs': open_jobs, 'related_descriptions': related, 'attachments': job.get('attachments') or [], 'saved_attachments': assets, 'questions': [q['question'] for q in job.get('questions') or [] if q.get('question')], 'skills': list(dict.fromkeys(skills)), 'client_names': extract_client_names(history), 'candidate_domains': extract_candidate_domains(texts), 'coverage': {'history_records': len(history), 'history_complete': False, 'scope': 'records embedded in the selected page; no pagination asserted', 'related_failures': failures, 'attachment_failures': asset_failures, 'attachments_downloaded': len(assets), 'cdp_profile': report['profile']}, **{key: job.get(src) for key, src in (('posted_on', 'postedOn'), ('workload', 'workload'), ('duration_label', 'durationLabel'), ('contractor_tier', 'contractorTier'), ('budget', 'budget'), ('extended_budget', 'extendedBudgetInfo'), ('client_activity', 'clientActivity'))}}
