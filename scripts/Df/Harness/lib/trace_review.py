# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.path_resolve import dfh_project_paths
from Df.Harness.lib.proof_metadata import dfh_executor_metadata_equivalent, dfh_reuse_equivalent_proof
from Df.Harness.lib.request_binding import dfh_native_project_fields
from Df.Harness.lib.storage import dfh_write_immutable_bytes
from Df.Harness.lib.trace_common import dfh_parse_tool_args
from agent_tools.research import json_data
import hashlib
import json
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`_iter_normalized_tool_calls()`
def _ag_calls_from_row(rows_list: list, pos: int, row: dict) -> list[tuple]:
	calls = row.get('tool_calls') if isinstance(row.get('tool_calls'), list) else []
	nxt_texts = [str(nxt.get('content') or '') for nxt in rows_list[pos + 1:pos + 4] if isinstance(nxt, dict) and 'GENERIC' == nxt.get('type')]
	r: list[tuple] = []
	for call in calls:
		if isinstance(call, dict):
			args = dfh_parse_tool_args(call.get('args', {}))
			r.append((str(call.get('name') or ''), args, str(args.get('CommandLine') or ''), nxt_texts))
	return r
# @used-by :func:`dfh_partial_candidate_read_issues()`
def _check_candidate_read_coverage(info: dict) -> str | None:
	r: str | None = None
	if not info['full_read'] and info['intervals']:
		total = info['total_lines']
		merged = _merge_line_intervals(info['intervals'])
		min_s, max_e = (merged[0][0], merged[-1][1])
		name = info['path'].name
		if 0 == total and (1 < len(merged) or (100 >= max_e and 1 == min_s)):
			r = f'reviewer performed a partial/truncated read of candidate response {name} (lines {min_s}-{max_e})'
		elif 0 < total and (1 < len(merged) or 1 < min_s or max_e < total):
			detail = f'non-contiguous intervals {merged} of {total}' if 1 < len(merged) else f'lines {min_s}-{max_e} of {total}'
			r = f'reviewer performed a partial/truncated read of candidate response {name} ({detail})'
	return r
# @used-by :func:`dfh_reviewer_isolation_issues()`
def _check_isolation_call(project_root: Path, daily_root: Path, name: str, args: dict, raw_cmd: str) -> list[str]:
	r: list[str] = []
	if name in ('write_file', 'edit_file', 'write_to_file', 'replace_file_content', 'multi_replace_file_content') or name.endswith(('write_file', 'edit_file', 'write_to_file', 'apply_patch')) or 'apply_patch' in name:
		r.append(f'reviewer called mutating tool {name}')
	if 'exec' == name or name.endswith(('run_command', 'exec_command')):
		cmd_text = raw_cmd or str(args.get('CommandLine') or args.get('cmd') or args.get('command') or '')
		if re.search('(?i)\\b(?:Set-Content|Out-File|Add-Content)\\b|\\.(?:write_text|write_bytes)\\b|\\bgen_review', cmd_text):
			r.append('reviewer executed a file-writing command or ad-hoc generator script')
	for key in ('AbsolutePath', 'Path', 'TargetFile', 'DirectoryPath', 'SearchPath', 'Cwd', 'path', 'workdir'):
		val = args.get(key)
		if isinstance(val, str) and val.strip():
			from agent_tools.project_rename_state import find_sibling_project_path
			sib = find_sibling_project_path(val, project_root, daily_root)
			if None is not sib:
				r.append(f'reviewer accessed sibling project path {sib}')
	return r
# @used-by :func:`_iter_normalized_tool_calls()`
def _codex_calls_from_row(row: dict) -> list[tuple]:
	pay = row.get('payload') if isinstance(row.get('payload'), dict) else {}
	r: list[tuple] = []
	if pay.get('type') in ('function_call', 'custom_tool_call'):
		raw_in = pay.get('arguments', pay.get('input', {}))
		raw_cmd = raw_in if isinstance(raw_in, str) else json.dumps(raw_in, ensure_ascii=False)
		r.append((str(pay.get('name') or ''), dfh_parse_tool_args(raw_in), raw_cmd, []))
	return r
