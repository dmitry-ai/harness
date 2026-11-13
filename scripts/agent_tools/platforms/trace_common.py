# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify A.A reviewer isolation, prompt-bias checks, and review-proof helpers across Antigravity and Codex adapters into platforms/trace_common.py":
# https://github.com/dmitry-ai/harness/issues/52
import hashlib
import json
from pathlib import Path
import re
from ..research import json_data
from ..storage import create_bytes
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
					yield (str(pay.get('name') or ''), _parse_tool_args(raw_in), raw_cmd, [])
			else:
				calls = row.get('tool_calls') if isinstance(row.get('tool_calls'), list) else []
				nxt_texts = [str(nxt.get('content') or '') for nxt in rows_list[pos + 1:pos + 4] if isinstance(nxt, dict) and 'GENERIC' == nxt.get('type')]
				for call in calls:
					if isinstance(call, dict):
						raw_args = call.get('args', {})
						args = _parse_tool_args(raw_args)
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
def _parse_tool_args(raw):
	parsed = raw
	if isinstance(raw, str):
		try:
			parsed = json.loads(raw)
		except ValueError:
			parsed = {}
	return parsed if isinstance(parsed, dict) else {}
def collect_prompt_bias_issues(prompts):
	issues = []
	for prompt_text in prompts or ():
		for issue in prompt_bias_issues(prompt_text):
			if issue not in issues:
				issues.append(issue)
	return issues
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
		target.parent.mkdir(parents=True, exist_ok=True)
		authored_bytes = final_text.encode('utf-8')
		if authored.exists() and authored.read_bytes() != authored_bytes:
			raise ValueError('Immutable native authored response differs')
		if not authored.exists():
			create_bytes(authored, authored_bytes)
		payload = json_data(proof)
		if target.exists() and target.read_bytes() != payload:
			raise ValueError(diff_error)
		if not target.exists():
			create_bytes(target, payload)
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
