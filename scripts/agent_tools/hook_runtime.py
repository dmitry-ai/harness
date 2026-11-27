# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Core.lib.array.first import df_last
from Df.Harness.Hook.JsonRunner import JsonRunner
from Df.Harness.lib.hook_runtime_ops import ABBREVIATIONS, ABBR_RE, AUX_TURN_SUFFIXES as _AUX_TURN_SUFFIXES, MULTI_SENT_RE, dfh_iter_turn_state_files as iter_turn_state_files, dfh_read_jsonl_dicts as _read_jsonl_dicts, dfh_read_last_user_segment as read_last_user_segment, dfh_scan_doc4_sentence_issues as scan_doc4_sentence_issues, dfh_slice_after_last_user as _slice_after_last_user
# @used-by :meth:`test_hook_unification.HookUnificationTests.test_run_json_hook_dispatches_and_fails_open()`
# @used-by :mod:`agent_tools.hook_runtime`
def run_json_hook(handler, *, stdin=None, stdout=None) -> dict:
	return JsonRunner(handler, stdin=stdin, stdout=stdout).run()
__all__ = ['ABBREVIATIONS', 'ABBR_RE', 'MULTI_SENT_RE', '_AUX_TURN_SUFFIXES', '_read_jsonl_dicts', '_slice_after_last_user', 'df_last', 'iter_turn_state_files', 'read_last_user_segment', 'run_json_hook', 'scan_doc4_sentence_issues']