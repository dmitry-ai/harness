# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.CommentScanners import CommentScanners
# @used-by :mod:`agent_tools.tdd.comment_scanners`
def finalize_line_tokens(raw_tokens: list[str]) -> tuple[str, ...]:
	return CommentScanners.finalize_line_tokens(raw_tokens)
# @used-by :func:`agent_tools.xref.java_lex._tokenize_java_step()`
# @used-by :func:`agent_tools.xref.js_lex._tokenize_js_step()`
# @used-by :mod:`agent_tools.tdd.comment_scanners`
def scan_block_comment(src: str, pos: int, open_tok: str, close_tok: str, *, nested: bool=False) -> int:
	return CommentScanners.scan_block_comment(src, pos, open_tok, close_tok, nested=nested)
# @used-by :mod:`agent_tools.tdd.comment_scanners`
def scan_cpp_raw(src: str, pos: int) -> int:
	return CommentScanners.scan_cpp_raw(src, pos)
# @used-by :mod:`agent_tools.tdd.comment_scanners`
def scan_css_url(src: str, pos: int) -> int:
	return CommentScanners.scan_css_url(src, pos)
# @used-by :mod:`agent_tools.tdd.comment_scanners`
def scan_heredoc(src: str, pos: int, *, php: bool=False) -> int:
	return CommentScanners.scan_heredoc(src, pos, php=php)
# @used-by :func:`agent_tools.xref.js_lex._tokenize_js_atom()`
# @used-by :mod:`agent_tools.tdd.comment_scanners`
def scan_js_regex(src: str, pos: int) -> int:
	return CommentScanners.scan_js_regex(src, pos)
# @used-by :mod:`agent_tools.tdd.comment_scanners`
def scan_line_block(src: str, pos: int, end_prefix: str) -> int:
	return CommentScanners.scan_line_block(src, pos, end_prefix)
# @used-by :func:`agent_tools.xref.java_lex._tokenize_java_step()`
# @used-by :func:`agent_tools.xref.js_lex._tokenize_js_step()`
# @used-by :mod:`agent_tools.tdd.comment_scanners`
def scan_line_comment(src: str, pos: int, *, stop_tag: str='') -> int:
	return CommentScanners.scan_line_comment(src, pos, stop_tag=stop_tag)
# @used-by :mod:`agent_tools.tdd.comment_scanners`
def scan_ps_herestring(src: str, pos: int, quote: str) -> int:
	return CommentScanners.scan_ps_herestring(src, pos, quote)
# @used-by :func:`agent_tools.xref.java_lex._tokenize_java_atom()`
# @used-by :func:`agent_tools.xref.js_lex._tokenize_js_atom()`
# @used-by :mod:`agent_tools.tdd.comment_scanners`
def scan_quoted(src: str, pos: int, quote: str, *, backslash: bool=True, doubled: bool=False, allow_nl: bool=True, backtick: bool=False) -> int:
	return CommentScanners.scan_quoted(src, pos, quote, backslash=backslash, doubled=doubled, allow_nl=allow_nl, backtick=backtick)
# @used-by :func:`agent_tools.xref.java_lex._tokenize_java_atom()`
# @used-by :mod:`agent_tools.tdd.comment_scanners`
def scan_triple_quote(src: str, pos: int, quote: str) -> int:
	return CommentScanners.scan_triple_quote(src, pos, quote)
__all__ = ['finalize_line_tokens', 'scan_block_comment', 'scan_cpp_raw', 'scan_css_url', 'scan_heredoc', 'scan_js_regex', 'scan_line_block', 'scan_line_comment', 'scan_ps_herestring', 'scan_quoted', 'scan_triple_quote']
