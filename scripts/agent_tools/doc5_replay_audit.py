# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Grounding.Doc5ReplayAuditor import Doc5ReplayAuditor
from . import doc5_context
# 2026-11-26 "Enforce historical feature-turn regression audit before worktree landing": https://github.com/dmitry-ai/harness/issues/373
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
_ANSWER_GATE_PATHS = Doc5ReplayAuditor.ANSWER_GATE_PATHS
# @used-by :func:`verify_worktree_answer_gate_corpus()`
# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_tracked_feature_turn_corpus_has_zero_false_positives_and_catches_regression()`
def _run_worktree_corpus_subprocess(wt_path: Path, fixtures_dir: Path, *, timeout: float=120.0) -> dict[str, Any]:
	return Doc5ReplayAuditor.run_worktree_corpus_subprocess(wt_path, fixtures_dir, timeout=timeout)
# @used-by :meth:`test_df_harness_s11_final_338.DfHarnessS11Final338Tests.test_doc5_replay_auditor_corpus_and_subprocess()`
# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_tracked_feature_turn_corpus_has_zero_false_positives_and_catches_regression()`
# @used-by :mod:`agent_tools.doc5_replay_audit`
def audit_feature_turn_corpus(fixtures_dir: Path | str) -> dict[str, Any]:
	return Doc5ReplayAuditor.audit_corpus(fixtures_dir, checker_fn=doc5_context.turn_requires_doc5_problem_analysis)
# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_audit_local_saved_turns_flags_false_positives_and_passes_clean_history()`
# @used-by :mod:`agent_tools.doc5_replay_audit`
def audit_local_saved_turns(project_root: Path | str, *, limit: int=20) -> dict[str, Any]:
	return Doc5ReplayAuditor.audit_saved_turns(project_root, limit=limit, checker_fn=doc5_context.turn_requires_doc5_problem_analysis)
# @used-by :meth:`Df.Harness.Git.WorktreeRebaseVerifier.WorktreeRebaseVerifier.__check_diff_coverage()`
# @used-by :meth:`test_df_harness_s11_final_338.DfHarnessS11Final338Tests.test_doc5_replay_auditor_saved_turns_and_worktree_verify()`
# @used-by :meth:`test_doc5_replay_audit.Doc5ReplayAuditTests.test_worktree_land_enforces_answer_gate_corpus_before_merge()`
# @used-by :mod:`agent_tools.doc5_replay_audit`
def verify_worktree_answer_gate_corpus(wt_path: Path, target_branch: str) -> dict[str, Any]:
	return Doc5ReplayAuditor(wt_path, target_branch, subprocess_runner=_run_worktree_corpus_subprocess).verify_worktree()
__all__ = ['audit_feature_turn_corpus', 'audit_local_saved_turns', 'verify_worktree_answer_gate_corpus']