# @used-by :func:`dfh_partial_candidate_read_issues()`
def _collect_candidate_read(root_resolved: Path, args: dict, nxt_texts: list[str], candidate_reads: dict[str, dict]) -> None:
	raw_path = str(args.get('AbsolutePath') or args.get('Path') or args.get('TargetFile') or args.get('path') or '').strip()
	norm_p = raw_path.replace('\\', '/').lower()
	is_cand = bool(raw_path) and (norm_p.endswith(('/answer.md', '/candidate.md')) or '/reviews/candidates/' in norm_p or ('/data/scratch/' in norm_p and ('answer' in Path(norm_p).name or 'candidate' in Path(norm_p).name)))
	if is_cand:
		try:
			p_obj = Path(raw_path)
			rp = p_obj.resolve() if p_obj.is_absolute() else (root_resolved / p_obj).resolve()
		except OSError:
			rp = Path(raw_path)
		entry = candidate_reads.setdefault(rp.as_posix().lower(), {'path': rp, 'intervals': [], 'full_read': False, 'total_lines': 0})
		_update_candidate_read_entry(entry, rp, args, nxt_texts)
# @used-by :func:`dfh_partial_candidate_read_issues()`
# @used-by :func:`dfh_reviewer_isolation_issues()`
def _iter_normalized_tool_calls(rows):
	rows_list = rows if isinstance(rows, list) else []
	for pos, entry in enumerate(rows_list):
		row = entry[1] if isinstance(entry, tuple) and 2 == len(entry) else entry
		if isinstance(row, dict):
			yield from (_codex_calls_from_row(row) if 'response_item' == row.get('type') else _ag_calls_from_row(rows_list, pos, row))
# @used-by :func:`_check_candidate_read_coverage()`
def _merge_line_intervals(intervals: list) -> list[list[int]]:
	r: list[list[int]] = []
	for s_val, e_val in sorted(intervals):
		if not r or r[-1][1] + 1 < s_val:
			r.append([s_val, e_val])
		else:
			r[-1][1] = max(r[-1][1], e_val)
	return r
# @used-by :func:`_collect_candidate_read()`
def _update_candidate_read_entry(entry: dict, rp: Path, args: dict, nxt_texts: list[str]) -> None:
	if rp.is_file():
		try:
			entry['total_lines'] = max(entry['total_lines'], len(rp.read_text(encoding='utf-8', errors='replace').splitlines()))
		except OSError:
			pass
	for txt in nxt_texts:
		m_tl = re.search('Total Lines:\\s*(\\d+)', txt)
		if m_tl:
			entry['total_lines'] = max(entry['total_lines'], int(m_tl.group(1)))
	start_ln, end_ln = (args.get('StartLine', args.get('offset')), args.get('EndLine', args.get('limit')))
	if None is start_ln and None is end_ln:
		entry['full_read'] = True
	else:
		s_val = int(start_ln) if isinstance(start_ln, int) or (isinstance(start_ln, str) and start_ln.isdigit()) else 1
		e_val = int(end_ln) if isinstance(end_ln, int) or (isinstance(end_ln, str) and end_ln.isdigit()) else max(entry['total_lines'], 800)
		entry['intervals'].append((s_val, e_val))
# @used-by :meth:`Df.Harness.Platform.Antigravity.ReviewProver.ReviewProver.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.ReviewProver.ReviewProver.run()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_build_native_review_proof_forwards_arch_role_on_bare_workspace()`
def dfh_build_native_review_proof(root, surface: str, parent_id: str, reviewer_id: str, agent_name: str, log_path, parent_log, raw_log_bytes: bytes, final_step, final_text: str, matched_prompts, rows, *, diff_error: str='Existing reviewer proof changed; preserve both and recheck native progress', extra_fields_fn=None, write: bool=True, role: str='AA') -> dict:
	bias_issues = dfh_collect_prompt_bias_issues(matched_prompts)
	if bias_issues:
		raise ValueError('Reviewer prompt biases verdict or omits negative schema outcomes: ' + '; '.join(bias_issues))
	isolation_issues = dfh_reviewer_isolation_issues(root, rows)
	if isolation_issues:
		raise ValueError('Independent reviewer isolation violated: ' + '; '.join(isolation_issues))
	extra = extra_fields_fn() if None is not extra_fields_fn else {}
	digest = hashlib.sha256(raw_log_bytes).hexdigest()
	proof = {'surface': surface, 'parent_id': parent_id, 'reviewer_id': reviewer_id, 'agent_name': agent_name, 'status': 'completed', 'native_log': str(log_path), 'parent_log': str(parent_log), 'native_log_sha256': digest, 'final_step': final_step, 'final_response_sha256': hashlib.sha256(final_text.encode('utf-8')).hexdigest(), 'final_response': final_text, **dfh_native_project_fields(root, role=role), **extra}
	return dfh_persist_review_proof(root, reviewer_id, digest, final_text, proof, write=write, diff_error=diff_error)
