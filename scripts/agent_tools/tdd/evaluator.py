# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/169
from __future__ import annotations
from pathlib import Path
from ..shell_audit import _split_shell_segments, normalize_host_path
from .classifier import _norm_posix, resolve_code_scope
from .commands import classify_test_command
def _apply_command_event(ev: dict, step: int, scopes: dict[str, dict], failfast_warnings: list[str]) -> None:
	outcome = ev.get('outcome') or {}
	if ev.get('is_git_commit') and outcome.get('exit_code') in (0, None):
		_apply_commit_reset(ev.get('commit_scope'), scopes)
	else:
		t_info = ev.get('test_info') or {}
		if t_info.get('is_test_cmd') and (not t_info.get('rigged_failure')):
			if t_info.get('is_full_suite'):
				_collect_failfast_warnings(str(ev.get('cmd') or ''), step, failfast_warnings)
			for sk, st in scopes.items():
				if _command_matches_scope(ev, sk, set(st['written_tests'])):
					_update_scope_from_test_cmd(sk, st, ev, step, outcome, t_info)
def _apply_commit_reset(c_scope: str | None, scopes: dict[str, dict]) -> None:
	c_key = Path(c_scope).resolve().as_posix().lower() if None is not c_scope else None
	for sk, st in scopes.items():
		if None is c_key or Path(sk).resolve().as_posix().lower() == c_key:
			st['state'] = 'IDLE'
			st['written_test_step'] = None
			st['red_step'] = None
			st['red_cmd'] = None
			st['cycle_had_prod_edit'] = False
			st['cycle_green_step'] = None
def _apply_file_write_event(ev: dict, step: int, scopes: dict[str, dict], violations: list[str]) -> None:
	cls = ev.get('classification')
	scope_str = str(ev.get('scope') or '')
	fpath = str(ev.get('path') or '')
	if 'non_code' != cls and scope_str:
		st = _ensure_scope(scopes, scope_str)
		if 'test' == cls:
			_apply_test_write(st, fpath, step)
		elif 'production' == cls:
			_apply_prod_write(st, fpath, step, violations)
def _apply_prod_write(st: dict, fpath: str, step: int, violations: list[str]) -> None:
	st['any_prod_edit'] = True
	if fpath not in st['touched_prod_files']:
		st['touched_prod_files'].append(fpath)
	if st['state'] in ('RED_VERIFIED', 'GREEN_IMPLEMENTING'):
		st['state'] = 'GREEN_IMPLEMENTING'
	elif 'TEST_WRITTEN' == st['state']:
		violations.append(f'EXEC-2 TDD-RED-GATE: Production code "{fpath}" edited at step {step} after writing test(s), but no failing (RED) test run was observed after the test edit. Run the new test and observe it fail before writing production code.')
	else:
		violations.append(f'EXEC-2 TDD-RED-GATE: Production code "{fpath}" edited at step {step} without first writing a test and observing it fail (RED).')
	st['cycle_had_prod_edit'] = True
	st['last_prod_edit_step'] = step
	st['last_code_edit_step'] = step
def _apply_test_write(st: dict, fpath: str, step: int) -> None:
	if fpath not in st['written_tests']:
		st['written_tests'].append(fpath)
	if st['state'] in ('IDLE', 'TEST_WRITTEN'):
		st['state'] = 'TEST_WRITTEN'
		st['written_test_step'] = step
	st['last_code_edit_step'] = step
def _collect_failfast_warnings(cmd_text: str, step: int, failfast_warnings: list[str]) -> None:
	from ..failfast_gate import missing_failfast_flag
	for seg in _split_shell_segments(cmd_text):
		miss = missing_failfast_flag(seg.strip())
		if None is not miss:
			warn = f'EXEC-2 fail-fast advisory: Full-suite command at step {step} ({miss[0]}) omitted "{miss[1]}"; prefer fail-fast or harness.py run-tests.'
			if warn not in failfast_warnings:
				failfast_warnings.append(warn)
			break
def _collect_final_green_violations(scopes: dict[str, dict]) -> list[str]:
	r: list[str] = []
	for sk, st in sorted(scopes.items()):
		if st['any_prod_edit']:
			last_edit = st['last_code_edit_step']
			full_green = st['last_full_green_step']
			if None is full_green or (None is not last_edit and full_green <= last_edit):
				r.append(f'EXEC-2 TDD-FULL-GATE: Repository "{sk}" has production code edits (last edit at step {last_edit}) without a subsequent passing (GREEN) full test suite run. Run the full test suite and verify all tests pass.')
	return r
