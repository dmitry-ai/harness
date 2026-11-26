# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.Enforcement import Enforcement
from .events import extract_antigravity_tdd_events
import sys
# @used-by :mod:`agent_tools.tdd.enforcement`
def _active_turn_issue_urls(new_text: str | None, old_text: str | None) -> list[str]:
	return Enforcement.active_turn_issue_urls(new_text, old_text)
# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.evaluate_pre_tool_use()`
# @used-by :mod:`agent_tools.tdd.enforcement`
def _compute_edited_content(name: str, args: dict, target_path: Path) -> tuple[str | None, str | None, list[str], set[int]]:
	return Enforcement.compute_edited_content(name, args, target_path)
# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.__staged_code_entries()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_enforcement_module_behavior_and_parity()`
# @used-by :mod:`agent_tools.tdd.enforcement`
def _git_head_text(repo_root: Path, rel_posix: str) -> str | None:
	return Enforcement.git_head_text(repo_root, rel_posix)
# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.__staged_code_entries()`
# @used-by :mod:`agent_tools.tdd.enforcement`
def _git_index_text(repo_root: Path, rel_posix: str) -> str | None:
	return Enforcement.git_index_text(repo_root, rel_posix)
# @used-by :func:`test_diff_executability_contract._verify_tdd_gate_delegation()`
# @used-by :meth:`test_comment_exemption_and_denied_writes.CommentExemptionAndDeniedWritesTests.test_tdd_exempts_comment_only_test_edits_and_recognizes_java_assertions()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_pre_tool_use_allows_comment_only_edit_and_denies_code_edit()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_enforcement_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_pre_tool_use_short_circuits_non_code_and_non_writing_commands()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_pre_tool_use_allows_matching_mechanical_edit_and_denies_extraneous_edit()`
# @used-by :mod:`agent_tools.tdd.enforcement`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def evaluate_pre_tool_use_tdd(name: str, args: dict, payload: dict) -> str | None:
	de = sys.modules.get('agent_tools.tdd.diff_executability')
	return Enforcement(event_extractor=extract_antigravity_tdd_events, diff_non_exec_fn=getattr(de, 'is_non_executable_diff', None)).evaluate_pre_tool_use(name, args, payload)
# @used-by :func:`test_diff_executability_contract._verify_tdd_gate_delegation()`
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_tdd_commit()`
# @used-by :meth:`test_comment_exemption_and_denied_writes.CommentExemptionAndDeniedWritesTests.test_tdd_exempts_comment_only_test_edits_and_recognizes_java_assertions()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_enforcement_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_hardening_header_exit_code_indirect_source_read_and_index_blob()`
# @used-by :mod:`agent_tools.tdd.enforcement`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def verify_staged_tdd_diff(repo_root: Path, staged_paths: list[str], *, message: str | None=None, project_root: Path | None=None, use_index: bool=False) -> list[str]:
	de = sys.modules.get('agent_tools.tdd.diff_executability')
	return Enforcement.verify_staged_diff(repo_root, staged_paths, message=message, project_root=project_root, use_index=use_index, diff_non_exec_fn=getattr(de, 'is_non_executable_diff', None))
__all__ = ['_active_turn_issue_urls', '_compute_edited_content', '_git_head_text', '_git_index_text', 'evaluate_pre_tool_use_tdd', 'verify_staged_tdd_diff']
