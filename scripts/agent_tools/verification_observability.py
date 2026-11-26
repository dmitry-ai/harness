# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add verification observability gate for failed shadow-replay runs":
# https://github.com/dmitry-ai/harness/issues/296
from __future__ import annotations
from pathlib import Path
from typing import Any
import re
from .hook_crash_audit import _load_turn_rows
from .platforms.trace_common import parse_tool_args
from .tdd_gate import _BG_TASK_FINISHED_RE, parse_command_outcome
_SHADOW_CMD_RE = re.compile(r'\bshadow-replay\b', re.IGNORECASE)
_FAIL_DISCLOSE_RE = re.compile(r'(?i)(?:valid\s*[:=]\s*false|"valid"\s*:\s*false|exit(?:ed)?\s*(?:with\s+code\s+|status\s+|=)?[1-9]\d*|\bfail(?:ed|ure)?\b|\berror\b|\u0443\u043f\u0430\u043b|\u043f\u0440\u043e\u0432\u0430\u043b|\u043e\u0448\u0438\u0431\u043a|\u043d\u0435\s+\u043f\u0440\u043e\u0448)')
# @used-by :func:`_inspect_shadow_call()`
def _cmd_from_call(call: dict[str, Any]) -> str:
	name = str(call.get('name') or '')
	r = ''
	if 'exec' == name or name.endswith(('run_command', 'exec_command')):
		args = parse_tool_args(call.get('args', call.get('arguments', {})))
		r = str(args.get('CommandLine') or args.get('cmd') or args.get('command') or '')
	return r
# @used-by :func:`_inspect_shadow_call()`
# @used-by :func:`_resolve_bg_shadow_runs()`
def _classify_shadow_output(step_idx: int, text: str) -> dict[str, Any]:
	out = parse_command_outcome(text)
	low = (text or '').lower()
	rc = out.get('exit_code')
	has_invalid = '"valid": false' in low or '"valid":false' in low
	failed = has_invalid or (None is not rc and 0 != rc) or 'fail' == out.get('status')
	passed = (not failed) and (0 == rc or ('pass' == out.get('status') and None is rc))
	return {'step': step_idx, 'passed': passed, 'failed': failed, 'exit_code': rc}
# @used-by :func:`detect_shadow_replay_runs()`
def _row_outputs(rows: list[dict[str, Any]], pos: int) -> list[str]:
	outs: list[str] = []
	for cand in rows[pos + 1:]:
		if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
			break
		if 'GENERIC' == cand.get('type') and cand.get('content'):
			outs.append(str(cand.get('content')))
	return outs
# @used-by :func:`detect_shadow_replay_runs()`
def _inspect_shadow_call(call: dict[str, Any], matched: str, step_idx: int, bg_steps: dict[str, int], runs: list[dict[str, Any]]) -> None:
	cmd = _cmd_from_call(call)
	if cmd and _SHADOW_CMD_RE.search(cmd):
		out_info = parse_command_outcome(matched)
		if out_info.get('background_task_id'):
			bg_steps[str(out_info['background_task_id'])] = step_idx
		else:
			runs.append(_classify_shadow_output(step_idx, matched))
# @used-by :func:`detect_shadow_replay_runs()`
def _resolve_bg_shadow_runs(rows: list[dict[str, Any]], bg_steps: dict[str, int], runs: list[dict[str, Any]]) -> None:
	for row in rows:
		if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and row.get('content'):
			m_fin = _BG_TASK_FINISHED_RE.search(str(row.get('content')))
			if None is not m_fin and m_fin.group(1).strip() in bg_steps:
				runs.append(_classify_shadow_output(bg_steps[m_fin.group(1).strip()], m_fin.group(2)))
# @used-by :func:`evaluate_verification_observability()`
def _closed_issues_after(turn: dict[str, Any] | None, fail_step: int) -> list[str]:
	closed: list[str] = []
	for act in (turn or {}).get('issue_actions') or ():
		if isinstance(act, dict) and 'close' == str(act.get('action') or '').lower():
			act_step = act.get('step')
			if None is act_step or (isinstance(act_step, int) and act_step >= fail_step):
				label = f"{act['repo']}#{act['number']}" if act.get('repo') and act.get('number') else str(act.get('url') or 'issue')
				closed.append(label)
	return closed
