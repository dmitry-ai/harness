# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Project.Rename.ProjectRenamer import ProjectRenamer
from pathlib import Path
from .project_rename_verify import capture_pre_rename_snapshot, verify_post_rename
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
# @used-by :func:`agent_tools.shadow_replay_command.resolve_shadow_launcher()`
# @used-by :func:`agent_tools.shadow_replay_command.stage_command_shadow_copies()`
# @used-by :mod:`agent_tools.project_rename`
def _infer_daily_root(root: Path, daily_root: Path | None) -> Path | None:
	return ProjectRenamer.infer_daily_root(root, daily_root)
# @used-by :func:`rename_project()`
# @used-by :mod:`agent_tools.project_rename`
def _update_projects_index(old_root: Path, new_root: Path, job_id: str, daily_root: Path | None, backups: list[tuple[Path, bytes | None]]) -> str | None:
	return ProjectRenamer.update_projects_index(old_root, new_root, job_id, daily_root, backups)
# @used-by :func:`agent_tools.cli_domains._op_render_analysis()`
# @used-by :func:`agent_tools.cli_domains._op_save_analysis()`
# @used-by :mod:`agent_tools.project_rename`
def apply_domain_promotion(project_root: Path, analysis_value: dict, result: dict, *, register_native: bool | None=None, launcher_root: Path | None=None) -> dict:
	return ProjectRenamer.apply_domain_promotion(project_root, analysis_value, result, register_native=register_native, launcher_root=launcher_root, maybe_promote_fn=maybe_promote_project_domain)
# @used-by :func:`apply_domain_promotion()`
# @used-by :mod:`agent_tools.project_rename`
def maybe_promote_project_domain(project_root: str | Path, analysis_value: dict, *, daily_root: Path | None=None, register_native: bool | None=None, launcher_root: Path | None=None) -> dict:
	return ProjectRenamer.maybe_promote_domain(project_root, analysis_value, daily_root=daily_root, register_native=register_native, launcher_root=launcher_root, rename_fn=rename_project)
# @used-by :func:`agent_tools.cli_registry._exec_rename_project()`
# @used-by :func:`agent_tools.shadow_replay_command._run_exec_rename_domain()`
# @used-by :func:`maybe_promote_project_domain()`
# @used-by :meth:`test_cleanup_integration.CleanupIntegrationTests.test_rename_project_cleanup_recent_and_old_path_history()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_project_preserves_all_seven_stages_config_journal_handoff_and_review_lineage()`
# @used-by :meth:`test_finalized_project_contract.FinalizedProjectContractTests.test_rename_rolls_back_finalized_fixture_on_review_authorize_regression()`
# @used-by :meth:`test_project_domain_drift.ProjectDomainDriftTests.test_check_project_flags_domain_drift_on_folder_and_registration_mismatch()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_preserves_launcher_handoff_reg_hash_and_review_lineage()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_cleanup_integration()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_rolls_back_on_collision_or_failure()`
# @used-by :meth:`test_project_rename.ProjectRenameTests.test_rename_project_updates_folder_indexes_registrations_rules_and_journal()`
# @used-by :meth:`test_project_rename_verification.ProjectRenameVerificationTests.test_post_verify_rolls_back_all_state_on_stage_or_review_regression()`
# @used-by :mod:`agent_tools.project_rename`
def rename_project(project_root: str | Path, *, domain: str | None=None, topic: str | None=None, daily_root: Path | None=None, register_native: bool | None=None, antigravity_projects_dirs: dict[str, Path] | None=None, antigravity_folders_json: Path | None=None, targets: list[str] | None=None, registrars: dict | None=None, launcher_root: Path | None=None) -> dict:
	return ProjectRenamer(project_root, domain=domain, topic=topic, daily_root=daily_root, register_native=register_native, antigravity_projects_dirs=antigravity_projects_dirs, antigravity_folders_json=antigravity_folders_json, targets=targets, registrars=registrars, launcher_root=launcher_root, update_index_fn=_update_projects_index, pre_snap_fn=capture_pre_rename_snapshot, verify_fn=verify_post_rename).rename()
# @used-by :mod:`agent_tools.project_rename`
def resolve_promotable_target_domain(analysis_value: dict, *, min_probability: int=75) -> tuple[str | None, str | None]:
	return ProjectRenamer.resolve_promotable_target_domain(analysis_value, min_probability=min_probability)
__all__ = ['_infer_daily_root', '_update_projects_index', 'apply_domain_promotion', 'maybe_promote_project_domain', 'rename_project', 'resolve_promotable_target_domain']
