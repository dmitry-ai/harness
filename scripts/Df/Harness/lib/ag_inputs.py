# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.ag_wire import dfh_decode_user_step_entry
from Df.Harness.lib.request_binding import dfh_canonical_path, dfh_format_binding_diagnostic, dfh_native_project_id, dfh_review_project_id, dfh_scoped_inputs
from Df.Harness.lib.runtime_resolve import dfh_resolve_antigravity_paths
from Df.Harness.lib.trace_common import UUID_PATTERN, dfh_extract_resource_uri, dfh_iter_antigravity_subagents, dfh_local_uri_to_path, dfh_open_readonly_sqlite, dfh_parse_tool_args, dfh_read_jsonl_objects
from Df.Harness.lib.trace_review import dfh_current_turn_requests, dfh_require_turn_binding
import json
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
ANTIGRAVITY_MODEL_TIERS = ('flash_lite', 'flash', 'pro')
COMPLETED_STEP_STATUSES = (3, 5)
# @used-by :func:`dfh_extract_subagent_uuids()`
def _extract_event_direct_uuids(ev: dict, out: list[str]) -> bool:
	content = str(ev.get('content') or '')
	if ev.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and re.match('^\\s*(?:The following is a <SYSTEM_MESSAGE>[^\\n]*\\n+\\s*)?<SYSTEM_MESSAGE>', content):
		sys_header = re.split('\\bcontent=', content, maxsplit=1)[0]
		for m_u in re.findall(f'\\[Message\\]\\s+timestamp=[^\\n]*?\\bsender=({UUID_PATTERN})\\b', sys_header, flags=re.I) + re.findall(f'\\bSubagent\\b[^\\n]{{0,80}}?\\b({UUID_PATTERN})\\b', sys_header, flags=re.I):
			if m_u.lower() not in out:
				out.append(m_u.lower())
	calls = [c for c in ev.get('tool_calls') or () if isinstance(c, dict)]
	for call in calls:
		if 'send_message' == call.get('name'):
			recip = str(dfh_parse_tool_args(call.get('args', {})).get('Recipient') or '').strip().lower()
			if re.fullmatch(UUID_PATTERN, recip) and recip not in out:
				out.append(recip)
	return any(('invoke_subagent' == c.get('name') for c in calls))
# @used-by :func:`dfh_extract_subagent_uuids()`
def _extract_invoke_output_uuids(rows_list: list, pos: int, uuid_re, out: list[str]) -> None:
	for cand in rows_list[pos + 1:]:
		if not isinstance(cand, dict):
			continue
		if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
			break
		if 'GENERIC' == cand.get('type') and cand.get('content'):
			for m_u in _uuids_from_generic_text(str(cand.get('content')), uuid_re):
				if m_u.lower() not in out:
					out.append(m_u.lower())
# @used-by :func:`dfh_find_subagent_invocations()`
def _match_event_subagents(parent_rows: list, i: int, event: dict, child_id: str, agent_name: str, initial_prompt: str, require_inherit_error: str | None, matches: list, extra_messages: list) -> None:
	for call in event.get('tool_calls', []):
		if 'send_message' == call.get('name'):
			args = dfh_parse_tool_args(call.get('args', {}))
			if args.get('Recipient') == child_id and isinstance(args.get('Message'), str):
				extra_messages.append(args['Message'])
		for sub in dfh_iter_antigravity_subagents(call):
			if sub.get('TypeName') == agent_name and sub.get('Prompt') and (sub['Prompt'] in initial_prompt):
				raw_model = sub.get('Model')
				eff = raw_model.strip().lower() if isinstance(raw_model, str) and raw_model.strip() else 'inherit'
				if None is not require_inherit_error and 'inherit' != eff:
					raise ValueError(require_inherit_error)
				matches.append((event.get('step_index'), sub, i + 1 < len(parent_rows) and child_id in parent_rows[i + 1].get('content', '')))
