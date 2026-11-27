# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.request_binding import dfh_format_binding_diagnostic, dfh_native_project_id, dfh_review_project_id, dfh_scoped_inputs
from Df.Harness.lib.runtime_context import dfh_platform_settings
from Df.Harness.lib.runtime_resolve import dfh_resolve_codex_paths
from Df.Harness.lib.trace_common import UUID_PATTERN, dfh_local_uri_to_path, dfh_open_readonly_sqlite, dfh_parse_tool_args
from Df.Harness.lib.trace_review import dfh_current_turn_requests, dfh_require_turn_binding
import glob
import json
import re
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
SUBAGENT_PARENT_CACHE: dict[str, tuple[int, int, str]] = {}
# @used-by :func:`dfh_codex_request_scope()`
def _collect_codex_user_inputs(visible: list, contexts: list, roots: list) -> list:
	inputs: list = []
	for index, text, payload in dfh_codex_messages(visible, 'user'):
		if dfh_actual_user_input(text, payload):
			turn = payload.get('internal_chat_message_metadata_passthrough', {}).get('turn_id')
			matching = [(step, value) for step, value in contexts if turn and value.get('turn_id') == turn]
			if matching and (not any((step <= index for step, _ in matching))):
				roots.append((index, str(dfh_local_uri_to_path(matching[0][1]['cwd'])), 'codex-turn-cwd'))
			inputs.append((index, text))
	return inputs
# @used-by :func:`dfh_codex_trace()`
def _find_codex_thread_row(resolved: dict, conversation_id: str) -> dict:
	found: list[dict] = []
	for database in dfh_state_db_files(resolved):
		with dfh_open_readonly_sqlite(database, row_factory=sqlite3.Row) as connection:
			row = connection.execute('SELECT * FROM threads WHERE id=?', (conversation_id,)).fetchone()
			if row:
				found.append(dict(row))
	if 1 != len(found):
		raise ValueError('Native Codex thread is missing or ambiguous in this profile')
	return found[0]
# @used-by :func:`dfh_codex_trace()`
def _parse_codex_rollout_rows(raw: bytes, conversation_id: str) -> list[tuple[int, dict]]:
	rows: list[tuple[int, dict]] = []
	for index, line in enumerate(raw.splitlines()):
		if not line.strip():
			continue
		try:
			value = json.loads(line)
		except ValueError as exc:
			raise ValueError('Native Codex trace has a partial record; retry after it is flushed') from exc
		kind, payload = (value.get('type'), value.get('payload', {}))
		if kind in ('session_meta', 'turn_context') or ('response_item' == kind and 'reasoning' != payload.get('type')) or ('event_msg' == kind and payload.get('type') in ('task_started', 'task_complete', 'turn_aborted')):
			rows.append((index, value))
		elif kind in ('compacted', 'context_compacted', 'checkpoint') or ('event_msg' == kind and payload.get('type') in ('context_compacted', 'compacted', 'checkpoint')):
			rows.append((index, {'type': 'event_msg', 'payload': {'type': 'context_compacted', 'turn_id': payload.get('turn_id')}}))
	if not rows or 'session_meta' != rows[0][1].get('type') or rows[0][1]['payload'].get('id') != conversation_id:
		raise ValueError('Codex trace identity differs from native database')
	return rows
# @used-by :func:`_collect_codex_user_inputs()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_user_message()`
def dfh_actual_user_input(text: str, payload: dict) -> bool:
	kinds = payload.get('internal_chat_message_metadata_passthrough', {}).get('content_item_kinds', [])
	if 'user.text' in kinds:
		r = True
	elif any((kind in ('agents_md.instructions', 'environments.environment_context') for kind in kinds)):
		r = False
	elif kinds:
		r = not text.lstrip().startswith('<external_codex_apps_open_page>')
	else:
		r = not text.lstrip().startswith(('<environment_context>', '<external_codex_apps_open_page>')) and (not (text.lstrip().startswith('# AGENTS.md instructions') and '<INSTRUCTIONS>' in text))
	return r
