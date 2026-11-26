# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any
from . import identity, transcripts
from .blocks import _build_agent_block, _build_journal_block, _build_journal_trace, _build_time_block, _build_trace_block, _build_turn_trace, _conversation_label, _resolve_conversation_steps, _resolve_hook
from .formatting import _UUID_RE, _split_model_and_effort, format_local_timestamp, parse_timestamp
import os
import re
# 2026-11-24
# "Add structured problem metadata builder and CLI command":
# https://github.com/dmitry-ai/harness/issues/180
_GITHUB_ISSUE_URL_RE = re.compile(r'^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+$')
# 2026-11-24
# "Decompose metadata.py into modular metadata collection package":
# https://github.com/dmitry-ai/harness/issues/170
_HOOKS: dict[str, tuple[Any, Any]] = {
	'_ag_transcript_file': (transcripts, transcripts._ag_transcript_file),
	'_extract_ag_transcript_info': (transcripts, transcripts._extract_ag_transcript_info),
	'_extract_codex_transcript_info': (transcripts, transcripts._extract_codex_transcript_info),
	'_read_ag_summary_row': (transcripts, transcripts._read_ag_summary_row),
	'_resolve_ag_model_and_effort': (transcripts, transcripts._resolve_ag_model_and_effort),
	'_resolve_ag_paths_safe': (identity, identity._resolve_ag_paths_safe),
	'_resolve_codex_paths_safe': (identity, identity._resolve_codex_paths_safe),
	'resolve_project_identity': (identity, identity.resolve_project_identity),
}
# @used-by :func:`build_github_issue_metadata()`
def _apply_issue_state_details(state_path: Path | None, state_obj: dict[str, Any] | None, canon_root: Path | None, platform: str | None, ctx: dict[str, Any]) -> dict[str, Any]:
	from .. import journal
	out: dict[str, Any] = {'group_file': None, 'jdir': None, 'start_step': None, 'state_path': state_path, 'steps': [], 'turn_id': None, 'turn_key': None}
	if isinstance(state_obj, dict):
		out['turn_key'] = str(state_obj.get('key') or state_path.stem) if None is not state_path else state_obj.get('key')
		out['turn_id'] = state_obj.get('native_turn_id')
		out['start_step'] = state_obj['native_start_step'] if isinstance(state_obj.get('native_start_step'), int) else None
		out['steps'] = transcripts._extract_turn_steps_from_state(state_obj)
		out['jdir'] = journal.canonicalize_journal_dir_identity(state_obj['journal']) if state_obj.get('journal') else (journal.resolve_journal_dir(canon_root) if None is not canon_root else None)
		out['group_file'] = _resolve_issue_group_file(state_obj, out['jdir'], out['turn_key'])
		_refine_issue_ctx_from_state(platform, ctx, out['turn_id'], out['start_step'])
	return out
# @used-by :func:`build_github_issue_metadata()`
# @used-by :func:`build_journal_metadata()`
def _assemble_optional_blocks(base: dict[str, Any], extras: tuple[tuple[str, dict[str, Any] | None], ...]) -> dict[str, Any]:
	for key, val in extras:
		if val:
			base[key] = val
	return base