# @used-by :func:`dfh_build_native_review_proof()`
def dfh_collect_prompt_bias_issues(prompts) -> list[str]:
	r: list[str] = []
	for prompt_text in prompts or ():
		for issue in dfh_prompt_bias_issues(prompt_text):
			if issue not in r:
				r.append(issue)
	return r
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_native_requests()`
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_native_requests()`
def dfh_current_turn_requests(selected, conversation_id: str, surface: str, error_msg: str, *, id_fmt: str='{cid}-{idx}', extra=None) -> list[dict]:
	if not selected:
		raise ValueError(error_msg)
	meta = extra or {}
	return [{'id': id_fmt.format(cid=conversation_id, idx=index), 'text': text, 'native_conversation_id': conversation_id, 'native_step': index, 'surface': surface, **meta, 'project_binding': binding} for index, text, binding in selected]
# @used-by :meth:`Df.Harness.Platform.Antigravity.ExecutorMetadataReader.ExecutorMetadataReader.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.ExecutorMetadataReader.ExecutorMetadataReader.run()`
def dfh_finalize_executor_checks(surface: str, role: str, conversation_id: str, parent_id, requested: dict, observed: dict, history, sources, detail: str, *, force_model_mismatch: bool=False) -> dict:
	checks = {key: 'unverified' if not requested.get(key) or (not observed.get(key)) else ('verified' if requested[key] == observed[key] else 'mismatch') for key in ('model', 'effort')}
	if force_model_mismatch:
		checks['model'] = 'mismatch'
	status = 'mismatch' if 'mismatch' in checks.values() else ('verified' if {'verified'} == set(checks.values()) else 'unverified')
	return {'schema_version': 1, 'surface': surface, 'role': role, 'conversation_id': conversation_id, 'parent_id': parent_id, 'requested': requested, 'observed': observed, 'observation_history': history, 'metadata_sources': sources, 'verification': {'status': status, **checks, 'detail': detail}}
# @used-by :meth:`Df.Harness.Platform.Antigravity.ToolTraceReader.ToolTraceReader.__extract_step_event()`
# @used-by :meth:`Df.Harness.Platform.Codex.ToolTraceReader.ToolTraceReader.__build_call_event()`
def dfh_make_tool_trace_event(event_id: str, step, output_step, name: str, arguments, result, successful: bool, created_at, completed_at, sha_payload, *, namespace=None) -> dict:
	r = {'id': event_id, 'step': step, 'output_step': output_step, 'name': name, 'arguments': arguments, 'result': result, 'successful': successful, 'created_at': created_at, 'completed_at': completed_at, 'native_event_sha256': hashlib.sha256(json_data(sha_payload)).hexdigest()}
	if None is not namespace:
		r['namespace'] = namespace
	return r
# @used-by :func:`Df.Harness.lib.trace_effects.dfh_collect_subagent_bfs()`
# @used-by :func:`dfh_reviewer_isolation_issues()`
def dfh_partial_candidate_read_issues(project_root: Path, rows: list) -> list[str]:
	candidate_reads: dict[str, dict] = {}
	root_resolved = Path(project_root).resolve()
	for name, args, _, nxt_texts in _iter_normalized_tool_calls(rows):
		if name.endswith(('view_file', 'read_file')):
			_collect_candidate_read(root_resolved, args, nxt_texts, candidate_reads)
	r: list[str] = []
	for info in candidate_reads.values():
		err = _check_candidate_read_coverage(info)
		if None is not err:
			r.append(err)
	return r
