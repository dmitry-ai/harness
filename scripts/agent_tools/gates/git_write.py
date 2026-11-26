# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
NAME = 'EXEC-5-GIT-GATE'
PRIORITY = 30
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
TOOLS = frozenset({'run_command'})
# @used-by :func:`agent_tools.gates._load_builtin_entry()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r = None
	if 'run_command' == name:
		# 2026-11-24
		# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
		# https://github.com/dmitry-ai/harness/issues/187
		from ..git_gate import prohibited_git_write_commands
		# 2026-11-26 "Block raw worktree removal and fail closed on locked cleanup": https://github.com/dmitry-ai/harness/issues/303
		from ..worktree_guard import prohibited_worktree_remove_commands
		cmd = args.get('CommandLine', '')
		violations = [*prohibited_git_write_commands(cmd), *prohibited_worktree_remove_commands(cmd)]
		r = '; '.join(violations) if violations else None
	return r
