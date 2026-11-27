# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.codex_metadata import dfh_codex_selection, dfh_codex_spawn
from Df.Harness.lib.codex_trace import dfh_codex_paths, dfh_codex_trace
from Df.Harness.lib.trace_review import dfh_finalize_executor_checks
from agent_tools.research import json_data
import hashlib
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ExecutorMetadataReader:
	# @used-by :func:`agent_tools.platforms.codex.native_executor_metadata()`
	# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.__build_extra_fields()`
	def __init__(self, root, conversation_id: str, *, role: str='primary', parent_id: str | None=None, backend=None, instance=None, _ops: dict[str, Any] | None=None) -> None:
		self.__root = root
		self.__conversation_id = conversation_id
		self.__role = role
		self.__parent_id = parent_id
		self.__backend = backend
		self.__instance = instance
		self.__ops = _ops or {}
	# @used-by :meth:`ExecutorMetadataReader.run()`
	def __resolve_child_requested(self, home, paths: dict, meta: dict, spawn: dict) -> dict[str, Any]:
		if not self.__parent_id or spawn.get('parent_thread_id') != self.__parent_id or self.__parent_id == self.__conversation_id:
			raise ValueError('Native parent/child relationship required for AA/AF metadata')
		_, parent_path, _, parent_rows = dfh_codex_trace(home, self.__parent_id, paths=paths, platform_settings_fn=self.__ops.get('platform_settings'), settings_fn=self.__ops.get('settings'))
		invocation = dfh_codex_spawn(parent_rows, meta)
		try:
			selection = dfh_codex_selection(parent_rows, meta, invocation)
			requested = {key: selection.get(key) for key in ('model', 'effort', 'selection')}
		except ValueError:
			arguments = invocation[2]
			requested = {'model': arguments.get('model'), 'effort': arguments.get('reasoning_effort') or arguments.get('model_reasoning_effort'), 'selection': 'explicit-parent-spawn' if arguments.get('model') else 'inherit'}
		requested['source'] = {'native_file': str(parent_path), 'kind': 'spawn_agent', 'step': invocation[0], 'call_id': invocation[1]}
		return requested
	# @used-by :func:`agent_tools.platforms.codex.native_executor_metadata()`
	# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.__build_extra_fields()`
	def run(self) -> dict[str, Any]:
		if self.__role not in ('primary', 'AA', 'AF', 'ARCH'):
			raise ValueError('Unknown executor role')
		paths = dfh_codex_paths(self.__backend, profile=self.__instance, conversation_id=self.__conversation_id, platform_settings_fn=self.__ops.get('platform_settings'), settings_fn=self.__ops.get('settings'))
		home = paths['home']
		_, path, _, rows = dfh_codex_trace(home, self.__conversation_id, paths=paths, platform_settings_fn=self.__ops.get('platform_settings'), settings_fn=self.__ops.get('settings'))
		contexts = [(index, item['payload']) for index, item in rows if 'turn_context' == item.get('type')]
		history = [{'step': index, 'model': context.get('model'), 'effort': context.get('effort')} for index, context in contexts]
		observed = {key: history[-1].get(key) if history else None for key in ('model', 'effort')}
		sources = [{'native_file': str(path), 'kind': 'turn_context', 'step': index, 'sha256': hashlib.sha256(json_data(context)).hexdigest()} for index, context in contexts]
		requested: dict[str, Any] = {'model': None, 'effort': None, 'selection': 'unavailable', 'source': None}
		meta = rows[0][1]['payload']
		source = meta.get('source')
		spawn = source.get('subagent', {}).get('thread_spawn', {}) if isinstance(source, dict) else {}
		if 'primary' == self.__role:
			if meta.get('model'):
				requested.update(model=meta['model'], effort=meta.get('reasoning_effort'), selection='native-session-selection', source={'native_file': str(path), 'kind': 'session_meta', 'step': rows[0][0]})
		else:
			requested = self.__resolve_child_requested(home, paths, meta, spawn)
		return dfh_finalize_executor_checks('codex-ui', self.__role, self.__conversation_id, self.__parent_id, requested, observed, history, sources, 'Native turn_context reports selected model/effort; missing fields remain unknown; server execution internals are not inferred')
