# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify process-tree termination in parallel_runner and enforce AST subprocess hygiene in pre-commit":
# https://github.com/dmitry-ai/harness/issues/206
from __future__ import annotations
from ..subprocess_hygiene_gate import evaluate_pre_tool_use_subprocess_hygiene
NAME = 'SUBPROCESS-HYGIENE-GATE'
PRIORITY = 125
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return evaluate_pre_tool_use_subprocess_hygiene(name, args, payload or {})
