# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class CodeSizePreToolGate:
	NAME = 'CODE-SIZE-RATCHET-GATE'
	PRIORITY = 120
	TOOLS = frozenset({'write_file', 'edit_file'})
	# @used-by :func:`agent_tools.code_size_gate.evaluate_pre_tool_use_code_size()`
	# @used-by :func:`agent_tools.gates.code_size.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_thin_pretool_shims_and_checkers()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		r = None
		if name in ('write_file', 'edit_file'):
			from Df.Harness.Gate.CodeSizeAnalyzer import CodeSizeAnalyzer
			from Df.Harness.Gate.CodeSizeChecker import CodeSizeChecker
			from Df.Harness.Gate.PythonIntegrity import PythonIntegrity
			from Df.Harness.Tdd.Enforcement import Enforcement
			resolved = CodeSizeAnalyzer.resolve_python_target(args, payload or {})
			if None is not resolved:
				repo_root, target, rel = resolved
				_, new_text, _, _ = Enforcement.compute_edited_content(name, args, target)
				if None is not new_text:
					base_text = Enforcement.git_head_text(repo_root, rel)
					if 'edit_file' != name or (not CodeSizeChecker.is_legacy_oversized_baseline(rel, base_text)):
						errs = CodeSizeChecker(rel, new_text, baseline_source=base_text).check()
						if 'write_file' == name and (not errs):
							errs.extend(PythonIntegrity.check(rel, new_text))
						r = '; '.join(errs[:3]) if errs else None
		return r
