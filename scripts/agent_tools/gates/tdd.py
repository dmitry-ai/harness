# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
NAME = 'EXEC-2-TDD-GATE'
PRIORITY = 110
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
TOOLS = frozenset({'run_command', 'write_file', 'edit_file'})
# @used-by :func:`agent_tools.gates._load_builtin_entry()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	# 2026-11-26
	# "Exempt service finalization calls from PreToolUse TDD gate and add journal-sync --all-open":
	# https://github.com/dmitry-ai/harness/issues/256
	from ..tdd.service_exempt import is_service_finalization_call
	if is_service_finalization_call(name, args, payload):
		r = None
	else:
		# 2026-11-24
		# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
		# https://github.com/dmitry-ai/harness/issues/187
		from ..tdd_gate import evaluate_pre_tool_use_tdd
		r = evaluate_pre_tool_use_tdd(name, args, payload or {})
	return r
