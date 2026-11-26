# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement diff executability classifier and automatic test skip":
# https://github.com/dmitry-ai/harness/issues/358
from __future__ import annotations
from .comment_lexers_c import scan_word_or_char
from .comment_scanners import finalize_line_tokens, scan_block_comment, scan_css_url, scan_heredoc, scan_line_comment, scan_quoted, scan_triple_quote
# @used-by :func:`_lex_indent_loop()`
def _consume_line_indent(src: str, i: int, tokens: list[str]) -> int:
	j, n = (i, len(src))
	while j < n and src[j] in ' \t':
		j += 1
	if j < n and src[j] not in '\r\n':
		tokens.append(f'INDENT:{src[i:j]}')
	return j
# @used-by :func:`_cmake_step()`
# @used-by :func:`_fsharp_step()`
# @used-by :func:`_hcl_step()`
# @used-by :func:`_lua_step()`
# @used-by :func:`_rust_step()`
# @used-by :func:`_sass_step()`
# @used-by :func:`_zig_step()`
def _emit(src: str, i: int, end: int, out: list[str]) -> int:
	if 0 <= end:
		out.append(src[i:end])
	return end
# @used-by :func:`_cmake_step()`
# @used-by :func:`_lua_step()`
def _scan_long_bracket(src: str, pos: int) -> int:
	n, r = (len(src), -1)
	if pos < n and '[' == src[pos]:
		eq = pos + 1
		while eq < n and '=' == src[eq]:
			eq += 1
		if eq < n and '[' == src[eq]:
			closer = ']' + ('=' * (eq - pos - 1)) + ']'
			idx = src.find(closer, eq + 1)
			r = -1 if -1 == idx else idx + len(closer)
	return r
# @used-by :func:`_rust_step()`
def _scan_rust_char_or_lifetime(src: str, pos: int) -> int:
	n = len(src)
	if pos + 2 < n and '\\' == src[pos + 1]:
		end = scan_quoted(src, pos, "'", backslash=True, allow_nl=False)
		r = end if 0 <= end else pos + 1
	elif pos + 2 < n and "'" == src[pos + 2] and src[pos + 1] not in "'\r\n":
		r = pos + 3
	else:
		r = pos + 1
	return r
# @used-by :func:`_rust_step()`
def _scan_rust_raw_str(src: str, pos: int) -> int:
	n, i, r = (len(src), pos, -2)
	if src.startswith(('br', 'cr'), i):
		i += 2
	elif 'r' == src[i]:
		i += 1
	else:
		i = -1
	if 0 <= i:
		hashes = 0
		while i < n and '#' == src[i]:
			hashes += 1
			i += 1
		if i < n and '"' == src[i]:
			closer = '"' + ('#' * hashes)
			idx = src.find(closer, i + 1)
			r = -1 if -1 == idx else idx + len(closer)
	return r
# @used-by :func:`lex_cmake()`
def _cmake_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
	ch = src[i]
	if '#' == ch:
		blk = _scan_long_bracket(src, i + 1)
		r = _emit(src, i, blk if 0 <= blk else scan_line_comment(src, i), comments)
	elif '"' == ch:
		r = _emit(src, i, scan_quoted(src, i, '"', backslash=True), tokens)
	elif '[' == ch:
		blk = _scan_long_bracket(src, i)
		r = _emit(src, i, blk, tokens) if 0 <= blk else -2
	else:
		r = -2
	return r
# @used-by :func:`lex_fsharp()`
def _fsharp_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
	if src.startswith('//', i):
		r = _emit(src, i, scan_line_comment(src, i), comments)
	elif src.startswith('(*', i):
		r = _emit(src, i, scan_block_comment(src, i, '(*', '*)', nested=True), comments)
	elif src.startswith('"""', i):
		r = _emit(src, i, scan_triple_quote(src, i, '"'), tokens)
	elif src.startswith('@"', i):
		r = _emit(src, i, scan_quoted(src, i + 1, '"', backslash=False, doubled=True), tokens)
	elif '"' == src[i]:
		r = _emit(src, i, scan_quoted(src, i, '"', backslash=True), tokens)
	else:
		r = -2
	return r
# @used-by :func:`lex_hcl()`
def _hcl_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
	if '#' == src[i] or src.startswith('//', i):
		r = _emit(src, i, scan_line_comment(src, i), comments)
	elif src.startswith('/*', i):
		r = _emit(src, i, scan_block_comment(src, i, '/*', '*/'), comments)
	elif src.startswith('<<', i):
		cand = scan_heredoc(src, i, php=False)
		r = _emit(src, i, cand, tokens) if 0 <= cand else -2
	elif '"' == src[i]:
		r = _emit(src, i, scan_quoted(src, i, '"', backslash=True), tokens)
	else:
		r = -2
	return r
