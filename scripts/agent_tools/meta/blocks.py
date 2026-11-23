# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/170
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any
from .formatting import _format_step_value, _system_display_name, format_duration_timecode, format_local_timestamp, posix_path
import re
import sys
def _build_agent_block(platform: str | None, instance_id: str | None, model: str | None, effort: str | None) -> dict[str, Any]:
	r: dict[str, Any] = {}
	sys_name = _system_display_name(platform)
	if sys_name:
		r['System'] = sys_name
	if instance_id:
		r['Instance'] = str(instance_id)
	if model:
		r['Model'] = model
		r['Effort'] = effort
	elif effort:
		r['Effort'] = effort
	return r
def _build_journal_block(steps: list[int] | tuple[int, ...], conv_label: str | None) -> dict[str, Any]:
	r: dict[str, Any] = {}
	step_val = _format_step_value(steps)
	if None is not step_val:
		r['Step'] = step_val
	if conv_label:
		r['Conversation'] = conv_label
	return r
def _build_journal_trace(jdir: Path | None, steps: list[int], group_file: str | Path | None, *, canon_root: Path | None=None, require_steps: bool=False) -> dict[str, Any]:
	r: dict[str, Any] = {}
	if None is not jdir and (steps or (not require_steps)):
		req_paths, res_paths = _journal_step_paths(jdir, steps)
		pairs = (('Request', req_paths), ('Response', res_paths), ('Group', _resolve_optional_path(group_file, canon_root)))
		r = {k: v for k, v in pairs if None is not v}
	return r
def _build_time_block(eff_req_dt: datetime | None, eff_res_dt: datetime, tz: Any) -> dict[str, Any]:
	r: dict[str, Any] = {}
	if None is not eff_req_dt:
		r['Request'] = format_local_timestamp(eff_req_dt, tz=tz)
	r['Response'] = format_local_timestamp(eff_res_dt, tz=tz)
	duration = format_duration_timecode(eff_req_dt, eff_res_dt)
	if None is not duration:
		r['Duration'] = duration
	return r
def _build_trace_block(*, cid: str | None, subagent_cid: str | None=None, turn_trace: dict[str, Any], journal_trace: dict[str, Any], transcript_path: str | Path | None=None) -> dict[str, Any]:
	r: dict[str, Any] = {}
	if cid:
		r['Conversation ID'] = cid
	if subagent_cid and subagent_cid != cid:
		r['Subagent ID'] = subagent_cid
	if turn_trace:
		r['Turn'] = turn_trace
	if journal_trace:
		r['Journal'] = journal_trace
	if transcript_path:
		tp = Path(transcript_path)
		r['Transcript'] = posix_path(tp.resolve() if tp.is_absolute() else tp)
	return r
def _build_turn_trace(*, turn_index: int | None, turn_id: Any, turn_key: str | None, start_step: int | None, final_step: int | None=None, tool_step: int | None=None, state_path: str | Path | None=None, canon_root: Path | None=None) -> dict[str, Any]:
	pairs = (
		('Number', turn_index if isinstance(turn_index, int) and 1 <= turn_index else None),
		('ID', str(turn_id) if turn_id else None),
		('Key', str(turn_key) if turn_key else None),
		('Start Step', start_step),
		('Final Step', final_step),
		('Tool Step', tool_step),
		('State', _resolve_optional_path(state_path, canon_root)),
	)
	return {k: v for k, v in pairs if None is not v}
def _conversation_label(*, summary_title: str | None, conversation_steps: list[int] | tuple[int, ...] | None, current_steps: list[int] | tuple[int, ...] | None) -> str | None:
	from ..completion import format_conversation_journal_title
	all_steps = sorted({int(s) for s in (*(conversation_steps or ()), *(current_steps or ())) if int is type(s) and 1 <= s})
	title = str(summary_title or '').strip()
	if (not title) or title.lower() in ('new conversation', 'untitled'):
		r: str | None = format_conversation_journal_title(all_steps) if all_steps else None
	elif not all_steps:
		r = title
	else:
		formatted = format_conversation_journal_title(all_steps)
		r = title if title == formatted or (not re.fullmatch(r'\d+(?:,\s*\d+)*', title)) else formatted
	return r
def _journal_step_paths(journal_dir: Path, steps: list[int]) -> tuple[str | list[str] | None, str | list[str] | None]:
	from .. import journal
	req_dir, res_dir = journal.journal_pair_dirs(journal_dir)
	clean = sorted({int(s) for s in (steps or ()) if int is type(s) and 1 <= s})
	if not clean:
		r: tuple[str | list[str] | None, str | list[str] | None] = (None, None)
	else:
		req_paths = [posix_path(journal.step_file(req_dir, st, directory=journal_dir)) for st in clean]
		res_paths = [posix_path(journal.step_file(res_dir, st, directory=journal_dir)) for st in clean]
		r = (req_paths[0], res_paths[0]) if 1 == len(clean) else (req_paths, res_paths)
	return r
def _resolve_conversation_steps(canon_root: Path | None, jdir: Path | None, cid: str | None) -> list[int] | None:
	r: list[int] | None = None
	if None is not canon_root and None is not jdir and cid:
		try:
			from ..completion import conversation_journal_steps
			r = conversation_journal_steps(canon_root, jdir, cid)
		except Exception:
			r = None
	return r
def _resolve_hook(name: str, module: Any, default: Any) -> Any:
	facade = sys.modules.get('agent_tools.metadata')
	facade_fn = getattr(facade, name, default) if None is not facade else default
	return facade_fn if facade_fn is not default else getattr(module, name, default)
def _resolve_optional_path(path: str | Path | None, canon_root: Path | None) -> str | None:
	if None is path:
		r: str | None = None
	else:
		p = Path(path)
		r = posix_path(p.resolve() if p.is_absolute() else ((canon_root / p).resolve() if None is not canon_root else p))
	return r
