# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.text.source import df_line_indent
from .js_imports import parse_cjs_exports, parse_destruct_require, parse_esm_export_list, parse_esm_import
from .js_lex import arrow_body_end, find_arrow_after_eq, match_delim, skip_ts_type_until, tokenize_js, unquote
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
JS_EXTS = ('.js', '.mjs', '.cjs', '.ts', '.tsx')
SKIP_PARTS = frozenset({'.git', '.venv', '__pycache__', 'build', 'dist', 'node_modules', 'venv', '\ua616', '\ua66e'})
_CLASS_MODS = frozenset({'abstract', 'async', 'declare', 'get', 'override', 'private', 'protected', 'public', 'readonly', 'set', 'static'})
_CTRL_WORDS = frozenset({'catch', 'do', 'else', 'finally', 'for', 'if', 'new', 'return', 'switch', 'throw', 'try', 'while', 'with'})
# @used-by :func:`_parse_fn_expr_body()`
# @used-by :func:`_parse_top_func()`
# @used-by :func:`_parse_top_global_fn()`
# @used-by :func:`_parse_var_fn_rhs()`
def _add_def(defs: list[dict], info: dict, top_names: set[str]) -> None:
	defs.append(info)
	if None is info['class_name']:
		top_names.add(info['name'])
# @used-by :func:`discover_js_files()`
def _collect_js_rels(root: Path, ov: dict[str, str]) -> list[str]:
	rels = {k for k in ov if k.lower().endswith(JS_EXTS)}
	for ext in JS_EXTS:
		for fpath in root.rglob(f'*{ext}'):
			parts = fpath.relative_to(root).parts
			if not any((p in SKIP_PARTS for p in parts)):
				rels.add(Path(*parts).as_posix())
	return sorted(rels)
# @used-by :func:`_parse_top_stmt()`
def _dispatch_top_decl(toks: list[tuple[str, str, int]], idx: int, i: int, start_ln: int, exported: bool, state: dict) -> int:
	n = len(toks)
	t = toks[i][1] if i < n else ''
	if 'function' == t or ('async' == t and i + 1 < n and 'function' == toks[i + 1][1]):
		r = _parse_top_func(toks, i + 1 if 'async' == t else i, start_ln, state, exported)
	elif 'class' == t or ('abstract' == t and i + 1 < n and 'class' == toks[i + 1][1]):
		r = _parse_top_class(toks, i + 1 if 'abstract' == t else i, state, exported)
	elif t in ('const', 'let'):
		r = _parse_top_const(toks, i, state, exported)
	else:
		r = _parse_top_fallback(toks, idx, state)
	return r
# @used-by :func:`_try_parse_class_member()`
def _finish_class_member(toks: list[tuple[str, str, int]], name_i: int, end: int, cls_name: str, ln: int, lines: list[str], is_static: bool, has_ov: bool, is_ts: bool) -> tuple[dict | None, int]:
	mname = toks[name_i][1]
	nxt = skip_ts_type_until(toks, name_i + 1, {'(', '=', ';'})
	r: tuple[dict | None, int] = (None, name_i + 1)
	if nxt < end and '(' == toks[nxt][1]:
		b_open = skip_ts_type_until(toks, match_delim(toks, nxt, '(', ')') + 1, {'{', ';'})
		if b_open < end and '{' == toks[b_open][1]:
			b_end = match_delim(toks, b_open, '{', '}')
			r = (_make_js_def(mname, f'{cls_name}#{mname}', cls_name, ln, b_open, b_end, lines, is_static=is_static, has_ts_ov=has_ov, is_ts=is_ts), b_end + 1)
	elif nxt < end and '=' == toks[nxt][1]:
		arr = find_arrow_after_eq(toks, nxt)
		if -1 != arr and arr < end:
			b_end = min(arrow_body_end(toks, arr), end - 1)
			r = (_make_js_def(mname, f'{cls_name}#{mname}', cls_name, ln, arr + 1, b_end, lines, is_static=is_static, has_ts_ov=has_ov, is_ts=is_ts), b_end + 1)
	return r
# 2026-11-26 "Extract general duplicated helpers into Df/Core and Df/Qa": https://github.com/dmitry-ai/harness/issues/378
# @used-by :func:`_make_js_def()`
# @used-by :meth:`test_df_core_qa_s10.DfCoreQaS10Tests.test_harness_callers_delegate_to_new_core_and_qa_helpers()`
def _line_indent(lines: list[str], lineno: int) -> str:
	return df_line_indent(lines[lineno - 1] if 1 <= lineno <= len(lines) else '')
