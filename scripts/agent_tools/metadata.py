# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prepend JSON metadata headers to new journal responses":
# https://github.com/dmitry-ai/harness/issues/151
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement shared execution metadata collector and tab-indented JSON header formatter":
# https://github.com/dmitry-ai/harness/issues/149
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any

_PROJECTS_DIR_CACHE: dict[tuple[str, int], list[dict[str, Any]]] = {}

_HARNESS_TOP_KEYS = frozenset(('Time', 'Issue', 'Project', 'Journal', 'Agent', 'Trace'))
_LEADING_JSON_FENCE_RE = re.compile(r'^```json[ \t]*\r?\n([\s\S]*?)\r?\n```[ \t]*(?:\r?\n\r?\n|\r?\n|$)')
_FRAC_SECONDS_RE = re.compile(r'(\.\d{6})\d+')
_UUID_RE = re.compile(r'^[a-f0-9-]{36}$', re.IGNORECASE)
_SYSTEM_DISPLAY = {
	'antigravity': 'Antigravity',
	'codex': 'Codex',
}


def posix_path(value: str | Path) -> str:
	p = Path(value)
	try:
		text = p.as_posix()
	except Exception:
		text = str(value).replace('\\', '/')
	return text.replace('\\', '/')


def parse_timestamp(value: datetime | str | None) -> datetime | None:
	if None is value:
		return None
	if isinstance(value, datetime):
		return value if None is not value.tzinfo else value.astimezone()
	raw = str(value).strip()
	if not raw:
		return None
	norm = _FRAC_SECONDS_RE.sub(r'\1', raw)
	if norm.endswith(('Z', 'z')):
		norm = norm[:-1] + '+00:00'
	try:
		dt = datetime.fromisoformat(norm)
	except ValueError:
		return None
	return dt if None is not dt.tzinfo else dt.astimezone()


def format_local_timestamp(value: datetime | str | None = None, *, tz=None) -> str:
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


def format_duration_timecode(start: datetime | str | None, end: datetime | str | None) -> str | None:
	start_dt = parse_timestamp(start)
	end_dt = parse_timestamp(end)
	if None is start_dt or None is end_dt:
		return None
	secs = max(0, int(round((end_dt - start_dt).total_seconds())))
	hours, rem = divmod(secs, 3600)
	mins, s = divmod(rem, 60)
	return f'{hours:02d}:{mins:02d}:{s:02d}'


def _is_harness_metadata_obj(obj: Any) -> bool:
	if not isinstance(obj, dict) or not obj:
		return False
	if not set(obj).issubset(_HARNESS_TOP_KEYS):
		return False
	proj = obj.get('Project')
	if not isinstance(proj, dict) or not isinstance(proj.get('Path'), str) or not proj['Path'].strip():
		return False
	return any((k in obj for k in ('Time', 'Issue', 'Journal', 'Agent', 'Trace')))


def render_metadata_header(data: dict[str, Any]) -> str:
	return '```json\n' + json.dumps(data, ensure_ascii=False, indent='\t') + '\n```\n\n'


def extract_leading_metadata_header(text: str) -> tuple[dict[str, Any] | None, str]:
	if not isinstance(text, str) or not text.startswith('```json'):
		return (None, text)
	m = _LEADING_JSON_FENCE_RE.match(text)
	if None is m:
		return (None, text)
	try:
		parsed = json.loads(m.group(1))
	except ValueError:
		return (None, text)
	if not _is_harness_metadata_obj(parsed):
		return (None, text)
	return (parsed, text[m.end():])


def strip_leading_metadata_header(text: str) -> str:
	return extract_leading_metadata_header(text)[1]


def prepend_metadata_header(body: str, data: dict[str, Any]) -> str:
	clean_body = strip_leading_metadata_header(body)
	return render_metadata_header(data) + clean_body


def _resolve_ag_paths_safe(backend=None, *, instance=None, conversation_id=None) -> dict[str, Any] | None:
	try:
		from .runtime import resolve_antigravity_paths, settings
		return resolve_antigravity_paths(backend=backend, instance=instance, conversation_id=conversation_id, config=settings())
	except Exception:
		return None


def _resolve_codex_paths_safe(backend=None, *, instance=None, conversation_id=None) -> dict[str, Any] | None:
	try:
		from .runtime import platform_settings, resolve_codex_paths
		return resolve_codex_paths(backend, instance=instance, conversation_id=conversation_id, codex_cfg=platform_settings('codex'))
	except Exception:
		return None


def _system_display_name(platform: str | None) -> str | None:
	raw = str(platform or '').strip().lower()
	if not raw:
		return None
	return _SYSTEM_DISPLAY.get(raw, raw.capitalize())


