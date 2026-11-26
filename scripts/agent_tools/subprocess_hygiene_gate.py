# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.SubprocessHygieneChecker import SubprocessHygieneChecker
from Df.Harness.Gate.SubprocessHygienePreToolGate import SubprocessHygienePreToolGate
from Df.Harness.Gate.SubprocessHygieneStagedGate import SubprocessHygieneStagedGate
# @used-by :meth:`test_subprocess_hygiene_and_tree_kill.SubprocessHygieneAndTreeKillTests.test_ast_hygiene_flags_unguarded_subprocess_in_tests_and_launchers_with_ratchet()`
# @used-by :mod:`agent_tools.subprocess_hygiene_gate`
def check_subprocess_hygiene_violations(path: str | Path, source: str, *, baseline_source: str | None=None) -> list[str]:
	return SubprocessHygieneChecker(path, source, baseline_source=baseline_source).check()
# @used-by :meth:`test_subprocess_hygiene_and_tree_kill.SubprocessHygieneAndTreeKillTests.test_pre_commit_and_pre_tool_use_enforce_subprocess_hygiene_ratchet()`
# @used-by :mod:`agent_tools.subprocess_hygiene_gate`
def evaluate_pre_tool_use_subprocess_hygiene(name: str, args: dict, payload: dict) -> str | None:
	return SubprocessHygienePreToolGate().check(name, args, payload)
# @used-by :mod:`agent_tools.subprocess_hygiene_gate`
def is_subprocess_hygiene_target(path: str | Path) -> bool:
	return SubprocessHygieneChecker.is_target(path)
# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_agent_staged()`
# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_code_size_ratchet()`
# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_subprocess_hygiene()`
# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_tdd_commit()`
# @used-by :mod:`agent_tools.subprocess_hygiene_gate`
def run_staged_gate(mod_name: str, func_name: str, *args, **kwargs) -> None:
	SubprocessHygieneStagedGate.run_staged_gate(mod_name, func_name, *args, **kwargs)
# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_subprocess_hygiene()`
# @used-by :mod:`agent_tools.subprocess_hygiene_gate`
def verify_staged_subprocess_hygiene(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	return SubprocessHygieneStagedGate(repo_root, staged_paths, use_index=use_index).verify()
__all__ = ['check_subprocess_hygiene_violations', 'evaluate_pre_tool_use_subprocess_hygiene', 'is_subprocess_hygiene_target', 'run_staged_gate', 'verify_staged_subprocess_hygiene']
