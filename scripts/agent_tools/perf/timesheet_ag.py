# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from typing import Any
import re
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.array.first import df_first, df_last
from ..platforms.trace_common import parse_tool_args
from .timesheet_common import classify_command, compute_top_gaps, parse_iso_ts, parse_test_output, round_opt
_BG_LAUNCH_RE = re.compile(r'Tool is running as a background task with task id:\s*(\S+)')
_BG_DONE_RE = re.compile(r'sender=(\S+)\b[\s\S]*?Task id "([^"]+)" finished with result:')
_COMPLETED_AT_RE = re.compile(r'Completed At:\s*(\S+)')
_CREATED_AT_RE = re.compile(r'Created At:\s*(\S+)')
_ERR_RE = re.compile(r'Encountered error in step execution|failed to read file|cannot find the file|Command exited with code [1-9]', re.I)
_TRUNC_RE = re.compile(r"tool's output was truncated|truncated due to being too long", re.I)
# @used-by :func:`_record_tool_call()`
def _add_cat(cats: dict[str, dict[str, Any]], cat: str, wall_s: float) -> None:
	slot = cats.setdefault(cat, {'count': 0, 'wall_s': 0.0})
	slot['count'] += 1
	slot['wall_s'] = round(slot['wall_s'] + max(0.0, wall_s), 3)
# @used-by :func:`_build_ag_result()`
def _ag_timestamps(rows: list[dict[str, Any]], last_user_ts: str | None, last_mod_ts: str | None) -> dict[str, Any]:
	ts_vals = [t for r in rows if None is not (t := parse_iso_ts(r.get('created_at')))]
	# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
	t_start = df_first(ts_vals)
	t_last = df_last(ts_vals)
	t_mod = parse_iso_ts(last_mod_ts)
	step_span = t_last - t_start if None is not t_start and None is not t_last else None
	mod_span = t_mod - t_start if None is not t_start and None is not t_mod else None
	return {'start_utc': rows[0].get('created_at') if rows else None, 'last_step_start_utc': rows[-1].get('created_at') if rows else None, 'db_last_user_input_time': last_user_ts, 'last_modified_utc': last_mod_ts, 'total_span_to_last_step_s': round_opt(step_span), 'total_span_to_last_modified_s': round_opt(mod_span)}
