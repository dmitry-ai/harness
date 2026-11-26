# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
class ServerHygieneGate:
	NAME = 'SERVER-HYGIENE-GATE'
	PRIORITY = 20
	TOOLS = frozenset({'run_command', 'write_file', 'edit_file'})
	__BACKUP_RE = re.compile(r'(\.bak\b|\.backup\b|\.orig\b|_backup\w*|cp\s+.*\.bak)', re.IGNORECASE)
	__SERVER_CMD_RE = re.compile(r'\b(nxcli\.io|nxcli\.net|ssh\.exe|ssh\s+)\b', re.IGNORECASE)
	__SERVER_SCRIPT_RE = re.compile(r'\b(nxcli\.io|nxcli\.net|ssh\.exe)\b', re.IGNORECASE)
	# @used-by :func:`agent_tools.gates.server_hygiene.check()`
	def check(self, name: str, args: dict, payload: dict | None=None) -> str | None:
		r = None
		if 'run_command' == name:
			cmd = args.get('CommandLine', '')
			if ServerHygieneGate.__SERVER_CMD_RE.search(cmd) and ServerHygieneGate.__BACKUP_RE.search(cmd):
				r = 'Creating backup files (*.bak, *.backup, _backup, *.orig) on remote servers is strictly prohibited! Use local Git.'
		elif name in ('write_file', 'edit_file'):
			content = args.get('Content') if 'write_file' == name else args.get('Replacement')
			if isinstance(content, str) and content and ServerHygieneGate.__SERVER_SCRIPT_RE.search(content) and ServerHygieneGate.__BACKUP_RE.search(content):
				r = 'Script contains server backup commands (*.bak, *.backup, _backup)! Creating backups on remote servers is strictly prohibited! Use local Git.'
		return r
