# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Gate.CodeStyleStagedGate import CodeStyleStagedGate
from Df.Harness.Gate.IssueCommentStagedGate import IssueCommentStagedGate
from Df.Harness.Gate.RepoLinkGate import RepoLinkGate
from Df.Harness.Gate.RulesAuditor import RulesAuditor
from Df.Harness.Gate.SubprocessHygieneStagedGate import SubprocessHygieneStagedGate
from Df.Harness.Gate.XrefStagedGate import XrefStagedGate
from Df.Harness.Tdd.DiffContract import DiffContract
from agent_tools.arch.enforcement import verify_staged_arch_audit
import sys
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class StagedGates:
	# @used-by :func:`agent_tools.staged_gates.verify_staged_extra_gates()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	def __init__(self, repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> None:
		self.__repo_root = repo_root
		self.__staged_paths = staged_paths
		self.__use_index = use_index
	# @used-by :func:`agent_tools.staged_gates.verify_staged_extra_gates()`
	# @used-by :meth:`test_df_harness_s11_wave2b_gate.DfHarnessS11Wave2bGateTests.test_gate_staged_and_repo_checks()`
	def verify(self) -> list[str]:
		violations = SubprocessHygieneStagedGate(self.__repo_root, self.__staged_paths, use_index=self.__use_index).verify()
		violations.extend(CodeStyleStagedGate(self.__repo_root, self.__staged_paths, use_index=self.__use_index).verify())
		violations.extend(IssueCommentStagedGate(self.__repo_root, self.__staged_paths, use_index=self.__use_index).verify())
		violations.extend(RulesAuditor.verify_staged(self.__repo_root, self.__staged_paths, use_index=self.__use_index))
		violations.extend(RepoLinkGate().verify_staged(self.__repo_root, self.__staged_paths, use_index=self.__use_index))
		violations.extend(XrefStagedGate(self.__repo_root, self.__staged_paths, use_index=self.__use_index).verify())
		violations.extend(verify_staged_arch_audit(self.__repo_root, self.__staged_paths, use_index=self.__use_index))
		warn = DiffContract.check_staged_mixed_commit_warning(self.__repo_root, self.__staged_paths, use_index=self.__use_index)
		if None is not warn:
			sys.stderr.write(f"WARNING: {warn['message']}\n")
		return violations
