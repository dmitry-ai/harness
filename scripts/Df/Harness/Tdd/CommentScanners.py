# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.comment_scanners`
class CommentScanners:
	__CPP_RAW_RE = re.compile(r'R"([^\s()\\]{0,16})\(')
	__HEREDOC_START_RE = re.compile(r'<<<[ \t]*(?:"([A-Za-z_]\w*)"|\'([A-Za-z_]\w*)\'|([A-Za-z_]\w*))')
	__SH_HEREDOC_RE = re.compile(r'<<(-?)[ \t]*(?:"([A-Za-z_]\w*)"|\'([A-Za-z_]\w*)\'|([A-Za-z_]\w*))')
	# @used-by :meth:`CommentScanners.scan_heredoc()`
	@staticmethod
	def __find_heredoc_end(src: str, start: int, tag: str, *, php: bool) -> int:
		i, n, r = (start, len(src), -1)
		while i < n:
			nl = src.find('\n', i)
			line_end = n if -1 == nl else nl
			stripped = src[i:line_end].strip()
			matched = (stripped == tag or stripped.startswith(f'{tag};')) if php else (stripped == tag)
			if matched:
				r = line_end
				break
			i = n if -1 == nl else nl + 1
		return r
	# @used-by :meth:`CommentScanners.scan_js_regex()`
	@staticmethod
	def __scan_regex_flags(src: str, pos: int) -> int:
		n = len(src)
		i = pos
		while i < n and src[i].isalpha():
			i += 1
		return i
	# @used-by :meth:`CommentScanners.scan_css_url()`
	@staticmethod
	def __scan_until_paren(src: str, pos: int) -> int:
		n = len(src)
		i, r = (pos, -1)
		while i < n:
			if '\\' == src[i]:
				i += 2
			elif ')' == src[i]:
				r = i + 1
				break
			else:
				i += 1
		return r
	# @used-by :func:`agent_tools.tdd.comment_scanners.finalize_line_tokens()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.lex()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.lex_php()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__lex_indent_loop()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__lex_loop()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.lex_dockerfile()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.lex_indent_hash()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.lex_sed()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.lex_sfc()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.lex_tcl()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.lex_batch()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.lex_hash_script()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.lex_vbscript()`
	@staticmethod
	def finalize_line_tokens(raw_tokens: list[str]) -> tuple[str, ...]:
		out: list[str] = []
		for tok in raw_tokens:
			if '\n' == tok:
				if out and '\n' != out[-1]:
					out.append('\n')
			else:
				out.append(tok)
		if out and '\n' != out[-1]:
			out.append('\n')
		return tuple(out)
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_block_comment()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__c_like_comment_step()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__php_code_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__fsharp_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__hcl_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__rust_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__sass_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__hash_block_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__sql_step()`
	# @used-by :meth:`Df.Harness.Xref.Java.Lexer.Lexer.__tokenize_java_step()`
	# @used-by :meth:`Df.Harness.Xref.Js.Lexer.Lexer.__tokenize_js_step()`
	@staticmethod
	def scan_block_comment(src: str, pos: int, open_tok: str, close_tok: str, *, nested: bool=False) -> int:
		n = len(src)
		olen, clen = (len(open_tok), len(close_tok))
		i, depth, r = (pos + olen, 1, -1)
		while i < n:
			if nested and src.startswith(open_tok, i):
				depth += 1
				i += olen
			elif src.startswith(close_tok, i):
				depth -= 1
				i += clen
				if 0 == depth:
					r = i
					break
			else:
				i += 1
		return r
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_cpp_raw()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__c_like_prefix_string()`
	@staticmethod
	def scan_cpp_raw(src: str, pos: int) -> int:
		m = CommentScanners.__CPP_RAW_RE.match(src, pos)
		if None is m:
			r = -1
		else:
			end_marker = f'){m.group(1)}"'
			idx = src.find(end_marker, m.end())
			r = -1 if -1 == idx else idx + len(end_marker)
		return r
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_css_url()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__c_like_special_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__sass_step()`
	@staticmethod
	def scan_css_url(src: str, pos: int) -> int:
		n = len(src)
		i = pos + 4
		while i < n and src[i] in ' \t\r\n':
			i += 1
		if i < n and src[i] in ('"', "'"):
			end_q = CommentScanners.scan_quoted(src, i, src[i], backslash=True, allow_nl=False)
			r = -1 if 0 > end_q else CommentScanners.__scan_until_paren(src, end_q)
		else:
			r = CommentScanners.__scan_until_paren(src, i)
		return r
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_heredoc()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__php_code_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__hcl_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__hash_here_or_regex()`
	@staticmethod
	def scan_heredoc(src: str, pos: int, *, php: bool=False) -> int:
		pat = CommentScanners.__HEREDOC_START_RE if php else CommentScanners.__SH_HEREDOC_RE
		m = pat.match(src, pos)
		if None is m:
			r = -1
		else:
			tag = next((g for g in m.groups()[-3:] if g), '')
			nl = src.find('\n', m.end())
			r = -1 if -1 == nl else CommentScanners.__find_heredoc_end(src, nl + 1, tag, php=php)
		return r
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_js_regex()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__c_like_special_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__hash_here_or_regex()`
	# @used-by :meth:`Df.Harness.Xref.Js.Lexer.Lexer.__tokenize_js_atom()`
	@staticmethod
	def scan_js_regex(src: str, pos: int) -> int:
		i, n, in_cls, r = (pos + 1, len(src), False, -1)
		while i < n and src[i] not in '\r\n':
			ch = src[i]
			if '\\' == ch:
				i += 2
			elif '/' == ch and (not in_cls):
				r = CommentScanners.__scan_regex_flags(src, i + 1)
				break
			else:
				in_cls = True if '[' == ch else (False if ']' == ch and in_cls else in_cls)
				i += 1
		return r
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_line_block()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__hash_block_step()`
	@staticmethod
	def scan_line_block(src: str, pos: int, end_prefix: str) -> int:
		n = len(src)
		i, r = (pos, -1)
		while i < n:
			nl = src.find('\n', i)
			line_end = n if -1 == nl else nl + 1
			if src[i:line_end].startswith(end_prefix) and (len(end_prefix) == len(src[i:line_end].rstrip('\r\n')) or src[i + len(end_prefix)] in ' \t\r\n'):
				r = line_end
				break
			i = line_end
		return r
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_line_comment()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__c_like_comment_step()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__php_code_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__cmake_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__fsharp_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__hcl_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__lua_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__rust_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__sass_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__zig_step()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.__tcl_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__hash_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__sql_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__vbs_step()`
	# @used-by :meth:`Df.Harness.Xref.Java.Lexer.Lexer.__tokenize_java_step()`
	# @used-by :meth:`Df.Harness.Xref.Js.Lexer.Lexer.__tokenize_js_step()`
	@staticmethod
	def scan_line_comment(src: str, pos: int, *, stop_tag: str='') -> int:
		n = len(src)
		nl = src.find('\n', pos)
		end = n if -1 == nl else nl
		if stop_tag:
			tag_idx = src.find(stop_tag, pos, end)
			if -1 != tag_idx:
				end = tag_idx
		return end
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_ps_herestring()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__hash_here_or_regex()`
	@staticmethod
	def scan_ps_herestring(src: str, pos: int, quote: str) -> int:
		nl = src.find('\n', pos + 2)
		if -1 == nl:
			r = -1
		else:
			end_marker = f'\n{quote}@'
			idx = src.find(end_marker, nl)
			r = -1 if -1 == idx else idx + len(end_marker)
		return r
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_quoted()`
	# @used-by :meth:`CommentScanners.scan_css_url()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__c_like_prefix_string()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__c_like_string_step()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__php_code_step()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__scan_template_expr()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__cmake_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__fsharp_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__hcl_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__lua_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__rust_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__sass_step()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__scan_rust_char_or_lifetime()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__zig_step()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.__tcl_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__hash_quote_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__sql_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__vbs_step()`
	# @used-by :meth:`Df.Harness.Xref.Java.Lexer.Lexer.__tokenize_java_atom()`
	# @used-by :meth:`Df.Harness.Xref.Js.Lexer.Lexer.__tokenize_js_atom()`
	@staticmethod
	def scan_quoted(src: str, pos: int, quote: str, *, backslash: bool=True, doubled: bool=False, allow_nl: bool=True, backtick: bool=False) -> int:
		n = len(src)
		i, r = (pos + 1, -1)
		while i < n:
			ch = src[i]
			if (not allow_nl) and ch in '\r\n':
				break
			if backslash and '\\' == ch:
				i += 2
			elif backtick and '`' == ch:
				i += 2
			elif doubled and ch == quote and i + 1 < n and src[i + 1] == quote:
				i += 2
			elif ch == quote:
				r = i + 1
				break
			else:
				i += 1
		return r
	# @used-by :func:`agent_tools.tdd.comment_scanners.scan_triple_quote()`
	# @used-by :meth:`Df.Harness.Tdd.CLikeCommentLexer.CLikeCommentLexer.__c_like_prefix_string()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__fsharp_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__hash_quote_step()`
	# @used-by :meth:`Df.Harness.Xref.Java.Lexer.Lexer.__tokenize_java_atom()`
	@staticmethod
	def scan_triple_quote(src: str, pos: int, quote: str) -> int:
		marker = quote * 3
		i, n, r = (pos + 3, len(src), -1)
		while i < n:
			if '\\' == src[i]:
				i += 2
			elif src.startswith(marker, i):
				r = i + 3
				break
			else:
				i += 1
		return r
