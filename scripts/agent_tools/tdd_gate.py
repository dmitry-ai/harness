# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-24
# "Decompose tdd_gate.py into modular TDD verification package":
# https://github.com/dmitry-ai/harness/issues/169
from .tdd.classifier import (
	SOFTWARE_CODE_SUFFIXES,
	_CODE_SUFFIX_ALT,
	_EXTENSIONLESS_CODE_NAMES,
	_GIT_HOOK_SCRIPT_NAMES,
	_PROJECT_MARKER_FILES,
	_SCOPE_SUBDIR_SEGMENTS,
	_SKIP_SCAN_DIRS,
	_TEST_CAMEL_SUFFIX_RE,
	_TEST_DIR_SEGMENTS,
	_TEST_FILENAME_RE,
	_TEST_HELPER_FILENAMES,
	_has_shebang,
	_norm_posix,
	classify_code_path,
	count_repo_test_files,
	is_software_code_file,
	is_test_file,
	resolve_code_scope,
)
from .tdd.commands import (
	_RIGGED_FAILURE_RE,
	_SHELL_DELETE_RE,
	_SHELL_TEST_FILE_TOKEN_RE,
	_SHELL_WRITE_CMD_PATTERNS,
	_extract_cmd_paths,
	_single_test_file_in_args,
	# 2026-11-23
	# "Add parallel fail-fast run-tests runner with module timeouts and TDD gate registration":
	# https://github.com/dmitry-ai/harness/issues/160
	classify_test_command,
	shell_code_write_targets,
	shell_test_delete_targets,
	# 2026-11-23
	# "Implement core Issue-First verification engine in agent_tools/issue_first_gate.py":
	# https://github.com/dmitry-ai/harness/issues/143
	shell_write_targets,
)
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
from .tdd.comment_diff import (
	COMMENT_LEXER_LANGUAGES,
	# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
	classify_comment_or_whitespace_diff,
	detect_comment_language,
	is_comment_only_diff,
	is_whitespace_only_diff,
)
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
from .tdd.diff_executability import (
	# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
	DEFAULT_MAX_REPORTED_FILES,
	# 2026-11-26 "Codify single-source diff executability contract across Harness gates and runtime snapshot": https://github.com/dmitry-ai/harness/issues/360
	DIFF_EXECUTABILITY_GATES,
	NON_EXECUTABLE_CATEGORIES,
	classify_git_path,
	classify_git_range,
	classify_text_diff,
	# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
	format_land_diff_telemetry,
	is_git_path_non_executable,
	is_non_executable_diff,
	resolve_land_test_plan,
	# 2026-11-26 "Codify single-source diff executability contract across Harness gates and runtime snapshot": https://github.com/dmitry-ai/harness/issues/360
	should_run_snapshot_canary,
	validate_no_tests_override_reason,
)
from .tdd.enforcement import (
	_active_turn_issue_urls,
	_compute_edited_content,
	_git_head_text,
	_git_index_text,
	evaluate_pre_tool_use_tdd,
	verify_staged_tdd_diff,
)
from .tdd.evaluator import (
	_command_matches_scope,
	# 2026-11-23
	# "Add parallel fail-fast run-tests runner with module timeouts and TDD gate registration":
	# https://github.com/dmitry-ai/harness/issues/160
	_git_main_repo_root,
	# 2026-11-23
	# "Enforce PreToolUse fail-fast normalization and block redundant schedule timers over run_command":
	# https://github.com/dmitry-ai/harness/issues/162
	evaluate_tdd_events,
)
from .tdd.events import (
	# 2026-11-23
	# "Detect unfinished background tasks in Antigravity turns and inherit unclosed TDD-FULL-GATE":
	# https://github.com/dmitry-ai/harness/issues/166
	_antigravity_segment_is_interrupted,
	_is_git_commit_command,
	_normalize_args_dict,
	_unwrap_arg_value,
	build_command_tdd_event,
	build_file_write_tdd_event,
	extract_antigravity_tdd_events,
)
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
from .tdd.exemption import (
	is_diff_exempt,
	is_git_path_exempt,
	is_write_event_exempt,
)
# 2026-11-25
# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
# https://github.com/dmitry-ai/harness/issues/239
from .tdd.mechanical import (
	find_matching_mechanical_recipes,
	matches_mechanical_recipe,
	record_mechanical_exemption,
	validate_mechanical_reason,
)
from .tdd.outcomes import (
	_BG_TASK_FINISHED_RE,
	_BG_TASK_ID_RE,
	_BG_TASK_LOG_RE,
	_EXIT_CODE_RE,
	_INVOCATION_ERROR_RE,
	_OUTPUT_BODY_SPLIT_RE,
	_ZERO_TESTS_RE,
	_infer_exit_code_from_log_text,
	_uri_to_local_path,
	parse_command_outcome,
)
from .tdd.ratchet import (
	_RATCHET_OK_LINE_RE,
	_RATCHET_SLOP_RE,
	_SKIP_MARKER_RE,
	_TEST_DEF_RE,
	_load_turn_ratchet_receipts,
	_match_ratchet_target,
	_parse_ratchet_ok_lines,
	find_ratchet_approval,
	ratchet_diff_violations,
	validate_ratchet_reason,
)
from .tdd.substantive import (
	_ASSERTION_LINE_RE,
	_CODE_LIT_EXT_RE,
	_SOURCE_TEXT_NONPY_READ_RE,
	_TEMP_PATH_HINT_RE,
	_ast_expr_contains_code_literal,
	_ast_expr_uses_repo_anchor,
	_ast_expr_uses_temp_base,
	is_substantive_test_content,
	source_text_assertion_issues,
)
# 2026-11-23
# "Implement universal TDD verification engine in agent_tools/tdd_gate.py":
# https://github.com/dmitry-ai/harness/issues/135
# 2026-11-24
# "Decompose tdd_gate.py into modular TDD verification package":
# https://github.com/dmitry-ai/harness/issues/169
__all__ = [
	'COMMENT_LEXER_LANGUAGES',
	# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
	'DEFAULT_MAX_REPORTED_FILES',
	# 2026-11-26 "Codify single-source diff executability contract across Harness gates and runtime snapshot": https://github.com/dmitry-ai/harness/issues/360
	'DIFF_EXECUTABILITY_GATES',
	'NON_EXECUTABLE_CATEGORIES',
	'SOFTWARE_CODE_SUFFIXES',
	'build_command_tdd_event',
	'build_file_write_tdd_event',
	'classify_code_path',
	'classify_comment_or_whitespace_diff',
	'classify_git_path',
	'classify_git_range',
	'classify_test_command',
	'classify_text_diff',
	'count_repo_test_files',
	'detect_comment_language',
	'evaluate_pre_tool_use_tdd',
	'evaluate_tdd_events',
	'extract_antigravity_tdd_events',
	'find_matching_mechanical_recipes',
	'find_ratchet_approval',
	# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
	'format_land_diff_telemetry',
	'is_comment_only_diff',
	'is_diff_exempt',
	'is_git_path_exempt',
	'is_git_path_non_executable',
	'is_non_executable_diff',
	'is_software_code_file',
	'is_substantive_test_content',
	'is_test_file',
	'is_whitespace_only_diff',
	'is_write_event_exempt',
	'matches_mechanical_recipe',
	'parse_command_outcome',
	'ratchet_diff_violations',
	'record_mechanical_exemption',
	'resolve_code_scope',
	'resolve_land_test_plan',
	'shell_code_write_targets',
	'shell_test_delete_targets',
	'shell_write_targets',
	# 2026-11-26 "Codify single-source diff executability contract across Harness gates and runtime snapshot": https://github.com/dmitry-ai/harness/issues/360
	'should_run_snapshot_canary',
	'source_text_assertion_issues',
	'validate_mechanical_reason',
	'validate_no_tests_override_reason',
	'validate_ratchet_reason',
	'verify_staged_tdd_diff',
]
