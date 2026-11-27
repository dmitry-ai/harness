# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.Grounding.CliOutputJsonParser import CliOutputJsonParser
# 2026-11-26 "Fix top-level JSON parsing and workspace repo scoping in doc5_context.py": https://github.com/dmitry-ai/harness/issues/368
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
# @used-by :meth:`test_cli_output_json.CliOutputJsonAndDoc5Tests.test_top_level_json_parser_ignores_nested_valid_false_and_catches_top_level_failures()`
# @used-by :meth:`test_df_harness_s11_final_338.DfHarnessS11Final338Tests.test_cli_output_json_parser_and_facade_cover_all_branches()`
# @used-by :mod:`agent_tools.cli_output_json`
def extract_top_level_json_objects(text: str) -> tuple[list[dict[str, Any]], bool]:
	return CliOutputJsonParser.extract_objects(text)
# @used-by :func:`Df.Harness.lib.hook_verif_ops.dfh_classify_shadow_output()`
# @used-by :meth:`Df.Harness.Grounding.CliCommandAuditor.CliCommandAuditor.is_passing_output()`
# @used-by :meth:`Df.Harness.Grounding.Doc5RequirementChecker.Doc5RequirementChecker.is_failed_cli_output()`
# @used-by :meth:`test_cli_output_json.CliOutputJsonAndDoc5Tests.test_top_level_json_parser_ignores_nested_valid_false_and_catches_top_level_failures()`
# @used-by :meth:`test_df_harness_s11_final_338.DfHarnessS11Final338Tests.test_cli_output_json_parser_and_facade_cover_all_branches()`
# @used-by :mod:`agent_tools.cli_output_json`
def top_level_json_has_failure(text: str) -> bool:
	return CliOutputJsonParser(text).has_failure()
__all__ = ['extract_top_level_json_objects', 'top_level_json_has_failure']
