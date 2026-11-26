# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.state import df_is_windows
import os
AGENT_ENV_KEYS = ('ANTIGRAVITY_AGENT', 'ANTIGRAVITY_CONVERSATION_ID', 'ANTIGRAVITY_TRAJECTORY_ID', 'ANTIGRAVITY_AGENTAPI_EXE', 'ANTIGRAVITY_SOURCE_METADATA', 'CODEX_HOME', 'CODEX_CLI_PATH', 'CODEX_SANDBOX', 'CODEX_THREAD_ID', 'CODEX_CI', 'CODEX_WINDOWS_REGISTERED_CORE', 'NODE_REPL_NODE_PATH', 'SKY_CUA_NATIVE_PIPE', 'HARNESS_AGENT_GIT', 'UPWORK_AGENT_GIT')
AGENT_PROCESS_NAMES = ('antigravity.exe', 'language_server.exe', 'codex.exe', 'codex-command-runner.exe', 'codex-code-mode-host.exe', 'codex-windows-sandbox-service.exe', 'codex-windows-sandbox-setup.exe', 'node_repl.exe', 'codex-computer-use.exe', 'codex-computer-use-swift.exe')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class AgentContextDetector:
	# @used-by :func:`agent_tools.git_gate.is_agent_git_context()`
	# @used-by :meth:`Df.Harness.Git.HookRunner.HookRunner.run()`
	# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def __init__(self, env: dict[str, str] | None=None, *, ancestor_names: list[str] | tuple[str, ...] | None=None) -> None:
		self.__env = os.environ if None is env else env
		self.__ancestor_names = ancestor_names
	# @used-by :meth:`AgentContextDetector.__ancestor_process_names()`
	@staticmethod
	def __read_win32_table() -> dict[int, tuple[int, str]]:
		import ctypes
		from ctypes import wintypes
		entry_cls = type('_PROCESSENTRY32W', (ctypes.Structure,), {'_fields_': [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD), ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG), ('dwFlags', wintypes.DWORD), ('szExeFile', ctypes.c_wchar * wintypes.MAX_PATH)]})
		kernel32 = ctypes.windll.kernel32
		snap = kernel32.CreateToolhelp32Snapshot(2, 0)
		table: dict[int, tuple[int, str]] = {}
		if None is not snap and snap != wintypes.HANDLE(-1).value:
			try:
				entry = entry_cls()
				entry.dwSize = ctypes.sizeof(entry_cls)
				if kernel32.Process32FirstW(snap, ctypes.byref(entry)):
					while True:
						table[int(entry.th32ProcessID)] = (int(entry.th32ParentProcessID), str(entry.szExeFile).lower())
						if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
							break
			finally:
				kernel32.CloseHandle(snap)
		return table
	# @used-by :meth:`AgentContextDetector.detect()`
	def __ancestor_process_names(self, pid: int | None=None) -> list[str]:
		r: list[str] = []
		if df_is_windows():
			table = self.__read_win32_table()
			curr = os.getpid() if None is pid else int(pid)
			visited: set[int] = set()
			while curr and curr not in visited and curr in table:
				visited.add(curr)
				ppid, name = table[curr]
				r.append(name)
				curr = ppid
		return r
	# @used-by :func:`agent_tools.git_gate.is_agent_git_context()`
	# @used-by :meth:`Df.Harness.Git.HookRunner.HookRunner.run()`
	# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def detect(self) -> bool:
		has_env = any((isinstance(val, str) and bool(val.strip()) and val.strip().lower() not in ('0', 'false', 'no') for key in AGENT_ENV_KEYS for val in (self.__env.get(key),)))
		if has_env:
			r = True
		else:
			ancestors = [str(n).lower() for n in self.__ancestor_names] if None is not self.__ancestor_names else self.__ancestor_process_names()
			r = any((name in {p.lower() for p in AGENT_PROCESS_NAMES} for name in ancestors))
		return r
