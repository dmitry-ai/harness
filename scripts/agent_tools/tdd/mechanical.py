# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.MechanicalExemption import MechanicalExemption
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_mechanical_exemption_spawns_zero_git_without_recipes()`
# @used-by :mod:`agent_tools.tdd.mechanical`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def find_matching_mechanical_recipes(repo_root: Path | None, *, message: str | None=None, project_root: Path | None=None) -> list[dict]:
	return MechanicalExemption.find_matching_recipes(repo_root, message=message, project_root=project_root)
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_mechanical_exemption_spawns_zero_git_without_recipes()`
# @used-by :meth:`test_tdd_pre_tool_use_perf.TddPreToolUsePerfTests.test_mechanical_exemption_spawns_zero_subprocesses_without_recipes()`
# @used-by :mod:`agent_tools.tdd.mechanical`
def is_git_file_mechanical_exempt(repo_root: Path, rel_posix: str, *, disk_text: str | None=None, use_index: bool=False, message: str | None=None, project_root: Path | None=None) -> bool:
	return MechanicalExemption.is_git_file_exempt(repo_root, rel_posix, disk_text=disk_text, use_index=use_index, message=message, project_root=project_root)
# @used-by :mod:`agent_tools.tdd.mechanical`
def is_mechanical_diff_exempt(old_text: str | None, new_text: str | None, *, repo_root: Path | None=None, message: str | None=None, project_root: Path | None=None) -> bool:
	return MechanicalExemption.is_mechanical_diff_exempt(old_text, new_text, repo_root=repo_root, message=message, project_root=project_root)
# @used-by :mod:`agent_tools.tdd.mechanical`
def matches_any_mechanical_recipes(old_text: str | None, new_text: str | None, recipes: list[dict] | tuple[dict, ...]) -> bool:
	return MechanicalExemption.matches_any_recipes(old_text, new_text, recipes)
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_matches_mechanical_recipe_strict_line_identity()`
# @used-by :mod:`agent_tools.tdd.mechanical`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def matches_mechanical_recipe(old_text: str | None, new_text: str | None, recipe: dict) -> bool:
	return MechanicalExemption.matches_recipe(old_text, new_text, recipe)
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_tdd_exempt_mechanical()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_worktree_land_skips_tests_for_non_executable_and_runs_for_executable()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_auditor_and_evaluator_accept_committed_mechanical_diff_and_reject_drift()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_cli_registration_and_validation_errors()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_git_gate_enforces_exact_recipe_issue_binding_and_mixed_m2_commit()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_pre_tool_use_allows_matching_mechanical_edit_and_denies_extraneous_edit()`
# @used-by :mod:`agent_tools.tdd.mechanical`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def record_mechanical_exemption(project_root: str | Path, *, repo: str | Path | None=None, issue_url: str, pattern: str, replacement: str, reason: str, is_regex: bool=False, ignore_case: bool=False, conversation: str | None=None, turn_key: str | None=None) -> dict:
	return MechanicalExemption.record_exemption(project_root, repo=repo, issue_url=issue_url, pattern=pattern, replacement=replacement, reason=reason, is_regex=is_regex, ignore_case=ignore_case, conversation=conversation, turn_key=turn_key)
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_cli_registration_and_validation_errors()`
# @used-by :mod:`agent_tools.tdd.mechanical`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def validate_mechanical_reason(reason: str) -> tuple[bool, str | None]:
	return MechanicalExemption.validate_reason(reason)
__all__ = ['find_matching_mechanical_recipes', 'is_git_file_mechanical_exempt', 'is_mechanical_diff_exempt', 'matches_any_mechanical_recipes', 'matches_mechanical_recipe', 'record_mechanical_exemption', 'validate_mechanical_reason']
