# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Cli.Dispatcher import Dispatcher, _LINK_SPECS
# @used-by :func:`test_project_rename._assert_renamed_journal_and_state()`
# @used-by :meth:`test_agent_tools.ContextTests.test_generate_context_cli_supports_positional_root_and_default_config()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_declarative_arg_specs_and_routers_parse_expected_flags()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :mod:`generate_context`
# @used-by :mod:`safe_commit`
# @used-by :mod:`snapshot_draft`
# @used-by :mod:`validate_anchors`
# @used-by :mod:`validate_links`
# @used-by :mod:`validate_statements`
# @used-by :mod:`validate_step`
def main(command: str, argv=None, *, context_default: Path | None=None, root_default: Path | None=None) -> int:
	return Dispatcher(command, argv, context_default=context_default, root_default=root_default).run()