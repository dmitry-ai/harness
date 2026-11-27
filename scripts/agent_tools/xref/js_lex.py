# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Xref.Js.Lexer import Lexer
# @used-by :mod:`agent_tools.xref.js_lex`
def arrow_body_end(toks: list[tuple[str, str, int]], arrow_idx: int) -> int:
	return Lexer.arrow_body_end(toks, arrow_idx)
# @used-by :mod:`agent_tools.xref.js_lex`
def find_arrow_after_eq(toks: list[tuple[str, str, int]], eq_idx: int) -> int:
	return Lexer.find_arrow_after_eq(toks, eq_idx)
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
# @used-by :mod:`agent_tools.xref.js_lex`
def match_delim(toks: list[tuple[str, str, int]], start: int, open_ch: str, close_ch: str) -> int:
	return Lexer.match_delim(toks, start, open_ch, close_ch)
# @used-by :mod:`agent_tools.xref.js_lex`
def skip_ts_type_until(toks: list[tuple[str, str, int]], start: int, stop_set: set[str]) -> int:
	return Lexer.skip_ts_type_until(toks, start, stop_set)
# @used-by :mod:`agent_tools.xref.js_lex`
def tokenize_js(source: str) -> list[tuple[str, str, int]]:
	return Lexer(source).tokenize()
# @used-by :mod:`agent_tools.xref.js_lex`
def unquote(s: str) -> str:
	return Lexer.unquote(s)
__all__ = ['arrow_body_end', 'find_arrow_after_eq', 'match_delim', 'skip_ts_type_until', 'tokenize_js', 'unquote']