def _command_matches_scope(event: dict, scope_str: str, written_test_files: set[str]) -> bool:
	scope_p = Path(scope_str).resolve()
	scope_key = scope_p.as_posix().lower()
	scope_main_key = _git_main_repo_root(scope_p).as_posix().lower()
	cmd_norm = _norm_posix(str(event.get('cmd') or '')).lower()
	t_info = event.get('test_info') or {}
	is_full_cmd = bool(t_info.get('is_full_suite'))
	cwd_raw = event.get('cwd')
	cwd_p = Path(cwd_raw).resolve() if cwd_raw else None
	resolved_scopes = _resolve_event_target_scopes(t_info.get('target_paths') or [], cwd_p)
	r = (
		_scopes_overlap(resolved_scopes, scope_p, scope_key, scope_main_key, is_full_cmd)
		or any(Path(tf).name.lower() in cmd_norm or Path(tf).stem.lower() in cmd_norm for tf in written_test_files)
		or scope_key in cmd_norm
		or ((not resolved_scopes) and _cwd_matches_scope(cwd_p, scope_p, scope_key, scope_main_key, is_full_cmd))
	)
	return r
def _cwd_matches_scope(cwd_p: Path | None, scope_p: Path, scope_key: str, scope_main_key: str, is_full_cmd: bool) -> bool:
	r = False
	if None is not cwd_p:
		cwd_scope = resolve_code_scope(cwd_p)
		direct = cwd_scope.as_posix().lower() == scope_key or cwd_p.is_relative_to(scope_p) or scope_p.is_relative_to(cwd_p)
		r = direct or (is_full_cmd and _git_main_repo_root(cwd_scope).as_posix().lower() == scope_main_key)
	return r
def _ensure_scope(scopes: dict[str, dict], scope_str: str) -> dict:
	return scopes.setdefault(scope_str, {
		'any_prod_edit': False,
		'cycle_green_step': None,
		'cycle_had_prod_edit': False,
		'last_code_edit_step': None,
		'last_full_green_step': None,
		'last_prod_edit_step': None,
		'red_cmd': None,
		'red_step': None,
		'state': 'IDLE',
		'touched_prod_files': [],
		'written_test_step': None,
		'written_tests': [],
	})
def _git_main_repo_root(repo: Path) -> Path:
	r = repo.resolve()
	dot_git = r / '.git'
	if dot_git.is_file():
		try:
			txt = dot_git.read_text(encoding='utf-8', errors='replace').strip()
			if txt.lower().startswith('gitdir:'):
				gitdir = normalize_host_path(txt.split(':', 1)[1].strip())
				if not gitdir.is_absolute():
					gitdir = (r / gitdir).resolve()
				if 'worktrees' == gitdir.parent.name and '.git' == gitdir.parent.parent.name:
					r = gitdir.parent.parent.parent.resolve()
		except OSError:
			pass
	return r
def _resolve_event_target_scopes(targets: list[str], cwd_p: Path | None) -> list[Path]:
	r: list[Path] = []
	for tp in targets:
		try:
			cand = normalize_host_path(tp)
			full = cand.resolve() if cand.is_absolute() else ((cwd_p / cand).resolve() if cwd_p else cand.resolve())
			r.append(resolve_code_scope(full))
		except OSError:
			continue
	return r
def _scopes_overlap(resolved_scopes: list[Path], scope_p: Path, scope_key: str, scope_main_key: str, is_full_cmd: bool) -> bool:
	direct = any(rs.as_posix().lower() == scope_key or rs.is_relative_to(scope_p) or scope_p.is_relative_to(rs) for rs in resolved_scopes)
	return direct or (is_full_cmd and any(_git_main_repo_root(rs).as_posix().lower() == scope_main_key for rs in resolved_scopes))
def _update_scope_from_test_cmd(sk: str, st: dict, ev: dict, step: int, outcome: dict, t_info: dict) -> None:
	scope_full = bool(t_info.get('is_full_suite')) or classify_test_command(str(ev.get('cmd') or ''), scope_root=Path(sk))['is_full_suite']
	if outcome.get('is_failure') and 'TEST_WRITTEN' == st['state'] and None is not st['written_test_step'] and step > st['written_test_step']:
		st['state'] = 'RED_VERIFIED'
		st['red_step'] = step
		st['red_cmd'] = ev.get('cmd')
	elif outcome.get('is_pass') and None is not st['last_code_edit_step'] and step > st['last_code_edit_step']:
		st['cycle_green_step'] = step
		if scope_full:
			st['last_full_green_step'] = step
def evaluate_tdd_events(events: list[dict], *, require_final_full_green: bool=True) -> dict:
	scopes: dict[str, dict] = {}
	violations: list[str] = []
	failfast_warnings: list[str] = []
	for ev in events or ():
		kind = ev.get('kind')
		step = int(ev.get('step', 0))
		if 'file_write' == kind:
			_apply_file_write_event(ev, step, scopes, violations)
		elif 'command' == kind:
			_apply_command_event(ev, step, scopes, failfast_warnings)
	if require_final_full_green:
		violations.extend(_collect_final_green_violations(scopes))
	r = {'scopes': scopes, 'verified': not violations, 'violations': violations}
	if failfast_warnings:
		r['failfast_warnings'] = failfast_warnings
	return r
