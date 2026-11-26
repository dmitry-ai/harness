# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Harden addon companion observability and conflict reservation hygiene":
# https://github.com/dmitry-ai/harness/issues/302
from __future__ import annotations
from pathlib import Path
from typing import Any
import ctypes
import json
import os
import re
from .hook_crash_audit import _load_turn_rows, _load_violation_receipt
_ADDONS_SLUG = 'dmitry-ai/antigravity-addons'
_DISCLOSE_WT_RE = re.compile(r'(?i)(?:worktree|permission\s+denied|failed\s+to\s+delete|блокировк\w*|не\s+удалось\s+удалить)')
_PYTEST_NOISE_RE = re.compile(r'(?i)(?:^|\n)\s*(?:Ran\s+\d+\s+tests?|={3,}\s*(?:test session|FAILURES|ERRORS)|\bFAILED\s+\S+::)')
_STILL_ACTIVE = 259
_WT_ERR_RE = re.compile(r"(?:error:\s+failed\s+to\s+delete\s+'[^']*(?:worktrees|ꘖ/data/worktrees)[^']*':\s*Permission\s+denied|fatal:[^\r\n]*worktree[^\r\n]*remove[^\r\n]*(?:denied|failed))", re.IGNORECASE)
_WT_PATH_RE = re.compile(r'(?:^|/)(?:\ua616/data/worktrees|\.git/worktrees)/', re.IGNORECASE)
# @used-by :func:`_is_pid_alive()`
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
# @used-by :func:`inspect_companion_runtime_health()`
def _is_pid_alive(pid: int) -> bool:
	if 0 >= int(pid):
		r = False
	elif 'nt' == os.name:
		r = _win_pid_alive(int(pid))
	else:
		try:
			os.kill(int(pid), 0)
			r = True
		except OSError:
			r = False
	return r
# @used-by :func:`_runtime_issues_from_data()`
# @used-by :func:`_touches_antigravity_addons()`
# @used-by :func:`is_live_runtime_data_file()`
def _norm_posix(value: str | Path) -> str:
	return str(value or '').replace('\\', '/').casefold()
# @used-by :func:`inspect_companion_runtime_health()`
def _runtime_issues_from_data(data: dict[str, Any], pid_alive_fn) -> tuple[list[str], str, int | None, str]:
	issues: list[str] = []
	state = str(data.get('state') or '').strip()
	pid = data.get('pid') if isinstance(data.get('pid'), int) and (not isinstance(data.get('pid'), bool)) else None
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
# @used-by :func:`evaluate_addon_observability()`
def _touches_antigravity_addons(turn: dict[str, Any] | None) -> bool:
	from .runtime import sanctioned_addon_code_roots
	touched = [str(p) for p in ((turn or {}).get('touched_files') or ()) if p]
	r = False
	if touched:
		roots = [_norm_posix(p).rstrip('/') + '/' for p in sanctioned_addon_code_roots()]
		r = any((any((_norm_posix(tf).startswith(rt) for rt in roots)) or '/antigravity/addons/' in _norm_posix(tf) for tf in touched))
	return r
# @used-by :func:`inspect_companion_runtime_health()`
# @used-by :mod:`agent_tools.addon_observability`
def default_companion_runtime_path() -> Path | None:
	env_path = str(os.environ.get('HARNESS_COMPANION_RUNTIME_JSON') or '').strip()
	if env_path:
		r: Path | None = Path(env_path)
	elif '1' == str(os.environ.get('HARNESS_TEST_NO_FSYNC') or '').strip():
		r = None
	else:
		appdata = str(os.environ.get('APPDATA') or '').strip()
		r = (Path(appdata) / 'AntigravityTools/runtime.json') if appdata else None
	return r
# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_readiness()`
# @used-by :mod:`agent_tools.addon_observability`
def check_close_companion_health(repo: str, code_repo: Path | None=None) -> str | None:
	r: str | None = None
	if _ADDONS_SLUG == str(repo or '').strip().lower():
		health = inspect_companion_runtime_health()
		if not health['healthy']:
			detail = '; '.join(health['issues'])
			r = f"EXEC-5 / DOC-5 companion health check failed for {repo} ({health['path']}): {detail}"
	# 2026-11-26 "Add sandboxed polyglot land tests and post-land health checks": https://github.com/dmitry-ai/harness/issues/304
	if None is r and None is not code_repo:
		from .polyglot_land import run_repo_health_check
		repo_health = run_repo_health_check(code_repo, slug=repo)
		if not repo_health['ok']:
			r = f"EXEC-5 / DOC-5 repo health check failed for {repo}: {repo_health['error']}"
	return r
# @used-by :func:`agent_tools.blocked_report._run_runner_audits()`
# @used-by :mod:`agent_tools.addon_observability`
def check_runner_addon_observability(runner) -> None:
	chk = evaluate_addon_observability(runner.root, runner.native, runner.turn, runner.value, runner.response)
	runner.value['addon_observability_check'] = chk
	if not chk['verified']:
		runner._fail_gate('addon_observability', chk['detail'])
# @used-by :func:`evaluate_worktree_removal_audit()`
# @used-by :mod:`agent_tools.addon_observability`
def detect_suppressed_worktree_errors(native: dict[str, Any] | None, turn: dict[str, Any] | None) -> list[dict[str, Any]]:
	r: list[dict[str, Any]] = []
	for pos, row in enumerate(_load_turn_rows(native, turn)):
		content = str(row.get('content') or '')
		if content and (not _PYTEST_NOISE_RE.search(content)):
			m = _WT_ERR_RE.search(content)
			if None is not m:
				step_idx = row['step_index'] if isinstance(row.get('step_index'), int) else pos
				r.append({'error': m.group(0).strip(), 'step': step_idx})
	return r
# @used-by :func:`agent_tools.gates.answer_checks._addon_observability_messages()`
# @used-by :func:`check_runner_addon_observability()`
# @used-by :mod:`agent_tools.addon_observability`
def evaluate_addon_observability(root: Path, native: dict[str, Any] | None, turn: dict[str, Any] | None, value: dict[str, Any] | None, response: str | None) -> dict[str, Any]:
	wt_chk = evaluate_worktree_removal_audit(root, native, turn, value, response)
	issues: list[str] = [] if wt_chk['verified'] else [wt_chk['detail']]
	comp_health: dict[str, Any] | None = None
	explicit_rt = bool(str(os.environ.get('HARNESS_COMPANION_RUNTIME_JSON') or '').strip())
	if _touches_antigravity_addons(turn) or explicit_rt:
		comp_health = inspect_companion_runtime_health()
		if not comp_health['healthy']:
			detail = '; '.join(comp_health['issues'])
			issues.append(f"EXEC-5 / DOC-5 companion runtime fault ({comp_health['path']}): {detail}")
	return {'verified': not issues, 'detail': '; '.join(issues), 'worktree_errors': wt_chk['errors'], 'companion_health': comp_health}
# @used-by :func:`evaluate_addon_observability()`
# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_suppressed_worktree_removal_error_audit()`
# @used-by :mod:`agent_tools.addon_observability`
def evaluate_worktree_removal_audit(root: Path, native: dict[str, Any] | None, turn: dict[str, Any] | None, value: dict[str, Any] | None, response: str | None) -> dict[str, Any]:
	errors = detect_suppressed_worktree_errors(native, turn)
	if not errors:
		r: dict[str, Any] = {'verified': True, 'errors': [], 'detail': ''}
	else:
		key = str((value or {}).get('key') or '')
		covered = set(_load_violation_receipt(Path(root), key).get('covered_worktree_error_steps') or ())
		resp_txt = str(response or '')
		if all((e.get('step') in covered for e in errors)):
			r = {'verified': True, 'errors': errors, 'detail': '', 'resolution': 'recovered_via_receipt'}
		elif bool(resp_txt.strip()) and bool(_DISCLOSE_WT_RE.search(resp_txt)) and ('permission denied' in resp_txt.lower() or 'worktree' in resp_txt.lower()):
			r = {'verified': True, 'errors': errors, 'detail': '', 'resolution': 'disclosed_in_response'}
		else:
			summary = '; '.join((f"step {e['step']}: {e['error']}" for e in errors[:3]))
			r = {'verified': False, 'errors': errors, 'detail': f'EXEC-5 / DOC-5 worktree_removal_audit: unhandled worktree removal failure(s) occurred during the active turn ({summary}). Diagnose the locking process or explicitly disclose the error in the response.'}
	return r