# @used-by :func:`_finish_class_member()`
# @used-by :func:`_parse_fn_expr_body()`
# @used-by :func:`_parse_top_func()`
# @used-by :func:`_parse_top_global_fn()`
# @used-by :func:`_parse_var_fn_rhs()`
def _make_js_def(name: str, qn: str, cls_name: str | None, lineno: int, b_start: int, b_end: int, lines: list[str], *, is_static: bool=False, has_ts_ov: bool=False, is_ts: bool=False) -> dict:
	return {'body_end': b_end, 'body_start': b_start, 'class_name': cls_name, 'has_ts_override': has_ts_ov, 'indent': _line_indent(lines, lineno), 'is_method': None is not cls_name, 'is_static': is_static, 'is_ts': is_ts, 'lineno': lineno, 'name': name, 'qualname': qn}
# @used-by :func:`_parse_top_class()`
def _parse_class_body(toks: list[tuple[str, str, int]], start: int, end: int, cls_name: str, lines: list[str], is_ts: bool) -> tuple[list[dict], set[str]]:
	defs, meths, i = ([], set(), start)
	while i < end:
		if ';' == toks[i][1]:
			i += 1
			continue
		dinfo, nxt = _try_parse_class_member(toks, i, end, cls_name, lines, is_ts)
		if None is not dinfo:
			defs.append(dinfo)
			meths.add(dinfo['name'])
			i = nxt
		elif '{' == toks[i][1]:
			i = match_delim(toks, i, '{', '}') + 1
		else:
			i += 1
	return (defs, meths)
# @used-by :func:`_parse_var_fn_rhs()`
def _parse_fn_expr_body(toks: list[tuple[str, str, int]], fn_i: int, name: str, ln: int, state: dict, exported: bool) -> int:
	i, n = (fn_i + 1, len(toks))
	while i < n and '(' != toks[i][1]:
		i += 1
	p_end = match_delim(toks, i, '(', ')') if i < n else n
	b_open = skip_ts_type_until(toks, p_end + 1, {'{'})
	if b_open < n and '{' == toks[b_open][1]:
		b_end = match_delim(toks, b_open, '{', '}')
		_add_def(state['defs'], _make_js_def(name, name, None, ln, b_open, b_end, state['lines'], is_ts=state['is_ts']), state['top_names'])
		if exported:
			state['exports'][name] = name
		r = b_end + 1
	else:
		r = fn_i + 1
	return r
# @used-by :func:`index_js_file()`
def _parse_js_tokens(toks: list[tuple[str, str, int]], lines: list[str], is_ts: bool) -> dict:
	state = {'classes': {}, 'default_exp': [], 'defs': [], 'exp_spans': [], 'exports': {}, 'imports': {}, 'is_ts': is_ts, 'lines': lines, 'top_names': set()}
	i, n = (0, len(toks))
	while i < n:
		i = _parse_top_stmt(toks, i, state)
	return {'classes': state['classes'], 'default_export': state['default_exp'][0] if state['default_exp'] else None, 'defs': state['defs'], 'export_spans': state['exp_spans'], 'exports': state['exports'], 'imports': state['imports'], 'top_names': state['top_names']}
# @used-by :func:`_parse_top_const()`
def _parse_named_var_decl(toks: list[tuple[str, str, int]], name_i: int, ln: int, state: dict, exported: bool) -> int:
	name, n = (toks[name_i][1], len(toks))
	eq_i = skip_ts_type_until(toks, name_i + 1, {'=', ';'})
	if eq_i < n and '=' == toks[eq_i][1]:
		if eq_i + 3 < n and 'require' == toks[eq_i + 1][1] and '(' == toks[eq_i + 2][1] and 'str' == toks[eq_i + 3][0]:
			state['imports'][name] = (unquote(toks[eq_i + 3][1]), '*')
			r = eq_i + 5
		else:
			r = _parse_var_fn_rhs(toks, eq_i, name, ln, state, exported)
	else:
		r = name_i + 1
	return r
# @used-by :func:`_dispatch_top_decl()`
def _parse_top_class(toks: list[tuple[str, str, int]], idx: int, state: dict, exported: bool) -> int:
	n, ln, i = (len(toks), toks[idx][2], idx + 1)
	if i < n and 'word' == toks[i][0]:
		cname = toks[i][1]
		base, b_open = _scan_class_header(toks, i + 1)
		if b_open < n and '{' == toks[b_open][1]:
			b_end = match_delim(toks, b_open, '{', '}')
			cdefs, meths = _parse_class_body(toks, b_open + 1, b_end, cname, state['lines'], state['is_ts'])
			state['classes'][cname] = {'base': base, 'body_end': b_end, 'body_start': b_open, 'lineno': ln, 'methods': meths, 'name': cname}
			state['defs'].extend(cdefs)
			state['top_names'].add(cname)
			if exported:
				state['exports'][cname] = cname
			r = b_end + 1
		else:
			r = i + 1
	else:
		r = idx + 1
	return r
