# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
from ..git_gate import prohibited_git_write_commands
NAME = 'EXEC-5-GIT-GATE'
PRIORITY = 30
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r = None
	if 'run_command' == name:
		violations = prohibited_git_write_commands(args.get('CommandLine', ''))
		r = '; '.join(violations) if violations else None
	return r
