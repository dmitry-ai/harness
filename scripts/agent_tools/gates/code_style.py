# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.CodeStylePreToolGate import CodeStylePreToolGate
NAME = CodeStylePreToolGate.NAME
PRIORITY = CodeStylePreToolGate.PRIORITY
TOOLS = CodeStylePreToolGate.TOOLS
# @used-by :meth:`Df.Harness.Gate.PreToolRegistry.PreToolRegistry.__load_builtin_entry()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return CodeStylePreToolGate().check(name, args, payload)
