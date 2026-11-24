# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
NAME = 'CODE-SIZE-RATCHET-GATE'
PRIORITY = 120
TOOLS = frozenset({'write_file', 'edit_file'})
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	from ..code_size_gate import evaluate_pre_tool_use_code_size
	return evaluate_pre_tool_use_code_size(name, args, payload or {})
