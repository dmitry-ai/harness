# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
NAME = 'EXEC-5-ISSUE-FIRST-GATE'
PRIORITY = 100
TOOLS = frozenset({'run_command', 'write_file', 'edit_file'})
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	from ..issue_first_gate import evaluate_pre_tool_use_issue_first
	return evaluate_pre_tool_use_issue_first(name, args, payload or {})