# @used-by :func:`_collect_issue_env_ctx()`
# @used-by :func:`agent_tools.issues.turn_scope._resolve_antigravity_parent_cid()`
def _collect_ag_issue_ctx(environ: dict[str, str], active_cid: str) -> dict[str, Any]:
	ag_backend_env = str(environ.get('ANTIGRAVITY_APP_DATA_DIR') or '').strip() or None
	ag_inst_env = str(environ.get('ANTIGRAVITY_ACCOUNT') or '').strip() or None
	ag_paths = _fn('_resolve_ag_paths_safe')(backend=ag_backend_env, instance=ag_inst_env, conversation_id=active_cid)
	if None is ag_paths and ag_backend_env:
		bp = Path(ag_backend_env).resolve()
		ag_paths = {'instance': ag_inst_env, 'backend_dir': bp, 'brain_dir': bp / 'brain', 'conversations_db': bp / 'conversation_summaries.db', 'conversations_dir': bp / 'conversations', 'projects_dir': bp.parent / 'config/projects'}
	active_row = _fn('_read_ag_summary_row')(ag_paths, active_cid)
	parent_cid = str(active_row.get('parent_conversation_id') or '').strip().lower() if isinstance(active_row, dict) else ''
	subagent_cid = active_cid if parent_cid else None
	primary_cid = parent_cid if parent_cid else active_cid
	summary_row = (_fn('_read_ag_summary_row')(ag_paths, primary_cid) or active_row) if parent_cid else active_row
	t_path = _fn('_ag_transcript_file')(ag_paths, active_cid)
	model, effort = _fn('_resolve_ag_model_and_effort')(ag_paths, active_cid, transcript_path=t_path)
	inst_id = (ag_paths.get('instance') if isinstance(ag_paths, dict) else None) or ag_inst_env
	return {'ag_paths': ag_paths, 'effort': effort, 'instance_id': inst_id, 'model': model, 'primary_cid': primary_cid, 'subagent_cid': subagent_cid, 'summary_row': summary_row, 'transcript_path': t_path, 'turn_index': None}
# @used-by :func:`_collect_issue_env_ctx()`
def _collect_codex_issue_ctx(environ: dict[str, str], active_cid: str) -> dict[str, Any]:
	cx_home_env = str(environ.get('CODEX_HOME') or '').strip() or None
	cx_paths = _fn('_resolve_codex_paths_safe')(backend=cx_home_env, conversation_id=active_cid)
	instance_id = cx_paths.get('instance') if isinstance(cx_paths, dict) else None
	try:
		from ..runtime import _codex_home_conversation_trace
		trace_str = _codex_home_conversation_trace(cx_paths.get('home') if isinstance(cx_paths, dict) else cx_home_env, active_cid, system_paths=cx_paths)
		t_path: Path | None = Path(trace_str).resolve() if trace_str else None
	except Exception:
		t_path = None
	c_info = _fn('_extract_codex_transcript_info')(t_path) if None is not t_path else {}
	return {'ag_paths': None, 'effort': c_info.get('effort'), 'instance_id': instance_id, 'model': c_info.get('model'), 'primary_cid': active_cid, 'subagent_cid': None, 'summary_row': None, 'transcript_path': t_path, 'turn_index': c_info.get('turn_index')}
# @used-by :func:`build_github_issue_metadata()`
def _collect_issue_env_ctx(environ: dict[str, str], platform: str | None, active_cid: str | None) -> dict[str, Any]:
	if 'antigravity' == platform and active_cid:
		r = _collect_ag_issue_ctx(environ, active_cid)
	elif 'codex' == platform and active_cid:
		r = _collect_codex_issue_ctx(environ, active_cid)
	else:
		r = {'ag_paths': None, 'effort': None, 'instance_id': None, 'model': None, 'primary_cid': active_cid, 'subagent_cid': None, 'summary_row': None, 'transcript_path': None, 'turn_index': None}
	return r
# @used-by :func:`build_journal_metadata()`
def _collect_journal_turn_state(platform: str, cid: str, ag_paths: dict[str, Any] | None, summary_row: dict[str, Any] | None, native: dict[str, Any], turn: dict[str, Any], request_at: Any, response_at: Any) -> dict[str, Any]:
	model, effort = _split_model_and_effort(turn.get('model'), turn.get('effort'))
	state: dict[str, Any] = {
		'effort': effort,
		'final_step': turn.get('final_step') if isinstance(turn.get('final_step'), int) else None,
		'model': model,
		'req_ts': request_at or turn.get('request_timestamp'),
		'res_ts': response_at or turn.get('response_timestamp'),
		'start_step': turn.get('start_step') if isinstance(turn.get('start_step'), int) else None,
		'turn_index': _resolve_turn_index(turn, native),
	}
	if 'antigravity' == platform:
		_enrich_journal_ag(cid, ag_paths, summary_row, native.get('source_file'), state)
	elif 'codex' == platform:
		_enrich_journal_codex(native.get('source_file'), turn.get('turn_id'), state)
	return state
