# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
NAME = 'EXEC-4-SCHEDULE-GATE'
PRIORITY = 95
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
TOOLS = frozenset({'schedule'})
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	# 2026-11-24
	# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
	# https://github.com/dmitry-ai/harness/issues/187
	from ..failfast_gate import evaluate_pre_tool_use_schedule
	return evaluate_pre_tool_use_schedule(name, args, payload or {})