# @used-by :func:`_collect_codex_user_inputs()`
def dfh_codex_messages(rows: list, role: str):
	for index, item in rows:
		payload = item.get('payload', {})
		if 'response_item' == item.get('type') and 'message' == payload.get('type') and payload.get('role') == role:
			content = payload.get('content', [])
			if not isinstance(content, list):
				raise ValueError('Unsupported native Codex message content')
			texts = [part['text'] for part in content if part.get('type') in ('input_text', 'output_text') and isinstance(part.get('text'), str)]
			if texts:
				yield (index, ''.join(texts), payload)
# @used-by :func:`agent_tools.platforms.codex.native_requests()`
def dfh_codex_native_requests(root, conversation_id: str, *, backend=None, instance=None, platform_settings_fn=None, settings_fn=None) -> list[dict]:
	paths = dfh_codex_paths(backend, profile=instance, conversation_id=conversation_id, platform_settings_fn=platform_settings_fn, settings_fn=settings_fn)
	home = paths['home']
	selected, _, _ = dfh_codex_request_scope(root, dfh_codex_trace(home, conversation_id, paths=paths, platform_settings_fn=platform_settings_fn, settings_fn=settings_fn)[3])
	return dfh_current_turn_requests(selected, conversation_id, 'codex-ui', 'Native Codex requests do not identify this project; open the session in the exact project directory or pass its /upwork-init URL', id_fmt='codex:{cid}:{idx}', extra={'native_profile_home': str(home)})
# @used-by :func:`agent_tools.platforms.codex._paths()`
# @used-by :func:`dfh_codex_native_requests()`
# @used-by :func:`dfh_codex_require_current_binding()`
# @used-by :func:`dfh_codex_trace()`
# @used-by :meth:`Df.Harness.Platform.Codex.ExecutorMetadataReader.ExecutorMetadataReader.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.ToolTraceReader.ToolTraceReader.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__init__()`
def dfh_codex_paths(backend=None, profile=None, *, conversation_id=None, platform_settings_fn=None, settings_fn=None) -> dict:
	load_cfg = settings_fn if None is not settings_fn else (lambda: SettingsLoader().run())
	ps_fn = platform_settings_fn if None is not platform_settings_fn else (lambda name: dfh_platform_settings(name, settings_fn=load_cfg))
	return dfh_resolve_codex_paths(backend, instance=profile, conversation_id=conversation_id, codex_cfg=ps_fn('codex'), settings_fn=load_cfg)
# @used-by :func:`dfh_codex_native_requests()`
# @used-by :func:`dfh_codex_require_current_binding()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__load_context()`
def dfh_codex_request_scope(root, rows: list, *, until=None, identifier=None):
	job_id = identifier if None is not identifier else dfh_native_project_id(root)
	visible = [(index, item) for index, item in rows if None is until or index <= until]
	contexts = [(index, item['payload']) for index, item in visible if 'turn_context' == item.get('type') and item['payload'].get('cwd')]
	roots = []
	meta = visible[0][1]['payload'] if visible else {}
	if meta.get('cwd'):
		roots.append((visible[0][0], str(dfh_local_uri_to_path(meta['cwd'])), 'codex-session-cwd'))
	roots.extend(((index, str(dfh_local_uri_to_path(value['cwd'])), 'codex-turn-cwd') for index, value in contexts))
	inputs = _collect_codex_user_inputs(visible, contexts, roots)
	return dfh_scoped_inputs(root, job_id, inputs, roots, until=until)
# @used-by :func:`agent_tools.platforms.codex.require_current_binding()`
# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.run()`
def dfh_codex_require_current_binding(root, conversation_id: str, *, backend=None, instance=None, rows=None, until=None, role: str='AA', platform_settings_fn=None, settings_fn=None):
	if None is rows:
		paths = dfh_codex_paths(backend, profile=instance, conversation_id=conversation_id, platform_settings_fn=platform_settings_fn, settings_fn=settings_fn)
		rows_val = dfh_codex_trace(paths['home'], conversation_id, paths=paths, platform_settings_fn=platform_settings_fn, settings_fn=settings_fn)[3]
	else:
		rows_val = rows
	job_id = dfh_review_project_id(root, role=role)
	selected, active, binding = dfh_codex_request_scope(root, rows_val, until=until, identifier=job_id)
	diag = dfh_format_binding_diagnostic(str(Path(root).resolve()), binding, expected_job_id=job_id)
	return dfh_require_turn_binding(selected, active, binding, f'Native Codex conversation is currently bound to another project or no exact project root ({diag})')
