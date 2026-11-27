# 2026-10-17 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Cleanup.Scanner import Scanner as ProjectCleanupScanner
from Df.Harness.lib.cleanup_mutation_ops import dfh_collect_folder_ancestors as _collect_folder_ancestors, dfh_finish_pending, dfh_prune_folders, dfh_remove_antigravity, dfh_restore_antigravity
from Df.Harness.lib.cleanup_store_ops import ACTIVE_CODEX_GLOBS as _ACTIVE_CODEX_GLOBS, ACTIVE_READONLY_HISTORY as _ACTIVE_READONLY_HISTORY, STATUS_NAMES as _STATUS_NAMES, dfh_age, dfh_antigravity_projects, dfh_base_age, dfh_belongs_cached, dfh_candidates, dfh_catalog_projects, dfh_codex_glob_scope as _codex_glob_scope, dfh_count_indexed_conversations, dfh_guard_history_db as _guard_history_db, dfh_legacy_initialization, dfh_linked, dfh_load_conversation_index, dfh_path_key, dfh_read_store_json as _json
from .cleanup_audit import maybe_write_cleanup_manifest, record_cleanup_answer_log
from .runtime import settings
from .storage import create_bytes, locked, replace_bytes
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :meth:`test_cleanup.CleanupTests.test_legacy_age_uses_birthtime_or_end_of_request_day_without_guessing_midnight_creation()`
def _age(root, state, config):
	return dfh_age(root, state, config)
# @used-by unused
def _base_age(root, state, config):
	return dfh_base_age(root, state, config)
# @used-by unused
def _belongs_cached(raw_path, wanted, prefix, key_cache):
	return dfh_belongs_cached(raw_path, wanted, prefix, key_cache)
# @used-by :func:`cleanup_projects()`
# @used-by :func:`conversations()`
def _count_indexed_conversations(root, ag_projects, homes, catalog, index):
	return dfh_count_indexed_conversations(root, ag_projects, homes, catalog, index)
# @used-by :func:`cleanup_projects()`
def _finish_pending(directory, root):
	dfh_finish_pending(directory, root, replace_bytes_fn=replace_bytes)
# @used-by :func:`cleanup_projects()`
# @used-by :func:`conversations()`
# @used-by :meth:`test_cleanup.CleanupTests.test_project_cleanup_scanner_reuses_single_pass_history_index_in_dry_run()`
def _load_conversation_index(backend, homes):
	return dfh_load_conversation_index(backend, homes)
# @used-by :func:`cleanup_projects()`
def antigravity_projects(directory, root):
	return dfh_antigravity_projects(directory, root)
# @used-by :func:`cleanup_projects()`
def candidates(daily, config, now):
	return dfh_candidates(daily, config, now)
# @used-by :func:`cleanup_projects()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_single_enabled_codex_instance_works_with_shared_catalog_superset()`
def catalog_projects(catalog, root, homes):
	return dfh_catalog_projects(catalog, root, homes)
# @used-by :meth:`Df.Harness.Upwork.CliRunner.CliRunner.__run_cleanup()`
# @used-by :meth:`test_cleanup.CleanupTests.run_cleanup()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_apply_persists_sidecar_manifest_with_rollback_snapshots_while_dry_run_stays_readonly()`
# @used-by :meth:`test_cleanup_audit.CleanupAuditTests.test_cleanup_report_writes_metadata_header_links_manifest_and_consumes_scratch_file()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests._run_cleanup_no_codex()`
# @used-by :meth:`test_cleanup_lifecycle.CleanupLifecycleTests._run_cleanup()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_all_disabled_and_claude_code_only_environment_without_antigravity_or_codex()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_custom_system_paths_stop_gate_and_claude_code_only_extensibility()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_per_instance_folders_json_uninitialized_instance_and_stop_gate_a6()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_cleanup_skips_disabled_codex_and_checks_all_enabled_antigravity_instances()`
# @used-by :meth:`test_instances_config.RuntimeInstancesTests.test_dynamic_folders_json_and_cleanup_without_homes()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_cleanup_integration()`
def cleanup_projects(*, apply=False, daily_root=None, now=None, config=None, ag_directory=None, ag_backend=None, folders=None, control=None):
	ops = {
		'antigravity_projects': antigravity_projects,
		'candidates': candidates,
		'catalog_projects': catalog_projects,
		'conversations': conversations,
		'count_indexed': _count_indexed_conversations,
		'default_conversations': _DEFAULT_CONVERSATIONS,
		'finish_pending': _finish_pending,
		'load_index': _load_conversation_index,
		'maybe_manifest': maybe_write_cleanup_manifest,
		'remove_antigravity': remove_antigravity,
		'restore_antigravity': restore_antigravity,
		'settings': settings,
	}
	return ProjectCleanupScanner(apply=apply, daily_root=daily_root, now=now, config=config, ag_directory=ag_directory, ag_backend=ag_backend, folders=folders, control=control, _ops=ops).run()
# @used-by :func:`cleanup_projects()`
# @used-by :meth:`test_cleanup.CleanupTests.test_changed_native_payload_during_final_check_is_never_unlinked()`
# @used-by :meth:`test_cleanup.CleanupTests.test_chat_after_native_unlink_restores_both_registrations_and_folder_assignment()`
# @used-by :meth:`test_cleanup.CleanupTests.test_new_conversation_after_preview_is_rechecked_before_any_delete()`
# @used-by :mod:`agent_tools.cleanup`
def conversations(root, ag_projects, backend, homes, catalog):
	return _count_indexed_conversations(root, ag_projects, homes, catalog, _load_conversation_index(backend, homes))
_DEFAULT_CONVERSATIONS = conversations
# @used-by unused
def legacy_initialization(root):
	return dfh_legacy_initialization(root)
# @used-by :func:`record_cleanup_answer()`
def linked(path):
	return dfh_linked(path)
# @used-by :meth:`test_cleanup.CleanupTests.test_file_uri_with_drive_in_authority_is_the_same_local_workspace()`
def path_key(value):
	return dfh_path_key(value)
# @used-by :meth:`test_cleanup.CleanupTests.test_only_newly_emptied_folder_ancestors_are_pruned()`
def prune_folders(value, removed_ids):
	return dfh_prune_folders(value, removed_ids)
# @used-by :func:`agent_tools.cleanup_audit.run_cleanup_report_cli()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_empty_answer_or_naive_timestamp_does_not_create_a_log()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_exact_answer_and_filename_use_the_same_istanbul_time_across_utc_midnight()`
# @used-by :meth:`test_cleanup.CleanupReportTests.test_repeated_and_concurrent_answers_never_overwrite_logs_in_the_same_minute()`
def record_cleanup_answer(body, *, now=None, log_root=None, config=None, manifest_path=None, project_root=None, env=None):
	return record_cleanup_answer_log(body, now=now, log_root=log_root, config=config, manifest_path=manifest_path, project_root=project_root, env=env, settings_fn=settings, linked_fn=linked)
# @used-by :func:`cleanup_projects()`
def remove_antigravity(root, directory, folders, expected, check):
	return dfh_remove_antigravity(root, directory, folders, expected, check, replace_bytes_fn=replace_bytes)
# @used-by :func:`cleanup_projects()`
def restore_antigravity(root, directory, folders):
	return dfh_restore_antigravity(root, directory, folders, create_bytes_fn=create_bytes, replace_bytes_fn=replace_bytes)
