# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Xref.Python.Model import Model
from Df.Harness.Xref.Python.Overrides import Overrides
from Df.Harness.Xref.Python.Tags import Tags
import ast
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class Graph:
	__UNITTEST_HOOKS = frozenset({'setUp', 'setUpClass', 'tearDown', 'tearDownClass'})
	# @used-by :func:`agent_tools.xref.python_graph.build_python_call_graph()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.check_repo()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.sync()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_xref_java_and_python_tail_branches()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_python_xref_classes_and_engine_roundtrip()`
	def __init__(self, repo_index: dict) -> None:
		self.__repo_index = repo_index
	# @used-by :func:`agent_tools.xref.python_graph.build_python_call_graph()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.check_repo()`
	# @used-by :meth:`Df.Harness.Xref.Python.Syncer.Syncer.sync()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_xref_java_and_python_tail_branches()`
	# @used-by :meth:`test_df_harness_s11_wave2b_xref.DfHarnessS11Wave2bXrefTests.test_python_xref_classes_and_engine_roundtrip()`
	def build(self) -> dict[str, set[tuple[str, str]]]:
		used_by: dict[str, set[tuple[str, str]]] = {}
		for finfo in self.__repo_index['files'].values():
			Graph.__scan_file_calls(finfo, self.__repo_index, used_by)
		Graph.__add_uses_edges(self.__repo_index, used_by)
		Graph.__add_override_and_test_edges(self.__repo_index, used_by)
		return used_by
	# @used-by :meth:`Graph.__add_override_and_test_edges()`
	@staticmethod
	def __add_def_framework_edge(finfo: dict, dinfo: dict, is_test_mod: bool, repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> None:
		mod, qn = (finfo['module'], dinfo['qualname'])
		skey = f'{mod}.{qn}'
		if dinfo['is_nested'] and dinfo['parent_resolvable']:
			pr = dinfo['parent_resolvable']
			p_key = f'{mod}.{pr}'
			p_kind = repo_index['symbols'][p_key]['kind'] if p_key in repo_index['symbols'] else 'func'
			Graph.__add_edge(used_by, skey, p_key, p_kind)
		elif dinfo['is_method'] and dinfo['class_qualname']:
			Graph.__add_method_framework_edges(finfo, dinfo, skey, repo_index, used_by)
		elif is_test_mod and dinfo['name'].startswith(('pytest_', 'test_')):
			Graph.__add_edge(used_by, skey, 'pytest', 'external')
		elif '__getattr__' == dinfo['name']:
			Graph.__add_edge(used_by, skey, mod, 'mod')
	# @used-by :meth:`Graph.__add_def_framework_edge()`
	# @used-by :meth:`Graph.__add_method_framework_edges()`
	# @used-by :meth:`Graph.__add_uses_edges()`
	# @used-by :meth:`Graph.__link_class_member()`
	# @used-by :meth:`Graph.__link_unique_or_typed_attr()`
	# @used-by :meth:`Graph.__record_all_exports()`
	# @used-by :meth:`Graph.__record_attr_ref()`
	# @used-by :meth:`Graph.__record_name_or_call_ref()`
	@staticmethod
	def __add_edge(used_by: dict[str, set[tuple[str, str]]], target_key: str, caller_key: str, caller_kind: str) -> None:
		if target_key != caller_key:
			used_by.setdefault(target_key, set()).add((caller_key, caller_kind))
	# @used-by :meth:`Graph.__add_def_framework_edge()`
	@staticmethod
	def __add_method_framework_edges(finfo: dict, dinfo: dict, skey: str, repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> None:
		cinfo = finfo['classes'].get(dinfo['class_qualname'])
		if None is not cinfo:
			if Overrides.is_unittest_testcase_subclass(finfo, cinfo, repo_index) and (dinfo['name'].startswith('test_') or dinfo['name'] in Graph.__UNITTEST_HOOKS):
				Graph.__add_edge(used_by, skey, 'unittest', 'mod')
			ov = Overrides(finfo, cinfo, repo_index).find_overridden_method(dinfo['name'])
			if None is not ov and ov not in repo_index['symbols'] and (not dinfo['name'].startswith('__')):
				Graph.__add_edge(used_by, skey, ov, 'meth')
	# @used-by :meth:`Graph.build()`
	@staticmethod
	def __add_override_and_test_edges(repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> None:
		for finfo in repo_index['files'].values():
			is_test_mod = finfo['rel_path'].startswith('tests/')
			for dinfo in finfo['defs']:
				Graph.__add_def_framework_edge(finfo, dinfo, is_test_mod, repo_index, used_by)
	# @used-by :meth:`Graph.build()`
	@staticmethod
	def __add_uses_edges(repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> None:
		for finfo in repo_index['files'].values():
			for item in Tags.collect_file_uses(finfo):
				if item['sphinx_target']:
					ok, key = Tags.resolve_sphinx_target(item['sphinx_target'], finfo['module'], repo_index)
					if ok and None is not key and key in repo_index['symbols']:
						Graph.__add_edge(used_by, key, item['caller_key'], item['caller_kind'])
	# @used-by :meth:`Graph.__scan_scope_nodes()`
	@staticmethod
	def __collect_local_bindings(scope_node: ast.AST, finfo: dict, repo_index: dict) -> tuple[dict[str, str], dict[str, str]]:
		local_imports = dict(finfo['imports'])
		var_types: dict[str, str] = {}
		for sub in ast.walk(scope_node):
			if isinstance(sub, (ast.Import, ast.ImportFrom)):
				Model.add_import_node(sub, finfo['module'], finfo['is_pkg'], local_imports)
			elif isinstance(sub, ast.Assign):
				Graph.__record_assign_type(sub, finfo, local_imports, repo_index, var_types)
			elif isinstance(sub, ast.arg) and None is not sub.annotation:
				cname = Graph.__resolve_class_key(Model.expr_dotted(sub.annotation), finfo, local_imports, repo_index)
				if cname:
					var_types[sub.arg] = cname
		return (local_imports, var_types)
	# @used-by :meth:`Graph.__resolve_class_key()`
	# @used-by :meth:`Graph.__resolve_dotted_symbol()`
	@staticmethod
	def __follow_reexport(cand: str, target_map: dict, repo_index: dict) -> str | None:
		cur, r = (cand, None)
		mods = repo_index['by_module']
		for _ in range(5):
			if cur in target_map:
				r = cur
				break
			nxt = Graph.__step_reexport(cur.split('.'), mods)
			if None is nxt or nxt == cur:
				break
			cur = nxt
		return r
	# @used-by :meth:`Graph.__link_super_member()`
	# @used-by :meth:`Graph.__link_unique_or_typed_attr()`
	# @used-by :meth:`Graph.__record_attr_ref()`
	# @used-by :meth:`Graph.__record_name_or_call_ref()`
	# @used-by :meth:`Graph.__record_with_ref()`
	@staticmethod
	def __link_class_member(class_key: str, attr: str, repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
		skey = f'{class_key}.{attr}'
		if skey in repo_index['symbols']:
			Graph.__add_edge(used_by, skey, caller[0], caller[1])
		elif class_key in repo_index['classes']:
			cinfo = repo_index['classes'][class_key]
			finfo = repo_index['by_module'][cinfo['module']]
			for b_raw in cinfo['bases']:
				bkey = Graph.__resolve_class_key(b_raw, finfo, finfo['imports'], repo_index)
				if bkey and bkey != class_key:
					Graph.__link_class_member(bkey, attr, repo_index, caller, used_by)
	# @used-by :meth:`Graph.__record_attr_ref()`
	@staticmethod
	def __link_super_member(finfo: dict, cls_qn: str, attr: str, repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
		cinfo = finfo['classes'].get(cls_qn)
		if None is not cinfo:
			for b_raw in cinfo['bases']:
				bkey = Graph.__resolve_class_key(b_raw, finfo, finfo['imports'], repo_index)
				if bkey:
					Graph.__link_class_member(bkey, attr, repo_index, caller, used_by)
	# @used-by :meth:`Graph.__record_attr_ref()`
	@staticmethod
	def __link_unique_or_typed_attr(node: ast.Attribute, attr: str, finfo: dict, cls_qn: str | None, var_types: dict[str, str], repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
		if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) and 'self' == node.value.value.id and None is not cls_qn:
			cinfo = finfo['classes'].get(cls_qn)
			raw_cls = cinfo['attrs'].get(node.value.attr) if cinfo else None
			ckey = Graph.__resolve_class_key(raw_cls or '', finfo, finfo['imports'], repo_index) if raw_cls else None
			if ckey:
				Graph.__link_class_member(ckey, attr, repo_index, caller, used_by)
		elif isinstance(node.value, ast.Name) and node.value.id in var_types:
			Graph.__link_class_member(var_types[node.value.id], attr, repo_index, caller, used_by)
		else:
			cands = repo_index['methods_by_name'].get(attr, ())
			if 1 == len(cands):
				Graph.__add_edge(used_by, cands[0], caller[0], caller[1])
	# @used-by :meth:`Graph.__scan_module_top()`
	@staticmethod
	def __record_all_exports(stmt: ast.Assign, finfo: dict, repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
		is_all = any((isinstance(t, ast.Name) and '__all__' == t.id for t in stmt.targets))
		if is_all and isinstance(stmt.value, (ast.List, ast.Tuple, ast.Set)):
			for elt in stmt.value.elts:
				if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
					hit = Graph.__resolve_dotted_symbol(elt.value, finfo, finfo['imports'], {}, repo_index)
					if None is not hit:
						Graph.__add_edge(used_by, hit, caller[0], caller[1])
	# @used-by :meth:`Graph.__collect_local_bindings()`
	@staticmethod
	def __record_assign_type(stmt: ast.Assign, finfo: dict, local_imports: dict[str, str], repo_index: dict, var_types: dict[str, str]) -> None:
		if isinstance(stmt.value, ast.Call):
			cname = Graph.__resolve_call_class(stmt.value, finfo, local_imports, repo_index)
			if cname:
				for tgt in stmt.targets:
					if isinstance(tgt, ast.Name):
						var_types[tgt.id] = cname
	# @used-by :meth:`Graph.__scan_scope_nodes()`
	@staticmethod
	def __record_attr_ref(node: ast.Attribute, finfo: dict, cls_qn: str | None, local_imports: dict[str, str], var_types: dict[str, str], repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
		mod, attr = (finfo['module'], node.attr)
		if isinstance(node.value, ast.Name) and node.value.id in ('self', 'cls') and None is not cls_qn:
			Graph.__link_class_member(f'{mod}.{cls_qn}', attr, repo_index, caller, used_by)
		elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and 'super' == node.value.func.id and None is not cls_qn:
			Graph.__link_super_member(finfo, cls_qn, attr, repo_index, caller, used_by)
		else:
			hit = Graph.__resolve_dotted_symbol(Model.expr_dotted(node), finfo, local_imports, var_types, repo_index)
			if None is not hit:
				Graph.__add_edge(used_by, hit, caller[0], caller[1])
			elif isinstance(node.value, ast.Call):
				ckey = Graph.__resolve_call_class(node.value, finfo, local_imports, repo_index)
				if ckey:
					Graph.__link_class_member(ckey, attr, repo_index, caller, used_by)
			else:
				Graph.__link_unique_or_typed_attr(node, attr, finfo, cls_qn, var_types, repo_index, caller, used_by)
	# @used-by :meth:`Graph.__scan_scope_nodes()`
	@staticmethod
	def __record_name_or_call_ref(node: ast.AST, finfo: dict, cls_qn: str | None, local_imports: dict[str, str], repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
		if isinstance(node, ast.Name):
			hit = Graph.__resolve_dotted_symbol(node.id, finfo, local_imports, {}, repo_index)
			if None is not hit:
				Graph.__add_edge(used_by, hit, caller[0], caller[1])
		elif isinstance(node, ast.Call):
			if isinstance(node.func, ast.Name) and 'cls' == node.func.id and None is not cls_qn:
				Graph.__link_class_member(f"{finfo['module']}.{cls_qn}", '__init__', repo_index, caller, used_by)
			else:
				ckey = Graph.__resolve_class_key(Model.expr_dotted(node.func), finfo, local_imports, repo_index)
				if ckey:
					Graph.__link_class_member(ckey, '__init__', repo_index, caller, used_by)
		elif isinstance(node, (ast.With, ast.AsyncWith)):
			Graph.__record_with_ref(node, finfo, local_imports, repo_index, caller, used_by)
	# @used-by :meth:`Graph.__record_name_or_call_ref()`
	@staticmethod
	def __record_with_ref(node: ast.With | ast.AsyncWith, finfo: dict, local_imports: dict[str, str], repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
		for item in node.items:
			if isinstance(item.context_expr, ast.Call):
				ckey = Graph.__resolve_class_key(Model.expr_dotted(item.context_expr.func), finfo, local_imports, repo_index)
				if ckey:
					Graph.__link_class_member(ckey, '__enter__', repo_index, caller, used_by)
					Graph.__link_class_member(ckey, '__exit__', repo_index, caller, used_by)
	# @used-by :meth:`Graph.__record_assign_type()`
	# @used-by :meth:`Graph.__record_attr_ref()`
	@staticmethod
	def __resolve_call_class(call_node: ast.Call, finfo: dict, local_imports: dict[str, str], repo_index: dict) -> str | None:
		dotted = Model.expr_dotted(call_node.func)
		r = Graph.__resolve_class_key(dotted, finfo, local_imports, repo_index)
		if None is r:
			sym_key = Graph.__resolve_dotted_symbol(dotted, finfo, local_imports, {}, repo_index)
			sym = repo_index['symbols'].get(sym_key) if sym_key else None
			ret_node = sym['node'].returns if sym and hasattr(sym.get('node'), 'returns') else None
			if None is not ret_node:
				sf = repo_index['files'].get(sym['rel_path'])
				if None is not sf:
					r = Graph.__resolve_class_key(Model.expr_dotted(ret_node), sf, sf['imports'], repo_index)
		return r
	# @used-by :meth:`Graph.__collect_local_bindings()`
	# @used-by :meth:`Graph.__link_class_member()`
	# @used-by :meth:`Graph.__link_super_member()`
	# @used-by :meth:`Graph.__link_unique_or_typed_attr()`
	# @used-by :meth:`Graph.__record_name_or_call_ref()`
	# @used-by :meth:`Graph.__record_with_ref()`
	# @used-by :meth:`Graph.__resolve_call_class()`
	@staticmethod
	def __resolve_class_key(dotted: str, finfo: dict, local_imports: dict[str, str], repo_index: dict) -> str | None:
		r: str | None = None
		if dotted:
			mod, head = (finfo['module'], dotted.split('.')[0])
			rest = dotted[len(head):]
			cands = [f'{mod}.{dotted}', dotted]
			if head in local_imports:
				cands.insert(0, local_imports[head] + rest)
			for cand in cands:
				hit = Graph.__follow_reexport(cand, repo_index['classes'], repo_index)
				if None is not hit:
					r = hit
					break
		return r
	# @used-by :meth:`Graph.__record_all_exports()`
	# @used-by :meth:`Graph.__record_attr_ref()`
	# @used-by :meth:`Graph.__record_name_or_call_ref()`
	# @used-by :meth:`Graph.__resolve_call_class()`
	@staticmethod
	def __resolve_dotted_symbol(dotted: str, finfo: dict, local_imports: dict[str, str], var_types: dict[str, str], repo_index: dict) -> str | None:
		r: str | None = None
		if dotted:
			mod, head = (finfo['module'], dotted.split('.')[0])
			rest = dotted[len(head):]
			cands = [f'{mod}.{dotted}', dotted]
			if head in local_imports:
				cands.insert(0, local_imports[head] + rest)
			if head in var_types and rest:
				cands.insert(0, var_types[head] + rest)
			for cand in cands:
				hit = Graph.__follow_reexport(cand, repo_index['symbols'], repo_index)
				if None is not hit:
					r = hit
					break
		return r
	# @used-by :meth:`Graph.build()`
	@staticmethod
	def __scan_file_calls(finfo: dict, repo_index: dict, used_by: dict[str, set[tuple[str, str]]]) -> None:
		tree = finfo['tree']
		if None is not tree:
			mod = finfo['module']
			Graph.__scan_module_top(tree, finfo, repo_index, (mod, 'mod'), used_by)
			for dinfo in finfo['defs']:
				if not dinfo['is_nested']:
					dqn = dinfo['qualname']
					Graph.__scan_scope_nodes(dinfo['node'], finfo, dinfo['class_qualname'], repo_index, (f'{mod}.{dqn}', dinfo['kind']), used_by)
	# @used-by :meth:`Graph.__scan_file_calls()`
	@staticmethod
	def __scan_module_top(tree: ast.Module, finfo: dict, repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
		for stmt in tree.body:
			if isinstance(stmt, ast.Assign):
				Graph.__record_all_exports(stmt, finfo, repo_index, caller, used_by)
				Graph.__scan_scope_nodes(stmt, finfo, None, repo_index, caller, used_by)
			elif not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
				Graph.__scan_scope_nodes(stmt, finfo, None, repo_index, caller, used_by)
			elif isinstance(stmt, ast.ClassDef):
				for dec in stmt.decorator_list:
					Graph.__scan_scope_nodes(dec, finfo, None, repo_index, caller, used_by)
				for sub in stmt.body:
					if not isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
						Graph.__scan_scope_nodes(sub, finfo, stmt.name, repo_index, caller, used_by)
	# @used-by :meth:`Graph.__scan_file_calls()`
	# @used-by :meth:`Graph.__scan_module_top()`
	@staticmethod
	def __scan_scope_nodes(root_node: ast.AST, finfo: dict, cls_qn: str | None, repo_index: dict, caller: tuple[str, str], used_by: dict[str, set[tuple[str, str]]]) -> None:
		local_imports, var_types = Graph.__collect_local_bindings(root_node, finfo, repo_index)
		for node in ast.walk(root_node):
			if isinstance(node, ast.Attribute):
				Graph.__record_attr_ref(node, finfo, cls_qn, local_imports, var_types, repo_index, caller, used_by)
			elif isinstance(node, (ast.Name, ast.Call, ast.With, ast.AsyncWith)):
				Graph.__record_name_or_call_ref(node, finfo, cls_qn, local_imports, repo_index, caller, used_by)
	# @used-by :meth:`Graph.__follow_reexport()`
	@staticmethod
	def __step_reexport(parts: list[str], mods: dict[str, dict]) -> str | None:
		r: str | None = None
		for split in range(len(parts) - 1, 0, -1):
			mf = mods.get('.'.join(parts[:split]))
			if None is not mf:
				attr = parts[split]
				mapped = mf['imports'].get(attr) or mf['aliases'].get(attr)
				if mapped:
					tail = '.'.join(parts[split + 1:])
					r = f'{mapped}.{tail}' if tail else mapped
					break
		return r
