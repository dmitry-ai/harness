# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import os
import platform
from Df.Core.lib.array.first import df_first
from Df.Core.lib.cache.dfcf import dfcf
from Df.Core.lib.cli import df_is_cli
from Df.Core.lib.text.explode import df_explode_space
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# 2017-04-03 Trigger a debugger breakpoint when `cond` is True and PYTHONBREAKPOINT is enabled.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/diagnostics.php#L3
# @used-by :meth:`test_df_qa.TestDfQa.test_diagnostics_and_exceptions()`
def df_break(cond: bool=True) -> None:
	if cond and '0' != os.environ.get('PYTHONBREAKPOINT', '0'):
		breakpoint()
# 2017-01-25 Detect the current web server or CLI runtime string (or [name, version] pair when `asArray` is True).
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/diagnostics.php#L14-L19
# @used-by :meth:`test_df_qa.TestDfQa.test_diagnostics_and_exceptions()`
def df_webserver(asArray: bool=False) -> str | list[str]:
	# @used-by :func:`df_webserver()`
	def _detect(as_arr: bool=False) -> str | list[str]:
		s = os.environ.get('SERVER_SOFTWARE')
		r = str(df_first(df_explode_space(s))) if s else (f'Python CLI/{platform.python_version()}' if df_is_cli() else 'Unknown/Unknown')
		return r.split('/') if as_arr else r
	return dfcf(_detect, [asArray])