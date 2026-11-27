# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.trace_common import dfh_parse_tool_args, dfh_read_jsonl_objects
from Df.Harness.lib.trace_effects import dfh_init_turn_accumulator, dfh_merge_turn_accumulators, dfh_record_normalized_tool_effects
import json
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_process_tool_calls_row()`
def _collect_following_outputs(rows: list, pos: int, step_idx: int, seg: dict) -> list[str]:
	outs: list[str] = []
	for cand in rows[pos + 1:]:
		if not isinstance(cand, dict):
			continue
		if cand.get('type') in ('PLANNER_RESPONSE', 'USER_INPUT', 'CHECKPOINT'):
			break
		if 'GENERIC' == cand.get('type') and cand.get('content'):
			c_str = str(cand.get('content'))
			outs.append(c_str[:4000])
			for m_out in re.finditer('file:///+([A-Za-z]:/[^\\s"\\\'<>`]+?/\\.system_generated/steps/\\d+/output\\.txt)', c_str):
				seg['file_reads'].append((step_idx, m_out.group(1).replace('\\', '/')))
	return outs
# @used-by :func:`_process_response_item_row()`
def _handle_child_call_item(root_p: Path, step_idx: int, pay: dict, seg: dict, pending_tdd: dict, pending_issue: dict) -> None:
	seg['tool_steps'].append(step_idx)
	raw_in = pay.get('arguments', pay.get('input', {}))
	raw_cmd = raw_in if isinstance(raw_in, str) else json.dumps(raw_in, ensure_ascii=False)
	p_name = str(pay.get('name') or '')
	seg['tool_records'].append({'step': step_idx, 'tools': [p_name], 'outputs': []})
	cev = dfh_record_normalized_tool_effects(root_p, step_idx, p_name, raw_in, raw_cmd, seg, track_turn_steps=True)
	if cev and pay.get('call_id'):
		pending_tdd[pay['call_id']] = cev
	if pay.get('call_id') and ('exec' == p_name or p_name.endswith(('exec_command', 'run_command'))):
		from agent_tools.issue_first_gate import is_df_github_issue_command
		cp_args = dfh_parse_tool_args(raw_in)
		ceff_cmd = str(cp_args.get('CommandLine') or cp_args.get('cmd') or cp_args.get('command') or raw_cmd)
		if is_df_github_issue_command(ceff_cmd):
			pending_issue[pay['call_id']] = (step_idx, ceff_cmd)
# @used-by :func:`_process_response_item_row()`
def _handle_child_output_item(pay: dict, seg: dict, pending_tdd: dict, pending_issue: dict, parse_outcome_fn) -> None:
	c_id = pay.get('call_id')
	out_val = pay.get('output')
	out_str = out_val if isinstance(out_val, str) else json.dumps(out_val, ensure_ascii=False)
	if c_id in pending_tdd:
		pending_tdd[c_id]['outcome'] = parse_outcome_fn(out_str)
	if c_id in pending_issue:
		from agent_tools.issue_first_gate import build_issue_action_events
		ci_step, ci_cmd = pending_issue.pop(c_id)
		seg['issue_first_events'].extend(build_issue_action_events(ci_step, ci_cmd, [out_str]))
# @used-by :func:`dfh_scan_child_trace_turn()`
def _process_child_row(root_p: Path, rows: list, pos: int, row: dict, seg: dict, child_bg: dict, pending_tdd: dict, pending_issue: dict, bg_re, parse_outcome_fn) -> None:
	step_idx = row.get('step_index') if isinstance(row.get('step_index'), int) else pos
	if 'CHECKPOINT' == row.get('type') or ('event_msg' == row.get('type') and 'context_compacted' == (row.get('payload') or {}).get('type')):
		seg['checkpoint_steps'].append(step_idx)
	if row.get('type') in ('EPHEMERAL_MESSAGE', 'SYSTEM_MESSAGE', 'GENERIC') and row.get('content'):
		m_fin = bg_re.search(str(row.get('content')))
		if m_fin and m_fin.group(1).strip() in child_bg:
			child_bg[m_fin.group(1).strip()]['outcome'] = parse_outcome_fn(m_fin.group(2))
	calls = [c for c in row.get('tool_calls') or [] if isinstance(c, dict)]
	if calls:
		_process_tool_calls_row(root_p, rows, pos, step_idx, calls, seg, child_bg)
	elif 'response_item' == row.get('type'):
		_process_response_item_row(root_p, step_idx, row, seg, pending_tdd, pending_issue, parse_outcome_fn)
