# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.fs import df_path_suffix
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.XrefChecker import XrefChecker
from Df.Harness.Gate.XrefPreToolGate import XrefPreToolGate
from Df.Harness.Gate.XrefStagedGate import XrefStagedGate
from Df.Harness.Gate.XrefWorktreeGate import XrefWorktreeGate
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
def _path_suffix(path: str | Path) -> str:
	return df_path_suffix(path)
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_gates_and_classifiers_recognize_dotpy_files()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax()`
# @used-by :mod:`agent_tools.xref_gate`
def check_file_xref_violations(path: str | Path, source: str, *, baseline_source: str | None=None) -> list[str]:
	return XrefChecker(path, source, baseline_source=baseline_source).check()
# @used-by :mod:`agent_tools.xref_gate`
def evaluate_pre_tool_use_xref(name: str, args: dict, payload: dict) -> str | None:
	return XrefPreToolGate().check(name, args, payload)
# @used-by :meth:`test_xref_gate.XrefGateTests.test_pre_tool_use_blocks_unannotated_new_python_js_java_and_forbidden_syntax()`
# @used-by :mod:`agent_tools.xref_gate`
def is_xref_governed_repo(repo_root: Path, staged_paths: list[str] | tuple[str, ...]=(), *, overrides_map: dict[str, str | None] | None=None) -> bool:
	return XrefChecker.is_governed_repo(repo_root, staged_paths, overrides_map=overrides_map)
# @used-by :meth:`test_xref_gate.XrefGateTests._assert_staged_js_java_and_legacy()`
# @used-by :mod:`agent_tools.xref_gate`
def verify_staged_xref(repo_root: Path, staged_paths: list[str], *, use_index: bool=True, strict: bool=False) -> list[str]:
	return XrefStagedGate(repo_root, staged_paths, use_index=use_index, strict=strict).verify()
# @used-by :func:`agent_tools.worktree_flow._rebase_and_test()`
# @used-by :meth:`test_xref_gate.XrefGateTests.test_worktree_land_blocks_stale_xref_and_passes_when_synced()`
# @used-by :mod:`agent_tools.xref_gate`
def verify_worktree_xref_changes(wt_path: Path, target_branch: str, *, strict: bool=False) -> list[str]:
	return XrefWorktreeGate(wt_path, target_branch, strict=strict).verify()
__all__ = ['check_file_xref_violations', 'evaluate_pre_tool_use_xref', 'is_xref_governed_repo', 'verify_staged_xref', 'verify_worktree_xref_changes']
