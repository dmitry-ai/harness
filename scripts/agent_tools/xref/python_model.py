# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import ast
# 2026-11-26
# "Implement Python AST cross-reference analyzer and sync CLI":
# https://github.com/dmitry-ai/harness/issues/287
SKIP_PARTS = frozenset({'.git', '.venv', '__pycache__', 'build', 'dist', 'node_modules', 'venv', '\ua616', '\ua66e'})
# @used-by :func:`_collect_file_ast()`
# @used-by :func:`_scan_control_imports()`
# @used-by :func:`agent_tools.xref.python_graph._collect_local_bindings()`
def _add_import_node(node: ast.AST, module_name: str, is_pkg: bool, out: dict[str, str]) -> None:
	if isinstance(node, ast.Import):
		for alias in node.names:
			local = alias.asname or alias.name.split('.')[0]
			out[local] = alias.name if alias.asname else local
	elif isinstance(node, ast.ImportFrom):
		base = _resolve_relative_module(module_name, is_pkg, node.level, node.module or '')
		for alias in node.names:
			if '*' != alias.name:
				local = alias.asname or alias.name
				out[local] = f'{base}.{alias.name}' if base else alias.name
# @used-by :func:`_walk_class()`
def _collect_class_attrs(cls_node: ast.ClassDef) -> dict[str, str]:
	attrs: dict[str, str] = {}
	for item in cls_node.body:
		if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and '__init__' == item.name:
			for sub in ast.walk(item):
				if isinstance(sub, ast.Assign) and isinstance(sub.value, ast.Call):
					cname = _expr_dotted(sub.value.func)
					if cname:
						for tgt in sub.targets:
							if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and 'self' == tgt.value.id:
								attrs[tgt.attr] = cname
	return attrs
# @used-by :func:`index_python_file()`
def _collect_file_ast(tree: ast.Module, module_name: str, is_pkg: bool, lines: list[str]) -> tuple[dict[str, str], dict[str, dict], list[dict], set[str], dict[str, str]]:
	imports, classes, defs, top_names, aliases = ({}, {}, [], set(), {})
	for stmt in tree.body:
		if isinstance(stmt, (ast.Import, ast.ImportFrom)):
			_add_import_node(stmt, module_name, is_pkg, imports)
		elif isinstance(stmt, ast.Assign):
			_record_top_assign(stmt, top_names, aliases)
		elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
			top_names.add(stmt.target.id)
		elif isinstance(stmt, (ast.If, ast.Try, ast.With)):
			_scan_control_imports(stmt, module_name, is_pkg, imports)
	_walk_body(tree.body, '', None, None, lines, classes, defs, top_names)
	return (imports, classes, defs, top_names, aliases)
# @used-by :func:`_make_def_info()`
def _decorator_info(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, list[str], bool, bool]:
	decs = list(node.decorator_list)
	dec_line = min((int(d.lineno) for d in decs), default=int(node.lineno))
	names = [_expr_dotted(d) for d in decs]
	ov_idx = [idx for idx, n in enumerate(names) if n in ('override', 'typing.override')]
	has_ov = bool(ov_idx)
	valid_pos = (not has_ov) or (len(names) - 1 == ov_idx[-1])
	return (dec_line, names, has_ov, valid_pos)
# @used-by :func:`_collect_class_attrs()`
# @used-by :func:`_decorator_info()`
# @used-by :func:`_record_top_assign()`
# @used-by :func:`_walk_class()`
# @used-by :func:`agent_tools.xref.python_graph._collect_local_bindings()`
# @used-by :func:`agent_tools.xref.python_graph._record_attr_ref()`
# @used-by :func:`agent_tools.xref.python_graph._record_name_or_call_ref()`
# @used-by :func:`agent_tools.xref.python_graph._record_with_ref()`
# @used-by :func:`agent_tools.xref.python_graph._resolve_call_class()`
def _expr_dotted(expr: ast.AST) -> str:
	if isinstance(expr, ast.Name):
		r = expr.id
	elif isinstance(expr, ast.Attribute):
		base = _expr_dotted(expr.value)
		r = f'{base}.{expr.attr}' if base else ''
	elif isinstance(expr, ast.Subscript):
		r = _expr_dotted(expr.value)
	elif isinstance(expr, ast.Call):
		r = _expr_dotted(expr.func)
	else:
		r = ''
	return r
