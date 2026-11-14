# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose git_gate.py into shell_audit.py, GitRepoGate, and single-pass pre-commit validation":
# https://github.com/dmitry-ai/harness/issues/67
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify cross-platform subagent BFS traversal, tool-call effect classifier, turn accumulator, and invoke_subagent parser in platforms/trace_common.py":
# https://github.com/dmitry-ai/harness/issues/64
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Consolidate review package reading, verdict recording, quorum checks, and content-addressed immutable receipts across review.py, text_review.py, text_workflow.py, text_sources.py, and storage.py":
# https://github.com/dmitry-ai/harness/issues/63
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Deduplicate turn compaction/delegation reducers, shell/path tool normalization, and request/metadata wrappers across Antigravity and Codex adapters":
# https://github.com/dmitry-ai/harness/issues/58
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify A.A reviewer isolation, prompt-bias checks, and review-proof helpers across Antigravity and Codex adapters into platforms/trace_common.py":
# https://github.com/dmitry-ai/harness/issues/52
import hashlib
import json
from pathlib import Path
import re
from ..research import json_data
from ..shell_audit import unflagged_git_read_commands, unpersisted_http_fetch_commands
from ..storage import write_immutable_bytes
_ACCUMULATOR_INTERNAL_KEYS = ('checkpoint_steps', 'tool_steps', 'subagent_steps', 'aa_subagent_steps', 'aa_partial_read_violations', 'af_subagent_steps', 'kb_persistence_steps', 'completion_service_steps', 'transcript_read_steps', 'tool_records', 'file_reads', 'file_writes')
_KB_PATH_TOKENS = ('\ua616/KB', '\ua616\\KB', '\\ua616/KB', '\\ua616\\\\KB')
_KB_PERSIST_CMD_RE = re.compile('\\b(?:save-analysis|collect|collect-http|collect-browser|extract|extract-file|capture-dom)\\b')
_SCRATCH_PATH_TOKENS = ('\ua616/data/scratch/', '\ua616/data/continuation.md', '\\ua616/data/scratch/', '\\ua616/data/continuation.md')
_SERVICE_CMD_RE = re.compile('\\b(?:turn-begin|answer-prepare|prepare-review|review-input|native-review-proof|record-review|disposition-review|authorize|recover-checkpoint|recover-turn-violation|adopt-requests|unadopt-requests|journal-sync|reconcile-unprepared-delivery|native-executor-metadata|validate_links\\.py|df_github_issue\\.py)\\b')
_SHELL_KB_WRITE_RE = re.compile('(?i)\\b(?:Set-Content|Out-File|Add-Content|WriteAllText|WriteAllBytes|write_text|write_bytes|tee)\\b')
def _has_kb_target(text):
	s = str(text or '')
	return any((tok in s for tok in _KB_PATH_TOKENS)) or '/kb/analysis.md' in s.replace('\\', '/').lower()
def _iter_normalized_tool_calls(rows):
	rows_list = rows if isinstance(rows, list) else []
	for pos, entry in enumerate(rows_list):
		row = entry[1] if isinstance(entry, tuple) and 2 == len(entry) else entry
		if isinstance(row, dict):
			if 'response_item' == row.get('type'):
				pay = row.get('payload') if isinstance(row.get('payload'), dict) else {}
				if pay.get('type') in ('function_call', 'custom_tool_call'):
					raw_in = pay.get('arguments', pay.get('input', {}))
					raw_cmd = raw_in if isinstance(raw_in, str) else json.dumps(raw_in, ensure_ascii=False)
					yield (str(pay.get('name') or ''), parse_tool_args(raw_in), raw_cmd, [])
			else:
				calls = row.get('tool_calls') if isinstance(row.get('tool_calls'), list) else []
				nxt_texts = [str(nxt.get('content') or '') for nxt in rows_list[pos + 1:pos + 4] if isinstance(nxt, dict) and 'GENERIC' == nxt.get('type')]
				for call in calls:
					if isinstance(call, dict):
						raw_args = call.get('args', {})
						args = parse_tool_args(raw_args)
						cmd = str(args.get('CommandLine') or '')
						yield (str(call.get('name') or ''), args, cmd, nxt_texts)
