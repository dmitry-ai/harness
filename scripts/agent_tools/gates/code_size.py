# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
NAME = 'CODE-SIZE-RATCHET-GATE'
PRIORITY = 120
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
TOOLS = frozenset({'write_file', 'edit_file'})
# @used-by :func:`agent_tools.gates._load_builtin_entry()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	# 2026-11-24
	# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
	# https://github.com/dmitry-ai/harness/issues/187
	from ..code_size_gate import evaluate_pre_tool_use_code_size
	return evaluate_pre_tool_use_code_size(name, args, payload or {})
