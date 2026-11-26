# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# Assert that `v` is stringable, convert it to a string, and dump it safely.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/type/conversion/string.php#L2-L23
# @used-by :func:`Df.Qa.lib.dump.type.df_type()`
# @used-by :meth:`Df.Qa.Dumper.Dumper.__dumpObject()`
# @used-by :meth:`test_df_upstream_fixes.TestDfUpstreamFixes.test_336_df_assert_stringable_returns_value()`
def df_string(v: Any) -> str:
	from Df.Qa.lib.dump import df_dump
	from Df.Qa.lib.validation.assert_.stringable import df_assert_stringable
	val = df_assert_stringable(v)
	return df_dump('' if None is val else str(val))
