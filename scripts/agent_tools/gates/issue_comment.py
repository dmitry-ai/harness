# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26
# "Add PreToolUse and pre-commit gate for issue-comment placement":
# https://github.com/dmitry-ai/harness/issues/273
NAME = 'ISSUE-COMMENT-GATE'
PRIORITY = 126
TOOLS = frozenset({'write_file', 'edit_file'})
# @used-by :func:`agent_tools.gates._load_builtin_entry()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	from ..issue_comment_gate import evaluate_pre_tool_use_issue_comment
	return evaluate_pre_tool_use_issue_comment(name, args, payload or {})
