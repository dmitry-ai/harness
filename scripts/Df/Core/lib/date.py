# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo
import re
from Df.Core.lib.lang.try_ import df_try
from Df.Core.lib.math import df_round
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2016-07-19 Return `d` or current local timezone-aware datetime.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L8-L17
# @used-by :func:`df_date_reset_time()`
# @used-by :func:`df_day_of_week_as_digit()`
# @used-by :func:`df_days_left()`
# @used-by :func:`df_dts()`
# @used-by :func:`df_hour()`
# @used-by :func:`df_month()`
# @used-by :func:`df_num_days()`
# @used-by :func:`df_today_add()`
# @used-by :func:`df_today_sub()`
# @used-by :func:`df_year()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date(d: datetime | None=None) -> datetime:
	return d if None is not d else datetime.now().astimezone()
# Construct a datetime from 1..6 positional components (year, month, day, hour, minute, second).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L19-L29
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date_create(*a: int) -> datetime:
	from Df.Qa.lib.validation.assert_.numeric_comparison import df_assert_between
	df_assert_between(len(a), 1, 6)
	vals = list(a) + [1, 1, 0, 0, 0][max(0, len(a) - 1):]
	return datetime(vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], tzinfo=timezone.utc)
# Parse an ISO-8601 database date string into a datetime.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L31-L39
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date_from_db(s: str, onE: Any=True) -> datetime | None:
	from Df.Qa.lib.validation.param import df_param_sne
	df_param_sne(s, 0)
	return df_try(lambda: datetime.fromisoformat(s.replace('Z', '+00:00')), onE)
# Parse a 14-digit YYYYMMDDHHMMSS timestamp string into a datetime.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L41-L69
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date_from_timestamp_14(timestamp: str, offsetType: str | None=None) -> datetime:
	from Df.Qa.lib.validation.assert_ import df_assert
	from Df.Qa.lib.validation.assert_.array import df_assert_in
	from Df.Qa.lib.validation.assert_.numeric_comparison import df_assert_eq
	df_assert(timestamp.isdigit())
	df_assert_eq(14, len(timestamp))
	m = re.match(r'^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$', timestamp)
	df_assert(None is not m)
	y, mo, da, hr, mi, sc = (int(g) for g in m.groups())
	dt = datetime(y, mo, da, hr, mi, sc, tzinfo=timezone.utc)
	if offsetType:
		df_assert_in(offsetType, ['UTC', 'GMT'])
		off = df_round((datetime.now().astimezone().utcoffset() or timedelta()).total_seconds() / 3600)
		dt = dt + timedelta(hours=off + (1 if 'UTC' == offsetType else 0))
	return dt
# 2016-07-19
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L71-L75
# @used-by :func:`df_date_max()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date_gt(d1: datetime, d2: datetime) -> bool:
	return d1.timestamp() > d2.timestamp()
# 2016-10-15 Unix epoch start datetime (1970-01-01T00:00:00Z).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L77-L81
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date_least() -> datetime:
	return datetime.fromtimestamp(0, tz=timezone.utc)
# 2016-07-19
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L83-L88
# @used-by :func:`df_date_min()`
# @used-by :func:`df_is_date_expired()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date_lt(d1: datetime, d2: datetime) -> bool:
	return d1.timestamp() < d2.timestamp()
# 2016-07-19
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L90-L96
# @used-by :func:`df_num_days()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date_max(d1: datetime, d2: datetime) -> datetime:
	return d1 if df_date_gt(d1, d2) else d2
# 2016-07-19
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L98-L102
# @used-by :func:`df_num_days()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date_min(d1: datetime, d2: datetime) -> datetime:
	return d1 if df_date_lt(d1, d2) else d2
# 2016-07-20 Parse a date string using `fmt` (or ISO-8601) with optional source timezone conversion.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L104-L146
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date_parse(dateS: str, throw: bool=True, fmt: str | None=None, tz: str='') -> datetime | None:
	try:
		parsed = datetime.strptime(dateS, fmt) if fmt else datetime.fromisoformat(dateS.replace('Z', '+00:00'))
		if tz:
			parsed = parsed.replace(tzinfo=ZoneInfo(tz)).astimezone()
		r: datetime | None = parsed
	except Exception:
		if throw:
			raise
		r = None
	return r
