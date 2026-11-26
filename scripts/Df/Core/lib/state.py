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
# @used-by :func:`Df.Harness.lib.hook_addon_ops.dfh_is_pid_alive()`
# @used-by :func:`Df.Harness.lib.process.dfh_pid_is_alive()`
# @used-by :func:`Df.Harness.lib.storage._acquire_stream_lock()`
# @used-by :func:`Df.Harness.lib.storage._release_stream_lock()`
# @used-by :func:`agent_tools.text_core.default_shell()`
# @used-by :meth:`Df.Harness.Config.AtomicWriter.AtomicWriter.__commit()`
# @used-by :meth:`Df.Harness.Gate.WorktreeIsolationGate.WorktreeIsolationGate.__resolve_target_path()`
# @used-by :meth:`Df.Harness.Git.AgentContextDetector.AgentContextDetector.__ancestor_process_names()`
# @used-by :meth:`Df.Harness.Git.CredentialLockCleaner.CredentialLockCleaner.__is_store_running()`
# @used-by :meth:`Df.Harness.Git.WorktreeLockFinder.WorktreeLockFinder.__query_win32()`
# @used-by :meth:`Df.Harness.TestRunner.ProcessTree.ProcessTree.kill()`
# @used-by :meth:`Df.Harness.TestRunner.WatchdogRunner.WatchdogRunner.__build_popen_kwargs()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cli_state_and_hash()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_first_last_starts_with_and_is_windows_delegation_to_df()`
# @used-by :mod:`Df.Harness.TestRunner.ProcessTree`
def df_is_windows() -> bool:
	return dfcf(lambda: 'WIN' == sys.platform[:3].upper())
