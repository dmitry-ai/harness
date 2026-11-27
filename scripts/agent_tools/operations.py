# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Cli.DomainExecutor import DomainExecutor
from Df.Harness.lib.cli_domain_ops import _load_consumed as _load_consumed_json, dfh_analysis_root as analysis_root, dfh_execute_collect as _execute_collect
from Df.Harness.lib.cli_input import dfh_consume_scratch_input as _consumed, dfh_load_operation_input as _operation_input, dfh_read_input_bytes as _read_input
from Df.Harness.lib.cli_operation_defs import COMMANDS, COMMAND_HELP as _COMMAND_HELP, COMPLETION_COMMANDS, CONSUME_COMMANDS as _CONSUME_COMMANDS, PROJECT_SPECS as _PROJECT_SPECS, dfh_add_operation_parsers
from . import completion as _completion_mod
from . import runtime as _runtime_mod
# @used-by :func:`agent_tools.upwork_project.main()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_dom_cli_dispatch_keeps_the_explicit_authorized_session()`
def add_parsers(sub):
	return dfh_add_operation_parsers(sub, add_completion_fn=_completion_mod.add_parser_arguments, settings_fn=_runtime_mod.settings)
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_analysis_workflow.NativeReviewTests.test_html_links_json_summary_non_destructive_collect_and_scratch_cleanliness()`
# @used-by :meth:`test_cli_registry.CliRegistryTests.test_operation_handlers_cover_all_non_completion_commands()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_collect_receipt_preserves_plan_after_input_is_consumed()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_invalid_consumption_scope_fails_before_analysis_changes()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_stdin_analysis_and_owned_scratch_inputs_leave_no_permanent_candidate()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_dom_cli_dispatch_keeps_the_explicit_authorized_session()`
def execute(args):
	return DomainExecutor(args, completion_execute_fn=_completion_mod.execute).run()