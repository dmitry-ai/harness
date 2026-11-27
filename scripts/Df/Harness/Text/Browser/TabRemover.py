# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class TabRemover:
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__broker_remove_tab()`
	def __init__(self, cdp_sess, anchor_target_id, ext_tab_id, target_id):
		self.__sess = cdp_sess
		self.__anchor_tid = anchor_target_id
		self.__ext_tab_id = ext_tab_id
		self.__target_id = target_id
	# @used-by :meth:`TabRemover.remove()`
	def __close_target(self) -> bool:
		try:
			close_res = self.__sess.send('Target.closeTarget', {'targetId': self.__target_id})
			r = bool(isinstance(close_res, dict) and close_res.get('success', True))
		except Exception:
			r = False
		return r
	# @used-by :meth:`TabRemover.remove()`
	def __remove_via_broker(self) -> bool:
		anchor_sid = None
		try:
			anchor_sid = self.__sess.attach_target(self.__anchor_tid)
			arg = json.dumps({'action': 'removeTab', 'tabId': self.__ext_tab_id})
			res = self.__sess.send('Runtime.evaluate', {'expression': f'globalThis.__harnessBroker({arg})', 'awaitPromise': True, 'returnByValue': True}, session_id=anchor_sid)
			val = res.get('result', {}).get('value') if isinstance(res, dict) else None
			r = bool(isinstance(val, dict) and val.get('ok'))
		except Exception:
			r = False
		finally:
			if anchor_sid:
				self.__sess.detach_target(anchor_sid)
		return r
	# @used-by :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.__broker_remove_tab()`
	def remove(self) -> bool:
		closed = self.__remove_via_broker() if self.__anchor_tid and None is not self.__ext_tab_id else False
		if not closed and self.__target_id:
			closed = self.__close_target()
		return closed
