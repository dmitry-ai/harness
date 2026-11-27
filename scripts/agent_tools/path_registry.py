# 2026-11-19 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Path.PathReporter import PathReporter
from Df.Harness.Path.ProjectPaths import ProjectPaths
from Df.Harness.Path.Registry import Registry as PathRegistry
from Df.Harness.Path.SimilarProjectAuditor import SimilarProjectAuditor
from Df.Harness.lib.path_discovery import dfh_candidate_discovery_roots, dfh_default_platform_paths, dfh_derive_platform_system_paths, dfh_find_local_marker_root, dfh_is_registered_single_project, dfh_refresh_known_overlay_links
from Df.Harness.lib.path_resolve import dfh_is_tracked_workspace, dfh_load_registry, dfh_project_paths, dfh_relocated_harness_code_dirs, dfh_relocated_roots, dfh_resolve_project_root, dfh_same_project_root, dfh_store_path, dfh_store_value, dfh_tool_list, dfh_tool_path, dfh_tool_value, dfh_var_value, dfh_workspace_override
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir, dfh_discover_overlay_file, dfh_has_v2_markers, dfh_infer_default_profile, dfh_inspect_journal_dir_on_disk, dfh_journal_cache_sig, dfh_v2_software_deliverable_dir, dfh_validate_overlay, dfh_validate_similar_project_groups
from Df.Harness.lib.path_state import DISCOVERY_STATE as _DISCOVERY_STATE, OVERLAY_REVERSE_MAP as _OVERLAY_REVERSE_MAP, PROJECT_PATHS_CACHE as _PROJECT_PATHS_CACHE, REGISTRY_CACHE as _REGISTRY_CACHE, SIMILAR_REVERSE_MAP as _SIMILAR_REVERSE_MAP, dfh_clear_registry_cache
from Df.Harness.lib.path_template import ESC_DOLLAR as _ESC_DOLLAR, ESC_PERCENT as _ESC_PERCENT, EXCLUDED_PROJECT_IDS as _EXCLUDED_PROJECT_IDS, INITIAL_HOME as _INITIAL_HOME, JOURNAL_BUCKET_DIR_RE as _JOURNAL_BUCKET_DIR_RE, SIMILAR_GROUP_ID_RE as _SIMILAR_GROUP_ID_RE, TOKEN_RE as _TOKEN_RE, URI_SCHEME_RE as _URI_SCHEME_RE, VAR_NAME_RE as _VAR_NAME_RE, dfh_canonical_journal_bucket, dfh_env_fingerprint, dfh_escape_template_literal, dfh_expand_structure, dfh_expand_template, dfh_glob_parent_stat, dfh_infer_harness_anchor, dfh_is_linked, dfh_lookup_env, dfh_normalize_path_str, dfh_path_key, dfh_resolve_os_user_home, dfh_resolve_process_home, dfh_validate_string_list, dfh_validate_string_map, dfh_validate_variables_map
from .path_cache import clear_path_cache, default_runtime_file, get_ttl_overlay_links, lookup_fast_project_paths, lru_get, lru_put, mark_overlay_links_refreshed, overlay_signature_for_roots, resolve_code_anchor, resolve_reverse_map, store_fast_project_paths
_CODE_ANCHOR = resolve_code_anchor(Path(__file__).resolve().parents[2])
DEFAULT_REGISTRY_FILE = Path(__file__).resolve().parents[2] / 'paths.json'
# @used-by :func:`_refresh_known_overlay_links()`
# @used-by :func:`agent_tools.issues.repo_locator._index_discovery_roots()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_refresh_known_overlay_links_uses_ttl_and_resets_on_clear()`
def _candidate_discovery_roots(reg: PathRegistry) -> tuple[tuple, tuple[Path, ...]]:
	return dfh_candidate_discovery_roots(reg)
# @used-by :func:`project_paths()`
def _journal_cache_sig(root: Path, reg: PathRegistry) -> tuple:
	return dfh_journal_cache_sig(root, reg)