# @used-by :func:`dfh_build_native_review_proof()`
# @used-by :meth:`test_reused_reviewer_and_metadata_drift_m5.ReusedReviewerAndMetadataDriftM5Tests.test_tolerates_monotonic_same_model_metadata_append_and_rejects_model_change()`
# @used-by :meth:`test_reused_reviewer_and_metadata_drift_m5.ReusedReviewerAndMetadataDriftM5Tests.test_verify_native_proof_accepts_reused_reviewer_send_message_and_rejects_self_mention()`
def dfh_persist_review_proof(root, reviewer_id: str, digest: str, final_text: str, proof: dict, *, write: bool=True, diff_error: str='Existing reviewer proof changed; preserve both and recheck native progress') -> dict:
	pp = dfh_project_paths(root, exact_root=True)
	root_p = pp.root
	target = pp.evidence_dir / 'Reviews' / f'{reviewer_id}-{digest[:16]}-native.json'
	authored = target.with_name(target.stem + '-authored.txt')
	proof['authored_response'] = authored.relative_to(root_p).as_posix() if authored.is_relative_to(root_p) else authored.as_posix()
	if write:
		dfh_write_immutable_bytes(authored, final_text.encode('utf-8'), diff_error='Immutable native authored response differs')
		reused = dfh_reuse_equivalent_proof(target, proof)
		if None is not reused:
			proof = reused
		else:
			dfh_write_immutable_bytes(target, json_data(proof), diff_error=diff_error)
	return {'proof': target.relative_to(root_p).as_posix() if target.is_relative_to(root_p) else target.as_posix(), **proof}
# @used-by :func:`dfh_collect_prompt_bias_issues()`
def dfh_prompt_bias_issues(prompt_text) -> list[str]:
	if not isinstance(prompt_text, str) or (not prompt_text.strip()):
		r: list[str] = []
	else:
		issues: list[str] = []
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
# @used-by :func:`Df.Harness.lib.ag_inputs.dfh_require_current_binding()`
# @used-by :func:`Df.Harness.lib.codex_trace.dfh_codex_require_current_binding()`
def dfh_require_turn_binding(selected, active, r, error_msg: str):
	if not selected or (not active):
		raise ValueError(error_msg)
	return r
# @used-by :func:`dfh_build_native_review_proof()`
# @used-by :meth:`Df.Harness.Platform.TraceAnalyzer.TraceAnalyzer.run()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :meth:`test_issue45_to_48.Issue45To48Tests.test_issue47_partial_candidate_read_blocked()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage()`
def dfh_reviewer_isolation_issues(root, rows) -> list[str]:
	project_root = Path(root).resolve()
	daily_root = next((p for p in project_root.parents if 'daily' == p.name), project_root.parent)
	r: list[str] = []
	for name, args, raw_cmd, _ in _iter_normalized_tool_calls(rows):
		r.extend(_check_isolation_call(project_root, daily_root, name, args, raw_cmd))
	r.extend(dfh_partial_candidate_read_issues(project_root, rows))
	return r
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProofVerifier.ProofVerifier.run()`
# @used-by :meth:`Df.Harness.Platform.Codex.ProofVerifier.ProofVerifier.run()`
# @used-by :meth:`test_reused_reviewer_and_metadata_drift_m5.ReusedReviewerAndMetadataDriftM5Tests.test_tolerates_monotonic_same_model_metadata_append_and_rejects_model_change()`
def dfh_verify_review_proof_core(root, native: dict, r: dict, fields, *, trace_error: str='Review proof differs from the current native trace', identity_error: str='Review proof has a different explicit project identity', allow_legacy_generation_model: bool=False) -> dict:
	for field in fields:
		if native.get(field) != r.get(field):
			raise ValueError(trace_error)
	if 'client_text_workspace' == r['project_kind'] or any((key in native for key in ('project_id', 'project_kind'))):
		for key in ('project_id', 'project_kind'):
			if native.get(key) != r.get(key):
				raise ValueError(identity_error)
	authored = Path(root) / r['authored_response']
	if authored.exists() and hashlib.sha256(authored.read_bytes()).hexdigest() != r['final_response_sha256']:
		raise ValueError('Immutable native authored reviewer response changed')
	if 'executor_metadata' in native and (not dfh_executor_metadata_equivalent(native['executor_metadata'], r.get('executor_metadata'), allow_legacy_generation_model=allow_legacy_generation_model)):
		raise ValueError('Native executor metadata differs from saved reviewer proof')
	return r
