# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
from Df.Harness.Path.ProjectPaths import ProjectPaths
from Df.Harness.Path.Registry import Registry
from Df.Harness.lib.path_discovery import dfh_find_local_marker_root, dfh_is_registered_single_project, dfh_refresh_known_overlay_links
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir, dfh_discover_overlay_file, dfh_infer_default_profile, dfh_journal_cache_sig
from Df.Harness.lib.path_state import DEFAULT_REGISTRY_FILE, DISCOVERY_STATE, OVERLAY_REVERSE_MAP, PROJECT_PATHS_CACHE, REGISTRY_CACHE, SHADOW_LOAD_HOOK, dfh_lookup_fast_project_paths, dfh_lru_get, dfh_lru_put, dfh_resolve_reverse_map, dfh_store_fast_project_paths
from Df.Harness.lib.path_template import dfh_env_fingerprint, dfh_is_linked, dfh_path_key
import json
import os
import stat
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_project_paths()`
def _build_or_fetch_project_paths(path_or_root: str | Path, reg: Any, env: dict[str, str] | None, exact_root: bool, journal_sig_fn: Any) -> ProjectPaths:
	root = dfh_canonicalize_root_dir(path_or_root, reg) if exact_root else dfh_resolve_project_root(path_or_root, registry=reg, env=env)
	ov_file = dfh_discover_overlay_file(root, reg, _resolved_root=True)
	ov_sig = (ov_file.as_posix(), (st := ov_file.stat()).st_mtime_ns, st.st_size, hash(ov_file.read_bytes())) if None is not ov_file else None
	cache_key = (id(reg), root.as_posix(), ov_sig, dfh_infer_default_profile(root, ov_file, reg), (journal_sig_fn or dfh_journal_cache_sig)(root, reg))
	pp = dfh_lru_get(PROJECT_PATHS_CACHE, cache_key)
	if None is pp:
		pp = ProjectPaths(root, registry=reg, env=env)
		dfh_lru_put(PROJECT_PATHS_CACHE, cache_key, pp)
	elif pp.has_overlay or pp.direct_similar_projects:
		pp.register_reverse_links()
	return pp
# @used-by :func:`dfh_relocated_harness_code_dirs()`
def _collect_relocated_code_candidates(cur_code: Path | None, reg: Any) -> list[str]:
	v2_rels = ('\u2c0f/\u227b/\u2655/\u26ef', 'Artifacts/\u227b/Deliverables/\u26ef', 'code')
	cands: list[str] = []
	if None is not cur_code:
		base = cur_code.parents[3] if cur_code.parts[-4:] in (('\u2c0f', '\u227b', '\u2655', '\u26ef'), ('Artifacts', '\u227b', 'Deliverables', '\u26ef')) else (cur_code.parent if 'code' == cur_code.name else None)
		if None is not base:
			cands.extend((str(base / rel) for rel in v2_rels))
	if reg.resolved_variables.get('HARNESS_ROOT'):
		cands.extend((f"{reg.resolved_variables['HARNESS_ROOT']}/{rel}" for rel in v2_rels))
	if isinstance(reg.harness_stores.get('legacy_primary'), str):
		cands.append(reg.harness_stores['legacy_primary'])
	return cands
# @used-by :func:`dfh_resolve_project_root()`
def _find_overlay_ancestor(start: Path, ancestors: tuple[Path, ...], reg: Any) -> Path | None:
	r: Path | None = None
	for anc in ancestors:
		if dfh_path_key(anc) in reg.workspace_overrides and anc != start:
			break
		if dfh_discover_overlay_file(anc, reg, _resolved_root=True):
			r = dfh_canonicalize_root_dir(anc, reg)
			break
	return r
# @used-by :func:`dfh_resolve_project_root()`
def _resolve_from_markers_or_reverse(start: Path, ancestors: tuple[Path, ...], reg: Any, default_registry_file: Path) -> Path:
	local_idx, local_root = dfh_find_local_marker_root(start, reg)
	rev_map = dfh_resolve_reverse_map(start, local_idx, local_root, reg, default_registry_file, DISCOVERY_STATE, OVERLAY_REVERSE_MAP, dfh_refresh_known_overlay_links)
	bound = len(ancestors) if None is local_idx else local_idx + 1
	rev_hit = next((rev_map[dfh_path_key(a)] for a in ancestors[:bound] if dfh_path_key(a) in rev_map and rev_map[dfh_path_key(a)].is_dir()), None)
	return rev_hit if None is not rev_hit else (local_root if None is not local_root else start)
# @used-by :func:`dfh_load_registry()`
def _resolve_registry_target(registry_path: str | Path | None, primary: str | Path | None, env: dict[str, str] | None, default_file: Path) -> Path:
	explicit_env = (env if None is not env else os.environ).get('HARNESS_PATHS_FILE')
	if None is not registry_path:
		r = Path(registry_path)
	elif None is not primary and (Path(primary) / 'paths.json').is_file():
		r = Path(primary) / 'paths.json'
	elif explicit_env:
		r = Path(explicit_env)
	else:
		r = default_file
	return r
# @used-by :func:`dfh_load_registry()`
def _stat_unlinked_registry(target: Path) -> tuple[Path, os.stat_result]:
	target_abs = Path(os.path.abspath(target))
	try:
		lst = os.lstat(target_abs)
		if stat.S_ISLNK(lst.st_mode) or target_abs.is_junction():
			raise ValueError(f'Linked paths.json registry refused: {target}')
	except FileNotFoundError:
		if dfh_is_linked(target):
			raise ValueError(f'Linked paths.json registry refused: {target}')
		raise
	return (target_abs, lst)
# @used-by :func:`dfh_is_tracked_workspace()`
def _workspace_is_explicitly_tracked(root: Path, reg: Any) -> bool | None:
	rk = dfh_path_key(root)
	if rk in reg.untracked_workspaces or None is not dfh_workspace_override(root, registry=reg):
		r: bool | None = False
	else:
		pp = dfh_project_paths(root, registry=reg, exact_root=True)
		if False is pp.tracked:
			r = False
		elif pp.has_overlay or pp.project_json.is_file() or pp.journal_dir.is_dir() or pp.turns_dir.is_dir():
			r = True
		else:
			r = None
	return r
# @used-by :func:`Df.Harness.lib.hook_stop_ops.dfh_tracked_workspace()`
# @used-by :func:`agent_tools.path_registry.is_tracked_workspace()`
def dfh_is_tracked_workspace(root: str | Path, *, registry: Any=None, projects_dirs: Any=None) -> tuple[bool, Path]:
	reg = registry or dfh_load_registry()
	raw_canon = dfh_canonicalize_root_dir(root, reg)
	direct = _workspace_is_explicitly_tracked(raw_canon, reg)
	if None is not direct:
		r = (direct, raw_canon)
	else:
		resolved = dfh_resolve_project_root(raw_canon, registry=reg)
		res_hit = _workspace_is_explicitly_tracked(resolved, reg) if dfh_path_key(resolved) != dfh_path_key(raw_canon) else None
		if None is not res_hit:
			r = (res_hit, resolved)
		else:
			r = (dfh_is_registered_single_project(raw_canon, registry=reg, projects_dirs=projects_dirs), raw_canon)
	return r
# @used-by :func:`Df.Harness.lib.admission_ops.dfh_resolve_admission_proof_file()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_analysis_root()`
# @used-by :func:`Df.Harness.lib.codex_metadata.dfh_codex_review_inputs()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_gate_resolved()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_similar_projects_metadata()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_begin()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_check_answer()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare_once()`
# @used-by :func:`Df.Harness.lib.completion_core.dfh_conversation_journal_steps()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_same_turn_artifact_path()`
# @used-by :func:`Df.Harness.lib.completion_recovery._scan_readonly_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_handoff_launcher_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_ratchet_ok()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_recover_checkpoint()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_similar_project_exempt()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_sync_conversation_title()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_conflict()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_load_turn_state()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_new_turn_state()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_persist_turn_recovery()`
# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_is_live_runtime_data_file()`
# @used-by :func:`Df.Harness.lib.journal_core.dfh_canonicalize_journal_dir_identity()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._overlay_needs_sync()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._sync_overlay_journal_slot()`
# @used-by :func:`Df.Harness.lib.path_discovery.dfh_default_platform_paths()`
# @used-by :func:`Df.Harness.lib.path_discovery.dfh_derive_platform_system_paths()`
# @used-by :func:`Df.Harness.lib.request_binding.dfh_canonical_path()`
# @used-by :func:`Df.Harness.lib.runtime_cache._load_uncached_settings()`
# @used-by :func:`Df.Harness.lib.runtime_validate.dfh_expand_path()`
# @used-by :func:`Df.Harness.lib.shadow_clone.dfh_shadow_isolation_context()`
# @used-by :func:`agent_tools.path_registry.load_registry()`
# @used-by :func:`dfh_is_tracked_workspace()`
# @used-by :func:`dfh_project_paths()`
# @used-by :func:`dfh_relocated_harness_code_dirs()`
# @used-by :func:`dfh_relocated_roots()`
# @used-by :func:`dfh_resolve_project_root()`
# @used-by :func:`dfh_same_project_root()`
# @used-by :func:`dfh_store_value()`
# @used-by :func:`dfh_tool_value()`
# @used-by :func:`dfh_var_value()`
# @used-by :func:`dfh_workspace_override()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__init__()`
# @used-by :meth:`Df.Harness.Journal.OpenTurnSyncer.OpenTurnSyncer.run()`
# @used-by :meth:`Df.Harness.Path.PathReporter.PathReporter.__init__()`
# @used-by :meth:`Df.Harness.Path.ProjectPaths.ProjectPaths.__init__()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.__init__()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_hook_emergency_and_path_tail()`
def dfh_load_registry(registry_path: str | Path | None=None, *, primary: str | Path | None=None, env: dict[str, str] | None=None, default_registry_file: Path=DEFAULT_REGISTRY_FILE) -> Registry:
	target = _resolve_registry_target(registry_path, primary, env, default_registry_file)
	target_abs, lst = _stat_unlinked_registry(target)
	fast_key = (os.path.normcase(str(target_abs)), lst.st_mtime_ns, lst.st_size, os.path.normcase(os.path.abspath(primary)) if None is not primary else '', dfh_env_fingerprint(env))
	cached = REGISTRY_CACHE.get(fast_key)
	if None is not cached:
		r = cached
	else:
		if dfh_is_linked(target):
			raise ValueError(f'Linked paths.json registry refused: {target}')
		resolved = target.resolve()
		r = Registry(resolved, json.loads(resolved.read_text(encoding='utf-8-sig')), primary=Path(primary) if None is not primary else None, env=env)
		if 64 < len(REGISTRY_CACHE):
			REGISTRY_CACHE.clear()
		REGISTRY_CACHE[fast_key] = r
	if None is not SHADOW_LOAD_HOOK[0]:
		r = SHADOW_LOAD_HOOK[0](r)
	return r
# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_execute_collect()`
# @used-by :func:`Df.Harness.lib.cli_input.dfh_verify_scratch_input_path()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_delegation_status()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_factual_kb_note_issues()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_instruction_snapshot()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_is_client_deliverable_path()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_similar_projects_metadata()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_workflow_gate_resolved()`
# @used-by :func:`Df.Harness.lib.completion_commands._try_launcher_handoff()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_check_answer()`
# @used-by :func:`Df.Harness.lib.completion_compaction.dfh_compaction_status()`
# @used-by :func:`Df.Harness.lib.completion_core.dfh_turns_folder()`
# @used-by :func:`Df.Harness.lib.completion_recovery._allowed_similar_peers()`
# @used-by :func:`Df.Harness.lib.config_codex.dfh_configure_codex_project()`
# @used-by :func:`Df.Harness.lib.config_codex.dfh_native_config()`
# @used-by :func:`Df.Harness.lib.config_codex.dfh_project_rule_paths()`
# @used-by :func:`Df.Harness.lib.hook_crash_ops.dfh_load_violation_receipt()`
# @used-by :func:`Df.Harness.lib.hook_markdown_ops.dfh_check_turn_budget_gate()`
# @used-by :func:`Df.Harness.lib.hook_pre_invocation_ops.dfh_scratch_answer_path()`
# @used-by :func:`Df.Harness.lib.journal.dfh_turns_dir()`
# @used-by :func:`Df.Harness.lib.journal_core.dfh_canonicalize_journal_dir_identity()`
# @used-by :func:`Df.Harness.lib.journal_core.dfh_journal_pair_names()`
# @used-by :func:`Df.Harness.lib.journal_core.dfh_resolve_journal_dir()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._sync_overlay_journal_slot()`
# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_ensure_project_journal_upgraded()`
# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_upgrade_journal()`
# @used-by :func:`Df.Harness.lib.request_binding.dfh_completion_project_id()`
# @used-by :func:`Df.Harness.lib.request_binding.dfh_native_project_fields()`
# @used-by :func:`Df.Harness.lib.request_binding.dfh_native_project_id()`
# @used-by :func:`Df.Harness.lib.shadow_command._stage_ag_from_receipt()`
# @used-by :func:`Df.Harness.lib.shadow_command.dfh_persist_shadow_replay_receipt()`
# @used-by :func:`Df.Harness.lib.storage.dfh_data_dir_for()`
# @used-by :func:`Df.Harness.lib.trace_review._arch_target_repo_roots()`
# @used-by :func:`Df.Harness.lib.trace_review.dfh_persist_review_proof()`
# @used-by :func:`_workspace_is_explicitly_tracked()`
# @used-by :func:`agent_tools.path_registry.project_paths()`
# @used-by :func:`dfh_resolve_journal_data_dir()`
# @used-by :func:`dfh_tool_value()`
# @used-by :meth:`Df.Harness.Completion.AnswerPreparer.AnswerPreparer.__init__()`
# @used-by :meth:`Df.Harness.Completion.BlockedReportAuditor.BlockedReportAuditor.__init__()`
# @used-by :meth:`Df.Harness.Completion.BudgetEvaluator.BudgetEvaluator.run()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__prepare_codex_outputs()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__finalize_codex_receipt()`
# @used-by :meth:`Df.Harness.Grounding.Doc5ReplayAuditor.Doc5ReplayAuditor.audit_saved_turns()`
# @used-by :meth:`Df.Harness.Path.PathReporter.PathReporter.__build_project_report()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.__eval_overlay_peers()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.__match_roots()`
# @used-by :meth:`Df.Harness.Path.SimilarProjectAuditor.SimilarProjectAuditor.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__resolve_day()`
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__find_reply_path()`
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__run_pre_invocation()`
# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.run()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_blocked_report_and_workflow_sync_ops()`
# @used-by :meth:`test_df_harness_s11_wave2d_completion_cov.DfHarnessS11Wave2dCompletionCovTests.test_compaction_and_response_links()`
# @used-by :meth:`test_df_harness_s11_wave2d_hook_cov.DfHarnessS11Wave2dHookCovTests.test_addon_and_markdown_ops()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_journal_integrity_and_records()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_paths_and_uri()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_hook_emergency_and_path_tail()`
def dfh_project_paths(path_or_root: str | Path, *, registry: Any=None, env: dict[str, str] | None=None, exact_root: bool=False, journal_sig_fn: Any=None) -> ProjectPaths:
	reg = registry or dfh_load_registry(env=env)
	fast_key = (id(reg), str(path_or_root), bool(exact_root))
	fast_hit = dfh_lookup_fast_project_paths(fast_key, reg, len(OVERLAY_REVERSE_MAP))
	if None is not fast_hit:
		if fast_hit.has_overlay or fast_hit.direct_similar_projects:
			fast_hit.register_reverse_links()
		r = fast_hit
	else:
		r = _build_or_fetch_project_paths(path_or_root, reg, env, exact_root, journal_sig_fn)
		dfh_store_fast_project_paths(fast_key, r, reg, len(OVERLAY_REVERSE_MAP))
	return r
