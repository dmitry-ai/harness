# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.lib.hook_crash_ops import dfh_load_turn_rows
from Df.Harness.lib.trace import dfh_cmd_from_call, dfh_row_outputs
from agent_tools.cli_output_json import top_level_json_has_failure
from agent_tools.tdd_gate import _BG_TASK_FINISHED_RE, parse_command_outcome
import re
import shlex
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_FAIL_DISCLOSE_RE = re.compile(r'(?i)(?:valid\s*[:=]\s*false|"valid"\s*:\s*false|exit(?:ed)?\s*(?:with\s+code\s+|status\s+|=)?[1-9]\d*|\bfail(?:ed|ure)?\b|\berror\b|\u0443\u043f\u0430\u043b|\u043f\u0440\u043e\u0432\u0430\u043b|\u043e\u0448\u0438\u0431\u043a|\u043d\u0435\s+\u043f\u0440\u043e\u0448)')
_SHADOW_CLI_RE = re.compile(r'(?:^|[;&|\r\n]\s*)(?:[^;&|\r\n]*?\s)?[\'"]?[^\'"\s;&|]*\b(?:harness|upwork_project)\.py[\'"]?\s+shadow-replay(?:\s|$|[;&|])', re.IGNORECASE)
_SHADOW_CMD_RE = re.compile(r'\bshadow-replay\b', re.IGNORECASE)
# @used-by :func:`dfh_detect_shadow_replay_runs()`
def _inspect_shadow_call(call: dict[str, Any], matched: str, step_idx: int, bg_steps: dict[str, int], runs: list[dict[str, Any]]) -> None:
	cmd = dfh_cmd_from_call(call)
	if cmd and dfh_is_shadow_replay_cmd(cmd):
		out_info = parse_command_outcome(matched)
		if out_info.get('background_task_id'):
			bg_steps[str(out_info['background_task_id'])] = step_idx
		else:
			runs.append(dfh_classify_shadow_output(step_idx, matched))
# @used-by :func:`dfh_detect_shadow_replay_runs()`
def _resolve_bg_shadow_runs(rows: list[dict[str, Any]], bg_steps: dict[str, int], runs: list[dict[str, Any]]) -> None:
	for row in rows:
		if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and row.get('content'):
			m_fin = _BG_TASK_FINISHED_RE.search(str(row.get('content')))
			if None is not m_fin and m_fin.group(1).strip() in bg_steps:
				runs.append(dfh_classify_shadow_output(bg_steps[m_fin.group(1).strip()], m_fin.group(2)))
# @used-by :func:`Df.Harness.lib.blocked_report_ops._run_runner_audits()`
# @used-by :mod:`agent_tools.verification_observability`
def dfh_check_runner_verification_observability(runner) -> None:
	from Df.Harness.Hook.VerificationObserver import VerificationObserver
	chk = VerificationObserver(runner.root, runner.native, runner.turn, runner.value, runner.response).run()
	runner.value['verification_observability_check'] = chk
	if not chk['verified']:
		runner._fail_gate('verification_observability', chk['detail'])
# @used-by :func:`_inspect_shadow_call()`
# @used-by :func:`_resolve_bg_shadow_runs()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_verif_pre_invocation_and_crash_ops()`
# @used-by :meth:`test_turn_begin_status_and_auditors.TurnBeginStatusAndAuditorsTests.test_all_trace_auditors_ignore_nested_foreign_reconciliation_and_flag_top_level_failure()`
# @used-by :mod:`agent_tools.verification_observability`
def dfh_classify_shadow_output(step_idx: int, text: str) -> dict[str, Any]:
	out = parse_command_outcome(text)
	rc = out.get('exit_code')
	has_invalid = top_level_json_has_failure(text)
	failed = has_invalid or (None is not rc and 0 != rc) or 'fail' == out.get('status')
	passed = (not failed) and (0 == rc or ('pass' == out.get('status') and None is rc))
	return {'exit_code': rc, 'failed': failed, 'passed': passed, 'step': step_idx}
