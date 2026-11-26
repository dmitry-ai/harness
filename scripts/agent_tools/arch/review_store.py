# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add arch-auditor subagent role and content-addressed review CLI":
# https://github.com/dmitry-ai/harness/issues/361
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
from Df.Harness.Arch.ReviewStore import ReviewStore
# @used-by :func:`record_arch_review()`
def _authenticate_arch_report(root: Path, parent_id: str, reviewer_id: str, report_bytes: bytes, pkg_name: str, *, native_evidence: Path | None, wait_timeout: float, platform: str | None, instance: str | None) -> dict[str, Any]:
	return ReviewStore.authenticate_report(root, parent_id, reviewer_id, report_bytes, pkg_name, native_evidence=native_evidence, wait_timeout=wait_timeout, platform=platform, instance=instance)
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_prepare_input_record_and_check_roundtrip_with_module_cache()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_review_store_roundtrip_auth_and_patch_seam()`
# @used-by :mod:`agent_tools.arch.review_store`
def inspect_arch_status(root: Path, *, repo: Path | None=None, response_text: str | None=None, issue_url: str | None=None) -> dict[str, Any]:
	return ReviewStore.inspect_status(root, repo=repo, response_text=response_text, issue_url=issue_url)
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_answer_and_stop_gates_enforce_significant_response_receipt_and_open_findings()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_pre_tool_use_blocks_unaudited_structural_write_and_allows_cached_or_approved_design()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_staged_pre_commit_enforces_approved_receipts_cache_and_anti_pattern_washing()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_staged_pre_commit_handles_participant_file_paths_and_incremental_multi_wave_commits()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_arch_native_review_proof_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_native_review_proof_and_verify_support_arch_role()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_prepare_input_record_and_check_roundtrip_with_module_cache()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_review_store_roundtrip_auth_and_patch_seam()`
# @used-by :mod:`agent_tools.arch.review_store`
def prepare_arch_package(root: Path, parent_id: str, *, kind: str, response_text: str | None=None, spec_text: str | None=None, repo: Path | None=None, files: list[str] | None=None, issue_url: str | None=None) -> dict[str, Any]:
	return ReviewStore.prepare_package(root, parent_id, kind=kind, response_text=response_text, spec_text=spec_text, repo=repo, files=files, issue_url=issue_url)
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_arch_native_review_proof_works_on_bare_code_workspace_without_text_marker()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_codex_native_review_proof_and_verify_support_arch_role()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_prepare_input_record_and_check_roundtrip_with_module_cache()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_review_store_roundtrip_auth_and_patch_seam()`
# @used-by :mod:`agent_tools.arch.review_store`
def read_arch_review_input(root: Path, package_rel: str, *, parent_id: str | None=None, reviewer_id: str | None=None) -> dict[str, Any]:
	return ReviewStore.read_review_input(root, package_rel, parent_id=parent_id, reviewer_id=reviewer_id)
# @used-by :func:`test_arch_audit_gates._record_verdict()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_prepare_input_record_and_check_roundtrip_with_module_cache()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_review_store_roundtrip_auth_and_patch_seam()`
# @used-by :mod:`agent_tools.arch.review_store`
def record_arch_review(root: Path, report_bytes: bytes, *, parent_id: str, reviewer_id: str, native_evidence: Path | None=None, wait_timeout: float=0.0, platform: str | None=None, instance: str | None=None) -> dict[str, Any]:
	return ReviewStore(root, auth_fn=_authenticate_arch_report).record_review(report_bytes, parent_id=parent_id, reviewer_id=reviewer_id, native_evidence=native_evidence, wait_timeout=wait_timeout, platform=platform, instance=instance)
__all__ = ['inspect_arch_status', 'prepare_arch_package', 'read_arch_review_input', 'record_arch_review']
