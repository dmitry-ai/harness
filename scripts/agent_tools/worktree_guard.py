# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Block raw worktree removal and fail closed on locked cleanup":
# https://github.com/dmitry-ai/harness/issues/303
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import os
import re
import stat
import subprocess
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.state import df_is_windows
from .git_gate import _NO_WINDOW
_MANAGED_WT_RE = re.compile(r'(?i)(?:\ua616[\\/]data[\\/]worktrees|\.git[\\/]worktrees)(?:[\\/][^\s"\';)}]+)?')
_PS_PROC_QUERY = 'Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress'
_RAW_WT_REMOVE_RE = re.compile(r'(?i)(?:^|[\s({])["\']?(?:[^"\'\s]*[/\\])?git(?:\.exe)?["\']?(?:\s+(?:--[A-Za-z0-9-]+(?:=\S+)?|-[Cc]\s+(?:"[^"]*"|\'[^\']*\'|\S+)|-[A-Za-z]))*\s+worktree\s+remove\b')
_SEG_SPLIT_RE = re.compile(r'(?:\r?\n|&&|\|\||;)')
_SHELL_DELETE_RE = re.compile(r'(?i)(?:\b(?:remove-item|rmdir|shutil\.rmtree|rmtree)\b|(?:^|[\s({])(?:rm|rd|del|ri|erase)(?:\.exe)?\s+(?:-[A-Za-z]|/[A-Za-z]|["\']|\$|\S))')
_VAR_WT_RE = re.compile(r'(?i)\$(\w+)\s*=\s*[^;\r\n]*(?:\ua616[\\/]data[\\/]worktrees|\.git[\\/]worktrees)')
# @used-by :func:`remove_worktree_fail_closed()`
def _format_cleanup_error(git_err: str, holders: list[dict[str, Any]], rem_errors: list[str]) -> str:
	parts: list[str] = []
	if git_err:
		parts.append(git_err)
	if holders:
		desc = ', '.join((f"{h['name']}(PID {h['pid']})" for h in holders[:4]))
		parts.append(f'locking processes: {desc}')
	if rem_errors:
		parts.append('; '.join(rem_errors[:3]))
	return ' | '.join(parts) if parts else 'Worktree directory remained present after cleanup'
# @used-by :func:`prohibited_worktree_shell_deletions()`
def _has_managed_worktree_delete(cmd: str) -> bool:
	r = False
	if _MANAGED_WT_RE.search(cmd) and _SHELL_DELETE_RE.search(cmd):
		bound_vars = [f'${v.casefold()}' for v in _VAR_WT_RE.findall(cmd)]
		for seg in _SEG_SPLIT_RE.split(cmd):
			if _SHELL_DELETE_RE.search(seg):
				seg_low = seg.casefold()
				if _MANAGED_WT_RE.search(seg) or any((tok in seg_low for tok in bound_vars)):
					r = True
					break
	return r
# @used-by :func:`_parse_process_row()`
# @used-by :func:`find_worktree_lock_holders()`
def _norm_posix(value: str | Path) -> str:
	return str(value or '').replace('\\', '/').casefold().rstrip('/')
# @used-by :func:`find_worktree_lock_holders()`
def _parse_process_row(row: dict[str, Any], target_posix: str, target_win: str) -> dict[str, Any] | None:
	r: dict[str, Any] | None = None
	if isinstance(row, dict):
		raw_pid = row.get('ProcessId') if None is not row.get('ProcessId') else row.get('pid')
		cmd = str(row.get('CommandLine') or row.get('command_line') or '').strip()
		if None is not raw_pid and cmd:
			try:
				pid = int(raw_pid)
			except (TypeError, ValueError):
				pid = 0
			if 0 < pid and os.getpid() != pid and (target_posix in _norm_posix(cmd) or target_win in cmd.casefold()):
				name = str(row.get('Name') or row.get('name') or 'unknown').strip()
				r = {'pid': pid, 'name': name, 'command_line': cmd[:300]}
	return r
# @used-by :func:`find_worktree_lock_holders()`
def _query_win32_processes() -> list[dict[str, Any]]:
	r: list[dict[str, Any]] = []
	# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
	if df_is_windows():
		try:
			proc = subprocess.run(['powershell', '-NoProfile', '-Command', _PS_PROC_QUERY], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15, check=False, creationflags=_NO_WINDOW)
		except (OSError, subprocess.SubprocessError):
			proc = None
		if None is not proc and 0 == proc.returncode and proc.stdout.strip():
			try:
				parsed = json.loads(proc.stdout)
			except ValueError:
				parsed = []
			r = [parsed] if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
	return r
