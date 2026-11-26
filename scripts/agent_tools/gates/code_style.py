# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
NAME = 'CODE-STYLE-GATE'
PRIORITY = 125
TOOLS = frozenset({'write_file', 'edit_file'})
# 2026-11-25
# "Add CODE-1 Python style ratchet linter gate in PreToolUse and pre-commit":
# https://github.com/dmitry-ai/harness/issues/243
# @used-by :func:`agent_tools.gates._load_builtin_entry()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	from ..code_style_gate import evaluate_pre_tool_use_code_style
	return evaluate_pre_tool_use_code_style(name, args, payload or {})