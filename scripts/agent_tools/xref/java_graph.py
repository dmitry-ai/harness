# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
from .java_lex import count_top_args, match_delim
from .java_tags import collect_file_java_uses, parse_javadoc_block, resolve_java_target
# 2026-11-26
# "Extend cross-reference engine for JS/TS and Java":
# https://github.com/dmitry-ai/harness/issues/301
_OBJECT_METHODS = frozenset({'clone', 'equals', 'finalize', 'hashCode', 'toString'})
_PLUGIN_CLS_RE = re.compile(r'(?:implementation|class)\s*=\s*"([A-Za-z0-9_$.]+)"')
# @used-by :func:`_add_external_entry_edges()`
# @used-by :func:`_add_java_uses_edges()`
# @used-by :func:`_add_see_override_edges()`
# @used-by :func:`_link_fallback_unique_method()`
# @used-by :func:`_link_java_method()`
# @used-by :func:`_record_java_def_override()`
def _add_java_edge(used_by: dict[str, set[str]], target_key: str, caller_key: str) -> None:
	if target_key != caller_key:
		used_by.setdefault(target_key, set()).add(caller_key)
# @used-by :func:`build_java_call_graph()`
def _add_external_entry_edges(repo_index: dict, used_by: dict[str, set[str]]) -> None:
	root = repo_index['repo_root']
	plugin_classes = _scan_plugin_xml_classes(root)
	build_ps1_text = (root / 'build.ps1').read_text(encoding='utf-8', errors='replace') if (root / 'build.ps1').is_file() else ''
	for skey, sinfo in repo_index['symbols'].items():
		if sinfo['type_fqn'] in plugin_classes and (sinfo['has_override'] or (sinfo['is_ctor'] and 0 == sinfo['param_count'])):
			_add_java_edge(used_by, skey, 'META-INF/plugin.xml')
		if 'main' == sinfo['name'] and sinfo['type_fqn'] in build_ps1_text:
			_add_java_edge(used_by, skey, 'build.ps1')
		if sinfo['is_empty_private_ctor'] and not used_by.get(skey):
			_add_java_edge(used_by, skey, 'non-instantiable utility class')
# @used-by :func:`build_java_call_graph()`
def _add_java_override_edges(repo_index: dict, used_by: dict[str, set[str]]) -> None:
	for finfo in repo_index['files'].values():
		for dinfo in finfo['defs']:
			_record_java_def_override(finfo, dinfo, repo_index, used_by)
# @used-by :func:`build_java_call_graph()`
def _add_java_uses_edges(repo_index: dict, used_by: dict[str, set[str]]) -> None:
	for finfo in repo_index['files'].values():
		for item in collect_file_java_uses(finfo):
			if item['link_target']:
				ok, tkey = resolve_java_target(item['link_target'], finfo, repo_index)
				if ok and None is not tkey and tkey in repo_index['symbols']:
					_add_java_edge(used_by, tkey, item['caller_key'])
# 2026-11-26
# "Apply cross-reference annotations across Harness Python and JavaScript":
# https://github.com/dmitry-ai/harness/issues/305
# @used-by :func:`_record_java_def_override()`
def _add_see_override_edges(finfo: dict, dinfo: dict, skey: str, repo_index: dict, used_by: dict[str, set[str]]) -> None:
	hdr = parse_javadoc_block(finfo['lines'], dinfo['doc_anchor_line'], finfo['rel_path'])
	for entry in hdr['see']:
		ok, ref = resolve_java_target(entry['raw_value'], finfo, repo_index)
		if ok and None is not ref:
			_add_java_edge(used_by, skey, ref)
# @used-by :func:`_scan_java_file()`
def _collect_java_var_types(toks: list[tuple[str, str, int]], start: int, end: int, finfo: dict, repo_index: dict) -> dict[str, str]:
	vtypes: dict[str, str] = {}
	for i in range(start, max(start, end - 1)):
		if 'word' == toks[i][0] and 'word' == toks[i + 1][0]:
			tfqn = _resolve_java_type(toks[i][1], finfo, repo_index)
			if None is not tfqn:
				vtypes[toks[i + 1][1]] = tfqn
	return vtypes
