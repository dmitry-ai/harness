# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.shadow_clone import dfh_path_pairs
from Df.Harness.lib.shadow_command import dfh_run_exec_rename_domain, dfh_run_generic_command
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class CommandExecutor:
	# @used-by :func:`agent_tools.shadow_replay_command.execute_shadow_command()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.__run_shadow_mode()`
	def __init__(self, src_project: Path, shadow_project: Path, shadow_launcher: Path | None, shadow_daily: Path | None, shadow_root: Path, *, exec_rename_domain: str | None, command: str | None, checks: dict, verified: list[str], errors: list[str]) -> None:
		self.__src_project = src_project
		self.__shadow_project = shadow_project
		self.__shadow_launcher = shadow_launcher
		self.__shadow_daily = shadow_daily
		self.__shadow_root = shadow_root
		self.__exec_rename_domain = exec_rename_domain
		self.__command = command
		self.__checks = checks
		self.__verified = verified
		self.__errors = errors
	# @used-by :func:`agent_tools.shadow_replay_command.execute_shadow_command()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.__run_shadow_mode()`
	def run(self) -> Path:
		pairs = dfh_path_pairs(((self.__src_project, self.__shadow_project),))
		if self.__exec_rename_domain:
			r = dfh_run_exec_rename_domain(self.__shadow_project, self.__shadow_launcher, self.__shadow_daily, self.__shadow_root, self.__exec_rename_domain, pairs, self.__checks, self.__verified, self.__errors)
		else:
			r = dfh_run_generic_command(self.__shadow_project, self.__shadow_launcher, self.__shadow_root, str(self.__command or ''), self.__checks, self.__verified, self.__errors)
		return r
