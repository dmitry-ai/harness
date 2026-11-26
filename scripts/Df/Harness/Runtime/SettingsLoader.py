# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class SettingsLoader:
	# @used-by :func:`agent_tools.runtime.settings()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_runtime_and_shadow_subsystem_classes()`
	def __init__(self, path: str | Path | None=None) -> None:
		self.__path = path
	# @used-by :meth:`SettingsLoader.run()`
	def __resolve_file(self) -> Path:
		from agent_tools import runtime
		if None is not self.__path:
			r = Path(self.__path)
		else:
			r = runtime.default_runtime_file(runtime.PRIMARY, runtime._CODE_ANCHOR, runtime.DEFAULT_REGISTRY_FILE)
		return r
	# @used-by :func:`agent_tools.runtime.settings()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_runtime_and_shadow_subsystem_classes()`
	def run(self) -> dict:
		from agent_tools import runtime
		from agent_tools.runtime_cache import load_cached_settings
		return load_cached_settings(self.__resolve_file(), runtime._validate_runtime)
