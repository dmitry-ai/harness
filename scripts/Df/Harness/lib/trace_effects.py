# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from pathlib import Path
from typing import Any
from Df.Harness.lib.trace_common import dfh_iter_antigravity_subagents, dfh_parse_tool_args
from agent_tools.shell_audit import run_shell_violation_scan, unflagged_git_read_commands, unpersisted_http_fetch_commands
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_ACCUMULATOR_INTERNAL_KEYS = ('checkpoint_steps', 'tool_steps', 'subagent_steps', 'aa_subagent_steps', 'aa_partial_read_violations', 'af_subagent_steps', 'kb_persistence_steps', 'completion_service_steps', 'transcript_read_steps', 'tool_records', 'file_reads', 'file_writes')
_KB_PATH_TOKENS = ('\ua616/KB', '\ua616\\KB', '\\ua616/KB', '\\ua616\\\\KB')
_KB_PERSIST_CMD_RE = re.compile('\\b(?:save-analysis|collect|collect-http|collect-browser|extract|extract-file|capture-dom)\\b')
_SCRATCH_PATH_TOKENS = ('\ua616/data/scratch/', '\ua616/data/continuation.md', '\\ua616/data/scratch/', '\\ua616/data/continuation.md')
_SERVICE_CMD_RE = re.compile('\\b(?:turn-begin|answer-check|answer-prepare|evidence-query|prepare-review|review-input|native-review-proof|record-review|disposition-review|authorize|recover-checkpoint|recover-turn-violation|adopt-requests|unadopt-requests|journal-sync|reconcile-unprepared-delivery|native-executor-metadata|validate_links\\.py|df_github_issue\\.py)\\b')
_SHELL_KB_WRITE_RE = re.compile('(?i)\\b(?:Set-Content|Out-File|Add-Content|WriteAllText|WriteAllBytes|write_text|write_bytes|tee)\\b')
_TOKEN_FIELDS = ('input_tokens', 'cache_read_tokens', 'output_tokens')
# @used-by :func:`dfh_summarize_turn_activity()`
def _compute_evicted_unreread(pre_cp_reads: list[str], post_cp_reads: list[str], allow_step_output_recovery: bool) -> list[str]:
	post_cp_lower = {p.lower() for p in post_cp_reads}
	recovered_step_nums = set()
	if allow_step_output_recovery:
		for pr in post_cp_reads:
			m_rec = re.search('(?:/steps/(\\d+)/output\\.txt|/step-(\\d+)\\.txt)$', pr, re.I)
			if m_rec:
				recovered_step_nums.add(m_rec.group(1) or m_rec.group(2))
	evicted = []
	for p in pre_cp_reads:
		if p.lower() in post_cp_lower:
			continue
		if allow_step_output_recovery:
			m_ev = re.search('/\\.system_generated/steps/(\\d+)/output\\.txt$', p, re.I)
			if m_ev and m_ev.group(1) in recovered_step_nums:
				continue
		evicted.append(p)
	return evicted
# @used-by :func:`dfh_summarize_turn_activity()`
def _compute_unpersisted_streaks(t_steps: list, sub_steps: list, kb_steps: list, f_reads: list, svc_steps) -> tuple[int, int, int]:
	reads_by_step: dict[Any, list[str]] = {}
	for st, p in f_reads:
		reads_by_step.setdefault(st, []).append(p)
	cur_streak, max_streak, max_src_reads = (0, 0, 0)
	cur_src_reads: set[str] = set()
	persist_or_sub, svc_set = (set(sub_steps) | set(kb_steps), set(svc_steps or ()))
	for st in t_steps:
		if st in svc_set and st not in persist_or_sub:
			continue
		if st in persist_or_sub:
			cur_streak = 0
			cur_src_reads.clear()
		else:
			cur_streak += 1
			max_streak = max(max_streak, cur_streak)
			cur_src_reads.update((rp.lower() for rp in reads_by_step.get(st, ()) if rp.lower().endswith('/kb/source.md')))
			max_src_reads = max(max_src_reads, len(cur_src_reads))
	return (cur_streak, max_streak, max_src_reads)
