# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.CodeClassifier import CodeClassifier
SOFTWARE_CODE_SUFFIXES = CodeClassifier.SOFTWARE_CODE_SUFFIXES
_CODE_SUFFIX_ALT = CodeClassifier.CODE_SUFFIX_ALT
_EXTENSIONLESS_CODE_NAMES = CodeClassifier.EXTENSIONLESS_CODE_NAMES
_GIT_HOOK_SCRIPT_NAMES = CodeClassifier.GIT_HOOK_SCRIPT_NAMES
_PROJECT_MARKER_FILES = CodeClassifier.PROJECT_MARKER_FILES
_SCOPE_SUBDIR_SEGMENTS = CodeClassifier.SCOPE_SUBDIR_SEGMENTS
_SKIP_SCAN_DIRS = CodeClassifier.SKIP_SCAN_DIRS
_TEST_CAMEL_SUFFIX_RE = CodeClassifier.TEST_CAMEL_SUFFIX_RE
_TEST_DIR_SEGMENTS = CodeClassifier.TEST_DIR_SEGMENTS
_TEST_FILENAME_RE = CodeClassifier.TEST_FILENAME_RE
_TEST_HELPER_FILENAMES = CodeClassifier.TEST_HELPER_FILENAMES
# @used-by :mod:`agent_tools.tdd.classifier`
def _has_shebang(path: Path, content: str | None=None) -> bool:
	return CodeClassifier.has_shebang(path, content=content)
# @used-by :mod:`agent_tools.tdd.classifier`
def _norm_posix(path: str | Path) -> str:
	return CodeClassifier.norm_posix(path)
# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.__resolve_pre_tool_target()`
# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.__staged_code_entries()`
# @used-by :meth:`Df.Harness.Arch.TriggerClassifier.TriggerClassifier.__append_scale_reasons()`
# @used-by :meth:`Df.Harness.Arch.TriggerClassifier.TriggerClassifier.classify_code_change()`
# @used-by :meth:`Df.Harness.Issue.DirtyIssueFirstScanner.DirtyIssueFirstScanner.__parse_dirty_porcelain()`
# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.resolve_target()`
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_gates_and_classifiers_recognize_dotpy_files()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_classifier_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_universal_code_vs_test_vs_non_code_classification()`
# @used-by :mod:`agent_tools.tdd.classifier`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def classify_code_path(path: str | Path, *, content: str | None=None) -> str:
	return CodeClassifier(path, content=content).classify()
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_classifier_module_behavior_and_parity()`
# @used-by :mod:`agent_tools.tdd.classifier`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def count_repo_test_files(scope_root: Path | None) -> int:
	return CodeClassifier.count_repo_test_files(scope_root)
# @used-by :mod:`agent_tools.tdd.classifier`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_software_code_file(path: str | Path, *, content: str | None=None) -> bool:
	return CodeClassifier.is_software_code_file(path, content=content)
# @used-by :mod:`agent_tools.tdd.classifier`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_test_file(path: str | Path, *, content: str | None=None) -> bool:
	return CodeClassifier.is_test_file(path, content=content)
# @used-by :meth:`test_code_fanout_gates.CodeFanoutGatesTests.test_parallel_deleted_worktrees_isolate_tdd_scopes_and_accept_main_full_green()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_classifier_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_resolve_code_scope_normalizes_git_and_non_git_test_dirs()`
# @used-by :meth:`test_tdd_worktree_and_subagent_trace.TddWorktreeAndSubagentTraceTests.test_resolve_code_scope_maps_deleted_worktree_to_main_code_repo()`
# @used-by :meth:`test_worktree_flow.WorktreeFlowTests.test_resolve_code_scope_keeps_active_worktree_for_new_files_and_falls_back_after_cleanup()`
# @used-by :mod:`agent_tools.tdd.classifier`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def resolve_code_scope(path: str | Path) -> Path:
	return CodeClassifier.resolve_code_scope(path)
__all__ = ['SOFTWARE_CODE_SUFFIXES', '_CODE_SUFFIX_ALT', '_EXTENSIONLESS_CODE_NAMES', '_GIT_HOOK_SCRIPT_NAMES', '_PROJECT_MARKER_FILES', '_SCOPE_SUBDIR_SEGMENTS', '_SKIP_SCAN_DIRS', '_TEST_CAMEL_SUFFIX_RE', '_TEST_DIR_SEGMENTS', '_TEST_FILENAME_RE', '_TEST_HELPER_FILENAMES', '_has_shebang', '_norm_posix', 'classify_code_path', 'count_repo_test_files', 'is_software_code_file', 'is_test_file', 'resolve_code_scope']
