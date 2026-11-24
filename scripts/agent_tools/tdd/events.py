# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Preserve multi-turn handed-off Stop Gate routing and stateful loop guard":
# https://github.com/dmitry-ai/harness/issues/224
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/173
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/169
from __future__ import annotations
from pathlib import Path
from ..shell_audit import classify_git_argv, normalize_host_path
from .classifier import classify_code_path, resolve_code_scope
from .commands import classify_test_command
from .outcomes import _BG_TASK_FINISHED_RE, _BG_TASK_ID_RE, extract_bg_task_ids, parse_command_outcome
import json
import re
_BG_ENDED_RE = re.compile(r'Task\s+id\s+"([^"]+)"\s+(?:finished|canceled|cancelled|terminated|killed)\b', re.IGNORECASE)
_BG_SENDER_RE = re.compile(r'\bsender=([A-Za-z0-9_./:-]+/task-\d+)\b', re.IGNORECASE)
_DENIED_WRITE_OUT_RE = re.compile(r'Encountered error in (?:tool|step) execution:|tool call denied by pre-tool hook:', re.IGNORECASE)
_SAFE_COMMIT_EXEC_RE = re.compile(r'\bsafe_commit\.py\b[^\r\n]*--execute\b')
_SAFE_COMMIT_REPO_RE = re.compile(r'--repo\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))')
_SUBAGENT_DONE_RE = re.compile(r'<SYSTEM_MESSAGE>.*(?:\bSubagent\b.*\bcompleted\b|\[Message\]\s+timestamp=[^\n]+\bsender=[0-9a-f]{8}-[0-9a-f]{4}-)', re.S | re.I)
_WRITE_TOOL_NAMES = frozenset({'edit_file', 'multi_replace_file_content', 'replace_file_content', 'write_file', 'write_to_file'})
def _antigravity_segment_is_interrupted(seg_rows: list[dict]) -> bool:
	from ..platforms.trace_common import is_waiting_status_stub
	active_bg: set[str] = set()
	spawned_subs, completed_subs, prepared = (0, 0, False)
	for pos, row in enumerate(seg_rows):
		if isinstance(row, dict):
			completed_subs += _scan_segment_status_row(row, active_bg)
			calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
			if calls:
				outs = _collect_following_outputs(seg_rows, pos)
				sub_delta, saw_prep = _scan_segment_calls(calls, outs, active_bg)
				spawned_subs += sub_delta
				prepared = prepared or saw_prep
	last = seg_rows[-1] if seg_rows else {}
	has_final_text = isinstance(last, dict) and 'PLANNER_RESPONSE' == last.get('type') and (not last.get('tool_calls')) and bool(str(last.get('content') or '').strip())
	last_text = str(last.get('content') or '') if isinstance(last, dict) else ''
	return (not prepared) and (bool(active_bg) or completed_subs < spawned_subs or (not has_final_text) or is_waiting_status_stub(last_text))
def _append_command_tool_event(step_idx: int, c_pos: int, cargs: dict, outputs: list[str], cwd: Path | None, events: list[dict], bg_task_index: dict[str, int]) -> None:
	cmd = str(cargs.get('CommandLine') or '').strip()
	if cmd:
		matched = [outputs[c_pos]] if c_pos < len(outputs) else outputs
		ev = build_command_tdd_event(step_idx, cmd, matched, cwd=cwd)
		bg_tid = ev['outcome'].get('background_task_id')
		if bg_tid:
			bg_task_index[bg_tid] = len(events)
		events.append(ev)
def _append_write_tool_event(step_idx: int, cname: str, cargs: dict, cwd: Path | None, events: list[dict]) -> None:
	raw_p = str(cargs.get('Path') or cargs.get('TargetFile') or cargs.get('AbsolutePath') or cargs.get('path') or '').strip()
	if raw_p:
		content_hint = cargs.get('Content') if 'write_file' == cname else None
		ev = build_file_write_tdd_event(step_idx, raw_p, cwd=cwd, content=content_hint if isinstance(content_hint, str) else None)
		if 'non_code' != ev['classification']:
			events.append(ev)
def _collect_following_outputs(rows: list[dict], pos: int) -> list[str]:
	r: list[str] = []
	for nxt in rows[pos + 1:]:
		if isinstance(nxt, dict):
			if nxt.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
				break
			if 'GENERIC' == nxt.get('type') and nxt.get('content'):
				r.append(str(nxt.get('content')))
	return r
