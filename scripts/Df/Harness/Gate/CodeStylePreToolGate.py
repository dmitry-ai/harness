# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class CodeStylePreToolGate:
	NAME = 'CODE-STYLE-GATE'
	PRIORITY = 125
	TOOLS = frozenset({'write_file', 'edit_file'})
	# @used-by :func:`agent_tools.code_style_gate.evaluate_pre_tool_use_code_style()`
	# @used-by :func:`agent_tools.gates.code_style.check()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_thin_pretool_shims_and_checkers()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		r = None
		if name in ('write_file', 'edit_file'):
			from Df.Harness.Gate.CodeSizeAnalyzer import CodeSizeAnalyzer
			from Df.Harness.Gate.CodeStyleChecker import CodeStyleChecker
			from Df.Harness.Tdd.Enforcement import Enforcement
			resolved = CodeSizeAnalyzer.resolve_python_target(args, payload or {})
			if None is not resolved:
				repo_root, target, rel = resolved
				_, new_text, _, _ = Enforcement.compute_edited_content(name, args, target)
				if None is not new_text:
					errs = CodeStyleChecker(rel, new_text, baseline_source=Enforcement.git_head_text(repo_root, rel)).check()
					r = '; '.join(errs[:3]) if errs else None
		return r
