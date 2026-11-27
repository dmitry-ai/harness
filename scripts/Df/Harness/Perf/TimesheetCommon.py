# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import re
import sqlite3
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class TimesheetCommon:
	__CMD_PATTERNS = (
		('test_runs', re.compile(r'(?i)\b(?:unittest|pytest|run-tests|perf-profile-tests)\b')),
		('github_issue_cli', re.compile(r'(?i)\bdf_github_issue\.py\b')),
		('answer_check_prepare', re.compile(r'(?i)\b(?:answer-check|answer-prepare|analysis-check)\b')),
		('git_commit_push', re.compile(r'(?i)\b(?:safe_commit\.py|git\b[^;&|]*\b(?:add|commit|push|rebase|merge))\b')),
		('harness_cli_other', re.compile(r'(?i)\b(?:harness\.py|upwork_project\.py)\b')),
	)
	__PYTEST_RE = re.compile(r'(\d+)\s+passed\b[^\n]*?\bin\s+([0-9]+(?:\.[0-9]+)?)s')
	__UNITTEST_RE = re.compile(r'Ran\s+(\d+)\s+tests?\s+in\s+([0-9]+(?:\.[0-9]+)?)s')
	# @used-by :func:`agent_tools.perf.timesheet_common.load_jsonl_rows()`
	# @used-by :meth:`Df.Harness.Perf.TimesheetBuilder.TimesheetBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_perf_classes_profile_and_build_timesheets()`
	def __init__(self, path: Path) -> None:
		self.__path = Path(path)
	# @used-by :func:`agent_tools.perf.timesheet_common.load_jsonl_rows()`
	# @used-by :meth:`Df.Harness.Perf.TimesheetBuilder.TimesheetBuilder.build()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_perf_classes_profile_and_build_timesheets()`
	def load_jsonl_rows(self) -> tuple[str, list[dict[str, Any]]]:
		raw = self.__path.read_bytes()
		digest = hashlib.sha256(raw).hexdigest()
		rows: list[dict[str, Any]] = []
		for line in raw.decode('utf-8', errors='replace').splitlines():
			if line.strip():
				try:
					obj = json.loads(line)
				except ValueError:
					obj = None
				if isinstance(obj, dict):
					rows.append(obj)
		return (digest, rows)
	# @used-by :meth:`TimesheetCommon.__journal_response_candidates()`
	@staticmethod
	def __bucket_name(step_num: int) -> str:
		start = ((step_num - 1) // 20) * 20 + 1
		return f'{start}\u2013{start + 19}'
	# @used-by :meth:`TimesheetCommon.resolve_journal_step_meta()`
	@staticmethod
	def __journal_response_candidates(project_root: Path, step_num: int) -> list[Path]:
		jroot, bucket = (project_root / '\ua66e', TimesheetCommon.__bucket_name(step_num))
		return [jroot / '\u227a' / bucket / f'{step_num}.md', jroot / '\u227a' / f'{step_num}.md', jroot / 'res' / f'{step_num}.md', jroot / '1 - Analysis/res' / f'{step_num}.md']
	# @used-by :meth:`TimesheetCommon.resolve_trace_source()`
	@staticmethod
	def __lookup_conversation_trace(cid: str, instance: str | None, platform: str | None, summary_db: Path | None) -> tuple[Path, Path | None]:
		from agent_tools.runtime import find_conversation_instance
		matches = find_conversation_instance(cid, platform=platform, include_disabled=True)
		picked = next((m for m in matches if None is instance or m['id'] == instance), None)
		if None is picked or (not picked.get('trace_file')):
			raise FileNotFoundError(f'Native trace file not found for conversation {cid}')
		db_raw = (picked.get('system_paths') or {}).get('conversations_db')
		return (Path(picked['trace_file']), summary_db or (Path(db_raw) if db_raw else None))
	# @used-by :meth:`TimesheetCommon.resolve_trace_source()`
	@staticmethod
	def __lookup_summary_db_optional(cid: str, instance: str | None, platform: str | None) -> Path | None:
		from agent_tools.runtime import find_conversation_instance
		r: Path | None = None
		try:
			matches = find_conversation_instance(cid, platform=platform, include_disabled=True)
			picked = next((m for m in matches if None is instance or m['id'] == instance), None)
			db_raw = (picked.get('system_paths') or {}).get('conversations_db') if None is not picked else None
			r = Path(db_raw) if db_raw else None
		except (OSError, ValueError, KeyError):
			r = None
		return r
	# @used-by :meth:`TimesheetCommon.resolve_journal_step_meta()`
	@staticmethod
	def __parse_header_meta(text: str) -> dict[str, Any]:
		m = re.match(r'^```json[ \t]*\r?\n([\s\S]*?)\r?\n```', (text or '').lstrip())
		try:
			obj = json.loads(m.group(1)) if m else {}
		except ValueError:
			obj = {}
		return obj if isinstance(obj, dict) else {}
	# @used-by :func:`agent_tools.perf.timesheet_common.classify_command()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__record_tool_call()`
	# @used-by :meth:`Df.Harness.Perf.CodexTimesheetAnalyzer.CodexTimesheetAnalyzer.__record_codex_call()`
	@staticmethod
	def classify_command(cmd: str) -> str:
		text, r = (str(cmd or ''), 'inspection_shell')
		for name, pat in TimesheetCommon.__CMD_PATTERNS:
			if pat.search(text):
				r = name
				break
		return r
	# @used-by :func:`agent_tools.perf.timesheet_common.compute_top_gaps()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__build_ag_result()`
	# @used-by :meth:`Df.Harness.Perf.CodexTimesheetAnalyzer.CodexTimesheetAnalyzer.__build_codex_result()`
	@staticmethod
	def compute_top_gaps(events: list[tuple[int, float | None, str, str | None, str]], *, limit: int=10) -> list[dict[str, Any]]:
		gaps: list[dict[str, Any]] = []
		for idx in range(len(events) - 1):
			s1, t1, k1, m1, sum1 = events[idx]
			s2, t2, _, _, _ = events[idx + 1]
			if None is not t1 and None is not t2 and t2 > t1:
				gaps.append({'from_step': s1, 'to_step': s2, 'dur_s': round(t2 - t1, 3), 'kind': k1, 'model': m1, 'summary': sum1[:140]})
		gaps.sort(key=lambda item: (-item['dur_s'], item['from_step']))
		return gaps[:max(1, int(limit))]
	# @used-by :func:`agent_tools.perf.timesheet_common.format_timesheet_text()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_perf_analyzers_and_timesheet_cli()`
	@staticmethod
	def format_text(report: dict[str, Any]) -> str:
		ts = report.get('timestamps') or {}
		toks = report.get('tokens') or {}
		cmds = (report.get('commands') or {}).get('categories') or {}
		lines = [
			f"Surface: {report.get('surface')}",
			f"Conversation: {report.get('conversation_id') or 'unknown'}",
			f"Step count: {report.get('step_count')}",
			f"Wall span (steps): {ts.get('total_span_to_last_step_s')}s (last_modified: {ts.get('total_span_to_last_modified_s')}s)",
			f"Tokens: fresh={toks.get('fresh_input_tokens')} cache_read={toks.get('cache_read_tokens')} output={toks.get('output_tokens')} plan_mode={toks.get('plan_mode_output_tokens')}",
			f"Checkpoints: {len(report.get('checkpoints') or ())}",
		]
		for cat, info in sorted(cmds.items()):
			lines.append(f"Command[{cat}]: count={info['count']} wall_s={info['wall_s']}")
		return '\n'.join(lines) + '\n'
	# @used-by :func:`agent_tools.perf.timesheet_common.parse_iso_ts()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__ag_timestamps()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__bg_match_records()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__command_wall_and_bg()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__extract_step_end_ts()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__process_planner_step()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__record_checkpoint()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__record_generic_step()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__sync_generic_dur()`
	# @used-by :meth:`Df.Harness.Perf.CodexTimesheetAnalyzer.CodexTimesheetAnalyzer.__build_codex_result()`
	# @used-by :meth:`Df.Harness.Perf.CodexTimesheetAnalyzer.CodexTimesheetAnalyzer.__process_codex_row()`
	# @used-by :meth:`Df.Harness.Perf.CodexTimesheetAnalyzer.CodexTimesheetAnalyzer.__record_codex_event()`
	@staticmethod
	def parse_iso_ts(raw: str | None) -> float | None:
		r: float | None = None
		if isinstance(raw, str) and raw.strip():
			norm = raw.strip().replace(' ', 'T')
			norm = norm[:-1] + '+00:00' if norm.endswith('Z') else norm
			norm = re.sub(r'(\.\d{6})\d+', r'\1', norm)
			try:
				dt = datetime.fromisoformat(norm)
				r = (dt.replace(tzinfo=timezone.utc) if None is dt.tzinfo else dt).timestamp()
			except ValueError:
				r = None
		return r
	# @used-by :func:`agent_tools.perf.timesheet_common.parse_test_output()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__resolve_bg_wait()`
	@staticmethod
	def parse_test_output(text: str) -> tuple[int | None, float | None]:
		body = str(text or '')
		m_u = TimesheetCommon.__UNITTEST_RE.search(body)
		if None is not m_u:
			r: tuple[int | None, float | None] = (int(m_u.group(1)), float(m_u.group(2)))
		else:
			m_p = TimesheetCommon.__PYTEST_RE.search(body)
			r = (int(m_p.group(1)), float(m_p.group(2))) if None is not m_p else (None, None)
		return r
	# @used-by :func:`agent_tools.perf.timesheet_common.read_summary_timestamps()`
	# @used-by :meth:`Df.Harness.Perf.TimesheetBuilder.TimesheetBuilder.build()`
	@staticmethod
	def read_summary_timestamps(db_path: Path | None, conversation_id: str | None) -> tuple[str | None, str | None]:
		r: tuple[str | None, str | None] = (None, None)
		if None is not db_path and conversation_id and db_path.is_file():
			try:
				from agent_tools.platforms.trace_common import open_readonly_sqlite
				with open_readonly_sqlite(db_path, row_factory=sqlite3.Row) as conn:
					row = conn.execute('SELECT last_user_input_time, last_modified_time FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
					if None is not row:
						r = (row['last_user_input_time'], row['last_modified_time'])
			except (OSError, sqlite3.Error, KeyError):
				r = (None, None)
		return r
	# @used-by :func:`agent_tools.perf.timesheet_common.resolve_journal_step_meta()`
	# @used-by :meth:`TimesheetCommon.resolve_trace_source()`
	@staticmethod
	def resolve_journal_step_meta(project_root: Path, step_num: int) -> dict[str, Any]:
		target = next((p for p in TimesheetCommon.__journal_response_candidates(Path(project_root).resolve(), int(step_num)) if p.is_file()), None)
		if None is target:
			raise FileNotFoundError(f'Journal response step {step_num} not found under {project_root}')
		meta = TimesheetCommon.__parse_header_meta(target.read_text(encoding='utf-8', errors='replace'))
		trace = meta.get('Trace') if isinstance(meta.get('Trace'), dict) else {}
		turn = trace.get('Turn') if isinstance(trace.get('Turn'), dict) else {}
		raw_tr = trace.get('Transcript')
		tpath = Path(raw_tr) if isinstance(raw_tr, str) and raw_tr.strip() else None
		s_step = turn.get('Start Step') if isinstance(turn.get('Start Step'), int) else None
		return {'conversation_id': trace.get('Conversation ID'), 'trace_path': tpath, 'start_step': s_step}
	# @used-by :func:`agent_tools.perf.timesheet_common.resolve_trace_source()`
	# @used-by :meth:`Df.Harness.Perf.TimesheetBuilder.TimesheetBuilder.run_cli()`
	# @used-by :meth:`test_df_harness_s11_wave2b_perf_runner_cov.DfHarnessS11Wave2bPerfRunnerCovTests.test_perf_analyzers_and_timesheet_cli()`
	@staticmethod
	def resolve_trace_source(*, trace: Path | None=None, conversation: str | None=None, project: Path | None=None, journal_step: int | None=None, instance: str | None=None, platform: str | None=None, summary_db: Path | None=None, turn_start_step: int | None=None) -> dict[str, Any]:
		cid, tpath, s_step, sdb = (conversation, trace, turn_start_step, summary_db)
		if None is not project and None is not journal_step:
			jmeta = TimesheetCommon.resolve_journal_step_meta(project, journal_step)
			cid, tpath = (cid or jmeta['conversation_id'], tpath or jmeta['trace_path'])
			s_step = jmeta['start_step'] if None is s_step else s_step
		if None is tpath and cid:
			tpath, sdb = TimesheetCommon.__lookup_conversation_trace(cid, instance, platform, sdb)
		elif None is sdb and cid:
			sdb = TimesheetCommon.__lookup_summary_db_optional(cid, instance, platform)
		if None is tpath or (not Path(tpath).is_file()):
			raise FileNotFoundError(f'Trace file not found: {tpath}')
		return {'trace_path': Path(tpath).resolve(), 'conversation_id': cid, 'summary_db': Path(sdb).resolve() if sdb else None, 'turn_start_step': s_step}
	# @used-by :func:`agent_tools.perf.timesheet_common.round_opt()`
	# @used-by :meth:`Df.Harness.Perf.AntigravityTimesheetAnalyzer.AntigravityTimesheetAnalyzer.__ag_timestamps()`
	# @used-by :meth:`Df.Harness.Perf.CodexTimesheetAnalyzer.CodexTimesheetAnalyzer.__build_codex_result()`
	@staticmethod
	def round_opt(val: float | None, digits: int=3) -> float | None:
		return None if None is val else round(float(val), digits)
