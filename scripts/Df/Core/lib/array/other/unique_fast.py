# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core/lib/array helper library": https://github.com/dmitry-ai/harness/issues/323
# Fast order-preserving deduplication for hashable scalar (str/int) elements, skipping None.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/array/other/unique_fast.php#L2-L25
# @used-by :func:`Df.Harness.lib.cleanup_audit_ops._extract_removed_record()`
# @used-by :func:`Df.Harness.lib.hook_markdown_ops._format_grounding_issues()`
# @used-by :func:`Df.Harness.lib.shell.dfh_extract_issue_urls()`
# @used-by :func:`agent_tools.shell_audit.extract_issue_urls()`
# @used-by :func:`agent_tools.tdd.commands.classify_test_command()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.__authored_targets()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.check_chat()`
# @used-by :meth:`Df.Harness.Gate.RepoLinkGate.RepoLinkGate.check_file()`
# @used-by :meth:`Df.Harness.Grounding.BlockLineAuditor.BlockLineAuditor.audit()`
# @used-by :meth:`Df.Harness.Issue.PendingPeerFinder.PendingPeerFinder.find()`
# @used-by :meth:`Df.Harness.Issue.ReadCache.ReadCache.__parse_log_index()`
# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.classify_test_command()`
# @used-by :meth:`agent_tools.text_diagnostics.SourceDiagnosticsScanner._referenced_paths()`
# @used-by :meth:`test_df_core_array.DfCoreArrayTests.test_other_and_part()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_clean_null_and_unique_fast_delegation_to_df()`
def dfa_unique_fast(a: list[Any] | dict[Any, Any]) -> list[Any]:
	vals = a.values() if isinstance(a, dict) else a
	return list(dict.fromkeys((v for v in vals if isinstance(v, (str, int)) and (not isinstance(v, bool)))))
