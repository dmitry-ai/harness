# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
from .shell_audit import _split_shell_segments, extract_issue_actions_from_outputs
from .tdd.events import _normalize_args_dict
from .tdd.outcomes import _BG_TASK_FINISHED_RE, _BG_TASK_LOG_RE, _uri_to_local_path, extract_bg_task_ids
from .tdd_gate import shell_write_targets
_DF_ISSUE_VAR_RE = re.compile(r'(\$[A-Za-z_][A-Za-z0-9_]*)\s*=\s*["\'][^"\']*df_github_issue\.py["\']', re.I)
_PY_INLINE_C_RE = re.compile(r'(?i)\bpython(?:3(?:\.\d+)?)?(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*-c\b')
_WRITE_TOOLS = frozenset({'edit_file', 'multi_replace_file_content', 'replace_file_content', 'write_file', 'write_to_file'})
def _bg_fin_outputs(fin_body: str, log_path: str | None) -> list[str]:
	r = [fin_body]
	m_log = _BG_TASK_LOG_RE.search(fin_body)
	cand = _uri_to_local_path(m_log.group(1)) if m_log else (Path(log_path) if log_path else None)
	if None is not cand and cand.is_file():
		try:
			r.append(cand.read_text(encoding='utf-8', errors='replace'))
		except OSError:
			pass
	return r
def _collect_row_outputs(segment: list[dict], pos: int) -> list[str]:
	r: list[str] = []
	for nxt in segment[pos + 1:]:
		if not isinstance(nxt, dict):
			continue
		if nxt.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
			break
		if 'GENERIC' == nxt.get('type') and nxt.get('content'):
			r.append(str(nxt.get('content')))
	return r
def _dispatch_row_calls(segment: list[dict], pos: int, step_idx: int, raw_calls: list, cwd: Path | None, events: list[dict], bg_cmds: dict[str, tuple[str, str | None]], build_write_fn, build_action_fn) -> None:
	calls = [c for c in raw_calls if isinstance(c, dict)]
	if calls:
		outputs = _collect_row_outputs(segment, pos)
		for c_pos, call in enumerate(calls):
			matched = [outputs[c_pos]] if c_pos < len(outputs) else outputs
			_dispatch_segment_call(step_idx, c_pos, call, matched, cwd, events, bg_cmds, build_write_fn, build_action_fn)
def _dispatch_segment_call(step_idx: int, c_pos: int, call: dict, matched: list[str], cwd: Path | None, events: list[dict], bg_cmds: dict[str, tuple[str, str | None]], build_write_fn, build_action_fn) -> None:
	cname = str(call.get('name') or '')
	cargs = _normalize_args_dict(call.get('args', {}))
	if cname in _WRITE_TOOLS:
		_handle_write_call(step_idx, c_pos, cname, cargs, matched, cwd, events, build_write_fn)
	elif 'run_command' == cname:
		_handle_run_command_call(step_idx, c_pos, cargs, matched, cwd, events, bg_cmds, build_write_fn, build_action_fn)
def _handle_run_command_call(step_idx: int, c_pos: int, cargs: dict, matched: list[str], cwd: Path | None, events: list[dict], bg_cmds: dict[str, tuple[str, str | None]], build_write_fn, build_action_fn) -> None:
	cmd = str(cargs.get('CommandLine') or '')
	for wt in shell_write_targets(cmd, cwd=cwd):
		ev = build_write_fn(step_idx, wt, cwd=cwd, sub_step=c_pos, cmd_outputs=matched)
		if None is not ev:
			events.append(ev)
	events.extend(build_action_fn(step_idx, cmd, matched, sub_step=c_pos))
	_register_bg_issue_tasks(cmd, matched, bg_cmds)
def _handle_write_call(step_idx: int, c_pos: int, cname: str, cargs: dict, matched: list[str], cwd: Path | None, events: list[dict], build_write_fn) -> None:
	raw_p = str(next((cargs[k] for k in ('Path', 'TargetFile', 'AbsolutePath', 'path') if cargs.get(k)), '')).strip()
	if raw_p:
		raw_c = cargs.get('Content') if 'write_file' == cname else None
		ev = build_write_fn(step_idx, raw_p, cwd=cwd, content=raw_c if isinstance(raw_c, str) else None, sub_step=c_pos, cmd_outputs=matched)
		if None is not ev:
			events.append(ev)
def _has_direct_issue_seg(segs: list[str], direct_re) -> bool:
	return any((direct_re.match(s) and (not _PY_INLINE_C_RE.search(s)) for s in segs))
