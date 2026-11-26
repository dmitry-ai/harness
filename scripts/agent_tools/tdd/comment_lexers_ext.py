# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.ExtCommentLexer import ExtCommentLexer
# @used-by :mod:`agent_tools.tdd.comment_lexers_ext`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_cmake(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return ExtCommentLexer.lex_cmake(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_ext`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_fsharp(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return ExtCommentLexer.lex_fsharp(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_ext`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_hcl(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return ExtCommentLexer.lex_hcl(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_ext`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_lua(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return ExtCommentLexer.lex_lua(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_ext`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_rust(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return ExtCommentLexer.lex_rust(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_ext`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_sass(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return ExtCommentLexer.lex_sass(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_ext`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_zig(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return ExtCommentLexer.lex_zig(source)
__all__ = ['lex_cmake', 'lex_fsharp', 'lex_hcl', 'lex_lua', 'lex_rust', 'lex_sass', 'lex_zig']
