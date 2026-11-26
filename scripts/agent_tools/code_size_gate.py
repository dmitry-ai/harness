# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.git import df_git_root
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.CodeSizeAnalyzer import CodeSizeAnalyzer
from Df.Harness.Gate.CodeSizeChecker import CodeSizeChecker
from Df.Harness.Gate.CodeSizePreToolGate import CodeSizePreToolGate
from Df.Harness.Gate.CodeSizeStagedGate import CodeSizeStagedGate
import ast
PROD_FILE_SLOC_LIMIT = CodeSizeChecker.PROD_FILE_SLOC_LIMIT
PROD_FUNC_SLOC_LIMIT = CodeSizeChecker.PROD_FUNC_SLOC_LIMIT
PROD_MCCABE_LIMIT = CodeSizeChecker.PROD_MCCABE_LIMIT
TEST_FILE_SLOC_LIMIT = CodeSizeChecker.TEST_FILE_SLOC_LIMIT
TEST_FUNC_SLOC_LIMIT = CodeSizeChecker.TEST_FUNC_SLOC_LIMIT
TEST_MCCABE_LIMIT = CodeSizeChecker.TEST_MCCABE_LIMIT
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
# @used-by :mod:`agent_tools.code_size_gate`
def _find_git_root(path: Path) -> Path | None:
	return df_git_root(path)
# @used-by :mod:`agent_tools.code_size_gate`
def _iter_functions(node: ast.AST, prefix: str='') -> list[tuple[str, ast.AST]]:
	return CodeSizeAnalyzer.iter_functions(node, prefix)
# @used-by :mod:`agent_tools.code_size_gate`
def _resolve_python_target(args: dict, payload: dict) -> tuple[Path, Path, str] | None:
	return CodeSizeAnalyzer.resolve_python_target(args, payload)
# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_comments_docstrings_and_declarative_tables_excluded_from_sloc()`
# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_override_decorator_and_typing_import_excluded_from_sloc()`
# @used-by :mod:`agent_tools.code_size_gate`
def analyze_python_source(source: str) -> dict:
	return CodeSizeAnalyzer(source).analyze()
# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_comments_docstrings_and_declarative_tables_excluded_from_sloc()`
# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_legacy_ratchet_allows_holding_or_shrinking_blocks_growth()`
# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_mccabe_complexity_and_semicolon_anti_gaming()`
# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_new_file_and_function_limits_and_test_soft_limits()`
# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_override_decorator_and_typing_import_excluded_from_sloc()`
# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_check_python_size_violations_rejects_syntax_error()`
# @used-by :mod:`agent_tools.code_size_gate`
def check_python_size_violations(path: str | Path, source: str, *, baseline_source: str | None=None) -> list[str]:
	return CodeSizeChecker(path, source, baseline_source=baseline_source).check()
# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_legacy_oversized_edit_deferred_in_pre_tool_use_while_write_file_enforced()`
# @used-by :mod:`agent_tools.code_size_gate`
def evaluate_pre_tool_use_code_size(name: str, args: dict, payload: dict) -> str | None:
	return CodeSizePreToolGate().check(name, args, payload)
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_code_size_ratchet()`
# @used-by :meth:`test_python_integrity_gate.PythonIntegrityGateTests.test_pre_commit_and_worktree_land_enforce_integrity_and_ratchet()`
# @used-by :mod:`agent_tools.code_size_gate`
def verify_staged_code_size_ratchet(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	return CodeSizeStagedGate(repo_root, staged_paths, use_index=use_index).verify()
__all__ = ['PROD_FILE_SLOC_LIMIT', 'PROD_FUNC_SLOC_LIMIT', 'PROD_MCCABE_LIMIT', 'TEST_FILE_SLOC_LIMIT', 'TEST_FUNC_SLOC_LIMIT', 'TEST_MCCABE_LIMIT', '_find_git_root', '_iter_functions', '_resolve_python_target', 'analyze_python_source', 'check_python_size_violations', 'evaluate_pre_tool_use_code_size', 'verify_staged_code_size_ratchet']
