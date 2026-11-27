# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from Df.Core.lib.state import df_is_windows
from Df.Harness.Config.AtomicWriter import AtomicWriter
import hashlib
import json
import time
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_locked()`
def _acquire_stream_lock(stream, path: Path, timeout: float) -> None:
	deadline = time.monotonic() + timeout
	while True:
		try:
			stream.seek(0)
			if df_is_windows():
				import msvcrt
				msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
			else:
				import fcntl
				fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
			break
		except OSError:
			if time.monotonic() >= deadline:
				raise TimeoutError(f'Lock busy: {path}')
			time.sleep(0.05)
# @used-by :func:`dfh_iter_embedded_json_objects()`
def _iter_str_json_objects(value: str, *, parse_root: bool, recursive: bool):
	parsed, loaded = (None, False)
	if parse_root:
		try:
			parsed, loaded = (json.loads(value), True)
		except ValueError:
			loaded = False
	if loaded:
		if not isinstance(parsed, str):
			yield from dfh_iter_embedded_json_objects(parsed, parse_root=parse_root, recursive=recursive)
	else:
		decoder, start = (json.JSONDecoder(), 0)
		while 0 <= (start := value.find('{', start)):
			try:
				item, size = decoder.raw_decode(value[start:])
			except ValueError:
				start += 1
			else:
				yield from dfh_iter_embedded_json_objects(item, parse_root=parse_root, recursive=recursive)
				start += size
# @used-by :func:`dfh_locked()`
def _release_stream_lock(stream) -> None:
	stream.seek(0)
	if df_is_windows():
		import msvcrt
		msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
	else:
		import fcntl
		fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
# @used-by :func:`Df.Harness.lib.admission_ops.dfh_capture_admission()`
# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_create_unique_log_file()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_restore_antigravity()`
# @used-by :func:`Df.Harness.lib.config_blocks.dfh_store_content_backup()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_publish_step()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_record_step()`
# @used-by :func:`agent_tools.storage.create_bytes()`
# @used-by :func:`dfh_write_immutable_bytes()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__handle_failure()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__create_new_group()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__write_pending_step()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__upsert_project_file()`
def dfh_create_bytes(path: Path, data: bytes) -> None:
	AtomicWriter(path, data, mode='create').run()
# @used-by :func:`Df.Harness.lib.admission_ops.dfh_capture_admission()`
# @used-by :func:`Df.Harness.lib.admission_ops.dfh_resolve_admission_proof_file()`
# @used-by :func:`Df.Harness.lib.cli_input._check_parallel_answer_md_guard()`
# @used-by :func:`Df.Harness.lib.cli_input.dfh_verify_scratch_input_path()`
# @used-by :func:`Df.Harness.lib.config_blocks.dfh_load_project_receipt()`
# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_upgrade_journal()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_build_shared_native()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_install_native_profiles()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_retire_owned_project_projections()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._collect_role_backup_originals()`
# @used-by :func:`Df.Harness.lib.native_links.dfh_backup()`
# @used-by :func:`Df.Harness.lib.native_links.dfh_state_path()`
# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_runtime_store_dir()`
# @used-by :func:`agent_tools.storage.data_dir_for()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__handle_failure()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__write_backups_and_planned()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.run()`
# @used-by :meth:`Df.Harness.Runtime.LauncherRenderer.LauncherRenderer.__resolve_store()`
def dfh_data_dir_for(path: Path, *, exact_root: bool=False) -> Path:
	from Df.Harness.lib.path_resolve import dfh_project_paths
	return dfh_project_paths(Path(path), exact_root=exact_root).data_dir
# @used-by :func:`Df.Harness.lib.codex_metadata._collect_output_receipts()`
# @used-by :func:`_iter_str_json_objects()`
# @used-by :func:`agent_tools.platforms.codex._json_objects()`
# @used-by :func:`agent_tools.storage.iter_embedded_json_objects()`
def dfh_iter_embedded_json_objects(value: Any, *, parse_root: bool=True, recursive: bool=True):
	if isinstance(value, dict):
		yield value
		if recursive:
			for child in value.values():
				yield from dfh_iter_embedded_json_objects(child, parse_root=parse_root, recursive=recursive)
	elif isinstance(value, list):
		for child in value:
			yield from dfh_iter_embedded_json_objects(child, parse_root=parse_root, recursive=recursive)
	elif isinstance(value, str):
		yield from _iter_str_json_objects(value, parse_root=parse_root, recursive=recursive)
