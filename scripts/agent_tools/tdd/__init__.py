# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from .classifier import SOFTWARE_CODE_SUFFIXES, classify_code_path, count_repo_test_files, is_software_code_file, is_test_file, resolve_code_scope
from .commands import classify_test_command, shell_code_write_targets, shell_test_delete_targets, shell_write_targets
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
from .comment_diff import COMMENT_LEXER_LANGUAGES, detect_comment_language, is_comment_only_diff
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
	'SOFTWARE_CODE_SUFFIXES',
	'build_command_tdd_event',
	'build_file_write_tdd_event',
	'classify_code_path',
	'classify_test_command',
	'count_repo_test_files',
	'detect_comment_language',
	'evaluate_pre_tool_use_tdd',
	'evaluate_tdd_events',
	'extract_antigravity_tdd_events',
	'find_matching_mechanical_recipes',
	'find_ratchet_approval',
	'is_comment_only_diff',
	'is_diff_exempt',
	'is_git_path_exempt',
	'is_software_code_file',
	'is_substantive_test_content',
	'is_test_file',
	'is_write_event_exempt',
	'matches_mechanical_recipe',
	'parse_command_outcome',
	'ratchet_diff_violations',
	'record_mechanical_exemption',
	'resolve_code_scope',
	'shell_code_write_targets',
	'shell_test_delete_targets',
	'shell_write_targets',
	'source_text_assertion_issues',
	'validate_mechanical_reason',
	'validate_ratchet_reason',
	'verify_staged_tdd_diff',
]