# @used-by :func:`dfh_workspace_context()`
def _resolve_ws_context_entry(roots: list, p_roots: list[Path]) -> list:
	if not roots:
		r = [(-1, str(p_roots[0]), 'antigravity-project-id')] if 1 == len(p_roots) else []
	elif 1 < len(roots):
		r = [(-1, None, 'antigravity-workspace-uris')]
	else:
		w_path = dfh_canonical_path(dfh_local_uri_to_path(roots[0]))
		target = p_roots[0] if (not w_path.exists()) and 1 == len(p_roots) and p_roots[0].exists() else w_path
		r = [(-1, str(target), 'antigravity-project-id' if target != w_path else 'antigravity-workspace-uris')]
	return r
# @used-by :func:`_extract_invoke_output_uuids()`
# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_trace_effects_review_and_clarifications()`
def _uuids_from_generic_text(cand_text: str, uuid_re) -> list[str]:
	r: list[str] = []
	if not re.search('(?:^|\\n)(?:File Path:\\s*`?file://|Showing lines \\d+-\\d+ of \\d+|Partial read \\(lines \\d+-\\d+ of \\d+\\)|Command exited with code \\d+\\.|Tool is running as a background task)', cand_text):
		r = re.findall(f'"(?:conversationId|agent_id|subagent_id)"\\s*:\\s*"({UUID_PATTERN})"', cand_text, flags=re.I) + re.findall(f'\\b(?:Subagents?|subagents?|workers?|coordinators?)\\b[^\\n]{{0,80}}?\\b({UUID_PATTERN})\\b', cand_text, flags=re.I)
		if not r and re.fullmatch(f'\\s*({UUID_PATTERN})\\s*', cand_text, flags=re.I):
			r = uuid_re.findall(cand_text)
	return r
# @used-by :func:`Df.Harness.lib.ag_daemon.dfh_discover_live_daemon()`
# @used-by :func:`Df.Harness.lib.ag_metadata._match_log_path_to_instance()`
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_native_invocation()`
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_proof_paths()`
# @used-by :func:`agent_tools.platforms.antigravity._antigravity_paths()`
# @used-by :func:`dfh_native_requests()`
# @used-by :func:`dfh_request_scope()`
# @used-by :func:`dfh_require_current_binding()`
# @used-by :func:`dfh_workspace_context()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ExecutorMetadataReader.ExecutorMetadataReader.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TitleSyncer.TitleSyncer.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ToolTraceReader.ToolTraceReader.__resolve_paths()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__init__()`
def dfh_antigravity_paths(backend=None, *, instance=None, conversation_id=None, settings_fn=None) -> dict:
	load_cfg = settings_fn if None is not settings_fn else (lambda: SettingsLoader().run())
	try:
		cfg = load_cfg()
	except (OSError, ValueError):
		cfg = None
	return dfh_resolve_antigravity_paths(backend=backend, instance=instance, conversation_id=conversation_id, config=cfg, settings_fn=load_cfg)
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_model_metadata()`
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_query_step_model_ids()`
# @used-by :func:`dfh_native_inputs()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ToolTraceReader.ToolTraceReader.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__load_statuses_and_journal()`
def dfh_conversation_db_path(backend, conversation_id: str, *, error_msg: str='Exact native conversation UUID required', paths=None) -> Path:
	if not re.fullmatch('[a-f0-9-]{36}', conversation_id):
		raise ValueError(error_msg)
	conv_dir = Path(paths['conversations_dir']) if paths else Path(backend) / 'conversations'
	return conv_dir / (conversation_id + '.db')
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__collect_subagent_bfs()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__resolve_subagent_child()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue45_post_checkpoint_res_citation_and_issue48_recursive_subagent_aggregation()`
def dfh_extract_subagent_uuids(rows_slice: list) -> list[str]:
	r: list[str] = []
	rows_list = rows_slice if isinstance(rows_slice, list) else []
	uuid_re = re.compile(f'\\b({UUID_PATTERN})\\b', re.I)
	for pos, ev in enumerate(rows_list):
		if isinstance(ev, dict) and _extract_event_direct_uuids(ev, r):
			_extract_invoke_output_uuids(rows_list, pos, uuid_re, r)
	return r
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_native_invocation()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.__select_invocation()`
def dfh_find_subagent_invocations(parent_rows: list, child_id: str, agent_name: str, initial_prompt: str, *, require_inherit_error: str | None=None) -> tuple[list, list]:
	matches, extra_messages = ([], [])
	for i, event in enumerate(parent_rows):
		_match_event_subagents(parent_rows, i, event, child_id, agent_name, initial_prompt, require_inherit_error, matches, extra_messages)
	return (matches, extra_messages)
