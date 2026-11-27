# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections import Counter
from pathlib import Path
from Df.Harness.Tdd.CodeClassifier import CodeClassifier
import ast
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class SubprocessHygieneChecker:
	__BLOCKING_FUNCS = frozenset({'call', 'check_call', 'check_output', 'run'})
	__CHECKED_FUNCS = __BLOCKING_FUNCS | frozenset({'Popen'})
	__LAUNCHER_NAME_RE = re.compile(r'(?i)(?:launcher|runner|watchdog|git_shim|hook_runner)')
	# @used-by :func:`agent_tools.subprocess_hygiene_gate.check_subprocess_hygiene_violations()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygienePreToolGate.SubprocessHygienePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygieneStagedGate.SubprocessHygieneStagedGate.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_thin_pretool_shims_and_checkers()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_gate_bulk_size_external_issue_and_subproc()`
	def __init__(self, path: str | Path, source: str, *, baseline_source: str | None=None) -> None:
		self.__path = path
		self.__source = source
		self.__baseline_source = baseline_source
	# @used-by :meth:`SubprocessHygieneChecker.__scan_source_findings()`
	@staticmethod
	def __call_violations(call: ast.Call, fn_name: str, rel_label: str) -> list[tuple[tuple[str, str, str], str]]:
		out: list[tuple[tuple[str, str, str], str]] = []
		sig = ast.unparse(call)
		lineno = getattr(call, 'lineno', 0)
		if not SubprocessHygieneChecker.__kw_has_non_none(call, ('stdin', 'input')):
			out.append(((fn_name, 'stdin', sig), f'SUBPROCESS-HYGIENE: {rel_label}:{lineno} calls subprocess.{fn_name}() without stdin=subprocess.DEVNULL (or input=...); inherited open stdin pipes can deadlock background runs.'))
		if fn_name in SubprocessHygieneChecker.__BLOCKING_FUNCS and (not SubprocessHygieneChecker.__kw_has_non_none(call, ('timeout',))):
			out.append(((fn_name, 'timeout', sig), f'SUBPROCESS-HYGIENE: {rel_label}:{lineno} calls subprocess.{fn_name}() without timeout=...; unbounded subprocess calls can hang tests or launchers indefinitely.'))
		return out
	# @used-by :meth:`SubprocessHygieneChecker.__scan_source_findings()`
	@staticmethod
	def __collect_subprocess_bindings(tree: ast.AST) -> tuple[set[str], dict[str, str]]:
		mods: set[str] = set()
		funcs: dict[str, str] = {}
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				for alias in node.names:
					if 'subprocess' == alias.name:
						mods.add(alias.asname or alias.name)
			elif isinstance(node, ast.ImportFrom) and 'subprocess' == node.module:
				for alias in node.names:
					if alias.name in SubprocessHygieneChecker.__CHECKED_FUNCS:
						funcs[alias.asname or alias.name] = alias.name
		return (mods, funcs)
	# @used-by :meth:`SubprocessHygieneChecker.__kw_has_non_none()`
	@staticmethod
	def __expr_has_dict_key(node: ast.AST, names: tuple[str, ...]) -> bool:
		r = False
		for sub in ast.walk(node):
			if isinstance(sub, ast.Dict) and any((isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value in names for k in sub.keys)):
				r = True
				break
		return r
	# @used-by :meth:`SubprocessHygieneChecker.__call_violations()`
	@staticmethod
	def __kw_has_non_none(call: ast.Call, names: tuple[str, ...]) -> bool:
		r = False
		for kw in call.keywords:
			if None is kw.arg:
				if SubprocessHygieneChecker.__expr_has_dict_key(kw.value, names):
					r = True
					break
			elif kw.arg in names and (not (isinstance(kw.value, ast.Constant) and None is kw.value.value)):
				r = True
				break
		return r
	# @used-by :meth:`SubprocessHygieneChecker.__scan_source_findings()`
	@staticmethod
	def __resolve_call_name(call: ast.Call, mod_aliases: set[str], direct_funcs: dict[str, str]) -> str | None:
		fn = call.func
		if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id in mod_aliases and fn.attr in SubprocessHygieneChecker.__CHECKED_FUNCS:
			r = fn.attr
		elif isinstance(fn, ast.Name) and fn.id in direct_funcs:
			r = direct_funcs[fn.id]
		else:
			r = None
		return r
	# @used-by :meth:`SubprocessHygieneChecker.check()`
	@staticmethod
	def __scan_source_findings(rel_label: str, source: str) -> list[tuple[tuple[str, str, str], str]] | None:
		try:
			tree = ast.parse(source or '')
		except SyntaxError:
			r = None
		else:
			mods, funcs = SubprocessHygieneChecker.__collect_subprocess_bindings(tree)
			found: list[tuple[tuple[str, str, str], str]] = []
			if mods or funcs:
				for node in ast.walk(tree):
					if isinstance(node, ast.Call):
						fn_name = SubprocessHygieneChecker.__resolve_call_name(node, mods, funcs)
						if None is not fn_name:
							found.extend(SubprocessHygieneChecker.__call_violations(node, fn_name, rel_label))
			r = found
		return r
	# @used-by :func:`agent_tools.subprocess_hygiene_gate.is_subprocess_hygiene_target()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygienePreToolGate.SubprocessHygienePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygieneStagedGate.SubprocessHygieneStagedGate.verify()`
	# @used-by :meth:`SubprocessHygieneChecker.check()`
	@staticmethod
	def is_target(path: str | Path) -> bool:
		rel = Path(str(path)).as_posix()
		low = rel.casefold()
		return low.endswith('.py') and (not low.startswith(('\ua616/', '\ua66e/', '.git/'))) and (CodeClassifier.is_test_file(rel) or bool(SubprocessHygieneChecker.__LAUNCHER_NAME_RE.search(Path(rel).name)))
	# @used-by :func:`agent_tools.subprocess_hygiene_gate.check_subprocess_hygiene_violations()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygienePreToolGate.SubprocessHygienePreToolGate.check()`
	# @used-by :meth:`Df.Harness.Gate.SubprocessHygieneStagedGate.SubprocessHygieneStagedGate.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_thin_pretool_shims_and_checkers()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	# @used-by :meth:`test_df_harness_s11_wave2b_tail_cov.DfHarnessS11Wave2bTailCovTests.test_gate_bulk_size_external_issue_and_subproc()`
	def check(self) -> list[str]:
		r: list[str] = []
		if SubprocessHygieneChecker.is_target(self.__path):
			rel_label = Path(self.__path).as_posix()
			cur = SubprocessHygieneChecker.__scan_source_findings(rel_label, self.__source)
			if cur:
				base = SubprocessHygieneChecker.__scan_source_findings(rel_label, self.__baseline_source) if None is not self.__baseline_source else None
				base_counts = Counter((sig for sig, _ in (base or ())))
				for sig, msg in cur:
					if 0 < base_counts[sig]:
						base_counts[sig] -= 1
					else:
						r.append(msg)
		return r
