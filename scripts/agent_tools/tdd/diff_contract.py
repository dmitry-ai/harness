# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.DiffContract import DiffContract
import sys
DIFF_EXECUTABILITY_GATES = DiffContract.DIFF_EXECUTABILITY_GATES
MIXED_COMMIT_COMMENT_THRESHOLD = DiffContract.MIXED_COMMIT_COMMENT_THRESHOLD
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_detect_mixed_commit_warning_threshold_and_exports()`
# @used-by :mod:`agent_tools.tdd.diff_contract`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def check_staged_mixed_commit_warning(repo_root: Path, staged_paths: list[str], *, use_index: bool=True, threshold: int=MIXED_COMMIT_COMMENT_THRESHOLD) -> dict[str, Any] | None:
	return DiffContract.check_staged_mixed_commit_warning(repo_root, staged_paths, use_index=use_index, threshold=threshold)
# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__check_repo_commits_and_files()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_detect_mixed_commit_warning_threshold_and_exports()`
# @used-by :mod:`agent_tools.tdd.diff_contract`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def check_touched_mixed_commit_warning(repo_root: Path, rel_paths: list[str], *, project_root: Path | None=None, threshold: int=MIXED_COMMIT_COMMENT_THRESHOLD) -> dict[str, Any] | None:
	return DiffContract.check_touched_mixed_commit_warning(repo_root, rel_paths, project_root=project_root, threshold=threshold)
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_detect_mixed_commit_warning_threshold_and_exports()`
# @used-by :mod:`agent_tools.tdd.diff_contract`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def detect_mixed_commit_warning(diff_info: dict[str, Any] | None, *, threshold: int=MIXED_COMMIT_COMMENT_THRESHOLD) -> dict[str, Any] | None:
	return DiffContract.detect_mixed_commit_warning(diff_info, threshold=threshold)
# @used-by :meth:`Df.Harness.Runtime.SnapshotPromoter.SnapshotPromoter.__promote_locked()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_all_six_gates_delegate_through_diff_executability()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_contract_constants_declare_all_six_gates_and_land_stage_policies()`
# @used-by :mod:`agent_tools.tdd.diff_contract`
# @used-by :mod:`agent_tools.tdd.diff_executability`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def should_run_snapshot_canary(repo_root: Path, base_ref: str | None=None, *, diff_info: dict[str, Any] | None=None) -> tuple[bool, str]:
	de = sys.modules.get('agent_tools.tdd.diff_executability')
	return DiffContract.should_run_snapshot_canary(repo_root, base_ref=base_ref, diff_info=diff_info, classify_range_fn=getattr(de, 'classify_git_range', None))
__all__ = ['DIFF_EXECUTABILITY_GATES', 'MIXED_COMMIT_COMMENT_THRESHOLD', 'check_staged_mixed_commit_warning', 'check_touched_mixed_commit_warning', 'detect_mixed_commit_warning', 'should_run_snapshot_canary']