# @used-by :func:`agent_tools.issues.turn_scope.detect_active_session()`
# @used-by :func:`build_github_issue_metadata()`
def _detect_env_platform(environ: dict[str, str]) -> tuple[str | None, str | None, int | None]:
	meta_cid, tool_step = transcripts._parse_antigravity_source_metadata(environ)
	ag_cid = str(environ.get('ANTIGRAVITY_CONVERSATION_ID') or '').strip().lower() or meta_cid or ''
	cx_cid = str(environ.get('CODEX_THREAD_ID') or '').strip().lower()
	if ag_cid and _UUID_RE.fullmatch(ag_cid):
		r: tuple[str | None, str | None, int | None] = ('antigravity', ag_cid, tool_step)
	elif cx_cid and _UUID_RE.fullmatch(cx_cid):
		r = ('codex', cx_cid, tool_step)
	else:
		r = (None, None, tool_step)
	return r
# @used-by :func:`_collect_journal_turn_state()`
def _enrich_journal_ag(cid: str, ag_paths: dict[str, Any] | None, summary_row: dict[str, Any] | None, source_file: Any, state: dict[str, Any]) -> None:
	t_path = source_file or (_fn('_ag_transcript_file')(ag_paths, cid) if cid else None)
	if None is state['req_ts'] or None is state['model'] or None is state['effort'] or None is state['turn_index']:
		t_info = _fn('_extract_ag_transcript_info')(t_path, start_step=state['start_step'], final_step=state['final_step'])
		_merge_transcript_fields(state, t_info)
		if None is state['model'] or None is state['effort']:
			fb_m, fb_e = _fn('_resolve_ag_model_and_effort')(ag_paths, cid, transcript_path=t_path, start_step=state['start_step'])
			state['model'] = state['model'] or fb_m
			state['effort'] = state['effort'] or fb_e
	if None is state['req_ts'] and isinstance(summary_row, dict) and summary_row.get('last_user_input_time'):
		state['req_ts'] = summary_row.get('last_user_input_time')
# @used-by :func:`_collect_journal_turn_state()`
def _enrich_journal_codex(source_file: Any, turn_id: Any, state: dict[str, Any]) -> None:
	if None is state['req_ts'] or None is state['model'] or None is state['effort'] or None is state['turn_index']:
		c_info = _fn('_extract_codex_transcript_info')(source_file, turn_id=turn_id, start_step=state['start_step'], final_step=state['final_step'])
		_merge_transcript_fields(state, c_info, include_model=True)
# @used-by :func:`build_github_issue_metadata()`
def _find_issue_state_pair(canon_root: Path | None, primary_cid: str | None) -> tuple[Path | None, dict[str, Any] | None]:
	r: tuple[Path | None, dict[str, Any] | None] = (None, None)
	if None is not canon_root and primary_cid:
		try:
			from ..path_registry import project_paths
			hit = transcripts._find_turn_state_for_conversation(project_paths(canon_root, exact_root=True).turns_dir, primary_cid)
			if None is not hit:
				r = hit
		except (OSError, ValueError):
			r = (None, None)
	return r
# @used-by :func:`_collect_ag_issue_ctx()`
# @used-by :func:`_collect_codex_issue_ctx()`
# @used-by :func:`_enrich_journal_ag()`
# @used-by :func:`_enrich_journal_codex()`
# @used-by :func:`_refine_issue_ctx_from_state()`
# @used-by :func:`_resolve_journal_platform()`
# @used-by :func:`build_github_issue_metadata()`
# @used-by :func:`build_journal_metadata()`
# @used-by :func:`build_problem_metadata()`
def _fn(name: str) -> Any:
	mod, default = _HOOKS[name]
	return _resolve_hook(name, mod, default)
