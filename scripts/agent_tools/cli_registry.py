# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Callable
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Cli.RegistryExecutor import RegistryExecutor
from Df.Harness.lib.cli_registry_defs import REGISTRY as _REGISTRY, dfh_add_registered_parsers as add_registered_parsers, dfh_ensure_builtin_plugins as _ensure_builtin_plugins, dfh_register_command as register_command, dfh_registered_commands as registered_commands, dfh_render_cli_index as render_cli_index
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :func:`test_arch_review_cli._run_arch_cli()`
def dispatch_registered(args, dump_fn: Callable, exit_fn: Callable) -> tuple[bool, int | None]:
	return RegistryExecutor(args, mode='dispatch', dump_fn=dump_fn, exit_fn=exit_fn).run()
# @used-by :meth:`test_cli_registry.CliRegistryTests.test_dynamic_command_registration_roundtrip()`
# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_schema_help_command_returns_contract_for_all_topics()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_cli_parser_dispatches_tdd_exempt_mechanical_with_turn_key()`
def execute_registered(args) -> tuple[bool, dict | None, int | None]:
	return RegistryExecutor(args, mode='execute').run()