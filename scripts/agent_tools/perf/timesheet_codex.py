# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from typing import Any
from Df.Harness.lib.platform import dfh_timesheet_add_cat
from ..platforms.trace_common import parse_tool_args
from .timesheet_common import classify_command, compute_top_gaps, parse_iso_ts, round_opt
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# @used-by :func:`_record_codex_output()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _add_cat(cats: dict[str, dict[str, Any]], cat: str, wall_s: float) -> None:
	dfh_timesheet_add_cat(cats, cat, wall_s)
# @used-by :func:`analyze_codex_rows()`
def _build_codex_result(rows: list[dict[str, Any]], st: dict[str, Any], top_gaps_limit: int) -> dict[str, Any]:
	ts_vals = [t for r in rows if None is not (t := parse_iso_ts(r.get('timestamp')))]
	span = round_opt(ts_vals[-1] - ts_vals[0] if 2 <= len(ts_vals) else 0.0)
	test_wall = st['cats'].get('test_runs', {}).get('wall_s', 0.0)
	return {
		'timestamps': {'start_utc': rows[0].get('timestamp') if rows else None, 'last_step_start_utc': rows[-1].get('timestamp') if rows else None, 'db_last_user_input_time': None, 'last_modified_utc': None, 'total_span_to_last_step_s': span, 'total_span_to_last_modified_s': None},
		'models': {'planner_steps_by_model': dict(sorted(st['model_steps'].items())), 'model_switches': [], 'cold_switch_count': 0, 'cold_switch_uncached_input_tokens': 0, 'same_model_cache_misses': [], 'peak_context_tokens': st['peak_tokens'], 'peak_context_step': st['peak_step']},
		'tokens': {'fresh_input_tokens': st['tokens']['fresh_input_tokens'], 'cache_read_tokens': st['tokens']['cache_read_tokens'], 'output_tokens': st['tokens']['output_tokens'], 'plan_mode_output_tokens': 0, 'unreported_records': 0},
		'checkpoints': st['checkpoints'],
		'tools': {'tool_calls_total': sum(st['tools'].values()), 'tool_calls_by_name': dict(sorted(st['tools'].items(), key=lambda kv: (-kv[1], kv[0]))), 'error_results_count': 0, 'truncated_outputs': st['truncated']},
		'commands': {'categories': dict(sorted(st['cats'].items())), 'bg_test_waits': [], 'net_wall_time_blocked_on_tests_s': round(test_wall, 3)},
		'top_gaps': compute_top_gaps(st['events'], limit=top_gaps_limit),
	}
# @used-by :func:`analyze_codex_rows()`
def _init_cx_state() -> dict[str, Any]:
	return {'cats': {}, 'checkpoints': [], 'cur_model': None, 'events': [], 'model_steps': Counter(), 'peak_step': None, 'peak_tokens': 0, 'pending': {}, 'tokens': Counter(), 'tools': Counter(), 'truncated': []}
# @used-by :func:`analyze_codex_rows()`
def _process_codex_row(idx: int, row: dict[str, Any], rows: list[dict[str, Any]], st: dict[str, Any]) -> None:
	kind, ts = (row.get('type'), parse_iso_ts(row.get('timestamp')))
	pay = row.get('payload') if isinstance(row.get('payload'), dict) else {}
	if 'turn_context' == kind:
		st['cur_model'] = str(pay.get('model') or st['cur_model'] or 'unknown')
		st['model_steps'][st['cur_model']] += 1
	elif 'event_msg' == kind:
		_record_codex_event(idx, row, rows, ts, st)
	elif 'response_item' == kind:
		_record_codex_item(idx, pay, ts, st)
# @used-by :func:`_record_codex_item()`
def _record_codex_call(idx: int, pay: dict[str, Any], ts: float | None, st: dict[str, Any]) -> None:
	name = str(pay.get('name') or 'unknown')
	st['tools'][name] += 1
	cid = str(pay.get('call_id') or f'step-{idx}')
	args = parse_tool_args(pay.get('arguments', pay.get('input', {})))
	cmd = str(args.get('cmd') or args.get('command') or '')
	if name.endswith(('exec_command', 'run_command')) or 'exec' == name:
		st['pending'][cid] = (ts, classify_command(cmd))
	st['events'].append((idx, ts, name, st['cur_model'], cmd[:120] or name))
# @used-by :func:`_process_codex_row()`
def _record_codex_event(idx: int, row: dict[str, Any], rows: list[dict[str, Any]], ts: float | None, st: dict[str, Any]) -> None:
	pay = row.get('payload') if isinstance(row.get('payload'), dict) else {}
	etype = pay.get('type')
	if 'context_compacted' == etype:
		t_next = parse_iso_ts(rows[idx + 1].get('timestamp')) if idx + 1 < len(rows) else None
		dur = round(max(0.0, t_next - ts), 3) if None is not ts and None is not t_next else None
		st['checkpoints'].append({'step': idx, 'at': row.get('timestamp'), 'dur_s': dur, 'pre_step_tokens': st['peak_tokens'] or None})
		st['events'].append((idx, ts, 'CHECKPOINT', st['cur_model'], 'context_compacted'))
	elif 'token_count' == etype:
		_record_codex_tokens(idx, pay, st)
# @used-by :func:`_process_codex_row()`
def _record_codex_item(idx: int, pay: dict[str, Any], ts: float | None, st: dict[str, Any]) -> None:
	ptype = pay.get('type')
	if ptype in ('function_call', 'custom_tool_call'):
		_record_codex_call(idx, pay, ts, st)
	elif 'function_call_output' == ptype:
		_record_codex_output(idx, pay, ts, st)
# @used-by :func:`_record_codex_item()`
def _record_codex_output(idx: int, pay: dict[str, Any], ts: float | None, st: dict[str, Any]) -> None:
	cid = str(pay.get('call_id') or '')
	pending = st['pending'].pop(cid, None)
	if None is not pending:
		t0, cat = pending
		wall = round(max(0.0, ts - t0), 3) if None is not t0 and None is not ts else 0.0
		_add_cat(st['cats'], cat, wall)
	out = str(pay.get('output') or '')
	if 15000 <= len(out):
		st['truncated'].append({'step': idx, 'chars': len(out), 'truncated_marker': False})
# @used-by :func:`_record_codex_event()`
def _record_codex_tokens(idx: int, pay: dict[str, Any], st: dict[str, Any]) -> None:
	usage = (pay.get('info') or {}).get('last_token_usage') if isinstance(pay.get('info'), dict) else None
	if isinstance(usage, dict):
		in_t = int(usage.get('input_tokens') or 0)
		cr_t = int(usage.get('cached_input_tokens') or 0)
		out_t = int(usage.get('output_tokens') or 0)
		st['tokens']['fresh_input_tokens'] += max(0, in_t - cr_t)
		st['tokens']['cache_read_tokens'] += cr_t
		st['tokens']['output_tokens'] += out_t
		if in_t > st['peak_tokens']:
			st['peak_tokens'], st['peak_step'] = (in_t, idx)
# 2026-11-24
# "Add harness perf-timesheet CLI for deterministic turn chronometry":
# https://github.com/dmitry-ai/harness/issues/191
# @used-by :func:`agent_tools.perf.timesheet.build_timesheet()`
def analyze_codex_rows(rows: list[dict[str, Any]], *, top_gaps_limit: int=10) -> dict[str, Any]:
	st = _init_cx_state()
	for idx, row in enumerate(rows):
		_process_codex_row(idx, row, rows, st)
	return _build_codex_result(rows, st, top_gaps_limit)