# @used-by :func:`_walk_body()`
# @used-by :func:`_walk_nested_in_func()`
def _make_def_info(node: ast.FunctionDef | ast.AsyncFunctionDef, prefix: str, class_qn: str | None, parent_res: str | None, lines: list[str]) -> dict:
	qname = f'{prefix}.{node.name}' if prefix else node.name
	dec_line, dec_names, has_ov, valid_pos = _decorator_info(node)
	raw_line = lines[dec_line - 1] if 1 <= dec_line <= len(lines) else ''
	indent = raw_line[:len(raw_line) - len(raw_line.lstrip(' \t'))]
	is_method = None is not class_qn and None is parent_res
	end_ln = int(getattr(node, 'end_lineno', node.lineno) or node.lineno)
	return {'class_qualname': class_qn, 'dec_lineno': dec_line, 'decorators': dec_names, 'end_lineno': end_ln, 'has_override': has_ov, 'indent': indent, 'is_method': is_method, 'is_nested': None is not parent_res, 'kind': 'meth' if is_method else 'func', 'lineno': int(node.lineno), 'name': node.name, 'node': node, 'override_valid_pos': valid_pos, 'parent_resolvable': parent_res, 'qualname': qname}
# @used-by :func:`_collect_file_ast()`
def _record_top_assign(stmt: ast.Assign, top_names: set[str], aliases: dict[str, str]) -> None:
	rhs = _expr_dotted(stmt.value)
	for tgt in stmt.targets:
		if isinstance(tgt, ast.Name):
			top_names.add(tgt.id)
			if rhs:
				aliases[tgt.id] = rhs
# @used-by :func:`_add_import_node()`
def _resolve_relative_module(module_name: str, is_pkg: bool, level: int, sub: str) -> str:
	if 0 == level:
		r = sub
	else:
		parts = module_name.split('.') if module_name else []
		base_parts = parts if is_pkg else parts[:-1]
		up = level - 1
		kept = base_parts[:-up] if 0 < up else base_parts
		prefix = '.'.join(kept)
		r = f'{prefix}.{sub}' if prefix and sub else (prefix or sub)
	return r
# @used-by :func:`_collect_file_ast()`
def _scan_control_imports(stmt: ast.AST, module_name: str, is_pkg: bool, imports: dict[str, str]) -> None:
	for sub in ast.walk(stmt):
		if isinstance(sub, (ast.Import, ast.ImportFrom)):
			_add_import_node(sub, module_name, is_pkg, imports)
# @used-by :func:`discover_python_files()`
def _source_roots_for_repo(repo_root: Path, rel_paths: list[str]) -> tuple[str, ...]:
	roots: list[str] = []
	for cand in ('scripts', 'src', 'tests'):
		if (repo_root / cand).is_dir() or any((p.startswith(f'{cand}/') for p in rel_paths)):
			roots.append(cand)
	return tuple(roots)
# @used-by :func:`_collect_file_ast()`
# @used-by :func:`_walk_class()`
def _walk_body(stmts: list[ast.stmt], prefix: str, class_qn: str | None, parent_res: str | None, lines: list[str], classes: dict[str, dict], defs: list[dict], top_names: set[str]) -> None:
	for stmt in stmts:
		if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
			info = _make_def_info(stmt, prefix, class_qn, parent_res, lines)
			defs.append(info)
			if not prefix:
				top_names.add(stmt.name)
			next_parent = parent_res if None is not parent_res else info['qualname']
			_walk_nested_in_func(stmt, info['qualname'], next_parent, lines, classes, defs)
		elif isinstance(stmt, ast.ClassDef):
			_walk_class(stmt, prefix, parent_res, lines, classes, defs, top_names)
