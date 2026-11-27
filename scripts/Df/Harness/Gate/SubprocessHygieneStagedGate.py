# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Gate.SubprocessHygieneChecker import SubprocessHygieneChecker
from Df.Harness.Tdd.Enforcement import Enforcement
import importlib
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class SubprocessHygieneStagedGate:
	# @used-by :func:`agent_tools.subprocess_hygiene_gate.verify_staged_subprocess_hygiene()`
	# @used-by :meth:`Df.Harness.Gate.StagedGates.StagedGates.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	def __init__(self, repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> None:
		self.__repo = Path(repo_root).resolve()
		self.__staged_paths = list(staged_paths or ())
		self.__use_index = use_index
	# @used-by :func:`agent_tools.subprocess_hygiene_gate.run_staged_gate()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate_cov.DfHarnessS11Wave2bGateCovTests.test_rules_auditor_subprocess_and_xref_checker()`
	@staticmethod
	def run_staged_gate(mod_name: str, func_name: str, *args, **kwargs) -> None:
		mod = importlib.import_module(f'agent_tools.{mod_name}')
		violations = getattr(mod, func_name)(*args, **kwargs)
		if violations:
			raise ValueError('; '.join(violations))
	# @used-by :func:`agent_tools.subprocess_hygiene_gate.verify_staged_subprocess_hygiene()`
	# @used-by :meth:`Df.Harness.Gate.StagedGates.StagedGates.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	def verify(self) -> list[str]:
		violations: list[str] = []
		for rel in self.__staged_paths:
			if not SubprocessHygieneChecker.is_target(rel):
				continue
			fpath = self.__repo / rel
			text = Enforcement.git_index_text(self.__repo, rel) if self.__use_index else (fpath.read_text(encoding='utf-8', errors='replace') if fpath.is_file() else None)
			if None is not text:
				violations.extend(SubprocessHygieneChecker(rel, text, baseline_source=Enforcement.git_head_text(self.__repo, rel)).check())
		return violations
