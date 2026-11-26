# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# Fast order-preserving deduplication for hashable scalar (str/int) elements, skipping None.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/unique_fast.php#L2-L25
# @used-by :func:`agent_tools.cleanup_audit._extract_removed_record()`
# @used-by :func:`agent_tools.grounding_helpers.audit_active_block()`
# @used-by :func:`agent_tools.issues.git_read_cache._parse_log_index()`
# @used-by :func:`agent_tools.issues.service_helpers.pending_similar_peer_slugs()`
# @used-by :func:`agent_tools.repo_link_gate._authored_targets()`
# @used-by :func:`agent_tools.repo_link_gate.chat_repo_link_issues()`
# @used-by :func:`agent_tools.repo_link_gate.file_repo_link_issues()`
# @used-by :func:`agent_tools.shell_audit.extract_issue_urls()`
# @used-by :func:`agent_tools.tdd.commands.classify_test_command()`
# @used-by :func:`check_markdown_slop._format_grounding_issues()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._referenced_paths()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_clean_null_and_unique_fast_delegation_to_df()`
def dfa_unique_fast(a: list[Any] | dict[Any, Any]) -> list[Any]:
	vals = a.values() if isinstance(a, dict) else a
	return list(dict.fromkeys((v for v in vals if isinstance(v, (str, int)) and (not isinstance(v, bool)))))
