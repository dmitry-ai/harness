# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re
_FRAC_SECONDS_RE = re.compile(r'(\.\d{6})\d+')
_SYSTEM_DISPLAY = {'antigravity': 'Antigravity', 'codex': 'Codex'}
_UUID_RE = re.compile(r'^[a-f0-9-]{36}$', re.IGNORECASE)
def _format_step_value(steps: list[int] | tuple[int, ...]) -> int | list[int] | None:
	clean = sorted({int(s) for s in (steps or ()) if int is type(s) and 1 <= s})
	if not clean:
		r: int | list[int] | None = None
	else:
		r = clean[0] if 1 == len(clean) else clean
	return r
def _parse_iso_timestamp(raw: str) -> datetime | None:
	norm = _FRAC_SECONDS_RE.sub(r'\1', raw)
	if norm.endswith(('Z', 'z')):
		norm = norm[:-1] + '+00:00'
	try:
		dt = datetime.fromisoformat(norm)
		r: datetime | None = dt if None is not dt.tzinfo else dt.astimezone()
	except ValueError:
		r = None
	return r
def _split_model_and_effort(raw_model: str | None, raw_effort: str | None=None) -> tuple[str | None, str | None]:
	model = str(raw_model).strip() if isinstance(raw_model, str) and raw_model.strip() else None
	effort = str(raw_effort).strip() if isinstance(raw_effort, str) and raw_effort.strip() else None
	if model and None is effort:
		from ..platforms.antigravity import _configuration
		parsed = _configuration(model)
		model = parsed.get('model') or model
		effort = parsed.get('effort')
	return (model, effort)
def _system_display_name(platform: str | None) -> str | None:
	raw = str(platform or '').strip().lower()
	return _SYSTEM_DISPLAY.get(raw, raw.capitalize()) if raw else None
# 2026-11-24
# "Decompose metadata.py into modular metadata collection package":
# https://github.com/dmitry-ai/harness/issues/170
def format_duration_timecode(start: datetime | str | None, end: datetime | str | None) -> str | None:
	start_dt = parse_timestamp(start)
	end_dt = parse_timestamp(end)
	if None is start_dt or None is end_dt:
		r: str | None = None
	else:
		secs = max(0, int(round((end_dt - start_dt).total_seconds())))
		hours, rem = divmod(secs, 3600)
		mins, s = divmod(rem, 60)
		r = f'{hours:02d}:{mins:02d}:{s:02d}'
	return r
def format_local_timestamp(value: datetime | str | None=None, *, tz=None) -> str:
	dt = parse_timestamp(value) if None is not value else datetime.now().astimezone()
	if None is dt:
		dt = datetime.now().astimezone()
	local_dt = dt.astimezone(tz) if None is not tz else dt.astimezone()
	offset = local_dt.utcoffset()
	total_mins = int(round(offset.total_seconds() / 60)) if None is not offset else 0
	sign = '+' if 0 <= total_mins else '-'
	hours, mins = divmod(abs(total_mins), 60)
	tz_label = f'UTC{sign}{hours}' if 0 == mins else f'UTC{sign}{hours}:{mins:02d}'
	return f'{local_dt:%Y-%m-%d %H:%M:%S} {tz_label}'
def parse_timestamp(value: datetime | str | None) -> datetime | None:
	if None is value:
		r: datetime | None = None
	elif isinstance(value, datetime):
		r = value if None is not value.tzinfo else value.astimezone()
	else:
		raw = str(value).strip()
		r = _parse_iso_timestamp(raw) if raw else None
	return r
def posix_path(value: str | Path) -> str:
	try:
		text = Path(value).as_posix()
	except Exception:
		text = str(value).replace('\\', '/')
	return text.replace('\\', '/')
