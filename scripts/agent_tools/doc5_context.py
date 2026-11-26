# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Trigger DOC-5 four-track validation from active-turn bug-report signals":
# https://github.com/dmitry-ai/harness/issues/294
from __future__ import annotations
from typing import Any
import re
from .hook_crash_audit import _load_turn_rows
from .platforms.trace_common import parse_tool_args
from .tdd_gate import _BG_TASK_FINISHED_RE, parse_command_outcome
_EXCLUDED_CLI_RE = re.compile(r'\b(?:pytest|unittest|run-tests|test-watchdog|perf-profile-tests|answer-check|answer-prepare|tdd-check|issue-first-check|analysis-check|rules-audit)\b', re.IGNORECASE)
_HARNESS_CLI_RE = re.compile(r'(?:harness|upwork_project|df_github_issue|validate_step)\.py', re.IGNORECASE)
# @used-by :func:`_earliest_cli_failure_step()`
def _cmd_from_call(call: dict[str, Any]) -> str:
	name = str(call.get('name') or '')
	r = ''
	if 'exec' == name or name.endswith(('run_command', 'exec_command')):
		args = parse_tool_args(call.get('args', call.get('arguments', {})))
		r = str(args.get('CommandLine') or args.get('cmd') or args.get('command') or '')
	return r
# @used-by :func:`_earliest_cli_failure_step()`
def _is_failed_cli_output(text: str) -> bool:
	out = parse_command_outcome(text)
	low = (text or '').lower()
	rc = out.get('exit_code')
	return (None is not rc and 0 != rc) or 'fail' == out.get('status') or '"valid": false' in low or '"valid":false' in low or 'valueerror:' in low or 'traceback (most recent call last)' in low
# @used-by :func:`_earliest_cli_failure_step()`
def _row_outputs(rows: list[dict[str, Any]], pos: int) -> list[str]:
	outs: list[str] = []
	for cand in rows[pos + 1:]:
		if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
			break
		if 'GENERIC' == cand.get('type') and cand.get('content'):
			outs.append(str(cand.get('content')))
	return outs
# @used-by :func:`_earliest_cli_failure_step()`
def _record_bg_cli_failures(rows: list[dict[str, Any]], bg_steps: dict[str, int], hits: list[int]) -> None:
	for row in rows:
		if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and row.get('content'):
			m_fin = _BG_TASK_FINISHED_RE.search(str(row.get('content')))
			if None is not m_fin and m_fin.group(1).strip() in bg_steps and _is_failed_cli_output(m_fin.group(2)):
				hits.append(bg_steps[m_fin.group(1).strip()])
# @used-by :func:`_earliest_cli_failure_step()`
def _inspect_call_failure(call: dict[str, Any], matched: str, step_idx: int, bg_steps: dict[str, int], hits: list[int]) -> None:
	cmd = _cmd_from_call(call)
	if cmd and _HARNESS_CLI_RE.search(cmd) and (not _EXCLUDED_CLI_RE.search(cmd)):
		out_info = parse_command_outcome(matched)
		if out_info.get('background_task_id'):
			bg_steps[str(out_info['background_task_id'])] = step_idx
		elif _is_failed_cli_output(matched):
			hits.append(step_idx)
# @used-by :func:`turn_requires_doc5_problem_analysis()`
def _earliest_cli_failure_step(turn: dict[str, Any], native: dict[str, Any] | None) -> int | None:
	rows = _load_turn_rows(native, turn)
	bg_steps: dict[str, int] = {}
	hits: list[int] = []
	for pos, row in enumerate(rows):
		calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
		if not calls:
			continue
		step_idx = row['step_index'] if isinstance(row.get('step_index'), int) else pos
		outs = _row_outputs(rows, pos)
		joined = '\n'.join(outs)
		for idx, call in enumerate(calls):
			_inspect_call_failure(call, outs[idx] if idx < len(outs) else joined, step_idx, bg_steps, hits)
	_record_bg_cli_failures(rows, bg_steps, hits)
	return min(hits) if hits else None
# @used-by :func:`turn_requires_doc5_problem_analysis()`
def _has_post_failure_parent_issue(turn: dict[str, Any], fail_step: int) -> bool:
	r = False
	for act in turn.get('issue_actions') or ():
		if isinstance(act, dict) and 'create' == str(act.get('action') or '').lower() and None is act.get('parent_number'):
			act_step = act.get('step')
			if None is act_step or (isinstance(act_step, int) and act_step >= fail_step):
				r = True
				break
	return r
# @used-by :func:`agent_tools.statements._detect_mode()`
def detect_df_analysis_mode(text: str, blocks: list[dict], requests: list | tuple, mode: str, *, turn_context: dict | None, prob_head_re, req_cmd_fn, explicit_fn) -> str:
	if mode in ('general', 'problem'):
		r = mode
	else:
		has_s0_meta = any((0 in b['sections'] and bool(prob_head_re.search(b['sections'][0][0])) for b in blocks))
		has_s1_prob = any((1 in b['sections'] and bool(prob_head_re.search(b['sections'][1][0])) and bool({2, 3, 4} & set(b['sections'])) for b in blocks))
		if has_s0_meta or has_s1_prob or turn_requires_doc5_problem_analysis(turn_context):
			r = 'problem'
		elif req_cmd_fn(requests):
			r = 'problem' if any((0 in b['sections'] for b in blocks)) else 'general'
		else:
			hyps, mets = explicit_fn(text)
			r = 'general' if hyps or mets else 'none'
	return r
# @used-by :func:`detect_df_analysis_mode()`
def turn_requires_doc5_problem_analysis(turn_context: dict | None) -> bool:
	r = False
	if isinstance(turn_context, dict):
		if turn_context.get('bug_report_signal'):
			r = True
		else:
			turn = turn_context.get('turn')
			if isinstance(turn, dict) and 'standalone' != turn.get('turn_id'):
				fail_step = _earliest_cli_failure_step(turn, turn_context.get('native'))
				r = None is not fail_step and _has_post_failure_parent_issue(turn, fail_step)
	return r
__all__ = ['detect_df_analysis_mode', 'turn_requires_doc5_problem_analysis']