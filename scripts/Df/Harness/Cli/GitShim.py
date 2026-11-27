# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_resolve import dfh_tool_list, dfh_tool_path
from agent_tools.git_gate import READ_SUBCOMMANDS, classify_git_argv, cleanup_stale_credential_locks, is_agent_git_context, normalize_host_path, run_git_hook, verify_git_write_invocation
import os
import shutil
import subprocess
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_NET_SUBCOMMANDS = ('push', 'fetch', 'pull', 'clone', 'ls-remote', 'submodule')
class GitShim:
	# @used-by :func:`git_shim.main()`
	# @used-by :func:`git_shim.prepare_git_invocation()`
	# @used-by :func:`git_shim.resolve_system_git()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_cli_subsystem_classes()`
	def __init__(self, argv: list[str] | None=None, *, mode: str='prepare', shim_mode: str | None=None, cwd: Path | None=None, script_dir: Path | None=None) -> None:
		self.__argv = list(sys.argv[1:] if None is argv else argv)
		self.__mode = mode
		self.__shim_mode = shim_mode
		self.__cwd = cwd
		self.__script_dir = script_dir
	# @used-by :meth:`GitShim.__prepare()`
	def __normalize_arg_token(self, token: str) -> str:
		prefixes = tuple(dfh_tool_list('posix_drive_prefixes'))
		return str(normalize_host_path(token)).replace('\\', '/') if token.startswith(prefixes) and 3 <= len(token.split('/')) else token
	# @used-by :meth:`GitShim.__run_main()`
	# @used-by :meth:`GitShim.run()`
	def __prepare(self) -> tuple[list[str], dict[str, str]]:
		mode = (self.__shim_mode or os.environ.get('GIT_SHIM_MODE') or os.environ.get('UPWORK_GIT_SHIM_MODE') or 'inject').strip().lower()
		effective = [self.__normalize_arg_token(tok) for tok in self.__argv]
		subcommand, has_flag = classify_git_argv(effective)
		if subcommand in READ_SUBCOMMANDS and (not has_flag):
			if 'reject' == mode:
				raise ValueError(f'EXEC-5 violation: git {subcommand} requires --no-optional-locks')
			effective = ['--no-optional-locks', *effective]
		elif subcommand in ('commit', 'push', 'filter-branch', 'merge', 'rebase', 'cherry-pick'):
			verify_git_write_invocation(effective, cwd=self.__cwd)
		if subcommand in _NET_SUBCOMMANDS and (not any((tok.lower().startswith('credentialstore.locktimeoutms=') for tok in effective))):
			effective = ['-c', 'credentialstore.locktimeoutms=5000', *effective]
		return (effective, {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
	# @used-by :meth:`GitShim.__resolve_system_git()`
	def __resolve_git_from_path(self) -> str | None:
		shim_dir = dfh_tool_path('git_shim_dir').resolve()
		script_dir = (self.__script_dir or Path(__file__).resolve().parents[3]).resolve()
		filtered: list[str] = []
		for entry in os.environ.get('PATH', '').split(os.pathsep):
			if entry.strip():
				try:
					if normalize_host_path(entry).resolve() not in (shim_dir, script_dir):
						filtered.append(entry)
				except OSError:
					continue
		found = shutil.which('git', path=os.pathsep.join(filtered))
		if found:
			r: str | None = found
		else:
			r = next((str(Path(raw_cand)) for raw_cand in dfh_tool_list('git_candidates') if Path(raw_cand).is_file()), None)
		return r
	# @used-by :meth:`GitShim.__run_main()`
	# @used-by :meth:`GitShim.run()`
	def __resolve_system_git(self) -> str:
		explicit = os.environ.get('UPWORK_REAL_GIT')
		r = str(normalize_host_path(explicit).resolve()) if explicit and normalize_host_path(explicit).is_file() else self.__resolve_git_from_path()
		if None is r:
			raise FileNotFoundError('System git executable not found outside .agents shim directory')
		return r
	# @used-by :meth:`GitShim.run()`
	def __run_main(self) -> int:
		if 2 <= len(self.__argv) and '--hook' == self.__argv[0]:
			r = run_git_hook(self.__argv[1], self.__argv[2:])
		else:
			cleanup_stale_credential_locks()
			try:
				effective, env = self.__prepare()
				binary = self.__resolve_system_git()
			except (ValueError, FileNotFoundError) as exc:
				print(f'ERROR: {exc}', file=sys.stderr)
				r = 2
			else:
				try:
					flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if is_agent_git_context() else 0
					r = subprocess.run([binary, *effective], env=env, creationflags=flags).returncode
				finally:
					cleanup_stale_credential_locks()
		return r
	# @used-by :func:`git_shim.main()`
	# @used-by :func:`git_shim.prepare_git_invocation()`
	# @used-by :func:`git_shim.resolve_system_git()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_cli_subsystem_classes()`
	def run(self) -> Any:
		if 'main' == self.__mode:
			r: Any = self.__run_main()
		elif 'resolve_git' == self.__mode:
			r = self.__resolve_system_git()
		else:
			r = self.__prepare()
		return r