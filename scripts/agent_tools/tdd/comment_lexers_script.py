# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.ScriptCommentLexer import ScriptCommentLexer
# @used-by :mod:`agent_tools.tdd.comment_lexers_script`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_batch(source: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
	return ScriptCommentLexer.lex_batch(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_script`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_hash_script(source: str, cfg: dict) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return ScriptCommentLexer.lex_hash_script(source, cfg)
# @used-by :mod:`agent_tools.tdd.comment_lexers_script`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_sql(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return ScriptCommentLexer.lex_sql(source)
# @used-by :mod:`agent_tools.tdd.comment_lexers_script`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_vbscript(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return ScriptCommentLexer.lex_vbscript(source)
__all__ = ['lex_batch', 'lex_hash_script', 'lex_sql', 'lex_vbscript']
