# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
import time
import uuid
from Df.Harness.lib.browser import dfh_query_target_infos
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class TabCreator:
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__broker_create_tab()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_browser.DfHarnessS11Wave2CCovBrowserTests.test_guarded_cdp_create_select_call_and_tab_broker()`
	def __init__(self, cdp_sess, get, anchor_target_id, verified_ctx, url, endpoint):
		self.__sess = cdp_sess
		self.__get = get
		self.__anchor_tid = anchor_target_id
		self.__ctx = verified_ctx
		self.__url = url
		self.__endpoint = endpoint
	# @used-by :meth:`TabCreator.create()`
	def __cleanup_tab(self, anchor_sid: str, ext_tab_id) -> None:
		if None is not ext_tab_id:
			try:
				arg = json.dumps({'action': 'removeTab', 'tabId': ext_tab_id})
				self.__sess.send('Runtime.evaluate', {'expression': f'globalThis.__harnessBroker({arg})', 'awaitPromise': True, 'returnByValue': True}, session_id=anchor_sid)
			except Exception:
				pass
	# @used-by :meth:`TabCreator.create()`
	def __navigate(self, target_id: str) -> None:
		page_sid = self.__sess.attach_target(target_id)
		try:
			self.__sess.send('Page.navigate', {'url': self.__url}, session_id=page_sid)
		finally:
			self.__sess.detach_target(page_sid)
	# @used-by :meth:`TabCreator.create()`
	def __wait_target_id(self, placeholder: str) -> str:
		target_id, deadline = (None, time.time() + 5.0)
		while time.time() < deadline:
			infos = dfh_query_target_infos(self.__sess, self.__get(self.__endpoint + '/json/list'))
			matches = [ti for ti in infos if 'page' == ti.get('type') and ti.get('browserContextId') == self.__ctx and (ti.get('url') == placeholder)]
			if 1 == len(matches):
				target_id = matches[0].get('targetId') or matches[0].get('id')
				break
			time.sleep(0.05)
		if not isinstance(target_id, str) or not target_id:
			raise RuntimeError('M-2A broker created tab could not be uniquely correlated in Target.getTargets')
		return target_id
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__broker_create_tab()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_browser.DfHarnessS11Wave2CCovBrowserTests.test_guarded_cdp_create_select_call_and_tab_broker()`
	def create(self):
		placeholder = f'about:blank#{uuid.uuid4().hex}'
		anchor_sid, ext_tab_id = (self.__sess.attach_target(self.__anchor_tid), None)
		try:
			arg = json.dumps({'action': 'createBackgroundTab', 'url': placeholder})
			eval_res = self.__sess.send('Runtime.evaluate', {'expression': f'globalThis.__harnessBroker({arg})', 'awaitPromise': True, 'returnByValue': True}, session_id=anchor_sid)
			broker_val = eval_res.get('result', {}).get('value') if isinstance(eval_res, dict) and (not eval_res.get('exceptionDetails')) else None
			if not isinstance(broker_val, dict) or not broker_val.get('ok'):
				raise PermissionError((broker_val or {}).get('error') or 'M-2A anchor extension broker failed to create background tab')
			ext_tab_id = broker_val.get('tabId')
			target_id = self.__wait_target_id(placeholder)
			self.__navigate(target_id)
			r = (target_id, ext_tab_id)
		except Exception:
			self.__cleanup_tab(anchor_sid, ext_tab_id)
			raise
		finally:
			self.__sess.detach_target(anchor_sid)
		return r
