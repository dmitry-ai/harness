# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
NAME = 'EXEC-5-GIT-GATE'
PRIORITY = 30
TOOLS = frozenset({'run_command'})
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r = None
	if 'run_command' == name:
		from ..git_gate import prohibited_git_write_commands
		violations = prohibited_git_write_commands(args.get('CommandLine', ''))
		r = '; '.join(violations) if violations else None
	return r
