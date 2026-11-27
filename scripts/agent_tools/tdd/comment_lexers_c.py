# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.CLikeCommentLexer import CLikeCommentLexer
# @used-by :mod:`agent_tools.tdd.comment_lexers_c`
def can_start_regex(tokens: list[str]) -> bool:
	return CLikeCommentLexer.can_start_regex(tokens)
# @used-by :mod:`agent_tools.tdd.comment_lexers_c`
def consume_shebang(source: str, tokens: list[str], enabled: bool) -> int:
	return CLikeCommentLexer.consume_shebang(source, tokens, enabled)
# @used-by :mod:`agent_tools.tdd.comment_lexers_c`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_c_like(source: str, cfg: dict) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return CLikeCommentLexer(source, cfg).lex()
# @used-by :mod:`agent_tools.tdd.comment_lexers_c`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_php(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return CLikeCommentLexer.lex_php(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_c`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_python(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return CLikeCommentLexer.lex_python(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_c`
def scan_word_or_char(src: str, i: int, tokens: list[str]) -> int:
	return CLikeCommentLexer.scan_word_or_char(src, i, tokens)
__all__ = ['can_start_regex', 'consume_shebang', 'lex_c_like', 'lex_php', 'lex_python', 'scan_word_or_char']
