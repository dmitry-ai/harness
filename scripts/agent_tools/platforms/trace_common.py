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
from ..storage import write_immutable_bytes
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
	from ..git_gate import unflagged_git_read_commands, unpersisted_http_fetch_commands
	meta = extra or {}
	bad = unflagged_git_read_commands(cmd)
	if bad:
		exec5_violations.append({'step': step_idx, **meta, 'commands': bad})
	bad_http = unpersisted_http_fetch_commands(cmd)
	if bad_http:
		http_violations.append({'step': step_idx, **meta, 'commands': bad_http})
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