def _extract_row_call_events(step_idx: int, calls: list[dict], outputs: list[str], cwd: Path | None, events: list[dict], bg_task_index: dict[str, int]) -> None:
	for c_pos, call in enumerate(calls):
		cname = str(call.get('name') or '')
		cargs = _normalize_args_dict(call.get('args', {}))
		if cname in _WRITE_TOOL_NAMES:
			matched = [outputs[c_pos]] if c_pos < len(outputs) else outputs
			if not is_denied_write_output(matched):
				_append_write_tool_event(step_idx, cname, cargs, cwd, events)
		elif 'run_command' == cname:
			_append_command_tool_event(step_idx, c_pos, cargs, outputs, cwd, events, bg_task_index)
def _is_git_commit_command(cmd: str, *, cwd: Path | None=None) -> tuple[bool, Path | None]:
	r: tuple[bool, Path | None] = (False, None)
	if isinstance(cmd, str) and 'git' in cmd.lower():
		from ..git_gate import resolve_git_repo_from_argv
		from ..shell_audit import _iter_shell_git_segments
		for _, tokens in _iter_shell_git_segments(cmd):
			sub, _ = classify_git_argv(tokens)
			if 'commit' == sub:
				r = (True, resolve_git_repo_from_argv(tokens, cwd=cwd))
				break
		if (not r[0]) and _SAFE_COMMIT_EXEC_RE.search(cmd):
			m_repo = _SAFE_COMMIT_REPO_RE.search(cmd)
			raw_r = (m_repo.group(1) or m_repo.group(2) or m_repo.group(3)) if m_repo else None
			repo = normalize_host_path(raw_r).resolve() if raw_r else (Path(cwd).resolve() if cwd else None)
			r = (True, repo)
	return r
def _load_transcript_rows(transcript_path: Path) -> list[dict]:
	t_path = Path(transcript_path)
	if 'transcript.jsonl' == t_path.name:
		full_sib = t_path.parent / 'transcript_full.jsonl'
		if full_sib.is_file():
			t_path = full_sib
	r: list[dict] = []
	if t_path.is_file():
		try:
			r = [json.loads(line) for line in t_path.read_text(encoding='utf-8', errors='replace').splitlines() if line.strip()]
		except (OSError, ValueError):
			r = []
	return r
def _normalize_args_dict(raw_args) -> dict:
	parsed = raw_args
	if isinstance(parsed, str):
		try:
			parsed = json.loads(parsed)
		except ValueError:
			parsed = None
	return {k: _unwrap_arg_value(v) for k, v in parsed.items()} if isinstance(parsed, dict) else {}
def _record_bg_task_completion(row: dict, events: list[dict], bg_task_index: dict[str, int]) -> None:
	if row.get('type') in ('SYSTEM_MESSAGE', 'EPHEMERAL_MESSAGE', 'GENERIC') and row.get('content'):
		m_fin = _BG_TASK_FINISHED_RE.search(str(row.get('content')))
		if m_fin:
			fin_tid = m_fin.group(1).strip()
			if fin_tid in bg_task_index:
				events[bg_task_index[fin_tid]]['outcome'] = parse_command_outcome(m_fin.group(2))
def _scan_segment_calls(calls: list[dict], outs: list[str], active_bg: set[str]) -> tuple[int, bool]:
	spawned, prepared = (0, False)
	for c_pos, call in enumerate(calls):
		cname = str(call.get('name') or '')
		cargs = _normalize_args_dict(call.get('args', {}))
		if 'invoke_subagent' == cname:
			spawned += 1
		elif 'run_command' == cname:
			if re.search(r'\banswer-prepare\b', str(cargs.get('CommandLine') or ''), re.I):
				prepared = True
			_track_bg_command_outputs(c_pos, outs, active_bg)
		elif 'manage_task' == cname and 'kill' == str(cargs.get('Action') or '').strip().lower():
			kill_tid = str(cargs.get('TaskId') or '').strip()
			if kill_tid:
				active_bg.discard(kill_tid)
	return (spawned, prepared)
def _scan_segment_status_row(row: dict, active_bg: set[str]) -> int:
	r = 0
	if row.get('type') in ('SYSTEM_MESSAGE', 'EPHEMERAL_MESSAGE', 'GENERIC') and row.get('content'):
		c_str = str(row.get('content'))
		if _SUBAGENT_DONE_RE.search(c_str):
			r = 1
		for m_e in _BG_ENDED_RE.finditer(c_str):
			active_bg.discard(m_e.group(1).strip())
		for m_s in _BG_SENDER_RE.finditer(c_str):
			active_bg.discard(m_s.group(1).strip())
	return r
