# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Perf.AntigravityTimesheetAnalyzer import AntigravityTimesheetAnalyzer
from Df.Harness.Perf.CodexTimesheetAnalyzer import CodexTimesheetAnalyzer
from Df.Harness.Perf.TimesheetCommon import TimesheetCommon
import json
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class TimesheetBuilder:
	# @used-by :func:`agent_tools.perf.timesheet.build_timesheet()`
	# @used-by :meth:`TimesheetBuilder.run_cli()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_perf_classes_profile_and_build_timesheets()`
	def __init__(self, trace_path: str | Path, *, conversation_id: str | None=None, summary_db: str | Path | None=None, turn_start_step: int | None=None, turn_end_step: int | None=None, top_gaps_limit: int=10) -> None:
		self.__trace_path = Path(trace_path).resolve()
		self.__conversation_id = conversation_id
		self.__summary_db = summary_db
		self.__turn_start_step = turn_start_step
		self.__turn_end_step = turn_end_step
		self.__top_gaps_limit = top_gaps_limit
	# @used-by :func:`agent_tools.perf.timesheet.build_timesheet()`
	# @used-by :meth:`TimesheetBuilder.run_cli()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_perf_and_test_runner_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_perf_classes_profile_and_build_timesheets()`
	def build(self) -> dict[str, Any]:
		digest, all_rows = TimesheetCommon(self.__trace_path).load_jsonl_rows()
		surface = TimesheetBuilder.__detect_surface(all_rows)
		cid = TimesheetBuilder.__infer_conversation_id(surface, all_rows, self.__trace_path, self.__conversation_id)
		rows = TimesheetBuilder.__slice_rows(surface, all_rows, self.__turn_start_step, self.__turn_end_step)
		if 'codex' == surface:
			body = CodexTimesheetAnalyzer(rows, top_gaps_limit=self.__top_gaps_limit).analyze()
		else:
			u_ts, m_ts = TimesheetCommon.read_summary_timestamps(Path(self.__summary_db) if self.__summary_db else None, cid)
			body = AntigravityTimesheetAnalyzer(rows, last_user_ts=u_ts, last_mod_ts=m_ts, top_gaps_limit=self.__top_gaps_limit).analyze()
		return {'schema_version': 1, 'valid': True, 'surface': surface, 'conversation_id': cid, 'trace_file': self.__trace_path.as_posix(), 'trace_sha256': digest, 'step_count': len(rows), 'slice': {'start_step': self.__turn_start_step, 'end_step': self.__turn_end_step}, **body}
	# @used-by :meth:`TimesheetBuilder.build()`
	@staticmethod
	def __detect_surface(rows: list[dict[str, Any]]) -> str:
		first = rows[0] if rows else {}
		return 'codex' if 'session_meta' == first.get('type') or ('timestamp' in first and 'payload' in first) else 'antigravity'
	# @used-by :meth:`TimesheetBuilder.build()`
	@staticmethod
	def __infer_conversation_id(surface: str, rows: list[dict[str, Any]], trace_path: Path, explicit: str | None) -> str | None:
		if explicit:
			r: str | None = explicit
		elif 'codex' == surface:
			meta = next((row.get('payload') for row in rows if 'session_meta' == row.get('type') and isinstance(row.get('payload'), dict)), {})
			r = meta.get('id') if isinstance(meta.get('id'), str) else None
		elif 'logs' == trace_path.parent.name and '.system_generated' == trace_path.parent.parent.name:
			r = trace_path.parent.parent.parent.name
		else:
			r = None
		return r
	# @used-by :meth:`TimesheetBuilder.build()`
	@staticmethod
	def __slice_rows(surface: str, rows: list[dict[str, Any]], start_step: int | None, end_step: int | None) -> list[dict[str, Any]]:
		if None is start_step and None is end_step:
			r = rows
		elif 'codex' == surface:
			lo = max(0, int(start_step)) if None is not start_step else 0
			hi = int(end_step) + 1 if None is not end_step else len(rows)
			r = rows[lo:hi]
		else:
			r = [row for pos, row in enumerate(rows) if (None is start_step or int(row.get('step_index', pos)) >= start_step) and (None is end_step or int(row.get('step_index', pos)) <= end_step)]
		return r
	# @used-by :func:`agent_tools.perf.timesheet.run_perf_timesheet_cli()`
	@staticmethod
	def run_cli(args) -> dict[str, Any]:
		src = TimesheetCommon.resolve_trace_source(trace=args.trace, conversation=args.conversation, project=args.project, journal_step=args.journal_step, instance=args.instance, platform=args.platform, summary_db=args.summary_db, turn_start_step=args.turn_start_step)
		report = TimesheetBuilder(src['trace_path'], conversation_id=src['conversation_id'], summary_db=src['summary_db'], turn_start_step=src['turn_start_step'], turn_end_step=args.turn_end_step, top_gaps_limit=args.top_gaps).build()
		if None is not args.output:
			out_p = Path(args.output).resolve()
			out_p.parent.mkdir(parents=True, exist_ok=True)
			out_p.write_text(json.dumps(report, ensure_ascii=False, indent='\t') + '\n', encoding='utf-8')
			report['output_file'] = out_p.as_posix()
		return report