# @used-by :func:`lex_lua()`
def _lua_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
	ch = src[i]
	if src.startswith('--', i):
		blk = _scan_long_bracket(src, i + 2)
		r = _emit(src, i, blk if 0 <= blk else scan_line_comment(src, i), comments)
	elif ch in ('"', "'"):
		r = _emit(src, i, scan_quoted(src, i, ch, backslash=True, allow_nl=False), tokens)
	elif '[' == ch:
		blk = _scan_long_bracket(src, i)
		r = _emit(src, i, blk, tokens) if 0 <= blk else -2
	else:
		r = -2
	return r
# @used-by :func:`lex_rust()`
def _rust_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
	ch = src[i]
	if src.startswith('//', i):
		r = _emit(src, i, scan_line_comment(src, i), comments)
	elif src.startswith('/*', i):
		r = _emit(src, i, scan_block_comment(src, i, '/*', '*/', nested=True), comments)
	elif ch in ('b', 'c', 'r'):
		raw_end = _scan_rust_raw_str(src, i)
		r = _emit(src, i, raw_end, tokens) if -2 != raw_end else -2
	elif '"' == ch:
		r = _emit(src, i, scan_quoted(src, i, '"', backslash=True), tokens)
	elif "'" == ch:
		r = _emit(src, i, _scan_rust_char_or_lifetime(src, i), tokens)
	else:
		r = -2
	return r
# @used-by :func:`lex_sass()`
def _sass_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
	ch = src[i]
	if src.startswith('//', i):
		r = _emit(src, i, scan_line_comment(src, i), comments)
	elif src.startswith('/*', i):
		r = _emit(src, i, scan_block_comment(src, i, '/*', '*/'), comments)
	elif 'url(' == src[i:i + 4].lower():
		r = _emit(src, i, scan_css_url(src, i), tokens)
	elif ch in ('"', "'"):
		r = _emit(src, i, scan_quoted(src, i, ch, backslash=True), tokens)
	else:
		r = -2
	return r
# @used-by :func:`lex_zig()`
def _zig_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
	ch = src[i]
	if src.startswith('//', i):
		r = _emit(src, i, scan_line_comment(src, i), comments)
	elif src.startswith('\\\\', i):
		r = _emit(src, i, scan_line_comment(src, i), tokens)
	elif ch in ('"', "'"):
		r = _emit(src, i, scan_quoted(src, i, ch, backslash=True, allow_nl=False), tokens)
	else:
		r = -2
	return r
# @used-by :func:`lex_cmake()`
# @used-by :func:`lex_hcl()`
# @used-by :func:`lex_lua()`
# @used-by :func:`lex_rust()`
# @used-by :func:`lex_zig()`
def _lex_loop(source: str, step_fn) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	i, n, tokens, comments, ok = (0, len(source), [], [], True)
	while i < n and ok:
		ch = source[i]
		if ch in ' \t\r':
			i += 1
		elif '\n' == ch:
			tokens.append('\n')
			i += 1
		else:
			nxt = step_fn(source, i, tokens, comments)
			ok = -1 != nxt
			i = scan_word_or_char(source, i, tokens) if -2 == nxt else nxt
	return (finalize_line_tokens(tokens), tuple(comments)) if ok else None
# @used-by :func:`lex_fsharp()`
# @used-by :func:`lex_sass()`
def _lex_indent_loop(source: str, step_fn) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	i, n, tokens, comments, ok, at_bol = (0, len(source), [], [], True, True)
	while i < n and ok:
		if at_bol:
			i, at_bol = (_consume_line_indent(source, i, tokens), False)
		elif source[i] in ' \t\r':
			i += 1
		elif '\n' == source[i]:
			tokens.append('\n')
			i, at_bol = (i + 1, True)
		else:
			nxt = step_fn(source, i, tokens, comments)
			ok = -1 != nxt
			i = scan_word_or_char(source, i, tokens) if -2 == nxt else nxt
	return (finalize_line_tokens(tokens), tuple(comments)) if ok else None
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_cmake(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return _lex_loop(source, _cmake_step)
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_fsharp(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return _lex_indent_loop(source, _fsharp_step)
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_hcl(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return _lex_loop(source, _hcl_step)
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_lua(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return _lex_loop(source, _lua_step)
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_rust(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return _lex_loop(source, _rust_step)
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_sass(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return _lex_indent_loop(source, _sass_step)
# @used-by :mod:`agent_tools.tdd.comment_diff`
# @used-by :mod:`agent_tools.tdd.comment_lexers`
def lex_zig(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
	return _lex_loop(source, _zig_step)
