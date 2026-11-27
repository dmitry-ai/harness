# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_resolve import dfh_var_value
from Df.Harness.lib.path_state import CODE_ANCHOR, DEFAULT_REGISTRY_FILE, dfh_default_runtime_file
from Df.Harness.lib.runtime_cache import dfh_load_cached_settings
from Df.Harness.lib.runtime_validate import dfh_validate_runtime
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class SettingsLoader:
	# @used-by :func:`Df.Harness.lib.ag_daemon.dfh_default_folders_json()`
	# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_antigravity_paths()`
	# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_native_invocation()`
	# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_proof_paths()`
	# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_record_cleanup_answer_log()`
	# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_resolve_cleanup_log_root()`
	# @used-by :func:`Df.Harness.lib.cli_operation_defs.dfh_add_operation_parsers()`
	# @used-by :func:`Df.Harness.lib.codex_control.dfh_shared_control()`
	# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_paths()`
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_instruction_snapshot()`
	# @used-by :func:`Df.Harness.lib.completion_core._scan_native_for_platform()`
	# @used-by :func:`Df.Harness.lib.config_codex.dfh_global_codex_instructions()`
	# @used-by :func:`Df.Harness.lib.config_codex.dfh_primary_settings()`
	# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_touches_antigravity_addons()`
	# @used-by :func:`Df.Harness.lib.hook_stop_ops._resolve_ag_from_settings()`
	# @used-by :func:`Df.Harness.lib.native_links.dfh_configuration()`
	# @used-by :func:`Df.Harness.lib.path_discovery._runtime_ag_projects_dirs()`
	# @used-by :func:`Df.Harness.lib.runtime_context._default_settings()`
	# @used-by :func:`Df.Harness.lib.runtime_conversations.dfh_safe_load_cfg()`
	# @used-by :func:`Df.Harness.lib.runtime_instances._load_cfg()`
	# @used-by :func:`agent_tools.runtime.settings()`
	# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__init__()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__register_multi()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__resolve_day()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.run()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ToolTraceReader.ToolTraceReader.__resolve_paths()`
	# @used-by :meth:`Df.Harness.Platform.Codex.ProofVerifier.ProofVerifier.run()`
	# @used-by :meth:`Df.Harness.Platform.Codex.ToolTraceReader.ToolTraceReader.run()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_runtime_and_shadow_subsystem_classes()`
	def __init__(self, path: str | Path | None=None, *, default_file_fn: Any=None, primary: Path | None=None, code_anchor: Path | None=None, registry_file: Path | None=None) -> None:
		self.__path = path
		self.__default_file_fn = default_file_fn
		self.__primary = primary
		self.__code_anchor = code_anchor
		self.__registry_file = registry_file
	# @used-by :meth:`SettingsLoader.run()`
	def __resolve_file(self) -> Path:
		if None is not self.__path:
			r = Path(self.__path)
		else:
			prim = self.__primary if None is not self.__primary else Path(dfh_var_value('HARNESS_CODE')).resolve()
			fn = self.__default_file_fn or dfh_default_runtime_file
			r = fn(prim, self.__code_anchor or CODE_ANCHOR, self.__registry_file or DEFAULT_REGISTRY_FILE)
		return r
	# @used-by :func:`Df.Harness.lib.ag_daemon.dfh_default_folders_json()`
	# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_antigravity_paths()`
	# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_native_invocation()`
	# @used-by :func:`Df.Harness.lib.ag_metadata.dfh_proof_paths()`
	# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_record_cleanup_answer_log()`
	# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_resolve_cleanup_log_root()`
	# @used-by :func:`Df.Harness.lib.cli_operation_defs.dfh_add_operation_parsers()`
	# @used-by :func:`Df.Harness.lib.codex_control.dfh_shared_control()`
	# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_paths()`
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_instruction_snapshot()`
	# @used-by :func:`Df.Harness.lib.completion_core._scan_native_for_platform()`
	# @used-by :func:`Df.Harness.lib.config_codex.dfh_global_codex_instructions()`
	# @used-by :func:`Df.Harness.lib.config_codex.dfh_primary_settings()`
	# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_touches_antigravity_addons()`
	# @used-by :func:`Df.Harness.lib.hook_stop_ops._resolve_ag_from_settings()`
	# @used-by :func:`Df.Harness.lib.native_links.dfh_configuration()`
	# @used-by :func:`Df.Harness.lib.path_discovery._runtime_ag_projects_dirs()`
	# @used-by :func:`Df.Harness.lib.runtime_context._default_settings()`
	# @used-by :func:`Df.Harness.lib.runtime_conversations.dfh_safe_load_cfg()`
	# @used-by :func:`Df.Harness.lib.runtime_instances._load_cfg()`
	# @used-by :func:`agent_tools.runtime.settings()`
	# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__init__()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__register_multi()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__resolve_day()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.run()`
	# @used-by :meth:`Df.Harness.Platform.Antigravity.ToolTraceReader.ToolTraceReader.__resolve_paths()`
	# @used-by :meth:`Df.Harness.Platform.Codex.ProofVerifier.ProofVerifier.run()`
	# @used-by :meth:`Df.Harness.Platform.Codex.ToolTraceReader.ToolTraceReader.run()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_runtime_and_shadow_subsystem_classes()`
	def run(self) -> dict:
		return dfh_load_cached_settings(self.__resolve_file(), dfh_validate_runtime)