# 2016-07-19 Return a copy of `date` (or now) with time reset to 00:00:00.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L148-L158
# @used-by :func:`df_is_date_expired()`
# @used-by :func:`df_num_days()`
# @used-by :func:`df_today_add()`
# @used-by :func:`df_today_sub()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date_reset_time(date: datetime | None=None) -> datetime:
	base = df_date(date)
	return base.replace(hour=0, minute=0, second=0, microsecond=0)
# Format a datetime for database storage (`YYYY-MM-DD HH:MM:SS` or ISO-8601).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L160-L166
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_date_to_db(date: datetime, inCurrentTimeZone: bool=True) -> str:
	return date.strftime('%Y-%m-%d %H:%M:%S') if inCurrentTimeZone else date.isoformat()
# 2016-07-19 Return ISO-8601 weekday digit (1=Monday .. 7=Sunday).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L168-L173
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_day_of_week_as_digit(date: datetime | None=None) -> int:
	return df_date(date).isoweekday()
# 2016-07-19 Signed number of days remaining until `d` (pass through None or int unchanged).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L175-L183
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_days_left(d: datetime | int | None) -> int | None:
	if None is d or (isinstance(d, int) and (not isinstance(d, bool))):
		r: int | None = d
	else:
		r = df_num_days(d, df_date()) * (-1 if df_is_date_expired(d) else 1)
	return r
# 2015-02-07 Format a datetime via strftime (or ISO-8601 when `fmt` is None), asserting non-empty output.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L196-L216
# @used-by :func:`df_dtss()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_dts(d: datetime | None=None, fmt: str | None=None, l: str | None=None) -> str:
	from Df.Qa.lib.validation.result import df_result_sne
	dt = df_date(d)
	return df_result_sne(dt.strftime(fmt) if fmt else dt.isoformat())
# Convert a date string from `sourceFormat` to `resultFormat`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L218-L232
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_dtss(dateInSourceFormat: str, sourceFormat: str, resultFormat: str, canBeEmpty: bool=False) -> str:
	if dateInSourceFormat:
		r = df_dts(datetime.strptime(dateInSourceFormat, sourceFormat), resultFormat)
	else:
		from Df.Qa.lib.validation.assert_ import df_assert
		df_assert(canBeEmpty, 'Empty $dateInSourceFormat is not allowed.')
		r = ''
	return r
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L234-L239
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_hour(date: datetime | None=None) -> int:
	return df_date(date).hour
# 2016-07-19 Return True iff `date` is strictly before today (comparing calendar days).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L241-L245
# @used-by :func:`df_days_left()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_is_date_expired(date: datetime) -> bool:
	return df_date_lt(df_date_reset_time(date), df_date_reset_time())
# 2018-11-13
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L254-L261
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_month(d: datetime | None=None) -> int:
	return df_date(d).month
# 2016-07-09 Format current time using `fmt` and optional IANA timezone `tz`.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L263-L273
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_now(fmt: str, tz: str | None=None) -> str:
	return datetime.now(ZoneInfo(tz) if tz else None).strftime(fmt)
# 2016-07-19 Whole calendar days between `d1` and `d2` (always non-negative).
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L300-L319
# @used-by :func:`df_days_left()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_num_days(d1: datetime | None=None, d2: datetime | None=None) -> int:
	dt1, dt2 = (df_date(d1), df_date(d2))
	a_min = df_date_reset_time(df_date_min(dt1, dt2))
	a_max = df_date_reset_time(df_date_max(dt1, dt2))
	return df_round((a_max.timestamp() - a_min.timestamp()) / 86400)
# 2015-04-07 Midnight datetime `add` days from today.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L321-L328
# @used-by :func:`df_tomorrow()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_today_add(add: int) -> datetime:
	return df_date_reset_time(df_date() + timedelta(days=add))
# 2016-10-15 Midnight datetime `sub` days before today.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L330-L334
# @used-by :func:`df_yesterday()`
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_today_sub(sub: int) -> datetime:
	return df_date_reset_time(df_date() - timedelta(days=sub))
# 2016-10-15
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L336-L340
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_tomorrow() -> datetime:
	return df_today_add(1)
# 2018-11-13
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L342-L349
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_year(date: datetime | None=None) -> int:
	return df_date(date).year
# 2016-10-15
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/date.php#L351-L355
# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_date_helpers()`
def df_yesterday() -> datetime:
	return df_today_sub(1)
