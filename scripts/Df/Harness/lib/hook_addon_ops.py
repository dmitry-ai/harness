# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Core.lib.fs import df_path_posix
from Df.Core.lib.state import df_is_windows
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.hook_crash_ops import dfh_load_turn_rows, dfh_load_violation_receipt
from Df.Harness.lib.path_resolve import dfh_load_registry
from Df.Harness.lib.runtime_cache import dfh_cached_addon_roots
from Df.Harness.lib.runtime_validate import dfh_expand_path
from Df.Qa.lib.validation.check_strict import df_is_int_strict
import ctypes
import json
import os
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_ADDONS_SLUG = 'dmitry-ai/antigravity-addons'
_DISCLOSE_WT_RE = re.compile(r'(?i)(?:worktree|permission\s+denied|failed\s+to\s+delete|блокировк\w*|не\s+удалось\s+удалить)')
_PYTEST_NOISE_RE = re.compile(r'(?i)(?:^|\n)\s*(?:Ran\s+\d+\s+tests?|={3,}\s*(?:test session|FAILURES|ERRORS)|\bFAILED\s+\S+::)')
_STILL_ACTIVE = 259
_WT_ERR_RE = re.compile(r"(?:error:\s+failed\s+to\s+delete\s+'[^']*(?:worktrees|ꘖ/data/worktrees)[^']*':\s*Permission\s+denied|fatal:[^\r\n]*worktree[^\r\n]*remove[^\r\n]*(?:denied|failed))", re.IGNORECASE)
_WT_PATH_RE = re.compile(r'(?:^|/)(?:\ua616/data/worktrees|\.git/worktrees)/', re.IGNORECASE)
# @used-by :func:`_runtime_issues_from_data()`
# @used-by :func:`dfh_is_live_runtime_data_file()`
# @used-by :func:`dfh_touches_antigravity_addons()`
def _norm_posix(value: str | Path) -> str:
	return df_path_posix(value or '').casefold()
# @used-by :func:`dfh_inspect_companion_runtime_health()`
def _runtime_issues_from_data(data: dict[str, Any], pid_alive_fn) -> tuple[list[str], str, int | None, str]:
	issues: list[str] = []
	state = str(data.get('state') or '').strip()
	pid = data.get('pid') if df_is_int_strict(data.get('pid')) else None
	rt_path = str(data.get('runtimePath') or '').strip()
	errors = data.get('errors') if isinstance(data.get('errors'), dict) else {}
	if 'error' == state.lower() or errors:
		keys = ', '.join(sorted((str(k) for k in errors))[:4]) or state
		issues.append(f'companion state is error ({keys})')
	if rt_path and _WT_PATH_RE.search(_norm_posix(rt_path)):
		issues.append(f'companion runtimePath points inside linked worktree ({rt_path})')
	if 'stopped' != state.lower() and None is not pid and (not pid_alive_fn(pid)):
		state_lbl = state or 'unknown'
		issues.append(f'companion PID {pid} is dead while state is {state_lbl}')
	return (issues, state, pid, rt_path)
# @used-by :func:`dfh_is_pid_alive()`
def _win_pid_alive(pid: int) -> bool:
	r = False
	handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
	if handle:
		try:
			code = ctypes.c_ulong()
			r = bool(ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) and _STILL_ACTIVE == int(code.value)
		finally:
			ctypes.windll.kernel32.CloseHandle(handle)
	return r
# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_readiness()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
# @used-by :mod:`agent_tools.addon_observability`
def dfh_check_close_companion_health(repo: str, code_repo: Path | None=None) -> str | None:
	r: str | None = None
	if _ADDONS_SLUG == str(repo or '').strip().lower():
		health = dfh_inspect_companion_runtime_health()
		if not health['healthy']:
			detail = '; '.join(health['issues'])
			hpath = health['path']
			r = f'EXEC-5 / DOC-5 companion health check failed for {repo} ({hpath}): {detail}'
	if None is r and None is not code_repo:
		from agent_tools.polyglot_land import run_repo_health_check
		repo_health = run_repo_health_check(code_repo, slug=repo)
		if not repo_health['ok']:
			err = repo_health['error']
			r = f'EXEC-5 / DOC-5 repo health check failed for {repo}: {err}'
	return r
