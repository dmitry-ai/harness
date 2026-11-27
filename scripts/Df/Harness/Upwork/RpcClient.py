# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import asyncio
import json
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class RpcClient:
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	# @used-by :meth:`test_onboarding.RPCTests.test_events_and_unrelated_responses_do_not_complete_call()`
	# @used-by :meth:`test_onboarding.RPCTests.test_unresponsive_browser_has_bounded_diagnostic()`
	def __init__(self, websocket, timeout: int=30) -> None:
		self.websocket, self.timeout, self.next_id = (websocket, timeout, 0)
	# @used-by :meth:`RpcClient.evaluate()`
	# @used-by :meth:`test_onboarding.RPCTests.test_events_and_unrelated_responses_do_not_complete_call()`
	# @used-by :meth:`test_onboarding.RPCTests.test_unresponsive_browser_has_bounded_diagnostic()`
	async def call(self, method: str, **params):
		self.next_id += 1
		ident = self.next_id
		await self.websocket.send(json.dumps({'id': ident, 'method': method, 'params': params}))
		# @used-by :meth:`RpcClient.call()`
		async def receive():
			while True:
				message = json.loads(await self.websocket.recv())
				if message.get('id') == ident:
					if 'error' in message:
						raise RuntimeError(f"CDP {method}: {message['error']}")
					return message['result']
		try:
			r = await asyncio.wait_for(receive(), timeout=self.timeout)
		except TimeoutError as exc:
			raise TimeoutError(f'CDP {method} did not respond within {self.timeout}s') from exc
		return r
	# @used-by :meth:`test_df_harness_s11_wave2a_upwork.DfHarnessS11Wave2aUpworkTests.test_upwork_extract_classes()`
	async def evaluate(self, expression: str):
		result = await self.call('Runtime.evaluate', expression=expression, awaitPromise=True, returnByValue=True)
		if result.get('exceptionDetails'):
			raise RuntimeError(f"Browser evaluation failed: {result['exceptionDetails']}")
		return result.get('result', {}).get('value')
