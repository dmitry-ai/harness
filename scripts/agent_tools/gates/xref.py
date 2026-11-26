# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26
# "Enforce cross-reference compliance in PreToolUse and Git gates":
# https://github.com/dmitry-ai/harness/issues/306
NAME = 'XREF-GATE'
PRIORITY = 127
TOOLS = frozenset({'write_file', 'edit_file'})
# @used-by :func:`agent_tools.gates._load_builtin_entry()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	from ..xref_gate import evaluate_pre_tool_use_xref
	return evaluate_pre_tool_use_xref(name, args, payload or {})
