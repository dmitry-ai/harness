# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from ..shell_audit import classify_git_argv, normalize_host_path
from .classifier import classify_code_path, resolve_code_scope
from .commands import classify_test_command
# 2026-11-24
# "Preserve multi-turn handed-off Stop Gate routing and stateful loop guard":
# https://github.com/dmitry-ai/harness/issues/224
from .outcomes import _BG_TASK_FINISHED_RE, _BG_TASK_ID_RE, extract_bg_task_ids, parse_command_outcome
import json
import re
_BG_ENDED_RE = re.compile(r'Task\s+id\s+"([^"]+)"\s+(?:finished|canceled|cancelled|terminated|killed)\b', re.IGNORECASE)
_BG_SENDER_RE = re.compile(r'\bsender=([A-Za-z0-9_./:-]+/task-\d+)\b', re.IGNORECASE)
# 2026-11-24
# "Fix EXEC-2 TDD trace scoping for deleted worktrees and subagent steps":
# https://github.com/dmitry-ai/harness/issues/173
_DENIED_WRITE_OUT_RE = re.compile(r'Encountered error in (?:tool|step) execution:|tool call denied by pre-tool hook:', re.IGNORECASE)
_SAFE_COMMIT_EXEC_RE = re.compile(r'\bsafe_commit\.py\b[^\r\n]*--execute\b')
_SAFE_COMMIT_REPO_RE = re.compile(r'--repo\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))')
_SUBAGENT_DONE_RE = re.compile(r'<SYSTEM_MESSAGE>.*(?:\bSubagent\b.*\bcompleted\b|\[Message\]\s+timestamp=[^\n]+\bsender=[0-9a-f]{8}-[0-9a-f]{4}-)', re.S | re.I)
_WRITE_TOOL_NAMES = frozenset({'edit_file', 'multi_replace_file_content', 'replace_file_content', 'write_file', 'write_to_file'})
# @used-by :func:`_select_active_segment()`
# @used-by :meth:`test_multiturn_handoff_stop_guard_and_schedule_m1.MultiturnHandoffStopGuardAndScheduleM1Tests.test_schedule_timers_and_stdout_prose_do_not_merge_completed_turn1_into_turn2()`
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
# @used-by :func:`_extract_row_call_events()`
def _append_command_tool_event(step_idx: int, c_pos: int, cargs: dict, outputs: list[str], cwd: Path | None, events: list[dict], bg_task_index: dict[str, int]) -> None:
	cmd = str(cargs.get('CommandLine') or '').strip()
	if cmd:
		matched = [outputs[c_pos]] if c_pos < len(outputs) else outputs
		ev = build_command_tdd_event(step_idx, cmd, matched, cwd=cwd)
		bg_tid = ev['outcome'].get('background_task_id')
		if bg_tid:
			bg_task_index[bg_tid] = len(events)
		events.append(ev)
# @used-by :func:`_extract_row_call_events()`
def _append_write_tool_event(step_idx: int, cname: str, cargs: dict, cwd: Path | None, events: list[dict]) -> None:
	raw_p = str(cargs.get('Path') or cargs.get('TargetFile') or cargs.get('AbsolutePath') or cargs.get('path') or '').strip()
	if raw_p:
		content_hint = cargs.get('Content') if 'write_file' == cname else None
		ev = build_file_write_tdd_event(step_idx, raw_p, cwd=cwd, content=content_hint if isinstance(content_hint, str) else None)
		if 'non_code' != ev['classification']:
			events.append(ev)
# @used-by :func:`_antigravity_segment_is_interrupted()`
# @used-by :func:`extract_antigravity_tdd_events()`
def _collect_following_outputs(rows: list[dict], pos: int) -> list[str]:
	r: list[str] = []
	for nxt in rows[pos + 1:]:
		if isinstance(nxt, dict):
			if nxt.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
				break
			if 'GENERIC' == nxt.get('type') and nxt.get('content'):
				r.append(str(nxt.get('content')))
	return r
# @used-by :func:`extract_antigravity_tdd_events()`
def _extract_row_call_events(step_idx: int, calls: list[dict], outputs: list[str], cwd: Path | None, events: list[dict], bg_task_index: dict[str, int]) -> None:
	for c_pos, call in enumerate(calls):
		cname = str(call.get('name') or '')
		cargs = _normalize_args_dict(call.get('args', {}))
		if cname in _WRITE_TOOL_NAMES:
			# 2026-11-24
			# "Fix EXEC-2 TDD trace scoping for deleted worktrees and subagent steps":
			# https://github.com/dmitry-ai/harness/issues/173
			matched = [outputs[c_pos]] if c_pos < len(outputs) else outputs
			if not is_denied_write_output(matched):
				_append_write_tool_event(step_idx, cname, cargs, cwd, events)
		elif 'run_command' == cname:
			_append_command_tool_event(step_idx, c_pos, cargs, outputs, cwd, events, bg_task_index)
