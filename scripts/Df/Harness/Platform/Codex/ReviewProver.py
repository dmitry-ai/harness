# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.Platform.Codex.ExecutorMetadataReader import ExecutorMetadataReader
from Df.Harness.lib.codex_metadata import dfh_codex_assignment_source, dfh_codex_model, dfh_codex_review_inputs, dfh_codex_selection, dfh_codex_spawn
from Df.Harness.lib.codex_trace import dfh_codex_paths, dfh_codex_require_current_binding, dfh_codex_trace, dfh_extract_codex_target_subagents
from Df.Harness.lib.trace_common import dfh_parse_tool_args
from Df.Harness.lib.trace_review import dfh_build_native_review_proof
import hashlib
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ReviewProver:
	# @used-by :func:`agent_tools.platforms.codex.native_review_proof()`
	# @used-by :meth:`Df.Harness.Platform.Codex.ProofVerifier.ProofVerifier.run()`
	def __init__(self, root, parent_id: str, reviewer_id: str, *, backend=None, instance=None, write: bool=True, wait_timeout: float=0.0, role: str='AA', _ops: dict[str, Any] | None=None) -> None:
		self.__root = root
		self.__parent_id = parent_id
		self.__reviewer_id = reviewer_id
		self.__backend = backend
		self.__instance = instance
		self.__write = write
		self.__wait_timeout = wait_timeout
		self.__role = role
		self.__ops = _ops or {}
	# @used-by :meth:`ReviewProver.run()`
	def __build_extra_fields(self, home, rows: list, meta: dict, assignment: str, child_model: dict, selection: dict, resolved_inst) -> dict[str, Any]:
		return {'native_profile_home': str(home), 'assignment_sha256': hashlib.sha256(assignment.encode('utf-8')).hexdigest(), 'assignment_source': dfh_codex_assignment_source(rows, meta, assignment), 'review_inputs': dfh_codex_review_inputs(self.__root, rows, self.__parent_id, self.__reviewer_id, role=self.__role), 'observed_model': child_model, 'model_selection': selection, 'executor_metadata': ExecutorMetadataReader(self.__root, self.__reviewer_id, role=self.__role, parent_id=self.__parent_id, backend=home, instance=resolved_inst, _ops=self.__ops).run(), 'model_verification': 'native child model/effort checked against actual parent spawn parameters'}
	# @used-by :meth:`ReviewProver.run()`
	def __collect_matched_prompts(self, parent_rows: list, assignment: str) -> list[str]:
		matched = [assignment]
		for _, p_item in parent_rows:
			p_pay = p_item.get('payload', {}) if isinstance(p_item, dict) else {}
			if 'response_item' == p_item.get('type') and p_pay.get('type') in ('function_call', 'custom_tool_call') and str(p_pay.get('name') or '').endswith(('send_input', 'send_message')):
				p_args = p_pay.get('arguments', p_pay.get('input', {}))
				if self.__reviewer_id.lower() in dfh_extract_codex_target_subagents(p_args):
					parsed = dfh_parse_tool_args(p_args)
					msg_txt = parsed.get('message') or parsed.get('Message') or parsed.get('input')
					if isinstance(msg_txt, str) and msg_txt.strip():
						matched.append(msg_txt)
		return matched
	# @used-by :meth:`ReviewProver.run()`
	def __validate_child_source(self, child_row: dict, rows: list) -> tuple[dict, dict, int, dict]:
		meta = rows[0][1]['payload']
		source = meta.get('source')
		if not isinstance(source, dict):
			raise ValueError('Native Codex reviewer is not a spawned child')
		spawn = source.get('subagent', {}).get('thread_spawn', {})
		if self.__parent_id == self.__reviewer_id or spawn.get('parent_thread_id') != self.__parent_id:
			raise ValueError('Codex source does not establish this parent/child relationship')
		if child_row.get('agent_path') and child_row['agent_path'] != spawn.get('agent_path'):
			raise ValueError('Codex child database and session source disagree')
		events = [(i, item['payload']) for i, item in rows if 'event_msg' == item.get('type')]
		if not events or 'task_complete' != events[-1][1].get('type') or (not events[-1][1].get('last_agent_message', '').strip()):
			raise ValueError('Codex reviewer has no completed final native turn')
		return (meta, spawn, events[-1][0], events[-1][1])
	# @used-by :func:`agent_tools.platforms.codex.native_review_proof()`
	# @used-by :meth:`Df.Harness.Platform.Codex.ProofVerifier.ProofVerifier.run()`
	def run(self) -> dict[str, Any]:
		paths = dfh_codex_paths(self.__backend, profile=self.__instance, conversation_id=self.__reviewer_id or self.__parent_id, platform_settings_fn=self.__ops.get('platform_settings'), settings_fn=self.__ops.get('settings'))
		home = paths['home']
		_, parent_path, _, parent_rows = dfh_codex_trace(home, self.__parent_id, paths=paths, platform_settings_fn=self.__ops.get('platform_settings'), settings_fn=self.__ops.get('settings'))
		child_row, path, raw, rows = dfh_codex_trace(home, self.__reviewer_id, paths=paths, platform_settings_fn=self.__ops.get('platform_settings'), settings_fn=self.__ops.get('settings'))
		meta, spawn, final_index, final = self.__validate_child_source(child_row, rows)
		invocation = dfh_codex_spawn(parent_rows, meta)
		dfh_codex_require_current_binding(self.__root, self.__parent_id, backend=home, rows=parent_rows, until=invocation[0], role=self.__role, platform_settings_fn=self.__ops.get('platform_settings'), settings_fn=self.__ops.get('settings'))
		selection, child_model = (dfh_codex_selection(parent_rows, meta, invocation), dfh_codex_model(rows))
		if child_model['model'] != selection['model'] or (None is not selection['effort'] and child_model['effort'] != selection['effort']):
			raise ValueError('Observed reviewer model/effort differs from the native parent spawn selection')
		assignment = invocation[2].get('message')
		if not isinstance(assignment, str) or (not assignment.strip()):
			raise ValueError('Native parent reviewer assignment is unavailable')
		matched = self.__collect_matched_prompts(parent_rows, assignment)
		resolved_inst = paths['instance'] or self.__instance
		return dfh_build_native_review_proof(self.__root, 'codex-ui', self.__parent_id, self.__reviewer_id, spawn.get('agent_path'), path, parent_path, raw, final_index, final['last_agent_message'], matched, rows, diff_error='Existing Codex proof differs; preserve both versions', extra_fields_fn=lambda: self.__build_extra_fields(home, rows, meta, assignment, child_model, selection, resolved_inst), write=self.__write, role=self.__role)
