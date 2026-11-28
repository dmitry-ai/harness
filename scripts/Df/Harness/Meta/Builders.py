# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any
from Df.Harness.Meta.Blocks import Blocks
from Df.Harness.Meta.ProjectIdentity import ProjectIdentity
from Df.Harness.Meta.TimestampFormatter import TimestampFormatter
from Df.Harness.Meta.TranscriptReader import TranscriptReader
import os
import re
import sys
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Builders:
	__GITHUB_ISSUE_URL_RE = re.compile(r'^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+$')
	__HOOK_TARGETS = {
		'_ag_transcript_file': ('agent_tools.meta.transcripts', TranscriptReader.ag_transcript_file),
		'_extract_ag_transcript_info': ('agent_tools.meta.transcripts', lambda p, **kw: TranscriptReader(p).extract_ag_info(**kw)),
		'_extract_codex_transcript_info': ('agent_tools.meta.transcripts', TranscriptReader.extract_codex_info),
		'_read_ag_summary_row': ('agent_tools.meta.transcripts', TranscriptReader.read_ag_summary_row),
		'_resolve_ag_model_and_effort': ('agent_tools.meta.transcripts', TranscriptReader.resolve_ag_model_and_effort),
		'_resolve_ag_paths_safe': ('agent_tools.meta.identity', ProjectIdentity.resolve_ag_paths_safe),
		'_resolve_codex_paths_safe': ('agent_tools.meta.identity', ProjectIdentity.resolve_codex_paths_safe),
		'resolve_project_identity': ('agent_tools.meta.identity', lambda r, **kw: ProjectIdentity(r, **kw).resolve()),
	}
	# @used-by :func:`agent_tools.meta.builders.build_github_issue_metadata()`
	# @used-by :meth:`Builders.build_problem()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	def __init__(self, project_root: str | Path | None=None, *, env: dict[str, str] | None=None, now: datetime | str | None=None, tz=None) -> None:
		self.__project_root = project_root
		self.__env = env
		self.__now = now
		self.__tz = tz
	# @used-by :func:`agent_tools.meta.builders.build_github_issue_metadata()`
	# @used-by :meth:`Builders.build_problem()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	def build_github_issue(self, *, issue_url: str) -> dict[str, Any]:
		from agent_tools.path_registry import canonicalize_root_dir
		environ = dict(os.environ) if None is self.__env else dict(self.__env)
		platform, active_cid, tool_step = Builders.detect_env_platform(environ)
		ctx = Builders.__collect_issue_env_ctx(environ, platform, active_cid)
		canon_root = canonicalize_root_dir(self.__project_root) if None is not self.__project_root and str(self.__project_root).strip() else None
		state_path, state_obj = Builders.__find_issue_state_pair(canon_root, ctx['primary_cid'])
		st = Builders.__apply_issue_state_details(state_path, state_obj, canon_root, platform, ctx)
		summary_row = ctx['summary_row']
		env_pid = str(environ.get('ANTIGRAVITY_PROJECT_ID') or '').strip() or (summary_row.get('project_id') if isinstance(summary_row, dict) else None)
		project_info = Builders.__fn('resolve_project_identity')(canon_root, ag_paths=ctx['ag_paths'], project_id=env_pid) if None is not canon_root else None
		conv_steps = Blocks.resolve_conversation_steps(canon_root, st['jdir'], ctx['primary_cid'])
		conv_label = Blocks.conversation_label(summary_title=summary_row.get('title') if isinstance(summary_row, dict) else None, conversation_steps=conv_steps, current_steps=st['steps'])
		turn_trace = Blocks.build_turn_trace(turn_index=ctx['turn_index'], turn_id=st['turn_id'], turn_key=st['turn_key'], start_step=st['start_step'], tool_step=tool_step, state_path=st['state_path'])
		journal_trace = Blocks.build_journal_trace(st['jdir'], st['steps'], st['group_file'], require_steps=True)
		trace_block = Blocks.build_trace(cid=ctx['primary_cid'], subagent_cid=ctx['subagent_cid'], turn_trace=turn_trace, journal_trace=journal_trace, transcript_path=ctx['transcript_path'])
		extras = (('Project', project_info), ('Journal', Blocks.build_journal(st['steps'], conv_label)), ('Agent', Blocks.build_agent(platform, ctx['instance_id'], ctx['model'], ctx['effort'])), ('Trace', trace_block))
		return Builders.__assemble_optional_blocks({'Time': TimestampFormatter(self.__now, tz=self.__tz).format_local(), 'Issue': str(issue_url)}, extras)
	# @used-by :meth:`Builders.build_github_issue()`
	@staticmethod
	def __apply_issue_state_details(state_path: Path | None, state_obj: dict[str, Any] | None, canon_root: Path | None, platform: str | None, ctx: dict[str, Any]) -> dict[str, Any]:
		from agent_tools import journal
		out: dict[str, Any] = {'group_file': None, 'jdir': None, 'start_step': None, 'state_path': state_path, 'steps': [], 'turn_id': None, 'turn_key': None}
		if isinstance(state_obj, dict):
			out['turn_key'] = str(state_obj.get('key') or state_path.stem) if None is not state_path else state_obj.get('key')
			out['turn_id'] = state_obj.get('native_turn_id')
			out['start_step'] = state_obj['native_start_step'] if isinstance(state_obj.get('native_start_step'), int) else None
			out['steps'] = TranscriptReader.extract_turn_steps_from_state(state_obj)
			out['jdir'] = journal.canonicalize_journal_dir_identity(state_obj['journal']) if state_obj.get('journal') else (journal.resolve_journal_dir(canon_root) if None is not canon_root else None)
			out['group_file'] = Builders.__resolve_issue_group_file(state_obj, out['jdir'], out['turn_key'])
			Builders.__refine_issue_ctx_from_state(platform, ctx, out['turn_id'], out['start_step'])
		return out
	# @used-by :meth:`Builders.build_github_issue()`
	# @used-by :meth:`Builders.build_journal()`
	@staticmethod
	def __assemble_optional_blocks(base: dict[str, Any], extras: tuple[tuple[str, Any], ...]) -> dict[str, Any]:
		for key, val in extras:
			if val:
				base[key] = val
		return base
	# @used-by :meth:`Builders.__collect_issue_env_ctx()`
	@staticmethod
	def __collect_codex_issue_ctx(environ: dict[str, str], active_cid: str) -> dict[str, Any]:
		cx_home_env = str(environ.get('CODEX_HOME') or '').strip() or None
		cx_paths = Builders.__fn('_resolve_codex_paths_safe')(backend=cx_home_env, conversation_id=active_cid)
		instance_id = cx_paths.get('instance') if isinstance(cx_paths, dict) else None
		try:
			from agent_tools.runtime import _codex_home_conversation_trace
			trace_str = _codex_home_conversation_trace(cx_paths.get('home') if isinstance(cx_paths, dict) else cx_home_env, active_cid, system_paths=cx_paths)
			t_path: Path | None = Path(trace_str).resolve() if trace_str else None
		except Exception:
			t_path = None
		c_info = Builders.__fn('_extract_codex_transcript_info')(t_path) if None is not t_path else {}
		return {'ag_paths': None, 'effort': c_info.get('effort'), 'instance_id': instance_id, 'model': c_info.get('model'), 'primary_cid': active_cid, 'subagent_cid': None, 'summary_row': None, 'transcript_path': t_path, 'turn_index': c_info.get('turn_index')}
	# @used-by :meth:`Builders.build_github_issue()`
	@staticmethod
	def __collect_issue_env_ctx(environ: dict[str, str], platform: str | None, active_cid: str | None) -> dict[str, Any]:
		if 'antigravity' == platform and active_cid:
			r = Builders.collect_ag_issue_ctx(environ, active_cid)
		elif 'codex' == platform and active_cid:
			r = Builders.__collect_codex_issue_ctx(environ, active_cid)
		else:
			r = {'ag_paths': None, 'effort': None, 'instance_id': None, 'model': None, 'primary_cid': active_cid, 'subagent_cid': None, 'summary_row': None, 'transcript_path': None, 'turn_index': None}
		return r
	# @used-by :meth:`Builders.build_journal()`
	@staticmethod
	def __collect_journal_turn_state(platform: str, cid: str, ag_paths: dict[str, Any] | None, summary_row: dict[str, Any] | None, native: dict[str, Any], turn: dict[str, Any], request_at: Any, response_at: Any) -> dict[str, Any]:
		model, effort = TimestampFormatter.split_model_and_effort(turn.get('model'), turn.get('effort'))
		state: dict[str, Any] = {'effort': effort, 'final_step': turn.get('final_step') if isinstance(turn.get('final_step'), int) else None, 'model': model, 'req_ts': request_at or turn.get('request_timestamp'), 'res_ts': response_at or turn.get('response_timestamp'), 'start_step': turn.get('start_step') if isinstance(turn.get('start_step'), int) else None, 'turn_index': Builders.__resolve_turn_index(turn, native)}
		if 'antigravity' == platform:
			Builders.__enrich_journal_ag(cid, ag_paths, summary_row, native.get('source_file'), state)
		elif 'codex' == platform:
			Builders.__enrich_journal_codex(native.get('source_file'), turn.get('turn_id'), state)
		return state
	# @used-by :meth:`Builders.__collect_journal_turn_state()`
	@staticmethod
	def __enrich_journal_ag(cid: str, ag_paths: dict[str, Any] | None, summary_row: dict[str, Any] | None, source_file: Any, state: dict[str, Any]) -> None:
		t_path = source_file or (Builders.__fn('_ag_transcript_file')(ag_paths, cid) if cid else None)
		if None is state['req_ts'] or None is state['model'] or None is state['effort'] or None is state['turn_index']:
			t_info = Builders.__fn('_extract_ag_transcript_info')(t_path, start_step=state['start_step'], final_step=state['final_step'])
			Builders.__merge_transcript_fields(state, t_info)
			if None is state['model'] or None is state['effort']:
				fb_m, fb_e = Builders.__fn('_resolve_ag_model_and_effort')(ag_paths, cid, transcript_path=t_path, start_step=state['start_step'])
				state['model'] = state['model'] or fb_m
				state['effort'] = state['effort'] or fb_e
		if None is state['req_ts'] and isinstance(summary_row, dict) and summary_row.get('last_user_input_time'):
			state['req_ts'] = summary_row.get('last_user_input_time')
	# @used-by :meth:`Builders.__collect_journal_turn_state()`
	@staticmethod
	def __enrich_journal_codex(source_file: Any, turn_id: Any, state: dict[str, Any]) -> None:
		if None is state['req_ts'] or None is state['model'] or None is state['effort'] or None is state['turn_index']:
			c_info = Builders.__fn('_extract_codex_transcript_info')(source_file, turn_id=turn_id, start_step=state['start_step'], final_step=state['final_step'])
			Builders.__merge_transcript_fields(state, c_info, include_model=True)
	# @used-by :meth:`Builders.__validate_problem_issue()`
	# @used-by :meth:`Builders.build_github_issue()`
	@staticmethod
	def __find_issue_state_pair(canon_root: Path | None, primary_cid: str | None) -> tuple[Path | None, dict[str, Any] | None]:
		r: tuple[Path | None, dict[str, Any] | None] = (None, None)
		if None is not canon_root and primary_cid:
			try:
				from agent_tools.path_registry import project_paths
				hit = TranscriptReader.find_turn_state_for_conversation(project_paths(canon_root, exact_root=True).turns_dir, primary_cid)
				if None is not hit:
					r = hit
			except (OSError, ValueError):
				r = (None, None)
		return r
	# @used-by :meth:`Builders.__collect_codex_issue_ctx()`
	# @used-by :meth:`Builders.__enrich_journal_ag()`
	# @used-by :meth:`Builders.__enrich_journal_codex()`
	# @used-by :meth:`Builders.__insert_source_project()`
	# @used-by :meth:`Builders.__refine_issue_ctx_from_state()`
	# @used-by :meth:`Builders.__resolve_journal_platform()`
	# @used-by :meth:`Builders.build_github_issue()`
	# @used-by :meth:`Builders.build_journal()`
	# @used-by :meth:`Builders.collect_ag_issue_ctx()`
	@staticmethod
	def __fn(name: str) -> Any:
		mod_name, default = Builders.__HOOK_TARGETS[name]
		submod, meta_pkg, facade = (sys.modules.get(mod_name), sys.modules.get('agent_tools.meta'), sys.modules.get('agent_tools.metadata'))
		sub_fn = getattr(submod, name, None) if None is not submod else None
		meta_fn = getattr(meta_pkg, name, None) if None is not meta_pkg else sub_fn
		fac_fn = getattr(facade, name, None) if None is not facade else None
		if None is not fac_fn and fac_fn is not meta_fn:
			r = fac_fn
		elif None is not sub_fn:
			r = sub_fn
		else:
			r = default
		return r
	# 2026-11-28 "Reject invalid or foreign GitHub issues in problem-metadata builder and CLI": https://github.com/dmitry-ai/harness/issues/429
	# @used-by :meth:`Builders.build_problem()`
	@staticmethod
	def __insert_source_project(meta: dict[str, Any], project_root: str | Path | None, source_project_root: str | Path | None) -> dict[str, Any]:
		from agent_tools.path_registry import canonicalize_root_dir
		r = meta
		if None is not source_project_root and str(source_project_root).strip():
			src_canon = canonicalize_root_dir(source_project_root)
			proj_canon = canonicalize_root_dir(project_root) if None is not project_root and str(project_root).strip() else None
			if src_canon != proj_canon:
				src_info = Builders.__fn('resolve_project_identity')(src_canon)
				ordered: dict[str, Any] = {}
				for key, val in meta.items():
					ordered[key] = val
					if 'Project' == key:
						ordered['Source Project'] = src_info
				if 'Source Project' not in ordered:
					ordered['Source Project'] = src_info
				r = ordered
		return r
	# @used-by :meth:`Builders.__enrich_journal_ag()`
	# @used-by :meth:`Builders.__enrich_journal_codex()`
	@staticmethod
	def __merge_transcript_fields(state: dict[str, Any], info: dict[str, Any], *, include_model: bool=False) -> None:
		for dst, src in (('req_ts', 'request_timestamp'), ('res_ts', 'response_timestamp'), ('turn_index', 'turn_index')):
			if None is state[dst]:
				state[dst] = info.get(src)
		if include_model:
			state['model'] = state['model'] or info.get('model')
			state['effort'] = state['effort'] or info.get('effort')
	# @used-by :meth:`Builders.build_problem()`
	@staticmethod
	def __normalize_problem_issue_url(issue_url: str | None, *, allow_no_issue: bool) -> str | None:
		raw = str(issue_url or '').strip().rstrip('/')
		if not raw:
			if not allow_no_issue:
				raise ValueError('Problem metadata requires a GitHub issue URL (mandatory "Issue" key); pass --issue <URL> or --no-issue for non-GitHub workspaces')
			r: str | None = None
		elif not Builders.__GITHUB_ISSUE_URL_RE.fullmatch(raw):
			raise ValueError(f'Invalid GitHub issue URL for problem metadata: {issue_url}')
		else:
			r = raw
		return r
	# @used-by :meth:`Builders.__apply_issue_state_details()`
	@staticmethod
	def __refine_issue_ctx_from_state(platform: str | None, ctx: dict[str, Any], turn_id: Any, start_step: int | None) -> None:
		if 'antigravity' == platform and ctx['primary_cid']:
			p_trans = Builders.__fn('_ag_transcript_file')(ctx['ag_paths'], ctx['primary_cid'])
			p_info = Builders.__fn('_extract_ag_transcript_info')(p_trans, start_step=start_step)
			if isinstance(p_info.get('turn_index'), int):
				ctx['turn_index'] = p_info['turn_index']
		elif 'codex' == platform and None is not ctx['transcript_path']:
			c_info = Builders.__fn('_extract_codex_transcript_info')(ctx['transcript_path'], turn_id=turn_id, start_step=start_step)
			if isinstance(c_info.get('turn_index'), int):
				ctx['turn_index'] = c_info['turn_index']
			ctx['model'] = ctx['model'] or c_info.get('model')
			ctx['effort'] = ctx['effort'] or c_info.get('effort')
	# @used-by :meth:`Builders.__apply_issue_state_details()`
	@staticmethod
	def __resolve_issue_group_file(state_obj: dict[str, Any], jdir: Path | None, turn_key: str | None) -> Path | None:
		from agent_tools import journal
		r: Path | None = None
		for slot in ('prepared', 'journal_record', 'delivery'):
			rec = state_obj.get(slot)
			if isinstance(rec, dict) and rec.get('group_file'):
				r = Path(rec['group_file'])
				break
		if None is r and None is not jdir and turn_key:
			r = journal.state_dir(jdir) / 'answer-groups' / f'native-{turn_key}.json'
		return r
	# @used-by :meth:`Builders.build_journal()`
	@staticmethod
	def __resolve_journal_platform(platform: str, native: dict[str, Any], cid: str) -> tuple[dict[str, Any] | None, Any, dict[str, Any] | None]:
		backend_raw, inst = (native.get('native_backend'), native.get('instance'))
		ag_paths = Builders.__fn('_resolve_ag_paths_safe')(backend=backend_raw, instance=inst, conversation_id=cid) if 'antigravity' == platform else None
		cx_paths = Builders.__fn('_resolve_codex_paths_safe')(backend=backend_raw, instance=inst, conversation_id=cid) if 'codex' == platform else None
		instance_id = inst or (ag_paths.get('instance') if isinstance(ag_paths, dict) else None) or (cx_paths.get('instance') if isinstance(cx_paths, dict) else None)
		summary_row = Builders.__fn('_read_ag_summary_row')(ag_paths, cid) if 'antigravity' == platform and cid else None
		return (ag_paths, instance_id, summary_row)
	# @used-by :meth:`Builders.__collect_journal_turn_state()`
	@staticmethod
	def __resolve_turn_index(turn: dict[str, Any], native: dict[str, Any]) -> Any:
		r = turn.get('turn_index')
		if not isinstance(r, int) or 1 > r:
			for idx, item in enumerate(native.get('turns') or (), 1):
				if isinstance(item, dict) and item.get('turn_id') == turn.get('turn_id'):
					r = idx
					break
		return r
	# 2026-11-28 "Reject invalid or foreign GitHub issues in problem-metadata builder and CLI": https://github.com/dmitry-ai/harness/issues/429
	# @used-by :meth:`Builders.build_problem()`
	@staticmethod
	def __validate_problem_issue(clean_url: str | None, *, project_root: str | Path | None, env: dict[str, str] | None, issue_spec: Any) -> None:
		if None is not clean_url:
			from Df.Harness.Grounding.ProblemIssueSpecification import ProblemIssueSpecification
			from agent_tools.path_registry import canonicalize_root_dir
			canon_root = canonicalize_root_dir(project_root) if None is not project_root and str(project_root).strip() else None
			if None is not issue_spec:
				errs = issue_spec.validate() if hasattr(issue_spec, 'validate') else list(issue_spec(clean_url, canon_root))
			else:
				environ = dict(os.environ) if None is env else dict(env)
				_, active_cid, _ = Builders.detect_env_platform(environ)
				_, state_obj = Builders.__find_issue_state_pair(canon_root, active_cid)
				reqs = list(state_obj.get('requests') or ()) if isinstance(state_obj, dict) else []
				errs = ProblemIssueSpecification([{'issue': clean_url}], root=canon_root, turn_state=state_obj, requests=reqs, schema_mode='problem', strict_evidence=True, conversation_id=active_cid).validate()
			if errs:
				raise ValueError('; '.join(errs))
	# @used-by :func:`agent_tools.meta.builders.build_journal_metadata()`
	@staticmethod
	def build_journal(root: str | Path, native: dict[str, Any], turn: dict[str, Any], *, journal_dir: str | Path, steps: list[int], turn_key: str, turn_state_path: str | Path | None=None, group_file: str | Path | None=None, conversation_steps: list[int] | None=None, request_at: datetime | str | None=None, response_at: datetime | str | None=None, tz=None) -> dict[str, Any]:
		from agent_tools.path_registry import canonicalize_root_dir, project_paths
		canon_root = canonicalize_root_dir(root)
		pp, jdir = (project_paths(canon_root, exact_root=True), Path(journal_dir).resolve())
		platform = str(native.get('platform') or '').strip().lower()
		cid = str(native.get('conversation_id') or '').strip()
		ag_paths, instance_id, summary_row = Builders.__resolve_journal_platform(platform, native, cid)
		project_info = Builders.__fn('resolve_project_identity')(canon_root, ag_paths=ag_paths, project_id=summary_row.get('project_id') if isinstance(summary_row, dict) else None)
		state = Builders.__collect_journal_turn_state(platform, cid, ag_paths, summary_row, native, turn, request_at, response_at)
		time_block = Blocks.build_time(TimestampFormatter.parse_timestamp(state['req_ts']), TimestampFormatter.parse_timestamp(state['res_ts']) or datetime.now().astimezone(), tz)
		conv_steps = Blocks.resolve_conversation_steps(canon_root, jdir, cid) if None is conversation_steps else conversation_steps
		conv_label = Blocks.conversation_label(summary_title=summary_row.get('title') if isinstance(summary_row, dict) else None, conversation_steps=conv_steps, current_steps=steps)
		state_p = Path(turn_state_path) if None is not turn_state_path else (pp.turns_dir / f'{turn_key}.json')
		turn_trace = Blocks.build_turn_trace(turn_index=state['turn_index'], turn_id=turn.get('turn_id'), turn_key=turn_key, start_step=state['start_step'], final_step=state['final_step'], state_path=state_p, canon_root=canon_root)
		journal_trace = Blocks.build_journal_trace(jdir, steps, group_file, canon_root=canon_root)
		trace_block = Blocks.build_trace(cid=cid, turn_trace=turn_trace, journal_trace=journal_trace, transcript_path=native.get('source_file'))
		extras = (('Journal', Blocks.build_journal(steps, conv_label)), ('Agent', Blocks.build_agent(platform, instance_id, state['model'], state['effort'])), ('Clarifications', Blocks.build_clarifications(turn, state_p, tz)), ('Trace', trace_block))
		return Builders.__assemble_optional_blocks({'Time': time_block, 'Project': project_info}, extras)
	# 2026-11-28 "Reject invalid or foreign GitHub issues in problem-metadata builder and CLI": https://github.com/dmitry-ai/harness/issues/429
	# @used-by :func:`agent_tools.meta.builders.build_problem_metadata()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta_cov.DfHarnessS11Wave2bMetaCovTests.test_blocks_clarifications_builders_problem_codex_and_turn_state()`
	@staticmethod
	def build_problem(*, issue_url: str | None=None, project_root: str | Path | None=None, source_project_root: str | Path | None=None, allow_no_issue: bool=False, env: dict[str, str] | None=None, now: datetime | str | None=None, tz=None, issue_spec: Any=None) -> dict[str, Any]:
		clean_url = Builders.__normalize_problem_issue_url(issue_url, allow_no_issue=allow_no_issue)
		Builders.__validate_problem_issue(clean_url, project_root=project_root, env=env, issue_spec=issue_spec)
		meta = Builders(project_root, env=env, now=now, tz=tz).build_github_issue(issue_url=clean_url or '')
		meta['Issue'] = clean_url
		return Builders.__insert_source_project(meta, project_root, source_project_root)
	# @used-by :func:`agent_tools.meta.builders._collect_ag_issue_ctx()`
	# @used-by :meth:`Builders.__collect_issue_env_ctx()`
	@staticmethod
	def collect_ag_issue_ctx(environ: dict[str, str], active_cid: str) -> dict[str, Any]:
		ag_backend_env = str(environ.get('ANTIGRAVITY_APP_DATA_DIR') or '').strip() or None
		ag_inst_env = str(environ.get('ANTIGRAVITY_ACCOUNT') or '').strip() or None
		ag_paths = Builders.__fn('_resolve_ag_paths_safe')(backend=ag_backend_env, instance=ag_inst_env, conversation_id=active_cid)
		if None is ag_paths and ag_backend_env:
			bp = Path(ag_backend_env).resolve()
			ag_paths = {'instance': ag_inst_env, 'backend_dir': bp, 'brain_dir': bp / 'brain', 'conversations_db': bp / 'conversation_summaries.db', 'conversations_dir': bp / 'conversations', 'projects_dir': bp.parent / 'config/projects'}
		active_row = Builders.__fn('_read_ag_summary_row')(ag_paths, active_cid)
		parent_cid = str(active_row.get('parent_conversation_id') or '').strip().lower() if isinstance(active_row, dict) else ''
		subagent_cid = active_cid if parent_cid else None
		primary_cid = parent_cid if parent_cid else active_cid
		summary_row = (Builders.__fn('_read_ag_summary_row')(ag_paths, primary_cid) or active_row) if parent_cid else active_row
		t_path = Builders.__fn('_ag_transcript_file')(ag_paths, active_cid)
		model, effort = Builders.__fn('_resolve_ag_model_and_effort')(ag_paths, active_cid, transcript_path=t_path)
		inst_id = (ag_paths.get('instance') if isinstance(ag_paths, dict) else None) or ag_inst_env
		return {'ag_paths': ag_paths, 'effort': effort, 'instance_id': inst_id, 'model': model, 'primary_cid': primary_cid, 'subagent_cid': subagent_cid, 'summary_row': summary_row, 'transcript_path': t_path, 'turn_index': None}
	# @used-by :func:`agent_tools.meta.builders._detect_env_platform()`
	# @used-by :meth:`Builders.__validate_problem_issue()`
	# @used-by :meth:`Builders.build_github_issue()`
	@staticmethod
	def detect_env_platform(environ: dict[str, str]) -> tuple[str | None, str | None, int | None]:
		meta_cid, tool_step = TranscriptReader.parse_antigravity_source_metadata(environ)
		ag_cid = str(environ.get('ANTIGRAVITY_CONVERSATION_ID') or '').strip().lower() or meta_cid or ''
		cx_cid = str(environ.get('CODEX_THREAD_ID') or '').strip().lower()
		if ag_cid and TimestampFormatter.UUID_RE.fullmatch(ag_cid):
			r: tuple[str | None, str | None, int | None] = ('antigravity', ag_cid, tool_step)
		elif cx_cid and TimestampFormatter.UUID_RE.fullmatch(cx_cid):
			r = ('codex', cx_cid, tool_step)
		else:
			r = (None, None, tool_step)
		return r
