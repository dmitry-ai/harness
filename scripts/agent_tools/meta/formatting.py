# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from Df.Harness.Meta.TimestampFormatter import TimestampFormatter
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
_FRAC_SECONDS_RE = TimestampFormatter.FRAC_SECONDS_RE
_SYSTEM_DISPLAY = TimestampFormatter.SYSTEM_DISPLAY
_UUID_RE = TimestampFormatter.UUID_RE
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_formatting_submodule_handles_paths_timestamps_steps_and_models()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _format_step_value(steps: list[int] | tuple[int, ...]) -> int | list[int] | None:
	return TimestampFormatter.format_step_value(steps)
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_formatting_submodule_handles_paths_timestamps_steps_and_models()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _split_model_and_effort(raw_model: str | None, raw_effort: str | None=None) -> tuple[str | None, str | None]:
	return TimestampFormatter.split_model_and_effort(raw_model, raw_effort)
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_formatting_submodule_handles_paths_timestamps_steps_and_models()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def _system_display_name(platform: str | None) -> str | None:
	return TimestampFormatter.system_display_name(platform)
# 2026-11-24
# "Decompose metadata.py into modular metadata collection package":
# https://github.com/dmitry-ai/harness/issues/170
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_format_local_timestamp_and_duration_timecode()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_formatting_submodule_handles_paths_timestamps_steps_and_models()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def format_duration_timecode(start: datetime | str | None, end: datetime | str | None) -> str | None:
	return TimestampFormatter.format_duration_timecode(start, end)
# @used-by :meth:`test_metadata.MetadataFormattingAndCollectionTests.test_format_local_timestamp_and_duration_timecode()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_formatting_submodule_handles_paths_timestamps_steps_and_models()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def format_local_timestamp(value: datetime | str | None=None, *, tz=None) -> str:
	return TimestampFormatter(value, tz=tz).format_local()
# @used-by :func:`agent_tools.cleanup_lifecycle._step_response_time()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_formatting_submodule_handles_paths_timestamps_steps_and_models()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def parse_timestamp(value: datetime | str | None) -> datetime | None:
	return TimestampFormatter.parse_timestamp(value)
# @used-by :func:`agent_tools.cleanup_audit.build_cleanup_metadata()`
# @used-by :func:`agent_tools.cleanup_audit.record_cleanup_answer_log()`
# @used-by :meth:`test_metadata_decomposition.MetadataDecompositionTests.test_formatting_submodule_handles_paths_timestamps_steps_and_models()`
# @used-by :mod:`agent_tools.meta`
# @used-by :mod:`agent_tools.metadata`
def posix_path(value: str | Path) -> str:
	return TimestampFormatter.posix_path(value)
