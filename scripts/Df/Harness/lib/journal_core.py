# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.path_resolve import dfh_load_registry, dfh_project_paths
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
from Df.Harness.lib.shadow_hooks import SHADOW_JOURNAL_IDENTITY_HOOK
from Df.Harness.lib.storage import dfh_journal_data_dir_for
import hashlib
import re
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
JOURNAL_BUCKET_SIZE = 20
JOURNAL_RANGE_SEP = '\u2013'
TURN_RESERVATIONS_FILE = 'turn-reservations.json'
V1_PAIR = ('req', 'res')
V2_PAIR = ('\u227b', '\u227a')
_BUCKET_DIR_RE = re.compile('^(\\d+)[-\\u2013](\\d+)$')
_LEGACY_ANALYSIS_NAMES = ('1 - Analysis', '1 - \u0410\u043d\u0430\u043b\u0438\u0437')
# @used-by :func:`dfh_canonicalize_journal_dir_identity()`
def _candidate_project_root(p: Path) -> Path | None:
	if '\ua66e' == p.parent.name and p.name in _LEGACY_ANALYSIS_NAMES:
		r: Path | None = p.parent.parent
	elif '_' == p.parent.name and '\ua66e' == p.name:
		r = p.parent.parent
	elif '\ua66e' == p.name:
		r = p.parent
	else:
		r = None
	return r
# @used-by :func:`dfh_iter_side_step_files()`
def _collect_bucket_steps(child: Path, side_p: Path, found: dict[int, Path]) -> None:
	for sub_f in sorted(child.iterdir(), key=lambda p: p.name):
		if dfh_is_step_md(sub_f):
			st = int(sub_f.stem)
			if st in found and found[st].read_bytes() != sub_f.read_bytes():
				raise ValueError(f'Conflicting duplicate journal step {st} in {side_p}: {found[st]} vs {sub_f}')
			if st not in found or child.name == dfh_journal_bucket_name(st):
				found[st] = sub_f
# @used-by :func:`dfh_detect_journal_version()`
def _side_needs_bucketing(side_p: Path) -> bool:
	r = False
	if side_p.is_dir():
		for child in side_p.iterdir():
			if dfh_is_step_md(child):
				r = True
				break
			if child.is_dir() and dfh_is_bucket_dir_name(child.name):
				b_steps = [int(bf.stem) for bf in child.iterdir() if dfh_is_step_md(bf)]
				if not b_steps or any((child.name != dfh_journal_bucket_name(st) for st in b_steps)):
					r = True
					break
	return r
# @used-by :func:`dfh_journal_pair_names()`
# @used-by :meth:`test_df_harness_s11_wave2d_journal_path_cov.DfHarnessS11Wave2dJournalPathCovTests.test_journal_integrity_and_records()`
def _resolve_dual_pair_names(directory: Path) -> tuple[str, str]:
	v2_files = any((bool(dfh_iter_side_step_files(directory / sub)) for sub in V2_PAIR if (directory / sub).is_dir()))
	v1_files = any((bool(dfh_iter_side_step_files(directory / sub)) for sub in V1_PAIR if (directory / sub).is_dir()))
	if v2_files and v1_files:
		raise ValueError(f'Conflicting V1 (req/res) and V2 (\u227b/\u227a) journal entries in {directory}')
	return V2_PAIR if v2_files or (not v1_files) else V1_PAIR
# @used-by :func:`dfh_resolve_journal_dir()`
# @used-by :func:`dfh_resolve_migrated_step_file()`
# @used-by :func:`dfh_same_journal_identity()`
# @used-by :func:`dfh_state_dir()`
# @used-by :meth:`Df.Harness.Meta.Builders.Builders.__apply_issue_state_details()`
# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__resolve_journal_dir()`
def dfh_canonicalize_journal_dir_identity(journal_path: str | Path) -> Path:
	p = Path(journal_path).resolve()
	r = p
	if not p.is_dir():
		if '\ua66e' == p.parent.name and p.name in _LEGACY_ANALYSIS_NAMES and ((p.parent / V2_PAIR[0]).is_dir() or (p.parent / V2_PAIR[1]).is_dir()):
			r = p.parent.resolve()
		else:
			cand_root = _candidate_project_root(p)
			if None is not cand_root:
				try:
					canon_root = dfh_canonicalize_root_dir(cand_root, dfh_load_registry())
					if canon_root.is_dir():
						pp = dfh_project_paths(canon_root, exact_root=True)
						if (canon_root != cand_root.resolve() or 2 <= pp.fs_version) and pp.journal_dir.is_dir():
							r = pp.journal_dir.resolve()
				except (OSError, ValueError):
					r = p
	return r