# @used-by :func:`Df.Harness.lib.journal_core.dfh_raw_state_dir()`
# @used-by :func:`agent_tools.storage.journal_data_dir_for()`
def dfh_journal_data_dir_for(eff: Path) -> Path:
	from Df.Harness.lib.path_resolve import dfh_resolve_journal_data_dir
	return dfh_resolve_journal_data_dir(Path(eff))
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_remove_antigravity()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_restore_antigravity()`
# @used-by :func:`Df.Harness.lib.completion_commands._begin_live()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_prepare_once()`
# @used-by :func:`Df.Harness.lib.completion_recovery._execute_checkpoint_recovery()`
# @used-by :func:`Df.Harness.lib.completion_recovery._persist_similar_exemption()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_handoff_launcher_turn()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_ratchet_ok()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_persist_turn_recovery()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_record_step()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_recover_step()`
# @used-by :func:`Df.Harness.lib.journal_reservations.dfh_release_turn_steps()`
# @used-by :func:`Df.Harness.lib.journal_reservations.dfh_reserve_turn_steps()`
# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_upgrade_journal()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_build_shared_native()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_install_native_profiles()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_retire_owned_project_projections()`
# @used-by :func:`agent_tools.storage.locked()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.__finalize_removal()`
# @used-by :meth:`Df.Harness.Cleanup.Scanner.Scanner.run()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.run()`
# @used-by :meth:`Df.Harness.Completion.NarrowReconciler.NarrowReconciler.__trim_narrowed_reservation()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.run()`
# @used-by :meth:`Df.Harness.Hook.EmergencyCapturer.EmergencyCapturer.run()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__register_single()`
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.run()`
@contextmanager
def dfh_locked(path: Path, timeout: float=15, *, create: bool=True):
	if create:
		path.parent.mkdir(parents=True, exist_ok=True)
	with path.open('a+b' if create else 'r+b') as stream:
		_acquire_stream_lock(stream, path, timeout)
		try:
			yield
		finally:
			_release_stream_lock(stream)
# @used-by :func:`agent_tools.storage.read_addressed_json()`
def dfh_read_addressed_json(path: Path, *, suffix: str='', stem_match: bool=False, error_msg: str='Invalid immutable artifact') -> tuple[bytes, dict]:
	target = Path(path)
	raw = target.read_bytes()
	value = json.loads(raw.decode('utf-8-sig'))
	sha = hashlib.sha256(raw).hexdigest()
	expected = sha if stem_match else sha + suffix
	actual = target.stem if stem_match else target.name
	if not isinstance(value, dict) or actual != expected:
		raise ValueError(error_msg)
	return (raw, value)
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_finish_pending()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_remove_antigravity()`
# @used-by :func:`Df.Harness.lib.cleanup_mutation_ops.dfh_restore_antigravity()`
# @used-by :func:`Df.Harness.lib.completion_compaction.dfh_write_compaction_index_file()`
# @used-by :func:`Df.Harness.lib.completion_recovery._execute_checkpoint_recovery()`
# @used-by :func:`Df.Harness.lib.completion_recovery._persist_similar_exemption()`
# @used-by :func:`Df.Harness.lib.completion_recovery._write_recovery_records()`
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_ratchet_ok()`
# @used-by :func:`Df.Harness.lib.completion_state.dfh_persist_turn_recovery()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops.dfh_save_guard()`
# @used-by :func:`Df.Harness.lib.hook_trace_cache._save_disk_index()`
# @used-by :func:`Df.Harness.lib.journal_reservations.dfh_write_turn_reservations()`
# @used-by :func:`Df.Harness.lib.journal_sync_ops.dfh_persist_turn_state()`
# @used-by :func:`Df.Harness.lib.journal_sync_ops.dfh_write_index_doc()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._rewrite_journal_readme()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._sync_overlay_journal_slot()`
# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_deploy_git_hooks()`
# @used-by :func:`Df.Harness.lib.shadow_command.dfh_persist_shadow_replay_receipt()`
# @used-by :func:`agent_tools.storage.replace_bytes()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__apply_files()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__commit_receipt()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__rollback_files()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__commit()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__write_backups_and_planned()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__load_existing_group()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.run()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__upsert_project_file()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.ProjectRegistrar.ProjectRegistrar.__write_folders()`
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__activate_release()`
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__promote_locked()`
def dfh_replace_bytes(path: Path, data: bytes) -> None:
	AtomicWriter(path, data, mode='replace').run()
# @used-by :func:`Df.Harness.lib.completion_state.dfh_conflict()`
# @used-by :func:`Df.Harness.lib.trace_review.dfh_persist_review_proof()`
# @used-by :func:`agent_tools.storage.write_immutable_bytes()`
def dfh_write_immutable_bytes(path: Path, payload: bytes, *, diff_error: str='Immutable artifact differs') -> Path:
	target = Path(path)
	target.parent.mkdir(parents=True, exist_ok=True)
	if target.exists():
		if target.read_bytes() != payload:
			raise ValueError(diff_error)
	else:
		try:
			dfh_create_bytes(target, payload)
		except FileExistsError:
			if target.read_bytes() != payload:
				raise ValueError(diff_error)
	return target
