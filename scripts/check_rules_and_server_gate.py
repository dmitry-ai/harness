# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
import json
import re
import sys
def check_rules_budget(name: str, args: dict) -> str | None:
	r = None
	path = args.get('Path', '')
	normalized = path.replace('\\', '/').lower() if path else ''
	content = (args.get('Content') if 'write_file' == name else args.get('Replacement')) if '/.agents/rules/' in normalized else None
	if content:
		byte_len = len(content.encode('utf-8'))
		if normalized.endswith('90-project.md') and byte_len > 4000:
			r = f"Size of 90-project.md ({byte_len} bytes) exceeds the 4,000-byte limit to avoid dropping out of the Antigravity system prompt. Run 'python C:/work/research/provision/code/AI/harness/code/scripts/split_project_rules.py' for automatic splitting or move the new section into a separate module .agents/rules/9X-<topic>.md."
		elif re.search('/9[1-9]-[^/]+\\.md$', normalized) and byte_len > 6000:
			r = f'Size of rule module {path} ({byte_len} bytes) exceeds the 6,000-byte limit. Split it into smaller topical modules.'
	return r
def check_server_hygiene(name: str, args: dict) -> str | None:
	r = None
	if 'run_command' == name:
		cmd = args.get('CommandLine', '')
		is_server_cmd = bool(re.search('\\b(nxcli\\.io|nxcli\\.net|ssh\\.exe|ssh\\s+)\\b', cmd, re.IGNORECASE))
		backup_pattern = re.search('(\\.bak\\b|\\.backup\\b|\\.orig\\b|_backup\\w*|cp\\s+.*\\.bak)', cmd, re.IGNORECASE)
		if is_server_cmd and backup_pattern:
			r = 'Creating backup files (*.bak, *.backup, _backup, *.orig) on remote servers is strictly prohibited! Use local Git.'
	elif name in ('write_file', 'edit_file'):
		content = args.get('Content') if 'write_file' == name else args.get('Replacement')
		if content and isinstance(content, str):
			is_server_script = bool(re.search('\\b(nxcli\\.io|nxcli\\.net|ssh\\.exe)\\b', content, re.IGNORECASE))
			has_backup_cmd = bool(re.search('(\\.bak\\b|\\.backup\\b|\\.orig\\b|_backup\\w*|cp\\s+.*\\.bak)', content, re.IGNORECASE))
			if is_server_script and has_backup_cmd:
				r = 'Script contains server backup commands (*.bak, *.backup, _backup)! Creating backups on remote servers is strictly prohibited! Use local Git.'
	return r
def main():
	decision = {'decision': 'allow'}
	try:
		raw = sys.stdin.read()
		if raw.strip():
			payload = json.loads(raw)
			tool_call = payload.get('toolCall', {})
			name = tool_call.get('name', '')
			args = tool_call.get('args', {})
			rule_err = check_rules_budget(name, args)
			if rule_err:
				decision = {'decision': 'deny', 'reason': f'REJECTED (RULES-BUDGET-GATE): {rule_err}'}
			else:
				server_err = check_server_hygiene(name, args)
				if server_err:
					decision = {'decision': 'deny', 'reason': f'REJECTED (SERVER-HYGIENE-GATE): {server_err}'}
	except Exception:
		decision = {'decision': 'allow'}
	sys.stdout.write(json.dumps(decision, ensure_ascii=False))
if '__main__' == __name__:
	main()