# @used-by :func:`Df.Harness.lib.journal_upgrade._execute_upgrade()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._unit_needs_upgrade()`
# @used-by :func:`Df.Harness.lib.journal_upgrade.dfh_ensure_project_journal_upgraded()`
# @used-by :func:`dfh_step_file()`
# @used-by :meth:`test_agent_tools.JournalTests.test_o_journal_20_entry_bucketing_and_partial_range_normalization()`
def dfh_detect_journal_version(directory: Path) -> int:
	d = Path(directory)
	if V1_PAIR == dfh_journal_pair_names(d):
		r = 1
	elif any((_side_needs_bucketing(d / side_name) for side_name in V2_PAIR)):
		r = 2
	else:
		r = 3
	return r
# @used-by :func:`Df.Harness.lib.journal_records._check_group_files()`
# @used-by :func:`Df.Harness.lib.journal_records._check_overwritten_conflict()`
# @used-by :func:`Df.Harness.lib.journal_records._reserve_and_publish_step()`
# @used-by :func:`Df.Harness.lib.journal_records._validate_answer_group_meta()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_recover_step()`
# @used-by :func:`dfh_raw_state_dir()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__create_new_group()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__load_existing_group()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__write_pending_step()`
def dfh_digest(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()
# @used-by :func:`dfh_resolve_migrated_step_file()`
# @used-by :func:`dfh_step_file()`
# @used-by :meth:`test_agent_tools.JournalTests.test_o_journal_20_entry_bucketing_and_partial_range_normalization()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_orphan_pair_adopted_without_duplicate_and_overwritten_claimed_pair_flags_conflict()`
def dfh_find_step_file(side_dir: Path, step: int) -> Path | None:
	r: Path | None = None
	side_p = Path(side_dir)
	if int is type(step) and 1 <= step and side_p.is_dir():
		canon = side_p / dfh_journal_bucket_name(step) / f'{step}.md'
		flat = side_p / f'{step}.md'
		if canon.is_file():
			r = canon
		elif flat.is_file():
			r = flat
		else:
			target_name = f'{step}.md'
			for child in sorted(side_p.iterdir(), key=lambda p: p.name):
				if child.is_dir() and dfh_is_bucket_dir_name(child.name) and (child / target_name).is_file():
					r = child / target_name
					break
	return r
# @used-by :func:`Df.Harness.lib.journal_upgrade._collect_one_side_dir()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._discover_upgrade_units()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._prune_legacy_side_dirs()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._summarize_v2_buckets()`
# @used-by :func:`_side_needs_bucketing()`
# @used-by :func:`agent_tools.article.detect_kind()`
# @used-by :func:`agent_tools.text_core.check_response()`
# @used-by :func:`dfh_find_step_file()`
# @used-by :func:`dfh_iter_side_step_files()`
# @used-by :func:`dfh_parse_step_file_path()`
def dfh_is_bucket_dir_name(name: str) -> bool:
	return bool(_BUCKET_DIR_RE.fullmatch(str(name or '')))
# @used-by :func:`Df.Harness.lib.journal_upgrade._collect_one_side_dir()`
# @used-by :func:`_collect_bucket_steps()`
# @used-by :func:`_side_needs_bucketing()`
# @used-by :func:`dfh_iter_side_step_files()`
def dfh_is_step_md(path: Path) -> bool:
	return path.is_file() and '.md' == path.suffix.lower() and path.stem.isascii() and path.stem.isdigit() and 1 <= int(path.stem)
# @used-by :func:`Df.Harness.lib.cleanup_lifecycle_ops.dfh_journal_pair_activity()`
# @used-by :func:`Df.Harness.lib.journal_records._scan_orphan_candidates()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_get_existing_step_ids()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._summarize_v2_buckets()`
# @used-by :func:`_resolve_dual_pair_names()`
# @used-by :func:`agent_tools.text_core.check_response()`
# @used-by :meth:`test_readable_links.ReadableProjectTests.test_record_answer_blocks_encoded_authored_links_before_any_journal_mutation()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_concurrent_native_reconciliation_creates_one_pair()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_foreground_integrity_check_preserves_a_deleted_completed_journal_file()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_matching_native_request_ids_reuse_an_existing_record_answer_group()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_missing_completed_group_receipt_cannot_create_a_duplicate_exchange()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_native_sync_recovers_a_completely_skipped_prepare_once()`
def dfh_iter_side_step_files(side_dir: Path) -> list[tuple[int, Path]]:
	side_p = Path(side_dir)
	found: dict[int, Path] = {}
	if side_p.is_dir():
		for child in sorted(side_p.iterdir(), key=lambda p: p.name):
			if dfh_is_step_md(child):
				found[int(child.stem)] = child
			elif child.is_dir() and dfh_is_bucket_dir_name(child.name):
				_collect_bucket_steps(child, side_p, found)
	return sorted(found.items(), key=lambda item: item[0])
# @used-by :func:`dfh_journal_bucket_name()`
def dfh_journal_bucket_bounds(step: int, bucket_size: int=JOURNAL_BUCKET_SIZE) -> tuple[int, int]:
	if int is not type(step) or 1 > step:
		raise ValueError('Step must be a positive integer')
	start = ((step - 1) // bucket_size) * bucket_size + 1
	return (start, start + bucket_size - 1)
# @used-by :func:`Df.Harness.lib.journal_upgrade._build_upgrade_plans()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._execute_upgrade()`
# @used-by :func:`Df.Harness.lib.journal_upgrade._rewrite_journal_readme()`
# @used-by :func:`_collect_bucket_steps()`
# @used-by :func:`_side_needs_bucketing()`
# @used-by :func:`dfh_find_step_file()`
# @used-by :func:`dfh_step_file()`
# @used-by :func:`test_journal_integrity._write_step_pair()`
# @used-by :meth:`test_agent_tools.JournalTests.test_o_journal_20_entry_bucketing_and_partial_range_normalization()`
def dfh_journal_bucket_name(step: int, bucket_size: int=JOURNAL_BUCKET_SIZE) -> str:
	start, end = dfh_journal_bucket_bounds(step, bucket_size)
	return f'{start}{JOURNAL_RANGE_SEP}{end}'
# @used-by :func:`Df.Harness.lib.cleanup_lifecycle_ops.dfh_journal_pair_activity()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_group()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_record()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :func:`Df.Harness.lib.journal_records._validate_answer_group_files()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_answer_groups()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_find_orphan_or_overwritten_steps()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_get_existing_step_ids()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_matching_group_response()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_publish_step()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_record_step()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_step_errors()`
# @used-by :func:`agent_tools.text_core.check_response()`
# @used-by :func:`dfh_resolve_migrated_step_file()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__prepare_context()`
# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.step_paths()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__resolve_segment_completion()`
# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_journal_steps()`
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__find_reply_path()`
# @used-by :meth:`Df.Harness.Upwork.ProjectInitializer.ProjectInitializer.__init_locked_state()`
# @used-by :meth:`Df.Harness.Workflow.FinalizeStageRunner.FinalizeStageRunner.__load_latest_reply()`
# @used-by :meth:`Df.Harness.Workflow.RequestAdopter.RequestAdopter.__saved_answers()`
# @used-by :meth:`test_df_harness_s11_wave2d_tail_cov.DfHarnessS11Wave2dTailCovTests.test_journal_tail()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
def dfh_journal_pair_dirs(directory: Path) -> tuple[Path, Path]:
	d = Path(directory)
	req_name, res_name = dfh_journal_pair_names(d)
	return (d / req_name, d / res_name)
# @used-by :func:`dfh_detect_journal_version()`
# @used-by :func:`dfh_journal_pair_dirs()`
def dfh_journal_pair_names(directory: Path) -> tuple[str, str]:
	d = Path(directory)
	has_v2 = (d / V2_PAIR[0]).is_dir() or (d / V2_PAIR[1]).is_dir()
	has_v1 = (d / V1_PAIR[0]).is_dir() or (d / V1_PAIR[1]).is_dir()
	if has_v2 and has_v1:
		r = _resolve_dual_pair_names(d)
	elif has_v2 or '\ua66e' == d.name:
		r = V2_PAIR
	elif has_v1 or d.name in _LEGACY_ANALYSIS_NAMES:
		r = V1_PAIR
	else:
		r = V1_PAIR
		try:
			pp = dfh_project_paths(d)
			if 2 <= pp.fs_version or (d.resolve() == pp.journal_dir.resolve() and 2 <= pp.journal_version):
				r = V2_PAIR
		except (OSError, ValueError):
			r = V1_PAIR
	return r
# @used-by :func:`Df.Harness.lib.completion_record._group_payload_matches()`
# @used-by :func:`Df.Harness.lib.completion_record._resolve_existing_group_payload()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_group()`
# @used-by :func:`Df.Harness.lib.journal_records._match_orphan_window()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_find_orphan_or_overwritten_steps()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_matching_group_response()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__resolve_effective_response()`
# @used-by :mod:`agent_tools.completion`
def dfh_norm_journal_response_text(text: str) -> str:
	from agent_tools.metadata import strip_leading_metadata_header
	return dfh_norm_journal_text(strip_leading_metadata_header(text or ''))
# @used-by :func:`Df.Harness.lib.completion_record._group_payload_matches()`
# @used-by :func:`Df.Harness.lib.completion_record._resolve_existing_group_payload()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_group()`
# @used-by :func:`Df.Harness.lib.journal_records._match_orphan_window()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_find_orphan_or_overwritten_steps()`
# @used-by :func:`dfh_norm_journal_response_text()`
# @used-by :mod:`agent_tools.completion`
def dfh_norm_journal_text(text: str) -> str:
	return dfh_strip_local_file_scheme((text or '').replace('\r\n', '\n'))
# @used-by :func:`Df.Harness.lib.completion_record.dfh_same_turn_artifact_path()`
# @used-by :func:`dfh_resolve_migrated_step_file()`
def dfh_parse_step_file_path(path: str | Path) -> tuple[Path, str, int] | None:
	p = Path(path)
	r: tuple[Path, str, int] | None = None
	if '.md' == p.suffix.lower() and p.stem.isascii() and p.stem.isdigit() and 1 <= int(p.stem):
		step = int(p.stem)
		parent = p.parent
		if parent.name in (*V1_PAIR, *V2_PAIR):
			r = (parent.parent, parent.name, step)
		elif dfh_is_bucket_dir_name(parent.name) and parent.parent.name in (*V1_PAIR, *V2_PAIR):
			r = (parent.parent.parent, parent.parent.name, step)
	return r
# @used-by :func:`Df.Harness.lib.journal_upgrade._migrate_journal_state_dir()`
# @used-by :func:`dfh_state_dir()`
# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.migrate_journal_state()`
def dfh_raw_state_dir(eff: Path, *, data_root: Path | None=None) -> Path:
	identity = str(eff.resolve()).casefold()
	base = Path(data_root) if None is not data_root else dfh_journal_data_dir_for(eff)
	return base / '.journal' / dfh_digest(identity.encode('utf-8'))[:24]
# @used-by :func:`Df.Harness.lib.completion_core.dfh_journal_dir()`
# @used-by :func:`Df.Harness.lib.shadow_clone.dfh_remap_shadow_state()`
# @used-by :func:`Df.Harness.lib.shadow_command.dfh_stage_command_shadow_copies()`
# @used-by :func:`agent_tools.completion._directory()`
# @used-by :meth:`Df.Harness.Meta.Builders.Builders.__apply_issue_state_details()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__load_statuses_and_journal()`
# @used-by :meth:`Df.Harness.Project.Rename.PostRenameVerifier.PostRenameVerifier.__collect_journal_errors()`
# @used-by :meth:`Df.Harness.Project.Rename.StateRewriter.StateRewriter.migrate_journal_state()`
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__find_reply_path()`
# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.__prepare_stage()`
# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.record()`
# @used-by :meth:`Df.Harness.Workflow.FinalizeStageRunner.FinalizeStageRunner.__load_latest_reply()`
# @used-by :meth:`Df.Harness.Workflow.RequestAdopter.RequestAdopter.__saved_answers()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
# @used-by :meth:`test_turn_completion.AnswerPreparationRunnerTests.test_gate_id_auto_clearing_and_resolve_journal_dir()`
# @used-by :meth:`test_turn_completion.TurnJournalReconcilerTests.test_compacted_status5_steps_single_pass_authorize_and_group_helpers()`
def dfh_resolve_journal_dir(root: Path, selected=None) -> Path:
	pp = dfh_project_paths(Path(root).resolve(), exact_root=True)
	if selected:
		sel_str = pp.expand(str(selected)) if '${' in str(selected) else str(selected)
		r = dfh_canonicalize_journal_dir_identity((pp.root / sel_str).resolve())
	else:
		r = pp.journal_dir.resolve()
	return r
# @used-by :func:`Df.Harness.lib.completion_links._resolve_local_target()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_matches_recorded_response()`
# @used-by :func:`agent_tools.links.validate_file()`
# @used-by :func:`agent_tools.source_grounding.resolve_local_href()`
# @used-by :meth:`Df.Harness.Completion.JournalReconciler.JournalReconciler.__resolve_effective_response()`
# @used-by :meth:`Df.Harness.Workflow.ReceiptVerifier.ReceiptVerifier.__resolve_artifact()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v1_journal_only_upgrade_preserves_v1_project_layout_and_historical_receipts()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
def dfh_resolve_migrated_step_file(path: str | Path) -> Path:
	p = Path(path)
	r = p.resolve() if p.is_file() else p
	if not p.is_file():
		parsed = dfh_parse_step_file_path(p)
		if None is not parsed:
			old_jdir, old_side, step = parsed
			eff_jdir = dfh_canonicalize_journal_dir_identity(old_jdir)
			if eff_jdir.is_dir():
				try:
					req_dir, res_dir = dfh_journal_pair_dirs(eff_jdir)
					found = dfh_find_step_file(req_dir if old_side in ('req', '\u227b') else res_dir, step)
					if None is not found:
						r = found.resolve()
				except ValueError:
					r = p
	return r
# @used-by :func:`Df.Harness.lib.admission_ops.dfh_admission_same_binding()`
# @used-by :func:`Df.Harness.lib.completion_core.dfh_conversation_journal_steps()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_same_turn_artifact_path()`
# @used-by :func:`Df.Harness.lib.completion_state._verify_turn_owner_and_journal()`
# @used-by :func:`Df.Harness.lib.journal_records._validate_answer_group_meta()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_answer_groups()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_get_existing_step_ids()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_recover_step()`
# @used-by :func:`agent_tools.shadow_replay_clone._legacy_shadow_patch_ctx()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__load_existing_group()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
def dfh_same_journal_identity(first: str | Path | None, second: str | Path | None) -> bool:
	from agent_tools.project_rename_state import same_journal_identity_with_rename
	base_fn = lambda a, b: same_journal_identity_with_rename(a, b, dfh_canonicalize_journal_dir_identity)
	hook = SHADOW_JOURNAL_IDENTITY_HOOK[0]
	return hook(base_fn, first, second) if None is not hook else base_fn(first, second)
# @used-by :func:`Df.Harness.lib.completion_record.dfh_group()`
# @used-by :func:`Df.Harness.lib.completion_record.dfh_record()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_acknowledged_sequence_gaps()`
# @used-by :func:`Df.Harness.lib.journal_integrity_ops.dfh_check_project_journal_problems()`
# @used-by :func:`Df.Harness.lib.journal_records._scan_orphan_candidates()`
# @used-by :func:`Df.Harness.lib.journal_records._validate_answer_group_files()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_get_existing_step_ids()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_iter_answer_group_records()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_publish_step()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_record_step()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_recover_step()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_step_errors()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_verify_answer()`
# @used-by :func:`Df.Harness.lib.journal_reservations.dfh_read_turn_reservations()`
# @used-by :func:`Df.Harness.lib.journal_reservations.dfh_release_turn_steps()`
# @used-by :func:`Df.Harness.lib.journal_reservations.dfh_reserve_turn_steps()`
# @used-by :func:`Df.Harness.lib.journal_reservations.dfh_write_turn_reservations()`
# @used-by :func:`Df.Harness.lib.shadow_clone.dfh_remap_shadow_state()`
# @used-by :func:`Df.Harness.lib.shadow_command.dfh_stage_command_shadow_copies()`
# @used-by :func:`test_project_rename._assert_renamed_journal_and_state()`
# @used-by :func:`test_project_rename._seed_project_artifacts()`
# @used-by :meth:`Df.Harness.Completion.NarrowReconciler.NarrowReconciler.__trim_narrowed_reservation()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__prepare_context()`
# @used-by :meth:`Df.Harness.Meta.Builders.Builders.__resolve_issue_group_file()`
# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.__prepare_stage()`
# @used-by :meth:`test_agent_tools.JournalTests.test_concurrent_real_processes_same_request_get_distinct_pairs()`
# @used-by :meth:`test_agent_tools.JournalTests.test_exact_bytes_and_no_keyword_authorization()`
# @used-by :meth:`test_agent_tools.JournalTests.test_failed_second_write_recovers_with_token()`
# @used-by :meth:`test_agent_tools.JournalTests.test_process_crash_releases_lock_and_reservation_is_recoverable()`
# @used-by :meth:`test_agent_tools.JournalTests.test_recovery_does_not_overwrite_conflict()`
# @used-by :meth:`test_agent_tools.UpworkProjectTests.test_agent_data_dir_prefers_vai_directory()`
# @used-by :meth:`test_journal_idle_sync_and_liveness.JournalIdleSyncAndLivenessTests.test_live_running_parallel_reservation_not_orphaned_while_idle_stuck_is_orphaned()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_finalize_stage_blocks_step_gap_dangling_reservation_and_reconciliation_error()`
# @used-by :meth:`test_journal_integrity.JournalIntegrityM4Tests.test_validate_step_strict_sequence_and_check_project_detect_gaps_and_orphans()`
# @used-by :meth:`test_onboarding.IsolationTests.test_pending_journal_cannot_be_recovered_into_another()`
# @used-by :meth:`test_path_registry.PathRegistryTests.test_cross_root_relocation_workflow_completion_review_and_antigravity_registration()`
# @used-by :meth:`test_path_registry_perf.PathRegistryPerformanceTests.test_data_dir_for_supports_exact_root_and_state_dir_skips_host_scan()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_antigravity_journal_conversation_auto_titling_and_comma_append()`
# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_registered_empty_launcher_project_tracks_pre_init_failures_and_hands_off_to_daily_project()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_adopt_requests_isolates_foreign_answer_group_mismatch()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_orphan_pair_adopted_without_duplicate_and_overwritten_claimed_pair_flags_conflict()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_complete_group_metadata_tamper_does_not_pass_historical_identity()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_legacy_complete_group_without_turn_state_exposes_proof_gap_without_readmission()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_missing_completed_group_receipt_cannot_create_a_duplicate_exchange()`
def dfh_state_dir(directory: Path) -> Path:
	return dfh_raw_state_dir(dfh_canonicalize_journal_dir_identity(directory))
# @used-by :func:`Df.Harness.lib.completion_record._build_record_receipt()`
# @used-by :func:`Df.Harness.lib.completion_record._group_payload_matches()`
# @used-by :func:`Df.Harness.lib.completion_record._resolve_existing_group_payload()`
# @used-by :func:`Df.Harness.lib.completion_record._verify_recorded_readback()`
# @used-by :func:`Df.Harness.lib.hook_stop_ops._record_emergency_files()`
# @used-by :func:`Df.Harness.lib.journal_records._check_group_files()`
# @used-by :func:`Df.Harness.lib.journal_records._validate_answer_group_files()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_matching_group_response()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_publish_step()`
# @used-by :func:`Df.Harness.lib.journal_records.dfh_step_errors()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__load_existing_group()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__sync_step()`
# @used-by :meth:`Df.Harness.Journal.Publisher.Publisher.__write_pending_step()`
# @used-by :meth:`Df.Harness.Meta.Blocks.Blocks.step_paths()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__resolve_segment_completion()`
# @used-by :meth:`Df.Harness.Project.Context.ContextAssembler.ContextAssembler.__collect_journal_steps()`
# @used-by :meth:`Df.Harness.Shadow.ReplayPipeline.ReplayPipeline.__find_reply_path()`
# @used-by :meth:`Df.Harness.Workflow.FinalizeStageRunner.FinalizeStageRunner.__load_latest_reply()`
# @used-by :meth:`Df.Harness.Workflow.RequestAdopter.RequestAdopter.__saved_answers()`
# @used-by :meth:`test_journal_metadata.JournalMetadataIntegrationTests.test_codex_prepare_reprepare_and_unprepared_recovery_prepend_metadata()`
# @used-by :meth:`test_turn_completion.CompletionCase.saved()`
def dfh_step_file(side_dir: Path, step: int, *, directory: Path | None=None) -> Path:
	side_p = Path(side_dir)
	found = dfh_find_step_file(side_p, step)
	if None is not found:
		r = found
	else:
		eff_dir = Path(directory) if None is not directory else side_p.parent
		r = side_p / dfh_journal_bucket_name(step) / f'{step}.md' if 3 <= dfh_detect_journal_version(eff_dir) else side_p / f'{step}.md'
	return r
# @used-by :func:`dfh_norm_journal_text()`
# @used-by :mod:`agent_tools.completion`
def dfh_strip_local_file_scheme(text: str) -> str:
	return re.sub('file:///+(?=[A-Za-z]:/)', '', text or '', flags=re.IGNORECASE).rstrip('\r\n ')
