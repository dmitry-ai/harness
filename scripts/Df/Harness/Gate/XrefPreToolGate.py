# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class XrefPreToolGate:
	NAME = 'XREF-GATE'
	PRIORITY = 127
	TOOLS = frozenset({'write_file', 'edit_file'})
	# @used-by :func:`agent_tools.gates.xref.check()`
	# @used-by :func:`agent_tools.xref_gate.evaluate_pre_tool_use_xref()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_thin_pretool_shims_and_checkers()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		r: str | None = None
		if name in ('write_file', 'edit_file'):
			from Df.Harness.Gate.XrefChecker import XrefChecker
			from Df.Harness.Tdd.Enforcement import Enforcement
			resolved = XrefChecker.resolve_target(args, payload or {})
			if None is not resolved:
				repo_root, target, rel = resolved
				old_disk, new_text, _, _ = Enforcement.compute_edited_content(name, args, target)
				if None is not new_text and XrefChecker.is_pre_tool_governed(repo_root, target, new_text):
					base = Enforcement.git_head_text(repo_root, rel) if None is not repo_root else old_disk
					errs = XrefChecker(rel, new_text, baseline_source=base).check()
					r = '; '.join(errs[:3]) if errs else None
		return r
