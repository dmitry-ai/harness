# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import os
import sys
from Df.Core.lib.cache.dfcf import dfcf
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2016-05-15 http://stackoverflow.com/a/2053295
# 2017-06-09 Intentionally returns False in CLI mode when REMOTE_ADDR is unset.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/state.php#L32-L39
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cli_state_and_hash()`
def df_is_localhost() -> bool:
	return os.environ.get('REMOTE_ADDR', '') in ('127.0.0.1', '::1')
# 2016-12-22
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/state.php#L41-L45
# @used-by :func:`agent_tools.addon_observability._is_pid_alive()`
# @used-by :func:`agent_tools.gates.worktree_isolation._resolve_target_path()`
# @used-by :func:`agent_tools.git_gate._ancestor_process_names()`
# @used-by :func:`agent_tools.git_gate.cleanup_stale_credential_locks()`
# @used-by :func:`agent_tools.landing_lease._pid_is_alive()`
# @used-by :func:`agent_tools.process_tree.kill_process_tree()`
# @used-by :func:`agent_tools.storage.create_bytes()`
# @used-by :func:`agent_tools.storage.locked()`
# @used-by :func:`agent_tools.text_core.default_shell()`
# @used-by :func:`agent_tools.watchdog_runner.run_test_watchdog()`
# @used-by :func:`agent_tools.worktree_guard._query_win32_processes()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cli_state_and_hash()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_first_last_starts_with_and_is_windows_delegation_to_df()`
# @used-by :mod:`agent_tools.process_tree`
def df_is_windows() -> bool:
	return dfcf(lambda: 'WIN' == sys.platform[:3].upper())