def _merge_line_intervals(intervals):
	merged = []
	for s_val, e_val in sorted(intervals):
		if not merged or merged[-1][1] + 1 < s_val:
			merged.append([s_val, e_val])
		else:
			merged[-1][1] = max(merged[-1][1], e_val)
	return merged
def collect_prompt_bias_issues(prompts):
	issues = []
	for prompt_text in prompts or ():
		for issue in prompt_bias_issues(prompt_text):
			if issue not in issues:
				issues.append(issue)
	return issues
def collect_shell_violations(cmd, step_idx, exec5_violations, http_violations, *, extra=None):
	meta = extra or {}
	bad = unflagged_git_read_commands(cmd)
	if bad:
		exec5_violations.append({'step': step_idx, **meta, 'commands': bad})
	bad_http = unpersisted_http_fetch_commands(cmd)
	if bad_http:
		http_violations.append({'step': step_idx, **meta, 'commands': bad_http})
def collect_subagent_bfs(root_id, root_p, seeds, resolve_child, aa_violations, *, max_depth=4):
	r = {root_id}
	queued_pairs = set()
	queue = []
	for seed_cid, seed_hint, seed_parent in seeds or ():
		if seed_cid and seed_cid not in r and (seed_cid, seed_parent) not in queued_pairs:
			queued_pairs.add((seed_cid, seed_parent))
			queue.append((seed_cid, 1, seed_hint, seed_parent))
	while queue:
		child_cid, depth, hint, expected_parent = queue.pop(0)
		if child_cid in r or depth > max_depth:
			continue
		resolved = resolve_child(child_cid, depth, hint, expected_parent)
		if None is resolved:
			continue
		r.add(child_cid)
		c_rows, is_aa, pre_children, on_visit = resolved
		for grand_cid in pre_children or ():
			if grand_cid and grand_cid not in r and (grand_cid, child_cid) not in queued_pairs:
				queued_pairs.add((grand_cid, child_cid))
				queue.append((grand_cid, depth + 1, False, child_cid))
		if is_aa:
			for p_err in partial_candidate_read_issues(root_p, c_rows):
				if p_err not in aa_violations:
					aa_violations.append(p_err)
		extra_children = on_visit(child_cid, c_rows) if None is not on_visit else ()
		for grand_cid in extra_children or ():
			if grand_cid and grand_cid not in r and (grand_cid, child_cid) not in queued_pairs:
				queued_pairs.add((grand_cid, child_cid))
				queue.append((grand_cid, depth + 1, False, child_cid))
	return r
def current_turn_requests(selected, conversation_id, surface, error_msg, *, id_fmt='{cid}-{idx}', extra=None):
	if not selected:
		raise ValueError(error_msg)
	meta = extra or {}
	return [{'id': id_fmt.format(cid=conversation_id, idx=index), 'text': text, 'native_conversation_id': conversation_id, 'native_step': index, 'surface': surface, **meta, 'project_binding': binding} for index, text, binding in selected]
def finalize_executor_checks(surface, role, conversation_id, parent_id, requested, observed, history, sources, detail, *, force_model_mismatch=False):
	checks = {key: 'unverified' if not requested.get(key) or not observed.get(key) else 'verified' if requested[key] == observed[key] else 'mismatch' for key in ('model', 'effort')}
	if force_model_mismatch:
		checks['model'] = 'mismatch'
	status = 'mismatch' if 'mismatch' in checks.values() else 'verified' if {'verified'} == set(checks.values()) else 'unverified'
	return {'schema_version': 1, 'surface': surface, 'role': role, 'conversation_id': conversation_id, 'parent_id': parent_id, 'requested': requested, 'observed': observed, 'observation_history': history, 'metadata_sources': sources, 'verification': {'status': status, **checks, 'detail': detail}}