# @used-by :func:`_walk_body()`
# @used-by :func:`_walk_nested_in_func()`
def _walk_class(stmt: ast.ClassDef, prefix: str, parent_res: str | None, lines: list[str], classes: dict[str, dict], defs: list[dict], top_names: set[str]) -> None:
	cqn = f'{prefix}.{stmt.name}' if prefix else stmt.name
	if not prefix:
		top_names.add(stmt.name)
	bases = [_expr_dotted(b) for b in stmt.bases if _expr_dotted(b)]
	meth_names = {m.name for m in stmt.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
	classes[cqn] = {'attrs': _collect_class_attrs(stmt), 'bases': bases, 'is_nested': None is not parent_res, 'lineno': int(stmt.lineno), 'methods': meth_names, 'name': stmt.name, 'qualname': cqn}
	_walk_body(stmt.body, cqn, cqn, parent_res, lines, classes, defs, set())
# @used-by :func:`_walk_body()`
def _walk_nested_in_func(fn_node: ast.AST, prefix: str, parent_res: str, lines: list[str], classes: dict[str, dict], defs: list[dict]) -> None:
	for child in ast.iter_child_nodes(fn_node):
		if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
			info = _make_def_info(child, prefix, None, parent_res, lines)
			defs.append(info)
			_walk_nested_in_func(child, info['qualname'], parent_res, lines, classes, defs)
		elif isinstance(child, ast.ClassDef):
			_walk_class(child, prefix, parent_res, lines, classes, defs, set())
		else:
			_walk_nested_in_func(child, prefix, parent_res, lines, classes, defs)
# @used-by :func:`agent_tools.xref.python_sync.check_python_repo()`
# @used-by :func:`agent_tools.xref.python_sync.sync_python_repo()`
def build_python_repo_index(repo_root: Path, *, overrides_map: dict[str, str] | None=None) -> dict:
	files, by_module, symbols, classes, methods_by_name = ({}, {}, {}, {}, {})
	for rel, mod, src in discover_python_files(repo_root, overrides_map=overrides_map):
		finfo = index_python_file(rel, mod, src)
		files[rel] = by_module[mod] = finfo
		for cqn, cinfo in finfo['classes'].items():
			classes[f'{mod}.{cqn}'] = {**cinfo, 'module': mod, 'rel_path': rel}
		for dinfo in finfo['defs']:
			qn = dinfo['qualname']
			skey = f'{mod}.{qn}'
			symbols[skey] = {**dinfo, 'module': mod, 'rel_path': rel, 'symbol_key': skey}
			if dinfo['is_method']:
				methods_by_name.setdefault(dinfo['name'], []).append(skey)
	return {'by_module': by_module, 'classes': classes, 'files': files, 'methods_by_name': methods_by_name, 'repo_root': Path(repo_root).resolve(), 'symbols': symbols}
# @used-by :func:`build_python_repo_index()`
def discover_python_files(repo_root: Path, *, overrides_map: dict[str, str] | None=None) -> list[tuple[str, str, str]]:
	root = Path(repo_root).resolve()
	ov = {Path(k).as_posix(): v for k, v in (overrides_map or {}).items()}
	rels = set(ov.keys())
	for pyf in root.rglob('*.py'):
		parts = pyf.relative_to(root).parts
		if not any((p in SKIP_PARTS for p in parts)):
			rels.add(Path(*parts).as_posix())
	sorted_rels = sorted(rels)
	sroots = _source_roots_for_repo(root, sorted_rels)
	out: list[tuple[str, str, str]] = []
	for rel in sorted_rels:
		src = ov[rel] if rel in ov else ((root / rel).read_text(encoding='utf-8', errors='replace') if (root / rel).is_file() else None)
		if None is not src:
			out.append((rel, module_name_for_rel(rel, sroots), src))
	return out
# @used-by :func:`agent_tools.xref.python_sync.check_python_file_local()`
# @used-by :func:`build_python_repo_index()`
def index_python_file(rel_posix: str, module_name: str, source: str) -> dict:
	lines = (source or '').splitlines()
	is_pkg = rel_posix.endswith('/__init__.py') or '__init__.py' == rel_posix
	try:
		tree = ast.parse(source or '', filename=rel_posix)
	except SyntaxError as exc:
		r = {'aliases': {}, 'classes': {}, 'defs': [], 'imports': {}, 'is_pkg': is_pkg, 'lines': lines, 'module': module_name, 'rel_path': rel_posix, 'source': source or '', 'syntax_error': str(exc), 'top_names': set(), 'tree': None}
	else:
		imports, classes, defs, top_names, aliases = _collect_file_ast(tree, module_name, is_pkg, lines)
		r = {'aliases': aliases, 'classes': classes, 'defs': defs, 'imports': imports, 'is_pkg': is_pkg, 'lines': lines, 'module': module_name, 'rel_path': rel_posix, 'source': source or '', 'syntax_error': None, 'top_names': top_names, 'tree': tree}
	return r
# @used-by :func:`discover_python_files()`
def module_name_for_rel(rel_posix: str, source_roots: tuple[str, ...]) -> str:
	trimmed = rel_posix
	for sr in source_roots:
		pref = f'{sr}/'
		if trimmed.startswith(pref):
			trimmed = trimmed[len(pref):]
			break
	if trimmed.endswith('/__init__.py'):
		trimmed = trimmed[:-len('/__init__.py')]
	elif '__init__.py' == trimmed:
		trimmed = ''
	elif trimmed.endswith('.py'):
		trimmed = trimmed[:-3]
	return trimmed.replace('/', '.')
