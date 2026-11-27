# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Platform.Antigravity.ExecutorMetadataReader import ExecutorMetadataReader
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.ag_inputs import COMPLETED_STEP_STATUSES, dfh_antigravity_paths, dfh_conversation_db_path, dfh_find_subagent_invocations, dfh_native_inputs, dfh_require_current_binding, dfh_transcript_path
from Df.Harness.lib.ag_metadata import dfh_query_step_model_ids
from Df.Harness.lib.ag_review_wait import dfh_resolve_parent_binding_inputs, dfh_wait_for_reviewer_final_step
from Df.Harness.lib.ag_wire import dfh_extract_transcript_user_input
from Df.Harness.lib.runtime_context import dfh_platform_settings
from Df.Harness.lib.trace_common import dfh_open_readonly_sqlite, dfh_read_jsonl_objects
from Df.Harness.lib.trace_review import dfh_build_native_review_proof
import re
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ReviewProver:
	# @used-by :func:`agent_tools.platforms.antigravity.native_review_proof()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ProofVerifier.ProofVerifier.run()`
	def __init__(self, root, parent_id: str, reviewer_id: str, *, backend=None, instance=None, write: bool=True, wait_timeout: float=0.0, role: str='AA', _ops: dict[str, Any] | None=None) -> None:
		self.__root = Path(root).resolve()
		self.__parent_id = parent_id
		self.__reviewer_id = reviewer_id
		self.__backend = backend
		self.__instance = instance
		self.__write = write
		self.__wait_timeout = wait_timeout
		self.__role = role
		self.__ops = _ops or {}
	# @used-by :meth:`ReviewProver.run()`
	def __build_extra_fields(self, backend: Path, paths: dict, parent_inputs: list, invocation: int, requested_model: str, resolved_inst) -> dict[str, Any]:
		dfh_require_current_binding(self.__root, self.__parent_id, backend=backend, instance=resolved_inst, inputs=dfh_resolve_parent_binding_inputs(backend, self.__parent_id, parent_inputs, paths=paths, native_inputs_fn=dfh_native_inputs, extract_transcript_fn=dfh_extract_transcript_user_input), until=invocation, role=self.__role, settings_fn=self.__ops.get('settings'))
		parent_models = dfh_query_step_model_ids(backend, self.__parent_id, step=invocation, paths=paths)
		child_models = dfh_query_step_model_ids(backend, self.__reviewer_id, paths=paths)
		if 'inherit' == requested_model.lower() and parent_models and child_models and (not child_models.issubset(parent_models)):
			raise ValueError(f'Observed reviewer model differs from the inherited {self.__role} model')
		executor_metadata = ExecutorMetadataReader(self.__root, self.__reviewer_id, role=self.__role, parent_id=self.__parent_id, backend=backend, instance=resolved_inst, _ops=self.__ops).run()
		if 'mismatch' == executor_metadata['verification']['status']:
			raise ValueError('Native reviewer generation/configuration differs from requested parent model/effort selection')
		model_selection = {'selection': executor_metadata['requested']['selection'], 'requested_model': requested_model}
		if executor_metadata['requested'].get('tier'):
			model_selection['tier'] = executor_metadata['requested']['tier']
		return {'model_verification': executor_metadata['verification']['status'] + ': native generation/executor fields', 'model_selection': model_selection, 'executor_metadata': executor_metadata, 'observed_model_ids': sorted(child_models), 'invocation_step': invocation}
	# @used-by :meth:`ReviewProver.run()`
	def __select_invocation(self, parent_inputs: list, expected_agent: str, initial_prompt: str) -> tuple[list, list, int, str]:
		matches, extra_msgs = dfh_find_subagent_invocations(parent_inputs, self.__reviewer_id, expected_agent, initial_prompt)
		if not matches:
			raise ValueError(f'Matching native {expected_agent}/{self.__role} invocation is not established')
		exact_matches = [m for m in matches if m[2]]
		selected = exact_matches[-1] if exact_matches else matches[-1]
		invocation, sub = (selected[0], selected[1])
		requested_model = sub['Model'].strip() if isinstance(sub.get('Model'), str) and sub['Model'].strip() else 'inherit'
		return (matches, extra_msgs, invocation, requested_model)
	# @used-by :meth:`ReviewProver.run()`
	def __verify_child_summary(self, paths: dict, expected_agent: str) -> None:
		if not all((re.fullmatch('[a-f0-9-]{36}', x) for x in (self.__parent_id, self.__reviewer_id))):
			raise ValueError('Native parent/reviewer UUIDs required')
		with dfh_open_readonly_sqlite(Path(paths['conversations_db']), row_factory=sqlite3.Row) as conn:
			child = conn.execute('SELECT parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id=?', (self.__reviewer_id,)).fetchone()
		if None is child or child['parent_conversation_id'] != self.__parent_id or expected_agent != child['agent_name']:
			raise ValueError(f'Native trace does not establish an independent {expected_agent}/{self.__role} child of this parent')
	# @used-by :func:`agent_tools.platforms.antigravity.native_review_proof()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ProofVerifier.ProofVerifier.run()`
	def run(self) -> dict[str, Any]:
		load_cfg = self.__ops.get('settings') or (lambda: SettingsLoader().run())
		ps_fn = self.__ops.get('platform_settings') or (lambda name: dfh_platform_settings(name, settings_fn=load_cfg))
		expected_agent = ps_fn('antigravity').get('roles', {}).get(self.__role, {}).get('agent', 'self')
		paths = dfh_antigravity_paths(backend=self.__backend, instance=self.__instance, conversation_id=self.__reviewer_id or self.__parent_id, settings_fn=load_cfg)
		backend = Path(paths['backend_dir'])
		self.__verify_child_summary(paths, expected_agent)
		log, raw, rows, last = dfh_wait_for_reviewer_final_step(paths, backend, self.__reviewer_id, wait_timeout=self.__wait_timeout, transcript_path_fn=dfh_transcript_path, db_path_fn=dfh_conversation_db_path, completed_statuses=COMPLETED_STEP_STATUSES)
		parent_log = dfh_transcript_path(paths['brain_dir'], self.__parent_id)
		parent_inputs = dfh_read_jsonl_objects(parent_log)
		initial_prompt = rows[0].get('content', '')
		matches, extra_msgs, invocation, req_model = self.__select_invocation(parent_inputs, expected_agent, initial_prompt)
		resolved_inst = paths['instance'] or self.__instance
		prompts = [initial_prompt, *extra_msgs, *(m[1]['Prompt'] for m in matches)]
		return dfh_build_native_review_proof(self.__root, 'antigravity-ui', self.__parent_id, self.__reviewer_id, expected_agent, log, parent_log, raw, last['step_index'], last['content'], prompts, rows, extra_fields_fn=lambda: self.__build_extra_fields(backend, paths, parent_inputs, invocation, req_model, resolved_inst), write=self.__write, role=self.__role)
