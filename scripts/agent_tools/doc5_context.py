# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from __future__ import annotations
from typing import Any
from Df.Harness.Grounding.Doc5ContextDetector import Doc5ContextDetector
from Df.Harness.Grounding.Doc5RequirementChecker import Doc5RequirementChecker
from Df.Harness.lib.trace import dfh_cmd_from_call, dfh_row_outputs
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _cmd_from_call(call: dict[str, Any]) -> str:
	return dfh_cmd_from_call(call)
# @used-by :meth:`test_turn_begin_status_and_auditors.TurnBeginStatusAndAuditorsTests.test_all_trace_auditors_ignore_nested_foreign_reconciliation_and_flag_top_level_failure()`
def _is_failed_cli_output(text: str) -> bool:
	return Doc5RequirementChecker.is_failed_cli_output(text)
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_harness_callers_delegate_to_df_harness_helpers()`
def _row_outputs(rows: list[dict[str, Any]], pos: int) -> list[str]:
	return dfh_row_outputs(rows, pos)
# @used-by :mod:`agent_tools.doc5_context`
def detect_df_analysis_mode(text: str, blocks: list[dict], requests: list | tuple, mode: str, *, turn_context: dict | None, prob_head_re, req_cmd_fn, explicit_fn) -> str:
	return Doc5ContextDetector(text, blocks, requests, mode, turn_context=turn_context, prob_head_re=prob_head_re, req_cmd_fn=req_cmd_fn, explicit_fn=explicit_fn).detect()
# @used-by :func:`agent_tools.doc5_replay_audit._audit_one_fixture()`
# @used-by :func:`agent_tools.doc5_replay_audit.audit_local_saved_turns()`
# @used-by :meth:`test_cli_output_json.CliOutputJsonAndDoc5Tests.test_excluded_fetchers_and_readonly_linters_do_not_trigger_doc5()`
# @used-by :meth:`test_cli_output_json.CliOutputJsonAndDoc5Tests.test_local_repo_scoping_ignores_external_upstream_issues_and_preserves_fallback()`
# @used-by :mod:`agent_tools.doc5_context`
def turn_requires_doc5_problem_analysis(turn_context: dict | None) -> bool:
	return Doc5RequirementChecker(turn_context).is_required()
setattr(turn_requires_doc5_problem_analysis, '_df_default_doc5_facade', True)
__all__ = ['detect_df_analysis_mode', 'turn_requires_doc5_problem_analysis']