# @used-by :func:`build_command_tdd_event()`
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
# @used-by :func:`extract_antigravity_tdd_events()`
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
# @used-by :func:`_extract_row_call_events()`
# @used-by :func:`_scan_segment_calls()`
# @used-by :func:`agent_tools.issue_first_bg._dispatch_segment_call()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_events_module_behavior_and_parity()`
def _normalize_args_dict(raw_args) -> dict:
	parsed = raw_args
	if isinstance(parsed, str):
		try:
			parsed = json.loads(parsed)
		except ValueError:
			parsed = None
	return {k: _unwrap_arg_value(v) for k, v in parsed.items()} if isinstance(parsed, dict) else {}
# @used-by :func:`extract_antigravity_tdd_events()`
def _record_bg_task_completion(row: dict, events: list[dict], bg_task_index: dict[str, int]) -> None:
	if row.get('type') in ('SYSTEM_MESSAGE', 'EPHEMERAL_MESSAGE', 'GENERIC') and row.get('content'):
		m_fin = _BG_TASK_FINISHED_RE.search(str(row.get('content')))
		if m_fin:
			fin_tid = m_fin.group(1).strip()
			if fin_tid in bg_task_index:
				events[bg_task_index[fin_tid]]['outcome'] = parse_command_outcome(m_fin.group(2))
# @used-by :func:`_antigravity_segment_is_interrupted()`
def _scan_segment_calls(calls: list[dict], outs: list[str], active_bg: set[str]) -> tuple[int, bool]:
	spawned, prepared = (0, False)
	for c_pos, call in enumerate(calls):
		cname = str(call.get('name') or '')
		cargs = _normalize_args_dict(call.get('args', {}))
		if 'invoke_subagent' == cname:
			spawned += 1
		# 2026-11-24
		# "Preserve multi-turn handed-off Stop Gate routing and stateful loop guard":
		# https://github.com/dmitry-ai/harness/issues/224
		elif 'run_command' == cname:
			if re.search(r'\banswer-prepare\b', str(cargs.get('CommandLine') or ''), re.I):
				prepared = True
			_track_bg_command_outputs(c_pos, outs, active_bg)
		elif 'manage_task' == cname and 'kill' == str(cargs.get('Action') or '').strip().lower():
			kill_tid = str(cargs.get('TaskId') or '').strip()
			if kill_tid:
				active_bg.discard(kill_tid)
	return (spawned, prepared)
# @used-by :func:`_antigravity_segment_is_interrupted()`
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
# @used-by :func:`extract_antigravity_tdd_events()`
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
# @used-by :func:`_scan_segment_calls()`
def _track_bg_command_outputs(c_pos: int, outs: list[str], active_bg: set[str]) -> None:
	matched = [outs[c_pos]] if c_pos < len(outs) else outs
	for out_s in matched:
		# 2026-11-24
		# "Preserve multi-turn handed-off Stop Gate routing and stateful loop guard":
		# https://github.com/dmitry-ai/harness/issues/224
		active_bg.update(extract_bg_task_ids(out_s))
# @used-by :func:`_normalize_args_dict()`
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
# @used-by :func:`_append_command_tool_event()`
# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_parallel_deleted_worktrees_isolate_tdd_scopes_and_accept_main_full_green()`
# @used-by :meth:`test_failfast_and_schedule_gate.FailFastAndScheduleGateTests.test_tdd_gate_records_non_failfast_full_suite_warning_without_breaking_verified()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_classify_test_command_recognizes_harness_run_tests_full_and_filtered()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_linked_worktree_scope_accepts_full_suite_green_on_main_repo()`
# @used-by :meth:`test_pytest_xdist_runner.PytestXdistRunnerTests.test_tdd_state_machine_rejects_exit_5_red_and_accepts_xdist_full_green()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_evaluator_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_lazy_exemption_and_full_green_edge_cases()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_memoizes_exemption_and_allows_exempt_only_edits()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_combined_git_commit_and_full_test_command_updates_full_green()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_subagent_events_sharing_parent_step_preserve_sub_step_order()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def build_command_tdd_event(step: int, cmd: str, outputs: list[str] | tuple[str, ...] | str, *, cwd: Path | None=None, scope_hint: Path | None=None, sub_step: int | None=None, subagent_id: str | None=None) -> dict:
	eff_cwd = Path(cwd).resolve() if None is not cwd else None
	is_commit, commit_repo = _is_git_commit_command(cmd, cwd=eff_cwd)
	test_info = classify_test_command(cmd, scope_root=scope_hint)
	outcome = parse_command_outcome(outputs)
	ev = {'cmd': str(cmd or ''), 'commit_scope': str(commit_repo) if None is not commit_repo else None, 'cwd': str(eff_cwd) if None is not eff_cwd else '', 'is_git_commit': is_commit, 'kind': 'command', 'outcome': outcome, 'step': int(step), 'test_info': test_info}
	# 2026-11-24
	# "Fix EXEC-2 TDD trace scoping for deleted worktrees and subagent steps":
	# https://github.com/dmitry-ai/harness/issues/173
	if None is not sub_step:
		ev['sub_step'] = int(sub_step)
	if subagent_id:
		ev['subagent_id'] = str(subagent_id)
	return ev