# @used-by :func:`dfh_collect_subagent_bfs()`
def _enqueue_bfs_children(queue: list, queued_pairs: set, visited: set, children, depth: int, parent_id: str) -> None:
	for grand_cid in children or ():
		if grand_cid and grand_cid not in visited and (grand_cid, parent_id) not in queued_pairs:
			queued_pairs.add((grand_cid, parent_id))
			queue.append((grand_cid, depth, False, parent_id))
# @used-by :func:`dfh_collect_subagent_bfs()`
def _enqueue_bfs_seeds(seeds, visited: set, queued_pairs: set) -> list:
	queue: list = []
	for seed_cid, seed_hint, seed_parent in seeds or ():
		if seed_cid and seed_cid not in visited and (seed_cid, seed_parent) not in queued_pairs:
			queued_pairs.add((seed_cid, seed_parent))
			queue.append((seed_cid, 1, seed_hint, seed_parent))
	return queue
# @used-by :func:`dfh_summarize_token_records()`
def _format_token_counts(known, unavailable) -> dict:
	return {field: {'known_sum': known[field], 'unreported_records': unavailable[field], 'complete_total': None if unavailable[field] else known[field]} for field in _TOKEN_FIELDS}
# @used-by :func:`_track_kb_and_service_steps()`
def _has_kb_target(text) -> bool:
	s = str(text or '')
	return any((tok in s for tok in _KB_PATH_TOKENS)) or '/kb/analysis.md' in s.replace('\\', '/').lower()
# @used-by :func:`dfh_record_normalized_tool_effects()`
def _record_file_tool_effects(root_p, step_idx, name: str, args: dict, is_read_tool: bool, is_write_tool: bool, target_path: str, acc: dict, *, extra_violation, cmd_outputs, sub_step) -> None:
	dfh_record_canonical_path(root_p, step_idx, target_path, is_read_tool, acc['file_reads'], acc['file_writes'], acc['touched_files'])
	if is_write_tool:
		content_hint = args.get('Content') if name.endswith(('write_file', 'write_to_file')) and isinstance(args.get('Content'), str) else None
		if 'tdd_events' in acc:
			from agent_tools.tdd.events import record_tdd_tool_write_event
			sub_cid = extra_violation.get('subagent_id') if isinstance(extra_violation, dict) else None
			record_tdd_tool_write_event(acc, step_idx, target_path, cwd=root_p, content=content_hint, cmd_outputs=cmd_outputs, sub_step=sub_step, subagent_id=sub_cid)
		if 'issue_first_events' in acc:
			from agent_tools.issue_first_gate import build_code_write_issue_first_event
			wifev = build_code_write_issue_first_event(step_idx, target_path, cwd=root_p, content=content_hint, sub_step=sub_step, cmd_outputs=cmd_outputs)
			if None is not wifev:
				acc['issue_first_events'].append(wifev)
# @used-by :func:`dfh_record_normalized_tool_effects()`
def _record_patch_effects(root_p, step_idx, patch_list: list[str], acc: dict, *, sub_step) -> None:
	for pt in patch_list:
		dfh_record_canonical_path(root_p, step_idx, pt, False, acc['file_reads'], acc['file_writes'], acc['touched_files'])
		if 'tdd_events' in acc:
			from agent_tools.tdd_gate import build_file_write_tdd_event
			pev = build_file_write_tdd_event(step_idx, pt, cwd=root_p)
			if 'non_code' != pev['classification']:
				acc['tdd_events'].append(pev)
		if 'issue_first_events' in acc:
			from agent_tools.issue_first_gate import build_code_write_issue_first_event
			pifev = build_code_write_issue_first_event(step_idx, pt, cwd=root_p, sub_step=sub_step)
			if None is not pifev:
				acc['issue_first_events'].append(pifev)
