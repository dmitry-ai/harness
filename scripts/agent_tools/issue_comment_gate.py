# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.IssueCommentChecker import IssueCommentChecker
from Df.Harness.Gate.IssueCommentPreToolGate import IssueCommentPreToolGate
from Df.Harness.Gate.IssueCommentStagedGate import IssueCommentStagedGate
# @used-by :meth:`test_comment_exemption_and_denied_writes.CommentExemptionAndDeniedWritesTests.test_issue_comment_gate_skips_body_misalignment_on_comment_only_diff()`
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_gates_and_classifiers_recognize_dotpy_files()`
# @used-by :meth:`test_issue_comment_gate.IssueCommentGateTests.test_allows_block_adjacent_function_header_trailing_and_new_file_comments()`
# @used-by :meth:`test_issue_comment_gate.IssueCommentGateTests.test_rejects_duplicate_and_out_of_header_author_lines()`
# @used-by :meth:`test_issue_comment_gate.IssueCommentGateTests.test_rejects_header_dumped_and_misplaced_issue_comments_across_languages()`
# @used-by :meth:`test_issue_comment_gate.IssueCommentGateTests.test_supports_xml_css_and_rejects_coarse_class_header_for_single_method_edit()`
# @used-by :mod:`agent_tools.issue_comment_gate`
def check_issue_comment_violations(path: str | Path, source: str, *, baseline_source: str | None=None) -> list[str]:
	return IssueCommentChecker(path, source, baseline_source=baseline_source).check()
# @used-by :mod:`agent_tools.issue_comment_gate`
def evaluate_pre_tool_use_issue_comment(name: str, args: dict, payload: dict) -> str | None:
	return IssueCommentPreToolGate().check(name, args, payload)
# @used-by :mod:`agent_tools.issue_comment_gate`
def verify_staged_issue_comment_placement(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	return IssueCommentStagedGate(repo_root, staged_paths, use_index=use_index).verify()
__all__ = ['check_issue_comment_violations', 'evaluate_pre_tool_use_issue_comment', 'verify_staged_issue_comment_placement']
