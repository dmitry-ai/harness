# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify process-tree termination in parallel_runner and enforce AST subprocess hygiene in pre-commit":
# https://github.com/dmitry-ai/harness/issues/206
from __future__ import annotations
import os
import signal
import subprocess
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
POPEN_TREE_KWARGS: dict = {'creationflags': _NO_WINDOW} if 'nt' == os.name else {'start_new_session': True}
def kill_process_tree(proc: subprocess.Popen, *, wait_timeout: float=5.0) -> None:
	if None is proc.poll():
		if 'nt' == os.name:
			subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=15, creationflags=_NO_WINDOW)
		else:
			try:
				os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
			except OSError:
				pass
		try:
			proc.kill()
		except OSError:
			pass
		try:
			proc.wait(timeout=wait_timeout)
		except (OSError, subprocess.TimeoutExpired):
			pass
