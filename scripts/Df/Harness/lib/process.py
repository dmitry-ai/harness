# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from ctypes import wintypes
from Df.Core.lib.state import df_is_windows
import ctypes
import os
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by :func:`dfh_pid_is_alive()`
def _alive_nt(pid: int) -> bool:
	kernel32 = ctypes.windll.kernel32
	handle = kernel32.OpenProcess(0x1000, False, pid)
	if not handle:
		r = 5 == kernel32.GetLastError()
	else:
		code = wintypes.DWORD()
		ok = bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code)))
		kernel32.CloseHandle(handle)
		r = ok and 259 == code.value
	return r
# @used-by :func:`agent_tools.landing_lease._pid_is_alive()`
# @used-by :meth:`Df.Harness.Git.LandingLease.LandingLease.__is_alive()`
# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
def dfh_pid_is_alive(pid: int) -> bool:
	target = int(pid)
	if 0 >= target:
		r = False
	elif df_is_windows():
		r = _alive_nt(target)
	else:
		try:
			os.kill(target, 0)
			r = True
		except PermissionError:
			r = True
		except OSError:
			r = False
	return r
