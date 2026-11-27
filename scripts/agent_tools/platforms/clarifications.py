# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Replace duplicated Harness logic with Df helpers": https://github.com/dmitry-ai/harness/issues/337
from Df.Core.lib.array.first import df_last
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Platform.ClarificationExtractor import ClarificationExtractor
from Df.Harness.lib.clarifications_ops import _extract_question_texts, _parse_answers, _parse_output_envelope, _record_ask_call, dfh_build_segment_metadata, dfh_find_generic_output, dfh_merge_segment_metadata as merge_segment_metadata
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_first_last_starts_with_and_is_windows_delegation_to_df()`
def _find_generic_output(segment: list[dict], pos: int, call_idx: int) -> dict | None:
	return dfh_find_generic_output(segment, pos, call_idx, last_fn=df_last)
# @used-by unused
def build_segment_metadata(segment: list[dict], seg_models: list[str] | tuple[str, ...], config_fn) -> dict[str, Any]:
	return dfh_build_segment_metadata(segment, seg_models, config_fn)
# @used-by :meth:`test_ask_question_clarifications_m8.AskQuestionClarificationsM8Tests.test_extract_ask_question_clarifications_from_steps_669_670()`
def extract_ask_question_clarifications(segment: list[dict]) -> list[dict[str, Any]]:
	return ClarificationExtractor(segment, last_fn=df_last).run()
