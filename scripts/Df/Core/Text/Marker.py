# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.text.starts_ends import df_ends_with, df_starts_with
from Df.Core.lib.text.trim import df_trim_text_left_right
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2021-12-12 Pair of begin/end delimiters for marking and unmarking strings (e.g., CDATA).
# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Marker.php#L3-L48
class Marker:
	# 2021-12-12
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Marker.php#L5-L9
	# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
	def __init__(self, begin: str, end: str) -> None:
		self.__begin = begin
		self.__end = end
	# 2021-12-12
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Marker.php#L11-L15
	# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
	def mark(self, s: str) -> str:
		return self.__begin + s + self.__end
	# 2021-12-12
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Marker.php#L17-L21
	# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
	def marked(self, s: str) -> str:
		return '1' if df_starts_with(s, self.__begin) and df_ends_with(s, self.__end) else ''
	# 2021-12-12
	# https://github.com/mage2pro/core/blob/11.6.1/Core/Text/Marker.php#L23-L27
	# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part1()`
	def unmark(self, s: str) -> str:
		return df_trim_text_left_right(s, self.__begin, self.__end)
