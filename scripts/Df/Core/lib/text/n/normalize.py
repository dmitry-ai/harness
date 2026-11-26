# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# Normalize CRLF (`\r\n`) and CR (`\r`) line endings to Unix LF (`\n`).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/n/normalize.php#L2-L10
# @used-by :func:`Df.Core.lib.text.n.explode.df_explode_n()`
# @used-by :func:`Df.Core.lib.text.n.has.df_is_multiline()`
# @used-by :func:`Df.Core.lib.text.n.remove.df_single_line()`
# @used-by :func:`agent_tools.cleanup_audit.record_cleanup_answer_log()`
# @used-by :func:`agent_tools.project_card.sync_block()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpS()`
# @used-by :meth:`agent_tools.issues.linter.IssueMarkdownLinter.normalize_newlines()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_normalize_and_trim_delegation_to_df()`
def df_normalize(s: str) -> str:
	return s.replace('\r\n', '\n').replace('\r', '\n')