# @used-by :func:`agent_tools.research.inside()`
# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
def _path_key(value: str | Path) -> str:
	return dfh_path_key(value)
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_refresh_known_overlay_links_uses_ttl_and_resets_on_clear()`
def _refresh_known_overlay_links(reg: PathRegistry) -> dict[str, Path]:
	return dfh_refresh_known_overlay_links(reg, candidate_roots_fn=_candidate_discovery_roots, default_registry_file=DEFAULT_REGISTRY_FILE)
# @used-by :func:`agent_tools.context.assemble()`
# @used-by :func:`agent_tools.context.generate()`
# @used-by :func:`agent_tools.issues.parity.check_similar_project_parity()`
# @used-by :func:`agent_tools.meta.builders.build_github_issue_metadata()`
# @used-by :func:`agent_tools.meta.builders.build_journal_metadata()`
# @used-by :func:`agent_tools.meta.builders.build_problem_metadata()`
# @used-by :func:`agent_tools.meta.identity.resolve_project_identity()`
# @used-by :func:`agent_tools.review.read_package_envelope()`
# @used-by :func:`agent_tools.tdd.mechanical.record_mechanical_exemption()`
# @used-by :func:`agent_tools.text_workflow._roots()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.is_issue_tracked()`
# @used-by :meth:`agent_tools.review.ReviewReportValidator.__init__()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.__init__()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_df_servers_relocation_and_nested_server_artifact_root()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
def canonicalize_root_dir(value: str | Path, *, registry: PathRegistry | None=None) -> Path:
	return dfh_canonicalize_root_dir(value, registry or load_registry())
# @used-by :func:`agent_tools.project_rename._apply_rename_mutations()`
# @used-by :func:`agent_tools.project_rename._rollback_rename()`
# @used-by :func:`git_fixture_cache._clear_harness_caches()`
# @used-by :func:`test_historical_admission._restore_tree_in_place()`
# @used-by :meth:`test_path_registry.PathRegistryTests.tearDown()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.tearDown()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_project_paths_lru_retains_more_than_256_entries()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_refresh_known_overlay_links_uses_ttl_and_resets_on_clear()`
# @used-by :meth:`test_repo_locator_perf.RepoLocatorPerformanceTests.tearDown()`
# @used-by :meth:`test_repo_locator_perf.RepoLocatorPerformanceTests.test_pruned_walk_skips_heavy_dirs_and_respects_ttl_cache_and_reset()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_evidence_loader_reuses_saved_extracted_html_and_caches_fragment_parse()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_runtime_settings_cache_invalidates_on_file_or_env_change_and_isolates_mutations()`
def clear_registry_cache() -> None:
	dfh_clear_registry_cache()
# @used-by :func:`agent_tools.upwork_project.antigravity_global_config_dirs()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
def default_platform_paths(adapter_kind: str, *, home: str | Path | None=None, user_data_dir: str | Path | None=None, registry: PathRegistry | None=None) -> dict[str, str]:
	return dfh_default_platform_paths(adapter_kind, home=home, user_data_dir=user_data_dir, registry=registry)
# @used-by unused
def derive_platform_system_paths(adapter_kind: str, explicit_paths: dict[str, str] | None=None, *, home: str | Path | None=None, user_data_dir: str | Path | None=None, plat_cfg: dict[str, Any] | None=None, registry: PathRegistry | None=None) -> dict[str, str]:
	return dfh_derive_platform_system_paths(adapter_kind, explicit_paths, home=home, user_data_dir=user_data_dir, plat_cfg=plat_cfg, registry=registry)
# @used-by unused
def discover_overlay_file(root: str | Path, *, registry: PathRegistry | None=None, _resolved_root: bool=False) -> Path | None:
	return dfh_discover_overlay_file(root, registry or load_registry(), _resolved_root=_resolved_root)
# @used-by unused
def escape_template_literal(value: str) -> str:
	return dfh_escape_template_literal(value)
# @used-by :func:`agent_tools.issues.parity.check_similar_project_parity()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
def evaluate_similar_project_touches(touched_repo_files: list[Path] | tuple[Path, ...] | set[Path], *, registry: PathRegistry | None=None) -> list[dict[str, Any]]:
	return SimilarProjectAuditor(touched_repo_files, registry=registry).run()
# @used-by unused
def expand_structure(value: Any, variables: dict[str, str], *, env: dict[str, str] | None=None) -> Any:
	return dfh_expand_structure(value, variables, env=env)
