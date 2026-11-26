# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.IssueCommentPreToolGate import IssueCommentPreToolGate
NAME = IssueCommentPreToolGate.NAME
PRIORITY = IssueCommentPreToolGate.PRIORITY
TOOLS = IssueCommentPreToolGate.TOOLS
# @used-by :meth:`Df.Harness.Gate.PreToolRegistry.PreToolRegistry.__load_builtin_entry()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return IssueCommentPreToolGate().check(name, args, payload)
