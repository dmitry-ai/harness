# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
STR_PAD_BOTH = 2
STR_PAD_LEFT = 0
STR_PAD_RIGHT = 1
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# @used-by :func:`df_pad()`
def _pad_counts(num_pad: int, position: int) -> tuple[int, int]:
	if STR_PAD_RIGHT == position:
		r = (0, num_pad)
	elif STR_PAD_LEFT == position:
		r = (num_pad, 0)
	elif STR_PAD_BOTH == position:
		left = num_pad // 2
		r = (left, num_pad - left)
	else:
		from Df.Qa.lib.validation.error import df_error
		df_error(f'Invalid pad position: {position}')
		r = (0, 0)
	return r
# @used-by :func:`df_pad()`
def _repeat_chars(pattern: str, count: int) -> str:
	plen = len(pattern)
	return ''.join((pattern[i % plen] for i in range(count))) if 0 < plen else ''
# Unicode-aware equivalent of PHP str_pad().
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/text/prepend-append/pad.php#L2-L44
# @used-by :func:`Df.Core.lib.text.prepend_append.pad0.df_pad0()`
# @used-by :func:`Df.Qa.lib.dump.kv.df_kv()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_text_helpers_part2()`
def df_pad(phrase: str, length: int, pattern: str=' ', position: int=STR_PAD_RIGHT) -> str:
	num_pad = length - len(phrase)
	if 0 >= length or 0 >= num_pad:
		r = phrase
	else:
		left_pad, right_pad = _pad_counts(num_pad, position)
		r = _repeat_chars(pattern, left_pad) + phrase + _repeat_chars(pattern, right_pad)
	return r