# @used-by :func:`find_java_overridden_method()`
def _infer_external_override(dinfo: dict, bases: list[str], finfo: dict) -> str | None:
	sig = dinfo['sig']
	if dinfo['name'] in _OBJECT_METHODS:
		r: str | None = f'java.lang.Object#{sig}'
	elif 1 == len(bases):
		base = bases[0]
		fqn = finfo['imports'].get(base, base)
		r = f'{fqn}#{sig}'
	else:
		r = None
	return r
# @used-by :func:`_record_java_call()`
def _link_enclosing_or_static(dinfo: dict, mname: str, argc: int, finfo: dict, repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	cur = dinfo['type_fqn']
	found = False
	while (not found) and '.' in cur:
		cur = cur.rsplit('.', 1)[0]
		if cur in repo_index['types']:
			found = _link_java_method(cur, mname, argc, repo_index, caller_key, used_by)
	if not found:
		for si in finfo['static_imports']:
			if si.endswith(f'.{mname}') or si.endswith('.*'):
				tfqn = si.rsplit('.', 1)[0]
				if tfqn in repo_index['types'] and _link_java_method(tfqn, mname, argc, repo_index, caller_key, used_by):
					break
# @used-by :func:`_record_qualified_call()`
def _link_fallback_unique_method(mname: str, argc: int, repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	cands = [sk for sk in repo_index['methods_by_name'].get(mname, ()) if repo_index['symbols'][sk]['param_count'] == argc]
	if 1 == len(cands):
		_add_java_edge(used_by, cands[0], caller_key)
# @used-by :func:`_link_java_method()`
def _link_java_base_method(type_fqn: str, mname: str, arg_count: int | None, repo_index: dict, caller_key: str, used_by: dict[str, set[str]], visited: set[str]) -> bool:
	r = False
	tinfo = repo_index['types'].get(type_fqn)
	if None is not tinfo:
		finfo = repo_index['files'].get(tinfo['rel_path'])
		for base in tinfo['bases']:
			bfqn = _resolve_java_type(base, finfo, repo_index) if finfo else None
			if None is not bfqn and _link_java_method(bfqn, mname, arg_count, repo_index, caller_key, used_by, visited):
				r = True
				break
	return r
# @used-by :func:`_link_enclosing_or_static()`
# @used-by :func:`_link_java_base_method()`
# @used-by :func:`_link_super_method()`
# @used-by :func:`_record_java_call()`
# @used-by :func:`_record_qualified_call()`
# @used-by :func:`_scan_java_token()`
def _link_java_method(type_fqn: str, mname: str, arg_count: int | None, repo_index: dict, caller_key: str, used_by: dict[str, set[str]], seen: set[str] | None=None) -> bool:
	visited = seen if None is not seen else set()
	if type_fqn in visited:
		r = False
	else:
		visited.add(type_fqn)
		hits = _matching_methods_on_type(type_fqn, mname, arg_count, repo_index)
		if hits:
			for h in hits:
				_add_java_edge(used_by, h, caller_key)
			r = True
		else:
			r = _link_java_base_method(type_fqn, mname, arg_count, repo_index, caller_key, used_by, visited)
	return r
# @used-by :func:`_record_qualified_call()`
def _link_super_method(dinfo: dict, mname: str, argc: int, finfo: dict, repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	tinfo = repo_index['types'].get(dinfo['type_fqn'])
	for base in (tinfo['bases'] if tinfo else ()):
		bfqn = _resolve_java_type(base, finfo, repo_index)
		if None is not bfqn:
			_link_java_method(bfqn, mname, argc, repo_index, caller_key, used_by)
# @used-by :func:`_link_java_method()`
# @used-by :func:`find_java_overridden_method()`
def _matching_methods_on_type(type_fqn: str, mname: str, arg_count: int | None, repo_index: dict) -> list[str]:
	out: list[str] = []
	for skey in repo_index['methods_by_name'].get(mname, ()):
		sinfo = repo_index['symbols'][skey]
		if sinfo['type_fqn'] != type_fqn:
			continue
		if None is arg_count or sinfo['param_count'] == arg_count or (sinfo['is_varargs'] and arg_count >= sinfo['param_count'] - 1):
			out.append(skey)
	return out
# @used-by :func:`_scan_java_token()`
def _record_java_call(toks: list[tuple[str, str, int]], i: int, dinfo: dict, finfo: dict, vtypes: dict[str, str], repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	mname = toks[i][1]
	p_close = match_delim(toks, i + 1, '(', ')')
	argc = count_top_args(toks, i + 1, p_close)
	prev = toks[i - 1][1] if 0 < i else ''
	if 'new' == prev:
		tfqn = _resolve_java_type(mname, finfo, repo_index, current_type_fqn=dinfo['type_fqn'])
		if None is not tfqn:
			_link_java_method(tfqn, tfqn.rsplit('.', 1)[-1], argc, repo_index, caller_key, used_by)
	elif '.' == prev and 1 < i:
		_record_qualified_call(toks, i - 2, mname, argc, dinfo, finfo, vtypes, repo_index, caller_key, used_by)
	elif '::' != prev:
		if not _link_java_method(dinfo['type_fqn'], mname, argc, repo_index, caller_key, used_by):
			_link_enclosing_or_static(dinfo, mname, argc, finfo, repo_index, caller_key, used_by)
# 2026-11-26
# "Apply cross-reference annotations across Harness Python and JavaScript":
# https://github.com/dmitry-ai/harness/issues/305
# @used-by :func:`_add_java_override_edges()`
def _record_java_def_override(finfo: dict, dinfo: dict, repo_index: dict, used_by: dict[str, set[str]]) -> None:
	skey = dinfo['symbol_key']
	ov = find_java_overridden_method(finfo, dinfo, repo_index)
	if None is not ov:
		if ov in repo_index['symbols']:
			_add_java_edge(used_by, ov, dinfo['enclosing_res'] if dinfo['is_anon'] else skey)
		if not dinfo['is_anon']:
			_add_java_edge(used_by, skey, ov)
	elif dinfo['has_override'] and (not dinfo['is_anon']):
		_add_see_override_edges(finfo, dinfo, skey, repo_index, used_by)
	if dinfo['is_anon'] and dinfo['enclosing_res']:
		_add_java_edge(used_by, skey, dinfo['enclosing_res'])
# @used-by :func:`_record_java_call()`
def _record_qualified_call(toks: list[tuple[str, str, int]], recv_i: int, mname: str, argc: int, dinfo: dict, finfo: dict, vtypes: dict[str, str], repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	recv = toks[recv_i][1]
	if 'this' == recv:
		_link_java_method(dinfo['type_fqn'], mname, argc, repo_index, caller_key, used_by)
	elif 'super' == recv:
		_link_super_method(dinfo, mname, argc, finfo, repo_index, caller_key, used_by)
	elif recv in vtypes:
		_link_java_method(vtypes[recv], mname, argc, repo_index, caller_key, used_by)
	else:
		tfqn = _resolve_java_type(recv, finfo, repo_index)
		if None is not tfqn:
			_link_java_method(tfqn, mname, argc, repo_index, caller_key, used_by)
		else:
			_link_fallback_unique_method(mname, argc, repo_index, caller_key, used_by)
# @used-by :func:`_collect_java_var_types()`
# @used-by :func:`_link_java_base_method()`
# @used-by :func:`_link_super_method()`
# @used-by :func:`_record_java_call()`
# @used-by :func:`_record_qualified_call()`
# @used-by :func:`_scan_java_token()`
# @used-by :func:`find_java_overridden_method()`
def _resolve_java_type(raw_name: str, finfo: dict, repo_index: dict, *, current_type_fqn: str | None=None) -> str | None:
	types, pkg = (repo_index['types'], finfo['package'])
	cands = _type_name_candidates(raw_name, finfo, pkg, current_type_fqn)
	r: str | None = next((c for c in cands if c in types), None)
	if None is r:
		suffix = f'.{raw_name}'
		hits = [tfqn for tfqn in types if tfqn.endswith(suffix)]
		r = hits[0] if 1 == len(hits) else None
	return r
# @used-by :func:`_resolve_java_type()`
def _type_name_candidates(raw_name: str, finfo: dict, pkg: str, current_type_fqn: str | None) -> list[str]:
	cands: list[str] = []
	if None is not current_type_fqn:
		if current_type_fqn.endswith(f'.{raw_name}') or current_type_fqn == raw_name:
			cands.append(current_type_fqn)
		cands.append(f'{current_type_fqn}.{raw_name}')
		if '.' in current_type_fqn:
			cands.append(f"{current_type_fqn.rsplit('.', 1)[0]}.{raw_name}")
	head = raw_name.split('.', 1)[0]
	if head in finfo['imports']:
		cands.append(finfo['imports'][head] + raw_name[len(head):])
	if pkg:
		cands.append(f'{pkg}.{raw_name}')
	cands.append(raw_name)
	return cands
# @used-by :func:`build_java_call_graph()`
def _scan_java_file(finfo: dict, repo_index: dict, used_by: dict[str, set[str]]) -> None:
	toks = finfo['tokens']
	file_vtypes = _collect_java_var_types(toks, 0, len(toks), finfo, repo_index)
	for dinfo in finfo['defs']:
		if '{' == toks[dinfo['body_start']][1]:
			caller = dinfo['enclosing_res'] if dinfo['is_anon'] else dinfo['symbol_key']
			vtypes = {**file_vtypes, **_collect_java_var_types(toks, dinfo['body_start'], dinfo['body_end'], finfo, repo_index)}
			for i in range(dinfo['body_start'] + 1, dinfo['body_end']):
				_scan_java_token(toks, i, dinfo, finfo, vtypes, repo_index, caller, used_by)
# @used-by :func:`_scan_java_file()`
def _scan_java_token(toks: list[tuple[str, str, int]], i: int, dinfo: dict, finfo: dict, vtypes: dict[str, str], repo_index: dict, caller_key: str, used_by: dict[str, set[str]]) -> None:
	if 'word' == toks[i][0] and i + 1 < len(toks) and '(' == toks[i + 1][1]:
		_record_java_call(toks, i, dinfo, finfo, vtypes, repo_index, caller_key, used_by)
	elif '::' == toks[i][1] and 0 < i and i + 1 < len(toks) and 'word' == toks[i + 1][0]:
		tfqn = vtypes.get(toks[i - 1][1]) or _resolve_java_type(toks[i - 1][1], finfo, repo_index)
		if None is not tfqn:
			_link_java_method(tfqn, toks[i + 1][1], None, repo_index, caller_key, used_by)
# @used-by :func:`_add_external_entry_edges()`
def _scan_plugin_xml_classes(repo_root: Path) -> set[str]:
	found: set[str] = set()
	for pxml in repo_root.rglob('plugin.xml'):
		if 'META-INF' == pxml.parent.name:
			found.update(_PLUGIN_CLS_RE.findall(pxml.read_text(encoding='utf-8', errors='replace')))
	return found
# @used-by :func:`agent_tools.xref.java_sync.check_java_repo()`
# @used-by :func:`agent_tools.xref.java_sync.sync_java_repo()`
def build_java_call_graph(repo_index: dict) -> dict[str, set[str]]:
	used_by: dict[str, set[str]] = {}
	for finfo in repo_index['files'].values():
		_scan_java_file(finfo, repo_index, used_by)
	_add_java_uses_edges(repo_index, used_by)
	_add_java_override_edges(repo_index, used_by)
	_add_external_entry_edges(repo_index, used_by)
	return used_by
# @used-by :func:`_record_java_def_override()`
# @used-by :func:`agent_tools.xref.java_sync._check_java_override()`
# @used-by :func:`agent_tools.xref.java_sync._sync_java_def_edit()`
def find_java_overridden_method(finfo: dict, dinfo: dict, repo_index: dict) -> str | None:
	r: str | None = None
	if not dinfo['is_ctor']:
		tinfo = repo_index['types'].get(dinfo['type_fqn'])
		bases = tinfo['bases'] if tinfo else []
		for base in bases:
			bfqn = _resolve_java_type(base, finfo, repo_index)
			if None is not bfqn:
				hits = _matching_methods_on_type(bfqn, dinfo['name'], dinfo['param_count'], repo_index)
				if hits:
					r = hits[0]
					break
		if None is r and dinfo['has_override']:
			r = _infer_external_override(dinfo, bases, finfo)
	return r
