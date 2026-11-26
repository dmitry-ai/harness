# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Gate.CodeStyleAnalyzer import CodeStyleAnalyzer
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class CodeStyleChecker:
	__COUNT_RULES = (
		('blanks', 'Blank line(s)', 'remove blank lines from Python source'),
		('yoda', 'Non-Yoda comparison(s)', 'place the constant or literal on the left (e.g., None is x, 200 == status)'),
		('double_quotes', 'Unnecessary double-quoted string(s)', 'use single quotes by default'),
	)
	# @used-by :func:`agent_tools.code_style_gate.check_python_style_violations()`
	# @used-by :meth:`Df.Harness.Gate.CodeStylePreToolGate.CodeStylePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.CodeStyleStagedGate.CodeStyleStagedGate.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_analyzers_and_checkers()`
	def __init__(self, path: str | Path, source: str, *, baseline_source: str | None=None) -> None:
		self.__path = path
		self.__source = source
		self.__baseline_source = baseline_source
	# @used-by :meth:`CodeStyleChecker.check()`
	@staticmethod
	def __check_function_returns(rel_label: str, cur_ret: dict[str, int], base_ret: dict[str, int]) -> list[str]:
		errs: list[str] = []
		for qname, cnt in cur_ret.items():
			lim = max(1, base_ret.get(qname, 1))
			if lim < cnt:
				errs.append(f'CODE-1: Function {rel_label}:{qname} has {cnt} return statements (limit {lim}); assign result to `r` and use a single return point')
		return errs
	# @used-by :meth:`CodeStyleChecker.check()`
	@staticmethod
	def __collect_count_style_errors(rel_label: str, cur: dict, base: dict | None) -> list[str]:
		errs: list[str] = []
		for key, label, hint in CodeStyleChecker.__COUNT_RULES:
			base_cnt = len(base[key]) if None is not base else 0
			if base_cnt < len(cur[key]):
				errs.append(f'CODE-1: {label} in {rel_label} at line(s) {cur[key][:5]}; {hint}')
		sp_lines = cur['space_indents']
		if sp_lines and (None is base or 0 == len(base['space_indents'])):
			errs.append(f'CODE-1: Space indentation in {rel_label} at line(s) {sp_lines[:5]}; indent new Python code with tab characters (\\t)')
		return errs
	# @used-by :func:`agent_tools.code_style_gate.check_python_style_violations()`
	# @used-by :meth:`Df.Harness.Gate.CodeStylePreToolGate.CodeStylePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.CodeStyleStagedGate.CodeStyleStagedGate.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_analyzers_and_checkers()`
	def check(self) -> list[str]:
		cur = CodeStyleAnalyzer(self.__source).analyze()
		errs: list[str] = []
		if not cur['syntax_error']:
			rel_label = Path(self.__path).as_posix()
			raw_base = CodeStyleAnalyzer(self.__baseline_source).analyze() if None is not self.__baseline_source else None
			base = raw_base if None is not raw_base and (not raw_base['syntax_error']) else None
			errs.extend(CodeStyleChecker.__collect_count_style_errors(rel_label, cur, base))
			errs.extend(CodeStyleChecker.__check_function_returns(rel_label, cur['returns'], base['returns'] if None is not base else {}))
		return errs