# @used-by :func:`dfh_record_normalized_tool_effects()`
def _record_shell_effects(root_p, step_idx, name: str, args: dict, scan_text: str, shell_cmd: str, acc: dict, *, extra_violation, cmd_outputs, sub_step, shell_violations_fn) -> dict | None:
	viol_fn = shell_violations_fn if None is not shell_violations_fn else dfh_collect_shell_violations
	run_shell_violation_scan(viol_fn, shell_cmd, step_idx, acc['exec5_violations'], acc['http_fetch_violations'], extra=extra_violation)
	eff_cmd = shell_cmd if name.endswith('run_command') else str(args.get('cmd') or args.get('command') or scan_text)
	raw_cwd = args.get('workdir') or args.get('Cwd')
	eff_cwd = Path(raw_cwd) if isinstance(raw_cwd, str) and raw_cwd.strip() else Path(root_p)
	tdd_ev = _record_shell_tdd(step_idx, eff_cmd, eff_cwd, acc, extra_violation=extra_violation, cmd_outputs=cmd_outputs, sub_step=sub_step)
	_record_shell_issue_first(step_idx, eff_cmd, eff_cwd, acc, cmd_outputs=cmd_outputs, sub_step=sub_step)
	return tdd_ev
# @used-by :func:`_record_shell_effects()`
def _record_shell_issue_first(step_idx, eff_cmd: str, eff_cwd: Path, acc: dict, *, cmd_outputs, sub_step) -> None:
	if 'issue_first_events' in acc:
		from agent_tools.issue_first_gate import build_code_write_issue_first_event, build_issue_action_events
		from agent_tools.tdd_gate import shell_write_targets
		for wt in shell_write_targets(eff_cmd, cwd=eff_cwd):
			ifev = build_code_write_issue_first_event(step_idx, wt, cwd=eff_cwd, sub_step=sub_step, cmd_outputs=cmd_outputs)
			if None is not ifev:
				acc['issue_first_events'].append(ifev)
		if cmd_outputs:
			acc['issue_first_events'].extend(build_issue_action_events(step_idx, eff_cmd, cmd_outputs, sub_step=sub_step))
# @used-by :func:`_record_shell_effects()`
def _record_shell_tdd(step_idx, eff_cmd: str, eff_cwd: Path, acc: dict, *, extra_violation, cmd_outputs, sub_step) -> dict | None:
	r = None
	if 'tdd_events' in acc:
		from agent_tools.tdd.events import build_command_tdd_event, record_tdd_tool_write_event
		from agent_tools.tdd_gate import shell_code_write_targets
		sub_cid = extra_violation.get('subagent_id') if isinstance(extra_violation, dict) else None
		for wt in shell_code_write_targets(eff_cmd, cwd=eff_cwd):
			record_tdd_tool_write_event(acc, step_idx, wt, cwd=eff_cwd, cmd_outputs=cmd_outputs, sub_step=sub_step, subagent_id=sub_cid)
		if eff_cmd.strip():
			r = build_command_tdd_event(step_idx, eff_cmd, cmd_outputs or (), cwd=eff_cwd, sub_step=sub_step, subagent_id=sub_cid)
			acc['tdd_events'].append(r)
	return r
# @used-by :func:`dfh_summarize_token_records()`
def _record_token_usage(totals: Counter, missing: Counter, group: dict, src: dict, fmap: dict) -> None:
	for field in _TOKEN_FIELDS:
		value = src.get(fmap[field])
		if int is type(value) and 0 <= value:
			totals[field] += value
			group['known'][field] += value
		else:
			missing[field] += 1
			group['missing'][field] += 1
# @used-by :func:`_track_turn_steps()`
def _track_invoke_subagent(step_idx, name: str, raw_args, acc: dict) -> None:
	if 'spawned_subagents' in acc:
		acc['spawned_subagents'] += 1
	if step_idx not in acc['subagent_steps']:
		acc['subagent_steps'].append(step_idx)
	for sub in dfh_iter_antigravity_subagents({'name': name, 'args': raw_args}):
		tname = str(sub.get('TypeName') or '').strip().lower()
		target_steps = acc['aa_subagent_steps'] if 'self' == tname else (acc['af_subagent_steps'] if tname else None)
		if None is not target_steps and step_idx not in target_steps:
			target_steps.append(step_idx)
