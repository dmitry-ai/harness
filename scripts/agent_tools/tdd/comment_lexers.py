# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from .comment_lexers_c import lex_c_like, lex_php, lex_python
from .comment_lexers_script import lex_batch, lex_hash_script, lex_sql, lex_vbscript
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
__all__ = [
	'lex_batch',
	'lex_c_like',
	'lex_hash_script',
	'lex_php',
	'lex_python',
	'lex_sql',
	'lex_vbscript',
]
