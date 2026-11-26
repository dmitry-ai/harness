# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.RAM import RAM
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2017-08-28 Return the process-wide RAM cache singleton.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/cache/o.php#L30-L37
# @used-by :func:`Df.Core.lib.cache.dfcf.dfcf()`
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_cache_dfc_dfcf_and_ram()`
def df_ram() -> RAM:
	return RAM.s()