# @used-by :func:`_enrich_journal_ag()`
# @used-by :func:`_enrich_journal_codex()`
def _merge_transcript_fields(state: dict[str, Any], info: dict[str, Any], *, include_model: bool=False) -> None:
	for dst, src in (('req_ts', 'request_timestamp'), ('res_ts', 'response_timestamp'), ('turn_index', 'turn_index')):
		if None is state[dst]:
			state[dst] = info.get(src)
	if include_model:
		state['model'] = state['model'] or info.get('model')
		state['effort'] = state['effort'] or info.get('effort')
# 2026-11-24
# "Add structured problem metadata builder and CLI command":
# https://github.com/dmitry-ai/harness/issues/180
# @used-by :func:`build_problem_metadata()`
def _normalize_problem_issue_url(issue_url: str | None, *, allow_no_issue: bool) -> str | None:
	raw = str(issue_url or '').strip().rstrip('/')
	if not raw:
		if not allow_no_issue:
			raise ValueError('Problem metadata requires a GitHub issue URL (mandatory "Issue" key); pass --issue <URL> or --no-issue for non-GitHub workspaces')
		r: str | None = None
	elif not _GITHUB_ISSUE_URL_RE.fullmatch(raw):
		raise ValueError(f'Invalid GitHub issue URL for problem metadata: {issue_url}')
	else:
		r = raw
	return r
# @used-by :func:`_apply_issue_state_details()`
def _refine_issue_ctx_from_state(platform: str | None, ctx: dict[str, Any], turn_id: Any, start_step: int | None) -> None:
	if 'antigravity' == platform and ctx['primary_cid']:
		p_trans = _fn('_ag_transcript_file')(ctx['ag_paths'], ctx['primary_cid'])
		p_info = _fn('_extract_ag_transcript_info')(p_trans, start_step=start_step)
		if isinstance(p_info.get('turn_index'), int):
			ctx['turn_index'] = p_info['turn_index']
	elif 'codex' == platform and None is not ctx['transcript_path']:
		c_info = _fn('_extract_codex_transcript_info')(ctx['transcript_path'], turn_id=turn_id, start_step=start_step)
		if isinstance(c_info.get('turn_index'), int):
			ctx['turn_index'] = c_info['turn_index']
		ctx['model'] = ctx['model'] or c_info.get('model')
		ctx['effort'] = ctx['effort'] or c_info.get('effort')
# @used-by :func:`_apply_issue_state_details()`
def _resolve_issue_group_file(state_obj: dict[str, Any], jdir: Path | None, turn_key: str | None) -> Path | None:
	from .. import journal
	r: Path | None = None
	for slot in ('prepared', 'journal_record', 'delivery'):
		rec = state_obj.get(slot)
		if isinstance(rec, dict) and rec.get('group_file'):
			r = Path(rec['group_file'])
			break
	if None is r and None is not jdir and turn_key:
		r = journal.state_dir(jdir) / 'answer-groups' / f'native-{turn_key}.json'
	return r
# @used-by :func:`build_journal_metadata()`
def _resolve_journal_platform(platform: str, native: dict[str, Any], cid: str) -> tuple[dict[str, Any] | None, Any, dict[str, Any] | None]:
	backend_raw, inst = (native.get('native_backend'), native.get('instance'))
	ag_paths = _fn('_resolve_ag_paths_safe')(backend=backend_raw, instance=inst, conversation_id=cid) if 'antigravity' == platform else None
	cx_paths = _fn('_resolve_codex_paths_safe')(backend=backend_raw, instance=inst, conversation_id=cid) if 'codex' == platform else None
	instance_id = inst or (ag_paths.get('instance') if isinstance(ag_paths, dict) else None) or (cx_paths.get('instance') if isinstance(cx_paths, dict) else None)
	summary_row = _fn('_read_ag_summary_row')(ag_paths, cid) if 'antigravity' == platform and cid else None
	return (ag_paths, instance_id, summary_row)
