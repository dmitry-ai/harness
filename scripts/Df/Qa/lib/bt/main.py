# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
import inspect
from Df.Core.lib.array.find import df_find
from Df.Core.lib.array.part import df_slice
from Df.Core.lib.array.select import dfa
from Df.Core.lib.reflection.text.cts import df_cts
from Df.Qa.lib.bt.throwable import df_bt_th
from Df.Qa.lib.exception import df_is_th
# 2026-11-26 "Port Df/Qa classes and validation libraries": https://github.com/dmitry-ai/harness/issues/325
# Build a normalized backtrace frame dict from a live Python frame object.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/main.php#L16-L37
# @used-by :func:`Df.Qa.lib.bt.throwable.df_bt_th()`
# @used-by :func:`df_bt()`
def _frame_dict(frame: Any, lineno: int | None=None) -> dict[str, Any]:
	fn = frame.f_code.co_name
	r: dict[str, Any] = {'file': frame.f_code.co_filename, 'function': fn, 'line': frame.f_lineno if None is lineno else lineno}
	cls_name = _mro_class(frame, fn) or _qual_class(frame, fn)
	if cls_name:
		r['class'] = cls_name
	return r
# Find the declaring class in MRO for a frame carrying `self` or `cls`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/main.php#L16-L37
# @used-by :func:`_frame_dict()`
def _mro_class(frame: Any, fn: str) -> str:
	self_obj = frame.f_locals.get('self')
	cls_obj = frame.f_locals.get('cls')
	cand = type(self_obj) if None is not self_obj else (cls_obj if isinstance(cls_obj, type) else None)
	r = ''
	if None is not cand:
		for base in cand.__mro__:
			if fn in base.__dict__:
				r = df_cts(base)
				break
	return r
# Infer enclosing class name from co_qualname for staticmethod frames without `self`/`cls`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/main.php#L16-L37
# @used-by :func:`_frame_dict()`
def _qual_class(frame: Any, fn: str) -> str:
	qn = str(getattr(frame.f_code, 'co_qualname', ''))
	suf = f'.{fn}'
	r = ''
	if qn.endswith(suf):
		prefix = qn[:-len(suf)]
		if prefix and (not prefix.endswith('<locals>')):
			mod = str(frame.f_globals.get('__name__', ''))
			r = f'{mod}.{prefix}' if mod else prefix
	return r
# 2021-10-04 Capture the call stack (or exception trace), with entry 0 being the caller of df_bt().
# 2023-07-27 "Shift the `file` and `line` keys to an entry back in `df_bt()`": https://github.com/mage2pro/core/issues/283
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/main.php#L16-L37
# @used-by :func:`Df.Core.lib.caller.entry.df_caller_entry()`
# @used-by :func:`Df.Qa.lib.bt.log.df_bt_s()`
# @used-by :func:`df_bt_has()`
# @used-by :meth:`Df.Qa.Failure.Exception.Exception._trace()`
# @used-by :meth:`Df.Qa.Method.Method.__caller()`
# @used-by :meth:`test_df_qa.TestDfQa.test_bt_helpers()`
def df_bt(p: Any=0, limit: int=0) -> list[dict[str, Any]]:
	if isinstance(p, list):
		r = [dict(e) for e in p]
	elif df_is_th(p):
		r = df_bt_th(p)
	else:
		skip = 0 if None is p else int(p)
		cur = inspect.currentframe()
		cur = cur.f_back if None is not cur else None
		frames: list[dict[str, Any]] = []
		while None is not cur:
			frames.append(_frame_dict(cur))
			if 0 < limit and skip + limit <= len(frames):
				break
			cur = cur.f_back
		r = list(df_slice(frames, skip, limit))
	return r
# 2020-05-25 Return True iff the call stack (or exception `t`) contains class `c` and method `m`.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/main.php#L43-L46
# @used-by :meth:`test_df_qa.TestDfQa.test_bt_helpers()`
def df_bt_has(c: str, m: str='', t: BaseException | None=None) -> bool:
	cls_name, meth = (c, m) if m else tuple(c.split('::', 1))
	return bool(df_find(lambda i: cls_name == dfa(i, 'class') and meth == dfa(i, 'function'), df_bt(t)))
# 2021-10-04 Increment a numeric stack offset `p` by `o`, passing arrays and exceptions through unchanged.
# https://github.com/mage2pro/core/blob/11.6.1/Qa/lib/bt/main.php#L57
# @used-by :func:`Df.Core.lib.caller.entry.df_caller_entry()`
# @used-by :func:`Df.Qa.lib.bt.log.df_bt_s()`
# @used-by :meth:`test_df_qa.TestDfQa.test_bt_helpers()`
def df_bt_inc(p: Any, o: int=1) -> Any:
	return p if isinstance(p, list) or df_is_th(p) else o + int(p or 0)