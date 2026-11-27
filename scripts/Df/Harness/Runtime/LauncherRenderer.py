# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.runtime_launcher_templates import GIT_HOOK_LAUNCHER_HEADER, GIT_MAIN, HOOK_DISCOVERY, HOOK_MAIN, HOOK_RUNNER_HEADER, RUNNER_COMMON
from Df.Harness.lib.storage import dfh_data_dir_for
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class LauncherRenderer:
	# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_runner()`
	# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_deploy_git_hooks()`
	# @used-by :func:`agent_tools.runtime_launchers.git_hook_launcher_source()`
	# @used-by :func:`agent_tools.runtime_launchers.harness_hook_runner_source()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_runtime_and_shadow_subsystem_classes()`
	def __init__(self, primary: str | Path, *, store_dir: str | Path | None=None, kind: str='hook_runner') -> None:
		self.__primary = Path(primary).resolve()
		self.__store_dir = store_dir
		self.__kind = kind
	# @used-by :meth:`LauncherRenderer.run()`
	def __resolve_store(self) -> Path:
		return Path(self.__store_dir).resolve() if None is not self.__store_dir else dfh_data_dir_for(self.__primary) / 'runtime-snapshots'
	# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_runner()`
	# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_deploy_git_hooks()`
	# @used-by :func:`agent_tools.runtime_launchers.git_hook_launcher_source()`
	# @used-by :func:`agent_tools.runtime_launchers.harness_hook_runner_source()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_runtime_and_shadow_subsystem_classes()`
	def run(self) -> str:
		fb_lit = json.dumps(self.__primary.as_posix(), ensure_ascii=True)
		st_lit = json.dumps(self.__resolve_store().as_posix(), ensure_ascii=True)
		consts = f'FALLBACK_PRIMARY = {fb_lit}\nRUNTIME_STORE = {st_lit}\n'
		if 'git_hook' == self.__kind:
			r = GIT_HOOK_LAUNCHER_HEADER + RUNNER_COMMON + consts + GIT_MAIN
		else:
			r = HOOK_RUNNER_HEADER + RUNNER_COMMON + consts + HOOK_DISCOVERY + HOOK_MAIN
		return r
