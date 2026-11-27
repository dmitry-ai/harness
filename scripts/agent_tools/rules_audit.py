# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.RulesAuditChecker import RulesAuditChecker
from Df.Harness.Gate.RulesAuditor import RulesAuditor
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_rules_audit()`
# @used-by :meth:`test_arch_rules_contract.ArchRulesContractTests.test_architecture_rule_is_compact_always_on_and_passes_doctor_and_rules_audit()`
# @used-by :meth:`test_ask_question_pre_tool_gate.AskQuestionPreToolGateTests.test_pre_tool_gate_blocks_stop_gate_bypass_and_docs_codify_rule()`
# @used-by :meth:`test_cli_command_grounding.CliCommandGroundingTests.test_exec2_rule_contains_shadow_replay_requirement_and_passes_rules_audit()`
# @used-by :meth:`test_diff_executability_contract.DiffExecutabilityContractTests.test_docs_and_rules_codify_contract_within_rules_audit_budgets()`
# @used-by :meth:`test_repo_tags_docs.RepoTagsDocsTests.test_rules_and_docs_codify_daily_tagging_and_link6_within_budgets()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_detects_broken_links_blind_references_drift_and_skill_leakage()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_detects_budget_html_comment_and_cross_platform_codex_leaks()`
# @used-by :meth:`test_snapshot_latency_and_delegation_policy.SnapshotLatencyAndDelegationPolicyTests.test_delegation_rule_and_worktree_doc_codify_multi_track_policy_and_pass_audits()`
# @used-by :mod:`agent_tools.rules_audit`
def audit_rules(primary: str | Path, *, workspace: str | Path | None=None, max_file_bytes: int=RulesAuditChecker.MAX_RULE_FILE_BYTES, max_always_on_bytes: int=RulesAuditChecker.MAX_ALWAYS_ON_BYTES, max_always_on_tokens: int=RulesAuditChecker.MAX_ALWAYS_ON_TOKENS, overrides: dict[Path, bytes] | None=None) -> dict:
	return RulesAuditor(primary, workspace=workspace, max_file_bytes=max_file_bytes, max_always_on_bytes=max_always_on_bytes, max_always_on_tokens=max_always_on_tokens, overrides=overrides).audit()
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_rules_audit()`
# @used-by :mod:`agent_tools.rules_audit`
def build_semantic_audit_brief(primary: str | Path, *, workspace: str | Path | None=None) -> str:
	return RulesAuditor.build_semantic_brief(primary, workspace=workspace)
# @used-by :mod:`agent_tools.rules_audit`
def check_shared_rule_edit(name: str, args: dict) -> str | None:
	return RulesAuditor.check_shared_rule_edit(name, args)
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_format_rules_audit()`
# @used-by :mod:`agent_tools.rules_audit`
def format_rules_audit_text(report: dict) -> str:
	return RulesAuditor.format_text(report)
# @used-by :mod:`agent_tools.rules_audit`
def verify_staged_rules_audit(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	return RulesAuditor.verify_staged(repo_root, staged_paths, use_index=use_index)
__all__ = ['audit_rules', 'build_semantic_audit_brief', 'check_shared_rule_edit', 'format_rules_audit_text', 'verify_staged_rules_audit']
