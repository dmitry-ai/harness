# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
from ..tdd_gate import evaluate_pre_tool_use_tdd
NAME = 'EXEC-2-TDD-GATE'
PRIORITY = 110
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return evaluate_pre_tool_use_tdd(name, args, payload or {})
