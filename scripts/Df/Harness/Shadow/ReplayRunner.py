# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Shadow.CommandExecutor import CommandExecutor
from Df.Harness.Shadow.ReplayPipeline import ReplayPipeline
from Df.Harness.Shadow.WorkspaceCloner import WorkspaceCloner
from Df.Harness.lib.path_resolve import dfh_project_paths
from Df.Harness.lib.runtime_resolve import dfh_resolve_antigravity_paths
from Df.Harness.lib.shadow_clone import dfh_cleanup_shadow_root, dfh_remap_shadow_state, dfh_shadow_isolation_context
from Df.Harness.lib.shadow_command import dfh_persist_shadow_replay_receipt, dfh_resolve_shadow_launcher, dfh_stage_command_shadow_copies
import uuid
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
NOT_RUN_STAGES = ('live_llm_generation', 'live_upwork_browser_capture', 'live_antigravity_rpc_title_sync')
class ReplayRunner:
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_shadow_replay()`
	# @used-by :func:`agent_tools.shadow_replay.run_shadow_replay()`
	def __init__(self, project: str | Path, conversation_id: str | None=None, *, launcher: str | Path | None=None, workspace: str | Path | None=None, platform: str='antigravity', backend: str | Path | None=None, response_file: str | Path | None=None, keep: bool=False, exec_rename_domain: str | None=None, command: str | None=None, legacy_ctx: Any=None) -> None:
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
		self.__legacy_ctx = legacy_ctx
	# @used-by :meth:`ReplayRunner.run()`
	def __build_report(self, src_launcher: Path | None, shadow_root: Path, cleaned: bool, verified: list[str], checks: dict, errors: list[str]) -> dict:
		report = {'checks': checks, 'cleaned_up': cleaned, 'conversation_id': self.__cid, 'errors': errors, 'launcher': str(src_launcher) if None is not src_launcher else None, 'platform': self.__platform, 'project': str(self.__src_project), 'shadow_dir': str(shadow_root), 'stages_not_run': list(NOT_RUN_STAGES), 'stages_verified': verified, 'valid': not errors}
		report['receipt_file'] = dfh_persist_shadow_replay_receipt(self.__ws_root, self.__src_project, report, exec_rename_domain=self.__exec_rename_domain, command=self.__command)
		return report
	# @used-by :meth:`ReplayRunner.run()`
	def __prepare_stage(self, src_launcher: Path | None, shadow_root: Path, command_mode: bool) -> tuple[Path, Path | None, dict[Path, Path], dict[str, Path], Path | None]:
		if command_mode:
			r = dfh_stage_command_shadow_copies(self.__src_project, src_launcher, shadow_root)
		else:
			from Df.Harness.lib.journal_core import dfh_resolve_journal_dir, dfh_state_dir
			sp = shadow_root / 'project'
			WorkspaceCloner(self.__src_project, sp, hardlink_evidence=True).run()
			states = {'project': dfh_state_dir(dfh_resolve_journal_dir(self.__src_project))}
			relocs = {self.__src_project: sp}
			sl = None
			if None is not src_launcher:
				sl = shadow_root / 'launcher'
				WorkspaceCloner(src_launcher, sl, hardlink_evidence=False).run()
				states['launcher'] = dfh_state_dir(dfh_resolve_journal_dir(src_launcher))
				relocs[src_launcher] = sl
			r = (sp, sl, relocs, states, None)
		return r
	# @used-by :meth:`ReplayRunner.run()`
	def __remap_copies(self, shadow_project: Path, src_launcher: Path | None, shadow_launcher: Path | None, old_states: dict[str, Path]) -> None:
		dfh_remap_shadow_state(self.__src_project, shadow_project, old_state=old_states['project'])
		if None is not src_launcher and None is not shadow_launcher:
			dfh_remap_shadow_state(src_launcher, shadow_launcher, extra_pairs=((self.__src_project, shadow_project),), old_state=old_states['launcher'])
	# @used-by :meth:`ReplayRunner.__run_shadow_mode()`
	def __resolve_native_paths(self) -> tuple[Path, Path | None]:
		b_arg = Path(self.__backend).resolve() if None is not self.__backend else None
		resolved = dfh_resolve_antigravity_paths(backend=b_arg, conversation_id=self.__cid)
		backend_dir = Path(resolved['backend_dir']).resolve()
		logs_dir = Path(resolved['brain_dir']).resolve() / self.__cid / '.system_generated/logs'
		full_t, comp_t = (logs_dir / 'transcript_full.jsonl', logs_dir / 'transcript.jsonl')
		return (backend_dir, full_t if full_t.is_file() else (comp_t if comp_t.is_file() else None))
	# @used-by :meth:`ReplayRunner.run()`
	def __run_shadow_mode(self, shadow_project: Path, shadow_launcher: Path | None, shadow_daily: Path | None, shadow_root: Path, checks: dict, verified: list[str], errors: list[str]) -> None:
		if self.__exec_rename_domain or self.__command:
			CommandExecutor(self.__src_project, shadow_project, shadow_launcher, shadow_daily, shadow_root, exec_rename_domain=self.__exec_rename_domain, command=self.__command, checks=checks, verified=verified, errors=errors).run()
		elif not self.__cid:
			raise ValueError('shadow-replay requires --conversation, --exec-rename-domain, or --command')
		else:
			backend_dir, native_tx = self.__resolve_native_paths()
			resp_p = Path(self.__response_file).resolve() if None is not self.__response_file else None
			ReplayPipeline(shadow_project, shadow_launcher, shadow_root, self.__cid, self.__platform, backend_dir, native_tx, resp_p, checks, verified, errors).run()
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_shadow_replay()`
	# @used-by :func:`agent_tools.shadow_replay.run_shadow_replay()`
	def run(self) -> dict:
		command_mode = bool(self.__exec_rename_domain or self.__command)
		src_launcher = dfh_resolve_shadow_launcher(self.__src_project, self.__launcher) if command_mode else (Path(self.__launcher).resolve() if None is not self.__launcher else None)
		shadow_root = dfh_project_paths(self.__ws_root, exact_root=True).scratch_dir / 'shadow-replay' / f'run-{uuid.uuid4().hex[:12]}'
		checks, verified, errors = ({}, [], [])
		try:
			shadow_project, shadow_launcher, relocations, old_states, shadow_daily = self.__prepare_stage(src_launcher, shadow_root, command_mode)
			with dfh_shadow_isolation_context(relocations, legacy_ctx=self.__legacy_ctx):
				self.__remap_copies(shadow_project, src_launcher, shadow_launcher, old_states)
				self.__run_shadow_mode(shadow_project, shadow_launcher, shadow_daily, shadow_root, checks, verified, errors)
		finally:
			cleaned = (not shadow_root.exists()) if self.__keep else dfh_cleanup_shadow_root(shadow_root)
		return self.__build_report(src_launcher, shadow_root, cleaned, verified, checks, errors)