# @used-by :func:`agent_tools.polyglot_land._expand_token()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_apache_prefix_concatenation_windows_env_vars_globs_and_escapes()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_template_and_schema_error_paths_reject_cycles_unknowns_symlinks_and_conflicts()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_transitive_escapes_literal_dollar_in_env_and_relative_slot_anchoring()`
def expand_template(template: str, variables: dict[str, str], *, env: dict[str, str] | None=None, normalize: bool=True, _resolving: tuple[str, ...]=()) -> str:
	return dfh_expand_template(template, variables, env=env, normalize=normalize, _resolving=_resolving)
# @used-by :meth:`test_path_registry.PathRegistryTests.test_is_tracked_workspace_supports_registered_single_projects_and_declarative_opt_outs()`
def is_tracked_workspace(root: str | Path, *, registry: PathRegistry | None=None, projects_dirs=None) -> tuple[bool, Path]:
	return dfh_is_tracked_workspace(root, registry=registry, projects_dirs=projects_dirs)
# @used-by :func:`agent_tools.issues.repo_locator._search_registry_and_roots()`
# @used-by :func:`agent_tools.polyglot_land.resolve_repo_verification_spec()`
# @used-by :func:`agent_tools.research.inside()`
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
# @used-by :func:`canonicalize_root_dir()`
# @used-by :func:`discover_overlay_file()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_custom_overlay_end_to_end_context_workflow_text_diagnostics_and_completion_canonicalization()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_is_tracked_workspace_supports_registered_single_projects_and_declarative_opt_outs()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_mid_process_overlay_creation_and_edit_invalidate_reverse_links_and_stay_fast()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_redirected_userprofile_separates_os_user_home_preserves_sandboxes_and_auto_detects_a6()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_template_and_schema_error_paths_reject_cycles_unknowns_symlinks_and_conflicts()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_refresh_known_overlay_links_uses_ttl_and_resets_on_clear()`
def load_registry(registry_path: str | Path | None=None, *, primary: str | Path | None=None, env: dict[str, str] | None=None) -> PathRegistry:
	return dfh_load_registry(registry_path, primary=primary, env=env, default_registry_file=DEFAULT_REGISTRY_FILE)
# @used-by unused
def normalize_path_str(raw: str, *, preserve_trailing_slash: bool=False) -> str:
	return dfh_normalize_path_str(raw, preserve_trailing_slash=preserve_trailing_slash)
# @used-by :func:`agent_tools.upwork_project.doctor()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_registry_and_runtime_contain_no_hardcoded_host_paths_outside_r_and_validate_five_overlays()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
def paths_report(project: str | Path | None=None, *, expand: str | None=None, check: bool=False, registry: PathRegistry | None=None) -> dict[str, Any]:
	return PathReporter(project, expand=expand, check=check, registry=registry).run()
