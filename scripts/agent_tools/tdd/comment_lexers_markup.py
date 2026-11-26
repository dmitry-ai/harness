# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.MarkupCommentLexer import MarkupCommentLexer
# @used-by :mod:`agent_tools.tdd.comment_lexers_markup`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_dockerfile(source: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
	return MarkupCommentLexer.lex_dockerfile(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_markup`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_indent_hash(source: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
	return MarkupCommentLexer.lex_indent_hash(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_markup`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_sed(source: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
	return MarkupCommentLexer.lex_sed(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_markup`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_sfc(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return MarkupCommentLexer.lex_sfc(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_markup`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_tcl(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return MarkupCommentLexer.lex_tcl(source)
__all__ = ['lex_dockerfile', 'lex_indent_hash', 'lex_sed', 'lex_sfc', 'lex_tcl']