# @used-by :func:`_track_turn_steps()`
def _track_kb_and_service_steps(step_idx, scan_text: str, target_path: str, patch_list: list[str], is_shell: bool, is_write_tool: bool, acc: dict) -> None:
	is_kb_persist = (is_write_tool and _has_kb_target(target_path)) or (bool(patch_list) and _has_kb_target('\n'.join(patch_list))) or (is_shell and (bool(_KB_PERSIST_CMD_RE.search(scan_text)) or ('answer-prepare' not in scan_text and bool(_SHELL_KB_WRITE_RE.search(scan_text)) and _has_kb_target(scan_text))))
	if is_kb_persist and step_idx not in acc['kb_persistence_steps']:
		acc['kb_persistence_steps'].append(step_idx)
	is_scratch_write = (is_write_tool and any((tok in target_path.replace('\\', '/') for tok in _SCRATCH_PATH_TOKENS))) or (bool(patch_list) and all((any((tok in pt.replace('\\', '/') for tok in _SCRATCH_PATH_TOKENS)) for pt in patch_list)))
	if ((is_shell and bool(_SERVICE_CMD_RE.search(scan_text))) or is_scratch_write) and step_idx not in acc['completion_service_steps']:
		acc['completion_service_steps'].append(step_idx)
# @used-by :func:`_track_turn_steps()`
def _track_other_subagent(step_idx, name: str, scan_text: str, is_shell: bool, is_file_tool: bool, acc: dict) -> None:
	is_spawn = name.endswith(('spawn_agent', 'invoke_subagent')) or ((not is_file_tool) and (not is_shell) and ('spawn_agent' in scan_text))
	if is_spawn or name.endswith(('send_input', 'send_message', 'wait', 'wait_agent')):
		if step_idx not in acc['subagent_steps']:
			acc['subagent_steps'].append(step_idx)
		if is_spawn:
			sub_bucket = acc['af_subagent_steps'] if re.search('(?i)"(?:task_name|agent_type|role)"\\s*:\\s*"[^"]*\\baf\\b', scan_text) else acc['aa_subagent_steps']
			if step_idx not in sub_bucket:
				sub_bucket.append(step_idx)
# @used-by :func:`dfh_record_normalized_tool_effects()`
def _track_turn_steps(step_idx, name: str, raw_args, scan_text: str, shell_cmd: str, target_path: str, patch_list: list[str], is_shell: bool, is_file_tool: bool, is_write_tool: bool, acc: dict, transcript_tokens) -> None:
	if is_shell and 'answer_prepared_in_segment' in acc and re.search('\\banswer-prepare\\b', shell_cmd):
		acc['answer_prepared_in_segment'] = True
	t_tokens = ('transcript_full.jsonl', 'transcript.jsonl') + tuple(transcript_tokens or ())
	is_real_recover = 'recover-checkpoint' in scan_text and (not re.search('--dry-run\\b', scan_text))
	if (is_real_recover or any((tok in scan_text for tok in t_tokens))) and step_idx not in acc['transcript_read_steps']:
		acc['transcript_read_steps'].append(step_idx)
	if 'invoke_subagent' == name:
		_track_invoke_subagent(step_idx, name, raw_args, acc)
	else:
		_track_other_subagent(step_idx, name, scan_text, is_shell, is_file_tool, acc)
	_track_kb_and_service_steps(step_idx, scan_text, target_path, patch_list, is_shell, is_write_tool, acc)