# @used-by :func:`agent_tools.analysis.publish_analysis()`
# @used-by :func:`agent_tools.analysis.publish_owned()`
# @used-by :func:`agent_tools.analysis.save_analysis()`
# @used-by :func:`agent_tools.analysis_merge.save_merged_analysis()`
# @used-by :func:`agent_tools.arch.review_store._arch_dir()`
# @used-by :func:`agent_tools.arch.review_store._load_verified_package()`
# @used-by :func:`agent_tools.arch.review_store.prepare_arch_package()`
# @used-by :func:`agent_tools.arch.review_store.read_arch_review_input()`
# @used-by :func:`agent_tools.arch.review_store.record_arch_review()`
# @used-by :func:`agent_tools.claims._manifest_primary()`
# @used-by :func:`agent_tools.context.assemble()`
# @used-by :func:`agent_tools.context.default_context_config()`
# @used-by :func:`agent_tools.context.generate()`
# @used-by :func:`agent_tools.doc5_context._workspace_repo_slugs()`
# @used-by :func:`agent_tools.doc5_replay_audit.audit_local_saved_turns()`
# @used-by :func:`agent_tools.evidence.local_file()`
# @used-by :func:`agent_tools.evidence.source_reference()`
# @used-by :func:`agent_tools.evidence_loader.resolve_http_observation()`
# @used-by :func:`agent_tools.experiments.result_issues()`
# @used-by :func:`agent_tools.gates.external_write._check_df_issue_turn_intent()`
# @used-by :func:`agent_tools.gates.external_write._match_upwork_root()`
# @used-by :func:`agent_tools.git_ignore.prepare_worktrees_base_dir()`
# @used-by :func:`agent_tools.intake._index()`
# @used-by :func:`agent_tools.intake._project()`
# @used-by :func:`agent_tools.intake._receipt()`
# @used-by :func:`agent_tools.intake._snapshot()`
# @used-by :func:`agent_tools.intake._validate_receipt()`
# @used-by :func:`agent_tools.intake.commit_capture()`
# @used-by :func:`agent_tools.issue_first_inherit._candidate_project_roots()`
# @used-by :func:`agent_tools.issues.acceptance_gate._load_acceptance_receipt()`
# @used-by :func:`agent_tools.issues.comment_grounding._resolve_grounding_root()`
# @used-by :func:`agent_tools.issues.parity._load_similar_project_exemptions()`
# @used-by :func:`agent_tools.issues.parity._peer_code_repo_candidates()`
# @used-by :func:`agent_tools.issues.repo_locator._append_peer_repos()`
# @used-by :func:`agent_tools.issues.repo_locator._append_project_paths()`
# @used-by :func:`agent_tools.issues.repo_locator._index_discovery_roots()`
# @used-by :func:`agent_tools.issues.service_helpers.pending_similar_peer_slugs()`
# @used-by :func:`agent_tools.issues.service_helpers.resolve_metadata_project_root()`
# @used-by :func:`agent_tools.issues.turn_scope._candidate_turns_dirs()`
# @used-by :func:`agent_tools.knowledge._load_media_descriptions()`
# @used-by :func:`agent_tools.knowledge.build_project_extra_sources()`
# @used-by :func:`agent_tools.knowledge.populate_agent_kb()`
# @used-by :func:`agent_tools.knowledge.sync_initial_website()`
# @used-by :func:`agent_tools.knowledge.sync_project_attachments_and_kb()`
# @used-by :func:`agent_tools.knowledge.sync_website_card()`
# @used-by :func:`agent_tools.landing_lease._lease_file_for()`
# @used-by :func:`agent_tools.meta.builders._find_issue_state_pair()`
# @used-by :func:`agent_tools.meta.builders.build_journal_metadata()`
# @used-by :func:`agent_tools.meta.identity._lookup_name_from_project_json()`
# @used-by :func:`agent_tools.metrics._save_executor_metadata()`
# @used-by :func:`agent_tools.metrics.project_metrics()`
# @used-by :func:`agent_tools.polyglot_land._sandbox_root()`
# @used-by :func:`agent_tools.project_card.sync_block()`
# @used-by :func:`agent_tools.project_drift.domain_drift_issues()`
# @used-by :func:`agent_tools.project_drift.require_no_domain_drift_for_finalize()`
# @used-by :func:`agent_tools.project_rename._ag_id_from_receipt()`
# @used-by :func:`agent_tools.project_rename._sync_registrations()`
# @used-by :func:`agent_tools.project_rename._validate_rename_inputs()`
# @used-by :func:`agent_tools.project_rename.maybe_promote_project_domain()`
# @used-by :func:`agent_tools.project_rename_state._update_project_json()`
# @used-by :func:`agent_tools.project_rename_state.migrate_journal_state()`
# @used-by :func:`agent_tools.project_rename_state.refresh_workflow_file_hash()`
# @used-by :func:`agent_tools.project_rename_state.rewrite_launcher_handoffs()`
# @used-by :func:`agent_tools.project_rename_state.rewrite_project_internal_state()`
# @used-by :func:`agent_tools.project_rename_verify._launcher_stale_files()`
# @used-by :func:`agent_tools.project_rename_verify._probe_workflow()`
# @used-by :func:`agent_tools.red_flags.sync_project_red_flags()`
# @used-by :func:`agent_tools.registration._begin()`
# @used-by :func:`agent_tools.registration._expected()`
# @used-by :func:`agent_tools.registration._read()`
# @used-by :func:`agent_tools.registration.save_registration()`
# @used-by :func:`agent_tools.repo_wait._active_turn_touched_paths()`
# @used-by :func:`agent_tools.repo_wait._workspace_code_repos()`
# @used-by :func:`agent_tools.research.collect()`
# @used-by :func:`agent_tools.research.compute_site_summary()`
# @used-by :func:`agent_tools.research.evidence_query()`
# @used-by :func:`agent_tools.research.extract_file()`
# @used-by :func:`agent_tools.research.extract_observation()`
# @used-by :func:`agent_tools.research.load_observation()`
# @used-by :func:`agent_tools.research.observed_use()`
# @used-by :func:`agent_tools.review._analysis()`
# @used-by :func:`agent_tools.review.disposition()`
# @used-by :func:`agent_tools.review.load_verified_claims_cache()`
# @used-by :func:`agent_tools.review.prepare()`
# @used-by :func:`agent_tools.review.prepare_verdict_record()`
# @used-by :func:`agent_tools.review.update_verified_claims_cache()`
# @used-by :func:`agent_tools.source_grounding.load_fact_ledger()`
# @used-by :func:`agent_tools.tdd.classifier._resolve_deleted_worktree_scope()`
# @used-by :func:`agent_tools.tdd.mechanical._candidate_recipe_dirs()`
# @used-by :func:`agent_tools.tdd.mechanical.record_mechanical_exemption()`
# @used-by :func:`agent_tools.tdd.ratchet._turn_receipt_dirs()`
# @used-by :func:`agent_tools.text_browser._endpoint_lock()`
# @used-by :func:`agent_tools.text_browser.save_cdp_identity()`
# @used-by :func:`agent_tools.text_claims.registry_path()`
# @used-by :func:`agent_tools.text_claims.save_registry()`
# @used-by :func:`agent_tools.text_sources._evaluate()`
# @used-by :func:`agent_tools.text_workflow._folder()`
# @used-by :func:`agent_tools.upwork_project.check_configuration()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :func:`agent_tools.upwork_project.default_context_config()`
# @used-by :func:`agent_tools.upwork_project.initialize_upwork_project()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :func:`agent_tools.worker_semaphore.default_slots_dir()`
# @used-by :func:`agent_tools.workflow.evidence_paths()`
# @used-by :func:`agent_tools.workflow.kb_paths()`
# @used-by :func:`agent_tools.worktree_flow._resolve_deleted_worktree_file()`
# @used-by :func:`agent_tools.worktree_flow._run_land_checks()`
# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
# @used-by :func:`test_arch_review_cli._init_text_workspace()`
# @used-by :meth:`agent_tools.experiments.ExperimentPlanStore.__init__()`
# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator._verify_saved_artifacts()`
# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.load()`
# @used-by :meth:`agent_tools.experiments.ExperimentRunValidator.record()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate._tdd_project_root()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.is_issue_tracked()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._collect_repos_and_issues()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._target_for_project_root()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.evidence_issue_files()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.issue_target_for_path()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.meta_dir_for_project_root()`
# @used-by :meth:`agent_tools.knowledge.AttachmentInventory.__init__()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._check_kb_membership()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._collect_client_urls()`
# @used-by :meth:`agent_tools.response_grounding.ResponseEvidenceAuditor._ingest_evidence_files()`
# @used-by :meth:`agent_tools.source_grounding.Tier0SourceIndex.__init__()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_ancestry_scope()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.__init__()`
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor.__init__()`
# @used-by :meth:`agent_tools.workflow.ResearchQuestionRegistry.__init__()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.__init__()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.adopt_requests()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.record_current_answer()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.resume()`
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.test_blocked_report_records_journal_despite_hygiene_failures_and_allows_doc5()`
# @used-by :meth:`test_blocked_report_hygiene_and_doc5_m2.BlockedReportHygieneAndDoc5M2Tests.test_blocked_report_still_rejects_client_claim_ids_inside_doc5()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_is_tracked_workspace_supports_registered_single_projects_and_declarative_opt_outs()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_template_and_schema_error_paths_reject_cycles_unknowns_symlinks_and_conflicts()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_transitive_escapes_literal_dollar_in_env_and_relative_slot_anchoring()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_project_paths_fast_cache_hits_and_invalidates_on_fs_mutations()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_project_paths_lru_retains_more_than_256_entries()`
# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_automatic_journal_only_upgrade_and_cli_subcommand()`
def project_paths(path_or_root: str | Path, *, registry: PathRegistry | None=None, env: dict[str, str] | None=None, exact_root: bool=False) -> ProjectPaths:
	return dfh_project_paths(path_or_root, registry=registry, env=env, exact_root=exact_root, journal_sig_fn=_journal_cache_sig)
