# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from fnmatch import fnmatchcase
import subprocess
from urllib.error import URLError
from urllib.parse import urlsplit
from Df.Harness.Text.Browser.CdpSession import CdpSession
from Df.Harness.lib.browser import dfh_argument_values, dfh_checked_ws, dfh_discover_cdp_browser, dfh_endpoint, dfh_endpoint_with_meta, dfh_http_json, dfh_normal_path, dfh_probe_cdp_arguments, dfh_profile, dfh_query_target_infos, dfh_session, dfh_transport
from agent_tools.runtime import settings
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class PreflightChecker:
	# @used-by :func:`agent_tools.text_browser.preflight()`
	# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.check()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__check()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__refresh_owned()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.create_target()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_preflight_guarded_cdp_tab_broker_and_collectors()`
	def __init__(self, spec, *, config=None, http_get=None, cdp_call=None, require_target=True, cdp_session=None):
		self.__spec = spec
		self.__config = settings() if None is config else config
		self.__http_get = http_get
		self.__cdp_call = cdp_call
		self.__require_target = require_target
		self.__cdp_session = cdp_session
	# @used-by :meth:`PreflightChecker.__run_checks()`
	def __check_account(self, session: dict, call, report: dict) -> None:
		account = session.get('account')
		if None is not account:
			if not isinstance(account, dict) or not isinstance(account.get('expected'), str) or (not account['expected']) or (not isinstance(account.get('expression'), str)) or (not account['expression']):
				raise ValueError('Configured account needs expected identity and a specific read-only observation expression')
			report['account']['expected'] = account['expected']
			if 'verified' == report['profile']['status'] and 'verified' == report['target']['status']:
				self.__probe_account(account, report['target']['websocket_url'], call, report)
			if 'verified' != report['account']['status']:
				report['issues'].append('Observed account is unknown or differs from the authorized account')
	# @used-by :meth:`PreflightChecker.__check_cmdline()`
	def __check_additional_args(self, arguments: list, constraints, report: dict) -> None:
		if not isinstance(constraints, dict):
			raise ValueError('Profile additional_arguments must map observed flags to expected values')
		details = []
		for flag, expected_value in constraints.items():
			if not isinstance(flag, str) or not flag.startswith('--') or (not isinstance(expected_value, str)):
				raise ValueError('Profile additional_arguments needs string flags and values')
			actual_values = dfh_argument_values(arguments, flag)
			status = 'unknown' if not actual_values else 'verified' if actual_values == [expected_value] else 'mismatch'
			details.append({'argument': flag, 'expected': expected_value, 'observed': actual_values, 'status': status})
			if 'verified' != status:
				report['profile']['status'] = status
				report['issues'].append(f'Additional profile argument {flag} is {status}')
		if details:
			report['profile']['additional_arguments'] = details
	# @used-by :meth:`PreflightChecker.__run_checks()`
	def __check_cmdline(self, browser_ws: str, call, expected: str, argument: str, prof_cfg: dict, needs_iso: bool, report: dict):
		r = None
		try:
			arguments = dfh_probe_cdp_arguments(browser_ws, call)
			values = dfh_argument_values(arguments, argument)
			if not values:
				report['issues'].append('Expected profile argument is absent from the native browser command line')
			elif 1 != len({dfh_normal_path(v) for v in values}):
				report['profile']['status'] = 'mismatch'
				report['issues'].append('Native browser command line has conflicting profile arguments')
			else:
				report['profile'].update(observed=values[0], evidence_method='Browser.getBrowserCommandLine', status='verified' if dfh_normal_path(values[0]) == dfh_normal_path(expected) else 'mismatch')
				if 'mismatch' == report['profile']['status']:
					report['issues'].append('Observed profile does not match the authorized profile')
			self.__check_additional_args(arguments, prof_cfg.get('additional_arguments', {}), report)
		except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
			r = exc
			if not needs_iso:
				report['issues'].append('Profile cannot be verified: ' + str(exc))
		return r
	# @used-by :meth:`PreflightChecker.__run_checks()`
	def __check_context_isolation(self, prof_cfg: dict, browser_ws: str, targets: list, endpoint: str, used_active_port: bool, active_ws_path: str | None, cmdline_exc, report: dict) -> list:
		r = []
		if None is not cmdline_exc and used_active_port and active_ws_path and (urlsplit(browser_ws).path != active_ws_path):
			report['profile']['status'] = 'mismatch'
			report['issues'].append('DevToolsActivePort websocket path does not match discovered browser endpoint')
		else:
			if 'verified' == report['profile']['status']:
				report['profile']['status'] = 'unknown'
			with self.__mux(browser_ws) as mux:
				r = dfh_query_target_infos(mux, targets)
				self.__verify_context_anchor(prof_cfg, r, targets, endpoint, mux, report)
				if 'verified' == report['profile']['status'] and None is not cmdline_exc and used_active_port:
					report['profile']['devtools_active_port_verified'] = True
		return r
	# @used-by :meth:`PreflightChecker.__verify_context_anchor()`
	def __check_extension_anchor(self, ext_id: str, target_infos: list, report: dict) -> bool:
		prefix = f'chrome-extension://{ext_id.strip()}/'
		ext_targets = [t for t in target_infos if str(t.get('url') or '').startswith(prefix)]
		ext_contexts = {t.get('browserContextId') for t in ext_targets if isinstance(t.get('browserContextId'), str) and t.get('browserContextId')}
		if 1 < len(ext_contexts):
			report['profile']['status'] = 'mismatch'
			report['issues'].append('Anchor extension is loaded in multiple browser contexts; load it exclusively in Default')
			r = True
		elif 1 == len(ext_contexts):
			chosen = next((t for t in ext_targets if t.get('url') == prefix + 'offscreen.html'), ext_targets[0])
			report['profile'].update(status='verified', evidence_method='M-2A:extension-offscreen-anchor', browser_context_id=next(iter(ext_contexts)), anchor_target_id=chosen.get('targetId') or chosen.get('id'), extension_id=ext_id.strip())
			r = True
		else:
			r = False
		return r
	# @used-by :meth:`PreflightChecker.__verify_context_anchor()`
	def __check_sentinel_origin(self, sentinel_origin: str, sentinel_cookie: str, target_infos: list, targets: list, endpoint: str, cdp_sess, report: dict) -> bool:
		origin = sentinel_origin.strip().rstrip('/')
		ws_by_id = {t.get('id'): t.get('webSocketDebuggerUrl') for t in (targets or []) if isinstance(t, dict) and t.get('id') and t.get('webSocketDebuggerUrl')}
		by_ctx: dict[str, list[str]] = {}
		for t in target_infos:
			tid, ctx = (t.get('targetId') or t.get('id'), t.get('browserContextId'))
			if 'page' == t.get('type') and isinstance(tid, str) and tid and isinstance(ctx, str) and ctx and (not str(t.get('url') or '').startswith('devtools://')):
				by_ctx.setdefault(ctx, []).append(tid)
		matched = {ctx_id for ctx_id, page_ids in by_ctx.items() if self.__probe_context_pages(origin, sentinel_cookie, page_ids, ws_by_id, endpoint, cdp_sess)}
		if 1 < len(matched):
			report['profile']['status'] = 'mismatch'
			report['issues'].append('Sentinel origin marker found in multiple browser contexts')
			r = True
		elif 1 == len(matched):
			report['profile'].update(status='verified', evidence_method='M-2B:sentinel-origin', browser_context_id=next(iter(matched)), sentinel_origin=origin)
			r = True
		else:
			r = False
		return r
	# @used-by :meth:`PreflightChecker.__run_checks()`
	def __check_target(self, session: dict, targets: list, target_infos: list, endpoint: str, report: dict) -> None:
		identifier = self.__spec.get('target_id')
		matches = [item for item in targets if isinstance(item, dict) and item.get('id') == identifier]
		if not self.__require_target and (not isinstance(identifier, str) or not identifier):
			report['target'] = {'status': 'omitted'}
		elif not isinstance(identifier, str) or not identifier or 1 != len(matches):
			report['issues'].append('Select one explicit current target_id; no arbitrary target is chosen')
		else:
			target, patterns = (matches[0], session.get('target_url_patterns', []))
			report['target'] = {key: target.get(key) for key in ('id', 'type', 'url', 'title')}
			report['target']['status'] = 'mismatch'
			self.__validate_target_fields(target, patterns, identifier, target_infos, endpoint, report)
	# @used-by :meth:`PreflightChecker.__run_checks()`
	def __discover(self, session: dict, get):
		endpoint, active_ws_path, used_active_port = dfh_endpoint_with_meta(session)
		try:
			version, targets, browser_ws = dfh_discover_cdp_browser(endpoint, get)
		except (URLError, OSError, ValueError):
			fb_ep = session.get('fallback_endpoint')
			if not (used_active_port and fb_ep and fb_ep.rstrip('/') != endpoint):
				raise
			endpoint = dfh_endpoint({'endpoint': fb_ep})
			active_ws_path, used_active_port = (None, False)
			version, targets, browser_ws = dfh_discover_cdp_browser(endpoint, get)
		return (endpoint, active_ws_path, used_active_port, version, targets, browser_ws)
	# @used-by :meth:`PreflightChecker.__check_context_isolation()`
	@contextmanager
	def __mux(self, browser_ws: str):
		if None is not self.__cdp_session:
			yield self.__cdp_session
		else:
			with CdpSession(browser_ws, self.__config, cdp_call=self.__cdp_call) as opened:
				yield opened
	# @used-by :meth:`PreflightChecker.__probe_sentinel_page()`
	def __page_has_marker(self, origin: str, sentinel_cookie: str, sid: str, cdp_sess) -> bool:
		quota = cdp_sess.send('Storage.getUsageAndQuota', {'origin': origin}, session_id=sid)
		usage = quota.get('usage', 0) if isinstance(quota, dict) else 0
		r = isinstance(usage, (int, float)) and 0 < usage
		if not r:
			ck_res = cdp_sess.send('Network.getCookies', {'urls': [origin + '/']}, session_id=sid)
			cks = ck_res.get('cookies') if isinstance(ck_res, dict) else []
			r = isinstance(cks, list) and any((isinstance(c, dict) and c.get('name') == sentinel_cookie for c in cks))
		return r
	# @used-by :meth:`PreflightChecker.__check_account()`
	def __probe_account(self, account: dict, target_ws: str, call, report: dict) -> None:
		try:
			native = call(target_ws, 'Runtime.evaluate', {'expression': account['expression'], 'throwOnSideEffect': True, 'returnByValue': True})
			if not isinstance(native, dict) or native.get('exceptionDetails'):
				raise ValueError('Native account observation did not complete without side effects')
			value = native.get('result', {}).get('value')
			report['account'].update(observed=value, status='unknown' if not isinstance(value, str) or not value else 'verified' if value == account['expected'] else 'mismatch', evidence_method='Runtime.evaluate(throwOnSideEffect:true)', limitation='This establishes only the configured application account marker, not server authorization internals')
		except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
			report['issues'].append('Account cannot be verified: ' + str(exc))
	# @used-by :meth:`PreflightChecker.__check_sentinel_origin()`
	def __probe_context_pages(self, origin: str, sentinel_cookie: str, page_ids: list[str], ws_by_id: dict, endpoint: str, cdp_sess) -> bool:
		r = False
		for pid in page_ids:
			probed = self.__probe_sentinel_page(origin, sentinel_cookie, pid, ws_by_id, endpoint, cdp_sess)
			if None is not probed:
				r = probed
				break
		return r
	# @used-by :meth:`PreflightChecker.__probe_context_pages()`
	def __probe_sentinel_page(self, origin: str, sentinel_cookie: str, pid: str, ws_by_id: dict, endpoint: str, cdp_sess) -> bool | None:
		fb_ws = None
		if pid in ws_by_id:
			try:
				fb_ws = dfh_checked_ws(ws_by_id[pid], endpoint)
			except ValueError:
				fb_ws = None
		sid = None
		try:
			sid = cdp_sess.attach_target(pid, fallback_ws=fb_ws)
			r: bool | None = self.__page_has_marker(origin, sentinel_cookie, sid, cdp_sess)
		except Exception:
			r = None
		finally:
			if sid:
				cdp_sess.detach_target(sid)
		return r
	# @used-by :meth:`PreflightChecker.check()`
	def __run_checks(self, report: dict) -> None:
		session = dfh_session(self.__spec, self.__config)
		report['surface'] = session['surface']
		endpoint, active_ws_path, used_active_port, version, targets, browser_ws = self.__discover(session, self.__http_get or dfh_http_json)
		call = dfh_transport(self.__config, self.__cdp_call)
		report.update(endpoint=endpoint, browser={'product': version.get('Browser'), 'websocket_url': browser_ws}, inventory=[{key: item.get(key) for key in ('id', 'type', 'url', 'title')} for item in targets if isinstance(item, dict)])
		expected, argument = dfh_profile(session, self.__config)
		prof_cfg = session.get('profile', {})
		needs_iso = bool(prof_cfg.get('extension_id') or prof_cfg.get('sentinel_origin'))
		report['profile'].update(expected=expected, argument=argument)
		cmdline_exc = self.__check_cmdline(browser_ws, call, expected, argument, prof_cfg, needs_iso, report)
		target_infos = self.__check_context_isolation(prof_cfg, browser_ws, targets, endpoint, used_active_port, active_ws_path, cmdline_exc, report) if needs_iso and 'mismatch' != report['profile']['status'] else []
		self.__check_target(session, targets, target_infos, endpoint, report)
		self.__check_account(session, call, report)
		target_ok = 'verified' == report['target']['status'] if self.__require_target else report['target']['status'] in ('verified', 'omitted')
		report['valid'] = 'verified' == report['profile']['status'] and target_ok and (not report['issues'])
	# @used-by :meth:`PreflightChecker.__validate_target_fields()`
	def __target_error(self, target: dict, patterns: list) -> str | None:
		if 'page' != target.get('type'):
			r: str | None = 'Selected target is not a shell/browser page'
		elif not patterns or not all((isinstance(p, str) and p for p in patterns)):
			r = 'Session needs explicit target_url_patterns'
		elif not any((fnmatchcase(target.get('url', ''), p) for p in patterns)):
			r = 'Current target URL is outside the authorized session patterns'
		elif None is not self.__spec.get('target_url') and target.get('url') != self.__spec['target_url']:
			r = 'Current target URL differs from the explicitly selected URL'
		else:
			r = None
		return r
	# @used-by :meth:`PreflightChecker.__check_target()`
	def __validate_target_fields(self, target: dict, patterns: list, identifier: str, target_infos: list, endpoint: str, report: dict) -> None:
		err = self.__target_error(target, patterns)
		if None is not err:
			report['issues'].append(err)
		else:
			verified_ctx = report['profile'].get('browser_context_id')
			actual_ctx = None
			if verified_ctx:
				t_info = next((ti for ti in target_infos if (ti.get('targetId') or ti.get('id')) == identifier), None)
				actual_ctx = (t_info or {}).get('browserContextId') or target.get('browserContextId')
			if verified_ctx and actual_ctx != verified_ctx:
				report['issues'].append('Selected target belongs to a secondary browser profile (browserContextId mismatch)')
			else:
				self.__verify_target_ws(target, endpoint, actual_ctx if verified_ctx else None, report)
	# @used-by :meth:`PreflightChecker.__check_context_isolation()`
	def __verify_context_anchor(self, prof_cfg: dict, target_infos: list, targets: list, endpoint: str, cdp_sess, report: dict) -> None:
		ext_id = prof_cfg.get('extension_id')
		sentinel_origin = prof_cfg.get('sentinel_origin')
		sentinel_cookie = prof_cfg.get('sentinel_cookie_name') or '__harness_primary_profile'
		handled = isinstance(ext_id, str) and bool(ext_id.strip()) and self.__check_extension_anchor(ext_id, target_infos, report)
		if not handled and isinstance(sentinel_origin, str) and sentinel_origin.strip():
			handled = self.__check_sentinel_origin(sentinel_origin, sentinel_cookie, target_infos, targets, endpoint, cdp_sess, report)
		if not handled and 'verified' != report['profile'].get('status'):
			report['issues'].append('Primary Chrome profile Default could not be verified via M-2A offscreen extension anchor or M-2B sentinel origin')
	# @used-by :meth:`PreflightChecker.__validate_target_fields()`
	def __verify_target_ws(self, target: dict, endpoint: str, actual_ctx: str | None, report: dict) -> None:
		target_ws = dfh_checked_ws(target.get('webSocketDebuggerUrl'), endpoint)
		if not urlsplit(target_ws).path.startswith('/devtools/page/'):
			raise ValueError('Selected target has no page websocket')
		extra = {'browser_context_id': actual_ctx} if None is not actual_ctx else {}
		report['target'].update(status='verified', websocket_url=target_ws, **extra)
	# @used-by :func:`agent_tools.text_browser.preflight()`
	# @used-by :meth:`Df.Harness.Text.Browser.AnchorStatusChecker.AnchorStatusChecker.check()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__check()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__refresh_owned()`
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.create_target()`
	# @used-by :meth:`test_df_harness_s11_wave2c_browser.DfHarnessS11Wave2CBrowserTests.test_preflight_guarded_cdp_tab_broker_and_collectors()`
	def check(self) -> dict:
		report = {'schema_version': 1, 'session_id': self.__spec.get('session_id'), 'valid': False, 'profile': {'status': 'unknown'}, 'target': {'status': 'unknown'}, 'account': {'status': 'unknown'}, 'issues': [], 'independent_http_allowed': True, 'limitation': 'Cooperative check of the configured live CDP endpoint; it does not prove server internals, model reading, or ownership of external calls'}
		try:
			self.__run_checks(report)
		except (ValueError, OSError, RuntimeError, TypeError, KeyError, IndexError) as exc:
			report['issues'].append(str(exc))
		return report
