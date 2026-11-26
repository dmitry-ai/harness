# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import ast
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.SubstantiveTestChecker import SubstantiveTestChecker
_ASSERTION_LINE_RE = SubstantiveTestChecker.ASSERTION_LINE_RE
_CODE_LIT_EXT_RE = SubstantiveTestChecker.CODE_LIT_EXT_RE
_SOURCE_TEXT_NONPY_READ_RE = SubstantiveTestChecker.SOURCE_TEXT_NONPY_READ_RE
_TEMP_PATH_HINT_RE = SubstantiveTestChecker.TEMP_PATH_HINT_RE
# @used-by :mod:`agent_tools.tdd.substantive`
def _ast_expr_contains_code_literal(node: ast.AST) -> str | None:
	return SubstantiveTestChecker.ast_expr_contains_code_literal(node)
# @used-by :mod:`agent_tools.tdd.substantive`
def _ast_expr_uses_repo_anchor(node: ast.AST) -> bool:
	return SubstantiveTestChecker.ast_expr_uses_repo_anchor(node)
# @used-by :mod:`agent_tools.tdd.substantive`
def _ast_expr_uses_temp_base(node: ast.AST) -> bool:
	return SubstantiveTestChecker.ast_expr_uses_temp_base(node)
# @used-by :meth:`test_comment_exemption_and_denied_writes.CommentExemptionAndDeniedWritesTests.test_tdd_exempts_comment_only_test_edits_and_recognizes_java_assertions()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_substantive_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_behavioral_test_guard_catches_source_text_and_wrappers_without_false_positives()`
# @used-by :mod:`agent_tools.tdd.substantive`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_substantive_test_content(path: str | Path, content: str) -> tuple[bool, str | None]:
	return SubstantiveTestChecker(path, content).check_content()
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_substantive_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_behavioral_test_guard_catches_source_text_and_wrappers_without_false_positives()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_hardening_header_exit_code_indirect_source_read_and_index_blob()`
# @used-by :mod:`agent_tools.tdd.substantive`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def source_text_assertion_issues(path: str | Path, added_lines: list[str] | tuple[str, ...], *, full_content: str | None=None, added_line_numbers: set[int] | None=None) -> list[str]:
	return SubstantiveTestChecker.source_text_assertion_issues(path, added_lines, full_content=full_content, added_line_numbers=added_line_numbers)
__all__ = ['_ASSERTION_LINE_RE', '_CODE_LIT_EXT_RE', '_SOURCE_TEXT_NONPY_READ_RE', '_TEMP_PATH_HINT_RE', '_ast_expr_contains_code_literal', '_ast_expr_uses_repo_anchor', '_ast_expr_uses_temp_base', 'is_substantive_test_content', 'source_text_assertion_issues']