# @used-by :func:`dfh_native_inputs()`
def dfh_load_transcript_inputs(backend, conversation_id: str, *, paths=None) -> dict:
	brain_dir = Path(paths['brain_dir']) if paths else Path(backend) / 'brain'
	t_path = dfh_transcript_path(brain_dir, conversation_id)
	r: dict = {}
	if t_path.is_file():
		try:
			r = {obj.get('step_index'): obj for obj in dfh_read_jsonl_objects(t_path) if isinstance(obj, dict) and 'USER_INPUT' == obj.get('type')}
		except (OSError, ValueError):
			r = {}
	return r
# @used-by :func:`dfh_request_scope()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.__build_extra_fields()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__load_context()`
def dfh_native_inputs(backend, conversation_id: str, *, paths=None, include_meta: bool=False) -> list:
	db_path = dfh_conversation_db_path(backend, conversation_id, error_msg='Exact current native conversation UUID required', paths=paths)
	with dfh_open_readonly_sqlite(db_path) as conn:
		rows = conn.execute('SELECT idx,status,step_format,step_payload FROM steps WHERE step_type=14 AND status IN (3,5) ORDER BY idx').fetchall()
	cache: dict = {}
	r: list = []
	for index, status, format_id, payload in rows:
		if 0 != format_id:
			raise ValueError('Native request format is unsupported; save exact requests from the current chat, without reconstruction')
		text, meta = dfh_decode_user_step_entry(payload, status, index, lambda: cache.setdefault('rows', dfh_load_transcript_inputs(backend, conversation_id, paths=paths)))
		r.append((index, text, meta) if include_meta else (index, text))
	return r
# @used-by :func:`agent_tools.platforms.antigravity.native_requests()`
def dfh_native_requests(root, conversation_id: str, *, backend=None, instance=None, settings_fn=None) -> list[dict]:
	paths = dfh_antigravity_paths(backend=backend, instance=instance, conversation_id=conversation_id, settings_fn=settings_fn)
	selected, _, _ = dfh_request_scope(root, conversation_id, Path(paths['backend_dir']), paths=paths, settings_fn=settings_fn)
	return dfh_current_turn_requests(selected, conversation_id, 'antigravity-ui', 'Native Antigravity requests do not identify this project; open the chat in the exact project workspace or pass its /upwork-init URL')
# @used-by :func:`dfh_workspace_context()`
def dfh_project_roots(backend, project_id, *, paths=None) -> list[Path]:
	r: list[Path] = []
	if isinstance(project_id, str) and project_id.strip() and project_id not in ('outside-of-project', 'default-cli-project'):
		projects_dir = Path(paths['projects_dir']) if paths else Path(backend).resolve().parent / 'config/projects'
		candidate = projects_dir / f'{project_id}.json'
		if candidate.is_file():
			try:
				data = json.loads(candidate.read_text(encoding='utf-8-sig'))
				r = [dfh_canonical_path(dfh_local_uri_to_path(dfh_extract_resource_uri(res))) for res in (data.get('projectResources') or {}).get('resources') or () if dfh_extract_resource_uri(res)]
			except Exception:
				r = []
	return r