def _split_model_and_effort(raw_model: str | None, raw_effort: str | None = None) -> tuple[str | None, str | None]:
	model = str(raw_model).strip() if isinstance(raw_model, str) and raw_model.strip() else None
	effort = str(raw_effort).strip() if isinstance(raw_effort, str) and raw_effort.strip() else None
	if model and None is effort:
		from .platforms.antigravity import _configuration
		parsed = _configuration(model)
		model = parsed.get('model') or model
		effort = parsed.get('effort')
	return (model, effort)


def _is_temp_path(path: Path) -> bool:
	try:
		tmp_root = Path(tempfile.gettempdir()).resolve()
		return path.resolve().is_relative_to(tmp_root)
	except OSError:
		return False


def _load_projects_dir_items(pdir: Path) -> list[dict[str, Any]]:
	try:
		mtime_ns = pdir.stat().st_mtime_ns
	except OSError:
		return []
	cache_key = (pdir.as_posix().lower(), mtime_ns)
	cached = _PROJECTS_DIR_CACHE.get(cache_key)
	if None is not cached:
		return cached
	if 64 < len(_PROJECTS_DIR_CACHE):
		_PROJECTS_DIR_CACHE.clear()
	items: list[dict[str, Any]] = []
	for pf in sorted(pdir.glob('*.json')):
		try:
			item = json.loads(pf.read_text(encoding='utf-8-sig'))
		except (OSError, ValueError):
			continue
		if isinstance(item, dict):
			items.append(item)
	_PROJECTS_DIR_CACHE[cache_key] = items
	return items


def _antigravity_project_dirs(ag_paths: dict[str, Any] | None = None, *, canon_root: Path | None = None) -> list[Path]:
	dirs: list[Path] = []
	seen: set[str] = set()
	def _push(p_val: str | Path | None) -> None:
		if not p_val:
			return
		p = Path(p_val)
		if not p.is_dir():
			return
		key = p.resolve().as_posix().lower()
		if key not in seen:
			seen.add(key)
			dirs.append(p.resolve())
	if isinstance(ag_paths, dict):
		_push(ag_paths.get('projects_dir'))
	if None is canon_root or (not _is_temp_path(canon_root)):
		try:
			from .runtime import platform_instances
			for inst in platform_instances('antigravity', include_disabled=True).values():
				_push((inst.get('system_paths') or {}).get('projects_dir'))
		except Exception:
			pass
	return dirs


def resolve_project_identity(
	root: str | Path,
	*,
	ag_paths: dict[str, Any] | None = None,
	project_id: str | None = None,
) -> dict[str, str]:
	from .path_registry import canonicalize_root_dir, project_paths
	from .platforms.antigravity import _project_item_matches_root
	canon = canonicalize_root_dir(root)
	name: str | None = None
	pdirs = _antigravity_project_dirs(ag_paths, canon_root=canon)
	if isinstance(project_id, str) and project_id.strip():
		pid = project_id.strip()
		for pdir in pdirs:
			cand = pdir / f'{pid}.json'
			if cand.is_file():
				try:
					data = json.loads(cand.read_text(encoding='utf-8-sig'))
					if isinstance(data, dict) and isinstance(data.get('name'), str) and data['name'].strip():
						matched, _ = _project_item_matches_root(data, canon)
						if matched:
							name = data['name'].strip()
							break
				except (OSError, ValueError):
					continue
	if None is name:
		relocated_name: str | None = None
		for pdir in pdirs:
			for item in _load_projects_dir_items(pdir):
				matched, is_reloc = _project_item_matches_root(item, canon)
				if matched and isinstance(item.get('name'), str) and item['name'].strip():
					if not is_reloc:
						name = item['name'].strip()
						break
					if None is relocated_name:
						relocated_name = item['name'].strip()
			if None is not name:
				break
		if None is name and None is not relocated_name:
			name = relocated_name
	if None is name:
		try:
			pj = project_paths(canon, exact_root=True).project_json
			if pj.is_file():
				pdata = json.loads(pj.read_text(encoding='utf-8-sig'))
				if isinstance(pdata, dict):
					for key in ('project_name', 'name', 'domain', 'title'):
						val = pdata.get(key)
						if isinstance(val, str) and val.strip():
							name = val.strip()
							break
		except (OSError, ValueError):
			pass
	if None is name:
		name = canon.name or posix_path(canon)
	return {'Name': name, 'Path': posix_path(canon)}