# @used-by :func:`evaluate_verification_observability()`
def _latest_unresolved_failure(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
	ordered = sorted(runs, key=lambda x: int(x.get('step') or 0))
	fail_idx = max((i for i, it in enumerate(ordered) if it.get('failed')), default=-1)
	if 0 > fail_idx:
		r = None
	elif any((it.get('passed') for it in ordered[fail_idx + 1:])):
		r = None
	else:
		r = ordered[fail_idx]
	return r
# @used-by :func:`evaluate_verification_observability()`
def _response_discloses_shadow_failure(response: str | None) -> bool:
	raw = str(response or '')
	return bool(_SHADOW_CMD_RE.search(raw)) and bool(_FAIL_DISCLOSE_RE.search(raw))
# @used-by :func:`evaluate_verification_observability()`
# @used-by :mod:`agent_tools.verification_observability`
def detect_shadow_replay_runs(native: dict[str, Any] | None, turn: dict[str, Any] | None) -> list[dict[str, Any]]:
	rows = _load_turn_rows(native, turn)
	bg_steps: dict[str, int] = {}
	runs: list[dict[str, Any]] = []
	for pos, row in enumerate(rows):
		calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
		if not calls:
			continue
		step_idx = row['step_index'] if isinstance(row.get('step_index'), int) else pos
		outs = _row_outputs(rows, pos)
		joined = '\n'.join(outs)
		for idx, call in enumerate(calls):
			_inspect_shadow_call(call, outs[idx] if idx < len(outs) else joined, step_idx, bg_steps, runs)
	_resolve_bg_shadow_runs(rows, bg_steps, runs)
	return runs
# @used-by :func:`agent_tools.blocked_report._run_runner_audits()`
# @used-by :mod:`agent_tools.verification_observability`
def check_runner_verification_observability(runner) -> None:
	chk = evaluate_verification_observability(runner.root, runner.native, runner.turn, runner.value, runner.response)
	runner.value['verification_observability_check'] = chk
	if not chk['verified']:
		runner._fail_gate('verification_observability', chk['detail'])
# @used-by :func:`agent_tools.gates.answer_checks._verification_obs_messages()`
# @used-by :func:`check_runner_verification_observability()`
# @used-by :mod:`agent_tools.verification_observability`
def evaluate_verification_observability(root: Path, native: dict[str, Any] | None, turn: dict[str, Any] | None, value: dict[str, Any] | None, response: str | None) -> dict[str, Any]:
	unresolved = _latest_unresolved_failure(detect_shadow_replay_runs(native, turn))
	if None is unresolved:
		r: dict[str, Any] = {'verified': True, 'unresolved_failure': None}
	else:
		fail_step = int(unresolved['step'])
		closed_after = _closed_issues_after(turn, fail_step)
		if closed_after:
			joined = ', '.join(closed_after[:5])
			r = {'verified': False, 'unresolved_failure': unresolved, 'closed_after_failure': closed_after, 'detail': f"EXEC-2 / VERIFY-4 verification_observability_check: unresolved shadow-replay failure at step {fail_step} (exit={unresolved.get('exit_code')}) was followed by closing issue(s) {joined} without a subsequent passing shadow-replay rerun."}
		elif _response_discloses_shadow_failure(response):
			r = {'verified': True, 'unresolved_failure': unresolved, 'resolution': 'disclosed_in_response'}
		else:
			r = {'verified': False, 'unresolved_failure': unresolved, 'detail': f"EXEC-2 / VERIFY-4 verification_observability_check: shadow-replay failed at step {fail_step} (exit={unresolved.get('exit_code')}) with no later passing rerun and without explicit failure disclosure in the response."}
	return r
__all__ = ['check_runner_verification_observability', 'detect_shadow_replay_runs', 'evaluate_verification_observability']