# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import getpass
import sys
from Df.Core.lib.cache.dfcf import dfcf
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2017-03-15 Zero-indexed argv element is the current script name; with i=None returns all argv elements.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/cli.php#L2-L15
# @used-by :func:`df_cli_cmd()`
# @used-by :func:`df_cli_script()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cli_state_and_hash()`
def df_cli_argv(i: int | None=None) -> str | list[str]:
	argv = list(sys.argv)
	if None is i:
		r: str | list[str] = argv
	else:
		r = argv[i] if 0 <= i < len(argv) else ''
	return r
# 2020-05-24
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/cli.php#L17-L21
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cli_state_and_hash()`
def df_cli_cmd() -> str:
	from Df.Core.lib.text.concatenate import df_cc_s
	return df_cc_s(df_cli_argv())
# 2020-02-15
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/cli.php#L23-L27
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cli_state_and_hash()`
def df_cli_script() -> str:
	return str(df_cli_argv(0))
# 2016-12-23 http://stackoverflow.com/a/7771601
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/cli.php#L29-L34
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cli_state_and_hash()`
def df_cli_user() -> str:
	return dfcf(lambda: getpass.getuser())
# 2016-10-25 http://stackoverflow.com/a/1042533
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/cli.php#L44-L54
# @used-by :func:`Df.Qa.lib.diagnostics.df_webserver()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cli_state_and_hash()`
def df_is_cli() -> bool:
	return bool(getattr(sys, 'argv', None))