def _read_ag_summary_row(ag_paths: dict[str, Any] | None, conversation_id: str) -> dict[str, Any] | None:
	if not isinstance(ag_paths, dict) or not ag_paths.get('conversations_db'):
		return None
	db_p = Path(ag_paths['conversations_db'])
	if not db_p.is_file():
		return None
	try:
		from .platforms.trace_common import open_readonly_sqlite
		with open_readonly_sqlite(db_p, row_factory=sqlite3.Row) as conn:
			row = conn.execute('SELECT * FROM conversation_summaries WHERE conversation_id=?', (conversation_id,)).fetchone()
			return dict(row) if None is not row else None
	except (OSError, sqlite3.Error):
		return None


def _ag_transcript_file(ag_paths: dict[str, Any] | None, conversation_id: str) -> Path | None:
	if not isinstance(ag_paths, dict) or not ag_paths.get('brain_dir'):
		return None
	logs = Path(ag_paths['brain_dir']) / conversation_id / '.system_generated/logs'
	full_t = logs / 'transcript_full.jsonl'
	compact_t = logs / 'transcript.jsonl'
	if full_t.is_file():
		return full_t.resolve()
	if compact_t.is_file():
		return compact_t.resolve()
	return full_t.resolve()


def _extract_ag_transcript_info(
	transcript_path: str | Path | None,
	*,
	start_step: int | None = None,
	end_step: int | None = None,
	final_step: int | None = None,
) -> dict[str, Any]:
	info: dict[str, Any] = {
		'request_timestamp': None,
		'response_timestamp': None,
		'model': None,
		'effort': None,
		'turn_index': None,
	}
	if not transcript_path:
		return info
	tp = Path(transcript_path)
	if not tp.is_file():
		return info
	try:
		from .platforms.trace_common import read_jsonl_objects
		rows = read_jsonl_objects(tp)
	except Exception:
		rows = []
		try:
			for ln in tp.read_text(encoding='utf-8', errors='replace').splitlines():
				if ln.strip():
					try:
						rows.append(json.loads(ln))
					except ValueError:
						continue
		except OSError:
			return info
	user_steps: list[int] = []
	slice_models: list[str] = []
	all_models: list[str] = []
	for row in rows:
		if not isinstance(row, dict):
			continue
		sidx = row.get('step_index')
		rtype = row.get('type')
		created = row.get('created_at')
		if 'USER_INPUT' == rtype and isinstance(sidx, int):
			user_steps.append(sidx)
			if None is not start_step and sidx == start_step and isinstance(created, str) and created.strip():
				info['request_timestamp'] = created.strip()
		if None is not final_step and sidx == final_step and isinstance(created, str) and created.strip():
			info['response_timestamp'] = created.strip()
		if 'PLANNER_RESPONSE' == rtype and isinstance(row.get('model'), str) and row['model'].strip():
			raw_m = row['model'].strip()
			all_models.append(raw_m)
			if isinstance(sidx, int):
				after_start = None is start_step or sidx > start_step
				before_end = None is end_step or sidx < end_step
				if after_start and before_end:
					slice_models.append(raw_m)
	if None is not start_step and user_steps:
		uniq_steps = sorted(set(user_steps))
		if start_step in uniq_steps:
			info['turn_index'] = uniq_steps.index(start_step) + 1
	elif user_steps:
		info['turn_index'] = len(set(user_steps))
	chosen_model = slice_models[-1] if slice_models else (all_models[-1] if all_models else None)
	if chosen_model:
		info['model'], info['effort'] = _split_model_and_effort(chosen_model)
	return info


