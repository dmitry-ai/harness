# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.text.source import df_match_delim
from Df.Harness.Tdd.CommentScanners import CommentScanners
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Lexer:
	__WORD_RE = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
	# @used-by :func:`agent_tools.xref.java_lex.tokenize_java()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.index_file()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_tdd_and_xref_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_java_xref_classes_tokenize_index_graph_and_sync()`
	def __init__(self, source: str) -> None:
		self.__source = source
	# @used-by :func:`agent_tools.xref.java_lex.tokenize_java()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.index_file()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_tdd_and_xref_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_java_xref_classes_tokenize_index_graph_and_sync()`
	def tokenize(self) -> list[tuple[str, str, int]]:
		toks: list[tuple[str, str, int]] = []
		i, n, line = (0, len(self.__source), 1)
		while i < n:
			i, line = Lexer.__tokenize_java_step(self.__source, i, line, toks)
		return toks
	# @used-by :meth:`Lexer.__parse_single_param()`
	@staticmethod
	def __clean_param_type(parts: list[str]) -> str:
		type_parts = parts[:-1] if 2 <= len(parts) else parts
		raw = ''.join(type_parts)
		arr = ''
		while raw.endswith('[]'):
			arr += '[]'
			raw = raw[:-2]
		if raw.endswith('...'):
			arr = '...'
			raw = raw[:-3]
		simple = raw.rsplit('.', 1)[-1] if '.' in raw else raw
		return f'{simple}{arr}'
	# @used-by :meth:`Lexer.extract_param_types()`
	@staticmethod
	def __parse_single_param(toks: list[tuple[str, str, int]], start: int, end: int) -> tuple[str, bool]:
		i, parts, is_varargs = (start, [], False)
		while i < end:
			t = toks[i][1]
			if '@' == t:
				i = Lexer.skip_annotation(toks, i, end)
			elif '<' == t:
				i = Lexer.match_delim(toks, i, '<', '>') + 1
			elif 'final' == t:
				i += 1
			elif '...' == t:
				is_varargs = True
				parts.append('...')
				i += 1
			else:
				parts.append(t)
				i += 1
		return (Lexer.__clean_param_type(parts), is_varargs)
	# @used-by :meth:`Lexer.__tokenize_java_step()`
	@staticmethod
	def __tokenize_java_atom(src: str, i: int, line: int, toks: list[tuple[str, str, int]]) -> tuple[int, int]:
		ch = src[i]
		if src.startswith('"""', i):
			end = max(i + 3, CommentScanners.scan_triple_quote(src, i, '"'))
			toks.append(('str', src[i:end], line))
			r = (end, line + src[i:end].count('\n'))
		elif ch in ('"', "'"):
			end = max(i + 1, CommentScanners.scan_quoted(src, i, ch, backslash=True, allow_nl=False))
			toks.append(('str', src[i:end], line))
			r = (end, line)
		elif src.startswith('...', i):
			toks.append(('punct', '...', line))
			r = (i + 3, line)
		elif src.startswith('::', i):
			toks.append(('punct', '::', line))
			r = (i + 2, line)
		else:
			r = Lexer.__tokenize_java_word_or_punct(src, i, line, toks)
		return r
	# @used-by :meth:`Lexer.tokenize()`
	@staticmethod
	def __tokenize_java_step(src: str, i: int, line: int, toks: list[tuple[str, str, int]]) -> tuple[int, int]:
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
		else:
			r = Lexer.__tokenize_java_atom(src, i, line, toks)
		return r
	# @used-by :meth:`Lexer.__tokenize_java_atom()`
	@staticmethod
	def __tokenize_java_word_or_punct(src: str, i: int, line: int, toks: list[tuple[str, str, int]]) -> tuple[int, int]:
		m = Lexer.__WORD_RE.match(src, i)
		if None is not m:
			toks.append(('word', m.group(0), line))
			r = (m.end(), line)
		else:
			toks.append(('punct', src[i], line))
			r = (i + 1, line)
		return r
	# @used-by :func:`agent_tools.xref.java_lex.count_top_args()`
	# @used-by :meth:`Df.Harness.Xref.Java.Graph.Graph.__record_java_call()`
	@staticmethod
	def count_top_args(toks: list[tuple[str, str, int]], open_p: int, close_p: int) -> int:
		if open_p + 1 >= close_p:
			r = 0
		else:
			count, depth, i = (1, 0, open_p + 1)
			while i < close_p:
				t = toks[i][1]
				if t in ('(', '[', '{'):
					depth += 1
				elif t in (')', ']', '}') and 0 < depth:
					depth -= 1
				elif ',' == t and 0 == depth:
					count += 1
				i += 1
			r = count
		return r
	# @used-by :func:`agent_tools.xref.java_lex.extract_param_types()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__record_method_def()`
	@staticmethod
	def extract_param_types(toks: list[tuple[str, str, int]], open_p: int, close_p: int) -> tuple[list[str], bool]:
		params: list[str] = []
		is_varargs = False
		seg_start, depth, i = (open_p + 1, 0, open_p + 1)
		while i <= close_p:
			t = toks[i][1] if i < close_p else ','
			if t in ('(', '<', '[', '{') and i < close_p:
				depth += 1
			elif t in (')', '>', ']', '}') and i < close_p and 0 < depth:
				depth -= 1
			elif ',' == t and 0 == depth:
				if seg_start < i:
					pt, va = Lexer.__parse_single_param(toks, seg_start, i)
					if pt:
						params.append(pt)
					is_varargs = is_varargs or va
				seg_start = i + 1
			i += 1
		return (params, is_varargs)
	# @used-by :func:`agent_tools.xref.java_lex.match_delim()`
	# @used-by :meth:`Df.Harness.Xref.Java.Graph.Graph.__record_java_call()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__find_decl_end()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__find_method_paren()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__parse_member()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__parse_type_body_item()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__parse_type_decl()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__read_new_type()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__record_anon_class()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__record_method_def()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__scan_anon_classes()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__scan_type_header()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__skip_enum_constants()`
	# @used-by :meth:`Lexer.__parse_single_param()`
	# @used-by :meth:`Lexer.skip_annotation()`
	@staticmethod
	def match_delim(toks: list[tuple[str, str, int]], start: int, open_ch: str, close_ch: str) -> int:
		return df_match_delim(toks, start, open_ch, close_ch)
	# @used-by :func:`agent_tools.xref.java_lex.skip_annotation()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__consume_modifiers()`
	# @used-by :meth:`Df.Harness.Xref.Java.Model.Model.__find_method_paren()`
	# @used-by :meth:`Lexer.__parse_single_param()`
	@staticmethod
	def skip_annotation(toks: list[tuple[str, str, int]], at_i: int, end: int) -> int:
		i = at_i + 1
		if i < end and 'word' == toks[i][0]:
			i += 1
			while i + 1 < end and '.' == toks[i][1] and 'word' == toks[i + 1][0]:
				i += 2
		if i < end and '(' == toks[i][1]:
			i = Lexer.match_delim(toks, i, '(', ')') + 1
		return i
