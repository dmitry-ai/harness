# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag
from Df.Harness.Research.Collector import Collector
from Df.Harness.Research.Extractor import Extractor
from Df.Harness.Research.Response import Response
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class DomCapturer:
	# @used-by :func:`agent_tools.research.capture_dom()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_dom_capturer_and_network_link_checker_fetch()`
	def __init__(self, root, url: str, tab_id: str, *, session_id=None, refresh_reason=None, context=None, config=None, guard=None) -> None:
		self.__root = root
		self.__url = url
		self.__tab_id = tab_id
		self.__session_id = session_id
		self.__refresh_reason = refresh_reason
		self.__context = context
		self.__config = config
		self.__guard = guard
	# @used-by :meth:`DomCapturer.capture()`
	def __read_dom(self, guard, identity: dict, target: str) -> Response:
		from Df.Harness.lib.browser import MINIMAL_DOM_CAPTURE_EXPR
		native, actual = guard.call('Runtime.evaluate', {'expression': MINIMAL_DOM_CAPTURE_EXPR, 'throwOnSideEffect': True, 'returnByValue': True}, include_identity=True)
		if actual['browser']['websocket_url'] != identity['browser']['websocket_url'] or actual['profile'] != identity['profile'] or actual['account'] != identity['account'] or (actual['target']['id'] != self.__tab_id):
			raise ValueError('CDP identity changed during DOM capture; no content proof is issued')
		if not isinstance(native, dict) or native.get('exceptionDetails'):
			raise ValueError('Native DOM evaluation did not complete without side effects')
		data = native.get('result', {}).get('value')
		if not isinstance(data, dict) or not isinstance(data.get('html'), str) or urldefrag(data.get('url', ''))[0] != urldefrag(target)[0]:
			raise ValueError('Tab navigated or DOM capture does not match the intended resource')
		return Response(data['url'], 0, 'text/html', data['html'].encode('utf-8'))
	# @used-by :meth:`DomCapturer.capture()`
	def __resolve_guard(self):
		from Df.Harness.Text.Browser.GuardedCdp import GuardedCdp
		if not isinstance(self.__session_id, str) or not self.__session_id or (not isinstance(self.__tab_id, str)) or (not self.__tab_id):
			raise ValueError('Explicit authorized CDP session_id and exact tab ID required')
		if None is self.__guard:
			guard = GuardedCdp(self.__root, {'session_id': self.__session_id, 'target_id': self.__tab_id}, config=self.__config)
		elif not isinstance(self.__guard, GuardedCdp) or self.__guard.root != Path(self.__root).resolve():
			raise ValueError('DOM reader needs a GuardedCDP instance for this exact project')
		else:
			guard = self.__guard
		if guard.spec.get('session_id') != self.__session_id or guard.spec.get('target_id') != self.__tab_id:
			raise ValueError('DOM session/target differs from the explicitly selected guard')
		return guard
	# @used-by :func:`agent_tools.research.capture_dom()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_research.DfHarnessS11Wave2CCovResearchTests.test_dom_capturer_and_network_link_checker_fetch()`
	# @uses :meth:`Df.Harness.Text.Browser.GuardedCdp.GuardedCdp.inspect()`
	def capture(self) -> dict:
		from Df.Harness.lib.browser import dfh_save_cdp_identity
		guard = self.__resolve_guard()
		identity = guard.inspect()
		if urldefrag(identity['target'].get('url', ''))[0] != urldefrag(self.__url)[0]:
			raise ValueError('Explicit tab ID must match the requested URL; no navigation or account fallback')
		id_ref, id_hash = dfh_save_cdp_identity(self.__root, {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(timespec='microseconds'), 'session_id': self.__session_id, 'target_id': self.__tab_id, 'browser_websocket': identity['browser']['websocket_url'], 'profile': identity['profile'], 'account': identity['account']})
		obs_ctx = dict(self.__context or {})
		obs_ctx.setdefault('session_id', self.__session_id)
		obs = Collector(self.__root, self.__url, scope=f'CDP-session:{self.__session_id}:tab:{self.__tab_id}:identity:{id_ref}', max_age=0, refresh_reason=self.__refresh_reason, fetcher=lambda target, _h, _t: self.__read_dom(guard, identity, target), observation_kind='dom', context=obs_ctx, extra_meta={'cdp_identity': id_ref, 'cdp_identity_sha256': id_hash}).collect()
		extra = {} if obs['error'] else Extractor.extract_observation(self.__root, obs['observation'])
		return {**obs, **extra, 'cdp_identity': id_ref, 'cdp_identity_sha256': id_hash}
