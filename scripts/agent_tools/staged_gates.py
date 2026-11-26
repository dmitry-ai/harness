# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26
# "Add blocking architecture audit gates with module-hash caching":
# https://github.com/dmitry-ai/harness/issues/363
from .arch.enforcement import verify_staged_arch_audit
from .code_style_gate import verify_staged_code_style_ratchet
# 2026-11-26
# "Add PreToolUse and pre-commit gate for issue-comment placement":
# https://github.com/dmitry-ai/harness/issues/273
from .issue_comment_gate import verify_staged_issue_comment_placement
# 2026-11-26 "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs": https://github.com/dmitry-ai/harness/issues/264
from .repo_link_gate import verify_staged_repo_links
# 2026-11-26
# "Add deterministic rules-audit CLI and aggregate budget enforcement":
# https://github.com/dmitry-ai/harness/issues/244
from .rules_audit import verify_staged_rules_audit
from .subprocess_hygiene_gate import verify_staged_subprocess_hygiene
# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
from .tdd.diff_executability import check_staged_mixed_commit_warning
# 2026-11-26
# "Enforce cross-reference compliance in PreToolUse and Git gates":
# https://github.com/dmitry-ai/harness/issues/306
from .xref_gate import verify_staged_xref
# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
import sys
# 2026-11-25
# "Add CODE-1 Python style ratchet linter gate in PreToolUse and pre-commit":
# https://github.com/dmitry-ai/harness/issues/243
# @used-by :meth:`agent_tools.git_gate.GitRepoGate._verify_agent_staged()`
# @used-by :meth:`test_arch_audit_gates.ArchAuditGatesTests.test_staged_pre_commit_enforces_approved_receipts_cache_and_anti_pattern_washing()`
# @used-by :meth:`test_mixed_commit_audit.MixedCommitAuditTests.test_pre_commit_emits_non_blocking_mixed_warning_to_stderr()`
# @used-by :meth:`test_repo_link_gate.RepoLinkGateTests.test_issue_linter_staged_gate_and_markdown_hook_enforce_repo_link_ban()`
# @used-by :meth:`test_rules_audit.RulesAuditTests.test_pre_tool_use_rules_budget_and_doctor_and_pre_commit_enforce_limits()`
def verify_staged_extra_gates(repo_root: Path, staged_paths: list[str], *, use_index: bool=True) -> list[str]:
	violations = verify_staged_subprocess_hygiene(repo_root, staged_paths, use_index=use_index)
	violations.extend(verify_staged_code_style_ratchet(repo_root, staged_paths, use_index=use_index))
	# 2026-11-26
	# "Add PreToolUse and pre-commit gate for issue-comment placement":
	# https://github.com/dmitry-ai/harness/issues/273
	violations.extend(verify_staged_issue_comment_placement(repo_root, staged_paths, use_index=use_index))
	# 2026-11-26
	# "Add deterministic rules-audit CLI and aggregate budget enforcement":
	# https://github.com/dmitry-ai/harness/issues/244
	violations.extend(verify_staged_rules_audit(repo_root, staged_paths, use_index=use_index))
	# 2026-11-26 "Ban file:/// links for GitHub repositories and ground tagged GitHub URLs": https://github.com/dmitry-ai/harness/issues/264
	violations.extend(verify_staged_repo_links(repo_root, staged_paths, use_index=use_index))
	# 2026-11-26
	# "Enforce cross-reference compliance in PreToolUse and Git gates":
	# https://github.com/dmitry-ai/harness/issues/306
	violations.extend(verify_staged_xref(repo_root, staged_paths, use_index=use_index))
	# 2026-11-26
	# "Add blocking architecture audit gates with module-hash caching":
	# https://github.com/dmitry-ai/harness/issues/363
	violations.extend(verify_staged_arch_audit(repo_root, staged_paths, use_index=use_index))
	# 2026-11-26 "Enforce mixed executable and bulk comment-only commit audit and decomposition rules": https://github.com/dmitry-ai/harness/issues/362
	warn = check_staged_mixed_commit_warning(repo_root, staged_paths, use_index=use_index)
	if None is not warn:
		sys.stderr.write(f"WARNING: {warn['message']}\n")
	return violations
