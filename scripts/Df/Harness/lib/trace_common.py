# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit
import json
import os
import re
import sqlite3
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
PRE_FLUSH_READER_HOOK: list[Any] = [None]
UUID_PATTERN = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
_WAIT_STUB_EN_RE = re.compile(r'(?i)(?:^|\n|\.\s+)\s*waiting\s+for\s+(?:the\s+)?(?:remaining\s+)?(?:\d+\s+)?(?:subagents?|background\s+tasks?|tasks?|commands?|test\s+runs?|tests?|suites?)\b[^\n]{0,140}\bto\s+(?:complete|finish)\b')
_WAIT_STUB_FENCE_RE = re.compile(r'```[\s\S]*?```')
_WAIT_STUB_QUOTE_RE = re.compile(r'\u00ab[^\u00bb]{0,400}\u00bb')
_WAIT_STUB_RU_BG_RE = re.compile(r'(?i)(?:^|\n)\s*(?:\u043f\u043e\u043b\u043d\u044b\u0439\s+\u043f\u0440\u043e\u0433\u043e\u043d|\u043f\u0440\u043e\u0433\u043e\u043d\s+\u0442\u0435\u0441\u0442\u043e\u0432|\u0444\u043e\u043d\u043e\u0432\u0430\u044f\s+\u0437\u0430\u0434\u0430\u0447\u0430|\u0437\u0430\u0434\u0430\u0447\u0430|\u043a\u043e\u043c\u0430\u043d\u0434\u0430)\b[^\n]{0,160}\b\u0437\u0430\u043f\u0443\u0449\u0435\u043d[\u0430\u043e]?\s+\u0432\s+\u0444\u043e\u043d\u0435\b')
_WAIT_STUB_RU_RE = re.compile(r'(?i)(?:^|\n|[.;]\s*)\s*(?:\u043e\u0436\u0438\u0434\u0430\u044e|\u0436\u0434\u0443)\s+(?:\u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438[\u044f\u044e]|\u043e\u043a\u043e\u043d\u0447\u0430\u043d\u0438[\u044f\u044e]|\u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u0438[\u044f\u044e]|\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442(?:\u0430|\u043e\u0432)?)\s+(?:\u043e\u0441\u0442\u0430\u0432\u0448\w*\s+|\u0444\u043e\u043d\u043e\u0432\w*\s+|\u043f\u043e\u043b\u043d\w*\s+)?(?:\d+\s+)?(?:\u0441\u0443\u0431-?\u0430\u0433\u0435\u043d\u0442\w*|\u0437\u0430\u0434\u0430\u0447\w*|\u043a\u043e\u043c\u0430\u043d\u0434\w*|\u043f\u0440\u043e\u0433\u043e\u043d\w*|\u0442\u0435\u0441\u0442\w*|\u043f\u0440\u043e\u0432\u0435\u0440\u043a\w*)')
# @used-by :func:`dfh_local_uri_to_path()`
def _strip_win_extended_prefix(text: str) -> str:
	r = text
	if text.startswith('\\\\?\\UNC\\'):
		r = '\\\\' + text[8:]
	elif text.startswith('\\\\?\\'):
		r = text[4:]
	return r
# @used-by :func:`Df.Harness.lib.ag_daemon.dfh_project_item_matches_root()`
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_project_roots()`
# @used-by :func:`Df.Harness.lib.cleanup_store_ops._match_ag_project_file()`
# @used-by :func:`Df.Harness.lib.cleanup_store_ops._parse_pending_ag_entry()`
# @used-by :meth:`Df.Harness.Project.RegistrationValidator.RegistrationValidator.__check_antigravity()`
def dfh_extract_resource_uri(res) -> str | None:
	r = None
	if isinstance(res, dict):
		cand = res.get('folderUri') or (res.get('gitFolder') or {}).get('folderUri') or (res.get('folder') or {}).get('folderUri')
		if isinstance(cand, str) and cand.strip():
			r = cand
	return r
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_intermediate_or_language_issues()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__resolve_segment_completion()`
# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.antigravity_segment_is_interrupted()`
# @used-by :meth:`test_background_wait_and_tdd_inheritance.BackgroundWaitAndTddInheritanceTests.test_waiting_stub_classifier_handles_ru_en_and_avoids_false_positives()`
def dfh_is_waiting_status_stub(text: str) -> bool:
	r = False
	raw = (text or '').strip()
	if raw:
		cleaned = _WAIT_STUB_QUOTE_RE.sub('', _WAIT_STUB_FENCE_RE.sub('', raw)).strip()
		if cleaned and (not re.search(r'(?m)^#{1,3}\s+', cleaned)) and 600 >= len(cleaned):
			r = bool(_WAIT_STUB_EN_RE.search(cleaned) or _WAIT_STUB_RU_RE.search(cleaned) or _WAIT_STUB_RU_BG_RE.search(cleaned))
	return r
