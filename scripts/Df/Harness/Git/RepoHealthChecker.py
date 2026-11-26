# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Git.VerificationSpecResolver import VerificationSpecResolver
import json
import os
import subprocess
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class RepoHealthChecker:
	# @used-by :func:`agent_tools.polyglot_land.run_repo_health_check()`
	# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__post_merge_checks()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	def __init__(self, code_repo: Path, *, slug: str | None=None, spec: dict[str, Any] | None=None, force: bool=False, run_fn=None) -> None:
		self.__code_repo = code_repo
		self.__slug = slug
		self.__spec = spec
		self.__force = force
		self.__run_fn = run_fn if None is not run_fn else subprocess.run
	# @used-by :meth:`RepoHealthChecker.check()`
	def __interpret_proc(self, proc: subprocess.CompletedProcess, eff: dict[str, Any]) -> dict[str, Any]:
		ok_codes = set(eff.get('health_ok_exit_codes') or (0,))
		skip_codes = set(eff.get('health_skip_exit_codes') or (2,))
		skip_states = {str(s).strip().lower() for s in (eff.get('health_skip_states') or ('unavailable', 'waiting-for-sign-in'))}
		state = self.__parse_state(proc.stdout)
		if proc.returncode in ok_codes:
			r = {'ok': True, 'skipped': False, 'state': state or 'ready', 'exit_code': proc.returncode, 'error': ''}
		elif proc.returncode in skip_codes and state in skip_states:
			r = {'ok': True, 'skipped': True, 'state': state, 'exit_code': proc.returncode, 'error': ''}
		else:
			detail = (proc.stderr or proc.stdout or f'health command exited {proc.returncode}').strip()
			r = {'ok': False, 'skipped': False, 'state': state or 'error', 'exit_code': proc.returncode, 'error': detail[:600]}
		return r
	# @used-by :meth:`RepoHealthChecker.__interpret_proc()`
	@staticmethod
	def __parse_state(stdout: str) -> str:
		r = ''
		text = (stdout or '').strip()
		if text:
			try:
				parsed = json.loads(text)
			except ValueError:
				parsed = None
			if isinstance(parsed, dict):
				r = str(parsed.get('state') or '').strip().lower()
		return r
	# @used-by :func:`agent_tools.polyglot_land.run_repo_health_check()`
	# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__post_merge_checks()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	def check(self) -> dict[str, Any]:
		eff = self.__spec if None is not self.__spec else VerificationSpecResolver(self.__code_repo, slug=self.__slug).resolve()
		if None is eff or (not eff.get('health_command')):
			r: dict[str, Any] = {'ok': True, 'skipped': True, 'state': 'none', 'error': ''}
		elif (not self.__force) and '1' == str(os.environ.get('HARNESS_TEST_NO_FSYNC') or '').strip() and '1' != str(os.environ.get('HARNESS_RUN_LIVE_HEALTH') or '').strip():
			r = {'ok': True, 'skipped': True, 'state': 'test_isolated', 'error': ''}
		else:
			try:
				proc = self.__run_fn(list(eff['health_command']), cwd=str(Path(self.__code_repo).resolve()), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30, check=False, creationflags=_NO_WINDOW)
			except (OSError, subprocess.SubprocessError) as exc:
				r = {'ok': False, 'skipped': False, 'state': 'error', 'exit_code': -1, 'error': str(exc)}
			else:
				r = self.__interpret_proc(proc, eff)
		return r