def init_turn_accumulator(*, extra=None):
	return {'aa_partial_read_violations': [], 'aa_subagent_steps': [], 'af_subagent_steps': [], 'checkpoint_steps': [], 'completion_service_steps': [], 'exec5_violations': [], 'file_reads': [], 'file_writes': [], 'http_fetch_violations': [], 'kb_persistence_steps': [], 'subagent_steps': [], 'tool_records': [], 'tool_steps': [], 'touched_files': [], 'transcript_read_steps': [], **(extra or {})}
def iter_antigravity_subagents(call):
	r = []
	if isinstance(call, dict) and 'invoke_subagent' == call.get('name'):
		raw_args = call.get('args', {})
		args = parse_tool_args(raw_args)
		if args:
			raw_subs = args.get('Subagents', [])
			invalid_subs = False
			if not isinstance(raw_subs, str):
				subs = raw_subs
			else:
				try:
					subs = json.loads(raw_subs)
				except ValueError:
					subs, invalid_subs = ([], True)
			if not subs and (not invalid_subs):
				subs = [args]
			if isinstance(subs, list):
				r = [sub for sub in subs if isinstance(sub, dict)]
	return r
def merge_turn_accumulators(items, *, allow_step_output_recovery=False):
	first, last = (items[0], items[-1])
	cp_steps = [s for item in items for s in item.get('checkpoint_steps', [])]
	t_steps = [s for item in items for s in item.get('tool_steps', [])]
	sub_steps = [s for item in items for s in item.get('subagent_steps', [])]
	aa_steps = [s for item in items for s in item.get('aa_subagent_steps', [])]
	aa_part_errs = list(dict.fromkeys((e for item in items for e in item.get('aa_partial_read_violations', []))))
	af_steps = [s for item in items for s in item.get('af_subagent_steps', [])]
	kb_steps = [s for item in items for s in item.get('kb_persistence_steps', [])]
	svc_steps = {s for item in items for s in item.get('completion_service_steps', [])}
	tr_steps = [s for item in items for s in item.get('transcript_read_steps', [])]
	records = [rec for item in items for rec in item.get('tool_records', [])]
	t_files = list(dict.fromkeys((f for item in items for f in item.get('touched_files', []))))
	f_reads = [fr for item in items for fr in item.get('file_reads', [])]
	f_writes = [fw for item in items for fw in item.get('file_writes', [])]
	i_actions = [a for item in items for a in item.get('issue_actions', [])]
	compaction, delegation = summarize_turn_activity(cp_steps, t_steps, sub_steps, aa_steps, af_steps, kb_steps, tr_steps, records, f_reads, f_writes, svc_steps=svc_steps, aa_part_errs=aa_part_errs, allow_step_output_recovery=allow_step_output_recovery)
	r = {**last, 'turn_id': first['turn_id'], 'start_step': first['start_step'], 'requests': [req for item in items for req in item['requests']], 'owned': all((item['owned'] for item in items)), 'exec5_violations': [v for item in items for v in item.get('exec5_violations', [])], 'http_fetch_violations': [v for item in items for v in item.get('http_fetch_violations', [])], 'touched_files': t_files, 'issue_actions': i_actions, 'compaction': compaction, 'delegation': delegation}
	for k in _ACCUMULATOR_INTERNAL_KEYS:
		r.pop(k, None)
	return r
def parse_tool_args(raw):
	parsed = raw
	if isinstance(raw, str):
		try:
			parsed = json.loads(raw)
		except ValueError:
			parsed = {}
	return parsed if isinstance(parsed, dict) else {}