# @used-by :func:`Df.Harness.lib.ag_inputs._match_event_subagents()`
# @used-by :func:`Df.Harness.lib.trace_effects._track_invoke_subagent()`
# @used-by :meth:`test_turn_completion.TraceCommonTests.test_iter_antigravity_subagents_and_kb_persistence_parity()`
def dfh_iter_antigravity_subagents(call) -> list[dict]:
	r: list[dict] = []
	if isinstance(call, dict) and 'invoke_subagent' == call.get('name'):
		args = dfh_parse_tool_args(call.get('args', {}))
		if args:
			raw_subs = args.get('Subagents', [])
			invalid_subs = False
			if not isinstance(raw_subs, str):
				subs = raw_subs
			else:
				try:
					subs = json.loads(raw_subs)
				except ValueError:
					subs, invalid_subs = ([], True)
			if not subs and (not invalid_subs):
				subs = [args]
			if isinstance(subs, list):
				r = [sub for sub in subs if isinstance(sub, dict)]
	return r
# @used-by :func:`Df.Harness.lib.ag_daemon.dfh_project_item_matches_root()`
# @used-by :func:`Df.Harness.lib.ag_inputs._resolve_ws_context_entry()`
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_project_roots()`
# @used-by :func:`Df.Harness.lib.cleanup_store_ops.dfh_path_key()`
# @used-by :func:`Df.Harness.lib.codex_trace._collect_codex_user_inputs()`
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_request_scope()`
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_trace()`
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_state_db_files()`
# @used-by :func:`Df.Harness.lib.hook_pre_invocation_ops.dfh_resolve_hook_root()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__index_db_threads()`
# @used-by :meth:`Df.Harness.Project.RegistrationValidator.RegistrationValidator.__check_antigravity()`
def dfh_local_uri_to_path(value, *, require_absolute: bool=False) -> Path:
	raw = os.fspath(value) if isinstance(value, os.PathLike) else value
	if not isinstance(raw, str) or (not raw):
		raise ValueError('Missing workspace path')
	if raw.startswith('file:'):
		uri = urlsplit(raw)
		raw = unquote(uri.path)
		host = unquote(uri.netloc)
		if re.fullmatch('[A-Za-z]:', host):
			raw = host + raw
		elif host and 'localhost' != host.casefold():
			raw = '//' + host + raw
		if re.match('^/[A-Za-z]:/', raw):
			raw = raw[1:]
	raw = _strip_win_extended_prefix(raw)
	if require_absolute and (not Path(raw).is_absolute()):
		raise ValueError('Workspace path must be absolute')
	return Path(_strip_win_extended_prefix(str(Path(raw).resolve())))
