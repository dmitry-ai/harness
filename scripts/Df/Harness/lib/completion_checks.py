# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Completion.BudgetEvaluator import BudgetEvaluator
from Df.Harness.Hook.CrashAuditor import CrashAuditor
from Df.Harness.Runtime.SettingsLoader import SettingsLoader
from Df.Harness.lib.completion_core import BUDGET_MAX_CHECKPOINTS, BUDGET_MAX_TOOL_STEPS, BUDGET_WINDOW_5H_MAX_STEPS, DEL_MAX_ISSUE_ACTIONS_WITHOUT_SUBAGENTS, DEL_MAX_TOTAL_STEPS_WITHOUT_SUBAGENTS, DEL_MAX_UNPERSISTED_SOURCE_READS, DEL_MAX_UNPERSISTED_STEPS, dfh_hash, dfh_now, dfh_read_meta, dfh_turns_folder
from Df.Harness.lib.config_codex import dfh_project_rule_paths
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_project_paths, dfh_var_value
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
from Df.Harness.lib.runtime_context import dfh_default_user_locale
from Df.Harness.lib.runtime_instances import dfh_platform_adapter_name
from Df.Harness.lib.trace_common import dfh_is_waiting_status_stub
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
GATE_SPECS = (
	('exec5', ('EXEC-5 violation in active turn (git read',), lambda root_p, turn, value, rc: bool(value.get('exec5_check', {}).get('verified'))),
	('hook_crash', ('DOC-5 / EXEC-5 hook_crash_check',), lambda root_p, turn, value, rc: bool(value.get('hook_crash_check', {}).get('verified', True))),
	('http_fetch', ('KB-3 / EXEC-1 violation',), lambda root_p, turn, value, rc: bool(value.get('http_fetch_check', {}).get('verified'))),
	('compaction', (), lambda root_p, turn, value, rc: bool(value.get('compaction_check', {}).get('verified'))),
	('evicted_citations', (), lambda root_p, turn, value, rc: bool(value.get('compaction_check', {}).get('verified')) and (not ((set(rc.get('cited_files') or ()) & set(value.get('compaction_check', {}).get('evicted_unreread_files') or ())) if rc.get('cited_files') else set(value.get('compaction_check', {}).get('evicted_unreread_files') or ())))),
	('delegation', ('REVIEW-1 / KB-3 violation',), lambda root_p, turn, value, rc: bool(value.get('delegation_check', {}).get('verified'))),
	('issue_first', ('EXEC-5 ISSUE-FIRST-GATE',), lambda root_p, turn, value, rc: bool(value.get('issue_first_check', {}).get('verified'))),
	('code_lifecycle', ('EXEC-5 violation in active turn (code/issue',), lambda root_p, turn, value, rc: bool(value.get('code_lifecycle_check', {}).get('verified'))),
	('tdd', ('EXEC-2 TDD-',), lambda root_p, turn, value, rc: bool(value.get('tdd_check', {}).get('verified'))),
	('language_and_stub', ('TEXT-1:', 'FILE-3 / REVIEW-1:'), lambda root_p, turn, value, rc: bool(value.get('language_and_stub_check', {}).get('verified'))),
	('aa_partial_read', ('REVIEW-3 / REVIEW-4: Independent A.A reviewer',), lambda root_p, turn, value, rc: not bool(value.get('delegation_check', {}).get('aa_partial_read_violations'))),
	('factual_kb_note', ('KB-2 / DOC-1 violation',), lambda root_p, turn, value, rc: not bool(dfh_factual_kb_note_issues(root_p, turn)['issues'])),
	('workflow_adoption', ('REVIEW-3 / REVIEW-4: Adopt current requests',), lambda root_p, turn, value, rc: dfh_workflow_gate_resolved(root_p, turn, 'workflow_adoption')),
	('review_authorize', (), lambda root_p, turn, value, rc: dfh_workflow_gate_resolved(root_p, turn, 'review_authorize')),
	('source_grounding', ('VERIFY-1', 'LINK-', 'KB-1 / KB-3:', 'DOC-1 / VERIFY-'), lambda root_p, turn, value, rc: bool(value.get('source_kb_check', {}).get('verified'))),
)
VERIFIED_CHECK_KEYS = ('exec5_check', 'hook_crash_check', 'addon_observability_check', 'verification_observability_check', 'http_fetch_check', 'compaction_check', 'delegation_check', 'issue_first_check', 'code_lifecycle_check', 'scope_deferral_check', 'tdd_check', 'language_and_stub_check', 'source_kb_check')
# @used-by :func:`dfh_instruction_snapshot()`
def _add_codex_guidance_sources(sources: dict[Path, str], root: Path, native: dict, cfg: dict) -> None:
	workspace = Path(cfg['workspace_root']).resolve()
	folders = [root]
	if root.is_relative_to(workspace):
		folders += [parent for parent in root.parents if parent == workspace or parent.is_relative_to(workspace)]
	if native.get('native_backend'):
		folders.append(Path(native['native_backend']))
	for folder in folders:
		for name in ('AGENTS.md', 'AGENTS.override.md'):
			path = folder / name
			if path.is_file():
				sources[path] = 'native-guidance-candidate'
