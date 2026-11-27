# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Tdd.CommentScanners import CommentScanners
import ast
import io
import re
import tokenize
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.comment_lexers_c`
class CLikeCommentLexer:
	__CODING_RE = re.compile(r'coding[:=]\s*[-\w.]+')
	__HTML_OPEN_RE = re.compile(r'<\?(?:php\b|=)?', re.IGNORECASE)
	__REGEX_PREV_CHARS = frozenset('=([{,;:!?&|^~+-*/%<>')
	__REGEX_PREV_WORDS = frozenset({'await', 'case', 'delete', 'do', 'else', 'in', 'instanceof', 'new', 'of', 'return', 'throw', 'typeof', 'void', 'yield'})
	__WORD_RE = re.compile(r'[A-Za-z0-9_$]+')
	# @used-by :func:`agent_tools.tdd.comment_lexers_c.lex_c_like()`
	# @used-by :meth:`Df.Harness.Tdd.CommentDiff.CommentDiff.lex_language()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.__consume_astro_frontmatter()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.lex_sfc()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	def __init__(self, source: str, cfg: dict) -> None:
		self.__source = source
		self.__cfg = cfg
	# @used-by :func:`agent_tools.tdd.comment_lexers_c.lex_c_like()`
	# @used-by :meth:`Df.Harness.Tdd.CommentDiff.CommentDiff.lex_language()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.__consume_astro_frontmatter()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.lex_sfc()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	def lex(self) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		src, cfg = (self.__source, self.__cfg)
		n, tokens, comments, ok = (len(src), [], [], True)
		ws_chars = (' \t\r\n', ' \t\r')[bool(cfg.get('nl_significant', True))]
		i = CLikeCommentLexer.consume_shebang(src, tokens, bool(cfg.get('shebang_code')))
		while i < n and ok:
			ch = src[i]
			if ch in ws_chars:
				i += 1
			elif '\n' == ch:
				tokens.append('\n')
				i += 1
			else:
				nxt = CLikeCommentLexer.__c_like_special_step(src, i, cfg, tokens, comments)
				ok = -1 != nxt
				i = CLikeCommentLexer.scan_word_or_char(src, i, tokens) if -2 == nxt else nxt
		return (CommentScanners.finalize_line_tokens(tokens), tuple(comments)) if ok else None
	# @used-by :meth:`CLikeCommentLexer.__c_like_special_step()`
	@staticmethod
	def __c_like_comment_step(src: str, i: int, cfg: dict, comments: list[str]) -> int:
		r = -2
		if cfg.get('line_slash') and src.startswith('//', i):
			r = CommentScanners.scan_line_comment(src, i)
			comments.append(src[i:r])
		elif src.startswith('/*', i):
			r = CommentScanners.scan_block_comment(src, i, '/*', '*/', nested=bool(cfg.get('block_nested')))
			if 0 <= r:
				comments.append(src[i:r])
		return r
	# @used-by :meth:`CLikeCommentLexer.__c_like_string_step()`
	@staticmethod
	def __c_like_prefix_string(src: str, i: int, cfg: dict) -> int:
		end = -2
		if cfg.get('raw_cpp') and src.startswith('R"', i):
			end = CommentScanners.scan_cpp_raw(src, i)
		elif cfg.get('verbatim_at') and src.startswith('@"', i):
			end = CommentScanners.scan_quoted(src, i + 1, '"', backslash=False, doubled=True)
		elif cfg.get('triple_quote') and src.startswith('"""', i):
			end = CommentScanners.scan_triple_quote(src, i, '"')
		elif cfg.get('triple_single') and src.startswith("'''", i):
			end = CommentScanners.scan_triple_quote(src, i, "'")
		return end
	# @used-by :meth:`CLikeCommentLexer.lex()`
	@staticmethod
	def __c_like_special_step(src: str, i: int, cfg: dict, tokens: list[str], comments: list[str]) -> int:
		c_end = CLikeCommentLexer.__c_like_comment_step(src, i, cfg, comments)
		if -2 != c_end:
			r = c_end
		elif cfg.get('css_url') and 'url(' == src[i:i + 4].lower():
			r = CLikeCommentLexer.__emit_slice(src, i, CommentScanners.scan_css_url(src, i), tokens)
		elif cfg.get('regex_slash') and '/' == src[i] and CLikeCommentLexer.can_start_regex(tokens):
			r = CLikeCommentLexer.__emit_slice(src, i, CommentScanners.scan_js_regex(src, i), tokens)
		else:
			r = CLikeCommentLexer.__c_like_string_step(src, i, cfg, tokens)
		return r
	# @used-by :meth:`CLikeCommentLexer.__c_like_special_step()`
	@staticmethod
	def __c_like_string_step(src: str, i: int, cfg: dict, tokens: list[str]) -> int:
		ch = src[i]
		end = CLikeCommentLexer.__c_like_prefix_string(src, i, cfg)
		if -2 == end:
			if '"' == ch or ("'" == ch and cfg.get('single_quote', True)):
				end = CommentScanners.scan_quoted(src, i, ch, backslash=True, allow_nl=bool(cfg.get('ml_quote')))
			elif '`' == ch and cfg.get('raw_tick'):
				end = CommentScanners.scan_quoted(src, i, '`', backslash=False)
			elif '`' == ch and cfg.get('template_tick'):
				end = CLikeCommentLexer.__scan_template_literal(src, i)
		return CLikeCommentLexer.__emit_slice(src, i, end, tokens)
	# @used-by :meth:`CLikeCommentLexer.__c_like_special_step()`
	# @used-by :meth:`CLikeCommentLexer.__c_like_string_step()`
	# @used-by :meth:`CLikeCommentLexer.__php_code_step()`
	@staticmethod
	def __emit_slice(src: str, i: int, end: int, out: list[str]) -> int:
		if 0 <= end:
			out.append(src[i:end])
		return end
	# @used-by :meth:`CLikeCommentLexer.lex_php()`
	@staticmethod
	def __lex_php_body(src: str, start: int, tokens: list[str], comments: list[str]) -> tuple[int, bool]:
		i, n, ok = (start, len(src), True)
		while i < n and ok:
			if src.startswith('?>', i):
				tokens.append('?>')
				i += 2
				break
			if src[i] in ' \t\r\n':
				i += 1
			else:
				nxt = CLikeCommentLexer.__php_code_step(src, i, tokens, comments)
				if -1 == nxt:
					ok = False
				else:
					i = CLikeCommentLexer.scan_word_or_char(src, i, tokens) if -2 == nxt else nxt
		return (i, ok)
	# @used-by :meth:`CLikeCommentLexer.__lex_php_body()`
	@staticmethod
	def __php_code_step(src: str, i: int, tokens: list[str], comments: list[str]) -> int:
		ch = src[i]
		if src.startswith('//', i) or ('#' == ch and (not src.startswith('#[', i))):
			r = CLikeCommentLexer.__emit_slice(src, i, CommentScanners.scan_line_comment(src, i, stop_tag='?>'), comments)
		elif src.startswith('/*', i):
			r = CLikeCommentLexer.__emit_slice(src, i, CommentScanners.scan_block_comment(src, i, '/*', '*/'), comments)
		elif src.startswith('<<<', i):
			r = CLikeCommentLexer.__emit_slice(src, i, CommentScanners.scan_heredoc(src, i, php=True), tokens)
		elif ch in ("'", '"', '`'):
			r = CLikeCommentLexer.__emit_slice(src, i, CommentScanners.scan_quoted(src, i, ch, backslash=True), tokens)
		else:
			r = -2
		return r
	# @used-by :meth:`CLikeCommentLexer.lex_php()`
	@staticmethod
	def __php_html_segment(src: str, pos: int, end: int, tokens: list[str], comments: list[str]) -> bool:
		i, ok = (pos, True)
		while i < end:
			c_idx = src.find('<!--', i, end)
			if -1 == c_idx:
				if src[i:end].strip():
					tokens.append(src[i:end].strip())
				break
			if src[i:c_idx].strip():
				tokens.append(src[i:c_idx].strip())
			c_end = src.find('-->', c_idx + 4, end)
			if -1 == c_end:
				ok = False
				break
			comments.append(src[c_idx:c_end + 3])
			i = c_end + 3
		return ok
	# @used-by :meth:`CLikeCommentLexer.lex_python()`
	@staticmethod
	def __py_token_text(tok: tokenize.TokenInfo) -> str:
		if tokenize.INDENT == tok.type:
			r = f'{tokenize.INDENT}:'
		elif tokenize.NEWLINE == tok.type:
			r = f'{tokenize.NEWLINE}:\n'
		else:
			r = f'{tok.type}:{tok.string}'
		return r
	# @used-by :meth:`CLikeCommentLexer.__scan_template_literal()`
	@staticmethod
	def __scan_template_expr(src: str, pos: int) -> int:
		i, n, depth, r = (pos, len(src), 1, -1)
		while i < n:
			ch = src[i]
			if ch in ('"', "'", '`'):
				i = CLikeCommentLexer.__scan_template_literal(src, i) if '`' == ch else CommentScanners.scan_quoted(src, i, ch)
				if 0 > i:
					break
			elif '{' == ch:
				depth += 1
				i += 1
			elif '}' == ch:
				depth -= 1
				i += 1
				if 0 == depth:
					r = i
					break
			else:
				i += 1
		return r
	# @used-by :meth:`CLikeCommentLexer.__c_like_string_step()`
	# @used-by :meth:`CLikeCommentLexer.__scan_template_expr()`
	@staticmethod
	def __scan_template_literal(src: str, pos: int) -> int:
		i, n, r = (pos + 1, len(src), -1)
		while i < n:
			ch = src[i]
			if '\\' == ch:
				i += 2
			elif '`' == ch:
				r = i + 1
				break
			elif src.startswith('${', i):
				i = CLikeCommentLexer.__scan_template_expr(src, i + 2)
				if 0 > i:
					break
			else:
				i += 1
		return r
	# @used-by :func:`agent_tools.tdd.comment_lexers_c.can_start_regex()`
	# @used-by :meth:`CLikeCommentLexer.__c_like_special_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__hash_here_or_regex()`
	# @used-by :meth:`Df.Harness.Xref.Js.Lexer.Lexer.__tokenize_js_atom()`
	@staticmethod
	def can_start_regex(tokens: list[str]) -> bool:
		prev = next((t for t in reversed(tokens) if '\n' != t), '')
		return (not prev) or prev in CLikeCommentLexer.__REGEX_PREV_WORDS or prev[-1] in CLikeCommentLexer.__REGEX_PREV_CHARS
	# @used-by :func:`agent_tools.tdd.comment_lexers_c.consume_shebang()`
	# @used-by :meth:`CLikeCommentLexer.lex()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.lex_hash_script()`
	@staticmethod
	def consume_shebang(source: str, tokens: list[str], enabled: bool) -> int:
		r = 0
		if enabled and source.startswith('#!'):
			nl = source.find('\n')
			r = len(source) if -1 == nl else nl
			tokens.extend((source[:r], '\n'))
		return r
	# @used-by :func:`agent_tools.tdd.comment_lexers_c.lex_php()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
	def lex_php(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		i, n, tokens, comments, ok = (0, len(source), [], [], True)
		while i < n and ok:
			m_open = CLikeCommentLexer.__HTML_OPEN_RE.search(source, i)
			html_end = n if None is m_open else m_open.start()
			ok = CLikeCommentLexer.__php_html_segment(source, i, html_end, tokens, comments)
			if (not ok) or None is m_open:
				break
			tokens.append(m_open.group(0).lower())
			i, ok = CLikeCommentLexer.__lex_php_body(source, m_open.end(), tokens, comments)
		return (CommentScanners.finalize_line_tokens(tokens), tuple(comments)) if ok else None
	# @used-by :func:`agent_tools.tdd.comment_lexers_c.lex_python()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_classifier_commands_and_lexers()`
	# @used-by :mod:`Df.Harness.Tdd.CommentDiff`
	@staticmethod
	def lex_python(source: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
		tokens: list[str] = []
		comments: list[str] = []
		try:
			ast.parse(source)
			for tok in tokenize.generate_tokens(io.StringIO(source).readline):
				if tok.type in (tokenize.NL, tokenize.ENCODING, tokenize.ENDMARKER):
					continue
				if tokenize.COMMENT == tok.type:
					is_ctrl = (1 == tok.start[0] and tok.string.startswith('#!')) or (2 >= tok.start[0] and bool(CLikeCommentLexer.__CODING_RE.search(tok.string)))
					(tokens if is_ctrl else comments).append(tok.string)
				else:
					tokens.append(CLikeCommentLexer.__py_token_text(tok))
			r: tuple[tuple[str, ...], tuple[str, ...]] | None = (tuple(tokens), tuple(comments))
		except (SyntaxError, tokenize.TokenError, IndentationError):
			r = None
		return r
	# @used-by :func:`agent_tools.tdd.comment_lexers_c.scan_word_or_char()`
	# @used-by :meth:`CLikeCommentLexer.__lex_php_body()`
	# @used-by :meth:`CLikeCommentLexer.lex()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__lex_indent_loop()`
	# @used-by :meth:`Df.Harness.Tdd.ExtCommentLexer.ExtCommentLexer.__lex_loop()`
	# @used-by :meth:`Df.Harness.Tdd.MarkupCommentLexer.MarkupCommentLexer.__tcl_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.__vbs_step()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.lex_hash_script()`
	# @used-by :meth:`Df.Harness.Tdd.ScriptCommentLexer.ScriptCommentLexer.lex_sql()`
	@staticmethod
	def scan_word_or_char(src: str, i: int, tokens: list[str]) -> int:
		m = CLikeCommentLexer.__WORD_RE.match(src, i)
		if None is not m:
			tokens.append(m.group(0))
			r = m.end()
		else:
			tokens.append(src[i])
			r = i + 1
		return r