# @used-by :func:`Df.Harness.lib.blocked_report_ops._run_runner_audits()`
# @used-by :mod:`agent_tools.addon_observability`
def dfh_check_runner_addon_observability(runner) -> None:
	from Df.Harness.Hook.AddonObserver import AddonObserver
	chk = AddonObserver(runner.root, runner.native, runner.turn, runner.value, runner.response).run()
	runner.value['addon_observability_check'] = chk
	if not chk['verified']:
		runner._fail_gate('addon_observability', chk['detail'])
# @used-by :func:`dfh_inspect_companion_runtime_health()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
# @used-by :mod:`agent_tools.addon_observability`
def dfh_default_companion_runtime_path() -> Path | None:
	env_path = str(os.environ.get('HARNESS_COMPANION_RUNTIME_JSON') or '').strip()
	if env_path:
		r: Path | None = Path(env_path)
	elif '1' == str(os.environ.get('HARNESS_TEST_NO_FSYNC') or '').strip():
		r = None
	else:
		appdata = str(os.environ.get('APPDATA') or '').strip()
		r = (Path(appdata) / 'AntigravityTools/runtime.json') if appdata else None
	return r
# @used-by :func:`dfh_evaluate_worktree_removal_audit()`
# @used-by :mod:`agent_tools.addon_observability`
def dfh_detect_suppressed_worktree_errors(native: dict[str, Any] | None, turn: dict[str, Any] | None) -> list[dict[str, Any]]:
	r: list[dict[str, Any]] = []
	for pos, row in enumerate(dfh_load_turn_rows(native, turn)):
		content = str(row.get('content') or '')
		if content and (not _PYTEST_NOISE_RE.search(content)):
			m = _WT_ERR_RE.search(content)
			if None is not m:
				step_idx = row['step_index'] if isinstance(row.get('step_index'), int) else pos
				r.append({'error': m.group(0).strip(), 'step': step_idx})
	return r
# @used-by :meth:`Df.Harness.Hook.AddonObserver.AddonObserver.run()`
# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_suppressed_worktree_removal_error_audit()`
# @used-by :mod:`agent_tools.addon_observability`
def dfh_evaluate_worktree_removal_audit(root: Path, native: dict[str, Any] | None, turn: dict[str, Any] | None, value: dict[str, Any] | None, response: str | None) -> dict[str, Any]:
	errors = dfh_detect_suppressed_worktree_errors(native, turn)
	if not errors:
		r: dict[str, Any] = {'detail': '', 'errors': [], 'verified': True}
	else:
		key = str((value or {}).get('key') or '')
		covered = set(dfh_load_violation_receipt(Path(root), key).get('covered_worktree_error_steps') or ())
		resp_txt = str(response or '')
		if all((e.get('step') in covered for e in errors)):
			r = {'detail': '', 'errors': errors, 'resolution': 'recovered_via_receipt', 'verified': True}
		elif bool(resp_txt.strip()) and bool(_DISCLOSE_WT_RE.search(resp_txt)) and ('permission denied' in resp_txt.lower() or 'worktree' in resp_txt.lower()):
			r = {'detail': '', 'errors': errors, 'resolution': 'disclosed_in_response', 'verified': True}
		else:
			summary = '; '.join((f"step {e['step']}: {e['error']}" for e in errors[:3]))
			r = {'detail': f'EXEC-5 / DOC-5 worktree_removal_audit: unhandled worktree removal failure(s) occurred during the active turn ({summary}). Diagnose the locking process or explicitly disclose the error in the response.', 'errors': errors, 'verified': False}
	return r
# @used-by :func:`Df.Harness.lib.hook_pre_invocation_ops.dfh_format_turn_begin_message()`
# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_pre_invocation_surfaces_companion_warning()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
# @used-by :mod:`agent_tools.addon_observability`
def dfh_format_pre_invocation_companion_warning(runtime_json: str | Path | None=None, *, pid_alive_fn=None) -> str:
	health = dfh_inspect_companion_runtime_health(runtime_json, pid_alive_fn=pid_alive_fn)
	detail = '; '.join(health['issues'])
	return '' if health['healthy'] else f', companion_warning={detail}'
