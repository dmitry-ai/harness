# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import ast
import io
from pathlib import Path
import tokenize
# 2026-11-24
# "Enforce transaction-boundary Python size ratchet and symbol integrity checks":
# https://github.com/dmitry-ai/harness/issues/186
from .python_integrity import check_python_integrity
from .shell_audit import normalize_host_path
from .tdd_gate import _compute_edited_content, _git_head_text, _git_index_text, is_test_file
# 2026-11-23
# "Enforce AST function and file SLOC ratchet gate in PreToolUse and Git pre-commit":
# https://github.com/dmitry-ai/harness/issues/161
PROD_FILE_SLOC_LIMIT = 300
PROD_FUNC_SLOC_LIMIT = 20
PROD_MCCABE_LIMIT = 8
TEST_FILE_SLOC_LIMIT = 600
TEST_FUNC_SLOC_LIMIT = 40
TEST_MCCABE_LIMIT = 12
_TRIVIAL_TOKENS = frozenset({tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT, tokenize.ENDMARKER, tokenize.ENCODING})
_BRANCH_NODES = (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler)
def _check_file_and_semis(rel_label: str, cur: dict, base: dict | None, file_lim: int) -> list[str]:
	errs: list[str] = []
	base_sloc = base['file_sloc'] if base else 0
	eff_file = max(file_lim, base_sloc) if base_sloc > file_lim else file_lim
	if cur['file_sloc'] > eff_file:
		kind = 'legacy ratchet' if eff_file > file_lim else 'limit'
		errs.append(f'CODE-4: File {rel_label} has {cur["file_sloc"]} executable SLOC, exceeding {kind} ({eff_file}); split new logic into a separate module')
	base_semi = len(base['semicolon_lines']) if base else 0
	if len(cur['semicolon_lines']) > base_semi:
		errs.append(f'CODE-4: Anti-gaming semicolon multi-statement line(s) detected in {rel_label} at line(s) {cur["semicolon_lines"][:5]}; write one statement per line')
	return errs
def _check_function_limits(rel_label: str, cur_funcs: dict, base_funcs: dict, func_lim: int, mccabe_lim: int) -> list[str]:
	errs: list[str] = []
	for qname, info in cur_funcs.items():
		binfo = base_funcs.get(qname)
		eff_sloc = max(func_lim, binfo['sloc']) if binfo and binfo['sloc'] > func_lim else func_lim
		eff_mc = max(mccabe_lim, binfo['mccabe']) if binfo and binfo['mccabe'] > mccabe_lim else mccabe_lim
		if info['sloc'] > eff_sloc:
			kind = 'legacy ratchet' if eff_sloc > func_lim else 'limit'
			errs.append(f'CODE-4: Function {rel_label}:{qname} has {info["sloc"]} executable SLOC, exceeding {kind} ({eff_sloc}); decompose into compact helpers')
		if info['mccabe'] > eff_mc:
			kind = 'legacy ratchet' if eff_mc > mccabe_lim else 'limit'
			errs.append(f'CODE-4: Function {rel_label}:{qname} has McCabe complexity {info["mccabe"]}, exceeding {kind} ({eff_mc}); simplify branching')
	return errs
def _code_lines_and_semicolons(source: str) -> tuple[set[int], list[int]]:
	code_lines: set[int] = set()
	per_line: dict[int, list[tuple[int, str]]] = {}
	try:
		for tok in tokenize.generate_tokens(io.StringIO(source).readline):
			if tok.type not in _TRIVIAL_TOKENS and tok.string.strip():
				ln = tok.start[0]
				code_lines.add(ln)
				per_line.setdefault(ln, []).append((tok.type, tok.string))
	except (tokenize.TokenError, IndentationError):
		pass
	semis = [ln for ln, toks in sorted(per_line.items()) if any((tokenize.OP == t and ';' == s and idx + 1 < len(toks) for idx, (t, s) in enumerate(toks)))]
	return (code_lines, semis)
# 2026-11-26
# "Codify navigable cross-reference standards and override SLOC exemption":
# https://github.com/dmitry-ai/harness/issues/286
def _add_override_decorator_lines(node: ast.AST, excluded: set[int]) -> None:
	for dec in getattr(node, 'decorator_list', ()):
		if (isinstance(dec, ast.Name) and 'override' == dec.id) or (isinstance(dec, ast.Attribute) and 'override' == dec.attr and isinstance(dec.value, ast.Name) and 'typing' == dec.value.id):
			excluded.update(range(dec.lineno, (getattr(dec, 'end_lineno', None) or dec.lineno) + 1))