def partial_candidate_read_issues(project_root: Path, rows: list) -> list[str]:
	issues = []
	candidate_reads: dict[str, dict] = {}
	root_resolved = Path(project_root).resolve()
	for name, args, _, nxt_texts in _iter_normalized_tool_calls(rows):
		if not name.endswith(('view_file', 'read_file')):
			continue
		raw_path = str(args.get('AbsolutePath') or args.get('Path') or args.get('TargetFile') or args.get('path') or '').strip()
		if not raw_path:
			continue
		norm_p = raw_path.replace('\\', '/').lower()
		is_cand = norm_p.endswith(('/answer.md', '/candidate.md')) or '/reviews/candidates/' in norm_p or ('/data/scratch/' in norm_p and ('answer' in Path(norm_p).name or 'candidate' in Path(norm_p).name))
		if not is_cand:
			continue
		try:
			p_obj = Path(raw_path)
			rp = p_obj.resolve() if p_obj.is_absolute() else (root_resolved / p_obj).resolve()
		except OSError:
			rp = Path(raw_path)
		key = rp.as_posix().lower()
		entry = candidate_reads.setdefault(key, {'path': rp, 'intervals': [], 'full_read': False, 'total_lines': 0})
		if rp.is_file():
			try:
				entry['total_lines'] = max(entry['total_lines'], len(rp.read_text(encoding='utf-8', errors='replace').splitlines()))
			except OSError:
				pass
		for txt in nxt_texts:
			m_tl = re.search('Total Lines:\\s*(\\d+)', txt)
			if m_tl:
				entry['total_lines'] = max(entry['total_lines'], int(m_tl.group(1)))
		start_ln = args.get('StartLine', args.get('offset'))
		end_ln = args.get('EndLine', args.get('limit'))
		if None is start_ln and None is end_ln:
			entry['full_read'] = True
		else:
			s_val = int(start_ln) if isinstance(start_ln, int) or (isinstance(start_ln, str) and start_ln.isdigit()) else 1
			e_val = int(end_ln) if isinstance(end_ln, int) or (isinstance(end_ln, str) and end_ln.isdigit()) else max(entry['total_lines'], 800)
			entry['intervals'].append((s_val, e_val))
	for info in candidate_reads.values():
		if info['full_read'] or not info['intervals']:
			continue
		total = info['total_lines']
		merged = _merge_line_intervals(info['intervals'])
		min_s = merged[0][0]
		max_e = merged[-1][1]
		if 0 == total and (1 < len(merged) or (100 >= max_e and 1 == min_s)):
			issues.append(f'reviewer performed a partial/truncated read of candidate response {info["path"].name} (lines {min_s}-{max_e})')
		elif 0 < total and (1 < len(merged) or 1 < min_s or max_e < total):
			if 1 < len(merged):
				issues.append(f'reviewer performed a partial/truncated read of candidate response {info["path"].name} (non-contiguous intervals {merged} of {total})')
			else:
				issues.append(f'reviewer performed a partial/truncated read of candidate response {info["path"].name} (lines {min_s}-{max_e} of {total})')
	return issues
def persist_review_proof(root, reviewer_id, digest, final_text, proof, *, write=True, diff_error='Existing reviewer proof changed; preserve both and recheck native progress'):
	root_p = Path(root).resolve()
	target = root_p / '\ua616/KB/Evidence/Reviews' / f'{reviewer_id}-{digest[:16]}-native.json'
	authored = target.with_name(target.stem + '-authored.txt')
	proof['authored_response'] = authored.relative_to(root_p).as_posix()
	if write:
		write_immutable_bytes(authored, final_text.encode('utf-8'), diff_error='Immutable native authored response differs')
		write_immutable_bytes(target, json_data(proof), diff_error=diff_error)
	return {'proof': target.relative_to(root_p).as_posix(), **proof}
def prompt_bias_issues(prompt_text):
	if not isinstance(prompt_text, str) or not prompt_text.strip():
		r = []
	else:
		issues = []
		if re.search('["\']approved["\']|\\bresult["\']?\\s*:\\s*["\']?approved\\b', prompt_text, re.I) and (not re.search('\\bneeds_changes\\b', prompt_text, re.I)):
			issues.append('prompt specifies result="approved" without "needs_changes"')
		if re.search('["\']supported["\']|\\boutcome["\']?\\s*:\\s*["\']?supported\\b', prompt_text, re.I) and (not (re.search('\\bqualified\\b', prompt_text, re.I) and re.search('\\bunsupported\\b', prompt_text, re.I))):
			issues.append('prompt specifies outcome="supported" without "qualified" and "unsupported"')
		if re.search('["\']direct["\']|\\brelationship["\']?\\s*:\\s*["\']?direct\\b', prompt_text, re.I) and (not (re.search('\\bproxy\\b', prompt_text, re.I) and re.search('\\birrelevant\\b', prompt_text, re.I))):
			issues.append('prompt specifies relationship="direct" without "proxy" and "irrelevant"')
		if re.search('["\']findings["\']\\s*:\\s*\\[\\s*\\]', prompt_text) and (not (re.search('\\bseverity\\b', prompt_text, re.I) and re.search('\\bremediation\\b', prompt_text, re.I))):
			issues.append('prompt hardcodes empty findings=[] without specifying finding object fields')
		r = issues
	return r