# @used-by :func:`_dispatch_top_decl()`
def _parse_top_const(toks: list[tuple[str, str, int]], idx: int, state: dict, exported: bool) -> int:
	i, n, ln = (idx + 1, len(toks), toks[idx][2])
	if i < n and '{' == toks[i][1]:
		r = parse_destruct_require(toks, i, state['imports'])
	elif i < n and 'word' == toks[i][0]:
		r = _parse_named_var_decl(toks, i, ln, state, exported)
	else:
		r = idx + 1
	return r
# @used-by :func:`_dispatch_top_decl()`
def _parse_top_fallback(toks: list[tuple[str, str, int]], idx: int, state: dict) -> int:
	g_end = _parse_top_global_fn(toks, idx, state)
	if -1 != g_end:
		r = g_end
	else:
		cjs = parse_cjs_exports(toks, idx, state['exports'], state['default_exp'])
		if -1 != cjs:
			state['exp_spans'].append((idx, cjs))
			r = cjs
		elif '{' == toks[idx][1]:
			r = match_delim(toks, idx, '{', '}') + 1
		else:
			r = idx + 1
	return r
# @used-by :func:`_dispatch_top_decl()`
def _parse_top_func(toks: list[tuple[str, str, int]], idx: int, ln: int, state: dict, exported: bool) -> int:
	n = len(toks)
	i = idx + 2 if idx + 1 < n and '*' == toks[idx + 1][1] else idx + 1
	if i < n and 'word' == toks[i][0]:
		name = toks[i][1]
		p_i = skip_ts_type_until(toks, i + 1, {'('})
		p_end = match_delim(toks, p_i, '(', ')') if p_i < n else n
		b_open = skip_ts_type_until(toks, p_end + 1, {'{'})
		if b_open < n and '{' == toks[b_open][1]:
			b_end = match_delim(toks, b_open, '{', '}')
			_add_def(state['defs'], _make_js_def(name, name, None, ln, b_open, b_end, state['lines'], is_ts=state['is_ts']), state['top_names'])
			if exported:
				state['exports'][name] = name
			r = b_end + 1
		else:
			r = i + 1
	else:
		r = idx + 1
	return r
# @used-by :func:`_parse_top_fallback()`
def _parse_top_global_fn(toks: list[tuple[str, str, int]], idx: int, state: dict) -> int:
	n, r = (len(toks), -1)
	if idx + 3 < n and toks[idx][1] in ('exports', 'globalThis', 'window') and '.' == toks[idx + 1][1] and 'word' == toks[idx + 2][0] and '=' == toks[idx + 3][1]:
		arrow_i = find_arrow_after_eq(toks, idx + 3)
		if -1 != arrow_i:
			b_end = arrow_body_end(toks, arrow_i)
			qn = toks[idx + 2][1] if 'exports' == toks[idx][1] else f'{toks[idx][1]}.{toks[idx + 2][1]}'
			_add_def(state['defs'], _make_js_def(qn, qn, None, toks[idx][2], arrow_i + 1, b_end, state['lines'], is_ts=state['is_ts']), state['top_names'])
			if 'exports' == toks[idx][1]:
				state['exports'][toks[idx + 2][1]] = qn
			r = b_end + 1
	return r
# @used-by :func:`_parse_js_tokens()`
def _parse_top_stmt(toks: list[tuple[str, str, int]], idx: int, state: dict) -> int:
	n, start_ln = (len(toks), toks[idx][2])
	exported = 'export' == toks[idx][1]
	i = idx + 2 if exported and idx + 1 < n and 'default' == toks[idx + 1][1] else (idx + 1 if exported else idx)
	t = toks[i][1] if i < n else ''
	if exported and '{' == t:
		r = parse_esm_export_list(toks, i, state['exports'])
		state['exp_spans'].append((idx, r))
	elif 'import' == t:
		r = parse_esm_import(toks, i, state['imports'])
	else:
		r = _dispatch_top_decl(toks, idx, i, start_ln, exported, state)
	return r
