# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Xref.Js.Lexer import Lexer
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Imports:
	# @used-by :func:`agent_tools.xref.js_imports.parse_esm_import()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_top_stmt()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_js_xref_classes_tokenize_imports_graph_and_sync()`
	def __init__(self, toks: list[tuple[str, str, int]]) -> None:
		self.__toks = toks
	# @used-by :func:`agent_tools.xref.js_imports.parse_esm_import()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_top_stmt()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_js_xref_classes_tokenize_imports_graph_and_sync()`
	def parse_esm_import(self, idx: int, imports: dict[str, tuple[str, str]]) -> int:
		toks, n = (self.__toks, len(self.__toks))
		i = idx + 2 if idx + 1 < n and 'type' == toks[idx + 1][1] else idx + 1
		from_i = i
		while from_i < n and toks[from_i][1] not in ('from', ';'):
			from_i += 1
		if from_i + 1 < n and 'from' == toks[from_i][1] and 'str' == toks[from_i + 1][0]:
			Imports.record_esm_specifiers(toks, i, from_i, Lexer.unquote(toks[from_i + 1][1]), imports)
			r = from_i + 2
		else:
			r = from_i + 1
		return r
	# @used-by :meth:`Imports.parse_module_exports_rhs()`
	@staticmethod
	def __record_obj_exports(toks: list[tuple[str, str, int]], start: int, end: int, exports: dict[str, str]) -> None:
		i = start
		while i < end:
			if 'word' == toks[i][0]:
				k = toks[i][1]
				if i + 2 < end and ':' == toks[i + 1][1] and 'word' == toks[i + 2][0]:
					exports[k] = toks[i + 2][1]
					i += 3
				else:
					exports[k] = k
					i += 1
			else:
				i += 1
	# @used-by :meth:`Imports.parse_destruct_require()`
	# @used-by :meth:`Imports.record_esm_specifiers()`
	@staticmethod
	def __record_pair_bindings(toks: list[tuple[str, str, int]], start: int, end: int, sep: str, spec: str, imports: dict[str, tuple[str, str]]) -> None:
		i = start
		while i < end:
			if 'word' == toks[i][0]:
				orig = toks[i][1]
				if i + 2 < end and sep == toks[i + 1][1] and 'word' == toks[i + 2][0]:
					imports[toks[i + 2][1]] = (spec, orig)
					i += 3
				else:
					imports[orig] = (spec, orig)
					i += 1
			else:
				i += 1
	# @used-by :func:`agent_tools.xref.js_imports.parse_cjs_exports()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_top_fallback()`
	@staticmethod
	def parse_cjs_exports(toks: list[tuple[str, str, int]], idx: int, exports: dict[str, str], default_exp: list[str]) -> int:
		n = len(toks)
		if idx + 3 < n and 'module' == toks[idx][1] and '.' == toks[idx + 1][1] and 'exports' == toks[idx + 2][1]:
			if '=' == toks[idx + 3][1]:
				r = Imports.parse_module_exports_rhs(toks, idx + 4, exports, default_exp)
			elif '.' == toks[idx + 3][1] and idx + 6 < n and 'word' == toks[idx + 4][0] and '=' == toks[idx + 5][1]:
				exports[toks[idx + 4][1]] = toks[idx + 6][1] if 'word' == toks[idx + 6][0] else toks[idx + 4][1]
				r = idx + 6
			else:
				r = idx + 1
		elif idx + 4 < n and 'exports' == toks[idx][1] and '.' == toks[idx + 1][1] and 'word' == toks[idx + 2][0] and '=' == toks[idx + 3][1]:
			exports[toks[idx + 2][1]] = toks[idx + 4][1] if 'word' == toks[idx + 4][0] else toks[idx + 2][1]
			r = idx + 4
		else:
			r = -1
		return r
	# @used-by :func:`agent_tools.xref.js_imports.parse_destruct_require()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_top_const()`
	@staticmethod
	def parse_destruct_require(toks: list[tuple[str, str, int]], open_i: int, imports: dict[str, tuple[str, str]]) -> int:
		close_i, n = (Lexer.match_delim(toks, open_i, '{', '}'), len(toks))
		if close_i + 4 < n and '=' == toks[close_i + 1][1] and 'require' == toks[close_i + 2][1] and '(' == toks[close_i + 3][1] and 'str' == toks[close_i + 4][0]:
			Imports.__record_pair_bindings(toks, open_i + 1, close_i, ':', Lexer.unquote(toks[close_i + 4][1]), imports)
			r = close_i + 6
		elif close_i + 2 < n and '=' == toks[close_i + 1][1] and 'word' == toks[close_i + 2][0] and toks[close_i + 2][1] in imports:
			Imports.__record_pair_bindings(toks, open_i + 1, close_i, ':', imports[toks[close_i + 2][1]][0], imports)
			r = close_i + 3
		else:
			r = close_i + 1
		return r
	# @used-by :func:`agent_tools.xref.js_imports.parse_esm_export_list()`
	# @used-by :meth:`Df.Harness.Xref.Js.Model.Model.__parse_top_stmt()`
	@staticmethod
	def parse_esm_export_list(toks: list[tuple[str, str, int]], idx: int, exports: dict[str, str]) -> int:
		end, i = (Lexer.match_delim(toks, idx, '{', '}'), idx + 1)
		while i < end:
			if 'word' == toks[i][0]:
				local = toks[i][1]
				if i + 2 < end and 'as' == toks[i + 1][1] and 'word' == toks[i + 2][0]:
					exports[toks[i + 2][1]] = local
					i += 3
				else:
					exports[local] = local
					i += 1
			else:
				i += 1
		return end + 1
	# @used-by :func:`agent_tools.xref.js_imports.parse_module_exports_rhs()`
	# @used-by :meth:`Imports.parse_cjs_exports()`
	@staticmethod
	def parse_module_exports_rhs(toks: list[tuple[str, str, int]], rhs: int, exports: dict[str, str], default_exp: list[str]) -> int:
		n = len(toks)
		if rhs < n and '{' == toks[rhs][1]:
			end = Lexer.match_delim(toks, rhs, '{', '}')
			Imports.__record_obj_exports(toks, rhs + 1, end, exports)
			r = end + 1
		elif rhs < n and 'word' == toks[rhs][0]:
			default_exp.append(toks[rhs][1])
			exports['default'] = toks[rhs][1]
			r = rhs + 1
		else:
			r = rhs + 1
		return r
	# @used-by :func:`agent_tools.xref.js_imports.record_esm_specifiers()`
	# @used-by :meth:`Imports.parse_esm_import()`
	@staticmethod
	def record_esm_specifiers(toks: list[tuple[str, str, int]], start: int, end: int, spec: str, imports: dict[str, tuple[str, str]]) -> None:
		i = start
		while i < end:
			t = toks[i][1]
			if '{' == t:
				ce = Lexer.match_delim(toks, i, '{', '}')
				Imports.__record_pair_bindings(toks, i + 1, min(ce, end), 'as', spec, imports)
				i = ce + 1
			elif '*' == t and i + 2 < end and 'as' == toks[i + 1][1] and 'word' == toks[i + 2][0]:
				imports[toks[i + 2][1]] = (spec, '*')
				i += 3
			elif 'word' == toks[i][0]:
				imports[t] = (spec, 'default')
				i += 1
			else:
				i += 1