# @used-by :func:`_append_write_tool_event()`
# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
# @used-by :func:`record_tdd_tool_write_event()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_missing_transcript_inheritance_and_plain_repo_commit_scope_reset()`
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_parallel_deleted_worktrees_isolate_tdd_scopes_and_accept_main_full_green()`
# @used-by :meth:`test_failfast_and_schedule_gate.FailFastAndScheduleGateTests.test_tdd_gate_records_non_failfast_full_suite_warning_without_breaking_verified()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_classify_test_command_recognizes_harness_run_tests_full_and_filtered()`
# @used-by :meth:`test_parallel_test_runner.ParallelTestRunnerTests.test_linked_worktree_scope_accepts_full_suite_green_on_main_repo()`
# @used-by :meth:`test_pytest_xdist_runner.PytestXdistRunnerTests.test_tdd_state_machine_rejects_exit_5_red_and_accepts_xdist_full_green()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_evaluator_skips_tdd_red_and_full_gates_for_comment_only_write()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_evaluator_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_lazy_exemption_and_full_green_edge_cases()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_memoizes_exemption_and_allows_exempt_only_edits()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_auditor_and_evaluator_accept_committed_mechanical_diff_and_reject_drift()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_combined_git_commit_and_full_test_command_updates_full_green()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_subagent_events_sharing_parent_step_preserve_sub_step_order()`
# @used-by :meth:`test_worktree_comment_exemption.WorktreeCommentExemptionTests.test_deleted_sibling_and_nested_worktree_comment_only_commits_are_exempt()`
# @used-by :meth:`test_worktree_comment_exemption.WorktreeCommentExemptionTests.test_deleted_worktree_non_comment_code_commit_remains_blocked()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def build_file_write_tdd_event(step: int, raw_path: str | Path, *, cwd: Path | None=None, content: str | None=None, sub_step: int | None=None, subagent_id: str | None=None) -> dict:
	cand = normalize_host_path(raw_path)
	full = cand.resolve() if cand.is_absolute() else ((Path(cwd).resolve() / cand).resolve() if None is not cwd else cand.resolve())
	cls = classify_code_path(full, content=content)
	scope = resolve_code_scope(full) if 'non_code' != cls else full.parent
	ev = {'classification': cls, 'kind': 'file_write', 'path': str(full), 'scope': str(scope), 'step': int(step)}
	# 2026-11-24
	# "Fix EXEC-2 TDD trace scoping for deleted worktrees and subagent steps":
	# https://github.com/dmitry-ai/harness/issues/173
	if None is not sub_step:
		ev['sub_step'] = int(sub_step)
	if subagent_id:
		ev['subagent_id'] = str(subagent_id)
	return ev
# 2026-11-24
# "Fix EXEC-2 TDD trace scoping for deleted worktrees and subagent steps":
# https://github.com/dmitry-ai/harness/issues/173
# @used-by :func:`_extract_row_call_events()`
# @used-by :func:`agent_tools.issue_first_gate.build_code_write_issue_first_event()`
# @used-by :func:`record_tdd_tool_write_event()`
def is_denied_write_output(outputs) -> bool:
	items = [outputs] if isinstance(outputs, str) else [str(item) for item in (outputs or ()) if item]
	return bool(items) and all((bool(_DENIED_WRITE_OUT_RE.search(item)) for item in items))
# 2026-11-24
# "Fix EXEC-2 TDD trace scoping for deleted worktrees and subagent steps":
# https://github.com/dmitry-ai/harness/issues/173
# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
def record_tdd_tool_write_event(acc: dict, step: int, raw_path: str | Path, *, cwd: Path | None=None, content: str | None=None, cmd_outputs=None, sub_step: int | None=None, subagent_id: str | None=None) -> dict | None:
	r = None
	if 'tdd_events' in acc and (not is_denied_write_output(cmd_outputs)):
		wev = build_file_write_tdd_event(step, raw_path, cwd=cwd, content=content, sub_step=sub_step, subagent_id=subagent_id)
		if 'non_code' != wev['classification']:
			acc['tdd_events'].append(wev)
			r = wev
	return r
# 2026-11-24
# "Decompose tdd_gate.py into modular TDD verification package":
# https://github.com/dmitry-ai/harness/issues/169
# @used-by :func:`agent_tools.tdd.enforcement._load_pre_tool_tdd_state()`
# @used-by :meth:`test_background_wait_and_tdd_inheritance.BackgroundWaitAndTddInheritanceTests.test_completed_prior_turn_does_not_bleed_tdd_events_into_unrelated_followup()`
# @used-by :meth:`test_background_wait_and_tdd_inheritance.BackgroundWaitAndTddInheritanceTests.test_unfinished_background_run_command_and_russian_stub_merge_and_preserve_tdd_full_gate()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_events_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_extract_antigravity_tdd_events_handles_compact_and_full_transcripts()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_denied_write_tool_call_is_excluded_from_tdd_events()`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
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