# @used-by :func:`analyze_antigravity_rows()`
def _bg_match_records(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
	done_map: dict[str, dict[str, Any]] = {}
	for row in rows:
		if 'SYSTEM_MESSAGE' == row.get('type'):
			content = str(row.get('content') or '')
			m = _BG_DONE_RE.search(content)
			if None is not m:
				done_map[m.group(1)] = {'done_step': row.get('step_index'), 'done_ts': parse_iso_ts(row.get('created_at')), 'content': content}
	return done_map
# @used-by :func:`analyze_antigravity_rows()`
def _build_ag_result(rows: list[dict[str, Any]], st: dict[str, Any], last_user_ts: str | None, last_mod_ts: str | None, top_gaps_limit: int) -> dict[str, Any]:
	cold_n = sum((1 for s in st['switches'] if s['cold_cache']))
	net_tests = round(st['sync_test_s'] + sum((b['idle_wait_s'] for b in st['bg_waits'])), 3)
	return {
		'timestamps': _ag_timestamps(rows, last_user_ts, last_mod_ts),
		'models': {'planner_steps_by_model': dict(sorted(st['model_steps'].items())), 'model_switches': st['switches'], 'cold_switch_count': cold_n, 'cold_switch_uncached_input_tokens': st['cold_tokens'], 'same_model_cache_misses': st['same_misses'], 'peak_context_tokens': st['peak_tokens'], 'peak_context_step': st['peak_step']},
		'tokens': {'fresh_input_tokens': st['tokens']['fresh_input_tokens'], 'cache_read_tokens': st['tokens']['cache_read_tokens'], 'output_tokens': st['tokens']['output_tokens'], 'plan_mode_output_tokens': st['plan_tokens'], 'unreported_records': st['unreported']},
		'checkpoints': st['checkpoints'],
		'tools': {'tool_calls_total': sum(st['tools'].values()), 'tool_calls_by_name': dict(sorted(st['tools'].items(), key=lambda kv: (-kv[1], kv[0]))), 'error_results_count': st['errors'], 'truncated_outputs': st['truncated']},
		'commands': {'categories': dict(sorted(st['cats'].items())), 'bg_test_waits': st['bg_waits'], 'net_wall_time_blocked_on_tests_s': net_tests},
		'top_gaps': compute_top_gaps(st['events'], limit=top_gaps_limit),
	}
# @used-by :func:`_record_tool_call()`
def _command_wall_and_bg(idx: int, tool_pos: int, rows: list[dict[str, Any]], cmd: str, done_map: dict[str, dict[str, Any]]) -> tuple[float, dict[str, Any] | None]:
	call_step = rows[idx].get('step_index')
	call_ts = parse_iso_ts(rows[idx].get('created_at'))
	res_idx = idx + 1 + tool_pos
	nxt = rows[res_idx] if res_idx < len(rows) and 'GENERIC' == rows[res_idx].get('type') else None
	nxt_txt = str(nxt.get('content') or '') if nxt else ''
	m_bg = _BG_LAUNCH_RE.search(nxt_txt)
	if None is not m_bg:
		r = _resolve_bg_wait(res_idx, rows, call_step, call_ts, m_bg.group(1), cmd, done_map)
	else:
		r = (_sync_generic_dur(call_ts, nxt, nxt_txt), None)
	return r
# @used-by :func:`_resolve_bg_wait()`
def _extract_step_end_ts(row: dict[str, Any]) -> float | None:
	content = str(row.get('content') or '')
	matches = _COMPLETED_AT_RE.findall(content)
	return parse_iso_ts(matches[-1]) if matches else parse_iso_ts(row.get('created_at'))
# @used-by :func:`analyze_antigravity_rows()`
def _init_ag_state() -> dict[str, Any]:
	return {'cats': {}, 'bg_waits': [], 'checkpoints': [], 'cold_tokens': 0, 'errors': 0, 'events': [], 'last_model': None, 'model_steps': Counter(), 'plan_tokens': 0, 'peak_step': None, 'peak_tokens': 0, 'same_misses': [], 'switches': [], 'sync_test_s': 0.0, 'tokens': Counter(), 'tools': Counter(), 'truncated': [], 'unreported': 0}
# @used-by :func:`analyze_antigravity_rows()`
def _process_planner_step(idx: int, row: dict[str, Any], rows: list[dict[str, Any]], done_map: dict[str, dict[str, Any]], st: dict[str, Any]) -> None:
	step_idx = int(row.get('step_index', idx))
	model = str(row.get('model') or 'unknown')
	st['model_steps'][model] += 1
	_record_tokens_and_switches(step_idx, row, model, st)
	calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
	for tpos, call in enumerate(calls):
		_record_tool_call(idx, tpos, call, rows, done_map, st)
	if any(('exit_plan_mode' == c.get('name') for c in calls)) and isinstance(row.get('output_tokens'), int):
		st['plan_tokens'] += row['output_tokens']
	summary = ', '.join((str(c.get('name')) for c in calls)) or 'final_or_text'
	st['events'].append((step_idx, parse_iso_ts(row.get('created_at')), 'PLANNER_RESPONSE', model, summary))
# @used-by :func:`analyze_antigravity_rows()`
def _record_checkpoint(idx: int, row: dict[str, Any], rows: list[dict[str, Any]], st: dict[str, Any]) -> None:
	t0 = parse_iso_ts(row.get('created_at'))
	t1 = parse_iso_ts(rows[idx + 1].get('created_at')) if idx + 1 < len(rows) else None
	dur = round(max(0.0, t1 - t0), 3) if None is not t0 and None is not t1 else None
	in_t = row.get('input_tokens') if isinstance(row.get('input_tokens'), int) else 0
	cr_t = row.get('cache_read_tokens') if isinstance(row.get('cache_read_tokens'), int) else 0
	ctx = in_t + cr_t
	if ctx > st['peak_tokens']:
		st['peak_tokens'], st['peak_step'] = (ctx, int(row.get('step_index', idx)))
	st['checkpoints'].append({'step': int(row.get('step_index', idx)), 'at': row.get('created_at'), 'dur_s': dur, 'pre_step_tokens': ctx or None})
	st['events'].append((int(row.get('step_index', idx)), t0, 'CHECKPOINT', None, 'context_compaction'))
# @used-by :func:`analyze_antigravity_rows()`
def _record_generic_step(idx: int, row: dict[str, Any], st: dict[str, Any]) -> None:
	content = str(row.get('content') or '')
	step_idx = int(row.get('step_index', idx))
	if _ERR_RE.search(content):
		st['errors'] += 1
	if _TRUNC_RE.search(content) or 15000 <= len(content):
		st['truncated'].append({'step': step_idx, 'chars': len(content), 'truncated_marker': bool(_TRUNC_RE.search(content))})
	first_ln = content.splitlines()[0] if content.splitlines() else ''
	st['events'].append((step_idx, parse_iso_ts(row.get('created_at')), str(row.get('type') or 'GENERIC'), None, first_ln))
# @used-by :func:`_process_planner_step()`
def _record_tokens_and_switches(step_idx: int, row: dict[str, Any], model: str, st: dict[str, Any]) -> None:
	in_t, cr_t, out_t = (row.get('input_tokens'), row.get('cache_read_tokens'), row.get('output_tokens'))
	if all((isinstance(v, int) and 0 <= v for v in (in_t, cr_t, out_t))):
		st['tokens']['fresh_input_tokens'] += in_t
		st['tokens']['cache_read_tokens'] += cr_t
		st['tokens']['output_tokens'] += out_t
		if in_t + cr_t > st['peak_tokens']:
			st['peak_tokens'], st['peak_step'] = (in_t + cr_t, step_idx)
		_record_model_switch(step_idx, model, in_t, cr_t, st)
	else:
		st['unreported'] += 1
	st['last_model'] = model
# @used-by :func:`_record_tokens_and_switches()`
def _record_model_switch(step_idx: int, model: str, in_t: int, cr_t: int, st: dict[str, Any]) -> None:
	prev = st['last_model']
	if None is not prev and model != prev:
		cold = 0 == cr_t
		st['switches'].append({'step': step_idx, 'from_model': prev, 'to_model': model, 'cold_cache': cold, 'input_tokens': in_t, 'cache_read_tokens': cr_t})
		if cold:
			st['cold_tokens'] += in_t
	elif None is not prev and model == prev and 0 == cr_t:
		st['same_misses'].append({'step': step_idx, 'model': model, 'input_tokens': in_t})
# @used-by :func:`_process_planner_step()`
def _record_tool_call(idx: int, tool_pos: int, call: dict[str, Any], rows: list[dict[str, Any]], done_map: dict[str, dict[str, Any]], st: dict[str, Any]) -> None:
	name = str(call.get('name') or 'unknown')
	st['tools'][name] += 1
	if name.endswith('run_command'):
		cmd = str(parse_tool_args(call.get('args', {})).get('CommandLine') or '')
		cat = classify_command(cmd)
		wall_s, bg_info = _command_wall_and_bg(idx, tool_pos, rows, cmd, done_map)
		_add_cat(st['cats'], cat, wall_s)
		if None is not bg_info and 'test_runs' == cat:
			st['bg_waits'].append(bg_info)
		elif 'test_runs' == cat:
			st['sync_test_s'] += wall_s
# @used-by :func:`_command_wall_and_bg()`
def _resolve_bg_wait(idx: int, rows: list[dict[str, Any]], call_step: Any, call_ts: float | None, task_id: str, cmd: str, done_map: dict[str, dict[str, Any]]) -> tuple[float, dict[str, Any] | None]:
	done = done_map.get(task_id)
	if None is done or None is call_ts or None is done.get('done_ts'):
		r: tuple[float, dict[str, Any] | None] = (0.0, None)
	else:
		wall_s = round(max(0.0, done['done_ts'] - call_ts), 3)
		done_pos = next((j for j in range(idx + 1, len(rows)) if rows[j].get('step_index') == done['done_step']), len(rows))
		prev_end = _extract_step_end_ts(rows[done_pos - 1]) if done_pos - 1 > idx else call_ts
		idle_s = round(max(0.0, done['done_ts'] - (prev_end if None is not prev_end else call_ts)), 3)
		tests_n, runner_s = parse_test_output(done['content'])
		r = (wall_s, {'call_step': call_step, 'bg_task': task_id, 'done_step': done['done_step'], 'wall_s': wall_s, 'idle_wait_s': idle_s, 'overlapped_work_s': round(max(0.0, wall_s - idle_s), 3), 'tests_count': tests_n, 'runner_s': runner_s, 'command': cmd[:160]})
	return r
# @used-by :func:`_command_wall_and_bg()`
def _sync_generic_dur(call_ts: float | None, nxt: dict[str, Any] | None, nxt_txt: str) -> float:
	c_starts = _CREATED_AT_RE.findall(nxt_txt)
	c_ends = _COMPLETED_AT_RE.findall(nxt_txt)
	t0 = parse_iso_ts(c_starts[0]) if c_starts else call_ts
	t1 = parse_iso_ts(c_ends[-1]) if c_ends else (parse_iso_ts(nxt.get('created_at')) if nxt else None)
	return round(max(0.0, t1 - t0), 3) if None is not t0 and None is not t1 else 0.0
# 2026-11-24
# "Add harness perf-timesheet CLI for deterministic turn chronometry":
# https://github.com/dmitry-ai/harness/issues/191
# @used-by :func:`agent_tools.perf.timesheet.build_timesheet()`
def analyze_antigravity_rows(rows: list[dict[str, Any]], *, last_user_ts: str | None=None, last_mod_ts: str | None=None, top_gaps_limit: int=10) -> dict[str, Any]:
	st = _init_ag_state()
	done_map = _bg_match_records(rows)
	for idx, row in enumerate(rows):
		rtype = row.get('type')
		if 'PLANNER_RESPONSE' == rtype:
			_process_planner_step(idx, row, rows, done_map, st)
		elif 'CHECKPOINT' == rtype:
			_record_checkpoint(idx, row, rows, st)
		else:
			_record_generic_step(idx, row, st)
	return _build_ag_result(rows, st, last_user_ts, last_mod_ts, top_gaps_limit)