def _extract_codex_transcript_info(
	rollout_path: str | Path | None,
	*,
	turn_id: str | None = None,
	start_step: int | None = None,
	final_step: int | None = None,
) -> dict[str, Any]:
	info: dict[str, Any] = {
		'request_timestamp': None,
		'response_timestamp': None,
		'model': None,
		'effort': None,
		'turn_index': None,
	}
	if not rollout_path:
		return info
	rp = Path(rollout_path)
	if not rp.is_file():
		return info
	turn_ids: list[str] = []
	matched_ctx: tuple[str | None, str | None] | None = None
	last_ctx: tuple[str | None, str | None] | None = None
	try:
		lines = rp.read_text(encoding='utf-8', errors='replace').splitlines()
	except OSError:
		return info
	for idx, ln in enumerate(lines):
		if not ln.strip():
			continue
		try:
			obj = json.loads(ln)
		except ValueError:
			continue
		if not isinstance(obj, dict):
			continue
		kind = obj.get('type')
		payload = obj.get('payload') if isinstance(obj.get('payload'), dict) else {}
		ts = obj.get('timestamp') if isinstance(obj.get('timestamp'), str) else None
		if 'event_msg' == kind and 'task_started' == payload.get('type'):
			tid = payload.get('turn_id')
			if isinstance(tid, str) and tid:
				if tid not in turn_ids:
					turn_ids.append(tid)
				if turn_id == tid and ts and None is info['request_timestamp']:
					info['request_timestamp'] = ts
		if None is not start_step and idx == start_step and ts and None is info['request_timestamp']:
			info['request_timestamp'] = ts
		if None is not final_step and idx == final_step and ts:
			info['response_timestamp'] = ts
		if 'event_msg' == kind and 'task_complete' == payload.get('type') and turn_id and payload.get('turn_id') == turn_id and ts:
			info['response_timestamp'] = ts
		if 'turn_context' == kind:
			m_val = payload.get('model') if isinstance(payload.get('model'), str) else None
			e_val = payload.get('effort') if isinstance(payload.get('effort'), str) else None
			if m_val or e_val:
				last_ctx = (m_val, e_val)
				if turn_id and payload.get('turn_id') == turn_id:
					matched_ctx = (m_val, e_val)
	if turn_id and turn_id in turn_ids:
		info['turn_index'] = turn_ids.index(turn_id) + 1
	elif turn_ids:
		info['turn_index'] = len(turn_ids)
	chosen = matched_ctx or last_ctx
	if chosen:
		info['model'], info['effort'] = _split_model_and_effort(chosen[0], chosen[1])
	return info


def _resolve_ag_model_and_effort(
	ag_paths: dict[str, Any] | None,
	conversation_id: str,
	*,
	transcript_path: str | Path | None = None,
	start_step: int | None = None,
	end_step: int | None = None,
) -> tuple[str | None, str | None]:
	t_info = _extract_ag_transcript_info(transcript_path, start_step=start_step, end_step=end_step)
	model, effort = (t_info.get('model'), t_info.get('effort'))
	if model and effort:
		return (model, effort)
	if isinstance(ag_paths, dict) and ag_paths.get('backend_dir'):
		try:
			from .platforms.antigravity import _model_metadata
			observed, _, _ = _model_metadata(Path(ag_paths['backend_dir']), conversation_id, paths=ag_paths)
			if None is model and observed.get('model'):
				model, parsed_eff = _split_model_and_effort(observed.get('model'), observed.get('effort'))
				effort = effort or parsed_eff
			elif None is effort and observed.get('effort'):
				effort = observed.get('effort')
		except Exception:
			pass
	return (model, effort)


def _format_step_value(steps: list[int] | tuple[int, ...]) -> int | list[int] | None:
	clean = sorted({int(s) for s in (steps or ()) if int is type(s) and 1 <= s})
	if not clean:
		return None
	return clean[0] if 1 == len(clean) else clean


def _journal_step_paths(journal_dir: Path, steps: list[int]) -> tuple[str | list[str] | None, str | list[str] | None]:
	from . import journal
	req_dir, res_dir = journal.journal_pair_dirs(journal_dir)
	clean = sorted({int(s) for s in (steps or ()) if int is type(s) and 1 <= s})
	if not clean:
		return (None, None)
	req_paths = [posix_path(journal.step_file(req_dir, st, directory=journal_dir)) for st in clean]
	res_paths = [posix_path(journal.step_file(res_dir, st, directory=journal_dir)) for st in clean]
	if 1 == len(clean):
		return (req_paths[0], res_paths[0])
	return (req_paths, res_paths)


def _conversation_label(
	*,
	summary_title: str | None,
	conversation_steps: list[int] | tuple[int, ...] | None,
	current_steps: list[int] | tuple[int, ...] | None,
) -> str | None:
	from .completion import format_conversation_journal_title
	all_steps = sorted({int(s) for s in (*(conversation_steps or ()), *(current_steps or ())) if int is type(s) and 1 <= s})
	title = str(summary_title or '').strip()
	if title and title.lower() not in ('new conversation', 'untitled'):
		if not all_steps:
			return title
		formatted = format_conversation_journal_title(all_steps)
		if title == formatted or (not re.fullmatch(r'\d+(?:,\s*\d+)*', title)):
			return title
		return formatted
	if all_steps:
		return format_conversation_journal_title(all_steps)
	return None