def _is_override_import(node: ast.AST) -> bool:
	return isinstance(node, ast.ImportFrom) and 'typing' == node.module and 1 == len(node.names) and 'override' == node.names[0].name and None is node.names[0].asname
def _collect_excluded_lines(tree: ast.AST) -> set[int]:
	excluded: set[int] = set()
	for node in ast.walk(tree):
		if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
			if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
				excluded.update(range(node.body[0].lineno, (node.body[0].end_lineno or node.body[0].lineno) + 1))
			_add_override_decorator_lines(node, excluded)
		elif _is_override_import(node):
			excluded.update(range(node.lineno, (getattr(node, 'end_lineno', None) or node.lineno) + 1))
		elif isinstance(node, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
			end_ln = getattr(node, 'end_lineno', None) or node.lineno
			if end_ln > node.lineno and _is_constant_expr(node):
				excluded.update(range(node.lineno + 1, end_ln + 1))
	return excluded
def _count_mccabe_in_node(node: ast.AST) -> int:
	count = 1 if isinstance(node, _BRANCH_NODES) else 0
	if isinstance(node, ast.comprehension):
		count += len(node.ifs)
	elif hasattr(ast, 'match_case') and isinstance(node, ast.match_case):
		pat = getattr(node, 'pattern', None)
		if not (hasattr(ast, 'MatchAs') and isinstance(pat, ast.MatchAs) and None is pat.pattern and None is pat.name):
			count += 1
	for child in ast.iter_child_nodes(node):
		if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
			count += _count_mccabe_in_node(child)
	return count
def _find_git_root(path: Path) -> Path | None:
	start = path if path.is_dir() else path.parent
	r = None
	for anc in (start, *start.parents):
		if (anc / '.git').exists():
			r = anc
			break
	return r
def _function_metrics(fn_node: ast.AST, effective_lines: set[int]) -> dict:
	start = fn_node.lineno
	end = getattr(fn_node, 'end_lineno', None) or start
	nested_lines: set[int] = set()
	for child in ast.iter_child_nodes(fn_node):
		for sub in ast.walk(child):
			if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
				sub_end = getattr(sub, 'end_lineno', None) or sub.lineno
				nested_lines.update(range(sub.lineno, sub_end + 1))
	own_lines = [ln for ln in effective_lines if start <= ln <= end and ln not in nested_lines]
	complexity = 1 + sum((_count_mccabe_in_node(stmt) for stmt in getattr(fn_node, 'body', ())))
	return {'sloc': len(own_lines), 'mccabe': complexity, 'lineno': start}
def _is_constant_expr(node: ast.AST) -> bool:
	if isinstance(node, ast.Constant):
		r = True
	elif isinstance(node, ast.UnaryOp):
		r = _is_constant_expr(node.operand)
	elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
		r = all((_is_constant_expr(el) for el in node.elts))
	elif isinstance(node, ast.Dict):
		r = all(((None is k or _is_constant_expr(k)) and _is_constant_expr(v) for k, v in zip(node.keys, node.values)))
	else:
		r = False
	return r
# 2026-11-24
# "Enforce transaction-boundary Python size ratchet and symbol integrity checks":
# https://github.com/dmitry-ai/harness/issues/186
def _is_legacy_oversized_baseline(path: str | Path, baseline_source: str | None) -> bool:
	r = False
	if None is not baseline_source:
		base = analyze_python_source(baseline_source)
		if None is base['syntax_error']:
			file_lim, func_lim, mccabe_lim = _limits_for_path(path)
			r = base['file_sloc'] > file_lim or any((f['sloc'] > func_lim or f['mccabe'] > mccabe_lim for f in base['functions'].values()))
	return r
def _iter_functions(node: ast.AST, prefix: str='') -> list[tuple[str, ast.AST]]:
	out: list[tuple[str, ast.AST]] = []
	for child in ast.iter_child_nodes(node):
		if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
			qname = f'{prefix}.{child.name}' if prefix else child.name
			out.append((qname, child))
			out.extend(_iter_functions(child, qname))
		elif isinstance(child, ast.ClassDef):
			cname = f'{prefix}.{child.name}' if prefix else child.name
			out.extend(_iter_functions(child, cname))
	return out
def _limits_for_path(path: str | Path) -> tuple[int, int, int]:
	return (TEST_FILE_SLOC_LIMIT, TEST_FUNC_SLOC_LIMIT, TEST_MCCABE_LIMIT) if is_test_file(path) else (PROD_FILE_SLOC_LIMIT, PROD_FUNC_SLOC_LIMIT, PROD_MCCABE_LIMIT)
def _resolve_python_target(args: dict, payload: dict) -> tuple[Path, Path, str] | None:
	r = None
	raw_p = str(args.get('Path') or '').strip()
	if raw_p and raw_p.lower().endswith('.py'):
		cwd_raw = str(payload.get('cwd') or '').strip()
		cwd = Path(cwd_raw).resolve() if cwd_raw else None
		cand = normalize_host_path(raw_p)
		target = cand.resolve() if cand.is_absolute() else ((cwd / cand).resolve() if cwd else cand.resolve())
		repo_root = _find_git_root(target)
		if None is not repo_root:
			rel = target.relative_to(repo_root).as_posix()
			if not rel.casefold().startswith(('\ua616/', '\ua66e/', '.git/')):
				r = (repo_root, target, rel)
	return r
def _unique_fn_map(pairs: list[tuple[str, ast.AST]], effective_lines: set[int]) -> dict[str, dict]:
	seen: dict[str, int] = {}
	result: dict[str, dict] = {}
	for qname, node in pairs:
		idx = seen.get(qname, 0) + 1
		seen[qname] = idx
		key = qname if 1 == idx else f'{qname}#{idx}'
		result[key] = _function_metrics(node, effective_lines)
	return result
def analyze_python_source(source: str) -> dict:
	try:
		tree = ast.parse(source or '')
	except SyntaxError as exc:
		r = {'file_sloc': 0, 'functions': {}, 'semicolon_lines': [], 'syntax_error': str(exc)}
	else:
		code_lines, semis = _code_lines_and_semicolons(source or '')
		effective = code_lines - _collect_excluded_lines(tree)
		funcs = _unique_fn_map(_iter_functions(tree), effective)
		r = {'file_sloc': len(effective), 'functions': funcs, 'semicolon_lines': semis, 'syntax_error': None}
	return r
def check_python_size_violations(path: str | Path, source: str, *, baseline_source: str | None=None) -> list[str]:
	cur = analyze_python_source(source)
	# 2026-11-24
	# "Enforce transaction-boundary Python size ratchet and symbol integrity checks":
	# https://github.com/dmitry-ai/harness/issues/186
	rel_label = Path(path).as_posix()
	if cur['syntax_error']:
		r = [f'CODE-4: Python syntax error in {rel_label}: {cur["syntax_error"]}']
	else:
		raw_base = analyze_python_source(baseline_source) if None is not baseline_source else None
		base = raw_base if (None is not raw_base and None is raw_base['syntax_error']) else None
		file_lim, func_lim, mccabe_lim = _limits_for_path(path)
		errs = _check_file_and_semis(rel_label, cur, base, file_lim)
		errs.extend(_check_function_limits(rel_label, cur['functions'], base['functions'] if base else {}, func_lim, mccabe_lim))
		r = errs
	return r
def evaluate_pre_tool_use_code_size(name: str, args: dict, payload: dict) -> str | None:
	r = None
	if name in ('write_file', 'edit_file'):
		resolved = _resolve_python_target(args, payload)
		if None is not resolved:
			repo_root, target, rel = resolved
			_, new_text, _, _ = _compute_edited_content(name, args, target)
			if None is not new_text:
				# 2026-11-24
				# "Enforce transaction-boundary Python size ratchet and symbol integrity checks":
				# https://github.com/dmitry-ai/harness/issues/186
				base_text = _git_head_text(repo_root, rel)
				if 'edit_file' != name or (not _is_legacy_oversized_baseline(rel, base_text)):
					errs = check_python_size_violations(rel, new_text, baseline_source=base_text)
					if 'write_file' == name and (not errs):
						errs.extend(check_python_integrity(rel, new_text))
					r = '; '.join(errs[:3]) if errs else None
	return r
def verify_staged_code_size_ratchet(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	repo = Path(repo_root).resolve()
	violations: list[str] = []
	for rel in staged_paths or ():
		if not rel.lower().endswith('.py') or rel.casefold().startswith(('\ua616/', '\ua66e/', '.git/')):
			continue
		fpath = repo / rel
		text = _git_index_text(repo, rel) if use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
		if None is not text:
			# 2026-11-24
			# "Enforce transaction-boundary Python size ratchet and symbol integrity checks":
			# https://github.com/dmitry-ai/harness/issues/186
			size_errs = check_python_size_violations(rel, text, baseline_source=_git_head_text(repo, rel))
			violations.extend(size_errs)
			if not any(('syntax' in e.lower() for e in size_errs)):
				violations.extend(check_python_integrity(rel, text))
	return violations
