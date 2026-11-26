# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Git.VerificationSpecResolver import VerificationSpecResolver
from agent_tools.path_registry import project_paths
import hashlib
import json
import os
import shutil
import subprocess
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_STRUCTURAL_KEYS = ('errors', 'instance', 'pid', 'runtimePath', 'state', 'version')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class PolyglotTestRunner:
	# @used-by :func:`agent_tools.polyglot_land.run_polyglot_land_tests()`
	# @used-by :meth:`Df.Harness.Git.WorktreeRebaseVerifier.WorktreeRebaseVerifier.__run_tests_suite()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	def __init__(self, main_repo: Path, wt_path: Path, *, spec: dict[str, Any] | None=None, base_ref: str | None=None, run_fn=None) -> None:
		self.__main_repo = main_repo
		self.__wt_path = wt_path
		self.__spec = spec
		self.__base_ref = base_ref
		self.__run_fn = run_fn if None is not run_fn else subprocess.run
	# @used-by :meth:`PolyglotTestRunner.run()`
	def __execute_spec(self, eff: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
		sandbox = self.__sandbox_root() / 'test-sandbox' / self.__wt_path.name
		watch = [Path(p) for p in (eff.get('watch_host_files') or ()) if str(p).strip()]
		before = {p.as_posix(): self.__snapshot_one(p) for p in watch}
		cwd = (self.__wt_path / str(eff.get('test_cwd') or '.')).resolve()
		timeout = max(5, int(eff.get('timeout_seconds') or 180))
		rc, timed_out, out = self.__run_proc(list(eff['test_command']), cwd, sandbox, timeout)
		after = {p.as_posix(): self.__snapshot_one(p) for p in watch}
		mutated = sorted((k for k in set(before) | set(after) if before.get(k) != after.get(k)))
		ok = 0 == rc and (not timed_out) and (not mutated)
		stage = 'host_mutation' if mutated else (None if ok else 'tests')
		return (ok, {'ok': ok, 'runner': 'polyglot', 'failure_stage': stage, 'timed_out': timed_out, 'mutated_host_files': mutated, 'exit_code': rc, 'output': out})
	# @used-by :meth:`PolyglotTestRunner.__execute_spec()`
	def __run_proc(self, cmd: list[str], cwd: Path, sandbox: Path, timeout: int) -> tuple[int, bool, str]:
		try:
			proc = self.__run_fn(cmd, cwd=str(cwd), env=self.__sandbox_env(sandbox), stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, check=False, creationflags=_NO_WINDOW)
			out = '\n'.join((p for p in (proc.stdout, proc.stderr) if p))[-4000:]
			r = (proc.returncode, False, out)
		except subprocess.TimeoutExpired as exc:
			r = (-1, True, f'Polyglot land tests timed out after {exc.timeout}s')
		finally:
			shutil.rmtree(sandbox, ignore_errors=True)
		return r
	# @used-by :meth:`PolyglotTestRunner.__run_proc()`
	@staticmethod
	def __sandbox_env(sandbox_dir: Path) -> dict[str, str]:
		appdata, localappdata, tools_state = (sandbox_dir / 'appdata', sandbox_dir / 'localappdata', sandbox_dir / 'tools-state')
		for sub in (appdata, localappdata, tools_state):
			sub.mkdir(parents=True, exist_ok=True)
		return {**os.environ, 'APPDATA': str(appdata), 'LOCALAPPDATA': str(localappdata), 'ANTIGRAVITY_TOOLS_STATE_DIR': str(tools_state), 'GIT_OPTIONAL_LOCKS': '0'}
	# @used-by :meth:`PolyglotTestRunner.__execute_spec()`
	def __sandbox_root(self) -> Path:
		r: Path | None = None
		for anc in (self.__main_repo, *self.__main_repo.parents[:4]):
			cand = anc / '\ua616/data'
			if cand.is_dir():
				r = cand
				break
		return r if None is not r else project_paths(self.__main_repo).data_dir
	# @used-by :meth:`PolyglotTestRunner.__execute_spec()`
	@staticmethod
	def __snapshot_one(path: Path) -> dict[str, Any] | None:
		r: dict[str, Any] | None = None
		if path.is_file():
			try:
				parsed = json.loads(path.read_text(encoding='utf-8-sig'))
			except (OSError, ValueError):
				parsed = None
			if isinstance(parsed, dict):
				r = {'kind': 'json', 'fields': {k: parsed.get(k) for k in _STRUCTURAL_KEYS}}
			else:
				try:
					r = {'kind': 'bytes', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
				except OSError:
					r = {'kind': 'unreadable'}
		return r
	# @used-by :func:`agent_tools.polyglot_land.run_polyglot_land_tests()`
	# @used-by :meth:`Df.Harness.Git.WorktreeRebaseVerifier.WorktreeRebaseVerifier.__run_tests_suite()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
	def run(self) -> tuple[bool, dict[str, Any] | None]:
		from agent_tools.tdd.diff_executability import classify_git_range
		if None is not self.__base_ref and (not classify_git_range(self.__wt_path, self.__base_ref, 'HEAD')['is_executable']):
			r: tuple[bool, dict[str, Any] | None] = (True, None)
		else:
			eff = self.__spec if None is not self.__spec else VerificationSpecResolver(self.__main_repo, self.__wt_path).resolve()
			r = (True, None) if None is eff or (not eff.get('test_command')) else self.__execute_spec(eff)
		return r
