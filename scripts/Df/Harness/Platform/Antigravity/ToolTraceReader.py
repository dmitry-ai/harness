# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.ag_inputs import dfh_antigravity_paths, dfh_conversation_db_path, dfh_transcript_path
from Df.Harness.lib.path_discovery import dfh_default_platform_paths
from Df.Harness.lib.runtime_instances import dfh_platform_instances
from Df.Harness.lib.trace_common import dfh_open_readonly_sqlite, dfh_parse_tool_args, dfh_read_jsonl_objects
from Df.Harness.lib.trace_review import dfh_make_tool_trace_event
import hashlib
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ToolTraceReader:
	# @used-by :func:`agent_tools.platforms.antigravity.native_tool_trace()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_codex_and_ag_scanners_and_tool_trace()`
	def __init__(self, root, request: dict[str, Any], *, _ops: dict[str, Any] | None=None) -> None:
		self.__root = root
		self.__request = request
		self.__ops = _ops or {}
	# @used-by :meth:`ToolTraceReader.run()`
	def __extract_step_event(self, rows: list, statuses: dict, index: int) -> dict:
		matches = [pos for pos, row in enumerate(rows) if row.get('step_index') == index]
		if 1 != len(matches):
			raise ValueError('Native invocation step is missing/ambiguous')
		pos = matches[0]
		row = rows[pos]
		calls = row.get('tool_calls', [])
		if 1 != len(calls):
			raise ValueError('Select a native step containing exactly one tool call; multi-call results cannot be safely attributed')
		following = self.__following_generics(rows, pos)
		if not following or any((c.get('error') for c in following)):
			raise ValueError('Native tool has no attributable successful result')
		output = following[-1]
		if 3 != statuses.get(output.get('step_index')):
			raise ValueError('Native database does not confirm successful tool completion')
		call = calls[0]
		arguments = dfh_parse_tool_args(call.get('args', {})) if isinstance(call.get('args', {}), (dict, str)) else {}
		return dfh_make_tool_trace_event(str(index), index, output['step_index'], call.get('name', ''), arguments, output.get('content', ''), True, row.get('created_at'), output.get('created_at'), {'call': call, 'output': {'step_index': output.get('step_index'), 'content': output.get('content'), 'created_at': output.get('created_at')}})
	# @used-by :meth:`ToolTraceReader.__extract_step_event()`
	def __following_generics(self, rows: list, pos: int) -> list[dict]:
		r: list[dict] = []
		for candidate in rows[pos + 1:]:
			if candidate.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT'):
				break
			if 'GENERIC' == candidate.get('type'):
				r.append(candidate)
		return r
	# @used-by :meth:`ToolTraceReader.run()`
	def __resolve_paths(self, conversation_id: str) -> dict:
		load_cfg = self.__ops.get('settings') or (lambda: SettingsLoader().run())
		inst_fn = self.__ops.get('platform_instances')
		if self.__request.get('native_profile_home'):
			home_req = Path(self.__request['native_profile_home']).resolve()
			cfg = load_cfg()
			ag_insts = (inst_fn('antigravity', include_disabled=True) if None is not inst_fn else dfh_platform_instances('antigravity', config=cfg, include_disabled=True)) if 'antigravity' in cfg['platforms'] else {}
			matched = [inst for inst in ag_insts.values() if inst.get('home') and Path(inst['home']).resolve() == home_req and inst['system_paths'].get('backend_dir')]
			if matched:
				r = dfh_antigravity_paths(backend=matched[0]['system_paths']['backend_dir'], instance=matched[0]['id'], conversation_id=conversation_id, settings_fn=load_cfg)
			else:
				r = dfh_antigravity_paths(backend=Path(dfh_default_platform_paths('antigravity', home=home_req)['backend_dir']), conversation_id=conversation_id, settings_fn=load_cfg)
		else:
			r = dfh_antigravity_paths(instance=self.__request.get('instance'), conversation_id=conversation_id, settings_fn=load_cfg)
		return r
	# @used-by :func:`agent_tools.platforms.antigravity.native_tool_trace()`
	# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_codex_and_ag_scanners_and_tool_trace()`
	def run(self) -> dict[str, Any]:
		conversation_id = self.__request.get('conversation_id', '')
		paths = self.__resolve_paths(conversation_id)
		database = dfh_conversation_db_path(Path(paths['backend_dir']), conversation_id, paths=paths)
		with dfh_open_readonly_sqlite(database) as connection:
			statuses = {index: status for index, status in connection.execute('SELECT idx,status FROM steps')}
		path = dfh_transcript_path(paths['brain_dir'], conversation_id)
		raw = path.read_bytes()
		rows = dfh_read_jsonl_objects(raw)
		selected = self.__request.get('step_indices')
		if not isinstance(selected, list) or (not selected) or any((int is not type(x) for x in selected)) or len(set(selected)) != len(selected):
			raise ValueError('Exact unique Antigravity native invocation step indices required')
		events = [self.__extract_step_event(rows, statuses, index) for index in selected]
		return {'surface': 'antigravity-ui', 'conversation_id': conversation_id, 'step_indices': selected, 'native_database': str(database), 'native_log': str(path), 'native_log_sha256': hashlib.sha256(raw).hexdigest(), 'events': events}
