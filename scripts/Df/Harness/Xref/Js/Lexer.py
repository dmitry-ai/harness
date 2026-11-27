# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.text.source import df_match_delim
from Df.Harness.Tdd.CLikeCommentLexer import CLikeCommentLexer
from Df.Harness.Tdd.CommentScanners import CommentScanners
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Lexer:
	__OPEN_FOR_CLOSE = {')': '(', '>': '<', ']': '[', '}': '{'}
	__WORD_RE = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
	# @used-by :func:`agent_tools.xref.js_lex.tokenize_js()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.index_file()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_js_xref_classes_tokenize_imports_graph_and_sync()`
	def __init__(self, source: str) -> None:
		self.__source = source
	# @used-by :func:`agent_tools.xref.js_lex.tokenize_js()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.index_file()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_js_xref_classes_tokenize_imports_graph_and_sync()`
	def tokenize(self) -> list[tuple[str, str, int]]:
		toks: list[tuple[str, str, int]] = []
		prev_words: list[str] = []
		i, n, line = (0, len(self.__source), 1)
		if self.__source.startswith('#!'):
			nl = self.__source.find('\n')
			i = n if -1 == nl else nl + 1
			line = 2
		while i < n:
			i, line = Lexer.__tokenize_js_step(self.__source, i, line, toks, prev_words)
		return toks
	# @used-by :meth:`Lexer.__scan_template_expr_tokens()`
	# @used-by :meth:`Lexer.__scan_template_tokens()`
	# @used-by :meth:`Lexer.__tokenize_js_atom()`
	# @used-by :meth:`Lexer.__tokenize_js_word_or_punct()`
	@staticmethod
	def __push_tok(kind: str, text: str, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> None:
		toks.append((kind, text, line))
		prev_words.append(text)
	# @used-by :meth:`Lexer.__scan_template_tokens()`
	@staticmethod
	def __scan_template_expr_tokens(src: str, start: int, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> tuple[int, int]:
		i, n, depth = (start, len(src), 1)
		while i < n and 0 < depth:
			ch = src[i]
			if '}' == ch and 1 == depth:
				i += 1
				break
			if ch in ('{', '}'):
				depth += 1 if '{' == ch else -1
				Lexer.__push_tok('punct', ch, line, toks, prev_words)
				i += 1
			else:
				i, line = Lexer.__tokenize_js_step(src, i, line, toks, prev_words)
		return (i, line)
	# @used-by :meth:`Lexer.__tokenize_js_step()`
	@staticmethod
	def __scan_template_tokens(src: str, start: int, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> tuple[int, int]:
		i, n = (start + 1, len(src))
		while i < n:
			ch = src[i]
			if '\\' == ch:
				i += 2
			elif '\n' == ch:
				line += 1
				i += 1
			elif '`' == ch:
				Lexer.__push_tok('str', '`...`', line, toks, prev_words)
				i += 1
				break
			elif src.startswith('${', i):
				i, line = Lexer.__scan_template_expr_tokens(src, i + 2, line, toks, prev_words)
			else:
				i += 1
		return (i, line)
	# @used-by :meth:`Lexer.__tokenize_js_step()`
	@staticmethod
	def __tokenize_js_atom(src: str, i: int, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> tuple[int, int]:
		ch = src[i]
		if ch in ("'", '"'):
			end = max(i + 1, CommentScanners.scan_quoted(src, i, ch, backslash=True, allow_nl=False))
			Lexer.__push_tok('str', src[i:end], line, toks, prev_words)
			r = (end, line)
		elif '/' == ch and CLikeCommentLexer.can_start_regex(prev_words):
			end = max(i + 1, CommentScanners.scan_js_regex(src, i))
			Lexer.__push_tok('regex', src[i:end], line, toks, prev_words)
			r = (end, line)
		elif src.startswith('=>', i):
			Lexer.__push_tok('punct', '=>', line, toks, prev_words)
			r = (i + 2, line)
		else:
			r = Lexer.__tokenize_js_word_or_punct(src, i, line, toks, prev_words)
		return r
	# @used-by :meth:`Lexer.__scan_template_expr_tokens()`
	# @used-by :meth:`Lexer.tokenize()`
	@staticmethod
	def __tokenize_js_step(src: str, i: int, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> tuple[int, int]:
		ch = src[i]
		if ch in ' \t\r':
			r = (i + 1, line)
		elif '\n' == ch:
			r = (i + 1, line + 1)
		elif src.startswith('//', i):
			r = (CommentScanners.scan_line_comment(src, i), line)
		elif src.startswith('/*', i):
			end = CommentScanners.scan_block_comment(src, i, '/*', '*/')
			end = len(src) if 0 > end else end
			r = (end, line + src[i:end].count('\n'))
		elif '`' == ch:
			r = Lexer.__scan_template_tokens(src, i, line, toks, prev_words)
		else:
			r = Lexer.__tokenize_js_atom(src, i, line, toks, prev_words)
		return r
	# @used-by :meth:`Lexer.__tokenize_js_atom()`
	@staticmethod
	def __tokenize_js_word_or_punct(src: str, i: int, line: int, toks: list[tuple[str, str, int]], prev_words: list[str]) -> tuple[int, int]:
		m = Lexer.__WORD_RE.match(src, i)
		if None is not m:
			Lexer.__push_tok('word', m.group(0), line, toks, prev_words)
			r = (m.end(), line)
		else:
			Lexer.__push_tok('punct', src[i], line, toks, prev_words)
			r = (i + 1, line)
		return r
	# @used-by :meth:`Lexer.arrow_body_end()`
	# @used-by :meth:`Lexer.skip_ts_type_until()`
	@staticmethod
	def __update_depths(tok: str, depths: dict[str, int]) -> bool:
		r = False
		if tok in depths:
			depths[tok] += 1
		elif tok in Lexer.__OPEN_FOR_CLOSE:
			op = Lexer.__OPEN_FOR_CLOSE[tok]
			if op in depths:
				if 0 < depths[op]:
					depths[op] -= 1
				else:
					r = True
		return r
	# @used-by :func:`agent_tools.xref.js_lex.arrow_body_end()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__finish_class_member()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_top_global_fn()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_var_fn_rhs()`
	@staticmethod
	def arrow_body_end(toks: list[tuple[str, str, int]], arrow_idx: int) -> int:
		n = len(toks)
		if arrow_idx + 1 < n and '{' == toks[arrow_idx + 1][1]:
			r = Lexer.match_delim(toks, arrow_idx + 1, '{', '}')
		else:
			depths = {'(': 0, '[': 0, '{': 0}
			i = arrow_idx + 1
			while i < n:
				t = toks[i][1]
				if (';' == t and 0 == sum(depths.values())) or (Lexer.__update_depths(t, depths) and '}' == t):
					break
				i += 1
			r = i
		return r
	# @used-by :func:`agent_tools.xref.js_lex.find_arrow_after_eq()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__finish_class_member()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_top_global_fn()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_var_fn_rhs()`
	@staticmethod
	def find_arrow_after_eq(toks: list[tuple[str, str, int]], eq_idx: int) -> int:
		n = len(toks)
		i = eq_idx + 2 if eq_idx + 1 < n and 'async' == toks[eq_idx + 1][1] else eq_idx + 1
		r = -1
		if i < n and 'word' == toks[i][0] and i + 1 < n and '=>' == toks[i + 1][1]:
			r = i + 1
		elif i < n and '(' == toks[i][1]:
			j = Lexer.match_delim(toks, i, '(', ')') + 1
			if j < n and ':' == toks[j][1]:
				j = Lexer.skip_ts_type_until(toks, j + 1, {'=>'})
			if j < n and '=>' == toks[j][1]:
				r = j
		return r
	# @used-by :func:`agent_tools.xref.js_lex.match_delim()`
	# @used-by :meth:`Df.Harness.Xref.Js.Imports.Imports.parse_destruct_require()`
	# @used-by :meth:`Df.Harness.Xref.Js.Imports.Imports.parse_esm_export_list()`
	# @used-by :meth:`Df.Harness.Xref.Js.Imports.Imports.parse_module_exports_rhs()`
	# @used-by :meth:`Df.Harness.Xref.Js.Imports.Imports.record_esm_specifiers()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__finish_class_member()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_class_body()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_fn_expr_body()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_top_class()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_top_fallback()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_top_func()`
	# @used-by :meth:`Lexer.arrow_body_end()`
	# @used-by :meth:`Lexer.find_arrow_after_eq()`
	@staticmethod
	def match_delim(toks: list[tuple[str, str, int]], start: int, open_ch: str, close_ch: str) -> int:
		return df_match_delim(toks, start, open_ch, close_ch)
	# @used-by :func:`agent_tools.xref.js_lex.skip_ts_type_until()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__finish_class_member()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_fn_expr_body()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_named_var_decl()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_top_func()`
	# @used-by :meth:`Lexer.find_arrow_after_eq()`
	@staticmethod
	def skip_ts_type_until(toks: list[tuple[str, str, int]], start: int, stop_set: set[str]) -> int:
		depths = {'(': 0, '<': 0, '[': 0}
		i, n = (start, len(toks))
		while i < n:
			t = toks[i][1]
			if 0 == sum(depths.values()) and t in stop_set:
				break
			Lexer.__update_depths(t, depths)
			i += 1
		return i
	# @used-by :func:`agent_tools.xref.js_lex.unquote()`
	# @used-by :meth:`Df.Harness.Xref.Js.Imports.Imports.parse_destruct_require()`
	# @used-by :meth:`Df.Harness.Xref.Js.Imports.Imports.parse_esm_import()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_named_var_decl()`
	@staticmethod
	def unquote(s: str) -> str:
		return s[1:-1] if 2 <= len(s) and s[0] == s[-1] and s[0] in ("'", '"') else s
