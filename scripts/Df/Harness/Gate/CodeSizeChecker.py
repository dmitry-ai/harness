# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Gate.CodeSizeAnalyzer import CodeSizeAnalyzer
from Df.Harness.Tdd.CodeClassifier import CodeClassifier
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class CodeSizeChecker:
	PROD_FILE_SLOC_LIMIT = 300
	PROD_FUNC_SLOC_LIMIT = 20
	PROD_MCCABE_LIMIT = 8
	TEST_FILE_SLOC_LIMIT = 600
	TEST_FUNC_SLOC_LIMIT = 40
	TEST_MCCABE_LIMIT = 12
	# @used-by :func:`agent_tools.code_size_gate.check_python_size_violations()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizePreToolGate.CodeSizePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeStagedGate.CodeSizeStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.PythonIntegrity.PythonIntegrity.verify_touched()`
	# @used-by :meth:`Df.Harness.Gate.PythonIntegrity.PythonIntegrity.verify_worktree()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_analyzers_and_checkers()`
	def __init__(self, path: str | Path, source: str, *, baseline_source: str | None=None) -> None:
		self.__path = path
		self.__source = source
		self.__baseline_source = baseline_source
	# @used-by :meth:`CodeSizeChecker.check()`
	@staticmethod
	def __check_file_and_semis(rel_label: str, cur: dict, base: dict | None, file_lim: int) -> list[str]:
		errs: list[str] = []
		base_sloc = base['file_sloc'] if base else 0
		eff_file = max(file_lim, base_sloc) if base_sloc > file_lim else file_lim
		cur_sloc = cur['file_sloc']
		if cur_sloc > eff_file:
			kind = 'legacy ratchet' if eff_file > file_lim else 'limit'
			errs.append(f'CODE-4: File {rel_label} has {cur_sloc} executable SLOC, exceeding {kind} ({eff_file}); split new logic into a separate module')
		base_semi = len(base['semicolon_lines']) if base else 0
		semis = cur['semicolon_lines']
		if len(semis) > base_semi:
			errs.append(f'CODE-4: Anti-gaming semicolon multi-statement line(s) detected in {rel_label} at line(s) {semis[:5]}; write one statement per line')
		return errs
	# @used-by :meth:`CodeSizeChecker.check()`
	@staticmethod
	def __check_function_limits(rel_label: str, cur_funcs: dict, base_funcs: dict, func_lim: int, mccabe_lim: int) -> list[str]:
		errs: list[str] = []
		for qname, info in cur_funcs.items():
			binfo = base_funcs.get(qname)
			eff_sloc = max(func_lim, binfo['sloc']) if binfo and binfo['sloc'] > func_lim else func_lim
			eff_mc = max(mccabe_lim, binfo['mccabe']) if binfo and binfo['mccabe'] > mccabe_lim else mccabe_lim
			f_sloc, f_mc = (info['sloc'], info['mccabe'])
			if f_sloc > eff_sloc:
				kind = 'legacy ratchet' if eff_sloc > func_lim else 'limit'
				errs.append(f'CODE-4: Function {rel_label}:{qname} has {f_sloc} executable SLOC, exceeding {kind} ({eff_sloc}); decompose into compact helpers')
			if f_mc > eff_mc:
				kind = 'legacy ratchet' if eff_mc > mccabe_lim else 'limit'
				errs.append(f'CODE-4: Function {rel_label}:{qname} has McCabe complexity {f_mc}, exceeding {kind} ({eff_mc}); simplify branching')
		return errs
	# @used-by :meth:`CodeSizeChecker.check()`
	# @used-by :meth:`CodeSizeChecker.is_legacy_oversized_baseline()`
	@staticmethod
	def __limits_for_path(path: str | Path) -> tuple[int, int, int]:
		return (CodeSizeChecker.TEST_FILE_SLOC_LIMIT, CodeSizeChecker.TEST_FUNC_SLOC_LIMIT, CodeSizeChecker.TEST_MCCABE_LIMIT) if CodeClassifier.is_test_file(path) else (CodeSizeChecker.PROD_FILE_SLOC_LIMIT, CodeSizeChecker.PROD_FUNC_SLOC_LIMIT, CodeSizeChecker.PROD_MCCABE_LIMIT)
	# @used-by :meth:`Df.Harness.Gate.CodeSizePreToolGate.CodeSizePreToolGate.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_analyzers_and_checkers()`
	@staticmethod
	def is_legacy_oversized_baseline(path: str | Path, baseline_source: str | None) -> bool:
		r = False
		if None is not baseline_source:
			base = CodeSizeAnalyzer(baseline_source).analyze()
			if None is base['syntax_error']:
				file_lim, func_lim, mccabe_lim = CodeSizeChecker.__limits_for_path(path)
				r = base['file_sloc'] > file_lim or any((f['sloc'] > func_lim or f['mccabe'] > mccabe_lim for f in base['functions'].values()))
		return r
	# @used-by :func:`agent_tools.code_size_gate.check_python_size_violations()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizePreToolGate.CodeSizePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.CodeSizeStagedGate.CodeSizeStagedGate.verify()`
	# @used-by :meth:`Df.Harness.Gate.PythonIntegrity.PythonIntegrity.verify_touched()`
	# @used-by :meth:`Df.Harness.Gate.PythonIntegrity.PythonIntegrity.verify_worktree()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_analyzers_and_checkers()`
	def check(self) -> list[str]:
		cur = CodeSizeAnalyzer(self.__source).analyze()
		rel_label = Path(self.__path).as_posix()
		syn_err = cur['syntax_error']
		if syn_err:
			r = [f'CODE-4: Python syntax error in {rel_label}: {syn_err}']
		else:
			raw_base = CodeSizeAnalyzer(self.__baseline_source).analyze() if None is not self.__baseline_source else None
			base = raw_base if (None is not raw_base and None is raw_base['syntax_error']) else None
			file_lim, func_lim, mccabe_lim = CodeSizeChecker.__limits_for_path(self.__path)
			errs = CodeSizeChecker.__check_file_and_semis(rel_label, cur, base, file_lim)
			errs.extend(CodeSizeChecker.__check_function_limits(rel_label, cur['functions'], base['functions'] if base else {}, func_lim, mccabe_lim))
			r = errs
		return r