# @used-by :func:`dfh_instruction_snapshot()`
def _collect_base_instruction_sources(root: Path, pp: Any, primary: Path, adapter_kind: str) -> tuple[dict[Path, str], list[str]]:
	sources: dict[Path, str] = {path: 'canonical' for path in sorted((primary / 'rules').glob('*.md'))}
	sources[primary / 'runtime.json'] = 'runtime'
	if (primary / 'paths.json').is_file():
		sources[primary / 'paths.json'] = 'paths-registry'
	if None is not pp.overlay_file and pp.overlay_file.is_file():
		sources[pp.overlay_file] = 'project-paths-overlay'
	adapter_doc = primary / 'platforms' / (adapter_kind + '.md')
	if adapter_doc.is_file():
		sources[adapter_doc] = 'adapter'
	errors: list[str] = []
	agents_dir = pp.agents_config_dir if pp.agents_config_dir.resolve() != primary.resolve() else (root / '.agents')
	if (agents_dir / 'rules.json').exists():
		sources[agents_dir / 'rules.json'] = 'project-registration'
	try:
		sources.update({path: 'project-rule' for path in dfh_project_rule_paths(root, primary)})
	except (OSError, ValueError) as exc:
		errors.append(str(exc))
	return (sources, errors)
# @used-by :func:`dfh_similar_projects_metadata()`
def _collect_group_peers(reg: Any, canon_root: Path, push_peer) -> None:
	for grp in reg.similar_project_groups:
		members = list(grp.get('members') or ())
		mem_roots = [dfh_canonicalize_root_dir(m['project'], reg) for m in members]
		if any((mr == canon_root for mr in mem_roots)) or _has_affiliated_member(members, canon_root):
			for mr in mem_roots:
				push_peer(mr)
# @used-by :func:`dfh_similar_projects_metadata()`
def _collect_peer_repo_slugs(peers: list[Path], reg: Any) -> list[str]:
	from agent_tools.issue_lifecycle import similar_project_repo_slugs
	peer_repos: list[str] = []
	seen_repos: set[str] = set()
	for p in peers:
		for slug in similar_project_repo_slugs(p, registry=reg):
			if slug.lower() not in seen_repos:
				seen_repos.add(slug.lower())
				peer_repos.append(slug)
	return peer_repos
# @used-by :func:`_collect_group_peers()`
def _has_affiliated_member(members: list[dict], canon_root: Path) -> bool:
	r = False
	for m in members:
		for aff in m.get('affiliated_paths') or ():
			try:
				aff_p = Path(aff).resolve()
				if aff_p == canon_root or aff_p.is_relative_to(canon_root):
					r = True
					break
			except OSError:
				continue
		if r:
			break
	return r
# @used-by :func:`dfh_instruction_snapshot()`
def _hash_instruction_sources(sources: dict[Path, str], errors: list[str], hash_fn) -> list[dict[str, Any]]:
	files: list[dict[str, Any]] = []
	for path, kind in sorted(sources.items(), key=lambda item: str(item[0])):
		try:
			files.append({'path': str(path.resolve()), 'kind': kind, 'sha256': hash_fn(path.read_bytes())})
		except OSError as exc:
			errors.append(str(exc))
	return files
