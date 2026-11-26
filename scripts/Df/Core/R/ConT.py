# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
from Df.Core.lib.cache.dfcf import dfcf
from Df.Core.lib.reflection.text.check import df_class_exists, df_is_abstract
from Df.Core.lib.reflection.text.cts import df_cts
# 2026-11-26 "Port Df/Core/lib/text and reflection helper libraries": https://github.com/dmitry-ai/harness/issues/324
# 2017-04-01 Convention-over-configuration class resolution helper.
# https://github.com/mage2pro/core/blob/11.6.1/Core/R/ConT.php#L3-L45
class ConT:
	__allow_abstract: bool = False
	# @used-by :meth:`ConT.generic()`
	@staticmethod
	def __resolve(f: Callable[[Any, Any], str], c: Any, suf: Any, df_def: str, throw: bool) -> str | None:
		from Df.Qa.lib.validation.error import df_error
		cand = f(c, suf)
		if df_class_exists(cand):
			if ConT.__allow_abstract or (not df_is_abstract(cand)):
				r: str | None = cand
			else:
				r = None if not throw else df_error(f'The «{cand}» class is abstract.')
		else:
			r = df_def if df_def else (None if not throw else df_error(f'The «{cand}» class is required.'))
		return r
	# 2016-10-26 Convention-over-configuration class lookup with optional fallback and abstract-class guard.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/R/ConT.php#L18-L36
	# @used-by :func:`Df.Core.lib.reflection.text.con_.df_con_child()`
	# @used-by :func:`Df.Core.lib.reflection.text.con_.df_con_sibling()`
	@staticmethod
	def generic(f: Callable[[Any, Any], str], c: Any, suf: Any, df_def: str='', throw: bool=True) -> str | None:
		return dfcf(lambda fn, cls_s, sfx, d, th: ConT.__resolve(fn, cls_s, sfx, d, th), [f, df_cts(c), suf, df_def, throw])
	# 2017-04-01 Temporarily toggle whether ConT.generic() accepts abstract classes during `f()`.
	# https://github.com/mage2pro/core/blob/11.6.1/Core/R/ConT.php#L5-L16
	# @used-by :meth:`test_df_core_text_misc.DfCoreTextMiscTests.test_caller_and_reflection_param()`
	@staticmethod
	def p(allowAbstract: bool, f: Callable[[], Any]) -> Any:
		prev = ConT.__allow_abstract
		ConT.__allow_abstract = allowAbstract
		try:
			r = f()
		finally:
			ConT.__allow_abstract = prev
		return r
