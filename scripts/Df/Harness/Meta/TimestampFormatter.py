# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class TimestampFormatter:
	FRAC_SECONDS_RE = re.compile(r'(\.\d{6})\d+')
	SYSTEM_DISPLAY = {'antigravity': 'Antigravity', 'codex': 'Codex'}
	UUID_RE = re.compile(r'^[a-f0-9-]{36}$', re.IGNORECASE)
	# @used-by :func:`agent_tools.meta.formatting.format_local_timestamp()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.__format_clarification_ts()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.build_time()`
	# @used-by :meth:`Df.Harness.Meta.Builders.Builders.build_github_issue()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	def __init__(self, value: datetime | str | None=None, *, tz=None) -> None:
		self.__value = value
		self.__tz = tz
	# @used-by :func:`agent_tools.meta.formatting.format_local_timestamp()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.__format_clarification_ts()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.build_time()`
	# @used-by :meth:`Df.Harness.Meta.Builders.Builders.build_github_issue()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	def format_local(self) -> str:
		dt = TimestampFormatter.parse_timestamp(self.__value) if None is not self.__value else datetime.now().astimezone()
		if None is dt:
			dt = datetime.now().astimezone()
		local_dt = dt.astimezone(self.__tz) if None is not self.__tz else dt.astimezone()
		offset = local_dt.utcoffset()
		total_mins = int(round(offset.total_seconds() / 60)) if None is not offset else 0
		sign = '+' if 0 <= total_mins else '-'
		hours, mins = divmod(abs(total_mins), 60)
		tz_label = f'UTC{sign}{hours}' if 0 == mins else f'UTC{sign}{hours}:{mins:02d}'
		return f'{local_dt:%Y-%m-%d %H:%M:%S} {tz_label}'
	# @used-by :meth:`TimestampFormatter.parse_timestamp()`
	@staticmethod
	def __parse_iso_timestamp(raw: str) -> datetime | None:
		norm = TimestampFormatter.FRAC_SECONDS_RE.sub(r'\1', raw)
		if norm.endswith(('Z', 'z')):
			norm = norm[:-1] + '+00:00'
		try:
			dt = datetime.fromisoformat(norm)
			r: datetime | None = dt if None is not dt.tzinfo else dt.astimezone()
		except ValueError:
			r = None
		return r
	# @used-by :meth:`TimestampFormatter.format_duration_timecode()`
	# @used-by :meth:`test_df_harness_s11_wave2b_meta.DfHarnessS11Wave2bMetaTests.test_meta_classes_render_headers_identity_transcripts_and_metrics()`
	@staticmethod
	def format_duration(seconds: float) -> str:
		secs = max(0, int(round(float(seconds))))
		hours, rem = divmod(secs, 3600)
		mins, s = divmod(rem, 60)
		return f'{hours:02d}:{mins:02d}:{s:02d}'
	# @used-by :func:`agent_tools.meta.formatting.format_duration_timecode()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.build_time()`
	@staticmethod
	def format_duration_timecode(start: datetime | str | None, end: datetime | str | None) -> str | None:
		start_dt = TimestampFormatter.parse_timestamp(start)
		end_dt = TimestampFormatter.parse_timestamp(end)
		return None if None is start_dt or None is end_dt else TimestampFormatter.format_duration((end_dt - start_dt).total_seconds())
	# @used-by :func:`agent_tools.meta.formatting._format_step_value()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.build_journal()`
	@staticmethod
	def format_step_value(steps: list[int] | tuple[int, ...]) -> int | list[int] | None:
		clean = sorted({int(s) for s in (steps or ()) if int is type(s) and 1 <= s})
		return None if not clean else (clean[0] if 1 == len(clean) else clean)
	# @used-by :func:`agent_tools.meta.formatting.parse_timestamp()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.__format_clarification_ts()`
	# @used-by :meth:`Df.Harness.Meta.Builders.Builders.build_journal()`
	# @used-by :meth:`TimestampFormatter.format_duration_timecode()`
	# @used-by :meth:`TimestampFormatter.format_local()`
	@staticmethod
	def parse_timestamp(value: datetime | str | None) -> datetime | None:
		if None is value:
			r: datetime | None = None
		elif isinstance(value, datetime):
			r = value if None is not value.tzinfo else value.astimezone()
		else:
			raw = str(value).strip()
			r = TimestampFormatter.__parse_iso_timestamp(raw) if raw else None
		return r
	# @used-by :func:`agent_tools.meta.formatting.posix_path()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.__resolve_optional_path()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.build_trace()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.step_paths()`
	# @used-by :meth:`Df.Harness.Meta.ProjectIdentity.ProjectIdentity.resolve()`
	@staticmethod
	def posix_path(value: str | Path) -> str:
		try:
			text = Path(value).as_posix()
		except Exception:
			text = str(value).replace('\\', '/')
		return text.replace('\\', '/')
	# @used-by :func:`agent_tools.meta.formatting._split_model_and_effort()`
	# @used-by :meth:`Df.Harness.Meta.Builders.Builders.__collect_journal_turn_state()`
	# @used-by :meth:`Df.Harness.Meta.TranscriptReader.TranscriptReader.__finalize_ag_info()`
	# @used-by :meth:`Df.Harness.Meta.TranscriptReader.TranscriptReader.extract_codex_info()`
	# @used-by :meth:`Df.Harness.Meta.TranscriptReader.TranscriptReader.resolve_ag_model_and_effort()`
	@staticmethod
	def split_model_and_effort(raw_model: str | None, raw_effort: str | None=None) -> tuple[str | None, str | None]:
		model = str(raw_model).strip() if isinstance(raw_model, str) and raw_model.strip() else None
		effort = str(raw_effort).strip() if isinstance(raw_effort, str) and raw_effort.strip() else None
		if model and None is effort:
			from agent_tools.platforms.antigravity import _configuration
			parsed = _configuration(model)
			model = parsed.get('model') or model
			effort = parsed.get('effort')
		return (model, effort)
	# @used-by :func:`agent_tools.meta.formatting._system_display_name()`
	# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.build_agent()`
	@staticmethod
	def system_display_name(platform: str | None) -> str | None:
		raw = str(platform or '').strip().lower()
		return TimestampFormatter.SYSTEM_DISPLAY.get(raw, raw.capitalize()) if raw else None
