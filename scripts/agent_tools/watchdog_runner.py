# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce watchdog timeout and stdin isolation for unittest and pytest in failfast_gate":
# https://github.com/dmitry-ai/harness/issues/205
from __future__ import annotations
from pathlib import Path
import os
import signal
import subprocess
import sys
import time
DEFAULT_WATCHDOG_TIMEOUT = 300.0
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
def _kill_watchdog_tree(proc: subprocess.Popen) -> None:
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
			proc.wait(timeout=5)
		except (OSError, subprocess.TimeoutExpired):
			pass
def _poll_until_exit(proc: subprocess.Popen, deadline: float) -> tuple[bool, int]:
	timed_out = False
	while None is proc.poll():
		if time.monotonic() >= deadline:
			timed_out = True
			_kill_watchdog_tree(proc)
			break
		time.sleep(0.05)
	try:
		rc = proc.wait(timeout=5)
	except (OSError, subprocess.TimeoutExpired):
		rc = 124 if timed_out else -1
	return (timed_out, 124 if timed_out else int(rc))
def run_test_watchdog(argv: list[str] | tuple[str, ...], *, timeout: float=DEFAULT_WATCHDOG_TIMEOUT, cwd: Path | str | None=None, env: dict[str, str] | None=None) -> dict:
	cmd = [str(tok) for tok in argv if None is not tok]
	if cmd and '--' == cmd[0]:
		cmd = cmd[1:]
	if not cmd:
		raise ValueError('test-watchdog requires a command to execute')
	eff_timeout = max(0.1, float(timeout))
	started = time.monotonic()
	kwargs: dict = {'stdin': subprocess.DEVNULL, 'cwd': str(Path(cwd).resolve()) if None is not cwd else None, 'env': env}
	if 'nt' == os.name:
		kwargs['creationflags'] = _NO_WINDOW
	else:
		kwargs['start_new_session'] = True
	proc = subprocess.Popen(cmd, **kwargs)
	timed_out, rc = _poll_until_exit(proc, started + eff_timeout)
	elapsed = round(time.monotonic() - started, 3)
	if timed_out:
		sys.stderr.write(f'TIMEOUT: test command exceeded --timeout={eff_timeout:g}s ({elapsed:.3f}s); process tree terminated.\n')
		sys.stderr.flush()
	return {'ok': (not timed_out) and (0 == rc), 'timed_out': timed_out, 'exit_code': rc, 'timeout': eff_timeout, 'elapsed': elapsed, 'command': cmd}
def run_watchdog_cli(args) -> dict:
	return run_test_watchdog(list(args.cmd or ()), timeout=args.timeout, cwd=args.cwd)
