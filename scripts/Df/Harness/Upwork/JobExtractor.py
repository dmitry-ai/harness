# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from agent_tools.runtime import HARNESS_META, settings
from agent_tools.text_browser import UPWORK_PAGE_STATE_EXPR, USER_AGENT_EXPR
from datetime import datetime, timezone
from Df.Harness.Upwork.AttachmentDownloader import AttachmentDownloader
from Df.Harness.Upwork.ClientMetadataExtractor import ClientMetadataExtractor
from Df.Harness.Upwork.JobUrlParser import JobUrlParser
from Df.Harness.Upwork.PageDecoder import PageDecoder
from Df.Harness.Upwork.TabSelector import TabSelector
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
_JOB_META_FIELDS = (('posted_on', 'postedOn'), ('workload', 'workload'), ('duration_label', 'durationLabel'), ('contractor_tier', 'contractorTier'), ('budget', 'budget'), ('extended_budget', 'extendedBudgetInfo'), ('client_activity', 'clientActivity'))
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class JobExtractor:
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_inspect()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_z_upwork_job_extractor_full_flow()`
	def __init__(self, url_or_id: str, cdp_port: int | None=9222, fetch_related: bool=True, attachments_dir=None, tab_id: str | None=None, *, session_id: str | None=None, config: dict | None=None, http_get=None, cdp_call=None) -> None:
		self.__url_or_id = url_or_id
		self.__cdp_port = cdp_port
		self.__fetch_related = fetch_related
		self.__attachments_dir = attachments_dir
		self.__tab_id = tab_id
		self.__session_id = session_id
		self.__config = config
		self.__http_get = http_get
		self.__cdp_call = cdp_call
	# @used-by :meth:`JobExtractor.__run_mux()`
	def __build_result(self, job_id: str, target: tuple[str, str, bool], details: dict, related: dict, failures: list, assets: list, asset_failures: list, profile: dict) -> dict:
		target_id, target_url, created_temp = target
		job = details.get('job') or {}
		history, open_jobs = (details.get('workHistory') or [], details.get('openJobs') or [])
		sands = details.get('sands') or {}
		skills = [c['name'] for g in sands.get('ontologySkills') or [] for c in g.get('children') or [] if c.get('name')]
		skills += [x['name'] for x in sands.get('additionalSkills') or [] if x.get('name')]
		texts = [job.get('description') or ''] + [x.get('description') or '' for x in related.values()]
		cov = {'history_records': len(history), 'history_complete': False, 'scope': 'records embedded in the selected page; no pagination asserted', 'related_failures': failures, 'attachment_failures': asset_failures, 'attachments_downloaded': len(assets), 'cdp_profile': profile}
		return {'schema_version': 2, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'source_tab': {'id': target_id, 'url': target_url, 'temporary': created_temp}, 'job_id': job_id, 'url': JobUrlParser.canonical_job_url(job_id), 'title': job.get('title') or '', 'description': job.get('description') or '', 'buyer': details.get('buyer') or {}, 'work_history': history, 'open_jobs': open_jobs, 'related_descriptions': related, 'attachments': job.get('attachments') or [], 'saved_attachments': assets, 'questions': [q['question'] for q in job.get('questions') or [] if q.get('question')], 'skills': list(dict.fromkeys(skills)), 'client_names': ClientMetadataExtractor.extract_client_names(history), 'candidate_domains': ClientMetadataExtractor.extract_candidate_domains(texts), 'coverage': cov, **{k: job.get(src) for k, src in _JOB_META_FIELDS}}
	# @used-by :meth:`JobExtractor.__run_mux()`
	def __capture_on_page(self, mux, page_sid: str, job_id: str, created_temp: bool) -> tuple[dict, dict, list, list, list]:
		page = self.__poll_page(mux, page_sid, created_temp)
		details = PageDecoder(page or {}, job_id).decode()
		job = details.get('job') or {}
		related, failures = self.__fetch_related_jobs(mux, page_sid, job_id, details) if self.__fetch_related else ({}, [])
		assets, asset_failures = self.__download_assets(mux, page_sid, job)
		return (details, related, failures, assets, asset_failures)
	# @used-by :meth:`JobExtractor.__resolve_target()`
	def __create_temp_tab(self, guard, mux, anchor_tid, verified_ctx, target_url: str, endpoint: str) -> tuple[str, str | None]:
		params = {'url': target_url, 'background': True, 'hidden': True}
		if verified_ctx:
			params['browserContextId'] = verified_ctx
		ext_tab_id = None
		try:
			res = mux.send('Target.createTarget', params)
			target_id = res.get('targetId') if isinstance(res, dict) else None
		except RuntimeError as exc:
			if not verified_ctx or not anchor_tid:
				raise PermissionError('No open Upwork job tab in Default and cannot open background tab while another Chrome profile is focused without M-2A extension') from exc
			target_id, ext_tab_id = guard._broker_create_tab(mux, anchor_tid, verified_ctx, target_url, endpoint)
		if not isinstance(target_id, str) or not target_id:
			raise RuntimeError('Failed to open temporary Upwork tab in verified Default profile')
		return (target_id, ext_tab_id)
	# @used-by :meth:`JobExtractor.__capture_on_page()`
	def __download_assets(self, mux, page_sid: str, job: dict) -> tuple[list, list]:
		assets, failures = ([], [])
		if None is not self.__attachments_dir and job.get('attachments'):
			cookies_res = mux.send('Network.getCookies', {'urls': ['https://www.upwork.com']}, session_id=page_sid)
			cookies = cookies_res.get('cookies', []) if isinstance(cookies_res, dict) else []
			ua = self.eval_session(mux, page_sid, USER_AGENT_EXPR, read_only=True) or 'UpworkOnboarding/2'
			for attachment in job['attachments']:
				try:
					assets.append(AttachmentDownloader(attachment, Path(self.__attachments_dir), cookies, ua).download())
				except (OSError, ValueError, KeyError) as exc:
					failures.append({'filename': attachment.get('fileName'), 'error': str(exc)})
		return (assets, failures)
	# @used-by :meth:`JobExtractor.__capture_on_page()`
	def __fetch_related_jobs(self, mux, page_sid: str, job_id: str, details: dict) -> tuple[dict, list]:
		ids = {(x.get('jobInfo') or {}).get('ciphertext') for x in details.get('workHistory') or []}
		ids |= {x.get('ciphertext') for x in details.get('openJobs') or []}
		related, failures = ({}, [])
		for raw_id in sorted(ids - {None, job_id}):
			ident = JobUrlParser.normalize_job_id(raw_id)
			rel_url = JobUrlParser.canonical_job_url(ident).replace('https://upwork.com', 'https://www.upwork.com')
			expr = f'(async()=>{{const r=await fetch({json.dumps(rel_url)},{{credentials:"include",signal:AbortSignal.timeout(20000)}});if(!r.ok)throw new Error("HTTP "+r.status);const d=new DOMParser().parseFromString(await r.text(),"text/html");return d.querySelector("#__NUXT_DATA__")?.textContent||"";}})()'
			try:
				text = self.eval_session(mux, page_sid, expr, await_promise=True, timeout_ms=25000)
				found = JobUrlParser.resolve_nuxt_devalue(json.loads(text))['vuex']['jobDetails']['job']
				if found.get('ciphertext') != ident:
					raise ValueError('Related job identity mismatch')
				related[ident] = {k: found.get(k) for k in ('title', 'description')}
			except (ValueError, KeyError, RuntimeError, TimeoutError) as exc:
				failures.append({'job_id': ident, 'error': str(exc)})
		return (related, failures)
	# @used-by :meth:`JobExtractor.__capture_on_page()`
	def __poll_page(self, mux, page_sid: str, created_temp: bool):
		page = None
		wait_until = time.time() + (15.0 if created_temp and None is self.__cdp_call else 0.0)
		while True:
			page = self.eval_session(mux, page_sid, UPWORK_PAGE_STATE_EXPR, read_only=True)
			if isinstance(page, dict) and (page.get('nuxt') or 'complete' == page.get('readyState')) or time.time() >= wait_until:
				break
			time.sleep(0.35)
		return page
	# @used-by :meth:`JobExtractor.__run_mux()`
	def __resolve_target(self, guard, mux, raw_tabs: list, verified_ctx, anchor_tid, job_id: str, endpoint: str):
		from agent_tools.text_browser import _checked_ws, _query_target_infos
		infos = _query_target_infos(mux, raw_tabs)
		ctx_by_id = {(ti.get('targetId') or ti.get('id')): ti.get('browserContextId') for ti in infos if isinstance(ti, dict)}
		if self.__tab_id and verified_ctx and (ctx_by_id.get(self.__tab_id) != verified_ctx):
			raise PermissionError('Selected tab belongs to a secondary Chrome profile (browserContextId mismatch)')
		verified_tabs = [t for t in raw_tabs if isinstance(t, dict) and (not verified_ctx or ctx_by_id.get(t.get('id')) == verified_ctx)]
		target_url = JobUrlParser.canonical_job_url(job_id).replace('https://upwork.com', 'https://www.upwork.com')
		try:
			sel = TabSelector(verified_tabs, job_id, self.__tab_id).select()
			fb_ws = _checked_ws(sel['webSocketDebuggerUrl'], endpoint) if sel.get('webSocketDebuggerUrl') else None
			r = (sel['id'], sel['url'], False, None, fb_ws)
		except ValueError:
			if self.__tab_id:
				raise
			tid, ext_tid = self.__create_temp_tab(guard, mux, anchor_tid, verified_ctx, target_url, endpoint)
			r = (tid, target_url, True, ext_tid, None)
		return r
	# @used-by :meth:`JobExtractor.extract()`
	def __run_mux(self, guard, report: dict, job_id: str, cfg: dict) -> dict:
		from agent_tools.text_browser import CDPSession, discover_cdp_browser
		endpoint = report['endpoint']
		if None is not self.__cdp_port and urlsplit(endpoint).port != int(self.__cdp_port):
			raise PermissionError(f'Requested CDP port {self.__cdp_port} differs from verified primary session endpoint {endpoint}')
		_, raw_tabs, browser_ws = discover_cdp_browser(endpoint, guard.get)
		verified_ctx, anchor_tid = (report['profile'].get('browser_context_id'), report['profile'].get('anchor_target_id'))
		with CDPSession(browser_ws, cfg, cdp_call=self.__cdp_call) as mux:
			target_id, target_url, created_temp, ext_tab_id, fb_ws = self.__resolve_target(guard, mux, raw_tabs, verified_ctx, anchor_tid, job_id, endpoint)
			try:
				page_sid = mux.attach_target(target_id, fallback_ws=fb_ws)
				try:
					details, related, failures, assets, asset_failures = self.__capture_on_page(mux, page_sid, job_id, created_temp)
				finally:
					mux.detach_target(page_sid)
			finally:
				if created_temp:
					guard._broker_remove_tab(mux, anchor_tid, ext_tab_id, target_id)
		return self.__build_result(job_id, (target_id, target_url, created_temp), details, related, failures, assets, asset_failures, report['profile'])
	# @used-by :func:`agent_tools.upwork_extract._eval_session()`
	# @used-by :meth:`JobExtractor.__download_assets()`
	# @used-by :meth:`JobExtractor.__fetch_related_jobs()`
	# @used-by :meth:`JobExtractor.__poll_page()`
	@staticmethod
	def eval_session(mux, session_id: str, expression: str, *, await_promise: bool=False, read_only: bool=False, timeout_ms: int=25000):
		params = {'expression': expression, 'returnByValue': True}
		if await_promise:
			params['awaitPromise'] = True
		if read_only:
			params['throwOnSideEffect'] = True
		result = mux.send('Runtime.evaluate', params, session_id=session_id, timeout_ms=timeout_ms)
		if not isinstance(result, dict) or result.get('exceptionDetails'):
			raise RuntimeError(f"Browser evaluation failed: {(result or {}).get('exceptionDetails')}")
		return result.get('result', {}).get('value')
	# @used-by :func:`agent_tools.upwork_extract.extract_upwork_job()`
	# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__cmd_inspect()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_z_upwork_job_extractor_full_flow()`
	def extract(self) -> dict:
		from agent_tools.text_browser import GuardedCDP, preflight
		job_id = JobUrlParser.normalize_job_id(self.__url_or_id)
		cfg = settings() if None is self.__config else self.__config
		sid = self.__session_id or cfg.get('text', {}).get('browser', {}).get('primary_session_id')
		if not isinstance(sid, str) or sid not in cfg.get('text', {}).get('browser', {}).get('sessions', {}):
			raise PermissionError('Configure text.browser.sessions primary session in runtime.json before Upwork CDP extraction')
		guard_root = HARNESS_META if HARNESS_META.is_dir() else Path.cwd()
		guard = GuardedCDP(guard_root, {'session_id': sid}, config=cfg, http_get=self.__http_get, cdp_call=self.__cdp_call)
		with guard._lock():
			report = preflight({'session_id': sid}, config=cfg, http_get=guard.get, cdp_call=self.__cdp_call, require_target=False)
			if not report['valid']:
				raise PermissionError('; '.join(report['issues']) or 'Primary Chrome profile Default could not be verified')
			r = self.__run_mux(guard, report, job_id, cfg)
		return r
