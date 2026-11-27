# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.codex_trace import dfh_codex_paths, dfh_codex_trace
from Df.Harness.lib.runtime_context import dfh_platform_settings
from Df.Harness.lib.runtime_instances import dfh_extract_platform_homes
from Df.Harness.lib.trace_review import dfh_make_tool_trace_event
import hashlib
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ToolTraceReader:
	# @used-by :func:`agent_tools.platforms.codex.native_tool_trace()`
	def __init__(self, root, request: dict[str, Any], *, _ops: dict[str, Any] | None=None) -> None:
		self.__root = root
		self.__request = request
		self.__ops = _ops or {}
	# @used-by :meth:`ToolTraceReader.run()`
	def __build_call_event(self, call_id: str, calls: dict, outputs: dict) -> dict:
		if call_id not in calls or call_id not in outputs or outputs[call_id][0] <= calls[call_id][0]:
			raise ValueError('Native tool call has no matched completed output')
		index, call, created_at = calls[call_id]
		output_index, output, completed_at = outputs[call_id]
		arguments = call.get('arguments', call.get('input', {}))
		if isinstance(arguments, str):
			try:
				arguments = json.loads(arguments)
			except ValueError:
				arguments = {'code': arguments} if 'custom_tool_call' == call.get('type') else {}
		result = output.get('output')
		error = True is output.get('isError') or (isinstance(result, dict) and True is result.get('isError'))
		if isinstance(result, str):
			try:
				error |= True is json.loads(result).get('isError')
			except (ValueError, AttributeError):
				pass
		return dfh_make_tool_trace_event(call_id, index, output_index, call.get('name', ''), arguments, result, not error, created_at, completed_at, [call, output], namespace=call.get('namespace'))
	# @used-by :meth:`ToolTraceReader.run()`
	def __collect_calls_and_outputs(self, rows: list, ids: list[str]) -> tuple[dict, dict]:
		calls, outputs = ({}, {})
		for index, item in rows:
			payload = item.get('payload', {})
			if 'response_item' == item.get('type') and payload.get('call_id') in ids:
				call_id, kind = (payload['call_id'], payload.get('type'))
				if kind in ('function_call', 'custom_tool_call'):
					if call_id in calls:
						raise ValueError('Ambiguous native tool invocation')
					calls[call_id] = (index, payload, item.get('timestamp'))
				elif kind in ('function_call_output', 'custom_tool_call_output'):
					if call_id in outputs:
						raise ValueError('Ambiguous native tool output')
					outputs[call_id] = (index, payload, item.get('timestamp'))
		return (calls, outputs)
	# @used-by :func:`agent_tools.platforms.codex.native_tool_trace()`
	def run(self) -> dict[str, Any]:
		load_cfg = self.__ops.get('settings') or (lambda: SettingsLoader().run())
		ps_fn = self.__ops.get('platform_settings') or (lambda name: dfh_platform_settings(name, settings_fn=load_cfg))
		homes_fn = self.__ops.get('extract_platform_homes') or dfh_extract_platform_homes
		conversation_id = self.__request.get('conversation_id', '')
		paths = dfh_codex_paths(self.__request.get('native_profile_home'), profile=self.__request.get('instance'), conversation_id=conversation_id, platform_settings_fn=ps_fn, settings_fn=load_cfg)
		home = paths['home']
		allowed_homes = [Path(value).resolve() for value in homes_fn(ps_fn('codex'), platform='codex', include_disabled=True).values()]
		if self.__request.get('native_profile_home') and home not in allowed_homes:
			raise ValueError('Native tool trace names an unconfigured Codex profile')
		_, path, raw, rows = dfh_codex_trace(home, conversation_id, paths=paths, platform_settings_fn=ps_fn, settings_fn=load_cfg)
		ids = self.__request.get('call_ids')
		if not isinstance(ids, list) or (not ids) or (not all((isinstance(x, str) and x.strip() for x in ids))) or len(set(ids)) != len(ids):
			raise ValueError('Exact unique Codex native tool call IDs required')
		calls, outputs = self.__collect_calls_and_outputs(rows, ids)
		events = [self.__build_call_event(cid, calls, outputs) for cid in ids]
		return {'surface': 'codex-ui', 'conversation_id': conversation_id, 'native_profile_home': str(home), 'call_ids': ids, 'native_log': str(path), 'native_log_sha256': hashlib.sha256(raw).hexdigest(), 'events': events}