def record_canonical_path(root_p, step_idx, raw_path, is_read, file_reads, file_writes, touched_files):
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
def record_normalized_tool_effects(root_p, step_idx, name, raw_args, raw_cmd, acc, *, extra_violation=None, track_turn_steps=False, transcript_tokens=()):
	args = raw_args if isinstance(raw_args, dict) else parse_tool_args(raw_args)
	scan_text = str(raw_cmd or '')
	is_shell = 'exec' == name or name.endswith(('exec_command', 'run_command'))
	shell_cmd = str(args.get('CommandLine') or '') if name.endswith('run_command') else scan_text
	if is_shell:
		collect_shell_violations(shell_cmd, step_idx, acc['exec5_violations'], acc['http_fetch_violations'], extra=extra_violation)
	patch_list = re.findall('^\\*\\*\\* (?:Add|Update|Delete) File:\\s*(.+)$', scan_text, flags=re.M) if 'apply_patch' in name else []
	for pt in patch_list:
		record_canonical_path(root_p, step_idx, pt, False, acc['file_reads'], acc['file_writes'], acc['touched_files'])
	is_read_tool = name.endswith(('read_file', 'view_file'))
	is_write_tool = name.endswith(('write_file', 'edit_file', 'write_to_file', 'replace_file_content', 'multi_replace_file_content'))
	is_file_tool = is_read_tool or is_write_tool
	target_path = str(args.get('Path') or args.get('TargetFile') or args.get('AbsolutePath') or args.get('path') or '').strip() if is_file_tool else ''
	if target_path:
		record_canonical_path(root_p, step_idx, target_path, is_read_tool, acc['file_reads'], acc['file_writes'], acc['touched_files'])
	if track_turn_steps:
		if is_shell and 'answer_prepared_in_segment' in acc and re.search('\\banswer-prepare\\b', shell_cmd):
			acc['answer_prepared_in_segment'] = True
		t_tokens = ('transcript_full.jsonl', 'transcript.jsonl', 'recover-checkpoint') + tuple(transcript_tokens or ())
		if any((tok in scan_text for tok in t_tokens)) and step_idx not in acc['transcript_read_steps']:
			acc['transcript_read_steps'].append(step_idx)
		if 'invoke_subagent' != name and (name.endswith(('spawn_agent', 'invoke_subagent', 'send_input', 'send_message', 'wait', 'wait_agent')) or ((not is_file_tool) and (not is_shell) and ('spawn_agent' in scan_text))):
			if step_idx not in acc['subagent_steps']:
				acc['subagent_steps'].append(step_idx)
			if name.endswith(('spawn_agent', 'invoke_subagent')) or ((not is_file_tool) and (not is_shell) and ('spawn_agent' in scan_text)):
				sub_bucket = acc['af_subagent_steps'] if re.search('(?i)"(?:task_name|agent_type|role)"\\s*:\\s*"[^"]*\\baf\\b', scan_text) else acc['aa_subagent_steps']
				if step_idx not in sub_bucket:
					sub_bucket.append(step_idx)
		elif 'invoke_subagent' == name:
			if 'spawned_subagents' in acc:
				acc['spawned_subagents'] += 1
			if step_idx not in acc['subagent_steps']:
				acc['subagent_steps'].append(step_idx)
			for sub in iter_antigravity_subagents({'name': name, 'args': raw_args}):
				tname = str(sub.get('TypeName') or '').strip().lower()
				target_steps = acc['aa_subagent_steps'] if 'self' == tname else acc['af_subagent_steps'] if tname else None
				if None is not target_steps and step_idx not in target_steps:
					target_steps.append(step_idx)
		is_kb_persist = (is_write_tool and _has_kb_target(target_path)) or (bool(patch_list) and _has_kb_target('\n'.join(patch_list))) or (is_shell and (bool(_KB_PERSIST_CMD_RE.search(scan_text)) or ('answer-prepare' not in scan_text and bool(_SHELL_KB_WRITE_RE.search(scan_text)) and _has_kb_target(scan_text))))
		if is_kb_persist and step_idx not in acc['kb_persistence_steps']:
			acc['kb_persistence_steps'].append(step_idx)
		is_scratch_write = (is_write_tool and any((tok in target_path.replace('\\', '/') for tok in _SCRATCH_PATH_TOKENS))) or (bool(patch_list) and all((any((tok in pt.replace('\\', '/') for tok in _SCRATCH_PATH_TOKENS)) for pt in patch_list)))
		if ((is_shell and bool(_SERVICE_CMD_RE.search(scan_text))) or is_scratch_write) and step_idx not in acc['completion_service_steps']:
			acc['completion_service_steps'].append(step_idx)