# @used-by :func:`Df.Harness.lib.config_codex.dfh_project_rule_paths()`
# @used-by :func:`Df.Harness.lib.native_links.dfh_relocated_primaries()`
# @used-by :func:`agent_tools.path_registry.relocated_harness_code_dirs()`
def dfh_relocated_harness_code_dirs(*, primary: str | Path | None=None, registry: Any=None) -> tuple[Path, ...]:
	reg = registry or dfh_load_registry()
	cur_code = Path(os.path.abspath(primary)) if None is not primary else (Path(reg.resolved_variables.get('HARNESS_CODE', '')).resolve() if reg.resolved_variables.get('HARNESS_CODE') else None)
	out: list[Path] = []
	for raw in _collect_relocated_code_candidates(cur_code, reg):
		p = Path(os.path.abspath(raw))
		if (None is cur_code or dfh_path_key(p) != dfh_path_key(cur_code)) and all((dfh_path_key(p) != dfh_path_key(x) for x in out)):
			out.append(p)
	return tuple(out)
# @used-by :func:`agent_tools.path_registry.relocated_roots()`
# @used-by :mod:`agent_tools.platforms.request_binding`
def dfh_relocated_roots(*, registry: Any=None) -> dict[str, str]:
	return dict((registry or dfh_load_registry()).relocations)