# @used-by :func:`check_pre_invocation._format_turn_begin_message()`
# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_pre_invocation_surfaces_companion_warning()`
# @used-by :mod:`agent_tools.addon_observability`
def format_pre_invocation_companion_warning(runtime_json: str | Path | None=None, *, pid_alive_fn=None) -> str:
	health = inspect_companion_runtime_health(runtime_json, pid_alive_fn=pid_alive_fn)
	detail = '; '.join(health['issues'])
	return '' if health['healthy'] else f', companion_warning={detail}'
# @used-by :func:`check_close_companion_health()`
# @used-by :func:`evaluate_addon_observability()`
# @used-by :func:`format_pre_invocation_companion_warning()`
# @used-by :meth:`test_addon_observability.AddonObservabilityTests.test_companion_runtime_health_detects_error_dead_pid_and_worktree_path()`
# @used-by :mod:`agent_tools.addon_observability`
def inspect_companion_runtime_health(runtime_json: str | Path | None=None, *, pid_alive_fn=None) -> dict[str, Any]:
	target = Path(runtime_json) if None is not runtime_json else default_companion_runtime_path()
	if None is target or (not target.is_file()):
		r: dict[str, Any] = {'healthy': True, 'state': 'absent', 'pid': None, 'runtime_path': '', 'issues': [], 'path': str(target or '')}
	else:
		try:
			data = json.loads(target.read_text(encoding='utf-8-sig'))
		except (OSError, ValueError) as exc:
			r = {'healthy': False, 'state': 'unreadable', 'pid': None, 'runtime_path': '', 'issues': [f'unreadable runtime.json: {exc}'], 'path': str(target)}
		else:
			if not isinstance(data, dict):
				r = {'healthy': False, 'state': 'invalid', 'pid': None, 'runtime_path': '', 'issues': ['runtime.json is not a JSON object'], 'path': str(target)}
			else:
				alive_fn = pid_alive_fn if None is not pid_alive_fn else _is_pid_alive
				issues, state, pid, rt_path = _runtime_issues_from_data(data, alive_fn)
				r = {'healthy': not issues, 'state': state, 'pid': pid, 'runtime_path': rt_path, 'issues': issues, 'path': str(target)}
	return r
# @used-by :func:`agent_tools.issues.service_helpers._parse_dirty_porcelain()`
# @used-by :func:`agent_tools.polyglot_land.dirty_blocking_main_files()`
# @used-by :mod:`agent_tools.addon_observability`
def is_live_runtime_data_file(code_repo: Path, rel_posix: str) -> bool:
	from .issues.workspace import IssueEvidenceWorkspace
	from .path_registry import load_registry
	rel_low = _norm_posix(rel_posix).lstrip('./')
	slug = (IssueEvidenceWorkspace.origin_repo_slug(code_repo) or '').strip().lower()
	r = False
	if slug and rel_low:
		raw_map = load_registry().raw.get('repo_runtime_data_files') or {}
		if isinstance(raw_map, dict):
			allowed = {_norm_posix(p).lstrip('./') for k, vals in raw_map.items() if str(k).strip().lower() == slug and isinstance(vals, list) for p in vals if isinstance(p, str)}
			r = rel_low in allowed
	return r
__all__ = ['check_close_companion_health', 'check_runner_addon_observability', 'default_companion_runtime_path', 'detect_suppressed_worktree_errors', 'evaluate_addon_observability', 'evaluate_worktree_removal_audit', 'format_pre_invocation_companion_warning', 'inspect_companion_runtime_health', 'is_live_runtime_data_file']