def _select_active_segment(rows: list[dict]) -> list[dict]:
	user_positions = [idx for idx, row in enumerate(rows) if isinstance(row, dict) and 'USER_INPUT' == row.get('type')]
	if not user_positions:
		r = rows
	else:
		start_pos = user_positions[-1] + 1
		for k in range(len(user_positions) - 2, -1, -1):
			if _antigravity_segment_is_interrupted(rows[user_positions[k] + 1:user_positions[k + 1]]):
				start_pos = user_positions[k] + 1
			else:
				break
		r = rows[start_pos:]
	return r
def _track_bg_command_outputs(c_pos: int, outs: list[str], active_bg: set[str]) -> None:
	matched = [outs[c_pos]] if c_pos < len(outs) else outs
	for out_s in matched:
		active_bg.update(extract_bg_task_ids(out_s))
def _unwrap_arg_value(val):
	r = val
	if isinstance(val, str) and 2 <= len(val) and '"' == val[0] and '"' == val[-1]:
		try:
			parsed = json.loads(val)
			if isinstance(parsed, str):
				r = parsed
		except ValueError:
			pass
	return r
def build_command_tdd_event(step: int, cmd: str, outputs: list[str] | tuple[str, ...] | str, *, cwd: Path | None=None, scope_hint: Path | None=None, sub_step: int | None=None, subagent_id: str | None=None) -> dict:
	eff_cwd = Path(cwd).resolve() if None is not cwd else None
	is_commit, commit_repo = _is_git_commit_command(cmd, cwd=eff_cwd)
	test_info = classify_test_command(cmd, scope_root=scope_hint)
	outcome = parse_command_outcome(outputs)
	ev = {'cmd': str(cmd or ''), 'commit_scope': str(commit_repo) if None is not commit_repo else None, 'cwd': str(eff_cwd) if None is not eff_cwd else '', 'is_git_commit': is_commit, 'kind': 'command', 'outcome': outcome, 'step': int(step), 'test_info': test_info}
	if None is not sub_step:
		ev['sub_step'] = int(sub_step)
	if subagent_id:
		ev['subagent_id'] = str(subagent_id)
	return ev
def build_file_write_tdd_event(step: int, raw_path: str | Path, *, cwd: Path | None=None, content: str | None=None, sub_step: int | None=None, subagent_id: str | None=None) -> dict:
	cand = normalize_host_path(raw_path)
	full = cand.resolve() if cand.is_absolute() else ((Path(cwd).resolve() / cand).resolve() if None is not cwd else cand.resolve())
	cls = classify_code_path(full, content=content)
	scope = resolve_code_scope(full) if 'non_code' != cls else full.parent
	ev = {'classification': cls, 'kind': 'file_write', 'path': str(full), 'scope': str(scope), 'step': int(step)}
	if None is not sub_step:
		ev['sub_step'] = int(sub_step)
	if subagent_id:
		ev['subagent_id'] = str(subagent_id)
	return ev
def is_denied_write_output(outputs) -> bool:
	items = [outputs] if isinstance(outputs, str) else [str(item) for item in (outputs or ()) if item]
	return bool(items) and all((bool(_DENIED_WRITE_OUT_RE.search(item)) for item in items))
def record_tdd_tool_write_event(acc: dict, step: int, raw_path: str | Path, *, cwd: Path | None=None, content: str | None=None, cmd_outputs=None, sub_step: int | None=None, subagent_id: str | None=None) -> dict | None:
	r = None
	if 'tdd_events' in acc and (not is_denied_write_output(cmd_outputs)):
		wev = build_file_write_tdd_event(step, raw_path, cwd=cwd, content=content, sub_step=sub_step, subagent_id=subagent_id)
		if 'non_code' != wev['classification']:
			acc['tdd_events'].append(wev)
			r = wev
	return r
def extract_antigravity_tdd_events(transcript_path: Path, *, cwd: Path | None=None) -> list[dict]:
	rows = _load_transcript_rows(transcript_path)
	segment = _select_active_segment(rows) if rows else []
	events: list[dict] = []
	bg_task_index: dict[str, int] = {}
	for pos, row in enumerate(segment):
		if isinstance(row, dict):
			step_idx = row.get('step_index') if isinstance(row.get('step_index'), int) else pos
			_record_bg_task_completion(row, events, bg_task_index)
			calls = [c for c in (row.get('tool_calls') or ()) if isinstance(c, dict)]
			if calls:
				outputs = _collect_following_outputs(segment, pos)
				_extract_row_call_events(step_idx, calls, outputs, cwd, events, bg_task_index)
	return events