# @used-by :func:`dfh_check_close_companion_health()`
# @used-by :func:`dfh_format_pre_invocation_companion_warning()`
# @used-by :meth:`Df.Harness.Hook.AddonObserver.AddonObserver.run()`
# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_companion_runtime_health_detects_error_dead_pid_and_worktree_path()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
# @used-by :mod:`agent_tools.addon_observability`
def dfh_inspect_companion_runtime_health(runtime_json: str | Path | None=None, *, pid_alive_fn=None) -> dict[str, Any]:
	target = Path(runtime_json) if None is not runtime_json else dfh_default_companion_runtime_path()
	if None is target or (not target.is_file()):
		r: dict[str, Any] = {'healthy': True, 'issues': [], 'path': str(target or ''), 'pid': None, 'runtime_path': '', 'state': 'absent'}
	else:
		try:
			data = json.loads(target.read_text(encoding='utf-8-sig'))
		except (OSError, ValueError) as exc:
			r = {'healthy': False, 'issues': [f'unreadable runtime.json: {exc}'], 'path': str(target), 'pid': None, 'runtime_path': '', 'state': 'unreadable'}
		else:
			if not isinstance(data, dict):
				r = {'healthy': False, 'issues': ['runtime.json is not a JSON object'], 'path': str(target), 'pid': None, 'runtime_path': '', 'state': 'invalid'}
			else:
				alive_fn = pid_alive_fn if None is not pid_alive_fn else dfh_is_pid_alive
				issues, state, pid, rt_path = _runtime_issues_from_data(data, alive_fn)
				r = {'healthy': not issues, 'issues': issues, 'path': str(target), 'pid': pid, 'runtime_path': rt_path, 'state': state}
	return r
# @used-by :func:`agent_tools.issues.service_helpers._parse_dirty_porcelain()`
# @used-by :func:`agent_tools.polyglot_land.dirty_blocking_main_files()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
# @used-by :mod:`agent_tools.addon_observability`
def dfh_is_live_runtime_data_file(code_repo: Path, rel_posix: str) -> bool:
	from agent_tools.issues.workspace import IssueEvidenceWorkspace
	rel_low = _norm_posix(rel_posix).lstrip('./')
	slug = (IssueEvidenceWorkspace.origin_repo_slug(code_repo) or '').strip().lower()
	r = False
	if slug and rel_low:
		raw_map = dfh_load_registry().raw.get('repo_runtime_data_files') or {}
		if isinstance(raw_map, dict):
			allowed = {_norm_posix(p).lstrip('./') for k, vals in raw_map.items() if str(k).strip().lower() == slug and isinstance(vals, list) for p in vals if isinstance(p, str)}
			r = rel_low in allowed
	return r
# @used-by :func:`dfh_inspect_companion_runtime_health()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
# @used-by :mod:`agent_tools.addon_observability`
def dfh_is_pid_alive(pid: int) -> bool:
	if 0 >= int(pid):
		r = False
	elif df_is_windows():
		r = _win_pid_alive(int(pid))
	else:
		try:
			os.kill(int(pid), 0)
			r = True
		except OSError:
			r = False
	return r
# @used-by :meth:`Df.Harness.Hook.AddonObserver.AddonObserver.run()`
# @used-by :mod:`agent_tools.addon_observability`
def dfh_touches_antigravity_addons(turn: dict[str, Any] | None) -> bool:
	touched = [str(p) for p in ((turn or {}).get('touched_files') or ()) if p]
	r = False
	if touched:
		try:
			cfg = SettingsLoader().run()
		except Exception:
			cfg = {}
		roots = [_norm_posix(p).rstrip('/') + '/' for p in dfh_cached_addon_roots(cfg, None, dfh_expand_path)]
		r = any((any((_norm_posix(tf).startswith(rt) for rt in roots)) or '/antigravity/addons/' in _norm_posix(tf) for tf in touched))
	return r