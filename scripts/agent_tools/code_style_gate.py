# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.CodeStyleAnalyzer import CodeStyleAnalyzer
from Df.Harness.Gate.CodeStyleChecker import CodeStyleChecker
from Df.Harness.Gate.CodeStylePreToolGate import CodeStylePreToolGate
from Df.Harness.Gate.CodeStyleStagedGate import CodeStyleStagedGate
# @used-by :mod:`agent_tools.code_style_gate`
def analyze_python_style(source: str) -> dict:
	return CodeStyleAnalyzer(source).analyze()
# @used-by :meth:`test_code_style_gate.CodeStyleGateTests.test_clean_code1_python_passes_all_checks()`
# @used-by :meth:`test_code_style_gate.CodeStyleGateTests.test_legacy_ratchet_preserves_existing_violations_but_blocks_new_ones()`
# @used-by :meth:`test_code_style_gate.CodeStyleGateTests.test_rejects_blank_lines_spaces_multireturn_non_yoda_and_double_quotes()`
# @used-by :mod:`agent_tools.code_style_gate`
def check_python_style_violations(path: str | Path, source: str, *, baseline_source: str | None=None) -> list[str]:
	return CodeStyleChecker(path, source, baseline_source=baseline_source).check()
# @used-by :mod:`agent_tools.code_style_gate`
def evaluate_pre_tool_use_code_style(name: str, args: dict, payload: dict) -> str | None:
	return CodeStylePreToolGate().check(name, args, payload)
# @used-by :mod:`agent_tools.code_style_gate`
def verify_staged_code_style_ratchet(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	return CodeStyleStagedGate(repo_root, staged_paths, use_index=use_index).verify()
__all__ = ['analyze_python_style', 'check_python_style_violations', 'evaluate_pre_tool_use_code_style', 'verify_staged_code_style_ratchet']