def build_journal_metadata(
	root: str | Path,
	native: dict[str, Any],
	turn: dict[str, Any],
	*,
	journal_dir: str | Path,
	steps: list[int],
	turn_key: str,
	turn_state_path: str | Path | None = None,
	group_file: str | Path | None = None,
	conversation_steps: list[int] | None = None,
	request_at: datetime | str | None = None,
	response_at: datetime | str | None = None,
	tz=None,
) -> dict[str, Any]:
	from .path_registry import canonicalize_root_dir, project_paths
	canon_root = canonicalize_root_dir(root)
	pp = project_paths(canon_root, exact_root=True)
	jdir = Path(journal_dir).resolve()
	platform = str(native.get('platform') or '').strip().lower()
	cid = str(native.get('conversation_id') or '').strip()
	backend_raw = native.get('native_backend')
	source_file = native.get('source_file')

	ag_paths = _resolve_ag_paths_safe(backend=backend_raw, instance=native.get('instance'), conversation_id=cid) if 'antigravity' == platform else None
	cx_paths = _resolve_codex_paths_safe(backend=backend_raw, instance=native.get('instance'), conversation_id=cid) if 'codex' == platform else None
	instance_id = native.get('instance') or (ag_paths.get('instance') if isinstance(ag_paths, dict) else None) or (cx_paths.get('instance') if isinstance(cx_paths, dict) else None)

	summary_row = _read_ag_summary_row(ag_paths, cid) if 'antigravity' == platform and cid else None
	project_id = summary_row.get('project_id') if isinstance(summary_row, dict) else None
	project_info = resolve_project_identity(canon_root, ag_paths=ag_paths, project_id=project_id)

	# Determine turn index within conversation
	turn_index = turn.get('turn_index')
	if not isinstance(turn_index, int) or 1 > turn_index:
		turns_list = native.get('turns') or ()
		for idx, item in enumerate(turns_list, 1):
			if isinstance(item, dict) and item.get('turn_id') == turn.get('turn_id'):
				turn_index = idx
				break

	# Extract timestamps and model/effort
	start_step = turn.get('start_step') if isinstance(turn.get('start_step'), int) else None
	final_step = turn.get('final_step') if isinstance(turn.get('final_step'), int) else None
	eff_req_ts = request_at or turn.get('request_timestamp')
	eff_res_ts = response_at or turn.get('response_timestamp')
	model, effort = _split_model_and_effort(turn.get('model'), turn.get('effort'))

	if 'antigravity' == platform:
		t_path = source_file or (_ag_transcript_file(ag_paths, cid) if cid else None)
		if None is eff_req_ts or None is model or None is effort or None is turn_index:
			t_info = _extract_ag_transcript_info(t_path, start_step=start_step, final_step=final_step)
			if None is eff_req_ts:
				eff_req_ts = t_info.get('request_timestamp')
			if None is eff_res_ts:
				eff_res_ts = t_info.get('response_timestamp')
			if None is turn_index:
				turn_index = t_info.get('turn_index')
			if None is model or None is effort:
				fb_m, fb_e = _resolve_ag_model_and_effort(ag_paths, cid, transcript_path=t_path, start_step=start_step)
				model = model or fb_m
				effort = effort or fb_e
		if None is eff_req_ts and isinstance(summary_row, dict) and summary_row.get('last_user_input_time'):
			eff_req_ts = summary_row.get('last_user_input_time')
	elif 'codex' == platform:
		if None is eff_req_ts or None is model or None is effort or None is turn_index:
			c_info = _extract_codex_transcript_info(source_file, turn_id=turn.get('turn_id'), start_step=start_step, final_step=final_step)
			if None is eff_req_ts:
				eff_req_ts = c_info.get('request_timestamp')
			if None is eff_res_ts:
				eff_res_ts = c_info.get('response_timestamp')
			if None is turn_index:
				turn_index = c_info.get('turn_index')
			model = model or c_info.get('model')
			effort = effort or c_info.get('effort')

	eff_res_dt = parse_timestamp(eff_res_ts) or datetime.now().astimezone()
	eff_req_dt = parse_timestamp(eff_req_ts)
	time_block: dict[str, Any] = {}
	if None is not eff_req_dt:
		time_block['Request'] = format_local_timestamp(eff_req_dt, tz=tz)
	time_block['Response'] = format_local_timestamp(eff_res_dt, tz=tz)
	duration = format_duration_timecode(eff_req_dt, eff_res_dt)
	if None is not duration:
		time_block['Duration'] = duration

	if None is conversation_steps and cid:
		try:
			from .completion import conversation_journal_steps
			conversation_steps = conversation_journal_steps(canon_root, jdir, cid)
		except Exception:
			conversation_steps = None
	conv_label = _conversation_label(
		summary_title=summary_row.get('title') if isinstance(summary_row, dict) else None,
		conversation_steps=conversation_steps,
		current_steps=steps,
	)
	journal_block: dict[str, Any] = {}
	step_val = _format_step_value(steps)
	if None is not step_val:
		journal_block['Step'] = step_val
	if conv_label:
		journal_block['Conversation'] = conv_label

	agent_block: dict[str, Any] = {}
	sys_name = _system_display_name(platform)
	if sys_name:
		agent_block['System'] = sys_name
	if instance_id:
		agent_block['Instance'] = str(instance_id)
	if model:
		agent_block['Model'] = model
		agent_block['Effort'] = effort
	elif effort:
		agent_block['Effort'] = effort

	state_p = Path(turn_state_path) if None is not turn_state_path else (pp.turns_dir / f'{turn_key}.json')
	turn_trace: dict[str, Any] = {}
	if isinstance(turn_index, int) and 1 <= turn_index:
		turn_trace['Number'] = turn_index
	if turn.get('turn_id'):
		turn_trace['ID'] = str(turn['turn_id'])
	if turn_key:
		turn_trace['Key'] = str(turn_key)
	if None is not start_step:
		turn_trace['Start Step'] = start_step
	if None is not final_step:
		turn_trace['Final Step'] = final_step
	turn_trace['State'] = posix_path(state_p.resolve() if state_p.is_absolute() else (canon_root / state_p).resolve())

	req_paths, res_paths = _journal_step_paths(jdir, steps)
	journal_trace: dict[str, Any] = {}
	if None is not req_paths:
		journal_trace['Request'] = req_paths
	if None is not res_paths:
		journal_trace['Response'] = res_paths
	if None is not group_file:
		gp = Path(group_file)
		journal_trace['Group'] = posix_path(gp.resolve() if gp.is_absolute() else (canon_root / gp).resolve())

	trace_block: dict[str, Any] = {}
	if cid:
		trace_block['Conversation ID'] = cid
	if turn_trace:
		trace_block['Turn'] = turn_trace
	if journal_trace:
		trace_block['Journal'] = journal_trace
	if source_file:
		trace_block['Transcript'] = posix_path(Path(source_file).resolve() if Path(source_file).is_absolute() else Path(source_file))

	result: dict[str, Any] = {
		'Time': time_block,
		'Project': project_info,
	}
	if journal_block:
		result['Journal'] = journal_block
	if agent_block:
		result['Agent'] = agent_block
	if trace_block:
		result['Trace'] = trace_block
	return result


