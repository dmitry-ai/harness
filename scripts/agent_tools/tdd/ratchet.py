# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.RatchetGuard import RatchetGuard
_RATCHET_OK_LINE_RE = RatchetGuard.RATCHET_OK_LINE_RE
_RATCHET_SLOP_RE = RatchetGuard.RATCHET_SLOP_RE
_SKIP_MARKER_RE = RatchetGuard.SKIP_MARKER_RE
_TEST_DEF_RE = RatchetGuard.TEST_DEF_RE
# @used-by :mod:`agent_tools.tdd.ratchet`
def _load_turn_ratchet_receipts(project_root: Path | None) -> list[dict]:
	return RatchetGuard.load_turn_receipts(project_root)
# @used-by :mod:`agent_tools.tdd.ratchet`
def _match_ratchet_target(target_spec: str, file_path: str | Path) -> bool:
	return RatchetGuard.match_target(target_spec, file_path)
# @used-by :mod:`agent_tools.tdd.ratchet`
def _parse_ratchet_ok_lines(body: str) -> list[tuple[str, str]]:
	return RatchetGuard.parse_ratchet_ok_lines(body)
# @used-by :mod:`agent_tools.tdd.ratchet`
def _turn_receipt_dirs(project_root: Path) -> list[Path]:
	return RatchetGuard.turn_receipt_dirs(project_root)
# @used-by :meth:`test_tdd_completion.TddTurnCompletionAndCliTests.test_cli_ratchet_ok_and_tdd_check_commands()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_ratchet_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_shell_code_write_targets_and_ratchet_issue_evidence()`
# @used-by :mod:`agent_tools.tdd.ratchet`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def find_ratchet_approval(file_path: str | Path, *, repo_root: Path | None=None, project_root: Path | None=None, turn_receipts: list[dict] | None=None, issue_urls: list[str] | tuple[str, ...]=()) -> dict | None:
	return RatchetGuard.find_approval(file_path, repo_root=repo_root, project_root=project_root, turn_receipts=turn_receipts, issue_urls=issue_urls)
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_ratchet_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_ratchet_diff_guard_and_ratchet_ok_validation()`
# @used-by :mod:`agent_tools.tdd.ratchet`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def ratchet_diff_violations(rel_path: str, old_text: str, new_text: str | None, *, approval: dict | None=None) -> list[str]:
	return RatchetGuard(rel_path, old_text, new_text, approval=approval).check()
# @used-by :func:`Df.Harness.lib.completion_recovery.dfh_ratchet_ok()`
# @used-by :meth:`test_tdd_decomposition.TddDecompositionTests.test_ratchet_module_behavior_and_parity()`
# @used-by :meth:`test_tdd_gate.TddGateCoreTests.test_ratchet_diff_guard_and_ratchet_ok_validation()`
# @used-by :mod:`agent_tools.tdd.ratchet`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def validate_ratchet_reason(reason: str) -> tuple[bool, str | None]:
	return RatchetGuard.validate_reason(reason)
__all__ = ['_RATCHET_OK_LINE_RE', '_RATCHET_SLOP_RE', '_SKIP_MARKER_RE', '_TEST_DEF_RE', '_load_turn_ratchet_receipts', '_match_ratchet_target', '_parse_ratchet_ok_lines', '_turn_receipt_dirs', 'find_ratchet_approval', 'ratchet_diff_violations', 'validate_ratchet_reason']
