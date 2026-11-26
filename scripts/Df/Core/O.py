# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2017-07-13 Dictionary-backed object supporting deep path access via bracket notation.
# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L3-L167
class O:
	# 2017-07-13
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L31-L55
	# @used-by :meth:`Df.Core.Text.Regex.Regex.i()`
	# @used-by :meth:`Df.Qa.Trace.Frame.Frame.i()`
	# @used-by :meth:`test_df_qa.TestDfQa.test_assert_class_and_other()`
	def __init__(self, a: dict[str, Any] | None=None) -> None:
		self.__a: dict[str, Any] = {} if None is a else a
	# 2017-07-13
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L100-L111
	# @used-by unused
	def __contains__(self, k: Any) -> bool:
		return self.offsetExists(k)
	# 2017-07-13
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L151-L157
	# @used-by unused
	def __delitem__(self, k: Any) -> None:
		self.offsetUnset(k)
	# 2017-07-13
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L113-L139
	# @used-by unused
	def __getitem__(self, k: Any) -> Any:
		return self.offsetGet(k)
	# 2017-07-13
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L141-L149
	# @used-by unused
	def __setitem__(self, k: Any, v: Any) -> None:
		self.offsetSet(k, v)
	# 2017-07-13
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L57-L81
	# @used-by unused
	def a(self, k: Any='', d: Any=None) -> Any:
		from Df.Core.lib.array.select import dfa
		return dfa(self.__a, k, d)
	# 2023-08-25
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L83-L87
	# @used-by unused
	def isEmpty(self) -> bool:
		return not self.__a
	# 2017-07-13
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L89-L98
	# @used-by unused
	def j(self) -> str:
		from Df.Core.lib.json import df_json_encode
		return df_json_encode(self.__a)
	# 2017-07-13
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L100-L111
	# @used-by :meth:`O.__contains__()`
	def offsetExists(self, k: Any) -> bool:
		from Df.Core.lib.array.deep import dfa_deep
		return None is not dfa_deep(self.__a, k)
	# 2017-07-13
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L113-L139
	# @used-by :meth:`O.__getitem__()`
	def offsetGet(self, k: Any) -> Any:
		from Df.Core.lib.array.deep import dfa_deep
		return dfa_deep(self.__a, k)
	# 2017-07-13
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L141-L149
	# @used-by :meth:`O.__setitem__()`
	def offsetSet(self, k: Any, v: Any) -> None:
		from Df.Core.lib.array.deep import dfa_deep_set
		dfa_deep_set(self.__a, k, v)
	# 2017-07-13
	# https://github.com/mage2pro/core/blob/11.6.1/Core/O.php#L151-L157
	# @used-by :meth:`O.__delitem__()`
	def offsetUnset(self, k: Any) -> None:
		from Df.Core.lib.array.deep import dfa_deep_unset
		dfa_deep_unset(self.__a, k)
