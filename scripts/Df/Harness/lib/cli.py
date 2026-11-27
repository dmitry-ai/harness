# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import os
# 2026-11-26 "Create Df/Harness library for shared Harness helpers": https://github.com/dmitry-ai/harness/issues/379
# Collect non-empty URL strings from CLI positional, repeatable `--url`, and legacy single `url` args.
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_collect_browser()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_collect_http()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_evidence_query()`
# @used-by :func:`agent_tools.cli_domains._collect_urls()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_cli_journal_and_project_helpers()`
def dfh_collect_urls(args: Any, *, require_nonempty: bool=True) -> list[str]:
	legacy_single = getattr(args, 'url', None)
	raw = [*(getattr(args, 'urls_pos', None) or ()), *(getattr(args, 'url_list', None) or ()), *([legacy_single] if isinstance(legacy_single, str) and legacy_single.strip() else ())]
	urls = [str(u).strip() for u in raw if isinstance(u, str) and str(u).strip()]
	if require_nonempty and (not urls):
		raise ValueError('Provide at least one URL via positional <URL> or --url <URL>')
	return urls
# Return bounded default worker count for parallel Harness test and profiling runners.
# @used-by :meth:`Df.Harness.Perf.SuiteProfiler.SuiteProfiler.default_workers()`
# @used-by :meth:`Df.Harness.TestRunner.SuiteRunner.SuiteRunner.default_workers()`
# @used-by :meth:`test_df_harness_lib_s10.DfHarnessLibS10Tests.test_cli_journal_and_project_helpers()`
def dfh_default_workers(cap: int=8) -> int:
	return min(max(2, (os.cpu_count() or 4) // 2), int(cap))