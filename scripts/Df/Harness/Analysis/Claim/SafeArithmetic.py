# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import ast
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class SafeArithmetic:
	# @used-by :func:`agent_tools.claims.evaluate_safe_arithmetic()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.CalculationValidator.CalculationValidator.__compute_expected()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.InlineCalcVerifier.InlineCalcVerifier.__process_match()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def __init__(self, expr: str, env: dict[str, Decimal] | None=None) -> None:
		self.__expr = expr
		self.__env = env or {}
		self.__literals: set[str] = set()
	# @used-by :meth:`SafeArithmetic.__eval_node()`
	def __eval_binop(self, node: ast.BinOp) -> Decimal:
		left, right = (self.__eval_node(node.left), self.__eval_node(node.right))
		if isinstance(node.op, ast.Add):
			r = left + right
		elif isinstance(node.op, ast.Sub):
			r = left - right
		elif isinstance(node.op, ast.Mult):
			r = left * right
		elif isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
			r = self.__eval_divop(node.op, left, right)
		elif isinstance(node.op, ast.Pow):
			if abs(right) > Decimal(10) or right != right.to_integral_value():
				raise ValueError('unsupported exponent')
			r = left ** int(right)
		else:
			raise ValueError('unsupported binop')
		return r
	# @used-by :meth:`SafeArithmetic.__eval_node()`
	def __eval_call(self, node: ast.Call) -> Decimal:
		if not isinstance(node.func, ast.Name) or node.func.id not in {'round', 'abs', 'min', 'max'} or node.keywords:
			raise ValueError('unsupported call')
		args = [self.__eval_node(a) for a in node.args]
		name = node.func.id
		if 'abs' == name and 1 == len(args):
			r = abs(args[0])
		elif 'min' == name and args:
			r = min(args)
		elif 'max' == name and args:
			r = max(args)
		elif 'round' == name and 1 <= len(args) <= 2:
			places = int(args[1]) if 2 == len(args) else 0
			if not 0 <= places <= 12:
				raise ValueError('invalid rounding places')
			r = args[0].quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
		else:
			raise ValueError('unsupported call arity')
		return r
	# @used-by :meth:`SafeArithmetic.__eval_binop()`
	def __eval_divop(self, op: ast.operator, left: Decimal, right: Decimal) -> Decimal:
		if 0 == right:
			raise ZeroDivisionError('modulo by zero' if isinstance(op, ast.Mod) else 'division by zero')
		if isinstance(op, ast.Div):
			r = left / right
		elif isinstance(op, ast.FloorDiv):
			r = left // right
		else:
			r = left % right
		return r
	# @used-by :meth:`SafeArithmetic.__eval_binop()`
	# @used-by :meth:`SafeArithmetic.__eval_call()`
	# @used-by :meth:`SafeArithmetic.evaluate()`
	def __eval_node(self, node: ast.AST) -> Decimal:
		if isinstance(node, ast.Expression):
			r = self.__eval_node(node.body)
		elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and (not isinstance(node.value, bool)):
			val_str = str(node.value)
			self.__literals.add(val_str)
			r = Decimal(val_str)
		elif isinstance(node, ast.Name) and node.id in self.__env:
			r = Decimal(self.__env[node.id])
		elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
			op_v = self.__eval_node(node.operand)
			r = op_v if isinstance(node.op, ast.UAdd) else -op_v
		elif isinstance(node, ast.BinOp):
			r = self.__eval_binop(node)
		elif isinstance(node, ast.Call):
			r = self.__eval_call(node)
		else:
			raise ValueError('unsupported AST node')
		return r
	# @used-by :meth:`SafeArithmetic.evaluate()`
	def __parse(self) -> ast.AST | None:
		norm = re.sub('(?<=\\d)[ \\u00a0\\u202f](?=\\d{3}(?!\\d))', '', self.__expr.strip())
		norm = re.sub('(?<=\\d),(?=\\d{3}(?!\\d))', '', norm).replace('\u2212', '-').replace('\u00d7', '*').replace('\u00f7', '/')
		r: ast.AST | None = None
		for cand in (norm, re.sub('(?<=\\d),(?=\\d)', '.', norm)):
			try:
				parsed = ast.parse(cand, mode='eval')
				if not any((isinstance(n, ast.Tuple) for n in ast.walk(parsed))):
					r = parsed
					break
			except SyntaxError:
				continue
		return r
	# @used-by :func:`agent_tools.claims.evaluate_safe_arithmetic()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.CalculationValidator.CalculationValidator.__compute_expected()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.InlineCalcVerifier.InlineCalcVerifier.__process_match()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_claim_calc_and_comparison_paths()`
	def evaluate(self) -> tuple[Decimal | None, set[str]]:
		r: tuple[Decimal | None, set[str]] = (None, set())
		if isinstance(self.__expr, str) and self.__expr.strip() and 400 >= len(self.__expr):
			tree = self.__parse()
			if None is not tree:
				try:
					with localcontext() as ctx:
						ctx.prec = 50
						res = self.__eval_node(tree)
					if res.is_finite():
						r = (res, set(self.__literals))
				except (ValueError, ZeroDivisionError, InvalidOperation, ArithmeticError, TypeError):
					r = (None, set())
		return r