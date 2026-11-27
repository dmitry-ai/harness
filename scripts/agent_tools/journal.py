# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Journal.Publisher import Publisher
from Df.Harness.lib.journal_core import JOURNAL_BUCKET_SIZE, JOURNAL_RANGE_SEP, TURN_RESERVATIONS_FILE, V1_PAIR, V2_PAIR, _BUCKET_DIR_RE, _LEGACY_ANALYSIS_NAMES, dfh_canonicalize_journal_dir_identity as canonicalize_journal_dir_identity, dfh_detect_journal_version as detect_journal_version, dfh_digest as digest, dfh_find_step_file as find_step_file, dfh_is_bucket_dir_name as is_bucket_dir_name, dfh_is_step_md as _is_step_md, dfh_iter_side_step_files as iter_side_step_files, dfh_journal_bucket_bounds as journal_bucket_bounds, dfh_journal_bucket_name as journal_bucket_name, dfh_journal_pair_dirs as journal_pair_dirs, dfh_journal_pair_names as journal_pair_names, dfh_norm_journal_response_text as norm_journal_response_text, dfh_norm_journal_text as norm_journal_text, dfh_parse_step_file_path as parse_step_file_path, dfh_raw_state_dir as _raw_state_dir, dfh_resolve_journal_dir as resolve_journal_dir, dfh_resolve_migrated_step_file as resolve_migrated_step_file, dfh_same_journal_identity as same_journal_identity, dfh_state_dir as state_dir, dfh_step_file as step_file, dfh_strip_local_file_scheme as strip_local_file_scheme
from Df.Harness.lib.journal_records import dfh_answer_groups as answer_groups, dfh_completed_request_group_index as completed_request_group_index, dfh_find_orphan_or_overwritten_steps as find_orphan_or_overwritten_steps, dfh_get_existing_step_ids as get_existing_step_ids, dfh_iter_answer_group_records as iter_answer_group_records, dfh_matching_group_response as matching_group_response, dfh_publish_step, dfh_record_step, dfh_recover_step, dfh_step_errors as step_errors, dfh_validate_payload as _payload, dfh_validate_step as validate_step, dfh_verify_answer as verify_answer
from Df.Harness.lib.journal_reservations import dfh_iter_turn_reservations as iter_turn_reservations, dfh_read_turn_reservations as _read_turn_reservations, dfh_release_turn_steps as release_turn_steps, dfh_reserve_turn_steps as reserve_turn_steps, dfh_reserved_step_ids as reserved_step_ids, dfh_write_turn_reservations as _write_turn_reservations
from Df.Harness.lib.journal_upgrade import dfh_ensure_project_journal_upgraded as ensure_project_journal_upgraded, dfh_upgrade_journal as upgrade_journal
from .storage import create_bytes, data_dir_for, journal_data_dir_for, locked, replace_bytes
# @used-by :func:`record_answer()`
# @used-by :func:`record_step()`
# @used-by :func:`recover_step()`
def _publish(directory: Path, step: int, state: dict, *, recovering: bool=False) -> None:
	dfh_publish_step(directory, step, state, recovering=recovering, create_bytes_fn=create_bytes)
# @used-by :func:`Df.Harness.lib.text_workflow.dfh_record_text_answer()`
# @used-by :func:`test_project_rename._seed_project_artifacts()`
# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.__resolve_steps()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_record_answer_subtracts_overlapping_request_ids_and_excludes_stale_steps_from_title()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_group_crash_reserves_all_numbers_and_preserves_previous_context()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_legacy_complete_group_without_turn_state_exposes_proof_gap_without_readmission()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_matching_native_request_ids_reuse_an_existing_record_answer_group()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_old_exact_native_turn_receipts_are_not_duplicated()`
def record_answer(directory, requests, response, turn, request_ids=None, *, adopt_steps=None, admission=None, admission_roots=None, allow_reprepare=False, reserved_turn_key=None):
	return Publisher(directory, requests, response, turn, request_ids, adopt_steps=adopt_steps, admission=admission, admission_roots=admission_roots, allow_reprepare=allow_reprepare, reserved_turn_key=reserved_turn_key, ops={'create_bytes': create_bytes, 'publish': _publish}).run()
# @used-by :meth:`test_agent_tools.JournalTests.test_empty_payload_has_no_side_effect()`
# @used-by :meth:`test_agent_tools.JournalTests.test_exact_bytes_and_no_keyword_authorization()`
# @used-by :meth:`test_agent_tools.JournalTests.test_existing_same_request_is_not_ownership()`
# @used-by :meth:`test_agent_tools.JournalTests.test_explicit_occupied_slot_and_overwrite_rejected()`
# @used-by :meth:`test_agent_tools.JournalTests.test_failed_second_write_recovers_with_token()`
# @used-by :meth:`test_agent_tools.JournalTests.test_o_journal_20_entry_bucketing_and_partial_range_normalization()`
# @used-by :meth:`test_agent_tools.JournalTests.test_process_crash_releases_lock_and_reservation_is_recoverable()`
# @used-by :meth:`test_agent_tools.JournalTests.test_recovery_does_not_overwrite_conflict()`
# @used-by :meth:`test_agent_tools.UpworkProjectTests.test_agent_data_dir_prefers_vai_directory()`
# @used-by :meth:`test_onboarding.IsolationTests.test_pending_journal_cannot_be_recovered_into_another()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_readable_links.ReadableReferenceTests.test_exact_quotes_code_and_source_copies_are_not_rewritten_or_rejected()`
# @used-by :meth:`test_resume_exports.ResumeExportTests.test_group_crash_reserves_all_numbers_and_preserves_previous_context()`
# @used-by :meth:`test_text_integration.TextBoundaryTests.test_matching_request_blocks_direct_write_but_unrelated_journal_is_allowed()`
def record_step(journal_dir: Path, req_content: str, res_content: str, target_step: int | None=None, allow_overwrite: bool=False) -> int:
	return dfh_record_step(journal_dir, req_content, res_content, target_step=target_step, allow_overwrite=allow_overwrite, create_bytes_fn=create_bytes, publish_fn=_publish)
# @used-by :meth:`test_agent_tools.JournalTests.test_failed_second_write_recovers_with_token()`
# @used-by :meth:`test_agent_tools.JournalTests.test_process_crash_releases_lock_and_reservation_is_recoverable()`
# @used-by :meth:`test_agent_tools.JournalTests.test_recovery_does_not_overwrite_conflict()`
# @used-by :meth:`test_onboarding.IsolationTests.test_pending_journal_cannot_be_recovered_into_another()`
def recover_step(directory: Path, step: int, token: str):
	dfh_recover_step(directory, step, token, publish_fn=_publish)