# @used-by :func:`agent_tools.upwork_project.check_configuration()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
def relocated_harness_code_dirs(*, primary: str | Path | None=None, registry: PathRegistry | None=None) -> tuple[Path, ...]:
	return dfh_relocated_harness_code_dirs(primary=primary, registry=registry)
# @used-by unused
def relocated_roots(*, registry: PathRegistry | None=None) -> dict[str, str]:
	return dfh_relocated_roots(registry=registry)
# @used-by :func:`agent_tools.analysis.publish_analysis()`
# @used-by :func:`agent_tools.issues.comment_grounding._resolve_grounding_root()`
# @used-by :func:`agent_tools.issues.service_helpers.resolve_metadata_project_root()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_mid_process_overlay_creation_and_edit_invalidate_reverse_links_and_stay_fast()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_resolve_project_root_skips_host_overlay_scan_for_temp_subdirs()`
def resolve_project_root(target: str | Path, *, registry: PathRegistry | None=None, env: dict[str, str] | None=None) -> Path:
	return dfh_resolve_project_root(target, registry=registry, env=env, default_registry_file=DEFAULT_REGISTRY_FILE)
# @used-by :func:`agent_tools.research.inside()`
# @used-by :func:`agent_tools.review.read_package_envelope()`
# @used-by :meth:`agent_tools.experiments.ExperimentPlanStore._is_plan_commit()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.operation_meta()`
# @used-by :meth:`agent_tools.text_workflow.ClientTextWorkspace.read_check()`
# @used-by :meth:`agent_tools.text_workflow.TextIntegrityVerifier.reconciled_integrity()`
# @used-by :meth:`agent_tools.workflow.WorkflowStateEngine.load()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_df_servers_relocation_and_nested_server_artifact_root()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage()`
def same_project_root(first: str | Path | None, second: str | Path | None, *, registry: PathRegistry | None=None) -> bool:
	return dfh_same_project_root(first, second, registry=registry)
