# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import ast
from .python_model import _add_import_node, _expr_dotted
from .python_overrides import find_overridden_method, is_unittest_testcase_subclass
from .python_tags import collect_file_uses, resolve_sphinx_target
# 2026-11-26
# "Implement Python AST cross-reference analyzer and sync CLI":
# https://github.com/dmitry-ai/harness/issues/287
_UNITTEST_HOOKS = frozenset({'setUp', 'setUpClass', 'tearDown', 'tearDownClass'})
# @used-by :func:`_add_def_framework_edge()`
# @used-by :func:`_add_method_framework_edges()`
# @used-by :func:`_add_uses_edges()`
# @used-by :func:`_link_class_member()`
# @used-by :func:`_link_unique_or_typed_attr()`
# @used-by :func:`_record_all_exports()`
# @used-by :func:`_record_attr_ref()`
# @used-by :func:`_record_name_or_call_ref()`
def _add_edge(used_by: dict[str, set[tuple[str, str]]], target_key: str, caller_key: str, caller_kind: str) -> None:
	if target_key != caller_key:
		used_by.setdefault(target_key, set()).add((caller_key, caller_kind))
# @used-by :func:`_add_override_and_test_edges()`
def _add_def_framework_edge(finfo: dict, dinfo: dict, is_test_mod: bool, repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> None:
	mod, qn = (finfo['module'], dinfo['qualname'])
	skey = f'{mod}.{qn}'
	if dinfo['is_nested'] and dinfo['parent_resolvable']:
		pr = dinfo['parent_resolvable']
		p_key = f'{mod}.{pr}'
		p_kind = repo_index['symbols'][p_key]['kind'] if p_key in repo_index['symbols'] else 'func'
		_add_edge(used_by, skey, p_key, p_kind)
	elif dinfo['is_method'] and dinfo['class_qualname']:
		_add_method_framework_edges(finfo, dinfo, skey, repo_index, used_by)
	elif is_test_mod and dinfo['name'].startswith(('pytest_', 'test_')):
		_add_edge(used_by, skey, 'pytest', 'external')
	elif '__getattr__' == dinfo['name']:
		_add_edge(used_by, skey, mod, 'mod')
# @used-by :func:`_add_def_framework_edge()`
def _add_method_framework_edges(finfo: dict, dinfo: dict, skey: str, repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> None:
	cinfo = finfo['classes'].get(dinfo['class_qualname'])
	if None is not cinfo:
		if is_unittest_testcase_subclass(finfo, cinfo, repo_index) and (dinfo['name'].startswith('test_') or dinfo['name'] in _UNITTEST_HOOKS):
			_add_edge(used_by, skey, 'unittest', 'mod')
		ov = find_overridden_method(finfo, cinfo, dinfo['name'], repo_index)
		if None is not ov and ov not in repo_index['symbols'] and (not dinfo['name'].startswith('__')):
			_add_edge(used_by, skey, ov, 'meth')
# @used-by :func:`build_python_call_graph()`
def _add_override_and_test_edges(repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> None:
	for finfo in repo_index['files'].values():
		is_test_mod = finfo['rel_path'].startswith('tests/')
		for dinfo in finfo['defs']:
			_add_def_framework_edge(finfo, dinfo, is_test_mod, repo_index, used_by)
# @used-by :func:`build_python_call_graph()`
def _add_uses_edges(repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> None:
	for finfo in repo_index['files'].values():
		for item in collect_file_uses(finfo):
			if item['sphinx_target']:
				ok, key = resolve_sphinx_target(item['sphinx_target'], finfo['module'], repo_index)
				if ok and None is not key and key in repo_index['symbols']:
					_add_edge(used_by, key, item['caller_key'], item['caller_kind'])
# @used-by :func:`_scan_scope_nodes()`
def _collect_local_bindings(scope_node: ast.AST, finfo: dict, repo_index: dict) -> tuple[dict[str, str], dict[str, str]]:
	local_imports = dict(finfo['imports'])
	var_types: dict[str, str] = {}
	for sub in ast.walk(scope_node):
		if isinstance(sub, (ast.Import, ast.ImportFrom)):
			_add_import_node(sub, finfo['module'], finfo['is_pkg'], local_imports)
		elif isinstance(sub, ast.Assign):
			_record_assign_type(sub, finfo, local_imports, repo_index, var_types)
		elif isinstance(sub, ast.arg) and None is not sub.annotation:
			cname = _resolve_class_key(_expr_dotted(sub.annotation), finfo, local_imports, repo_index)
			if cname:
				var_types[sub.arg] = cname
	return (local_imports, var_types)
# @used-by :func:`_link_super_member()`
# @used-by :func:`_link_unique_or_typed_attr()`
# @used-by :func:`_record_attr_ref()`
# @used-by :func:`_record_name_or_call_ref()`
# @used-by :func:`_record_with_ref()`
def _link_class_member(class_key: str, attr: str, repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
	skey = f'{class_key}.{attr}'
	if skey in repo_index['symbols']:
		_add_edge(used_by, skey, caller[0], caller[1])
	elif class_key in repo_index['classes']:
		cinfo = repo_index['classes'][class_key]
		finfo = repo_index['by_module'][cinfo['module']]
		for b_raw in cinfo['bases']:
			bkey = _resolve_class_key(b_raw, finfo, finfo['imports'], repo_index)
			if bkey and bkey != class_key:
				_link_class_member(bkey, attr, repo_index, caller, used_by)
# @used-by :func:`_record_attr_ref()`
def _link_super_member(finfo: dict, cls_qn: str, attr: str, repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
	cinfo = finfo['classes'].get(cls_qn)
	if None is not cinfo:
		for b_raw in cinfo['bases']:
			bkey = _resolve_class_key(b_raw, finfo, finfo['imports'], repo_index)
			if bkey:
				_link_class_member(bkey, attr, repo_index, caller, used_by)
# @used-by :func:`_record_attr_ref()`
def _link_unique_or_typed_attr(node: ast.Attribute, attr: str, finfo: dict, cls_qn: str | None, var_types: dict[str, str], repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
	if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) and 'self' == node.value.value.id and None is not cls_qn:
		cinfo = finfo['classes'].get(cls_qn)
		raw_cls = cinfo['attrs'].get(node.value.attr) if cinfo else None
		ckey = _resolve_class_key(raw_cls or '', finfo, finfo['imports'], repo_index) if raw_cls else None
		if ckey:
			_link_class_member(ckey, attr, repo_index, caller, used_by)
	elif isinstance(node.value, ast.Name) and node.value.id in var_types:
		_link_class_member(var_types[node.value.id], attr, repo_index, caller, used_by)
	else:
		cands = repo_index['methods_by_name'].get(attr, ())
		if 1 == len(cands):
			_add_edge(used_by, cands[0], caller[0], caller[1])
# @used-by :func:`_collect_local_bindings()`
def _record_assign_type(stmt: ast.Assign, finfo: dict, local_imports: dict[str, str], repo_index: dict, var_types: dict[str, str]) -> None:
	if isinstance(stmt.value, ast.Call):
		cname = _resolve_class_key(_expr_dotted(stmt.value.func), finfo, local_imports, repo_index)
		if cname:
			for tgt in stmt.targets:
				if isinstance(tgt, ast.Name):
					var_types[tgt.id] = cname
# @used-by :func:`_scan_scope_nodes()`
def _record_attr_ref(node: ast.Attribute, finfo: dict, cls_qn: str | None, local_imports: dict[str, str], var_types: dict[str, str], repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
	mod, attr = (finfo['module'], node.attr)
	if isinstance(node.value, ast.Name) and node.value.id in ('self', 'cls') and None is not cls_qn:
		_link_class_member(f'{mod}.{cls_qn}', attr, repo_index, caller, used_by)
	elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and 'super' == node.value.func.id and None is not cls_qn:
		_link_super_member(finfo, cls_qn, attr, repo_index, caller, used_by)
	else:
		hit = _resolve_dotted_symbol(_expr_dotted(node), finfo, local_imports, var_types, repo_index)
		if None is not hit:
			_add_edge(used_by, hit, caller[0], caller[1])
		elif isinstance(node.value, ast.Call):
			ckey = _resolve_class_key(_expr_dotted(node.value.func), finfo, local_imports, repo_index)
			if ckey:
				_link_class_member(ckey, attr, repo_index, caller, used_by)
		else:
			_link_unique_or_typed_attr(node, attr, finfo, cls_qn, var_types, repo_index, caller, used_by)
# @used-by :func:`_scan_scope_nodes()`
def _record_name_or_call_ref(node: ast.AST, finfo: dict, local_imports: dict[str, str], repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
	if isinstance(node, ast.Name):
		hit = _resolve_dotted_symbol(node.id, finfo, local_imports, {}, repo_index)
		if None is not hit:
			_add_edge(used_by, hit, caller[0], caller[1])
	elif isinstance(node, ast.Call):
		ckey = _resolve_class_key(_expr_dotted(node.func), finfo, local_imports, repo_index)
		if ckey:
			_link_class_member(ckey, '__init__', repo_index, caller, used_by)
	elif isinstance(node, (ast.With, ast.AsyncWith)):
		_record_with_ref(node, finfo, local_imports, repo_index, caller, used_by)
# @used-by :func:`_record_name_or_call_ref()`
def _record_with_ref(node: ast.With | ast.AsyncWith, finfo: dict, local_imports: dict[str, str], repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
	for item in node.items:
		if isinstance(item.context_expr, ast.Call):
			ckey = _resolve_class_key(_expr_dotted(item.context_expr.func), finfo, local_imports, repo_index)
			if ckey:
				_link_class_member(ckey, '__enter__', repo_index, caller, used_by)
				_link_class_member(ckey, '__exit__', repo_index, caller, used_by)
# @used-by :func:`_resolve_class_key()`
# @used-by :func:`_resolve_dotted_symbol()`
def _follow_reexport(cand: str, target_map: dict, repo_index: dict) -> str | None:
	cur, r = (cand, None)
	mods = repo_index['by_module']
	for _ in range(5):
		if cur in target_map:
			r = cur
			break
		parts = cur.split('.')
		nxt = _step_reexport(parts, mods)
		if None is nxt or nxt == cur:
			break
		cur = nxt
	return r
# @used-by :func:`_follow_reexport()`
def _step_reexport(parts: list[str], mods: dict[str, dict]) -> str | None:
	r: str | None = None
	for split in range(len(parts) - 1, 0, -1):
		mod_name = '.'.join(parts[:split])
		mf = mods.get(mod_name)
		if None is not mf:
			attr = parts[split]
			mapped = mf['imports'].get(attr) or mf['aliases'].get(attr)
			if mapped:
				tail = '.'.join(parts[split + 1:])
				r = f'{mapped}.{tail}' if tail else mapped
				break
	return r
# @used-by :func:`_scan_module_top()`
def _record_all_exports(stmt: ast.Assign, finfo: dict, repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
	is_all = any((isinstance(t, ast.Name) and '__all__' == t.id for t in stmt.targets))
	if is_all and isinstance(stmt.value, (ast.List, ast.Tuple, ast.Set)):
		for elt in stmt.value.elts:
			if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
				hit = _resolve_dotted_symbol(elt.value, finfo, finfo['imports'], {}, repo_index)
				if None is not hit:
					_add_edge(used_by, hit, caller[0], caller[1])
# @used-by :func:`_collect_local_bindings()`
# @used-by :func:`_link_class_member()`
# @used-by :func:`_link_super_member()`
# @used-by :func:`_link_unique_or_typed_attr()`
# @used-by :func:`_record_assign_type()`
# @used-by :func:`_record_attr_ref()`
# @used-by :func:`_record_name_or_call_ref()`
# @used-by :func:`_record_with_ref()`
def _resolve_class_key(dotted: str, finfo: dict, local_imports: dict[str, str], repo_index: dict) -> str | None:
	r: str | None = None
	if dotted:
		mod = finfo['module']
		head = dotted.split('.')[0]
		rest = dotted[len(head):]
		cands = [f'{mod}.{dotted}', dotted]
		if head in local_imports:
			cands.insert(0, local_imports[head] + rest)
		for cand in cands:
			hit = _follow_reexport(cand, repo_index['classes'], repo_index)
			if None is not hit:
				r = hit
				break
	return r
# @used-by :func:`_record_all_exports()`
# @used-by :func:`_record_attr_ref()`
# @used-by :func:`_record_name_or_call_ref()`
def _resolve_dotted_symbol(dotted: str, finfo: dict, local_imports: dict[str, str], var_types: dict[str, str], repo_index: dict) -> str | None:
	r: str | None = None
	if dotted:
		mod = finfo['module']
		head = dotted.split('.')[0]
		rest = dotted[len(head):]
		cands = [f'{mod}.{dotted}', dotted]
		if head in local_imports:
			cands.insert(0, local_imports[head] + rest)
		if head in var_types and rest:
			cands.insert(0, var_types[head] + rest)
		for cand in cands:
			hit = _follow_reexport(cand, repo_index['symbols'], repo_index)
			if None is not hit:
				r = hit
				break
	return r
# @used-by :func:`build_python_call_graph()`
def _scan_file_calls(finfo: dict, repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> None:
	tree = finfo['tree']
	if None is not tree:
		mod = finfo['module']
		_scan_module_top(tree, finfo, repo_index, (mod, 'mod'), used_by)
		for dinfo in finfo['defs']:
			if not dinfo['is_nested']:
				dqn = dinfo['qualname']
				caller = (f'{mod}.{dqn}', dinfo['kind'])
				_scan_scope_nodes(dinfo['node'], finfo, dinfo['class_qualname'], repo_index, caller, used_by)
# @used-by :func:`_scan_file_calls()`
def _scan_module_top(tree: ast.Module, finfo: dict, repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
	for stmt in tree.body:
		if isinstance(stmt, ast.Assign):
			_record_all_exports(stmt, finfo, repo_index, caller, used_by)
			_scan_scope_nodes(stmt, finfo, None, repo_index, caller, used_by)
		elif not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
			_scan_scope_nodes(stmt, finfo, None, repo_index, caller, used_by)
		elif isinstance(stmt, ast.ClassDef):
			for dec in stmt.decorator_list:
				_scan_scope_nodes(dec, finfo, None, repo_index, caller, used_by)
			for sub in stmt.body:
				if not isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
					_scan_scope_nodes(sub, finfo, stmt.name, repo_index, caller, used_by)
# @used-by :func:`_scan_file_calls()`
# @used-by :func:`_scan_module_top()`
def _scan_scope_nodes(root_node: ast.AST, finfo: dict, cls_qn: str | None, repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
	local_imports, var_types = _collect_local_bindings(root_node, finfo, repo_index)
	for node in ast.walk(root_node):
		if isinstance(node, ast.Attribute):
			_record_attr_ref(node, finfo, cls_qn, local_imports, var_types, repo_index, caller, used_by)
		elif isinstance(node, (ast.Name, ast.Call, ast.With, ast.AsyncWith)):
			_record_name_or_call_ref(node, finfo, local_imports, repo_index, caller, used_by)
# @used-by :func:`agent_tools.xref.python_sync.check_python_repo()`
# @used-by :func:`agent_tools.xref.python_sync.sync_python_repo()`
def build_python_call_graph(repo_index: dict) -> dict[str, set[tuple[str, str]]]:
	used_by: dict[str, set[tuple[str, str]]] = {}
	for finfo in repo_index['files'].values():
		_scan_file_calls(finfo, repo_index, used_by)
	_add_uses_edges(repo_index, used_by)
	_add_override_and_test_edges(repo_index, used_by)
	return used_by
