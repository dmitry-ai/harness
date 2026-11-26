# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from .classifier import SOFTWARE_CODE_SUFFIXES, classify_code_path, count_repo_test_files, is_software_code_file, is_test_file, resolve_code_scope
from .commands import classify_test_command, shell_code_write_targets, shell_test_delete_targets, shell_write_targets
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
from .comment_diff import COMMENT_LEXER_LANGUAGES, classify_comment_or_whitespace_diff, detect_comment_language, is_comment_only_diff, is_whitespace_only_diff
# 2026-11-26 "Add diff executability telemetry to worktree_land output and tdd_check scopes": https://github.com/dmitry-ai/harness/issues/359
# 2026-11-26 "Codify single-source diff executability contract across Harness gates and runtime snapshot": https://github.com/dmitry-ai/harness/issues/360
from .diff_executability import DEFAULT_MAX_REPORTED_FILES, DIFF_EXECUTABILITY_GATES, NON_EXECUTABLE_CATEGORIES, classify_git_path, classify_git_range, classify_text_diff, format_land_diff_telemetry, is_git_path_non_executable, is_non_executable_diff, resolve_land_test_plan, should_run_snapshot_canary, validate_no_tests_override_reason
from .enforcement import evaluate_pre_tool_use_tdd, verify_staged_tdd_diff
from .evaluator import evaluate_tdd_events
from .events import build_command_tdd_event, build_file_write_tdd_event, extract_antigravity_tdd_events
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
from .exemption import is_diff_exempt, is_git_path_exempt, is_write_event_exempt
# 2026-11-25
# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
# https://github.com/dmitry-ai/harness/issues/239
from .mechanical import find_matching_mechanical_recipes, matches_mechanical_recipe, record_mechanical_exemption, validate_mechanical_reason
from .outcomes import parse_command_outcome
from .ratchet import find_ratchet_approval, ratchet_diff_violations, validate_ratchet_reason
from .substantive import is_substantive_test_content, source_text_assertion_issues
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