# @used-by :meth:`Df.Harness.Hook.VerificationObserver.VerificationObserver.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_verif_pre_invocation_and_crash_ops()`
# @used-by :mod:`agent_tools.verification_observability`
def dfh_closed_issues_after(turn: dict[str, Any] | None, fail_step: int) -> list[str]:
	closed: list[str] = []
	for act in (turn or {}).get('issue_actions') or ():
		if isinstance(act, dict) and 'close' == str(act.get('action') or '').lower():
			act_step = act.get('step')
			if None is act_step or (isinstance(act_step, int) and act_step >= fail_step):
				repo, num = (act.get('repo'), act.get('number'))
				label = f'{repo}#{num}' if repo and num else str(act.get('url') or 'issue')
				closed.append(label)
	return closed
# @used-by :meth:`Df.Harness.Hook.VerificationObserver.VerificationObserver.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_verif_pre_invocation_and_crash_ops()`
# @used-by :meth:`test_observability_diagnostics.ObservabilityDiagnosticsTests.test_detect_shadow_replay_ignores_cli_arguments_and_matches_real_invocations()`
# @used-by :mod:`agent_tools.verification_observability`
def dfh_detect_shadow_replay_runs(native: dict[str, Any] | None, turn: dict[str, Any] | None) -> list[dict[str, Any]]:
	rows = dfh_load_turn_rows(native, turn)
	bg_steps: dict[str, int] = {}
	runs: list[dict[str, Any]] = []
	for pos, row in enumerate(rows):
		calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
		if not calls:
			continue
		step_idx = row['step_index'] if isinstance(row.get('step_index'), int) else pos
		outs = dfh_row_outputs(rows, pos)
		joined = '\n'.join(outs)
		for idx, call in enumerate(calls):
			_inspect_shadow_call(call, outs[idx] if idx < len(outs) else joined, step_idx, bg_steps, runs)
	_resolve_bg_shadow_runs(rows, bg_steps, runs)
	return runs
# @used-by :func:`_inspect_shadow_call()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_verif_pre_invocation_and_crash_ops()`
# @used-by :mod:`agent_tools.verification_observability`
def dfh_is_shadow_replay_cmd(cmd: str) -> bool:
	r = False
	if _SHADOW_CMD_RE.search(cmd):
		try:
			toks = shlex.split(cmd, posix=False)
		except ValueError:
			r = bool(_SHADOW_CLI_RE.search(cmd))
		else:
			for idx in range(len(toks) - 1):
				cur = toks[idx].strip('\'"').replace('\\', '/').lower()
				nxt = toks[idx + 1].strip('\'"').lower()
				if cur.endswith(('harness.py', 'upwork_project.py')) and 'shadow-replay' == nxt:
					r = True
					break
	return r
# @used-by :meth:`Df.Harness.Hook.VerificationObserver.VerificationObserver.run()`
# @used-by :mod:`agent_tools.verification_observability`
def dfh_latest_unresolved_failure(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
	ordered = sorted(runs, key=lambda x: int(x.get('step') or 0))
	fail_idx = max((i for i, it in enumerate(ordered) if it.get('failed')), default=-1)
	if 0 > fail_idx:
		r = None
	elif any((it.get('passed') for it in ordered[fail_idx + 1:])):
		r = None
	else:
		r = ordered[fail_idx]
	return r
# @used-by :meth:`Df.Harness.Hook.VerificationObserver.VerificationObserver.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_verif_pre_invocation_and_crash_ops()`
# @used-by :mod:`agent_tools.verification_observability`
def dfh_response_discloses_shadow_failure(response: str | None) -> bool:
	raw = str(response or '')
	return bool(_SHADOW_CMD_RE.search(raw)) and bool(_FAIL_DISCLOSE_RE.search(raw))