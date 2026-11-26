# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from .js_lex import match_delim, unquote
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
# @used-by :func:`parse_module_exports_rhs()`
def _record_obj_exports(toks: list[tuple[str, str, int]], start: int, end: int, exports: dict[str, str]) -> None:
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
# @used-by :func:`parse_destruct_require()`
# @used-by :func:`record_esm_specifiers()`
def _record_pair_bindings(toks: list[tuple[str, str, int]], start: int, end: int, sep: str, spec: str, imports: dict[str, tuple[str, str]]) -> None:
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
# @used-by :func:`agent_tools.xref.js_model._parse_top_fallback()`
def parse_cjs_exports(toks: list[tuple[str, str, int]], idx: int, exports: dict[str, str], default_exp: list[str]) -> int:
	n = len(toks)
	if idx + 3 < n and 'module' == toks[idx][1] and '.' == toks[idx + 1][1] and 'exports' == toks[idx + 2][1]:
		if '=' == toks[idx + 3][1]:
			r = parse_module_exports_rhs(toks, idx + 4, exports, default_exp)
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
# @used-by :func:`agent_tools.xref.js_model._parse_top_const()`
def parse_destruct_require(toks: list[tuple[str, str, int]], open_i: int, imports: dict[str, tuple[str, str]]) -> int:
	close_i = match_delim(toks, open_i, '{', '}')
	n = len(toks)
	if close_i + 4 < n and '=' == toks[close_i + 1][1] and 'require' == toks[close_i + 2][1] and '(' == toks[close_i + 3][1] and 'str' == toks[close_i + 4][0]:
		_record_pair_bindings(toks, open_i + 1, close_i, ':', unquote(toks[close_i + 4][1]), imports)
		r = close_i + 6
	elif close_i + 2 < n and '=' == toks[close_i + 1][1] and 'word' == toks[close_i + 2][0] and toks[close_i + 2][1] in imports:
		_record_pair_bindings(toks, open_i + 1, close_i, ':', imports[toks[close_i + 2][1]][0], imports)
		r = close_i + 3
	else:
		r = close_i + 1
	return r
# @used-by :func:`agent_tools.xref.js_model._parse_top_stmt()`
def parse_esm_export_list(toks: list[tuple[str, str, int]], idx: int, exports: dict[str, str]) -> int:
	end = match_delim(toks, idx, '{', '}')
	i = idx + 1
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
# @used-by :func:`agent_tools.xref.js_model._parse_top_stmt()`
def parse_esm_import(toks: list[tuple[str, str, int]], idx: int, imports: dict[str, tuple[str, str]]) -> int:
	n = len(toks)
	i = idx + 2 if idx + 1 < n and 'type' == toks[idx + 1][1] else idx + 1
	from_i = i
	while from_i < n and toks[from_i][1] not in ('from', ';'):
		from_i += 1
	if from_i + 1 < n and 'from' == toks[from_i][1] and 'str' == toks[from_i + 1][0]:
		record_esm_specifiers(toks, i, from_i, unquote(toks[from_i + 1][1]), imports)
		r = from_i + 2
	else:
		r = from_i + 1
	return r
# @used-by :func:`parse_cjs_exports()`
def parse_module_exports_rhs(toks: list[tuple[str, str, int]], rhs: int, exports: dict[str, str], default_exp: list[str]) -> int:
	n = len(toks)
	if rhs < n and '{' == toks[rhs][1]:
		end = match_delim(toks, rhs, '{', '}')
		_record_obj_exports(toks, rhs + 1, end, exports)
		r = end + 1
	elif rhs < n and 'word' == toks[rhs][0]:
		default_exp.append(toks[rhs][1])
		exports['default'] = toks[rhs][1]
		r = rhs + 1
	else:
		r = rhs + 1
	return r
# @used-by :func:`parse_esm_import()`
def record_esm_specifiers(toks: list[tuple[str, str, int]], start: int, end: int, spec: str, imports: dict[str, tuple[str, str]]) -> None:
	i = start
	while i < end:
		t = toks[i][1]
		if '{' == t:
			ce = match_delim(toks, i, '{', '}')
			_record_pair_bindings(toks, i + 1, min(ce, end), 'as', spec, imports)
			i = ce + 1
		elif '*' == t and i + 2 < end and 'as' == toks[i + 1][1] and 'word' == toks[i + 2][0]:
			imports[toks[i + 2][1]] = (spec, '*')
			i += 3
		elif 'word' == toks[i][0]:
			imports[t] = (spec, 'default')
			i += 1
		else:
			i += 1
