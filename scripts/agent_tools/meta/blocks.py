# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any
from Df.Core.lib.array.clean.main import df_clean_null
from Df.Harness.Meta.Blocks import Blocks
# 2026-11-24
# "Decompose metadata.py into modular metadata collection package":
# https://github.com/dmitry-ai/harness/issues/170
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_blocks_builders_produce_step_paths_labels_and_blocks()`
def _build_agent_block(platform: str | None, instance_id: str | None, model: str | None, effort: str | None) -> dict[str, Any]:
	return Blocks.build_agent(platform, instance_id, model, effort)
# 2026-11-26
# "Surface ask_question clarifications in journal headers and require deferral disclosure":
# https://github.com/dmitry-ai/harness/issues/376
# @used-by unused
def _build_clarifications_block(turn: dict[str, Any], state_path: Path | None, tz: Any) -> list[dict[str, Any]] | None:
	return Blocks.build_clarifications(turn, state_path, tz)
# @used-by unused
def _build_journal_block(steps: list[int] | tuple[int, ...], conv_label: str | None) -> dict[str, Any]:
	return Blocks.build_journal(steps, conv_label)
# @used-by unused
def _build_journal_trace(jdir: Path | None, steps: list[int], group_file: str | Path | None, *, canon_root: Path | None=None, require_steps: bool=False) -> dict[str, Any]:
	return Blocks.build_journal_trace(jdir, steps, group_file, canon_root=canon_root, require_steps=require_steps, clean_null_fn=df_clean_null)
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_blocks_builders_produce_step_paths_labels_and_blocks()`
def _build_time_block(eff_req_dt: datetime | None, eff_res_dt: datetime, tz: Any) -> dict[str, Any]:
	return Blocks.build_time(eff_req_dt, eff_res_dt, tz)
# @used-by unused
def _build_trace_block(*, cid: str | None, subagent_cid: str | None=None, turn_trace: dict[str, Any], journal_trace: dict[str, Any], transcript_path: str | Path | None=None) -> dict[str, Any]:
	return Blocks.build_trace(cid=cid, subagent_cid=subagent_cid, turn_trace=turn_trace, journal_trace=journal_trace, transcript_path=transcript_path)
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_clean_null_and_unique_fast_delegation_to_df()`
def _build_turn_trace(*, turn_index: int | None, turn_id: Any, turn_key: str | None, start_step: int | None, final_step: int | None=None, tool_step: int | None=None, state_path: str | Path | None=None, canon_root: Path | None=None) -> dict[str, Any]:
	return Blocks.build_turn_trace(turn_index=turn_index, turn_id=turn_id, turn_key=turn_key, start_step=start_step, final_step=final_step, tool_step=tool_step, state_path=state_path, canon_root=canon_root, clean_null_fn=df_clean_null)
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_blocks_builders_produce_step_paths_labels_and_blocks()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _conversation_label(*, summary_title: str | None, conversation_steps: list[int] | tuple[int, ...] | None, current_steps: list[int] | tuple[int, ...] | None) -> str | None:
	return Blocks.conversation_label(summary_title=summary_title, conversation_steps=conversation_steps, current_steps=current_steps)
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_blocks_builders_produce_step_paths_labels_and_blocks()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _journal_step_paths(journal_dir: Path, steps: list[int]) -> tuple[str | list[str] | None, str | list[str] | None]:
	return Blocks(journal_dir, steps).step_paths()
# @used-by unused
def _resolve_conversation_steps(canon_root: Path | None, jdir: Path | None, cid: str | None) -> list[int] | None:
	return Blocks.resolve_conversation_steps(canon_root, jdir, cid)
# @used-by unused
def _resolve_hook(name: str, module: Any, default: Any) -> Any:
	return Blocks.resolve_hook(name, module, default)