# @used-by :func:`Df.Harness.lib.storage.dfh_journal_data_dir_for()`
# @used-by :func:`agent_tools.path_cache.resolve_journal_data_dir()`
def dfh_resolve_journal_data_dir(eff: Path) -> Path:
	fast_root = None
	if '\ua66e' == eff.name and eff.parent.is_dir():
		cand = eff.parent.parent if '_' == eff.parent.name and eff.parent.parent.is_dir() else eff.parent
		if ((cand / '\ua616').is_dir() or (cand / '.agents').is_dir() or (cand / '\U0001f56e').is_dir() or (cand / '_/\ua616').is_dir()) and None is dfh_workspace_override(cand):
			fast_root = cand
	return dfh_project_paths(fast_root, exact_root=True).data_dir if None is not fast_root else dfh_project_paths(eff).data_dir
# @used-by :func:`Df.Harness.lib.hook_markdown_ops.dfh_infer_project_root()`
# @used-by :func:`_build_or_fetch_project_paths()`
# @used-by :func:`agent_tools.path_registry.resolve_project_root()`
# @used-by :func:`dfh_is_tracked_workspace()`
def dfh_resolve_project_root(target: str | Path, *, registry: Any=None, env: dict[str, str] | None=None, default_registry_file: Path=DEFAULT_REGISTRY_FILE) -> Path:
	reg = registry or dfh_load_registry(env=env)
	resolved = Path(target).resolve()
	start = dfh_canonicalize_root_dir(resolved.parent if resolved.exists() and (not resolved.is_dir()) else resolved, reg)
	if dfh_path_key(start) in reg.workspace_overrides:
		r = start
	elif start.name in ('.agents', '.codex') and dfh_path_key(start.parent) in reg.workspace_overrides:
		r = start.parent
	else:
		ancestors = (start, *start.parents)
		ov_hit = _find_overlay_ancestor(start, ancestors, reg)
		r = ov_hit if None is not ov_hit else _resolve_from_markers_or_reverse(start, ancestors, reg, default_registry_file)
	return r
