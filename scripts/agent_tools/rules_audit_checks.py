# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.RulesAuditChecker import RulesAuditChecker
MAX_ALWAYS_ON_BYTES = RulesAuditChecker.MAX_ALWAYS_ON_BYTES
MAX_ALWAYS_ON_TOKENS = RulesAuditChecker.MAX_ALWAYS_ON_TOKENS
MAX_RULE_FILE_BYTES = RulesAuditChecker.MAX_RULE_FILE_BYTES
WORKSPACE_AUTO_FILES = RulesAuditChecker.WORKSPACE_AUTO_FILES
_FENCE_RE = RulesAuditChecker.FENCE_RE
_HTML_COMMENT_RE = RulesAuditChecker.HTML_COMMENT_RE
# @used-by :mod:`agent_tools.rules_audit_checks`
def check_budget_smells(entries: list[dict], workspace_files: list[dict], *, max_file_bytes: int=MAX_RULE_FILE_BYTES, max_always_on_bytes: int=MAX_ALWAYS_ON_BYTES, max_always_on_tokens: int=MAX_ALWAYS_ON_TOKENS) -> list[dict]:
	return RulesAuditChecker.check_budget_smells(entries, workspace_files, max_file_bytes=max_file_bytes, max_always_on_bytes=max_always_on_bytes, max_always_on_tokens=max_always_on_tokens)
# @used-by :mod:`agent_tools.rules_audit_checks`
def check_cross_platform_leaks(entries: list[dict], workspace_files: list[dict]) -> list[dict]:
	return RulesAuditChecker.check_cross_platform_leaks(entries, workspace_files)
# @used-by :mod:`agent_tools.rules_audit_checks`
def check_html_comments(entries: list[dict]) -> list[dict]:
	return RulesAuditChecker.check_html_comments(entries)
# @used-by :mod:`agent_tools.rules_audit_checks`
def check_instruction_drift(entries: list[dict], primary: Path) -> list[dict]:
	return RulesAuditChecker.check_instruction_drift(entries, primary)
# @used-by :mod:`agent_tools.rules_audit_checks`
def check_links_and_blind_references(entries: list[dict]) -> list[dict]:
	return RulesAuditChecker.check_links_and_blind_references(entries)
# @used-by :mod:`agent_tools.rules_audit_checks`
def check_skill_leakage_duplicates(entries: list[dict], primary: Path) -> list[dict]:
	return RulesAuditChecker.check_skill_leakage_duplicates(entries, primary)
__all__ = ['MAX_ALWAYS_ON_BYTES', 'MAX_ALWAYS_ON_TOKENS', 'MAX_RULE_FILE_BYTES', 'WORKSPACE_AUTO_FILES', '_FENCE_RE', '_HTML_COMMENT_RE', 'check_budget_smells', 'check_cross_platform_leaks', 'check_html_comments', 'check_instruction_drift', 'check_links_and_blind_references', 'check_skill_leakage_duplicates']