# @used-by :func:`agent_tools.platforms.antigravity._request_scope()`
# @used-by :func:`dfh_native_requests()`
# @used-by :func:`dfh_require_current_binding()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__load_context()`
def dfh_request_scope(root, conversation_id: str, backend, *, inputs=None, until=None, identifier=None, paths=None, contexts=None, settings_fn=None):
	job_id = identifier if None is not identifier else dfh_native_project_id(root)
	resolved = paths or dfh_antigravity_paths(backend=backend, conversation_id=conversation_id, settings_fn=settings_fn)
	eff_inputs = dfh_native_inputs(backend, conversation_id, paths=resolved, include_meta=True) if None is inputs else inputs
	eff_contexts = dfh_workspace_context(backend, conversation_id, paths=resolved, settings_fn=settings_fn) if None is contexts else contexts
	return dfh_scoped_inputs(root, job_id, eff_inputs, eff_contexts, until=until)
# @used-by :func:`agent_tools.platforms.antigravity.require_current_binding()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.__build_extra_fields()`
def dfh_require_current_binding(root, conversation_id: str, *, backend=None, instance=None, inputs=None, until=None, role: str='AA', settings_fn=None):
	paths = dfh_antigravity_paths(backend=backend, instance=instance, conversation_id=conversation_id, settings_fn=settings_fn)
	job_id = dfh_review_project_id(root, role=role)
	selected, active, binding = dfh_request_scope(root, conversation_id, Path(paths['backend_dir']), inputs=inputs, until=until, identifier=job_id, paths=paths, settings_fn=settings_fn)
	diag = dfh_format_binding_diagnostic(str(Path(root).resolve()), binding, expected_job_id=job_id)
	return dfh_require_turn_binding(selected, active, binding, f'Native Antigravity conversation is currently bound to another project or no exact project root ({diag})')
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_native_invocation()`
# @used-by :func:`dfh_load_transcript_inputs()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ToolTraceReader.ToolTraceReader.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__load_context()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__resolve_subagent_child()`
def dfh_transcript_path(brain_dir, conversation_id: str) -> Path:
	logs_dir = Path(brain_dir) / conversation_id / '.system_generated/logs'
	full_trace = logs_dir / 'transcript_full.jsonl'
	compact_trace = logs_dir / 'transcript.jsonl'
	return full_trace if full_trace.is_file() else (compact_trace if compact_trace.is_file() else full_trace)
# @used-by :func:`agent_tools.platforms.antigravity._workspace_context()`
# @used-by :func:`dfh_request_scope()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__load_context()`
def dfh_workspace_context(backend, conversation_id: str, *, paths=None, settings_fn=None) -> list:
	resolved = paths or dfh_antigravity_paths(backend=backend, conversation_id=conversation_id, settings_fn=settings_fn)
	file = Path(resolved['conversations_db'])
	r: list = []
	if file.is_file():
		with dfh_open_readonly_sqlite(file) as conn:
			columns = {row[1] for row in conn.execute('PRAGMA table_info(conversation_summaries)')}
			has_ws = 'workspace_uris' in columns
			sql = 'SELECT workspace_uris, project_id FROM conversation_summaries WHERE conversation_id=?' if 'project_id' in columns else 'SELECT workspace_uris, NULL FROM conversation_summaries WHERE conversation_id=?'
			row = conn.execute(sql, (conversation_id,)).fetchone() if has_ws else None
		if has_ws:
			roots = json.loads(row[0]) if row and row[0] else []
			project_id = row[1] if row and 1 < len(row) else None
			if not isinstance(roots, list) or any((not isinstance(rt, str) or (not rt.startswith('file://')) for rt in roots)):
				raise ValueError('Native Antigravity workspace_uris format is unsupported')
			r = _resolve_ws_context_entry(roots, dfh_project_roots(backend, project_id, paths=resolved))
	return r
