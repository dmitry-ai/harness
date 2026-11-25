# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add CODE-1 Python style ratchet linter gate in PreToolUse and pre-commit":
# https://github.com/dmitry-ai/harness/issues/243
from __future__ import annotations
from pathlib import Path
import ast
import io
import tokenize
from .code_size_gate import _iter_functions, _resolve_python_target
from .tdd_gate import _compute_edited_content, _git_head_text, _git_index_text
_SCALAR_YODA_TYPES = (type(None), bool, int, float, str)
_YODA_OPS = (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)
_COUNT_RULES = (
	('blanks', 'Blank line(s)', 'remove blank lines from Python source'),
	('yoda', 'Non-Yoda comparison(s)', 'place the constant or literal on the left (e.g., None is x, 200 == status)'),
	('double_quotes', 'Unnecessary double-quoted string(s)', 'use single quotes by default'),
)
def _check_function_returns(rel_label: str, cur_ret: dict[str, int], base_ret: dict[str, int]) -> list[str]:
	errs: list[str] = []
	for qname, cnt in cur_ret.items():
		lim = max(1, base_ret.get(qname, 1))
		if lim < cnt:
			errs.append(f'CODE-1: Function {rel_label}:{qname} has {cnt} return statements (limit {lim}); assign result to `r` and use a single return point')
	return errs
def _collect_count_style_errors(rel_label: str, cur: dict, base: dict | None) -> list[str]:
	errs: list[str] = []
	for key, label, hint in _COUNT_RULES:
		base_cnt = len(base[key]) if None is not base else 0
		if base_cnt < len(cur[key]):
			errs.append(f'CODE-1: {label} in {rel_label} at line(s) {cur[key][:5]}; {hint}')
	if cur['space_indents'] and (None is base or 0 == len(base['space_indents'])):
		errs.append(f'CODE-1: Space indentation in {rel_label} at line(s) {cur["space_indents"][:5]}; indent new Python code with tab characters (\\t)')
	return errs
def _collect_fn_returns(fn_node: ast.AST) -> int:
	returns: list[ast.Return] = []
	is_gen = False
	stack = list(getattr(fn_node, 'body', ()))
	while stack:
		node = stack.pop()
		if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
			continue
		if isinstance(node, (ast.Yield, ast.YieldFrom)):
			is_gen = True
		elif isinstance(node, ast.Return):
			returns.append(node)
		stack.extend(ast.iter_child_nodes(node))
	return sum((0 if is_gen and None is ret.value else 1 for ret in returns))
def _collect_yoda_lines(tree: ast.AST) -> list[int]:
	lines: list[int] = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Compare) and 1 == len(node.ops) and isinstance(node.ops[0], _YODA_OPS):
			right = node.comparators[0]
			if (not isinstance(node.left, ast.Constant)) and isinstance(right, ast.Constant) and type(right.value) in _SCALAR_YODA_TYPES:
				lines.append(int(getattr(node, 'lineno', 0)))
	return sorted(lines)
def _is_unneeded_double_quote(tok_text: str) -> bool:
	body = tok_text.lstrip('rRbBuUfF')
	return 2 <= len(body) and body.startswith('"') and body.endswith('"') and (not body.startswith('"""')) and ('\n' not in body) and ("'" not in body) and ('\\' not in body)
def _scan_tokens(source: str) -> tuple[list[int], list[int], list[int]]:
	str_lines: set[int] = set()
	space_indents: list[int] = []
	dbl_quotes: list[int] = []
	try:
		for tok in tokenize.generate_tokens(io.StringIO(source).readline):
			if tokenize.STRING == tok.type:
				str_lines.update(range(tok.start[0], tok.end[0] + 1))
				if _is_unneeded_double_quote(tok.string):
					dbl_quotes.append(tok.start[0])
			elif tokenize.INDENT == tok.type and ' ' in tok.string:
				space_indents.append(tok.start[0])
	except (tokenize.TokenError, IndentationError):
		pass
	blanks = [idx for idx, line in enumerate(source.splitlines(), 1) if '' == line.strip() and idx not in str_lines]
	return (blanks, space_indents, dbl_quotes)
def _unique_return_map(tree: ast.AST) -> dict[str, int]:
	seen: dict[str, int] = {}
	out: dict[str, int] = {}
	for qname, node in _iter_functions(tree):
		idx = seen.get(qname, 0) + 1
		seen[qname] = idx
		key = qname if 1 == idx else f'{qname}#{idx}'
		out[key] = _collect_fn_returns(node)
	return out
def analyze_python_style(source: str) -> dict:
	try:
		tree = ast.parse(source or '')
	except SyntaxError:
		r = {'syntax_error': True, 'blanks': [], 'space_indents': [], 'double_quotes': [], 'yoda': [], 'returns': {}}
	else:
		blanks, space_indents, dbl_quotes = _scan_tokens(source or '')
		r = {'syntax_error': False, 'blanks': blanks, 'space_indents': space_indents, 'double_quotes': dbl_quotes, 'yoda': _collect_yoda_lines(tree), 'returns': _unique_return_map(tree)}
	return r
def check_python_style_violations(path: str | Path, source: str, *, baseline_source: str | None=None) -> list[str]:
	cur = analyze_python_style(source)
	errs: list[str] = []
	if not cur['syntax_error']:
		rel_label = Path(path).as_posix()
		raw_base = analyze_python_style(baseline_source) if None is not baseline_source else None
		base = raw_base if None is not raw_base and (not raw_base['syntax_error']) else None
		errs.extend(_collect_count_style_errors(rel_label, cur, base))
		errs.extend(_check_function_returns(rel_label, cur['returns'], base['returns'] if None is not base else {}))
	return errs
def evaluate_pre_tool_use_code_style(name: str, args: dict, payload: dict) -> str | None:
	r = None
	if name in ('write_file', 'edit_file'):
		resolved = _resolve_python_target(args, payload)
		if None is not resolved:
			repo_root, target, rel = resolved
			_, new_text, _, _ = _compute_edited_content(name, args, target)
			if None is not new_text:
				errs = check_python_style_violations(rel, new_text, baseline_source=_git_head_text(repo_root, rel))
				r = '; '.join(errs[:3]) if errs else None
	return r
def verify_staged_code_style_ratchet(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	repo = Path(repo_root).resolve()
	violations: list[str] = []
	for rel in staged_paths or ():
		if not rel.lower().endswith('.py') or rel.casefold().startswith(('\ua616/', '\ua66e/', '.git/')):
			continue
		fpath = repo / rel
		text = _git_index_text(repo, rel) if use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
		if None is not text:
			violations.extend(check_python_style_violations(rel, text, baseline_source=_git_head_text(repo, rel)))
	return violations