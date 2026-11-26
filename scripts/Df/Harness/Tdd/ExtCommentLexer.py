# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Tdd.CLikeCommentLexer import CLikeCommentLexer
from Df.Harness.Tdd.CommentScanners import CommentScanners
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.comment_lexers_ext`
class ExtCommentLexer:
	# @used-by :meth:`ExtCommentLexer.lex_cmake()`
	@staticmethod
	def __cmake_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
		ch = src[i]
		if '#' == ch:
			blk = ExtCommentLexer.__scan_long_bracket(src, i + 1)
			r = ExtCommentLexer.__emit(src, i, blk if 0 <= blk else CommentScanners.scan_line_comment(src, i), comments)
		elif '"' == ch:
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_quoted(src, i, '"', backslash=True), tokens)
		elif '[' == ch:
			blk = ExtCommentLexer.__scan_long_bracket(src, i)
			r = ExtCommentLexer.__emit(src, i, blk, tokens) if 0 <= blk else -2
		else:
			r = -2
		return r
	# @used-by :meth:`ExtCommentLexer.__lex_indent_loop()`
	@staticmethod
	def __consume_line_indent(src: str, i: int, tokens: list[str]) -> int:
		j, n = (i, len(src))
		while j < n and src[j] in ' \t':
			j += 1
		if j < n and src[j] not in '\r\n':
			tokens.append(f'INDENT:{src[i:j]}')
		return j
	# @used-by :meth:`ExtCommentLexer.__cmake_step()`
	# @used-by :meth:`ExtCommentLexer.__fsharp_step()`
	# @used-by :meth:`ExtCommentLexer.__hcl_step()`
	# @used-by :meth:`ExtCommentLexer.__lua_step()`
	# @used-by :meth:`ExtCommentLexer.__rust_step()`
	# @used-by :meth:`ExtCommentLexer.__sass_step()`
	# @used-by :meth:`ExtCommentLexer.__zig_step()`
	@staticmethod
	def __emit(src: str, i: int, end: int, out: list[str]) -> int:
		if 0 <= end:
			out.append(src[i:end])
		return end
	# @used-by :meth:`ExtCommentLexer.lex_fsharp()`
	@staticmethod
	def __fsharp_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
		if src.startswith('//', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_line_comment(src, i), comments)
		elif src.startswith('(*', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_block_comment(src, i, '(*', '*)', nested=True), comments)
		elif src.startswith('"""', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_triple_quote(src, i, '"'), tokens)
		elif src.startswith('@"', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_quoted(src, i + 1, '"', backslash=False, doubled=True), tokens)
		elif '"' == src[i]:
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_quoted(src, i, '"', backslash=True), tokens)
		else:
			r = -2
		return r
	# @used-by :meth:`ExtCommentLexer.lex_hcl()`
	@staticmethod
	def __hcl_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
		if '#' == src[i] or src.startswith('//', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_line_comment(src, i), comments)
		elif src.startswith('/*', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_block_comment(src, i, '/*', '*/'), comments)
		elif src.startswith('<<', i):
			cand = CommentScanners.scan_heredoc(src, i, php=False)
			r = ExtCommentLexer.__emit(src, i, cand, tokens) if 0 <= cand else -2
		elif '"' == src[i]:
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_quoted(src, i, '"', backslash=True), tokens)
		else:
			r = -2
		return r
	# @used-by :meth:`ExtCommentLexer.lex_fsharp()`
	# @used-by :meth:`ExtCommentLexer.lex_sass()`
	@staticmethod
	def __lex_indent_loop(source: str, step_fn) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		i, n, tokens, comments, ok, at_bol = (0, len(source), [], [], True, True)
		while i < n and ok:
			if at_bol:
				i, at_bol = (ExtCommentLexer.__consume_line_indent(source, i, tokens), False)
			elif source[i] in ' \t\r':
				i += 1
			elif '\n' == source[i]:
				tokens.append('\n')
				i, at_bol = (i + 1, True)
			else:
				nxt = step_fn(source, i, tokens, comments)
				ok = -1 != nxt
				i = CLikeCommentLexer.scan_word_or_char(source, i, tokens) if -2 == nxt else nxt
		return (CommentScanners.finalize_line_tokens(tokens), tuple(comments)) if ok else None
	# @used-by :meth:`ExtCommentLexer.lex_cmake()`
	# @used-by :meth:`ExtCommentLexer.lex_hcl()`
	# @used-by :meth:`ExtCommentLexer.lex_lua()`
	# @used-by :meth:`ExtCommentLexer.lex_rust()`
	# @used-by :meth:`ExtCommentLexer.lex_zig()`
	@staticmethod
	def __lex_loop(source: str, step_fn) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
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
				i = CLikeCommentLexer.scan_word_or_char(source, i, tokens) if -2 == nxt else nxt
		return (CommentScanners.finalize_line_tokens(tokens), tuple(comments)) if ok else None
	# @used-by :meth:`ExtCommentLexer.lex_lua()`
	@staticmethod
	def __lua_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
		ch = src[i]
		if src.startswith('--', i):
			blk = ExtCommentLexer.__scan_long_bracket(src, i + 2)
			r = ExtCommentLexer.__emit(src, i, blk if 0 <= blk else CommentScanners.scan_line_comment(src, i), comments)
		elif ch in ('"', "'"):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_quoted(src, i, ch, backslash=True, allow_nl=False), tokens)
		elif '[' == ch:
			blk = ExtCommentLexer.__scan_long_bracket(src, i)
			r = ExtCommentLexer.__emit(src, i, blk, tokens) if 0 <= blk else -2
		else:
			r = -2
		return r
	# @used-by :meth:`ExtCommentLexer.lex_rust()`
	@staticmethod
	def __rust_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
		ch = src[i]
		if src.startswith('//', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_line_comment(src, i), comments)
		elif src.startswith('/*', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_block_comment(src, i, '/*', '*/', nested=True), comments)
		elif ch in ('b', 'c', 'r'):
			raw_end = ExtCommentLexer.__scan_rust_raw_str(src, i)
			r = ExtCommentLexer.__emit(src, i, raw_end, tokens) if -2 != raw_end else -2
		elif '"' == ch:
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_quoted(src, i, '"', backslash=True), tokens)
		elif "'" == ch:
			r = ExtCommentLexer.__emit(src, i, ExtCommentLexer.__scan_rust_char_or_lifetime(src, i), tokens)
		else:
			r = -2
		return r
	# @used-by :meth:`ExtCommentLexer.lex_sass()`
	@staticmethod
	def __sass_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
		ch = src[i]
		if src.startswith('//', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_line_comment(src, i), comments)
		elif src.startswith('/*', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_block_comment(src, i, '/*', '*/'), comments)
		elif 'url(' == src[i:i + 4].lower():
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_css_url(src, i), tokens)
		elif ch in ('"', "'"):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_quoted(src, i, ch, backslash=True), tokens)
		else:
			r = -2
		return r
	# @used-by :meth:`ExtCommentLexer.__cmake_step()`
	# @used-by :meth:`ExtCommentLexer.__lua_step()`
	@staticmethod
	def __scan_long_bracket(src: str, pos: int) -> int:
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
	# @used-by :meth:`ExtCommentLexer.__rust_step()`
	@staticmethod
	def __scan_rust_char_or_lifetime(src: str, pos: int) -> int:
		n = len(src)
		if pos + 2 < n and '\\' == src[pos + 1]:
			end = CommentScanners.scan_quoted(src, pos, "'", backslash=True, allow_nl=False)
			r = end if 0 <= end else pos + 1
		elif pos + 2 < n and "'" == src[pos + 2] and src[pos + 1] not in "'\r\n":
			r = pos + 3
		else:
			r = pos + 1
		return r
	# @used-by :meth:`ExtCommentLexer.__rust_step()`
	@staticmethod
	def __scan_rust_raw_str(src: str, pos: int) -> int:
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
	# @used-by :meth:`ExtCommentLexer.lex_zig()`
	@staticmethod
	def __zig_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
		ch = src[i]
		if src.startswith('//', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_line_comment(src, i), comments)
		elif src.startswith('\\\\', i):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_line_comment(src, i), tokens)
		elif ch in ('"', "'"):
			r = ExtCommentLexer.__emit(src, i, CommentScanners.scan_quoted(src, i, ch, backslash=True, allow_nl=False), tokens)
		else:
			r = -2
		return r
	# @used-by :func:`agent_tools.tdd.comment_lexers_ext.lex_cmake()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
	def lex_cmake(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		return ExtCommentLexer.__lex_loop(source, ExtCommentLexer.__cmake_step)
	# @used-by :func:`agent_tools.tdd.comment_lexers_ext.lex_fsharp()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
	def lex_fsharp(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		return ExtCommentLexer.__lex_indent_loop(source, ExtCommentLexer.__fsharp_step)
	# @used-by :func:`agent_tools.tdd.comment_lexers_ext.lex_hcl()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
	def lex_hcl(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		return ExtCommentLexer.__lex_loop(source, ExtCommentLexer.__hcl_step)
	# @used-by :func:`agent_tools.tdd.comment_lexers_ext.lex_lua()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
	def lex_lua(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		return ExtCommentLexer.__lex_loop(source, ExtCommentLexer.__lua_step)
	# @used-by :func:`agent_tools.tdd.comment_lexers_ext.lex_rust()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
	def lex_rust(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		return ExtCommentLexer.__lex_loop(source, ExtCommentLexer.__rust_step)
	# @used-by :func:`agent_tools.tdd.comment_lexers_ext.lex_sass()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
	def lex_sass(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		return ExtCommentLexer.__lex_indent_loop(source, ExtCommentLexer.__sass_step)
	# @used-by :func:`agent_tools.tdd.comment_lexers_ext.lex_zig()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
	def lex_zig(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		return ExtCommentLexer.__lex_loop(source, ExtCommentLexer.__zig_step)