def require_turn_binding(selected, active, binding, error_msg):
	if not selected or not active:
		raise ValueError(error_msg)
	return binding
def reviewer_isolation_issues(root, rows):
	project_root = Path(root).resolve()
	daily_root = next((p for p in project_root.parents if 'daily' == p.name), project_root.parent)
	issues = []
	for name, args, raw_cmd, _ in _iter_normalized_tool_calls(rows):
		if name in ('write_file', 'edit_file', 'write_to_file', 'replace_file_content', 'multi_replace_file_content') or name.endswith(('write_file', 'edit_file', 'write_to_file', 'apply_patch')) or 'apply_patch' in name:
			issues.append(f'reviewer called mutating tool {name}')
		if 'exec' == name or name.endswith(('run_command', 'exec_command')):
			cmd_text = raw_cmd or str(args.get('CommandLine') or args.get('cmd') or args.get('command') or '')
			if re.search('(?i)\\b(?:Set-Content|Out-File|Add-Content)\\b|\\.(?:write_text|write_bytes)\\b|\\bgen_review', cmd_text):
				issues.append('reviewer executed a file-writing command or ad-hoc generator script')
		for key in ('AbsolutePath', 'Path', 'TargetFile', 'DirectoryPath', 'SearchPath', 'Cwd', 'path', 'workdir'):
			val = args.get(key)
			if not isinstance(val, str) or not val.strip():
				continue
			try:
				candidate = Path(val).resolve()
			except OSError:
				continue
			if candidate.is_relative_to(daily_root) and (not candidate.is_relative_to(project_root)) and (not project_root.is_relative_to(candidate)):
				issues.append(f'reviewer accessed sibling project path {candidate}')
	issues.extend(partial_candidate_read_issues(project_root, rows))
	return issues
