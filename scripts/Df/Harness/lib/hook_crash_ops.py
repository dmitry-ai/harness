# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_resolve import dfh_project_paths
import json
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_HOOK_CRASH_RE = re.compile(r'JSON hook "([^"]+)" failed[^\r\n]*', re.IGNORECASE)
_HOOK_FAILURE_WORD_RE = re.compile(r'(?i)(?:fail(?:ed|ure)?|crash\w*|timeout|exit\s+status\s+[1-9]\d*|таймаут\w*|падени\w*|сбо[йяею]\w*|упал\w*|ошибк\w*|обрыв\w*)')
_HOOK_TOPIC_RE = re.compile(r'(?i)(?:json\s+hook|pretooluse|stop\s+gate|preinvocation|rules-and-server-gate|doc4-anti-slop-gate|final-turn-gate|harness_hook_runner|хук[а-я]*)')
# @used-by :func:`dfh_has_recorded_hook_issue()`
def _collect_issue_refs(turn: dict[str, Any], value: dict[str, Any] | None) -> list[tuple[str, int]]:
	raw_items: list[Any] = list(turn.get('issue_actions') or ())
	gh_raw = (value or {}).get('github_issues')
	if isinstance(gh_raw, dict):
		raw_items.extend(gh_raw.values())
	elif isinstance(gh_raw, list):
		raw_items.extend(gh_raw)
	refs: list[tuple[str, int]] = []
	for it in raw_items:
		if isinstance(it, dict):
			slug, num = (str(it.get('repo') or '').strip(), it.get('number'))
			if slug and isinstance(num, int) and (not isinstance(num, bool)):
				refs.append((slug, num))
	return refs
# @used-by :func:`dfh_detect_hook_crashes()`
def _extract_hook_error(row: dict[str, Any]) -> tuple[str, str] | None:
	r: tuple[str, str] | None = None
	if 'ERROR' == str(row.get('status') or '').strip().upper():
		for raw in (row.get('error'), row.get('content')):
			m = _HOOK_CRASH_RE.search(str(raw or ''))
			if None is not m:
				r = (m.group(1), m.group(0).strip())
				break
	return r
# @used-by :func:`dfh_has_recorded_hook_issue()`
def _issue_evidence_mentions_crash(files: list[Path], crashes: list[dict[str, Any]]) -> bool:
	r = False
	for fpath in files[:1]:
		try:
			data = json.loads(fpath.read_text(encoding='utf-8'))
			obj = data.get('issue') if isinstance(data.get('issue'), dict) else data
			title = obj.get('title') or '' if isinstance(obj, dict) else ''
			body = obj.get('body') or '' if isinstance(obj, dict) else ''
			blob = f'{title}\n{body}' if isinstance(obj, dict) else ''
			r = dfh_text_documents_hook_crash(blob, crashes)
		except (OSError, ValueError):
			r = False
	return r
