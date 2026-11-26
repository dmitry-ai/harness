# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import uuid
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ReplayRunner:
	# @used-by :func:`agent_tools.shadow_replay.run_shadow_replay()`
	def __init__(self, project: str | Path, conversation_id: str | None=None, *, launcher: str | Path | None=None, workspace: str | Path | None=None, platform: str='antigravity', backend: str | Path | None=None, response_file: str | Path | None=None, keep: bool=False, exec_rename_domain: str | None=None, command: str | None=None) -> None:
		self.__src_project = Path(project).resolve()
		self.__cid = str(conversation_id or '').strip().lower()
		self.__launcher = launcher
		self.__ws_root = Path(workspace).resolve() if None is not workspace else self.__src_project
		self.__platform = platform
		self.__backend = backend
		self.__response_file = response_file
		self.__keep = keep
		self.__exec_rename_domain = exec_rename_domain
		self.__command = command
	# @used-by :meth:`ReplayRunner.run()`
	def __build_report(self, src_launcher: Path | None, shadow_root: Path, cleaned: bool, verified: list[str], checks: dict, errors: list[str]) -> dict:
		from agent_tools import shadow_replay as sr
		report = {'checks': checks, 'cleaned_up': cleaned, 'conversation_id': self.__cid, 'errors': errors, 'launcher': str(src_launcher) if None is not src_launcher else None, 'platform': self.__platform, 'project': str(self.__src_project), 'shadow_dir': str(shadow_root), 'stages_not_run': list(sr.NOT_RUN_STAGES), 'stages_verified': verified, 'valid': not errors}
		report['receipt_file'] = sr.persist_shadow_replay_receipt(self.__ws_root, self.__src_project, report, exec_rename_domain=self.__exec_rename_domain, command=self.__command)
		return report
	# @used-by :func:`agent_tools.shadow_replay.run_shadow_replay()`
	def run(self) -> dict:
		from agent_tools import shadow_replay as sr
		command_mode = bool(self.__exec_rename_domain or self.__command)
		src_launcher = sr.resolve_shadow_launcher(self.__src_project, self.__launcher) if command_mode else (Path(self.__launcher).resolve() if None is not self.__launcher else None)
		shadow_root = sr.project_paths(self.__ws_root, exact_root=True).scratch_dir / 'shadow-replay' / f'run-{uuid.uuid4().hex[:12]}'
		checks, verified, errors = ({}, [], [])
		try:
			shadow_project, shadow_launcher, relocations, old_states, shadow_daily = sr._prepare_shadow_stage(self.__src_project, src_launcher, shadow_root, command_mode)
			with sr.shadow_isolation_context(relocations):
				sr._remap_staged_copies(self.__src_project, shadow_project, src_launcher, shadow_launcher, old_states)
				sr._run_shadow_mode(self.__src_project, shadow_project, shadow_launcher, shadow_daily, shadow_root, cid=self.__cid, platform=self.__platform, backend=self.__backend, response_file=self.__response_file, exec_rename_domain=self.__exec_rename_domain, command=self.__command, checks=checks, verified=verified, errors=errors)
		finally:
			cleaned = (not shadow_root.exists()) if self.__keep else sr.cleanup_shadow_root(shadow_root)
		return self.__build_report(src_launcher, shadow_root, cleaned, verified, checks, errors)
