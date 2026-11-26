# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.ServiceExempt import ServiceExempt
# @used-by :mod:`agent_tools.tdd.service_exempt`
def is_service_finalization_call(name: str, args: dict[str, Any], payload: dict[str, Any] | None=None) -> bool:
	return ServiceExempt().is_exempt(name, args, payload)
__all__ = ['is_service_finalization_call']
