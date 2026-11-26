# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from .js_tags import collect_file_js_uses, resolve_js_link, resolve_js_module_path
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
# @used-by :func:`_add_js_override_edges()`
# @used-by :func:`_add_js_uses_edges()`
# @used-by :func:`_link_js_class_member()`
# @used-by :func:`_record_js_word_ref()`
# @used-by :func:`_record_obj_member_call()`
# @used-by :func:`_scan_js_inline_require()`
def _add_js_edge(used_by: dict[str, set[str]], target_key: str, caller_key: str) -> None:
	if target_key != caller_key:
		used_by.setdefault(target_key, set()).add(caller_key)
# @used-by :func:`build_js_call_graph()`
def _add_js_override_edges(repo_index: dict, used_by: dict[str, set[str]]) -> None:
	for finfo in repo_index['files'].values():
		rel = finfo['rel_path']
		for dinfo in finfo['defs']:
			ov = find_js_overridden_method(finfo, dinfo, repo_index)
			if None is not ov:
				qn = dinfo['qualname']
				_add_js_edge(used_by, ov, f'{rel}::{qn}')
# @used-by :func:`build_js_call_graph()`
def _add_js_uses_edges(repo_index: dict, used_by: dict[str, set[str]]) -> None:
	for finfo in repo_index['files'].values():
		for item in collect_file_js_uses(finfo):
			if item['link_target']:
				ok, tkey = resolve_js_link(item['link_target'], item['note'], finfo['rel_path'], repo_index)
				if ok and None is not tkey and tkey in repo_index['symbols']:
					_add_js_edge(used_by, tkey, item['caller_key'])
# @used-by :func:`_scan_js_file_calls()`
def _collect_js_cls_attrs(finfo: dict, repo_index: dict) -> dict[str, dict[str, tuple[str, str]]]:
	toks = finfo['tokens']
	attrs: dict[str, dict[str, tuple[str, str]]] = {}
	for dinfo in finfo['defs']:
		if dinfo['is_method'] and 'constructor' == dinfo['name'] and dinfo['class_name']:
			cmap = attrs.setdefault(dinfo['class_name'], {})
			for i in range(dinfo['body_start'], max(dinfo['body_start'], dinfo['body_end'] - 4)):
				if 'this' == toks[i][1] and '.' == toks[i + 1][1] and 'word' == toks[i + 2][0] and '=' == toks[i + 3][1] and 'new' == toks[i + 4][1] and i + 5 < dinfo['body_end'] and 'word' == toks[i + 5][0]:
					c_hit = _resolve_js_class(toks[i + 5][1], finfo, repo_index)
					if None is not c_hit:
						cmap[toks[i + 2][1]] = c_hit
	return attrs
# @used-by :func:`_scan_js_file_calls()`
# @used-by :func:`_scan_js_scope()`
def _collect_js_var_types(toks: list[tuple[str, str, int]], start: int, end: int, finfo: dict, repo_index: dict) -> dict[str, tuple[str, str]]:
	vtypes: dict[str, tuple[str, str]] = {}
	i = start
	while i + 3 < end:
		if toks[i][1] in ('const', 'let') and 'word' == toks[i + 1][0] and '=' == toks[i + 2][1] and 'new' == toks[i + 3][1] and i + 4 < end and 'word' == toks[i + 4][0]:
			c_hit = _resolve_js_class(toks[i + 4][1], finfo, repo_index)
			if None is not c_hit:
				vtypes[toks[i + 1][1]] = c_hit
		i += 1
	return vtypes
# @used-by :func:`_scan_js_file_calls()`
def _def_and_export_spans(finfo: dict) -> list[tuple[int, int]]:
	spans = list(finfo['export_spans'])
	for dinfo in finfo['defs']:
		spans.append((dinfo['body_start'], dinfo['body_end']))
	return spans
# @used-by :func:`_scan_js_file_calls()`
def _in_any_span(idx: int, spans: list[tuple[int, int]]) -> bool:
	return any((s <= idx <= e for s, e in spans))