# @used-by :func:`_collect_journal_turn_state()`
def _resolve_turn_index(turn: dict[str, Any], native: dict[str, Any]) -> Any:
	r = turn.get('turn_index')
	if not isinstance(r, int) or 1 > r:
		for idx, item in enumerate(native.get('turns') or (), 1):
			if isinstance(item, dict) and item.get('turn_id') == turn.get('turn_id'):
				r = idx
				break
	return r
# @used-by :func:`agent_tools.cleanup_audit.build_cleanup_metadata()`
# @used-by :func:`build_problem_metadata()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._prepend_issue_metadata()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_build_github_issue_metadata_live_env_child_subagent_and_standalone()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_builders_honor_facade_monkeypatch_seam_and_match_metadata_parity()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def build_github_issue_metadata(*, issue_url: str, project_root: str | Path | None=None, env: dict[str, str] | None=None, now: datetime | str | None=None, tz=None) -> dict[str, Any]:
	from ..path_registry import canonicalize_root_dir
	environ = dict(os.environ) if None is env else dict(env)
	platform, active_cid, tool_step = _detect_env_platform(environ)
	ctx = _collect_issue_env_ctx(environ, platform, active_cid)
	canon_root = canonicalize_root_dir(project_root) if None is not project_root and str(project_root).strip() else None
	state_path, state_obj = _find_issue_state_pair(canon_root, ctx['primary_cid'])
	st = _apply_issue_state_details(state_path, state_obj, canon_root, platform, ctx)
	summary_row = ctx['summary_row']
	env_pid = str(environ.get('ANTIGRAVITY_PROJECT_ID') or '').strip() or (summary_row.get('project_id') if isinstance(summary_row, dict) else None)
	project_info = _fn('resolve_project_identity')(canon_root, ag_paths=ctx['ag_paths'], project_id=env_pid) if None is not canon_root else None
	conv_steps = _resolve_conversation_steps(canon_root, st['jdir'], ctx['primary_cid'])
	conv_label = _conversation_label(summary_title=summary_row.get('title') if isinstance(summary_row, dict) else None, conversation_steps=conv_steps, current_steps=st['steps'])
	turn_trace = _build_turn_trace(turn_index=ctx['turn_index'], turn_id=st['turn_id'], turn_key=st['turn_key'], start_step=st['start_step'], tool_step=tool_step, state_path=st['state_path'])
	journal_trace = _build_journal_trace(st['jdir'], st['steps'], st['group_file'], require_steps=True)
	trace_block = _build_trace_block(cid=ctx['primary_cid'], subagent_cid=ctx['subagent_cid'], turn_trace=turn_trace, journal_trace=journal_trace, transcript_path=ctx['transcript_path'])
	extras = (('Project', project_info), ('Journal', _build_journal_block(st['steps'], conv_label)), ('Agent', _build_agent_block(platform, ctx['instance_id'], ctx['model'], ctx['effort'])), ('Trace', trace_block))
	return _assemble_optional_blocks({'Time': format_local_timestamp(now, tz=tz), 'Issue': str(issue_url)}, extras)
