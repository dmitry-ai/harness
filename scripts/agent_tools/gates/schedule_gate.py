# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
from ..failfast_gate import evaluate_pre_tool_use_schedule
NAME = 'EXEC-4-SCHEDULE-GATE'
PRIORITY = 95
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return evaluate_pre_tool_use_schedule(name, args, payload or {})
