# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
_MANAGED_WT_RE = re.compile(r'(?i)(?:\ua616[\\/]data[\\/]worktrees|\.git[\\/]worktrees)(?:[\\/][^\s"\';)}]+)?')
_RAW_WT_REMOVE_RE = re.compile(r'(?i)(?:^|[\s({])["\']?(?:[^"\'\s]*[/\\])?git(?:\.exe)?["\']?(?:\s+(?:--[A-Za-z0-9-]+(?:=\S+)?|-[Cc]\s+(?:"[^"]*"|\'[^\']*\'|\S+)|-[A-Za-z]))*\s+worktree\s+remove\b')
_SEG_SPLIT_RE = re.compile(r'(?:\r?\n|&&|\|\||;)')
_SHELL_DELETE_RE = re.compile(r'(?i)(?:\b(?:remove-item|rmdir|shutil\.rmtree|rmtree)\b|(?:^|[\s({])(?:rm|rd|del|ri|erase)(?:\.exe)?\s+(?:-[A-Za-z]|/[A-Za-z]|["\']|\$|\S))')
_VAR_WT_RE = re.compile(r'(?i)\$(\w+)\s*=\s*[^;\r\n]*(?:\ua616[\\/]data[\\/]worktrees|\.git[\\/]worktrees)')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class WorktreeCommandGuard:
	# @used-by :func:`agent_tools.worktree_guard.prohibited_worktree_remove_commands()`
	# @used-by :func:`agent_tools.worktree_guard.prohibited_worktree_shell_deletions()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	def __init__(self, command_line: str) -> None:
		self.__cmd = str(command_line or '')
	# @used-by :meth:`WorktreeCommandGuard.check()`
	def __has_managed_delete(self) -> bool:
		r = False
		if _MANAGED_WT_RE.search(self.__cmd) and _SHELL_DELETE_RE.search(self.__cmd):
			bound_vars = [f'${v.casefold()}' for v in _VAR_WT_RE.findall(self.__cmd)]
			for seg in _SEG_SPLIT_RE.split(self.__cmd):
				if _SHELL_DELETE_RE.search(seg):
					seg_low = seg.casefold()
					if _MANAGED_WT_RE.search(seg) or any((tok in seg_low for tok in bound_vars)):
						r = True
						break
		return r
	# @used-by :func:`agent_tools.worktree_guard.prohibited_worktree_remove_commands()`
	# @used-by :func:`agent_tools.worktree_guard.prohibited_worktree_shell_deletions()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_flow_guard_and_land()`
	def check(self, *, mode: str='remove') -> list[str]:
		r: list[str] = []
		if 'delete' == mode:
			if self.__has_managed_delete():
				r.append('EXEC-5: Direct shell/Python deletion of managed worktrees under `\ua616/data/worktrees/` is prohibited; use `harness.py worktree-cleanup` so locked worktrees are diagnosed rather than silently suppressed.')
		else:
			for seg in _SEG_SPLIT_RE.split(self.__cmd):
				if _RAW_WT_REMOVE_RE.search(seg) and 'harness.py' not in seg.casefold():
					r.append('EXEC-5: Direct `git worktree remove` is prohibited; use `harness.py worktree-land` or `harness.py worktree-cleanup` so locked worktrees fail closed with lock-holder diagnostics.')
					break
		return r