# @used-by :func:`Df.Harness.lib.ag_daemon.dfh_project_item_matches_root()`
# @used-by :func:`Df.Harness.lib.codex_metadata._match_review_receipt()`
# @used-by :func:`Df.Harness.lib.completion_commands._try_launcher_handoff()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_same_turn_artifact_path()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_handoff_launcher_turn()`
# @used-by :func:`Df.Harness.lib.completion_state._verify_turn_owner_and_journal()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_same_saved_request()`
# @used-by :func:`agent_tools.path_registry.same_project_root()`
def dfh_same_project_root(first: str | Path | None, second: str | Path | None, *, registry: Any=None) -> bool:
	from agent_tools.project_rename_state import same_project_root_check
	reg = registry or dfh_load_registry()
	return same_project_root_check(first, second, lambda s: dfh_canonicalize_root_dir(s, reg), dfh_path_key)
# @used-by :func:`Df.Harness.lib.cleanup_store_ops._check_legacy_manifests()`
# @used-by :func:`agent_tools.path_registry.store_path()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.run()`
def dfh_store_path(name: str, *, registry: Any=None) -> Path:
	val = dfh_store_value(name, registry=registry)
	if not isinstance(val, str):
		raise TypeError(f'Harness store {name!r} is not a single path string')
	return Path(val)
# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_resolve_cleanup_log_root()`
# @used-by :func:`agent_tools.path_registry.store_value()`
# @used-by :func:`dfh_store_path()`
def dfh_store_value(name: str, *, registry: Any=None) -> Any:
	reg = registry or dfh_load_registry()
	if name not in reg.harness_stores:
		raise KeyError(f'Unknown harness store entry: {name}')
	return deepcopy(reg.harness_stores[name])
# @used-by :func:`agent_tools.path_registry.tool_list()`
# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__normalize_arg_token()`
# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__resolve_git_from_path()`
def dfh_tool_list(name: str, *, project_root: str | Path | None=None, registry: Any=None) -> list[str]:
	val = dfh_tool_value(name, project_root=project_root, registry=registry)
	if isinstance(val, list):
		r = [str(x) for x in val]
	elif isinstance(val, str):
		r = [val]
	else:
		raise TypeError(f'Tool entry {name!r} is not a list of strings')
	return r
# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_effective_git_hooks_dir()`
# @used-by :func:`agent_tools.path_registry.tool_path()`
# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__resolve_git_from_path()`
def dfh_tool_path(name: str, *, project_root: str | Path | None=None, registry: Any=None) -> Path:
	val = dfh_tool_value(name, project_root=project_root, registry=registry)
	if not isinstance(val, str):
		raise TypeError(f'Tool entry {name!r} is not a single path string')
	return Path(val)
# @used-by :func:`agent_tools.path_registry.tool_value()`
# @used-by :func:`dfh_tool_list()`
# @used-by :func:`dfh_tool_path()`
def dfh_tool_value(name: str, *, project_root: str | Path | None=None, registry: Any=None) -> Any:
	reg = registry or dfh_load_registry()
	pp = dfh_project_paths(project_root, registry=reg) if None is not project_root else None
	if None is not pp and name in pp.tools:
		r = deepcopy(pp.tools[name])
	elif name in reg.tools:
		r = deepcopy(reg.tools[name])
	else:
		raise KeyError(f'Unknown tool entry in paths.json: {name}')
	return r
# @used-by :func:`Df.Harness.lib.cleanup_store_ops._check_legacy_manifests()`
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_rules_audit()`
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_runtime_promote()`
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_runtime_status()`
# @used-by :func:`Df.Harness.lib.completion_checks.dfh_instruction_snapshot()`
# @used-by :func:`Df.Harness.lib.completion_core.dfh_policy()`
# @used-by :func:`Df.Harness.lib.config_codex.dfh_configure_codex_project()`
# @used-by :func:`Df.Harness.lib.config_codex.dfh_primary_settings()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_legacy_project_projection_paths()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_shared_native_outputs()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_build_shared_native()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_install_native_profiles()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_retire_owned_project_projections()`
# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_runtime_store_dir()`
# @used-by :func:`agent_tools.path_registry.var_value()`
# @used-by :meth:`Df.Harness.Arch.RepoReceiptSpecification.RepoReceiptSpecification.harness_arch_root()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.run()`
# @used-by :meth:`Df.Harness.Runtime.SettingsLoader.SettingsLoader.__resolve_file()`
def dfh_var_value(name: str, *, registry: Any=None) -> str:
	reg = registry or dfh_load_registry()
	if name not in reg.resolved_variables:
		raise KeyError(f'Unknown registry variable: {name}')
	return reg.resolved_variables[name]
# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_resolve_cleanup_log_root()`
# @used-by :func:`_workspace_is_explicitly_tracked()`
# @used-by :func:`agent_tools.path_registry.workspace_override()`
# @used-by :func:`dfh_resolve_journal_data_dir()`
def dfh_workspace_override(path: str | Path, key: str | None=None, *, registry: Any=None) -> Any:
	reg = registry or dfh_load_registry()
	entry = reg.workspace_overrides.get(dfh_path_key(Path(path).resolve()))
	if None is entry:
		r = None
	else:
		r = entry.get(key) if None is not key else deepcopy(entry)
	return r