# @used-by :func:`agent_tools.completion._record()`
# @used-by :func:`agent_tools.stop_emergency_capture._build_emergency_response()`
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_build_journal_metadata_for_antigravity_and_codex()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_builders_honor_facade_monkeypatch_seam_and_match_metadata_parity()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def build_journal_metadata(root: str | Path, native: dict[str, Any], turn: dict[str, Any], *, journal_dir: str | Path, steps: list[int], turn_key: str, turn_state_path: str | Path | None=None, group_file: str | Path | None=None, conversation_steps: list[int] | None=None, request_at: datetime | str | None=None, response_at: datetime | str | None=None, tz=None) -> dict[str, Any]:
	from ..path_registry import canonicalize_root_dir, project_paths
	canon_root = canonicalize_root_dir(root)
	pp, jdir = (project_paths(canon_root, exact_root=True), Path(journal_dir).resolve())
	platform = str(native.get('platform') or '').strip().lower()
	cid = str(native.get('conversation_id') or '').strip()
	ag_paths, instance_id, summary_row = _resolve_journal_platform(platform, native, cid)
	project_info = _fn('resolve_project_identity')(canon_root, ag_paths=ag_paths, project_id=summary_row.get('project_id') if isinstance(summary_row, dict) else None)
	state = _collect_journal_turn_state(platform, cid, ag_paths, summary_row, native, turn, request_at, response_at)
	time_block = _build_time_block(parse_timestamp(state['req_ts']), parse_timestamp(state['res_ts']) or datetime.now().astimezone(), tz)
	conv_steps = _resolve_conversation_steps(canon_root, jdir, cid) if None is conversation_steps else conversation_steps
	conv_label = _conversation_label(summary_title=summary_row.get('title') if isinstance(summary_row, dict) else None, conversation_steps=conv_steps, current_steps=steps)
	state_p = Path(turn_state_path) if None is not turn_state_path else (pp.turns_dir / f'{turn_key}.json')
	turn_trace = _build_turn_trace(turn_index=state['turn_index'], turn_id=turn.get('turn_id'), turn_key=turn_key, start_step=state['start_step'], final_step=state['final_step'], state_path=state_p, canon_root=canon_root)
	journal_trace = _build_journal_trace(jdir, steps, group_file, canon_root=canon_root)
	trace_block = _build_trace_block(cid=cid, turn_trace=turn_trace, journal_trace=journal_trace, transcript_path=native.get('source_file'))
	extras = (('Journal', _build_journal_block(steps, conv_label)), ('Agent', _build_agent_block(platform, instance_id, state['model'], state['effort'])), ('Trace', trace_block))
	return _assemble_optional_blocks({'Time': time_block, 'Project': project_info}, extras)
# 2026-11-24
# "Add structured problem metadata builder and CLI command":
# https://github.com/dmitry-ai/harness/issues/180
# @used-by :func:`agent_tools.cli_registry._exec_problem_metadata()`
# @used-by :meth:`test_problem_metadata.ProblemMetadataTests.test_build_problem_metadata_allow_no_issue_keeps_mandatory_issue_key()`
# @used-by :meth:`test_problem_metadata.ProblemMetadataTests.test_build_problem_metadata_rejects_missing_or_invalid_issue_url()`
# @used-by :meth:`test_problem_metadata.ProblemMetadataTests.test_build_problem_metadata_with_issue_url_and_distinct_source_project()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def build_problem_metadata(*, issue_url: str | None=None, project_root: str | Path | None=None, source_project_root: str | Path | None=None, allow_no_issue: bool=False, env: dict[str, str] | None=None, now: datetime | str | None=None, tz=None) -> dict[str, Any]:
	from ..path_registry import canonicalize_root_dir
	clean_url = _normalize_problem_issue_url(issue_url, allow_no_issue=allow_no_issue)
	meta = build_github_issue_metadata(issue_url=clean_url or '', project_root=project_root, env=env, now=now, tz=tz)
	meta['Issue'] = clean_url
	if None is not source_project_root and str(source_project_root).strip():
		src_canon = canonicalize_root_dir(source_project_root)
		proj_canon = canonicalize_root_dir(project_root) if None is not project_root and str(project_root).strip() else None
		if src_canon != proj_canon:
			src_info = _fn('resolve_project_identity')(src_canon)
			ordered: dict[str, Any] = {}
			for key, val in meta.items():
				ordered[key] = val
				if 'Project' == key:
					ordered['Source Project'] = src_info
			if 'Source Project' not in ordered:
				ordered['Source Project'] = src_info
			meta = ordered
	return meta
