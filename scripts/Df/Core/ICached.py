# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from abc import ABC, abstractmethod
# 2026-11-26 "Port Df/Core base classes and primitive libraries": https://github.com/dmitry-ai/harness/issues/322
# 2017-08-30
# https://github.com/mage2pro/core/blob/11.6.1/Core/ICached.php#L3-L13
class ICached(ABC):
	# 2017-08-30
	# https://github.com/mage2pro/core/blob/11.6.1/Core/ICached.php#L6-L12
	# @used-by :meth:`Df.Core.RAM.RAM.set()`
	@abstractmethod
	def tags(self) -> list[str]:
		raise NotImplementedError
