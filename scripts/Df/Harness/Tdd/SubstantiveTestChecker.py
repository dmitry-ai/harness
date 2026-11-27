# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Tdd.CodeClassifier import CodeClassifier
import ast
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
# @used-by :mod:`agent_tools.tdd.substantive`
class SubstantiveTestChecker:
	ASSERTION_LINE_RE = re.compile(
		r'(?:\bassert\s+|\bassert\s*\('
		r'|\bself\.assert[A-Z]\w*\s*\('
		r'|\b\w+\.assert_(?:called|not_called|any_call|has_calls)\w*\s*\('
		r'|\bpytest\.raises\s*\('
		r'|\bassertRaises(?:Regex)?\s*\('
		r'|\bexpect\s*\('
		r'|\.(?:toEqual|toBe|toThrow|toContain|toMatch|toStrictEqual|toHaveBeenCalled|toHaveLength|rejects|resolves)\b'
		r'|\bassert\.(?:strictEqual|deepStrictEqual|deepEqual|equal|ok|throws|rejects|match|fail)\s*\('
		r'|\bAssert\.\w+\s*\('
		r'|\bAssert::\w+\s*\('
		r'|\b[A-Za-z_]\w*\.assert(?:Equals|True|False|Null|NotNull|Throws|Same|NotSame|ArrayEquals)\s*\('
		r'|\bthrow\s+new\s+AssertionError\b'
		r'|\$this->assert\w+\s*\('
		r'|\|\s*Should\s+-'
		r'|\bAssert-\w+\b'
		r'|\bt\.(?:Error|Errorf|Fatal|Fatalf|Fail|FailNow)\s*\('
		r'|\b(?:assert|require)\.\w+\s*\('
		r'|\b(?:debug_)?assert(?:_eq|_ne)?!\s*\('
		r'|\bfail\s*\()'
	)
	CODE_LIT_EXT_RE = re.compile(rf'(?i)[A-Za-z0-9_./\\-]+\.(?:{CodeClassifier.CODE_SUFFIX_ALT})(?=[\'"`\s,)\]]|$)')
	SOURCE_TEXT_NONPY_READ_RE = re.compile(
		rf'(?i)(?:readFileSync|readFile|ReadAllText|ReadAllLines|file_get_contents|Get-Content|os\.ReadFile|read_to_string|readString|\.read_text|\.read_bytes|inspect\.getsource)\s*\([^)\n]*[\'"]([^\'"\n]+\.(?:{CodeClassifier.CODE_SUFFIX_ALT}))[\'"]'
	)
	TEMP_PATH_HINT_RE = re.compile(
		r'(?i)(?:^|[/\\._-])(?:tmp|temp|tmpdir|tmp_path|sandbox|fixture|fixtures|sample|samples|mock|mocks|generated|out|output|dist|build|work|td|proj|project|repo|code_repo|scratch|harness_hook_runner)(?:$|[/\\._-])'
	)
	__NONPY_TEMP_RE = re.compile(r'(?i)\b(?:tmp|temp|tmpdir|tmp_path|os\.tmpdir|mkdtemp|self\.root|TemporaryDirectory)\b')
	__REPO_ANCHOR_ATTRS = frozenset({'HARNESS_CODE', 'PRIMARY', 'PRIMARY_AGENTS_DIR'})
	__REPO_ANCHOR_NAMES = frozenset({'HARNESS_CODE', 'PRIMARY', 'PRIMARY_AGENTS_DIR', 'REPO_ROOT', 'SCRIPTS', 'SCRIPT_DIR', '__file__'})
	# @used-by :func:`agent_tools.tdd.substantive.is_substantive_test_content()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_test_write()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__verify_staged_test_file()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	def __init__(self, path: str | Path, content: str='') -> None:
		self.__path = path
		self.__content = content
	# @used-by :func:`agent_tools.tdd.substantive.is_substantive_test_content()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_test_write()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__verify_staged_test_file()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd.DfHarnessS11Wave2bTddTests.test_tdd_enforcement_evaluator_events_and_guards()`
	def check_content(self) -> tuple[bool, str | None]:
		p = Path(str(self.__path))
		content = self.__content
		if not isinstance(content, str) or not content.strip():
			r = (False, f'Test file {p.name} is empty; write concrete behavioral assertions.')
		elif p.name.lower() in CodeClassifier.TEST_HELPER_FILENAMES:
			r = (True, None)
		else:
			non_comment = [ln.strip() for ln in content.splitlines() if ln.strip() and (not ln.strip().startswith(('#', '//', '/*', '*', '--', 'REM ', 'rem ')))]
			if not non_comment:
				r = (False, f'Test file {p.name} contains only comments and no executable tests.')
			else:
				has_assert = bool(SubstantiveTestChecker.ASSERTION_LINE_RE.search(content)) or ('.py' == p.suffix.lower() and SubstantiveTestChecker.__py_has_ast_assertion(content))
				r = (True, None) if has_assert else (False, f'Test file {p.name} contains no verifiable assertions or expectations (assertionless test stubs are prohibited).')
		return r
	# @used-by :meth:`SubstantiveTestChecker.__collect_repo_anchor_vars()`
	# @used-by :meth:`SubstantiveTestChecker.__collect_var_code_lits()`
	@staticmethod
	def __assign_targets_and_value(node: ast.AST) -> tuple[list[str], ast.AST] | None:
		r = None
		if isinstance(node, ast.Assign):
			r = ([t.id for t in node.targets if isinstance(t, ast.Name)], node.value)
		elif isinstance(node, ast.AnnAssign) and None is not node.value and isinstance(node.target, ast.Name):
			r = ([node.target.id], node.value)
		return r
	# @used-by :meth:`SubstantiveTestChecker.__eval_py_call_node()`
	@staticmethod
	def __check_direct_read_call(node: ast.Call, var_code_lits: dict[str, str], repo_anchor_vars: set[str], p_name: str, lineno: int | None) -> str | None:
		r = None
		target_expr = SubstantiveTestChecker.__read_or_open_target(node)
		if None is not target_expr:
			lit = SubstantiveTestChecker.ast_expr_contains_code_literal(target_expr)
			if None is lit and isinstance(target_expr, ast.Name) and target_expr.id in var_code_lits:
				lit = var_code_lits[target_expr.id]
			if None is not lit and ((not SubstantiveTestChecker.ast_expr_uses_temp_base(target_expr)) or SubstantiveTestChecker.__has_repo_anchor(target_expr, repo_anchor_vars)):
				r = f'Behavioral test violation in {p_name}:{lineno}: test reads production source file "{lit}" as text instead of executing its behavior.'
		return r
	# @used-by :meth:`SubstantiveTestChecker.__eval_py_call_node()`
	@staticmethod
	def __check_wrapper_call(node: ast.Call, read_wrappers: dict[str, set[int]], repo_anchor_vars: set[str], p_name: str, lineno: int | None) -> str | None:
		r = None
		fn = node.func
		fn_name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
		if fn_name and fn_name in read_wrappers:
			for p_idx in read_wrappers[fn_name]:
				if p_idx < len(node.args):
					arg_expr = node.args[p_idx]
					w_lit = SubstantiveTestChecker.ast_expr_contains_code_literal(arg_expr)
					if None is not w_lit and ((not SubstantiveTestChecker.ast_expr_uses_temp_base(arg_expr)) or SubstantiveTestChecker.__has_repo_anchor(arg_expr, repo_anchor_vars)):
						r = f'Behavioral test violation in {p_name}:{lineno}: helper "{fn_name}" reads production source file "{w_lit}" as text instead of executing its behavior.'
						break
		return r
	# @used-by :meth:`SubstantiveTestChecker.__collect_read_wrappers()`
	@staticmethod
	def __collect_read_wrapper_params(fn_node: ast.AST, repo_anchor_vars: set[str]) -> set[int]:
		param_names = [a.arg for a in fn_node.args.args]
		r: set[int] = set()
		for sub in ast.walk(fn_node):
			if isinstance(sub, ast.Call):
				s_tgt = SubstantiveTestChecker.__read_or_open_target(sub)
				if None is not s_tgt and ((not SubstantiveTestChecker.ast_expr_uses_temp_base(s_tgt)) or SubstantiveTestChecker.__has_repo_anchor(s_tgt, repo_anchor_vars)):
					used_names = {n.id for n in ast.walk(s_tgt) if isinstance(n, ast.Name)}
					for p_idx, p_name in enumerate(param_names):
						if p_name in used_names:
							r.add(p_idx)
		return r
	# @used-by :meth:`SubstantiveTestChecker.__py_source_text_issues()`
	@staticmethod
	def __collect_read_wrappers(tree: ast.AST, repo_anchor_vars: set[str]) -> dict[str, set[int]]:
		r: dict[str, set[int]] = {}
		for node in ast.walk(tree):
			if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
				matched = SubstantiveTestChecker.__collect_read_wrapper_params(node, repo_anchor_vars)
				if matched:
					r[node.name] = matched
		return r
	# @used-by :meth:`SubstantiveTestChecker.__py_source_text_issues()`
	@staticmethod
	def __collect_repo_anchor_vars(tree: ast.AST) -> set[str]:
		r: set[str] = set()
		for node in ast.walk(tree):
			pair = SubstantiveTestChecker.__assign_targets_and_value(node)
			if None is not pair and SubstantiveTestChecker.ast_expr_uses_repo_anchor(pair[1]):
				r.update(pair[0])
		return r
	# @used-by :meth:`SubstantiveTestChecker.__py_source_text_issues()`
	@staticmethod
	def __collect_var_code_lits(tree: ast.AST, repo_anchor_vars: set[str]) -> dict[str, str]:
		r: dict[str, str] = {}
		for node in ast.walk(tree):
			pair = SubstantiveTestChecker.__assign_targets_and_value(node)
			if None is not pair:
				lit_v = SubstantiveTestChecker.ast_expr_contains_code_literal(pair[1])
				if None is not lit_v and ((not SubstantiveTestChecker.ast_expr_uses_temp_base(pair[1])) or SubstantiveTestChecker.__has_repo_anchor(pair[1], repo_anchor_vars)):
					for name in pair[0]:
						r[name] = lit_v
		return r
	# @used-by :meth:`SubstantiveTestChecker.__py_source_text_issues()`
	@staticmethod
	def __eval_py_call_node(node: ast.Call, p_name: str, var_code_lits: dict[str, str], read_wrappers: dict[str, set[int]], repo_anchor_vars: set[str]) -> list[str]:
		r: list[str] = []
		lineno = getattr(node, 'lineno', None)
		fn = node.func
		if isinstance(fn, ast.Attribute) and fn.attr in ('getsource', 'getsourcelines'):
			r.append(f'Behavioral test violation in {p_name}:{lineno}: inspect.{fn.attr}() reads source text instead of testing runtime behavior.')
		else:
			w_err = SubstantiveTestChecker.__check_wrapper_call(node, read_wrappers, repo_anchor_vars, p_name, lineno)
			if None is not w_err:
				r.append(w_err)
			d_err = SubstantiveTestChecker.__check_direct_read_call(node, var_code_lits, repo_anchor_vars, p_name, lineno)
			if None is not d_err:
				r.append(d_err)
		return r
	# @used-by :meth:`SubstantiveTestChecker.__check_direct_read_call()`
	# @used-by :meth:`SubstantiveTestChecker.__check_wrapper_call()`
	# @used-by :meth:`SubstantiveTestChecker.__collect_read_wrapper_params()`
	# @used-by :meth:`SubstantiveTestChecker.__collect_var_code_lits()`
	@staticmethod
	def __has_repo_anchor(expr: ast.AST, repo_anchor_vars: set[str]) -> bool:
		return SubstantiveTestChecker.ast_expr_uses_repo_anchor(expr) or any((isinstance(sub, ast.Name) and sub.id in repo_anchor_vars for sub in ast.walk(expr)))
	# @used-by :meth:`SubstantiveTestChecker.source_text_assertion_issues()`
	@staticmethod
	def __nonpy_source_text_issues(p_name: str, added_lines: list[str] | tuple[str, ...]) -> list[str]:
		r: list[str] = []
		for idx, raw_line in enumerate(added_lines or (), 1):
			line = str(raw_line)
			if re.search(r'\binspect\.getsource(?:lines)?\s*\(', line):
				r.append(f'Behavioral test violation in {p_name} (added line {idx}): inspect.getsource reads source text instead of testing behavior.')
			elif not SubstantiveTestChecker.__NONPY_TEMP_RE.search(line):
				for m in SubstantiveTestChecker.SOURCE_TEXT_NONPY_READ_RE.finditer(line):
					lit = m.group(1)
					if (not CodeClassifier.is_test_file(lit)) and (not SubstantiveTestChecker.TEMP_PATH_HINT_RE.search(lit)):
						r.append(f'Behavioral test violation in {p_name} (added line {idx}): test reads production source file "{lit}" as text instead of executing its behavior.')
		return r
	# @used-by :meth:`SubstantiveTestChecker.check_content()`
	@staticmethod
	def __py_has_ast_assertion(content: str) -> bool:
		r = False
		try:
			tree = ast.parse(content)
			r = any((isinstance(node, ast.Assert) or (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and (node.func.attr.startswith('assert') or node.func.attr in ('raises', 'fail'))) for node in ast.walk(tree)))
		except SyntaxError:
			pass
		return r
	# @used-by :meth:`SubstantiveTestChecker.source_text_assertion_issues()`
	@staticmethod
	def __py_source_text_issues(p_name: str, full_content: str, added_line_numbers: set[int] | None) -> list[str] | None:
		r: list[str] | None = None
		try:
			tree = ast.parse(full_content)
		except SyntaxError:
			tree = None
		if None is not tree:
			repo_anchor_vars = SubstantiveTestChecker.__collect_repo_anchor_vars(tree)
			var_code_lits = SubstantiveTestChecker.__collect_var_code_lits(tree, repo_anchor_vars)
			read_wrappers = SubstantiveTestChecker.__collect_read_wrappers(tree, repo_anchor_vars)
			r = []
			for node in ast.walk(tree):
				if isinstance(node, ast.Call):
					lineno = getattr(node, 'lineno', None)
					if None is added_line_numbers or None is lineno or lineno in added_line_numbers:
						r.extend(SubstantiveTestChecker.__eval_py_call_node(node, p_name, var_code_lits, read_wrappers, repo_anchor_vars))
		return r
	# @used-by :meth:`SubstantiveTestChecker.__check_direct_read_call()`
	# @used-by :meth:`SubstantiveTestChecker.__collect_read_wrapper_params()`
	@staticmethod
	def __read_or_open_target(call: ast.Call) -> ast.AST | None:
		fn = call.func
		is_read = isinstance(fn, ast.Attribute) and fn.attr in ('read_text', 'read_bytes')
		is_open = (isinstance(fn, ast.Name) and 'open' == fn.id) or (isinstance(fn, ast.Attribute) and 'open' == fn.attr)
		if is_read:
			r = fn.value
		elif is_open:
			r = call.args[0] if call.args else None
		else:
			r = None
		return r
	# @used-by :func:`agent_tools.tdd.substantive._ast_expr_contains_code_literal()`
	# @used-by :meth:`SubstantiveTestChecker.__check_direct_read_call()`
	# @used-by :meth:`SubstantiveTestChecker.__check_wrapper_call()`
	# @used-by :meth:`SubstantiveTestChecker.__collect_var_code_lits()`
	@staticmethod
	def ast_expr_contains_code_literal(node: ast.AST) -> str | None:
		r = None
		for sub in ast.walk(node):
			if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
				m = SubstantiveTestChecker.CODE_LIT_EXT_RE.search(sub.value)
				if m and (not CodeClassifier.is_test_file(m.group(0))) and (not SubstantiveTestChecker.TEMP_PATH_HINT_RE.search(m.group(0))):
					r = m.group(0)
					break
		return r
	# @used-by :func:`agent_tools.tdd.substantive._ast_expr_uses_repo_anchor()`
	# @used-by :meth:`SubstantiveTestChecker.__collect_repo_anchor_vars()`
	# @used-by :meth:`SubstantiveTestChecker.__has_repo_anchor()`
	@staticmethod
	def ast_expr_uses_repo_anchor(node: ast.AST) -> bool:
		r = False
		for sub in ast.walk(node):
			if (isinstance(sub, ast.Name) and sub.id in SubstantiveTestChecker.__REPO_ANCHOR_NAMES) or (isinstance(sub, ast.Attribute) and sub.attr in SubstantiveTestChecker.__REPO_ANCHOR_ATTRS):
				r = True
				break
		return r
	# @used-by :func:`agent_tools.tdd.substantive._ast_expr_uses_temp_base()`
	# @used-by :meth:`SubstantiveTestChecker.__check_direct_read_call()`
	# @used-by :meth:`SubstantiveTestChecker.__check_wrapper_call()`
	# @used-by :meth:`SubstantiveTestChecker.__collect_read_wrapper_params()`
	# @used-by :meth:`SubstantiveTestChecker.__collect_var_code_lits()`
	@staticmethod
	def ast_expr_uses_temp_base(node: ast.AST) -> bool:
		r = False
		for sub in ast.walk(node):
			if (isinstance(sub, ast.Name) and SubstantiveTestChecker.TEMP_PATH_HINT_RE.search(sub.id)) or (isinstance(sub, ast.Attribute) and SubstantiveTestChecker.TEMP_PATH_HINT_RE.search(sub.attr)):
				r = True
				break
		return r
	# @used-by :func:`agent_tools.tdd.substantive.source_text_assertion_issues()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_test_write()`
	# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__verify_staged_test_file()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_tdd_exemption_mechanical_ratchet_and_substantive()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tdd_cov2.DfHarnessS11Wave2bTddCov2Tests.test_outcome_service_substantive_and_worktree_scope()`
	@staticmethod
	def source_text_assertion_issues(path: str | Path, added_lines: list[str] | tuple[str, ...], *, full_content: str | None=None, added_line_numbers: set[int] | None=None) -> list[str]:
		p = Path(str(path))
		r: list[str] | None = None
		if '.py' == p.suffix.lower() and isinstance(full_content, str) and full_content.strip():
			r = SubstantiveTestChecker.__py_source_text_issues(p.name, full_content, added_line_numbers)
		if None is r:
			r = SubstantiveTestChecker.__nonpy_source_text_issues(p.name, added_lines)
		return r
