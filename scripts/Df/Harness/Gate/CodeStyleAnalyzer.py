# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Gate.CodeSizeAnalyzer import CodeSizeAnalyzer
import ast
import io
import tokenize
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class CodeStyleAnalyzer:
	__SCALAR_YODA_TYPES = (type(None), bool, int, float, str)
	__YODA_OPS = (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)
	# @used-by :func:`agent_tools.code_style_gate.analyze_python_style()`
	# @used-by :meth:`Df.Harness.Gate.CodeStyleChecker.CodeStyleChecker.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_analyzers_and_checkers()`
	def __init__(self, source: str) -> None:
		self.__source = source or ''
	# @used-by :meth:`CodeStyleAnalyzer.__unique_return_map()`
	@staticmethod
	def __collect_fn_returns(fn_node: ast.AST) -> int:
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
	# @used-by :meth:`CodeStyleAnalyzer.analyze()`
	@staticmethod
	def __collect_yoda_lines(tree: ast.AST) -> list[int]:
		lines: list[int] = []
		for node in ast.walk(tree):
			if isinstance(node, ast.Compare) and 1 == len(node.ops) and isinstance(node.ops[0], CodeStyleAnalyzer.__YODA_OPS):
				right = node.comparators[0]
				if (not isinstance(node.left, ast.Constant)) and isinstance(right, ast.Constant) and type(right.value) in CodeStyleAnalyzer.__SCALAR_YODA_TYPES:
					lines.append(int(getattr(node, 'lineno', 0)))
		return sorted(lines)
	# @used-by :meth:`CodeStyleAnalyzer.__scan_tokens()`
	@staticmethod
	def __is_unneeded_double_quote(tok_text: str) -> bool:
		body = tok_text.lstrip('rRbBuUfF')
		return 2 <= len(body) and body.startswith('"') and body.endswith('"') and (not body.startswith('"""')) and ('\n' not in body) and ("'" not in body) and ('\\' not in body)
	# @used-by :meth:`CodeStyleAnalyzer.analyze()`
	@staticmethod
	def __scan_tokens(source: str) -> tuple[list[int], list[int], list[int]]:
		str_lines: set[int] = set()
		space_indents: list[int] = []
		dbl_quotes: list[int] = []
		try:
			for tok in tokenize.generate_tokens(io.StringIO(source).readline):
				if tokenize.STRING == tok.type:
					str_lines.update(range(tok.start[0], tok.end[0] + 1))
					if CodeStyleAnalyzer.__is_unneeded_double_quote(tok.string):
						dbl_quotes.append(tok.start[0])
				elif tokenize.INDENT == tok.type and ' ' in tok.string:
					space_indents.append(tok.start[0])
		except (tokenize.TokenError, IndentationError):
			pass
		blanks = [idx for idx, line in enumerate(source.splitlines(), 1) if '' == line.strip() and idx not in str_lines]
		return (blanks, space_indents, dbl_quotes)
	# @used-by :meth:`CodeStyleAnalyzer.analyze()`
	@staticmethod
	def __unique_return_map(tree: ast.AST) -> dict[str, int]:
		seen: dict[str, int] = {}
		out: dict[str, int] = {}
		for qname, node in CodeSizeAnalyzer.iter_functions(tree):
			idx = seen.get(qname, 0) + 1
			seen[qname] = idx
			key = qname if 1 == idx else f'{qname}#{idx}'
			out[key] = CodeStyleAnalyzer.__collect_fn_returns(node)
		return out
	# @used-by :func:`agent_tools.code_style_gate.analyze_python_style()`
	# @used-by :meth:`Df.Harness.Gate.CodeStyleChecker.CodeStyleChecker.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_analyzers_and_checkers()`
	def analyze(self) -> dict:
		try:
			tree = ast.parse(self.__source)
		except SyntaxError:
			r = {'syntax_error': True, 'blanks': [], 'space_indents': [], 'double_quotes': [], 'yoda': [], 'returns': {}}
		else:
			blanks, space_indents, dbl_quotes = CodeStyleAnalyzer.__scan_tokens(self.__source)
			r = {'syntax_error': False, 'blanks': blanks, 'space_indents': space_indents, 'double_quotes': dbl_quotes, 'yoda': CodeStyleAnalyzer.__collect_yoda_lines(tree), 'returns': CodeStyleAnalyzer.__unique_return_map(tree)}
		return r
