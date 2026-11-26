# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.CommentDiff import CommentDiff
COMMENT_LEXER_LANGUAGES = CommentDiff.COMMENT_LEXER_LANGUAGES
_BASENAME_LANG = CommentDiff.BASENAME_LANG
_EXTENSION_LANG = CommentDiff.EXTENSION_LANG
# @used-by :mod:`agent_tools.tdd.comment_diff`
def _git_read_text(repo: Path, args: list[str]) -> str | None:
	return CommentDiff.git_read_text(repo, args)
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def classify_comment_or_whitespace_diff(path: str | Path, old_text: str | None, new_text: str | None) -> str | None:
	return CommentDiff(path, old_text, new_text).classify()
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_gates_and_classifiers_recognize_dotpy_files()`
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_all_software_code_suffixes_and_basenames_have_lexers()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_comment_only_diffs_accepted_for_all_20_languages()`
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def detect_comment_language(path: str | Path, *, content: str | None=None) -> str | None:
	return CommentDiff.detect_language(path, content=content)
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_all_software_code_suffixes_and_basenames_have_lexers()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_comment_only_diffs_accepted_for_all_20_languages()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_non_comment_and_edge_cases_fail_closed()`
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_comment_only_diff(path: str | Path, old_text: str | None, new_text: str | None) -> bool:
	return CommentDiff.is_comment_only(path, old_text, new_text)
# @used-by :meth:`test_diff_executability.DiffExecutabilityTests.test_whitespace_only_and_indentation_sensitive_fail_closed()`
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_whitespace_only_diff(path: str | Path, old_text: str | None, new_text: str | None) -> bool:
	return CommentDiff.is_whitespace_only(path, old_text, new_text)
# @used-by :mod:`agent_tools.tdd.comment_diff`
def lex_language(lang: str, source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return CommentDiff.lex_language(lang, source)
__all__ = ['COMMENT_LEXER_LANGUAGES', '_BASENAME_LANG', '_EXTENSION_LANG', '_git_read_text', 'classify_comment_or_whitespace_diff', 'detect_comment_language', 'is_comment_only_diff', 'is_whitespace_only_diff', 'lex_language']
