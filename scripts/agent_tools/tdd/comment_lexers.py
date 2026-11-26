# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from .comment_lexers_c import lex_c_like, lex_php, lex_python
# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
from .comment_lexers_ext import lex_cmake, lex_fsharp, lex_hcl, lex_lua, lex_rust, lex_sass, lex_zig
from .comment_lexers_markup import lex_dockerfile, lex_indent_hash, lex_sed, lex_sfc, lex_tcl
from .comment_lexers_script import lex_batch, lex_hash_script, lex_sql, lex_vbscript
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
__all__ = [
	'lex_batch',
	'lex_c_like',
	'lex_cmake',
	'lex_dockerfile',
	'lex_fsharp',
	'lex_hash_script',
	'lex_hcl',
	'lex_indent_hash',
	'lex_lua',
	'lex_php',
	'lex_python',
	'lex_rust',
	'lex_sass',
	'lex_sed',
	'lex_sfc',
	'lex_sql',
	'lex_tcl',
	'lex_vbscript',
	'lex_zig',
]