# @used-by :func:`_record_shell_effects()`
# @used-by :func:`agent_tools.platforms.antigravity._ag_ops()`
# @used-by :func:`agent_tools.platforms.codex._cx_ops()`
# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_tdd_and_issue_first_check_skip_shell_violation_scanning()`
def dfh_collect_shell_violations(cmd: str, step_idx, exec5_violations: list, http_violations: list, *, extra=None) -> None:
	meta = extra or {}
	bad = unflagged_git_read_commands(cmd)
	if bad:
		exec5_violations.append({'step': step_idx, **meta, 'commands': bad})
	bad_http = unpersisted_http_fetch_commands(cmd)
	if bad_http:
		http_violations.append({'step': step_idx, **meta, 'commands': bad_http})
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__collect_subagent_bfs()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__collect_subagent_bfs()`
def dfh_collect_subagent_bfs(root_id: str, root_p: Path, seeds, resolve_child, aa_violations: list, *, max_depth: int=4) -> set[str]:
	from Df.Harness.lib.trace_review import dfh_partial_candidate_read_issues
	r = {root_id}
	queued_pairs: set = set()
	queue = _enqueue_bfs_seeds(seeds, r, queued_pairs)
	while queue:
		child_cid, depth, hint, expected_parent = queue.pop(0)
		if child_cid in r or depth > max_depth:
			continue
		resolved = resolve_child(child_cid, depth, hint, expected_parent)
		if None is resolved:
			continue
		r.add(child_cid)
		c_rows, is_aa, pre_children, on_visit = resolved
		_enqueue_bfs_children(queue, queued_pairs, r, pre_children, depth + 1, child_cid)
		if is_aa:
			aa_violations.extend((e for e in dfh_partial_candidate_read_issues(root_p, c_rows) if e not in aa_violations))
		extra_children = on_visit(child_cid, c_rows) if None is not on_visit else ()
		_enqueue_bfs_children(queue, queued_pairs, r, extra_children, depth + 1, child_cid)
	return r
# @used-by :func:`Df.Harness.lib.completion_child_trace.dfh_scan_child_trace_turn()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__scan_segment()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__start_turn()`
# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_trace_effects_review_and_clarifications()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_denied_write_tool_call_is_excluded_from_tdd_events()`
# @used-by :meth:`test_tdd_worktree_land_green.TddWorktreeLandGreenTests.test_antigravity_scanners_forward_untruncated_output_to_tdd_while_capping_tool_records()`
# @used-by :meth:`test_turn_completion.TraceCommonTests.test_iter_antigravity_subagents_and_kb_persistence_parity()`
def dfh_init_turn_accumulator(*, extra=None) -> dict:
	return {'aa_partial_read_violations': [], 'aa_subagent_steps': [], 'af_subagent_steps': [], 'checkpoint_steps': [], 'completion_service_steps': [], 'exec5_violations': [], 'file_reads': [], 'file_writes': [], 'http_fetch_violations': [], 'issue_first_events': [], 'kb_persistence_steps': [], 'subagent_steps': [], 'tdd_events': [], 'tool_records': [], 'tool_steps': [], 'touched_files': [], 'transcript_read_steps': [], **(extra or {})}
# @used-by :func:`Df.Harness.lib.completion_child_trace.dfh_scan_child_trace_turn()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__merge_pending()`
def dfh_merge_turn_accumulators(items: list[dict], *, allow_step_output_recovery: bool=False) -> dict:
	first, last = (items[0], items[-1])
	flat = lambda k: [x for it in items for x in it.get(k, [])]
	uniq = lambda k: list(dict.fromkeys(flat(k)))
	compaction, delegation = dfh_summarize_turn_activity(flat('checkpoint_steps'), flat('tool_steps'), flat('subagent_steps'), flat('aa_subagent_steps'), flat('af_subagent_steps'), flat('kb_persistence_steps'), flat('transcript_read_steps'), flat('tool_records'), flat('file_reads'), flat('file_writes'), svc_steps=set(flat('completion_service_steps')), aa_part_errs=uniq('aa_partial_read_violations'), allow_step_output_recovery=allow_step_output_recovery)
	r = {**last, 'turn_id': first['turn_id'], 'start_step': first['start_step'], 'requests': flat('requests'), 'owned': all((it['owned'] for it in items)), 'exec5_violations': flat('exec5_violations'), 'http_fetch_violations': flat('http_fetch_violations'), 'touched_files': uniq('touched_files'), 'issue_actions': flat('issue_actions'), 'issue_first_events': flat('issue_first_events'), 'tdd_events': flat('tdd_events'), 'compaction': compaction, 'delegation': delegation}
	for k in _ACCUMULATOR_INTERNAL_KEYS:
		r.pop(k, None)
	return r