# @used-by :func:`_process_child_row()`
def _process_response_item_row(root_p: Path, step_idx: int, row: dict, seg: dict, pending_tdd: dict, pending_issue: dict, parse_outcome_fn) -> None:
	pay = row.get('payload') if isinstance(row.get('payload'), dict) else {}
	if pay.get('type') in ('function_call_output', 'custom_tool_call_output') and None is not pay.get('output'):
		_handle_child_output_item(pay, seg, pending_tdd, pending_issue, parse_outcome_fn)
	elif pay.get('type') in ('function_call', 'custom_tool_call'):
		_handle_child_call_item(root_p, step_idx, pay, seg, pending_tdd, pending_issue)
# @used-by :func:`_process_child_row()`
def _process_tool_calls_row(root_p: Path, rows: list, pos: int, step_idx: int, calls: list[dict], seg: dict, child_bg: dict) -> None:
	from agent_tools.shell_audit import extract_issue_actions_from_outputs
	outs = _collect_following_outputs(rows, pos, step_idx, seg)
	seg['tool_steps'].append(step_idx)
	seg['tool_records'].append({'step': step_idx, 'tools': [c.get('name', '') for c in calls], 'outputs': outs})
	for act_item in extract_issue_actions_from_outputs(outs):
		seg['issue_actions'].append({**act_item, 'step': step_idx})
	for c_idx, call in enumerate(calls):
		raw_args = call.get('args', {})
		args = dfh_parse_tool_args(raw_args)
		args_text = json.dumps(args, ensure_ascii=False) if args or isinstance(raw_args, dict) else str(raw_args)
		matched = [outs[c_idx]] if c_idx < len(outs) else outs
		cev = dfh_record_normalized_tool_effects(root_p, step_idx, call.get('name', ''), raw_args, args_text, seg, track_turn_steps=True, cmd_outputs=matched)
		if cev and cev.get('outcome', {}).get('background_task_id'):
			child_bg[cev['outcome']['background_task_id']] = cev
# @used-by :func:`Df.Harness.lib.completion_commands._load_check_context()`
# @used-by :func:`Df.Harness.lib.completion_recovery._scan_readonly_turn()`
def dfh_scan_child_trace_turn(root_p: Path, eff_conv: str, native: dict) -> dict:
	if native.get('turns'):
		r = native['turns'][-1]
	else:
		from agent_tools.tdd_gate import _BG_TASK_FINISHED_RE, parse_command_outcome
		seg = dfh_init_turn_accumulator(extra={'turn_id': f'child-{eff_conv}', 'start_step': 0, 'requests': [], 'owned': True, 'issue_actions': []})
		src_raw = str(native.get('source_file') or '').strip()
		src_file = Path(src_raw) if src_raw else None
		rows = []
		if None is not src_file and src_file.is_file():
			try:
				rows = dfh_read_jsonl_objects(src_file)
			except (OSError, ValueError):
				rows = []
		child_bg, pending_tdd, pending_issue = ({}, {}, {})
		for pos, row in enumerate(rows):
			if isinstance(row, dict):
				_process_child_row(root_p, rows, pos, row, seg, child_bg, pending_tdd, pending_issue, _BG_TASK_FINISHED_RE, parse_command_outcome)
		r = dfh_merge_turn_accumulators([seg], allow_step_output_recovery=True)
	return r