def _find_turn_state_for_conversation(turns_dir: Path, conversation_id: str) -> tuple[Path, dict[str, Any]] | None:
	if not turns_dir.is_dir() or not conversation_id:
		return None
	cid_low = conversation_id.strip().lower()
	candidates: list[tuple[int, int, Path, dict[str, Any]]] = []
	for sf in turns_dir.glob('*.json'):
		if sf.name.endswith(('-checkpoint-recovery.json', '-violation-recovery.json', '-similar-exemptions.json', '-ratchet-ok.json')):
			continue
		try:
			data = json.loads(sf.read_text(encoding='utf-8'))
			mtime_ns = sf.stat().st_mtime_ns
		except (OSError, ValueError):
			continue
		if not isinstance(data, dict):
			continue
		if str(data.get('conversation_id') or '').strip().lower() != cid_low:
			continue
		is_open = 1 if 'open' == data.get('status') else 0
		candidates.append((is_open, mtime_ns, sf.resolve(), data))
	if not candidates:
		return None
	candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
	return (candidates[0][2], candidates[0][3])


def _extract_turn_steps_from_state(state: dict[str, Any]) -> list[int]:
	for slot in ('prepared', 'journal_record', 'delivery'):
		rec = state.get(slot)
		if isinstance(rec, dict) and isinstance(rec.get('journal_steps'), list):
			valid = [st for st in rec['journal_steps'] if int is type(st) and 1 <= st]
			if valid:
				return sorted(set(valid))
	reserved = state.get('reserved_journal_steps')
	if isinstance(reserved, list):
		valid = [st for st in reserved if int is type(st) and 1 <= st]
		if valid:
			return sorted(set(valid))
	return []


def _parse_antigravity_source_metadata(env: dict[str, str]) -> tuple[str | None, int | None]:
	raw = str(env.get('ANTIGRAVITY_SOURCE_METADATA') or '').strip()
	if not raw:
		return (None, None)
	try:
		parsed = json.loads(raw)
	except ValueError:
		return (None, None)
	tool_obj = parsed.get('tool') if isinstance(parsed, dict) and isinstance(parsed.get('tool'), dict) else {}
	cid = str(tool_obj.get('conversationId') or '').strip().lower() or None
	sidx = tool_obj.get('stepIndex')
	step_idx = sidx if int is type(sidx) and 0 <= sidx else None
	return (cid, step_idx)