# @used-by :func:`dfh_load_turn_rows()`
def _slice_turn_rows(all_rows: list[Any], turn: dict[str, Any]) -> list[dict[str, Any]]:
	start_i = turn['start_step'] if isinstance(turn.get('start_step'), int) else 0
	final_i = turn['final_step'] if isinstance(turn.get('final_step'), int) and turn.get('completed') else None
	out: list[dict[str, Any]] = []
	for pos, row in enumerate(all_rows):
		if isinstance(row, dict):
			s_idx = row['step_index'] if isinstance(row.get('step_index'), int) else pos
			if ('USER_INPUT' == row.get('type') and s_idx > start_i) or (None is not final_i and s_idx > final_i):
				break
			if s_idx >= start_i:
				out.append(row)
	return out
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_recover_turn_violation()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_verif_pre_invocation_and_crash_ops()`
# @used-by :mod:`agent_tools.hook_crash_audit`
def dfh_build_violation_recovery_receipt(root_p: Path, key: str, turn: dict[str, Any], reason: str | None, now_fn, *, native: dict[str, Any] | None=None) -> tuple[dict[str, Any], Any]:
	exec5_v = list(turn.get('exec5_violations') or [])
	http_v = list(turn.get('http_fetch_violations') or [])
	hook_v = dfh_detect_hook_crashes(native, turn)
	receipt = {
		'covered_exec5_steps': [it.get('step') for it in exec5_v if None is not it.get('step')],
		'covered_hook_crash_steps': [it.get('step') for it in hook_v if None is not it.get('step')],
		'covered_http_fetch_steps': [it.get('step') for it in http_v if None is not it.get('step')],
		'exec5_violations': exec5_v,
		'hook_crash_violations': hook_v,
		'http_fetch_violations': http_v,
		'reason': (reason or 'Retrospective turn violation acknowledged for journal completion').strip(),
		'recovered_at': now_fn(),
		'turn_key': key,
	}
	return (receipt, lambda value: {'exec5_check': value['exec5_check'], 'http_fetch_check': value['http_fetch_check']})
# @used-by :func:`Df.Harness.lib.blocked_report_ops._run_runner_audits()`
# @used-by :mod:`agent_tools.hook_crash_audit`
def dfh_check_runner_hook_crashes(runner) -> None:
	from Df.Harness.Hook.CrashAuditor import CrashAuditor
	chk = CrashAuditor(runner.root, runner.native, runner.turn, runner.value, runner.response).run()
	runner.value['hook_crash_check'] = chk
	if not chk['verified']:
		runner._fail_gate('hook_crash', chk['detail'])
# @used-by :func:`dfh_build_violation_recovery_receipt()`
# @used-by :meth:`Df.Harness.Hook.CrashAuditor.CrashAuditor.run()`
# @used-by :meth:`test_snapshot_canary_and_hook_crash_audit.SnapshotCanaryAndHookCrashAuditTests.test_hook_crash_audit_blocks_silent_omission_and_accepts_disclosed_issue_or_recovery()`
# @used-by :mod:`agent_tools.hook_crash_audit`
def dfh_detect_hook_crashes(native: dict[str, Any] | None, turn: dict[str, Any] | None) -> list[dict[str, Any]]:
	explicit = (turn or {}).get('hook_crashes')
	if isinstance(explicit, list):
		r = [dict(it) for it in explicit if isinstance(it, dict)]
	else:
		r = []
		for pos, row in enumerate(dfh_load_turn_rows(native, turn)):
			hit = _extract_hook_error(row)
			if None is not hit:
				step_idx = row.get('step_index') if isinstance(row.get('step_index'), int) else pos
				r.append({'error': hit[1], 'hook': hit[0], 'step': step_idx})
	return r
# @used-by :meth:`Df.Harness.Hook.CrashAuditor.CrashAuditor.run()`
# @used-by :mod:`agent_tools.hook_crash_audit`
def dfh_has_recorded_hook_issue(root: Path, turn: dict[str, Any], value: dict[str, Any] | None, crashes: list[dict[str, Any]]) -> bool:
	from agent_tools.issue_lifecycle import evidence_issue_files
	return any((_issue_evidence_mentions_crash(evidence_issue_files(root, slug, f'issue-{num}.json'), crashes) for slug, num in _collect_issue_refs(turn, value)))
# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_detect_suppressed_worktree_errors()`
# @used-by :func:`Df.Harness.lib.hook_verif_ops.dfh_detect_shadow_replay_runs()`
# @used-by :func:`agent_tools.cli_command_grounding._collect_passing_trace_commands()`
# @used-by :func:`agent_tools.doc5_context._earliest_cli_failure_step()`
# @used-by :func:`dfh_detect_hook_crashes()`
# @used-by :mod:`agent_tools.hook_crash_audit`
def dfh_load_turn_rows(native: dict[str, Any] | None, turn: dict[str, Any] | None) -> list[dict[str, Any]]:
	src = Path(str((native or {}).get('source_file') or '')) if (native or {}).get('source_file') else None
	r: list[dict[str, Any]] = []
	if None is not src and src.is_file():
		try:
			all_rows = [json.loads(ln) for ln in src.read_text(encoding='utf-8', errors='replace').splitlines() if ln.strip()]
		except (OSError, ValueError):
			all_rows = []
		r = _slice_turn_rows(all_rows, turn or {})
	return r
# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_evaluate_worktree_removal_audit()`
# @used-by :meth:`Df.Harness.Hook.CrashAuditor.CrashAuditor.run()`
# @used-by :mod:`agent_tools.hook_crash_audit`
def dfh_load_violation_receipt(root: Path, turn_key: str) -> dict[str, Any]:
	r: dict[str, Any] = {}
	if turn_key:
		rf = dfh_project_paths(root, exact_root=True).turns_dir / f'{turn_key}-violation-recovery.json'
		if rf.is_file():
			try:
				parsed = json.loads(rf.read_text(encoding='utf-8'))
				if isinstance(parsed, dict):
					r = parsed
			except (OSError, ValueError):
				r = {}
	return r
# @used-by :func:`_issue_evidence_mentions_crash()`
# @used-by :meth:`Df.Harness.Hook.CrashAuditor.CrashAuditor.run()`
# @used-by :mod:`agent_tools.hook_crash_audit`
def dfh_text_documents_hook_crash(text: str | None, crashes: list[dict[str, Any]]) -> bool:
	raw = str(text or '')
	if not raw.strip():
		r = False
	else:
		low = raw.lower()
		named = any((str(c.get('hook') or '').lower() in low for c in crashes if c.get('hook')))
		r = (named or bool(_HOOK_TOPIC_RE.search(raw))) and bool(_HOOK_FAILURE_WORD_RE.search(raw))
	return r