# @used-by :func:`_record_chained_new_call()`
# @used-by :func:`_record_js_new_expr()`
# @used-by :func:`_record_obj_member_call()`
# @used-by :func:`_try_record_class_member()`
def _link_js_class_member(cls_ref: tuple[str, str], member: str, repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	c_rel, c_name = cls_ref
	skey = f'{c_rel}::{c_name}#{member}'
	if skey in repo_index['symbols']:
		_add_js_edge(used_by, skey, caller_key)
	else:
		finfo = repo_index['files'].get(c_rel)
		cinfo = finfo['classes'].get(c_name) if finfo else None
		if None is not cinfo and cinfo['base']:
			b_ref = _resolve_js_class(cinfo['base'], finfo, repo_index)
			if None is not b_ref and b_ref != cls_ref:
				_link_js_class_member(b_ref, member, repo_index, caller_key, used_by)
# @used-by :func:`_scan_js_token_at()`
def _record_js_member_call(toks: list[tuple[str, str, int]], dot_i: int, finfo: dict, cls_name: str | None, cls_attrs: dict[str, dict[str, tuple[str, str]]], vtypes: dict[str, tuple[str, str]], repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	if 0 < dot_i and dot_i + 1 < len(toks) and 'word' == toks[dot_i + 1][0]:
		prop, prev = (toks[dot_i + 1][1], toks[dot_i - 1][1])
		if _try_record_class_member(toks, dot_i, prev, prop, finfo, cls_name, cls_attrs, repo_index, caller_key, used_by):
			return
		if ')' == prev:
			_record_chained_new_call(toks, dot_i, prop, finfo, repo_index, caller_key, used_by)
		else:
			_record_obj_member_call(prev, prop, finfo, vtypes, repo_index, caller_key, used_by)
# @used-by :func:`_record_js_member_call()`
def _try_record_class_member(toks: list[tuple[str, str, int]], dot_i: int, prev: str, prop: str, finfo: dict, cls_name: str | None, cls_attrs: dict[str, dict[str, tuple[str, str]]], repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> bool:
	r = True
	if 'this' == prev and None is not cls_name:
		_link_js_class_member((finfo['rel_path'], cls_name), prop, repo_index, caller_key, used_by)
	elif 'super' == prev and None is not cls_name:
		cinfo = finfo['classes'].get(cls_name)
		b_ref = _resolve_js_class(cinfo['base'], finfo, repo_index) if cinfo and cinfo['base'] else None
		if None is not b_ref:
			_link_js_class_member(b_ref, prop, repo_index, caller_key, used_by)
	elif 2 < dot_i and 'this' == toks[dot_i - 3][1] and '.' == toks[dot_i - 2][1] and None is not cls_name and prev in cls_attrs.get(cls_name, {}):
		_link_js_class_member(cls_attrs[cls_name][prev], prop, repo_index, caller_key, used_by)
	else:
		r = False
	return r
# @used-by :func:`_record_js_member_call()`
def _record_chained_new_call(toks: list[tuple[str, str, int]], dot_i: int, prop: str, finfo: dict, repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	depth, j = (0, dot_i - 1)
	while 0 <= j:
		if ')' == toks[j][1]:
			depth += 1
		elif '(' == toks[j][1]:
			depth -= 1
			if 0 == depth:
				break
		j -= 1
	if 1 < j and 'word' == toks[j - 1][0] and 'new' == toks[j - 2][1]:
		c_ref = _resolve_js_class(toks[j - 1][1], finfo, repo_index)
		if None is not c_ref:
			_link_js_class_member(c_ref, prop, repo_index, caller_key, used_by)
# @used-by :func:`_record_js_member_call()`
def _record_obj_member_call(obj_name: str, prop: str, finfo: dict, vtypes: dict[str, tuple[str, str]], repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	if obj_name in finfo['imports']:
		spec, _ = finfo['imports'][obj_name]
		t_rel = resolve_js_module_path(finfo['rel_path'], spec, repo_index['files'])
		if None is not t_rel:
			tf = repo_index['files'][t_rel]
			mapped = tf['exports'].get(prop, prop)
			skey = f'{t_rel}::{mapped}'
			if skey in repo_index['symbols']:
				_add_js_edge(used_by, skey, caller_key)
	elif obj_name in vtypes:
		_link_js_class_member(vtypes[obj_name], prop, repo_index, caller_key, used_by)
	elif obj_name in finfo['classes']:
		_link_js_class_member((finfo['rel_path'], obj_name), prop, repo_index, caller_key, used_by)
	else:
		cands = repo_index['methods_by_name'].get(prop, ())
		if 1 == len(cands):
			_add_js_edge(used_by, cands[0], caller_key)
# @used-by :func:`_scan_js_token_at()`
def _record_js_new_expr(toks: list[tuple[str, str, int]], idx: int, finfo: dict, repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	n = len(toks)
	if idx + 1 < n and 'word' == toks[idx + 1][0]:
		raw = toks[idx + 1][1]
		if idx + 3 < n and '.' == toks[idx + 2][1] and 'word' == toks[idx + 3][0]:
			c_ref = _resolve_js_ns_class(raw, toks[idx + 3][1], finfo, repo_index)
		else:
			c_ref = _resolve_js_class(raw, finfo, repo_index)
		if None is not c_ref:
			_link_js_class_member(c_ref, 'constructor', repo_index, caller_key, used_by)
# @used-by :func:`_record_js_new_expr()`
def _resolve_js_ns_class(ns: str, prop: str, finfo: dict, repo_index: dict) -> tuple[str, str] | None:
	r: tuple[str, str] | None = None
	if ns in finfo['imports']:
		spec, _ = finfo['imports'][ns]
		t_rel = resolve_js_module_path(finfo['rel_path'], spec, repo_index['files'])
		if None is not t_rel:
			tf = repo_index['files'][t_rel]
			mapped = tf['exports'].get(prop, prop)
			if mapped in tf['classes']:
				r = (t_rel, mapped)
	return r
# @used-by :func:`_scan_js_token_at()`
def _record_js_word_ref(toks: list[tuple[str, str, int]], idx: int, finfo: dict, repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	name = toks[idx][1]
	prev = toks[idx - 1][1] if 0 < idx else ''
	if prev not in ('.', 'function', 'class'):
		rel = finfo['rel_path']
		if f'{rel}::{name}' in repo_index['symbols']:
			_add_js_edge(used_by, f'{rel}::{name}', caller_key)
		elif name in finfo['imports']:
			spec, orig = finfo['imports'][name]
			t_rel = resolve_js_module_path(rel, spec, repo_index['files'])
			if None is not t_rel:
				tf = repo_index['files'][t_rel]
				mapped = tf['default_export'] if orig in ('default', '*') else tf['exports'].get(orig, orig)
				if mapped and f'{t_rel}::{mapped}' in repo_index['symbols']:
					_add_js_edge(used_by, f'{t_rel}::{mapped}', caller_key)
# @used-by :func:`_collect_js_cls_attrs()`
# @used-by :func:`_collect_js_var_types()`
# @used-by :func:`_link_js_class_member()`
# @used-by :func:`_record_chained_new_call()`
# @used-by :func:`_record_js_new_expr()`
# @used-by :func:`_try_record_class_member()`
# @used-by :func:`find_js_overridden_method()`
def _resolve_js_class(raw_name: str, finfo: dict, repo_index: dict) -> tuple[str, str] | None:
	rel = finfo['rel_path']
	r: tuple[str, str] | None = None
	if raw_name in finfo['classes']:
		r = (rel, raw_name)
	elif raw_name in finfo['imports']:
		spec, orig = finfo['imports'][raw_name]
		t_rel = resolve_js_module_path(rel, spec, repo_index['files'])
		if None is not t_rel:
			tf = repo_index['files'][t_rel]
			mapped = tf['default_export'] if orig in ('default', '*') else tf['exports'].get(orig, orig)
			if mapped and mapped in tf['classes']:
				r = (t_rel, mapped)
	return r
# @used-by :func:`build_js_call_graph()`
def _scan_js_file_calls(finfo: dict, repo_index: dict, used_by: dict[str, set[str]]) -> None:
	rel, toks = (finfo['rel_path'], finfo['tokens'])
	spans = _def_and_export_spans(finfo)
	cls_attrs = _collect_js_cls_attrs(finfo, repo_index)
	top_caller = f'{rel}::*module*'
	top_vtypes = _collect_js_var_types(toks, 0, len(toks), finfo, repo_index)
	for i in range(len(toks)):
		if not _in_any_span(i, spans):
			_scan_js_token_at(toks, i, finfo, None, cls_attrs, top_vtypes, repo_index, top_caller, used_by)
	for dinfo in finfo['defs']:
		qn = dinfo['qualname']
		_scan_js_scope(toks, dinfo['body_start'], dinfo['body_end'] + 1, finfo, dinfo['class_name'], cls_attrs, repo_index, f'{rel}::{qn}', used_by)
# @used-by :func:`_scan_js_token_at()`
def _scan_js_inline_require(toks: list[tuple[str, str, int]], idx: int, finfo: dict, repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	n = len(toks)
	if idx + 3 < n and 'require' == toks[idx][1] and '(' == toks[idx + 1][1] and 'str' == toks[idx + 2][0] and ')' == toks[idx + 3][1]:
		spec = toks[idx + 2][1][1:-1]
		t_rel = resolve_js_module_path(finfo['rel_path'], spec, repo_index['files'])
		if None is not t_rel:
			tf = repo_index['files'][t_rel]
			if idx + 5 < n and '.' == toks[idx + 4][1] and 'word' == toks[idx + 5][0]:
				mapped = tf['exports'].get(toks[idx + 5][1], toks[idx + 5][1])
				if f'{t_rel}::{mapped}' in repo_index['symbols']:
					_add_js_edge(used_by, f'{t_rel}::{mapped}', caller_key)
			elif tf['default_export'] and f"{t_rel}::{tf['default_export']}" in repo_index['symbols']:
				_add_js_edge(used_by, f"{t_rel}::{tf['default_export']}", caller_key)
# @used-by :func:`_scan_js_file_calls()`
def _scan_js_scope(toks: list[tuple[str, str, int]], start: int, end: int, finfo: dict, cls_name: str | None, cls_attrs: dict[str, dict[str, tuple[str, str]]], repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	vtypes = _collect_js_var_types(toks, start, end, finfo, repo_index)
	for i in range(start, min(end, len(toks))):
		_scan_js_token_at(toks, i, finfo, cls_name, cls_attrs, vtypes, repo_index, caller_key, used_by)
# @used-by :func:`_scan_js_file_calls()`
# @used-by :func:`_scan_js_scope()`
def _scan_js_token_at(toks: list[tuple[str, str, int]], i: int, finfo: dict, cls_name: str | None, cls_attrs: dict[str, dict[str, tuple[str, str]]], vtypes: dict[str, tuple[str, str]], repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	kind, text, _ = toks[i]
	if '.' == text:
		_record_js_member_call(toks, i, finfo, cls_name, cls_attrs, vtypes, repo_index, caller_key, used_by)
	elif 'new' == text:
		_record_js_new_expr(toks, i, finfo, repo_index, caller_key, used_by)
	elif 'require' == text:
		_scan_js_inline_require(toks, i, finfo, repo_index, caller_key, used_by)
	elif 'word' == kind:
		_record_js_word_ref(toks, i, finfo, repo_index, caller_key, used_by)
# @used-by :func:`agent_tools.xref.js_sync.check_js_repo()`
# @used-by :func:`agent_tools.xref.js_sync.sync_js_repo()`
def build_js_call_graph(repo_index: dict) -> dict[str, set[str]]:
	used_by: dict[str, set[str]] = {}
	for finfo in repo_index['files'].values():
		_scan_js_file_calls(finfo, repo_index, used_by)
	_add_js_uses_edges(repo_index, used_by)
	_add_js_override_edges(repo_index, used_by)
	return used_by
# @used-by :func:`_add_js_override_edges()`
# @used-by :func:`agent_tools.xref.js_sync._check_js_override()`
# @used-by :func:`agent_tools.xref.js_sync._sync_js_def_edit()`
def find_js_overridden_method(finfo: dict, dinfo: dict, repo_index: dict) -> str | None:
	r: str | None = None
	if dinfo['is_method'] and 'constructor' != dinfo['name'] and dinfo['class_name']:
		cinfo = finfo['classes'].get(dinfo['class_name'])
		seen: set[tuple[str, str]] = set()
		cur_f, cur_base = (finfo, cinfo['base'] if cinfo else None)
		while cur_base:
			b_ref = _resolve_js_class(cur_base, cur_f, repo_index)
			if None is b_ref or b_ref in seen:
				break
			seen.add(b_ref)
			b_rel, b_cls = b_ref
			cand = f"{b_rel}::{b_cls}#{dinfo['name']}"
			if cand in repo_index['symbols']:
				r = cand
				break
			cur_f = repo_index['files'][b_rel]
			cur_base = cur_f['classes'][b_cls]['base']
	return r