# @used-by :func:`dfh_delegation_status()`
def _is_unpersisted_bulk(is_upwork: bool, tool_steps: int, sub_steps: int, kb_steps: int, cur_streak: int, max_src_reads: int, issue_actions_count: int) -> bool:
	return bool(is_upwork and ((tool_steps > DEL_MAX_UNPERSISTED_STEPS and 0 == sub_steps and 0 == kb_steps) or cur_streak > DEL_MAX_UNPERSISTED_STEPS or (max_src_reads >= DEL_MAX_UNPERSISTED_SOURCE_READS and 0 == sub_steps) or (tool_steps > DEL_MAX_TOTAL_STEPS_WITHOUT_SUBAGENTS and 0 == sub_steps) or (issue_actions_count > DEL_MAX_ISSUE_ACTIONS_WITHOUT_SUBAGENTS and 0 == sub_steps)))
# @used-by :func:`dfh_factual_kb_note_issues()`
def _scan_kb_touched_file(tf: Any, pp: Any, kb_prefix: str, ev_prefix: str, r: dict[str, Any], validate_fn) -> None:
	tf_norm = str(tf).replace('\\', '/').lower()
	fpath = Path(tf) if Path(tf).is_absolute() else (pp.root / Path(tf))
	fpath_low = fpath.as_posix().lower()
	in_kb = '/\ua616/kb/' in tf_norm or tf_norm.endswith('/kb/analysis.md') or tf_norm.endswith('/kb/analysis.json') or fpath_low.startswith(kb_prefix)
	in_ev = '/\ua616/kb/evidence/' in tf_norm or fpath_low.startswith(ev_prefix)
	if in_kb and (not in_ev):
		basename = Path(tf).name.lower()
		if basename in ('analysis.md', 'analysis.json'):
			r['has_analysis'] = True
			r['has_normative'] = True
		elif basename in ('project.md', 'projects.md'):
			r['has_normative'] = True
		elif fpath.is_file():
			try:
				r['issues'].extend(validate_fn(fpath, fpath.read_text(encoding='utf-8', errors='replace')))
			except OSError:
				pass