def _process_segment_row(segment: list[dict], pos: int, row: dict, cwd: Path | None, events: list[dict], bg_cmds: dict[str, tuple[str, str | None]], build_write_fn, build_action_fn) -> None:
	step_idx = row.get('step_index') if isinstance(row.get('step_index'), int) else pos
	if row.get('type') in ('SYSTEM_MESSAGE', 'EPHEMERAL_MESSAGE', 'GENERIC') and row.get('content'):
		_record_bg_issue_completion(str(row.get('content')), step_idx, bg_cmds, events, build_action_fn)
	if row.get('tool_calls'):
		_dispatch_row_calls(segment, pos, step_idx, row['tool_calls'], cwd, events, bg_cmds, build_write_fn, build_action_fn)
def _record_bg_issue_completion(c_str: str, step_idx: int, bg_cmds: dict[str, tuple[str, str | None]], events: list[dict], build_action_fn) -> None:
	m_fin = _BG_TASK_FINISHED_RE.search(c_str)
	if m_fin:
		entry = bg_cmds.get(m_fin.group(1).strip())
		if None is not entry:
			cmd, log_path = entry
			events.extend(build_action_fn(step_idx, cmd, _bg_fin_outputs(m_fin.group(2), log_path)))
def _record_bg_seg_issues(cev: dict, fin_body: str, prev_log: str | None, step_idx, seg: dict) -> None:
	from .issue_first_gate import build_issue_action_events, is_df_github_issue_command
	cmd = str(cev.get('cmd') or '')
	if is_df_github_issue_command(cmd):
		eff_step = step_idx if isinstance(step_idx, int) else int(cev.get('step', 0))
		outs = _bg_fin_outputs(fin_body, prev_log)
		if 'issue_first_events' in seg:
			seg['issue_first_events'].extend(build_issue_action_events(eff_step, cmd, outs))
		if 'issue_actions' in seg:
			for act in extract_issue_actions_from_outputs(outs):
				seg['issue_actions'].append({**act, 'step': eff_step})
def _register_bg_issue_tasks(cmd: str, matched: list[str], bg_cmds: dict[str, tuple[str, str | None]]) -> None:
	joined = '\n'.join(matched)
	m_log = _BG_TASK_LOG_RE.search(joined)
	lp = _uri_to_local_path(m_log.group(1)) if m_log else None
	lp_str = str(lp) if None is not lp else None
	for tid in extract_bg_task_ids(joined):
		bg_cmds[tid] = (cmd, lp_str)
def _var_issue_matches(cmd: str, segments: list[str]) -> bool:
	r = False
	for vname in _DF_ISSUE_VAR_RE.findall(cmd):
		pat = re.compile(rf'(?i)(?:^|[\s&;])(?:python(?:3(?:\.\d+)?)?(?:\.exe)?\s+(?:-[A-Za-z0-9_]+\s+)*)?["\']?{re.escape(vname)}["\']?\s+(?:create|fetch|edit|comment|close)\b')
		if any((pat.search(s) and (not _PY_INLINE_C_RE.search(s)) for s in segments)):
			r = True
			break
	return r
# 2026-11-26 "Fix comment-only diff and denied-write gate false positives": https://github.com/dmitry-ai/harness/issues/276
def extract_segment_issue_first_events(segment: list[dict], cwd: Path | None, build_write_fn, build_action_fn) -> list[dict]:
	events: list[dict] = []
	bg_cmds: dict[str, tuple[str, str | None]] = {}
	for pos, row in enumerate(segment):
		if isinstance(row, dict):
			_process_segment_row(segment, pos, row, cwd, events, bg_cmds, build_write_fn, build_action_fn)
	return events
def handle_antigravity_bg_task_message(c_str: str, step_idx, seg: dict, parse_command_outcome) -> None:
	m_fin = _BG_TASK_FINISHED_RE.search(c_str)
	if m_fin:
		fin_tid, fin_body = (m_fin.group(1).strip(), m_fin.group(2))
		cev = (seg.get('bg_tdd_index') or {}).get(fin_tid)
		if None is not cev:
			prev_log = (cev.get('outcome') or {}).get('background_log_path')
			cev['outcome'] = parse_command_outcome(fin_body)
			_record_bg_seg_issues(cev, fin_body, prev_log, step_idx, seg)
def is_df_issue_command_text(cmd: str, direct_re) -> bool:
	r = False
	if isinstance(cmd, str) and 'df_github_issue.py' in cmd.lower():
		segs = [seg.strip() for seg in _split_shell_segments(cmd) if seg.strip()]
		r = _has_direct_issue_seg(segs, direct_re) or _var_issue_matches(cmd, segs)
	return r
