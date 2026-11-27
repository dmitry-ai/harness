# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Meta.TranscriptReader import TranscriptReader
from Df.Harness.lib.trace import dfh_read_ag_rows
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _ag_transcript_file(ag_paths: dict[str, Any] | None, conversation_id: str) -> Path | None:
	return TranscriptReader.ag_transcript_file(ag_paths, conversation_id)
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_transcripts_submodule_parses_antigravity_codex_and_turn_state()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _extract_ag_transcript_info(transcript_path: str | Path | None, *, start_step: int | None=None, end_step: int | None=None, final_step: int | None=None) -> dict[str, Any]:
	return TranscriptReader(transcript_path, fallback_read_fn=dfh_read_ag_rows).extract_ag_info(start_step=start_step, end_step=end_step, final_step=final_step)
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_transcripts_submodule_parses_antigravity_codex_and_turn_state()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _extract_codex_transcript_info(rollout_path: str | Path | None, *, turn_id: str | None=None, start_step: int | None=None, final_step: int | None=None) -> dict[str, Any]:
	return TranscriptReader.extract_codex_info(rollout_path, turn_id=turn_id, start_step=start_step, final_step=final_step)
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_transcripts_submodule_parses_antigravity_codex_and_turn_state()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _extract_turn_steps_from_state(state: dict[str, Any]) -> list[int]:
	return TranscriptReader.extract_turn_steps_from_state(state)
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_transcripts_submodule_parses_antigravity_codex_and_turn_state()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _find_turn_state_for_conversation(turns_dir: Path, conversation_id: str) -> tuple[Path, dict[str, Any]] | None:
	return TranscriptReader.find_turn_state_for_conversation(turns_dir, conversation_id)
# @used-by :func:`agent_tools.issues.turn_scope._fallback_env_session()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_transcripts_submodule_parses_antigravity_codex_and_turn_state()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _parse_antigravity_source_metadata(env: dict[str, str]) -> tuple[str | None, int | None]:
	return TranscriptReader.parse_antigravity_source_metadata(env)
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_hook_and_transcript_callers_delegate_to_df_harness()`
def _read_ag_rows(tp: Path) -> list[Any]:
	return TranscriptReader.read_ag_rows(tp, fallback_fn=dfh_read_ag_rows)
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _read_ag_summary_row(ag_paths: dict[str, Any] | None, conversation_id: str) -> dict[str, Any] | None:
	return TranscriptReader.read_ag_summary_row(ag_paths, conversation_id)
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _resolve_ag_model_and_effort(ag_paths: dict[str, Any] | None, conversation_id: str, *, transcript_path: str | Path | None=None, start_step: int | None=None, end_step: int | None=None) -> tuple[str | None, str | None]:
	return TranscriptReader.resolve_ag_model_and_effort(ag_paths, conversation_id, transcript_path=transcript_path, start_step=start_step, end_step=end_step)
