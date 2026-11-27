# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_same_project_root
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
from Df.Harness.lib.storage import dfh_iter_embedded_json_objects
from Df.Harness.lib.trace_common import dfh_parse_tool_args
from agent_tools.research import inside
import hashlib
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_codex_review_inputs()`
def _collect_output_receipts(payload: dict, call_args: str, root_p: Path, parent_id: str, reviewer_id: str, role: str, call_id: str, index: int) -> list[dict]:
	r: list[dict] = []
	for receipt in dfh_iter_embedded_json_objects(payload.get('output'), parse_root=False):
		matched = _match_review_receipt(receipt, root_p, parent_id, reviewer_id, role, call_args, call_id, index)
		if None is not matched:
			r.append(matched)
	return r
# @used-by :func:`_collect_output_receipts()`
def _match_review_receipt(receipt: dict, root_p: Path, parent_id: str, reviewer_id: str, role: str, call_args: str, call_id: str, index: int) -> dict | None:
	r: dict | None = None
	key = {'ARCH': 'arch_review_input'}.get(role, 'upwork_review_input')
	if 1 == receipt.get(key) and True is receipt.get('verified') and receipt.get('reviewer_id') == reviewer_id and receipt.get('parent_id') == parent_id and dfh_same_project_root(receipt.get('project_root'), root_p):
		try:
			package = inside(root_p, receipt.get('package', ''))
		except ValueError:
			package = None
		if None is not package and package.is_file() and package.name in call_args and hashlib.sha256(package.read_bytes()).hexdigest() == receipt.get('package_sha256'):
			r = {'package': receipt['package'], 'package_sha256': receipt['package_sha256'], 'call_id': call_id, 'output_step': index}
	return r
# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.__build_extra_fields()`
def dfh_codex_assignment_source(rows: list, meta: dict, assignment: str) -> str:
	r: str | None = None
	path = meta['source']['subagent']['thread_spawn']['agent_path']
	for _, item in rows:
		payload = item.get('payload', {})
		if 'response_item' == item.get('type') and 'agent_message' == payload.get('type') and payload.get('recipient') == path:
			parts = payload.get('content', [])
			if any((part.get('text', '').startswith('Message Type: NEW_TASK') for part in parts)) and any((part.get('encrypted_content') == assignment for part in parts if 'encrypted_content' == part.get('type'))):
				r = 'matching-native-spawn-and-child-ciphertext'
				break
	if None is r:
		if assignment.startswith('gAAAAA'):
			raise ValueError('Encrypted native spawn does not match the child assignment')
		r = 'native-parent-spawn.message'
	return r
# @used-by :func:`dfh_codex_selection()`
# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.run()`
# @used-by :meth:`test_executor_metadata.ExecutorMetadataTests.test_existing_codex_review_model_gate_still_rejects_missing_actual_context()`
def dfh_codex_model(rows: list, before=None) -> dict:
	contexts = [item['payload'] for index, item in rows if 'turn_context' == item.get('type') and (None is before or index <= before)]
	if not contexts or (not contexts[-1].get('model')) or (not contexts[-1].get('effort')):
		raise ValueError('Actual Codex model/effort is unavailable in native turn context')
	return {key: contexts[-1][key] for key in ('model', 'effort')}
# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.__build_extra_fields()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
def dfh_codex_review_inputs(root, rows: list, parent_id: str, reviewer_id: str, *, role: str='AA') -> list[dict]:
	calls: dict = {}
	r: list[dict] = []
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	for index, item in rows:
		payload = item.get('payload', {})
		if 'response_item' == item.get('type'):
			call_id, kind = (payload.get('call_id'), payload.get('type'))
			if kind in ('function_call', 'custom_tool_call'):
				arguments = payload.get('input', payload.get('arguments', ''))
				if isinstance(arguments, str) and 'review-input' in arguments:
					calls[call_id] = arguments
			elif kind in ('function_call_output', 'custom_tool_call_output') and call_id in calls:
				r.extend(_collect_output_receipts(payload, calls[call_id], root_p, parent_id, reviewer_id, role, call_id, index))
	if not r:
		raise ValueError('Native reviewer has no successful review-input execution for this immutable package')
	return r
# @used-by :meth:`Df.Harness.Platform.Codex.ExecutorMetadataReader.ExecutorMetadataReader.__resolve_child_requested()`
# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.run()`
def dfh_codex_selection(parent_rows: list, child_meta: dict, invocation=None) -> dict:
	index, call_id, arguments = invocation or dfh_codex_spawn(parent_rows, child_meta)
	parent = dfh_codex_model(parent_rows, before=index)
	model = arguments.get('model') or parent['model']
	effort = arguments.get('reasoning_effort') or arguments.get('model_reasoning_effort')
	if None is effort and model == parent['model']:
		effort = parent['effort']
	return {'model': model, 'effort': effort, 'invocation_call_id': call_id, 'task_name': arguments['task_name'], 'selection': 'explicit-parent-spawn' if arguments.get('model') or arguments.get('reasoning_effort') else 'inherit'}
# @used-by :func:`dfh_codex_selection()`
# @used-by :meth:`Df.Harness.Platform.Codex.ExecutorMetadataReader.ExecutorMetadataReader.__resolve_child_requested()`
# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.run()`
def dfh_codex_spawn(parent_rows: list, child_meta: dict) -> tuple:
	path, created, matches = (child_meta['source']['subagent']['thread_spawn'].get('agent_path', ''), child_meta.get('timestamp'), [])
	for index, item in parent_rows:
		payload = item.get('payload', {})
		if 'response_item' == item.get('type') and payload.get('name', '').endswith('spawn_agent') and (not (created and item.get('timestamp') and item['timestamp'] > created)):
			value = dfh_parse_tool_args(payload.get('arguments', payload.get('input', '{}')))
			if value.get('task_name') and path.endswith('/' + value['task_name']):
				matches.append((index, payload.get('call_id'), value))
	if not matches:
		raise ValueError('Native parent spawn call and its model selection are not established')
	return matches[-1]
