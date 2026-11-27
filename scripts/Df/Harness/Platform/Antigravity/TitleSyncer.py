# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.lib.ag_daemon import dfh_discover_live_daemon, dfh_read_current_conversation_title
from Df.Harness.lib.ag_inputs import dfh_antigravity_paths
from Df.Harness.lib.shadow_hooks import SHADOW_TITLE_HOOK
import json
import re
import ssl
import urllib.error
import urllib.request
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class TitleSyncer:
	# @used-by :func:`Df.Harness.lib.completion_core._run_ag_title_sync()`
	# @used-by :func:`agent_tools.platforms.antigravity.update_conversation_title()`
	def __init__(self, conversation_id: str, title: str, *, backend=None, instance=None, paths=None, timeout: float=2.0, _ops: dict[str, Any] | None=None) -> None:
		self.__conversation_id = conversation_id
		self.__title = title
		self.__backend = backend
		self.__instance = instance
		self.__paths = paths
		self.__timeout = timeout
		self.__ops = _ops or {}
	# @used-by :meth:`TitleSyncer.run()`
	def __post_endpoints(self, daemon: dict, cid: str, clean_title: str, db_title: str | None, ann_title: str | None) -> dict[str, Any]:
		payload = json.dumps({'cascadeIds': [cid], 'annotations': {'title': clean_title}, 'mergeAnnotations': True}, ensure_ascii=False).encode('utf-8')
		headers = {'content-type': 'application/json', 'x-codeium-csrf-token': daemon['csrf_token'], 'connect-protocol-version': '1'}
		endpoints = [(s, daemon[k]) for s, k in (('http', 'http_port'), ('https', 'https_port')) if None is not daemon.get(k)]
		r: dict[str, Any] | None = None
		last_error = ''
		for scheme, port in endpoints:
			ok, err = self.__send_one(scheme, port, payload, headers)
			if ok:
				r = {'synced': True, 'changed': True, 'title': clean_title, 'previous_title': ann_title if None is not ann_title else (db_title or ''), 'conversation_id': cid, 'endpoint_scheme': scheme, 'endpoint_port': port, 'daemon_pid': daemon['pid']}
				break
			last_error = err
		return r if None is not r else {'synced': False, 'changed': False, 'title': clean_title, 'conversation_id': cid, 'reason': 'rpc_error', 'error': last_error}
	# @used-by :meth:`TitleSyncer.__post_endpoints()`
	def __send_one(self, scheme: str, port: int, payload: bytes, headers: dict) -> tuple[bool, str]:
		url = f'{scheme}://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/UpdateConversationAnnotations'
		req = urllib.request.Request(url, data=payload, method='POST', headers=headers)
		handlers: list[Any] = [urllib.request.ProxyHandler({})]
		if 'https' == scheme:
			handlers.append(urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
		opener = urllib.request.build_opener(*handlers)
		try:
			with opener.open(req, timeout=self.__timeout) as resp:
				raw = resp.read().decode('utf-8', errors='replace')
				status = getattr(resp, 'status', 200)
			if 200 != status:
				r = (False, f'HTTP {status}')
			elif not isinstance(json.loads(raw) if raw.strip() else {}, dict):
				r = (False, 'Invalid UpdateConversationAnnotations response schema')
			else:
				r = (True, '')
		except (OSError, ValueError, urllib.error.URLError) as exc:
			r = (False, str(exc))
		return r
	# @used-by :func:`Df.Harness.lib.completion_core._run_ag_title_sync()`
	# @used-by :func:`agent_tools.platforms.antigravity.update_conversation_title()`
	def run(self) -> dict[str, Any]:
		hook = SHADOW_TITLE_HOOK[0]
		if None is not hook:
			r = hook(self.__conversation_id, self.__title, backend=self.__backend, instance=self.__instance, paths=self.__paths, timeout=self.__timeout)
		else:
			cid = str(self.__conversation_id or '').strip().lower()
			clean_title = str(self.__title or '').strip()
			if not re.fullmatch('[a-f0-9-]{36}', cid):
				raise ValueError('Exact native Antigravity conversation UUID required')
			if not clean_title:
				raise ValueError('Nonempty conversation title required')
			resolved = self.__paths or dfh_antigravity_paths(backend=self.__backend, instance=self.__instance, conversation_id=cid, settings_fn=self.__ops.get('settings'))
			db_title, ann_title = dfh_read_current_conversation_title(resolved, cid)
			if db_title == clean_title and ann_title == clean_title:
				r = {'synced': True, 'changed': False, 'title': clean_title, 'conversation_id': cid, 'reason': 'already_up_to_date'}
			else:
				discover_fn = self.__ops.get('discover_live_daemon') or (lambda **kw: dfh_discover_live_daemon(settings_fn=self.__ops.get('settings'), is_live_pid_fn=self.__ops.get('is_live_pid'), **kw))
				daemon = discover_fn(paths=resolved)
				r = {'synced': False, 'changed': False, 'title': clean_title, 'conversation_id': cid, 'reason': 'daemon_unavailable'} if None is daemon else self.__post_endpoints(daemon, cid, clean_title, db_title, ann_title)
		return r
