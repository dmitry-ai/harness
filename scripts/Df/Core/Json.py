# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.lang.prop.custom import DF_N, df_prop
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2023-08-04
# https://github.com/mage2pro/core/blob/11.6.1/Core/Json.php#L3-L13
class Json:
	# 2023-08-04 "Implement `df_json_dont_sort()`": https://github.com/mage2pro/core/issues/313
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Json.php#L5-L12
	# @used-by :func:`Df.Core.lib.json.df_json_dont_sort()`
	# @used-by :func:`Df.Core.lib.json.df_json_sort()`
	# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_exception_and_json_class()`
	@staticmethod
	def bSort(v: Any=DF_N) -> Any:
		return df_prop(None, v, True)