def summarize_turn_activity(cp_steps, t_steps, sub_steps, aa_steps, af_steps, kb_steps, tr_steps, records, f_reads, f_writes, *, svc_steps=(), aa_part_errs=None, allow_step_output_recovery=False):
	last_cp = max(cp_steps) if cp_steps else None
	pre_cp_steps = [s for s in t_steps if None is not last_cp and s < last_cp]
	post_cp_rec = [s for s in tr_steps if None is not last_cp and s > last_cp]
	pre_cp_records = [rec for rec in records if None is not last_cp and rec['step'] < last_cp]
	pre_cp_reads = list(dict.fromkeys((p for st, p in f_reads if None is not last_cp and st < last_cp)))
	post_cp_reads = list(dict.fromkeys((p for st, p in f_reads if None is not last_cp and st > last_cp)))
	post_cp_writes = list(dict.fromkeys((p for st, p in f_writes if None is not last_cp and st > last_cp)))
	post_cp_lower = {p.lower() for p in post_cp_reads}
	recovered_step_nums = set()
	if allow_step_output_recovery:
		for pr in post_cp_reads:
			m_rec = re.search('(?:/steps/(\\d+)/output\\.txt|/step-(\\d+)\\.txt)$', pr, re.I)
			if m_rec:
				recovered_step_nums.add(m_rec.group(1) or m_rec.group(2))
	evicted_unreread = []
	for p in pre_cp_reads:
		if p.lower() in post_cp_lower:
			continue
		if allow_step_output_recovery:
			m_ev_step = re.search('/\\.system_generated/steps/(\\d+)/output\\.txt$', p, re.I)
			if m_ev_step and m_ev_step.group(1) in recovered_step_nums:
				continue
		evicted_unreread.append(p)
	reads_by_step = {}
	for st, p in f_reads:
		reads_by_step.setdefault(st, []).append(p)
	cur_streak = 0
	max_streak = 0
	cur_src_reads = set()
	max_src_reads = 0
	persist_or_sub = set(sub_steps) | set(kb_steps)
	svc_set = set(svc_steps or ())
	for st in t_steps:
		if st in svc_set and st not in persist_or_sub:
			continue
		if st in persist_or_sub:
			cur_streak = 0
			cur_src_reads.clear()
		else:
			cur_streak += 1
			if cur_streak > max_streak:
				max_streak = cur_streak
			for rp in reads_by_step.get(st, ()):
				if rp.lower().endswith('/kb/source.md'):
					cur_src_reads.add(rp.lower())
			if len(cur_src_reads) > max_src_reads:
				max_src_reads = len(cur_src_reads)
	return ({'occurred': bool(cp_steps), 'checkpoint_steps': cp_steps, 'last_checkpoint_step': last_cp, 'pre_checkpoint_tool_steps': pre_cp_steps, 'post_checkpoint_recovery_steps': post_cp_rec, 'recovered_in_trace': not cp_steps or not pre_cp_steps or bool(post_cp_rec), 'pre_checkpoint_records': pre_cp_records, 'pre_checkpoint_read_files': pre_cp_reads, 'post_checkpoint_read_files': post_cp_reads, 'post_checkpoint_written_files': post_cp_writes, 'evicted_unreread_files': evicted_unreread}, {'tool_step_count': len(t_steps), 'subagent_step_count': len(sub_steps), 'aa_subagent_step_count': len(aa_steps), 'aa_partial_read_violations': list(aa_part_errs or []), 'af_subagent_step_count': len(af_steps), 'kb_persistence_step_count': len(kb_steps), 'unpersisted_step_streak': cur_streak, 'max_unpersisted_step_streak': max_streak, 'max_unpersisted_source_reads': max_src_reads})
def verify_review_proof_core(root, native, result, fields, *, trace_error='Review proof differs from the current native trace', identity_error='Review proof has a different explicit project identity', allow_legacy_generation_model=False):
	for field in fields:
		if native.get(field) != result.get(field):
			raise ValueError(trace_error)
	if 'client_text_workspace' == result['project_kind'] or any((key in native for key in ('project_id', 'project_kind'))):
		for key in ('project_id', 'project_kind'):
			if native.get(key) != result.get(key):
				raise ValueError(identity_error)
	authored = Path(root) / result['authored_response']
	if authored.exists() and hashlib.sha256(authored.read_bytes()).hexdigest() != result['final_response_sha256']:
		raise ValueError('Immutable native authored reviewer response changed')
	if 'executor_metadata' in native and native['executor_metadata'] != result['executor_metadata']:
		if not allow_legacy_generation_model:
			raise ValueError('Native executor metadata differs from saved reviewer proof')
		saved_meta = native['executor_metadata']
		curr_meta = result['executor_metadata']
		if not isinstance(saved_meta, dict) or 'generation_model' in (saved_meta.get('observed') or {}):
			raise ValueError('Native executor metadata differs from saved reviewer proof')
		norm_curr = {**curr_meta, 'observed': {k: v for k, v in (curr_meta.get('observed') or {}).items() if k in (saved_meta.get('observed') or {})}, 'requested': {k: v for k, v in (curr_meta.get('requested') or {}).items() if k in (saved_meta.get('requested') or {})}}
		if saved_meta != norm_curr:
			raise ValueError('Native executor metadata differs from saved reviewer proof')
	return result
