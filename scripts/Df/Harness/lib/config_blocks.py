# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.storage import dfh_create_bytes, dfh_data_dir_for
import hashlib
import json
import os
import re
import tomllib
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
DISCOVERY_KINDS = ('rules', 'skills', 'agents')
END = '<!-- upwork-init:instructions:end -->'
START = '<!-- upwork-init:instructions:start -->'
# @used-by :func:`_step_toml_char()`
def _advance_quoted(text: str, index: int, quote: str) -> tuple[int, str | None]:
	if quote.startswith('"') and '\\' == text[index]:
		r: tuple[int, str | None] = (index + 2, quote)
	elif text.startswith(quote, index):
		nxt = index + len(quote)
		if 3 == len(quote):
			while nxt < len(text) and text[nxt] == quote[0]:
				nxt += 1
		r = (nxt, None)
	else:
		r = (index + 1, quote)
	return r
# @used-by :func:`dfh_root_options()`
def _collect_root_edits(text: str, values: dict[str, str | None]) -> tuple[list[tuple[int, int, str]], set[str]]:
	edits: list[tuple[int, int, str]] = []
	found: set[str] = set()
	for start, end in _toml_statements(text):
		statement = text[start:end].lstrip()
		if statement.startswith('['):
			break
		for key, val in values.items():
			if re.match('^(?:' + key + '|"' + key + '"|\'' + key + "')\\s*=", statement):
				nl = '\r\n' if text[start:end].endswith('\r\n') else '\n'
				edits.append((start, end, '' if None is val else key + ' = ' + val + nl))
				found.add(key)
	return (edits, found)
# @used-by :func:`dfh_root_options()`
def _legacy_doc_option_updates(data: dict, legacy_bytes: int | None) -> dict[str, str | None]:
	updates: dict[str, str | None] = {}
	if None is not legacy_bytes:
		names = data.get('project_doc_fallback_filenames', [])
		if 'CODEX.md' in names:
			remaining = [name for name in names if 'CODEX.md' != name]
			updates['project_doc_fallback_filenames'] = json.dumps(remaining) if remaining else None
		if data.get('project_doc_max_bytes') in (65536, 65536 + legacy_bytes):
			updates['project_doc_max_bytes'] = None
	return updates
# @used-by :func:`_toml_statements()`
def _step_toml_char(text: str, index: int, depth: int, quote: str | None, comment: bool) -> tuple[int, int, str | None, bool, bool]:
	ch = text[index]
	if comment:
		r = (index + 1, depth, quote, '\n' != ch, False)
	elif quote:
		nxt, nq = _advance_quoted(text, index, quote)
		r = (nxt, depth, nq, False, False)
	elif ch in '"\'':
		nq = ch * 3 if text.startswith(ch * 3, index) else ch
		r = (index + len(nq), depth, nq, False, False)
	else:
		nd = depth + (1 if ch in '[{' else (-1 if ch in ']}' else 0))
		r = (index + 1, nd, None, '#' == ch, '\n' == ch and 0 == nd)
	return r
# @used-by :func:`_collect_root_edits()`
def _toml_statements(text: str):
	start = index = depth = 0
	quote: str | None = None
	comment = False
	while index < len(text):
		index, depth, quote, comment, boundary = _step_toml_char(text, index, depth, quote, comment)
		if boundary:
			yield (start, index)
			start = index
	if start < len(text):
		yield (start, len(text))