# @used-by :func:`_record_file_tool_effects()`
# @used-by :func:`_record_patch_effects()`
def dfh_record_canonical_path(root_p, step_idx, raw_path, is_read: bool, file_reads: list, file_writes: list, touched_files: list) -> None:
	cleaned = str(raw_path or '').strip()
	if cleaned:
		try:
			p_obj = Path(cleaned)
			norm_p = (p_obj.resolve() if p_obj.is_absolute() else (Path(root_p) / p_obj).resolve()).as_posix()
		except OSError:
			norm_p = cleaned.replace('\\', '/')
		if is_read:
			file_reads.append((step_idx, norm_p))
		else:
			if cleaned not in touched_files:
				touched_files.append(cleaned)
			file_writes.append((step_idx, norm_p))
# @used-by :func:`Df.Harness.lib.completion_child_trace._handle_child_call_item()`
# @used-by :func:`Df.Harness.lib.completion_child_trace._process_tool_calls_row()`
# @used-by :func:`agent_tools.platforms.trace_common.record_normalized_tool_effects()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__record_one_tool_call()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__record_subagent_tool_calls()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_subagent_call()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__handle_tool_call_row()`
# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_trace_effects_review_and_clarifications()`
def dfh_record_normalized_tool_effects(root_p, step_idx, name: str, raw_args, raw_cmd, acc: dict, *, extra_violation=None, track_turn_steps: bool=False, transcript_tokens=(), cmd_outputs=None, sub_step=None, shell_violations_fn=None) -> dict | None:
	args = raw_args if isinstance(raw_args, dict) else dfh_parse_tool_args(raw_args)
	scan_text = str(raw_cmd or '')
	is_shell = 'exec' == name or name.endswith(('exec_command', 'run_command'))
	shell_cmd = str(args.get('CommandLine') or '') if name.endswith('run_command') else scan_text
	tdd_cmd_event = _record_shell_effects(root_p, step_idx, name, args, scan_text, shell_cmd, acc, extra_violation=extra_violation, cmd_outputs=cmd_outputs, sub_step=sub_step, shell_violations_fn=shell_violations_fn) if is_shell else None
	patch_list = re.findall('^\\*\\*\\* (?:Add|Update|Delete) File:\\s*(.+)$', scan_text, flags=re.M) if 'apply_patch' in name else []
	_record_patch_effects(root_p, step_idx, patch_list, acc, sub_step=sub_step)
	is_read_tool = name.endswith(('read_file', 'view_file'))
	is_write_tool = name.endswith(('write_file', 'edit_file', 'write_to_file', 'replace_file_content', 'multi_replace_file_content'))
	is_file_tool = is_read_tool or is_write_tool
	target_path = str(args.get('Path') or args.get('TargetFile') or args.get('AbsolutePath') or args.get('path') or '').strip() if is_file_tool else ''
	if target_path:
		_record_file_tool_effects(root_p, step_idx, name, args, is_read_tool, is_write_tool, target_path, acc, extra_violation=extra_violation, cmd_outputs=cmd_outputs, sub_step=sub_step)
	if track_turn_steps:
		_track_turn_steps(step_idx, name, raw_args, scan_text, shell_cmd, target_path, patch_list, is_shell, is_file_tool, is_write_tool, acc, transcript_tokens)
	return tdd_cmd_event
