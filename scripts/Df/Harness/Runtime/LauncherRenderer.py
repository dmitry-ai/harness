# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class LauncherRenderer:
	# @used-by :func:`agent_tools.runtime_launchers.git_hook_launcher_source()`
	# @used-by :func:`agent_tools.runtime_launchers.harness_hook_runner_source()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_runtime_and_shadow_subsystem_classes()`
	def __init__(self, primary: str | Path, *, store_dir: str | Path | None=None, kind: str='hook_runner') -> None:
		self.__primary = Path(primary).resolve()
		self.__store_dir = store_dir
		self.__kind = kind
	# @used-by :meth:`LauncherRenderer.run()`
	def __resolve_store(self) -> Path:
		from agent_tools.storage import data_dir_for
		return Path(self.__store_dir).resolve() if None is not self.__store_dir else data_dir_for(self.__primary) / 'runtime-snapshots'
	# @used-by :func:`agent_tools.runtime_launchers.git_hook_launcher_source()`
	# @used-by :func:`agent_tools.runtime_launchers.harness_hook_runner_source()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_runtime_and_shadow_subsystem_classes()`
	def run(self) -> str:
		from agent_tools import runtime_launchers as rl
		fb_lit = json.dumps(self.__primary.as_posix(), ensure_ascii=True)
		st_lit = json.dumps(self.__resolve_store().as_posix(), ensure_ascii=True)
		consts = f'FALLBACK_PRIMARY = {fb_lit}\nRUNTIME_STORE = {st_lit}\n'
		if 'git_hook' == self.__kind:
			r = rl.GIT_HOOK_LAUNCHER_HEADER + rl._RUNNER_COMMON + consts + rl._GIT_MAIN
		else:
			r = rl.HOOK_RUNNER_HEADER + rl._RUNNER_COMMON + consts + rl._HOOK_DISCOVERY + rl._HOOK_MAIN
		return r
