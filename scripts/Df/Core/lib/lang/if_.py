# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.lang.call.if_ import df_call_if
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# Lazy conditional branching for both true and false branches.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/if.php#L2-L9
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def df_if(cond: bool, onTrue: Any, onFalse: Any=None) -> Any:
	return df_call_if(onTrue) if cond else df_call_if(onFalse)
# 2016-02-09 Lazy conditional branching for the true branch only.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/if.php#L11-L18
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def df_if1(cond: bool, onTrue: Any, onFalse: Any=None) -> Any:
	return df_call_if(onTrue) if cond else onFalse
# 2016-02-09 Lazy conditional branching for the false branch only.
# https://github.com/mage2pro/core/blob/11.6.1/Core/lib/lang/if.php#L20-L27
# @used-by :meth:`test_df_core_base.DfCoreBaseTests.test_lang_call_if_and_prop()`
def df_if2(cond: bool, onTrue: Any, onFalse: Any=None) -> Any:
	return onTrue if cond else df_call_if(onFalse)
