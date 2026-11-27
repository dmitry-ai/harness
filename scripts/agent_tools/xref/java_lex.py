# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Java.Lexer import Lexer
# @used-by :mod:`agent_tools.xref.java_lex`
def count_top_args(toks: list[tuple[str, str, int]], open_p: int, close_p: int) -> int:
	return Lexer.count_top_args(toks, open_p, close_p)
# @used-by :mod:`agent_tools.xref.java_lex`
def extract_param_types(toks: list[tuple[str, str, int]], open_p: int, close_p: int) -> tuple[list[str], bool]:
	return Lexer.extract_param_types(toks, open_p, close_p)
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
# @used-by :mod:`agent_tools.xref.java_lex`
def match_delim(toks: list[tuple[str, str, int]], start: int, open_ch: str, close_ch: str) -> int:
	return Lexer.match_delim(toks, start, open_ch, close_ch)
# @used-by :mod:`agent_tools.xref.java_lex`
def skip_annotation(toks: list[tuple[str, str, int]], at_i: int, end: int) -> int:
	return Lexer.skip_annotation(toks, at_i, end)
# @used-by :mod:`agent_tools.xref.java_lex`
def tokenize_java(source: str) -> list[tuple[str, str, int]]:
	return Lexer(source).tokenize()
__all__ = ['count_top_args', 'extract_param_types', 'match_delim', 'skip_annotation', 'tokenize_java']
