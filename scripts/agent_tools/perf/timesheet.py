# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add harness perf-timesheet CLI for deterministic turn chronometry":
# https://github.com/dmitry-ai/harness/issues/191
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
from .timesheet_ag import analyze_antigravity_rows
from .timesheet_codex import analyze_codex_rows
from .timesheet_common import format_timesheet_text, load_jsonl_rows, read_summary_timestamps, resolve_trace_source
def _detect_surface(rows: list[dict[str, Any]]) -> str:
	first = rows[0] if rows else {}
	return 'codex' if 'session_meta' == first.get('type') or ('timestamp' in first and 'payload' in first) else 'antigravity'
def _infer_conversation_id(surface: str, rows: list[dict[str, Any]], trace_path: Path, explicit: str | None) -> str | None:
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
def _slice_rows(surface: str, rows: list[dict[str, Any]], start_step: int | None, end_step: int | None) -> list[dict[str, Any]]:
	if None is start_step and None is end_step:
		r = rows
	elif 'codex' == surface:
		lo = max(0, int(start_step)) if None is not start_step else 0
		hi = int(end_step) + 1 if None is not end_step else len(rows)
		r = rows[lo:hi]
	else:
		r = [row for pos, row in enumerate(rows) if (None is start_step or int(row.get('step_index', pos)) >= start_step) and (None is end_step or int(row.get('step_index', pos)) <= end_step)]
	return r
def build_timesheet(trace_path: str | Path, *, conversation_id: str | None=None, summary_db: str | Path | None=None, turn_start_step: int | None=None, turn_end_step: int | None=None, top_gaps_limit: int=10) -> dict[str, Any]:
	tp = Path(trace_path).resolve()
	digest, all_rows = load_jsonl_rows(tp)
	surface = _detect_surface(all_rows)
	cid = _infer_conversation_id(surface, all_rows, tp, conversation_id)
	rows = _slice_rows(surface, all_rows, turn_start_step, turn_end_step)
	if 'codex' == surface:
		body = analyze_codex_rows(rows, top_gaps_limit=top_gaps_limit)
	else:
		u_ts, m_ts = read_summary_timestamps(Path(summary_db) if summary_db else None, cid)
		body = analyze_antigravity_rows(rows, last_user_ts=u_ts, last_mod_ts=m_ts, top_gaps_limit=top_gaps_limit)
	return {'schema_version': 1, 'valid': True, 'surface': surface, 'conversation_id': cid, 'trace_file': tp.as_posix(), 'trace_sha256': digest, 'step_count': len(rows), 'slice': {'start_step': turn_start_step, 'end_step': turn_end_step}, **body}
def run_perf_timesheet_cli(args) -> dict[str, Any]:
	src = resolve_trace_source(trace=args.trace, conversation=args.conversation, project=args.project, journal_step=args.journal_step, instance=args.instance, platform=args.platform, summary_db=args.summary_db, turn_start_step=args.turn_start_step)
	report = build_timesheet(src['trace_path'], conversation_id=src['conversation_id'], summary_db=src['summary_db'], turn_start_step=src['turn_start_step'], turn_end_step=args.turn_end_step, top_gaps_limit=args.top_gaps)
	if None is not args.output:
		out_p = Path(args.output).resolve()
		out_p.parent.mkdir(parents=True, exist_ok=True)
		out_p.write_text(json.dumps(report, ensure_ascii=False, indent='\t') + '\n', encoding='utf-8')
		report['output_file'] = out_p.as_posix()
	return report
__all__ = ['build_timesheet', 'format_timesheet_text', 'run_perf_timesheet_cli']
