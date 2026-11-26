# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
NAME = 'SERVER-HYGIENE-GATE'
PRIORITY = 20
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
TOOLS = frozenset({'run_command', 'write_file', 'edit_file'})
_BACKUP_RE = re.compile(r'(\.bak\b|\.backup\b|\.orig\b|_backup\w*|cp\s+.*\.bak)', re.IGNORECASE)
_SERVER_CMD_RE = re.compile(r'\b(nxcli\.io|nxcli\.net|ssh\.exe|ssh\s+)\b', re.IGNORECASE)
_SERVER_SCRIPT_RE = re.compile(r'\b(nxcli\.io|nxcli\.net|ssh\.exe)\b', re.IGNORECASE)
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
# @used-by :func:`agent_tools.gates._load_builtin_entry()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r = None
	if 'run_command' == name:
		cmd = args.get('CommandLine', '')
		if _SERVER_CMD_RE.search(cmd) and _BACKUP_RE.search(cmd):
			r = 'Creating backup files (*.bak, *.backup, _backup, *.orig) on remote servers is strictly prohibited! Use local Git.'
	elif name in ('write_file', 'edit_file'):
		content = args.get('Content') if 'write_file' == name else args.get('Replacement')
		if isinstance(content, str) and content and _SERVER_SCRIPT_RE.search(content) and _BACKUP_RE.search(content):
			r = 'Script contains server backup commands (*.bak, *.backup, _backup)! Creating backups on remote servers is strictly prohibited! Use local Git.'
	return r