# @used-by :func:`remove_worktree_fail_closed()`
def _remove_tree_strict(wt_path: Path) -> list[str]:
	errors: list[str] = []
	for dirpath, dirnames, filenames in os.walk(wt_path, topdown=False):
		base = Path(dirpath)
		for name in filenames:
			_unlink_strict(base / name, False, errors)
		for name in dirnames:
			_unlink_strict(base / name, True, errors)
	if wt_path.exists():
		_unlink_strict(wt_path, True, errors)
	return errors
# @used-by :func:`_remove_tree_strict()`
def _unlink_strict(target: Path, is_dir: bool, errors: list[str]) -> None:
	try:
		target.rmdir() if is_dir else target.unlink()
	except PermissionError:
		try:
			os.chmod(target, stat.S_IWRITE)
			target.rmdir() if is_dir else target.unlink()
		except OSError as exc:
			errors.append(f'{target.as_posix()}: {exc}')
	except OSError as exc:
		errors.append(f'{target.as_posix()}: {exc}')
# @used-by :func:`remove_worktree_fail_closed()`
# @used-by :meth:`test_worktree_cleanup_guard.WorktreeCleanupGuardTests.test_worktree_cleanup_fails_closed_with_lock_holders_on_locked_dir()`
# @used-by :mod:`agent_tools.worktree_guard`
def find_worktree_lock_holders(wt_path: Path, *, process_rows: list[dict[str, Any]] | None=None) -> list[dict[str, Any]]:
	rows = process_rows if None is not process_rows else _query_win32_processes()
	target_posix = _norm_posix(Path(wt_path).resolve())
	target_win = str(Path(wt_path).resolve()).casefold().rstrip('\\')
	found: list[dict[str, Any]] = []
	seen: set[int] = set()
	for row in rows:
		item = _parse_process_row(row, target_posix, target_win)
		if None is not item and item['pid'] not in seen:
			seen.add(item['pid'])
			found.append(item)
	return found
# @used-by :func:`agent_tools.gates.git_write.check()`
# @used-by :mod:`agent_tools.worktree_guard`
def prohibited_worktree_remove_commands(command_line: str) -> list[str]:
	r: list[str] = []
	text = str(command_line or '')
	for seg in _SEG_SPLIT_RE.split(text):
		if _RAW_WT_REMOVE_RE.search(seg) and 'harness.py' not in seg.casefold():
			r.append('EXEC-5: Direct `git worktree remove` is prohibited; use `harness.py worktree-land` or `harness.py worktree-cleanup` so locked worktrees fail closed with lock-holder diagnostics.')
			break
	return r
# @used-by :func:`agent_tools.gates.worktree_isolation.check()`
# @used-by :mod:`agent_tools.worktree_guard`
def prohibited_worktree_shell_deletions(command_line: str) -> list[str]:
	r: list[str] = []
	if _has_managed_worktree_delete(str(command_line or '')):
		r.append('EXEC-5: Direct shell/Python deletion of managed worktrees under `ꘖ/data/worktrees/` is prohibited; use `harness.py worktree-cleanup` so locked worktrees are diagnosed rather than silently suppressed.')
	return r
# @used-by :func:`agent_tools.worktree_flow.worktree_cleanup()`
# @used-by :mod:`agent_tools.worktree_guard`
def remove_worktree_fail_closed(main_repo: Path, wt_path: Path, *, force: bool, git_exec_fn) -> dict[str, Any]:
	git_err = ''
	rem_errors: list[str] = []
	if wt_path.exists():
		if (wt_path / '.git').exists():
			args = ['worktree', 'remove', '--force', str(wt_path)] if force else ['worktree', 'remove', str(wt_path)]
			proc = git_exec_fn(main_repo, *args)
			if 0 != proc.returncode:
				git_err = (proc.stderr or proc.stdout or f'git worktree remove exited {proc.returncode}').strip()
		else:
			holders_pre = find_worktree_lock_holders(wt_path)
			if not holders_pre:
				rem_errors = _remove_tree_strict(wt_path)
	still_exists = wt_path.exists()
	ok = (not still_exists) and (not git_err) and (not rem_errors)
	holders = [] if ok else find_worktree_lock_holders(wt_path)
	err = '' if ok else _format_cleanup_error(git_err, holders, rem_errors)
	return {'ok': ok, 'error': err, 'removal_errors': rem_errors, 'locking_processes': holders}
__all__ = ['find_worktree_lock_holders', 'prohibited_worktree_remove_commands', 'prohibited_worktree_shell_deletions', 'remove_worktree_fail_closed']