# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Exempt service finalization calls from EXEC-2-TDD-GATE and add journal-sync --all-open":
# https://github.com/dmitry-ai/harness/issues/256
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
NAME = 'EXEC-2-TDD-GATE'
PRIORITY = 110
TOOLS = frozenset({'run_command', 'write_file', 'edit_file'})
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	from ..tdd.service_exempt import is_service_finalization_call
	if is_service_finalization_call(name, args, payload):
		r = None
	else:
		from ..tdd_gate import evaluate_pre_tool_use_tdd
		r = evaluate_pre_tool_use_tdd(name, args, payload or {})
	return r