# @used-by :meth:`Df.Harness.Meta.MetricsSummarizer.MetricsSummarizer.__summarize_ag_paths()`
# @used-by :meth:`Df.Harness.Platform.Codex.TokenSummarizer.TokenSummarizer.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_platform_cov.DfHarnessS11Wave2dPlatformCovTests.test_trace_effects_review_and_clarifications()`
def dfh_summarize_token_records(events, bindings=None, *, extra=None, field_map=None, prefix=None, tools=None) -> dict:
	totals, missing = (Counter(), Counter())
	generations, duplicates, phases = (0, 0, {})
	fmap = field_map or {field: field for field in _TOKEN_FIELDS}
	for event in events:
		if 'duplicate' == event[0]:
			duplicates += 1
			continue
		_, owner, step_idx, usage = event
		generations += 1
		stage = next((part['stage'] for part in (bindings or {}).get(owner, []) if part['first_step'] <= step_idx <= part['last_step']), 'unassigned')
		group = phases.setdefault(stage, {'known': Counter(), 'missing': Counter(), 'generations': 0})
		group['generations'] += 1
		_record_token_usage(totals, missing, group, usage if isinstance(usage, dict) else {}, fmap)
	return {**(prefix or {}), 'generations': generations, 'duplicate_records_ignored': duplicates, 'tokens': _format_token_counts(totals, missing), 'tools': dict(tools or {}), 'phases': {stage: {'generations': g['generations'], 'tokens': _format_token_counts(g['known'], g['missing'])} for stage, g in phases.items()}, **(extra or {})}
# @used-by :func:`dfh_merge_turn_accumulators()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__finalize_turn()`
def dfh_summarize_turn_activity(cp_steps, t_steps, sub_steps, aa_steps, af_steps, kb_steps, tr_steps, records, f_reads, f_writes, *, svc_steps=(), aa_part_errs=None, allow_step_output_recovery: bool=False) -> tuple[dict, dict]:
	last_cp = max(cp_steps) if cp_steps else None
	pre_cp_steps = [s for s in t_steps if None is not last_cp and s < last_cp]
	post_cp_rec = [s for s in tr_steps if None is not last_cp and s > last_cp]
	pre_cp_records = [rec for rec in records if None is not last_cp and rec['step'] < last_cp]
	pre_cp_reads = list(dict.fromkeys((p for st, p in f_reads if None is not last_cp and st < last_cp)))
	post_cp_reads = list(dict.fromkeys((p for st, p in f_reads if None is not last_cp and st > last_cp)))
	post_cp_writes = list(dict.fromkeys((p for st, p in f_writes if None is not last_cp and st > last_cp)))
	evicted = _compute_evicted_unreread(pre_cp_reads, post_cp_reads, allow_step_output_recovery)
	cur_streak, max_streak, max_src_reads = _compute_unpersisted_streaks(t_steps, sub_steps, kb_steps, f_reads, svc_steps)
	comp = {'occurred': bool(cp_steps), 'checkpoint_steps': cp_steps, 'last_checkpoint_step': last_cp, 'pre_checkpoint_tool_steps': pre_cp_steps, 'post_checkpoint_recovery_steps': post_cp_rec, 'recovered_in_trace': not cp_steps or (not pre_cp_steps) or bool(post_cp_rec), 'pre_checkpoint_records': pre_cp_records, 'pre_checkpoint_read_files': pre_cp_reads, 'post_checkpoint_read_files': post_cp_reads, 'post_checkpoint_written_files': post_cp_writes, 'evicted_unreread_files': evicted}
	deleg = {'tool_step_count': len(t_steps), 'subagent_step_count': len(sub_steps), 'aa_subagent_step_count': len(aa_steps), 'aa_partial_read_violations': list(aa_part_errs or []), 'af_subagent_step_count': len(af_steps), 'kb_persistence_step_count': len(kb_steps), 'unpersisted_step_streak': cur_streak, 'max_unpersisted_step_streak': max_streak, 'max_unpersisted_source_reads': max_src_reads}
	return (comp, deleg)