def build_github_issue_metadata(
	*,
	issue_url: str,
	project_root: str | Path | None = None,
	env: dict[str, str] | None = None,
	now: datetime | str | None = None,
	tz=None,
) -> dict[str, Any]:
	from . import journal
	from .path_registry import canonicalize_root_dir, project_paths

	environ = dict(os.environ) if None is env else dict(env)
	meta_cid, tool_step = _parse_antigravity_source_metadata(environ)
	ag_cid = (str(environ.get('ANTIGRAVITY_CONVERSATION_ID') or '').strip().lower() or meta_cid or '')
	cx_cid = str(environ.get('CODEX_THREAD_ID') or '').strip().lower()

	platform: str | None = None
	active_cid: str | None = None
	if ag_cid and _UUID_RE.fullmatch(ag_cid):
		platform = 'antigravity'
		active_cid = ag_cid
	elif cx_cid and _UUID_RE.fullmatch(cx_cid):
		platform = 'codex'
		active_cid = cx_cid

	ag_paths: dict[str, Any] | None = None
	cx_paths: dict[str, Any] | None = None
	instance_id: str | None = None
	primary_cid: str | None = active_cid
	subagent_cid: str | None = None
	summary_row: dict[str, Any] | None = None
	transcript_path: Path | None = None
	model: str | None = None
	effort: str | None = None
	turn_index: int | None = None

	if 'antigravity' == platform and active_cid:
		ag_backend_env = str(environ.get('ANTIGRAVITY_APP_DATA_DIR') or '').strip() or None
		ag_inst_env = str(environ.get('ANTIGRAVITY_ACCOUNT') or '').strip() or None
		ag_paths = _resolve_ag_paths_safe(backend=ag_backend_env, instance=ag_inst_env, conversation_id=active_cid)
		if None is ag_paths and ag_backend_env:
			bp = Path(ag_backend_env).resolve()
			ag_paths = {
				'instance': ag_inst_env,
				'backend_dir': bp,
				'brain_dir': bp / 'brain',
				'conversations_db': bp / 'conversation_summaries.db',
				'conversations_dir': bp / 'conversations',
				'projects_dir': bp.parent / 'config/projects',
			}
		instance_id = (ag_paths.get('instance') if isinstance(ag_paths, dict) else None) or ag_inst_env
		active_row = _read_ag_summary_row(ag_paths, active_cid)
		if isinstance(active_row, dict) and str(active_row.get('parent_conversation_id') or '').strip():
			subagent_cid = active_cid
			primary_cid = str(active_row['parent_conversation_id']).strip().lower()
			summary_row = _read_ag_summary_row(ag_paths, primary_cid) or active_row
		else:
			summary_row = active_row
		transcript_path = _ag_transcript_file(ag_paths, active_cid)
		model, effort = _resolve_ag_model_and_effort(ag_paths, active_cid, transcript_path=transcript_path)
	elif 'codex' == platform and active_cid:
		cx_home_env = str(environ.get('CODEX_HOME') or '').strip() or None
		cx_paths = _resolve_codex_paths_safe(backend=cx_home_env, conversation_id=active_cid)
		instance_id = cx_paths.get('instance') if isinstance(cx_paths, dict) else None
		try:
			from .runtime import _codex_home_conversation_trace
			trace_str = _codex_home_conversation_trace(cx_paths.get('home') if isinstance(cx_paths, dict) else cx_home_env, active_cid, system_paths=cx_paths)
			if trace_str:
				transcript_path = Path(trace_str).resolve()
		except Exception:
			transcript_path = None
		if None is not transcript_path:
			c_info = _extract_codex_transcript_info(transcript_path)
			model = c_info.get('model')
			effort = c_info.get('effort')
			turn_index = c_info.get('turn_index')

	canon_root: Path | None = None
	if None is not project_root and str(project_root).strip():
		canon_root = canonicalize_root_dir(project_root)

	state_path: Path | None = None
	state_obj: dict[str, Any] | None = None
	if None is not canon_root and primary_cid:
		try:
			pp = project_paths(canon_root, exact_root=True)
			hit = _find_turn_state_for_conversation(pp.turns_dir, primary_cid)
			if None is not hit:
				state_path, state_obj = hit
		except (OSError, ValueError):
			pass

	steps: list[int] = []
	jdir: Path | None = None
	group_file: Path | None = None
	turn_key: str | None = None
	turn_id: str | None = None
	start_step: int | None = None
	if isinstance(state_obj, dict):
		turn_key = str(state_obj.get('key') or state_path.stem) if None is not state_path else state_obj.get('key')
		turn_id = state_obj.get('native_turn_id')
		if isinstance(state_obj.get('native_start_step'), int):
			start_step = state_obj['native_start_step']
		steps = _extract_turn_steps_from_state(state_obj)
		if state_obj.get('journal'):
			jdir = journal.canonicalize_journal_dir_identity(state_obj['journal'])
		elif None is not canon_root:
			jdir = journal.resolve_journal_dir(canon_root)
		for slot in ('prepared', 'journal_record', 'delivery'):
			rec = state_obj.get(slot)
			if isinstance(rec, dict) and rec.get('group_file'):
				group_file = Path(rec['group_file'])
				break
		if None is group_file and None is not jdir and turn_key:
			group_file = journal.state_dir(jdir) / 'answer-groups' / f'native-{turn_key}.json'
		if 'antigravity' == platform and primary_cid:
			p_trans = _ag_transcript_file(ag_paths, primary_cid)
			p_info = _extract_ag_transcript_info(p_trans, start_step=start_step)
			if isinstance(p_info.get('turn_index'), int):
				turn_index = p_info['turn_index']
		elif 'codex' == platform and None is not transcript_path:
			c_info = _extract_codex_transcript_info(transcript_path, turn_id=turn_id, start_step=start_step)
			if isinstance(c_info.get('turn_index'), int):
				turn_index = c_info['turn_index']
			model = model or c_info.get('model')
			effort = effort or c_info.get('effort')

	env_pid = str(environ.get('ANTIGRAVITY_PROJECT_ID') or '').strip() or (summary_row.get('project_id') if isinstance(summary_row, dict) else None)
	project_info = resolve_project_identity(canon_root, ag_paths=ag_paths, project_id=env_pid) if None is not canon_root else None

	conv_steps: list[int] | None = None
	if None is not canon_root and None is not jdir and primary_cid:
		try:
			from .completion import conversation_journal_steps
			conv_steps = conversation_journal_steps(canon_root, jdir, primary_cid)
		except Exception:
			conv_steps = None
	conv_label = _conversation_label(
		summary_title=summary_row.get('title') if isinstance(summary_row, dict) else None,
		conversation_steps=conv_steps,
		current_steps=steps,
	)

	journal_block: dict[str, Any] = {}
	step_val = _format_step_value(steps)
	if None is not step_val:
		journal_block['Step'] = step_val
	if conv_label:
		journal_block['Conversation'] = conv_label

	agent_block: dict[str, Any] = {}
	sys_name = _system_display_name(platform)
	if sys_name:
		agent_block['System'] = sys_name
	if instance_id:
		agent_block['Instance'] = str(instance_id)
	if model:
		agent_block['Model'] = model
		agent_block['Effort'] = effort
	elif effort:
		agent_block['Effort'] = effort

	turn_trace: dict[str, Any] = {}
	if isinstance(turn_index, int) and 1 <= turn_index:
		turn_trace['Number'] = turn_index
	if turn_id:
		turn_trace['ID'] = str(turn_id)
	if turn_key:
		turn_trace['Key'] = str(turn_key)
	if None is not start_step:
		turn_trace['Start Step'] = start_step
	if None is not tool_step:
		turn_trace['Tool Step'] = tool_step
	if None is not state_path:
		turn_trace['State'] = posix_path(state_path)

	journal_trace: dict[str, Any] = {}
	if None is not jdir and steps:
		req_paths, res_paths = _journal_step_paths(jdir, steps)
		if None is not req_paths:
			journal_trace['Request'] = req_paths
		if None is not res_paths:
			journal_trace['Response'] = res_paths
		if None is not group_file:
			journal_trace['Group'] = posix_path(group_file.resolve() if group_file.is_absolute() else group_file)

	trace_block: dict[str, Any] = {}
	if primary_cid:
		trace_block['Conversation ID'] = primary_cid
	if subagent_cid and subagent_cid != primary_cid:
		trace_block['Subagent ID'] = subagent_cid
	if turn_trace:
		trace_block['Turn'] = turn_trace
	if journal_trace:
		trace_block['Journal'] = journal_trace
	if None is not transcript_path:
		trace_block['Transcript'] = posix_path(transcript_path)

	result: dict[str, Any] = {
		'Time': format_local_timestamp(now, tz=tz),
		'Issue': str(issue_url),
	}
	if project_info:
		result['Project'] = project_info
	if journal_block:
		result['Journal'] = journal_block
	if agent_block:
		result['Agent'] = agent_block
	if trace_block:
		result['Trace'] = trace_block
	return result