# @used-by :func:`agent_tools.intake._project()`
# @used-by :func:`agent_tools.project_rename._update_projects_index()`
# @used-by :func:`agent_tools.upwork_project.resolve_or_create_project_dir()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._target_for_project_root()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.evidence_issue_files()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.issue_target_for_path()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.resolve_issue_targets()`
# @used-by :mod:`agent_tools.intake`
# @used-by :mod:`agent_tools.runtime`
def store_path(name: str, *, registry: PathRegistry | None=None) -> Path:
	return dfh_store_path(name, registry=registry)
# @used-by :func:`agent_tools.issues.repo_locator._search_registry_and_roots()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.resolve_issue_targets()`
def store_value(name: str, *, registry: PathRegistry | None=None) -> Any:
	return dfh_store_value(name, registry=registry)
# @used-by :func:`agent_tools.git_gate.cleanup_stale_credential_locks()`
# @used-by :func:`agent_tools.text_core.default_shell()`
# @used-by :func:`agent_tools.upwork_data._find_poppler_tool()`
def tool_list(name: str, *, project_root: str | Path | None=None, registry: PathRegistry | None=None) -> list[str]:
	return dfh_tool_list(name, project_root=project_root, registry=registry)
# @used-by :func:`agent_tools.polyglot_land._resolve_node_exe()`
# @used-by :mod:`agent_tools.git_gate`
# @used-by :mod:`agent_tools.runtime`
def tool_path(name: str, *, project_root: str | Path | None=None, registry: PathRegistry | None=None) -> Path:
	return dfh_tool_path(name, project_root=project_root, registry=registry)
# @used-by unused
def tool_value(name: str, *, project_root: str | Path | None=None, registry: PathRegistry | None=None) -> Any:
	return dfh_tool_value(name, project_root=project_root, registry=registry)
# @used-by :meth:`test_path_registry.PathRegistryTests.test_df_servers_relocation_and_nested_server_artifact_root()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_similar_projects_groups_symmetric_overlays_affiliated_paths_and_validation()`
# @used-by :mod:`agent_tools.runtime`
def var_value(name: str, *, registry: PathRegistry | None=None) -> str:
	return dfh_var_value(name, registry=registry)
# @used-by :func:`agent_tools.text_browser._endpoint_lock()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace._target_for_project_root()`
# @used-by :meth:`agent_tools.issues.workspace.IssueEvidenceWorkspace.issue_target_for_path()`
def workspace_override(path: str | Path, key: str | None=None, *, registry: PathRegistry | None=None) -> Any:
	return dfh_workspace_override(path, key, registry=registry)
