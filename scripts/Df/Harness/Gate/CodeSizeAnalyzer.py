# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.git import df_git_root
from agent_tools.shell_audit import normalize_host_path
import ast
import io
import tokenize
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class CodeSizeAnalyzer:
	__BRANCH_NODES = (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler)
	__TRIVIAL_TOKENS = frozenset({tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT, tokenize.ENDMARKER, tokenize.ENCODING})
	# @used-by :func:`agent_tools.code_size_gate.analyze_python_source()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeChecker.CodeSizeChecker.check()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeChecker.CodeSizeChecker.is_legacy_oversized_baseline()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_gate_classes_enforce_python_and_pretool_checks()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_analyzers_and_checkers()`
	def __init__(self, source: str) -> None:
		self.__source = source or ''
	# @used-by :meth:`CodeSizeAnalyzer.__collect_excluded_lines()`
	@staticmethod
	def __add_override_decorator_lines(node: ast.AST, excluded: set[int]) -> None:
		for dec in getattr(node, 'decorator_list', ()):
			if (isinstance(dec, ast.Name) and 'override' == dec.id) or (isinstance(dec, ast.Attribute) and 'override' == dec.attr and isinstance(dec.value, ast.Name) and 'typing' == dec.value.id):
				excluded.update(range(dec.lineno, (getattr(dec, 'end_lineno', None) or dec.lineno) + 1))
	# @used-by :meth:`CodeSizeAnalyzer.analyze()`
	@staticmethod
	def __code_lines_and_semicolons(source: str) -> tuple[set[int], list[int]]:
		code_lines: set[int] = set()
		per_line: dict[int, list[tuple[int, str]]] = {}
		try:
			for tok in tokenize.generate_tokens(io.StringIO(source).readline):
				if tok.type not in CodeSizeAnalyzer.__TRIVIAL_TOKENS and tok.string.strip():
					ln = tok.start[0]
					code_lines.add(ln)
					per_line.setdefault(ln, []).append((tok.type, tok.string))
		except (tokenize.TokenError, IndentationError):
			pass
		semis = [ln for ln, toks in sorted(per_line.items()) if any((tokenize.OP == t and ';' == s and idx + 1 < len(toks) for idx, (t, s) in enumerate(toks)))]
		return (code_lines, semis)
	# @used-by :meth:`CodeSizeAnalyzer.analyze()`
	@staticmethod
	def __collect_excluded_lines(tree: ast.AST) -> set[int]:
		excluded: set[int] = set()
		for node in ast.walk(tree):
			if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
				if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
					excluded.update(range(node.body[0].lineno, (node.body[0].end_lineno or node.body[0].lineno) + 1))
				CodeSizeAnalyzer.__add_override_decorator_lines(node, excluded)
			elif CodeSizeAnalyzer.__is_override_import(node):
				excluded.update(range(node.lineno, (getattr(node, 'end_lineno', None) or node.lineno) + 1))
			elif isinstance(node, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
				end_ln = getattr(node, 'end_lineno', None) or node.lineno
				if end_ln > node.lineno and CodeSizeAnalyzer.__is_constant_expr(node):
					excluded.update(range(node.lineno + 1, end_ln + 1))
		return excluded
	# @used-by :meth:`CodeSizeAnalyzer.__function_metrics()`
	@staticmethod
	def __count_mccabe_in_node(node: ast.AST) -> int:
		count = 1 if isinstance(node, CodeSizeAnalyzer.__BRANCH_NODES) else 0
		if isinstance(node, ast.comprehension):
			count += len(node.ifs)
		elif hasattr(ast, 'match_case') and isinstance(node, ast.match_case):
			pat = getattr(node, 'pattern', None)
			if not (hasattr(ast, 'MatchAs') and isinstance(pat, ast.MatchAs) and None is pat.pattern and None is pat.name):
				count += 1
		for child in ast.iter_child_nodes(node):
			if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
				count += CodeSizeAnalyzer.__count_mccabe_in_node(child)
		return count
	# @used-by :meth:`CodeSizeAnalyzer.__unique_fn_map()`
	@staticmethod
	def __function_metrics(fn_node: ast.AST, effective_lines: set[int]) -> dict:
		start = fn_node.lineno
		end = getattr(fn_node, 'end_lineno', None) or start
		nested_lines: set[int] = set()
		for child in ast.iter_child_nodes(fn_node):
			for sub in ast.walk(child):
				if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
					sub_end = getattr(sub, 'end_lineno', None) or sub.lineno
					nested_lines.update(range(sub.lineno, sub_end + 1))
		own_lines = [ln for ln in effective_lines if start <= ln <= end and ln not in nested_lines]
		complexity = 1 + sum((CodeSizeAnalyzer.__count_mccabe_in_node(stmt) for stmt in getattr(fn_node, 'body', ())))
		return {'sloc': len(own_lines), 'mccabe': complexity, 'lineno': start}
	# @used-by :meth:`CodeSizeAnalyzer.__collect_excluded_lines()`
	@staticmethod
	def __is_constant_expr(node: ast.AST) -> bool:
		if isinstance(node, ast.Constant):
			r = True
		elif isinstance(node, ast.UnaryOp):
			r = CodeSizeAnalyzer.__is_constant_expr(node.operand)
		elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
			r = all((CodeSizeAnalyzer.__is_constant_expr(el) for el in node.elts))
		elif isinstance(node, ast.Dict):
			r = all(((None is k or CodeSizeAnalyzer.__is_constant_expr(k)) and CodeSizeAnalyzer.__is_constant_expr(v) for k, v in zip(node.keys, node.values)))
		else:
			r = False
		return r
	# @used-by :meth:`CodeSizeAnalyzer.__collect_excluded_lines()`
	@staticmethod
	def __is_override_import(node: ast.AST) -> bool:
		return isinstance(node, ast.ImportFrom) and 'typing' == node.module and 1 == len(node.names) and 'override' == node.names[0].name and None is node.names[0].asname
	# @used-by :meth:`CodeSizeAnalyzer.analyze()`
	@staticmethod
	def __unique_fn_map(pairs: list[tuple[str, ast.AST]], effective_lines: set[int]) -> dict[str, dict]:
		seen: dict[str, int] = {}
		result: dict[str, dict] = {}
		for qname, node in pairs:
			idx = seen.get(qname, 0) + 1
			seen[qname] = idx
			key = qname if 1 == idx else f'{qname}#{idx}'
			result[key] = CodeSizeAnalyzer.__function_metrics(node, effective_lines)
		return result
	# @used-by :func:`agent_tools.code_size_gate._iter_functions()`
	# @used-by :meth:`CodeSizeAnalyzer.analyze()`
	# @used-by :meth:`Df.Harness.Gate.CodeStyleAnalyzer.CodeStyleAnalyzer.__unique_return_map()`
	@staticmethod
	def iter_functions(node: ast.AST, prefix: str='') -> list[tuple[str, ast.AST]]:
		out: list[tuple[str, ast.AST]] = []
		for child in ast.iter_child_nodes(node):
			if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
				qname = f'{prefix}.{child.name}' if prefix else child.name
				out.append((qname, child))
				out.extend(CodeSizeAnalyzer.iter_functions(child, qname))
			elif isinstance(child, ast.ClassDef):
				cname = f'{prefix}.{child.name}' if prefix else child.name
				out.extend(CodeSizeAnalyzer.iter_functions(child, cname))
		return out
	# @used-by :func:`agent_tools.code_size_gate._resolve_python_target()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizePreToolGate.CodeSizePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.CodeStylePreToolGate.CodeStylePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygienePreToolGate.SubprocessHygienePreToolGate.check()`
	@staticmethod
	def resolve_python_target(args: dict, payload: dict) -> tuple[Path, Path, str] | None:
		r = None
		raw_p = str(args.get('Path') or '').strip()
		if raw_p and raw_p.lower().endswith('.py'):
			cwd_raw = str(payload.get('cwd') or '').strip()
			cwd = Path(cwd_raw).resolve() if cwd_raw else None
			cand = normalize_host_path(raw_p)
			target = cand.resolve() if cand.is_absolute() else ((cwd / cand).resolve() if cwd else cand.resolve())
			repo_root = df_git_root(target)
			if None is not repo_root:
				rel = target.relative_to(repo_root).as_posix()
				if not rel.casefold().startswith(('\ua616/', '\ua66e/', '.git/')):
					r = (repo_root, target, rel)
		return r
	# @used-by :func:`agent_tools.code_size_gate.analyze_python_source()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeChecker.CodeSizeChecker.check()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeChecker.CodeSizeChecker.is_legacy_oversized_baseline()`
	# @used-by :meth:`test_df_harness_s11_wave2b.DfHarnessS11Wave2bTests.test_gate_classes_enforce_python_and_pretool_checks()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_analyzers_and_checkers()`
	def analyze(self) -> dict:
		try:
			tree = ast.parse(self.__source)
		except SyntaxError as exc:
			r = {'file_sloc': 0, 'functions': {}, 'semicolon_lines': [], 'syntax_error': str(exc)}
		else:
			code_lines, semis = CodeSizeAnalyzer.__code_lines_and_semicolons(self.__source)
			effective = code_lines - CodeSizeAnalyzer.__collect_excluded_lines(tree)
			funcs = CodeSizeAnalyzer.__unique_fn_map(CodeSizeAnalyzer.iter_functions(tree), effective)
			r = {'file_sloc': len(effective), 'functions': funcs, 'semicolon_lines': semis, 'syntax_error': None}
		return r