# @used-by :func:`_parse_named_var_decl()`
def _parse_var_fn_rhs(toks: list[tuple[str, str, int]], eq_i: int, name: str, ln: int, state: dict, exported: bool) -> int:
	arrow_i = find_arrow_after_eq(toks, eq_i)
	if -1 != arrow_i:
		b_end = arrow_body_end(toks, arrow_i)
		_add_def(state['defs'], _make_js_def(name, name, None, ln, arrow_i + 1, b_end, state['lines'], is_ts=state['is_ts']), state['top_names'])
		if exported:
			state['exports'][name] = name
		r = b_end + 1
	else:
		n = len(toks)
		fn_i = eq_i + 2 if eq_i + 2 < n and 'async' == toks[eq_i + 1][1] and 'function' == toks[eq_i + 2][1] else (eq_i + 1 if eq_i + 1 < n and 'function' == toks[eq_i + 1][1] else -1)
		r = _parse_fn_expr_body(toks, fn_i, name, ln, state, exported) if -1 != fn_i else eq_i + 1
	return r
# @used-by :func:`_parse_top_class()`
def _scan_class_header(toks: list[tuple[str, str, int]], start: int) -> tuple[str | None, int]:
	i, n, base = (start, len(toks), None)
	while i < n and '{' != toks[i][1]:
		if 'extends' == toks[i][1] and i + 1 < n and 'word' == toks[i + 1][0]:
			base = toks[i + 1][1]
			i += 2
			while i + 1 < n and '.' == toks[i][1] and 'word' == toks[i + 1][0]:
				base = f'{base}.{toks[i + 1][1]}'
				i += 2
		else:
			i += 1
	return (base, i)
# @used-by :func:`_parse_class_body()`
def _try_parse_class_member(toks: list[tuple[str, str, int]], start: int, end: int, cls_name: str, lines: list[str], is_ts: bool) -> tuple[dict | None, int]:
	i, ln, is_static, has_ov = (start, toks[start][2], False, False)
	while i < end and toks[i][1] in _CLASS_MODS and i + 1 < end and toks[i + 1][1] not in ('(', '=', ';'):
		is_static = is_static or 'static' == toks[i][1]
		has_ov = has_ov or 'override' == toks[i][1]
		i += 1
	i = i + 1 if i < end and '*' == toks[i][1] else i
	r: tuple[dict | None, int] = (None, start + 1)
	if i < end and 'word' == toks[i][0] and toks[i][1] not in _CTRL_WORDS:
		r = _finish_class_member(toks, i, end, cls_name, ln, lines, is_static, has_ov, is_ts)
	return r
# @used-by :func:`agent_tools.xref.js_sync.check_js_repo()`
# @used-by :func:`agent_tools.xref.js_sync.sync_js_repo()`
def build_js_repo_index(repo_root: Path, *, overrides_map: dict[str, str] | None=None) -> dict:
	files, symbols, methods_by_name = ({}, {}, {})
	for rel, src in discover_js_files(repo_root, overrides_map=overrides_map):
		finfo = index_js_file(rel, src)
		files[rel] = finfo
		for dinfo in finfo['defs']:
			qn = dinfo['qualname']
			skey = f'{rel}::{qn}'
			symbols[skey] = {**dinfo, 'rel_path': rel, 'symbol_key': skey}
			if dinfo['is_method']:
				methods_by_name.setdefault(dinfo['name'], []).append(skey)
	return {'files': files, 'methods_by_name': methods_by_name, 'repo_root': Path(repo_root).resolve(), 'symbols': symbols}
# @used-by :func:`build_js_repo_index()`
def discover_js_files(repo_root: Path, *, overrides_map: dict[str, str] | None=None) -> list[tuple[str, str]]:
	root = Path(repo_root).resolve()
	ov = {Path(k).as_posix(): v for k, v in (overrides_map or {}).items()}
	out: list[tuple[str, str]] = []
	for rel in _collect_js_rels(root, ov):
		src = ov[rel] if rel in ov else ((root / rel).read_text(encoding='utf-8', errors='replace') if (root / rel).is_file() else None)
		if None is not src:
			out.append((rel, src))
	return out
# @used-by :func:`agent_tools.xref.js_sync.check_js_file_local()`
# @used-by :func:`build_js_repo_index()`
def index_js_file(rel_posix: str, source: str) -> dict:
	lines = (source or '').splitlines()
	is_ts = rel_posix.lower().endswith(('.ts', '.tsx'))
	toks = tokenize_js(source or '')
	parsed = _parse_js_tokens(toks, lines, is_ts)
	return {**parsed, 'is_ts': is_ts, 'lines': lines, 'rel_path': rel_posix, 'source': source or '', 'tokens': toks}