# @used-by :func:`Df.Harness.lib.completion_state._refresh_core_checks()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`agent_tools.completion._budget_status()`
def dfh_budget_status(root: str | Path, turn: dict[str, Any], *, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	folder_fn = eff_ops.get('folder') or dfh_turns_folder
	read_fn = eff_ops.get('read') or dfh_read_meta
	return BudgetEvaluator(root, turn, turns_dir=folder_fn(root), read_fn=read_fn, max_checkpoints=BUDGET_MAX_CHECKPOINTS, max_tool_steps=BUDGET_MAX_TOOL_STEPS, max_window_5h_steps=BUDGET_WINDOW_5H_MAX_STEPS).run()
# @used-by :func:`Df.Harness.lib.completion_commands._child_check_value()`
# @used-by :func:`Df.Harness.lib.completion_state._refresh_core_checks()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
def dfh_delegation_status(root: str | Path, turn: dict[str, Any]) -> dict[str, Any]:
	del_info = dict(turn.get('delegation') or {})
	tool_steps = int(del_info.get('tool_step_count') or 0)
	sub_steps = int(del_info.get('subagent_step_count') or 0)
	aa_steps = int(del_info.get('aa_subagent_step_count') if 'aa_subagent_step_count' in del_info else sub_steps)
	af_steps = int(del_info.get('af_subagent_step_count') or 0)
	kb_steps = int(del_info.get('kb_persistence_step_count') or 0)
	cur_streak = int(del_info.get('unpersisted_step_streak') if 'unpersisted_step_streak' in del_info else tool_steps if 0 == sub_steps and 0 == kb_steps else 0)
	max_streak = int(del_info.get('max_unpersisted_step_streak') if 'max_unpersisted_step_streak' in del_info else cur_streak)
	max_src_reads = int(del_info.get('max_unpersisted_source_reads') or 0)
	issue_actions_count = len(turn.get('issue_actions') or [])
	aa_part_errs = list(del_info.get('aa_partial_read_violations') or [])
	is_upwork = dfh_project_paths(root, exact_root=True).project_json.is_file()
	unpersisted = _is_unpersisted_bulk(is_upwork, tool_steps, sub_steps, kb_steps, cur_streak, max_src_reads, issue_actions_count)
	return {'verified': not unpersisted, 'tool_step_count': tool_steps, 'subagent_step_count': sub_steps, 'aa_subagent_step_count': aa_steps, 'aa_partial_read_violations': aa_part_errs, 'af_subagent_step_count': af_steps, 'kb_persistence_step_count': kb_steps, 'issue_actions_count': issue_actions_count, 'max_unpersisted_steps': DEL_MAX_UNPERSISTED_STEPS, 'unpersisted_step_streak': cur_streak, 'max_unpersisted_step_streak': max_streak, 'max_unpersisted_source_reads': max_src_reads, 'max_allowed_unpersisted_source_reads': DEL_MAX_UNPERSISTED_SOURCE_READS}
# @used-by :func:`Df.Harness.lib.completion_commands._child_check_value()`
# @used-by :func:`Df.Harness.lib.completion_state._refresh_core_checks()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`agent_tools.completion._exec5_status()`
def dfh_exec5_status(turn: dict[str, Any], root: Any=None, key: Any=None, *, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	return dfh_recoverable_step_status(turn, 'exec5_violations', 'covered_exec5_steps', root, key, ops=ops)
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__audit_workflow_scope()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_completion_checks_and_admission_guard()`
# @used-by :mod:`Df.Harness.lib.completion_checks`
def dfh_factual_kb_note_issues(root: str | Path, turn: dict[str, Any]) -> dict[str, Any]:
	from agent_tools.knowledge import validate_kb_factual_note
	pp = dfh_project_paths(root, exact_root=True)
	kb_prefix = pp.kb_dir.as_posix().lower().rstrip('/') + '/'
	ev_prefix = pp.evidence_dir.as_posix().lower().rstrip('/') + '/'
	r: dict[str, Any] = {'has_normative': False, 'has_analysis': False, 'issues': []}
	for tf in turn.get('touched_files') or []:
		_scan_kb_touched_file(tf, pp, kb_prefix, ev_prefix, r, validate_kb_factual_note)
	return r
# @used-by :func:`Df.Harness.lib.completion_state._refresh_turn_checks()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_completion_checks_and_admission_guard()`
def dfh_gate_resolved(root: str | Path, turn: dict[str, Any], value: dict[str, Any]) -> bool:
	rc = value.get('readiness_check') or {}
	gid = str(rc.get('gate_id') or '')
	rc_detail = str(rc.get('detail') or '')
	if '' == gid and rc_detail.startswith('COMPACT-1 / KB-3 violation'):
		gid = 'evicted_citations' if 'cited in response' in rc_detail else 'compaction'
	root_p = dfh_canonicalize_root_dir(root, dfh_load_registry())
	specific = next((pred(root_p, turn, value, rc) for spec_id, prefixes, pred in GATE_SPECS if spec_id == gid or ('' == gid and prefixes and rc_detail.startswith(prefixes))), False)
	return bool(specific and all((value.get(k, {}).get('verified', True) for k in VERIFIED_CHECK_KEYS)))
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
def dfh_hook_crash_status(root: str | Path, native: dict[str, Any] | None, turn: dict[str, Any], value: dict[str, Any], response: str) -> dict[str, Any]:
	return CrashAuditor(root, native, turn, value, response).run()
# @used-by :func:`Df.Harness.lib.completion_commands._child_check_value()`
# @used-by :func:`Df.Harness.lib.completion_state._refresh_core_checks()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`agent_tools.completion._http_fetch_status()`
def dfh_http_fetch_status(turn: dict[str, Any], root: Any=None, key: Any=None, *, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	return dfh_recoverable_step_status(turn, 'http_fetch_violations', 'covered_http_fetch_steps', root, key, ops=ops)
# @used-by :func:`Df.Harness.lib.completion_state._upgrade_turn_defaults()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`agent_tools.completion._instruction_snapshot()`
def dfh_instruction_snapshot(root: str | Path, native: dict[str, Any], *, stage: str, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	eff_ops = ops or {}
	pp = dfh_project_paths(root, exact_root=True)
	root_p = pp.root
	primary = Path(eff_ops.get('primary') or dfh_var_value('HARNESS_CODE')).resolve()
	settings_fn = eff_ops.get('settings') or (lambda: SettingsLoader().run())
	cfg = settings_fn()
	plat_id = native['platform']
	adapter_kind = dfh_platform_adapter_name(plat_id, (cfg.get('platforms') or {}).get(plat_id), settings_fn=settings_fn)
	sources, errors = _collect_base_instruction_sources(root_p, pp, primary, adapter_kind)
	if 'codex' == adapter_kind:
		_add_codex_guidance_sources(sources, root_p, native, cfg)
	files = _hash_instruction_sources(sources, errors, eff_ops.get('hash') or dfh_hash)
	now_fn = eff_ops.get('now') or dfh_now
	return {'captured_at': now_fn(), 'capture_stage': stage, 'sources': files, 'errors': errors, 'selection_verified': False, 'delivery_to_model_verified': False}
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :func:`Df.Harness.lib.completion_record._validate_record_preconditions()`
# @used-by :func:`agent_tools.completion._intermediate_or_language_issues()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__check_turn_hygiene()`
def dfh_intermediate_or_language_issues(requests: Any, response: str, *, ops: dict[str, Any] | None=None) -> list[str]:
	from agent_tools.source_grounding import verify_target_locale
	settings_fn = (ops or {}).get('settings')
	r: list[str] = []
	if dfh_is_waiting_status_stub(response or ''):
		r.append('FILE-3 / REVIEW-1: Response is an intermediate subagent/task waiting status stub rather than a complete final response')
	req_raw = '\n'.join((req.get('text', '') if isinstance(req, dict) else str(req) for req in requests or []))
	for err in verify_target_locale(response or '', target_locale='und', container_text=req_raw, allow_explicit_english_request=True, min_target_ratio=0.01, min_alpha=20, default_locale=dfh_default_user_locale(settings_fn=settings_fn)):
		r.append(err['message'])
	return r
# @used-by :func:`Df.Harness.lib.completion_commands._child_check_value()`
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :func:`Df.Harness.lib.completion_recovery._build_dry_run_checkpoint()`
# @used-by :func:`Df.Harness.lib.completion_state._refresh_core_checks()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`agent_tools.completion._compaction_status()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__audit_workflow_scope()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_completion_checks_and_admission_guard()`
def dfh_is_client_deliverable_path(path_text: Any, root: Any=None) -> bool:
	norm = str(path_text).replace('\\', '/').lower()
	segs = ('/letters/', '/result/', '/defects/')
	if '/\ua616/' in norm or '/\ua66e/' in norm:
		r = False
	elif None is not root:
		pp = dfh_project_paths(root, exact_root=True)
		if norm.startswith(pp.agent_dir.as_posix().lower().rstrip('/') + '/') or norm.startswith(pp.journal_root_dir.as_posix().lower().rstrip('/') + '/'):
			r = False
		else:
			segs = tuple({*segs, *(s.lower() for s in pp.deliverable_segments)})
			slot_hit = any((None is not pp.path(slot) and norm.startswith(pp.path(slot).as_posix().lower().rstrip('/') + '/') for slot in ('letters_dir', 'proposals_dir', 'articles_dir')))
			r = slot_hit or any((seg in norm for seg in segs))
	else:
		r = any((seg in norm for seg in segs))
	return r
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_issue_first_check_turn()`
# @used-by :func:`Df.Harness.lib.completion_state._initial_lifecycle_checks()`
# @used-by :func:`Df.Harness.lib.completion_state._refresh_active_turn_checks()`
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__check_turn_hygiene()`
def dfh_issue_first_status(root: str | Path, turn: dict[str, Any]) -> dict[str, Any]:
	from agent_tools.issue_first_gate import evaluate_issue_first_events
	return evaluate_issue_first_events(list(turn.get('issue_first_events') or []), requests=list(turn.get('requests') or []), project_root=root)
# @used-by :func:`agent_tools.completion._recoverable_step_status()`
# @used-by :func:`dfh_exec5_status()`
# @used-by :func:`dfh_http_fetch_status()`
def dfh_recoverable_step_status(turn: dict[str, Any], violations_key: str, covered_key: str, root: Any=None, key: Any=None, *, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	violations = list(turn.get(violations_key) or [])
	rec = dfh_violation_recovery(root, key, ops=ops) if violations else {}
	covered = set(rec.get(covered_key) or [])
	unrecovered = [item for item in violations if item.get('step') not in covered]
	r: dict[str, Any] = {'verified': not unrecovered, 'violations': violations}
	if violations and (not unrecovered):
		r['recovered_via_receipt'] = True
	return r
# @used-by :func:`Df.Harness.lib.completion_state._refresh_active_turn_checks()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
def dfh_similar_projects_metadata(root: str | Path) -> tuple[list[str], list[str]]:
	reg = dfh_load_registry()
	canon_root = dfh_canonicalize_root_dir(root, reg)
	pp = dfh_project_paths(canon_root, registry=reg, exact_root=True)
	peers: list[Path] = []
	seen_peers: set[str] = set()
	# @used-by :func:`dfh_similar_projects_metadata()`
	def _push_peer(p: Path) -> None:
		cp = dfh_canonicalize_root_dir(p, reg)
		ck = cp.as_posix().lower()
		if cp != canon_root and ck not in seen_peers:
			seen_peers.add(ck)
			peers.append(cp)
	for p in pp.similar_projects:
		_push_peer(p)
	_collect_group_peers(reg, canon_root, _push_peer)
	return ([p.as_posix() for p in peers], _collect_peer_repo_slugs(peers, reg))
# @used-by :func:`Df.Harness.lib.completion_commands._collect_check_payload()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_tdd_check_turn()`
# @used-by :func:`Df.Harness.lib.completion_state._initial_lifecycle_checks()`
# @used-by :func:`Df.Harness.lib.completion_state._refresh_active_turn_checks()`
# @used-by :func:`agent_tools.completion._completion_ops()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__check_turn_hygiene()`
def dfh_tdd_status(root: str | Path, turn: dict[str, Any]) -> dict[str, Any]:
	from agent_tools.tdd_gate import evaluate_tdd_events
	return evaluate_tdd_events(list(turn.get('tdd_events') or []), require_final_full_green=True, project_root=root)
# @used-by :func:`agent_tools.completion._violation_recovery()`
# @used-by :func:`dfh_recoverable_step_status()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_completion_checks_and_admission_guard()`
def dfh_violation_recovery(root: Any, key: Any, *, ops: dict[str, Any] | None=None) -> dict[str, Any]:
	r: dict[str, Any] = {}
	if None is not root and key:
		eff_ops = ops or {}
		path = (eff_ops.get('folder') or dfh_turns_folder)(root) / f'{key}-violation-recovery.json'
		if path.is_file():
			try:
				r = (eff_ops.get('read') or dfh_read_meta)(path)
			except (OSError, ValueError):
				r = {}
	return r
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_completion_checks_and_admission_guard()`
# @used-by :mod:`Df.Harness.lib.completion_checks`
def dfh_workflow_gate_resolved(root_p: Path, turn: dict[str, Any], kind: str) -> bool:
	wf_file = dfh_project_paths(root_p, exact_root=True).workflow_json
	if not wf_file.is_file():
		r = True
	elif 'workflow_adoption' == kind:
		from agent_tools.workflow import load
		r = {req['id'] for req in turn.get('requests') or []}.issubset({req['id'] for req in load(root_p).get('requests') or []})
	else:
		from agent_tools.review import approval_current
		from agent_tools.workflow import load
		r = bool(approval_current(root_p, load(root_p)))
	return r