# @used-by :func:`Df.Harness.lib.config_codex.dfh_native_config()`
# @used-by :func:`dfh_replace_managed_block()`
# @used-by :func:`dfh_store_content_backup()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.run()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__commit()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__finalize_codex_receipt()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__plan_outputs()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__plan_retirements()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__write_backups_and_planned()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_guidance_uses_current_canonical_loader_without_copying_rule_bodies()`
# @used-by :meth:`test_portability.ProjectionTests.test_shared_generation_uses_one_owner_across_projects_and_profile_install()`
# @used-by :meth:`test_portability.ProjectionTests.test_verified_legacy_migrates_but_manual_configuration_and_fallback_survive()`
def dfh_digest(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()
# @used-by :func:`Df.Harness.lib.config_codex._run_codex_project_publish()`
# @used-by :func:`agent_tools.configuration._managed_block()`
# @used-by :func:`dfh_replace_managed_block()`
# @used-by :meth:`Df.Harness.Config.NativeBuilder.NativeBuilder.__prepare_codex_outputs()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__finalize_codex_receipt()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def dfh_extract_managed_block(value: str, start_marker: str=START, end_marker: str=END, *, error_message: str='Malformed managed developer instructions; configuration preserved') -> str:
	if start_marker not in value and end_marker not in value:
		r = ''
	elif 1 != value.count(start_marker) or 1 != value.count(end_marker) or value.index(start_marker) > value.index(end_marker):
		raise ValueError(error_message)
	else:
		r = value[value.index(start_marker):value.index(end_marker) + len(end_marker)]
	return r
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_skills()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_legacy_skill()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._populate_source_metadata()`
def dfh_frontmatter(path: Path) -> dict[str, Any]:
	text = Path(path).read_text(encoding='utf-8-sig')
	match = re.match('^---\\r?\\n(.*?)\\r?\\n---\\r?\\n', text, re.S)
	values: dict[str, Any] = {}
	for line in match.group(1).splitlines() if match else []:
		key, sep, value = line.partition(':')
		if sep and key.strip() and (not key.startswith(' ')):
			val = value.strip()
			values[key.strip()] = json.loads(val) if val.startswith('"') else val
	return values
# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_runner()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_legacy_project_projection_paths()`
# @used-by :func:`Df.Harness.lib.native_ag_plan.dfh_shared_plan()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_obsolete_skill_entry()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_profile_role()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_one_shared_role()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_plan_codex_link()`
# @used-by :func:`Df.Harness.lib.native_links.dfh_prepare_link_parent()`
# @used-by :func:`Df.Harness.lib.native_links.dfh_remove_link()`
# @used-by :func:`Df.Harness.lib.native_links.dfh_verify_retired_directory_link()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__apply_files()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__rollback_files()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__verify()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.create()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.restore_retired()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.verify_before_create()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.verify_retired()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Plan.Plan.file()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__plan_outputs()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__plan_retirements()`
def dfh_has_linked_ancestor(path: str | Path, *, include_self: bool=True) -> Path | None:
	resolved = Path(os.path.abspath(path))
	candidates = (resolved, *resolved.parents) if include_self else resolved.parents
	return next((item for item in candidates if dfh_is_linked_path(item)), None)
# @used-by :func:`Df.Harness.lib.native_codex_plan._plan_codex_skills()`
# @used-by :func:`Df.Harness.lib.native_codex_roles._retire_obsolete_skill_entry()`
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_plan_codex_link()`
# @used-by :func:`Df.Harness.lib.native_links.dfh_direct_link_matches_target()`
# @used-by :func:`Df.Harness.lib.native_links.dfh_link_matches_target()`
# @used-by :func:`Df.Harness.lib.native_links.dfh_remove_link()`
# @used-by :func:`Df.Harness.lib.native_links.dfh_verify_retired_directory_link()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :func:`dfh_has_linked_ancestor()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.Applier.Applier.__prune_empty_parents()`
# @used-by :meth:`Df.Harness.Config.NativeProfile.ManagedLink.ManagedLink.restore_retired()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_changed_created_link_does_not_stop_other_guarded_rollback()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_concurrent_personal_edit_does_not_stop_other_guarded_rollback()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_concurrent_replacement_during_skill_rollback_is_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_custom_same_name_role_and_personal_loader_edit_are_preserved()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_edited_wrapper_is_not_retired_or_replaced()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_new_link_failure_rolls_back_existing_profile_files()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_pilot_changes_only_selected_profiles_and_links_original_content()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_project_retirement_skips_a_linked_source_directory()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_role_parent_link_injected_immediately_before_creation_cannot_escape()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_parent_link_injected_during_backup_is_preserved_without_escape()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_parent_link_injected_immediately_before_creation_cannot_escape()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_rename_does_not_touch_unselected_profile_or_forget_ownership()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_skill_rename_retires_owned_dangling_link_with_identity_backup()`
def dfh_is_linked_path(path: str | Path) -> bool:
	candidate = Path(path)
	return candidate.is_symlink() or bool(getattr(candidate, 'is_junction', lambda: False)())
# @used-by :func:`Df.Harness.lib.config_codex.dfh_project_rule_paths()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._plan_ag_manifests()`
# @used-by :func:`agent_tools.upwork_project.check_configuration()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_discovery_manifests()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def dfh_load_discovery_manifest(path: str | Path, *, missing_ok: bool=True, entries_error: str='Manifest needs an entries list', check_inherits: bool=False) -> dict:
	target = Path(path)
	data = json.loads(target.read_text(encoding='utf-8-sig')) if target.exists() or (not missing_ok) else {}
	if not isinstance(data, dict) or not isinstance(data.get('entries', []), list) or (check_inherits and (not isinstance(data.get('inherits', []), list))):
		raise ValueError(entries_error)
	return data
# @used-by :func:`Df.Harness.lib.config_codex.dfh_native_config()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_retire_owned_project_projections()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__publish_locked()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._verify_projection_receipt()`
def dfh_load_project_receipt(target: str | Path, *, by_path: bool=False, error_message: str='Project native ownership receipt must be an object; preserved') -> tuple[Path, bytes | None, dict]:
	path = Path(target) if by_path else dfh_data_dir_for(target) / 'native-config.json'
	raw = path.read_bytes() if path.exists() else None
	data = json.loads(raw.decode('utf-8-sig')) if None is not raw else {}
	if not isinstance(data, dict):
		raise ValueError(error_message)
	return (path, raw, data)
# @used-by :func:`agent_tools.upwork_project.check_configuration()`
# @used-by :func:`agent_tools.upwork_project.configure_project()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def dfh_project_discovery_entries(primary: str | Path, kind: str, *, require_dir: bool=False) -> list[dict[str, str]]:
	shared = Path(primary) / kind
	if require_dir and (not shared.is_dir()):
		raise FileNotFoundError(shared)
	return [{'path': shared.as_posix()}, *([{'path': 'rules'}] if 'rules' == kind else [])]
# @used-by :func:`Df.Harness.lib.config_codex.dfh_native_config()`
# @used-by :func:`Df.Harness.lib.native_codex_plan.dfh_retire_owned_project_projections()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__commit()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__plan_outputs()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__plan_retirements()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__write_backups_and_planned()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._verify_projection_receipt()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def dfh_receipt_sha256(entry: Any) -> str | None:
	return entry.get('sha256') if isinstance(entry, dict) else entry
# @used-by :func:`Df.Harness.lib.native_codex_roles.dfh_profile_agents()`
# @used-by :func:`dfh_root_options()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def dfh_replace_managed_block(value: str, block: str, *, start_marker: str=START, end_marker: str=END, expected_sha256: str | None=None, malformed_message: str='Malformed managed developer instructions; configuration preserved', edited_message: str='Managed developer instructions were manually edited; configuration preserved') -> str:
	old_block = dfh_extract_managed_block(value, start_marker, end_marker, error_message=malformed_message)
	if not old_block:
		r = value + ('\n\n' if value and block else '') + block
	else:
		if old_block != block and (dfh_digest(old_block.encode('utf-8')) != expected_sha256):
			raise ValueError(edited_message)
		index = value.index(start_marker)
		r = value[:index] + block + value[index + len(old_block):]
	return r
# @used-by :func:`Df.Harness.lib.config_codex._append_rule_source()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._manifest_build_inherits()`
# @used-by :func:`Df.Harness.lib.native_ag_plan._manifest_filter_entries()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._scan_manifest_entry()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def dfh_resolve_manifest_entry(agents_dir: str | Path, entry: Any) -> tuple[Path | None, bool]:
	if not isinstance(entry, dict) or not isinstance(entry.get('path'), str):
		r: tuple[Path | None, bool] = (None, False)
	else:
		r = ((Path(agents_dir) / Path(entry['path']).expanduser()).resolve(), bool(set(entry) - {'path'}))
	return r
# @used-by :func:`Df.Harness.lib.config_codex.dfh_native_config()`
# @used-by :meth:`test_portability.ProjectionTests.test_multiline_toml_values_do_not_damage_unrelated_settings()`
# @used-by :meth:`test_portability.ProjectionTests.test_native_toml_preserves_settings_and_resolves_models_from_one_config()`
def dfh_root_options(text: str, instructions: str | None=None, *, legacy_bytes: int | None=None, expected_block: str | None=None) -> str:
	data = tomllib.loads(text) if text.strip() else {}
	block = START + '\n' + instructions.strip() + '\n' + END if instructions else ''
	value = dfh_replace_managed_block(data.get('developer_instructions', ''), block, expected_sha256=expected_block)
	values: dict[str, str | None] = {'developer_instructions': json.dumps(value, ensure_ascii=False) if value.strip() else None} if 'developer_instructions' in data or block else {}
	values.update(_legacy_doc_option_updates(data, legacy_bytes))
	edits, found = _collect_root_edits(text, values)
	for start, end, replacement in reversed(edits):
		text = text[:start] + replacement + text[end:]
	text = ''.join((key + ' = ' + val + '\n' for key, val in values.items() if key not in found and None is not val)) + text
	tomllib.loads(text)
	return text
# @used-by :func:`Df.Harness.lib.native_links.dfh_backup()`
# @used-by :meth:`Df.Harness.Config.ProjectionPublisher.ProjectionPublisher.__write_backups_and_planned()`
# @used-by :meth:`test_native_profiles.NativeProfileTests.test_unified_managed_link_and_manifest_helpers()`
def dfh_store_content_backup(backup_root: str | Path, path: str | Path, payload: bytes, *, error_message: str | None=None) -> tuple[Path, str]:
	digest = dfh_digest(payload)
	backup = Path(backup_root) / dfh_digest(str(path).encode('utf-8')) / (digest + '.bin')
	backup.parent.mkdir(parents=True, exist_ok=True)
	if not backup.exists():
		dfh_create_bytes(backup, payload)
	if backup.read_bytes() != payload:
		raise ValueError(error_message or f'Backup hash collision or modification; preserved: {backup}')
	return (backup, digest)