# @used-by :func:`Df.Harness.lib.ag_daemon._read_db_title()`
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_native_inputs()`
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_workspace_context()`
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_model_metadata()`
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_native_invocation()`
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_query_step_model_ids()`
# @used-by :func:`Df.Harness.lib.ag_review_wait._is_reviewer_in_flight()`
# @used-by :func:`Df.Harness.lib.ag_review_wait._probe_reviewer_final()`
# @used-by :func:`Df.Harness.lib.cleanup_lifecycle_ops.dfh_load_codex_history_rows()`
# @used-by :func:`Df.Harness.lib.cleanup_store_ops._read_ag_rows()`
# @used-by :func:`Df.Harness.lib.codex_trace._find_codex_thread_row()`
# @used-by :meth:`Df.Harness.Meta.TranscriptReader.TranscriptReader.read_ag_summary_row()`
# @used-by :meth:`Df.Harness.Perf.TimesheetCommon.TimesheetCommon.read_summary_timestamps()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.__verify_child_summary()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ToolTraceReader.ToolTraceReader.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__db_child_seeds()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__load_context()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__load_statuses_and_journal()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__query_child_summary()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__index_db_threads()`
@contextmanager
def dfh_open_readonly_sqlite(db_path, *, guard=None, query_only: bool=False, row_factory=None, timeout=None):
	path = Path(db_path)
	if None is not guard:
		guard(path)
	kw: dict[str, Any] = {'uri': True}
	if None is not timeout:
		kw['timeout'] = timeout
	conn = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', **kw)
	try:
		if None is not row_factory:
			conn.row_factory = row_factory
		if query_only:
			conn.execute('PRAGMA query_only=ON')
		yield conn
	finally:
		conn.close()
# @used-by :func:`Df.Harness.lib.ag_inputs._extract_event_direct_uuids()`
# @used-by :func:`Df.Harness.lib.ag_inputs._match_event_subagents()`
# @used-by :func:`Df.Harness.lib.clarifications_ops._extract_question_texts()`
# @used-by :func:`Df.Harness.lib.codex_metadata.dfh_codex_spawn()`
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_extract_codex_target_subagents()`
# @used-by :func:`Df.Harness.lib.completion_child_trace._handle_child_call_item()`
# @used-by :func:`Df.Harness.lib.completion_child_trace._process_tool_calls_row()`
# @used-by :func:`Df.Harness.lib.trace_effects.dfh_record_normalized_tool_effects()`
# @used-by :func:`Df.Harness.lib.trace_review._ag_calls_from_row()`
# @used-by :func:`Df.Harness.lib.trace_review._codex_calls_from_row()`
# @used-by :func:`dfh_iter_antigravity_subagents()`
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__record_ag_tool_calls()`
# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__record_tool_call()`
# @used-by :meth:`Df.Harness.Perf.CodexTimesheetAnalyzer.CodexTimesheetAnalyzer.__record_codex_call()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ToolTraceReader.ToolTraceReader.__extract_step_event()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__record_one_tool_call()`
# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.__collect_matched_prompts()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_subagent_call()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_tool_call_row()`
def dfh_parse_tool_args(raw) -> dict:
	parsed = raw
	if isinstance(raw, str):
		try:
			parsed = json.loads(raw)
		except ValueError:
			parsed = {}
	return parsed if isinstance(parsed, dict) else {}
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_load_transcript_inputs()`
# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_native_invocation()`
# @used-by :func:`Df.Harness.lib.ag_review_wait._probe_reviewer_final()`
# @used-by :func:`Df.Harness.lib.ag_review_wait.dfh_reviewer_assigned_package()`
# @used-by :func:`Df.Harness.lib.completion_child_trace.dfh_scan_child_trace_turn()`
# @used-by :func:`Df.Harness.lib.hook_pre_invocation_ops.dfh_pre_flush_begin_context()`
# @used-by :func:`agent_tools.platforms.antigravity._ag_ops()`
# @used-by :meth:`Df.Harness.Meta.TranscriptReader.TranscriptReader.read_ag_rows()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ToolTraceReader.ToolTraceReader.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__load_context()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__resolve_subagent_child()`
def dfh_read_jsonl_objects(source, *, partial_error=None) -> list:
	hook = PRE_FLUSH_READER_HOOK[0]
	if None is not hook:
		r = hook(source, partial_error=partial_error)
	else:
		text = source.decode('utf-8') if isinstance(source, (bytes, bytearray)) else Path(source).read_text(encoding='utf-8')
		try:
			r = [json.loads(line) for line in text.splitlines() if line.strip()]
		except ValueError as exc:
			if None is not partial_error:
				raise ValueError(partial_error) from exc
			raise
	return r