# @used-by :func:`agent_tools.platforms.codex._trace()`
# @used-by :func:`dfh_codex_native_requests()`
# @used-by :func:`dfh_codex_require_current_binding()`
# @used-by :meth:`Df.Harness.Platform.Codex.ExecutorMetadataReader.ExecutorMetadataReader.__resolve_child_requested()`
# @used-by :meth:`Df.Harness.Platform.Codex.ExecutorMetadataReader.ExecutorMetadataReader.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.ToolTraceReader.ToolTraceReader.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__load_context()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__resolve_subagent_child()`
def dfh_codex_trace(home, conversation_id: str, *, paths=None, platform_settings_fn=None, settings_fn=None) -> tuple[dict, Path, bytes, list[tuple[int, dict]]]:
	resolved = paths or dfh_codex_paths(home, conversation_id=conversation_id, platform_settings_fn=platform_settings_fn, settings_fn=settings_fn)
	sessions_dir = dfh_local_uri_to_path(resolved['sessions_dir']) if resolved.get('sessions_dir') else None
	if not re.fullmatch('[a-f0-9-]{36}', conversation_id):
		raise ValueError('Exact native Codex thread UUID required')
	row = _find_codex_thread_row(resolved, conversation_id)
	path = dfh_local_uri_to_path(row['rollout_path'])
	if sessions_dir and (not path.is_relative_to(sessions_dir)):
		raise ValueError('Codex trace is outside the selected profile sessions')
	raw = path.read_bytes()
	return (row, path, raw, _parse_codex_rollout_rows(raw, conversation_id))
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__collect_bfs_seeds()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_subagent_output()`
def dfh_extract_codex_spawn_output_uuids(out_text: str) -> list[str]:
	r: list[str] = []
	if isinstance(out_text, str) and out_text.strip():
		try:
			parsed = json.loads(out_text)
		except ValueError:
			parsed = None
		if not isinstance(parsed, dict):
			r = [m.lower() for m in re.findall(f'\\b({UUID_PATTERN})\\b', out_text, flags=re.I)]
		else:
			matched = [u for u in dict.fromkeys((str(parsed[k]).strip().lower() for k in ('agent_id', 'conversationId', 'subagent_id', 'id', 'thread_id') if isinstance(parsed.get(k), str))) if re.fullmatch(UUID_PATTERN, u)]
			r = matched if matched or any((k in parsed for k in ('output', 'message', 'response', 'content'))) else [m.lower() for m in re.findall(f'\\b({UUID_PATTERN})\\b', out_text, flags=re.I)]
	return r
# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.__collect_matched_prompts()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_subagent_call()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_tool_call_row()`
def dfh_extract_codex_target_subagents(raw_args) -> list[str]:
	parsed_args = dfh_parse_tool_args(raw_args)
	candidates = [val.strip().lower() for key in ('id', 'Recipient', 'agent_id', 'subagent_id') for val in [parsed_args.get(key)] if isinstance(val, str)]
	ids_val = parsed_args.get('ids')
	if isinstance(ids_val, list):
		candidates.extend((item.strip().lower() for item in ids_val if isinstance(item, str)))
	return [u for u in dict.fromkeys(candidates) if re.fullmatch(UUID_PATTERN, u)]
# @used-by :func:`_find_codex_thread_row()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__index_profile_subagents()`
def dfh_state_db_files(paths_or_home) -> list[Path]:
	if isinstance(paths_or_home, dict):
		home = dfh_local_uri_to_path(paths_or_home['home']) if paths_or_home.get('home') else None
		glob_raw = paths_or_home.get('state_db_glob') or 'state_*.sqlite'
		if Path(glob_raw).is_absolute():
			r = sorted((Path(p) for p in glob.glob(glob_raw, recursive=True) if Path(p).is_file()))
		elif None is home:
			r = []
		else:
			r = sorted((Path(p) for p in glob.glob((home / glob_raw).as_posix(), recursive=True) if Path(p).is_file()))
	else:
		r = sorted(dfh_local_uri_to_path(paths_or_home).glob('state_*.sqlite'))
	return r
