# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
NAME = 'RULES-BUDGET-GATE'
PRIORITY = 10
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
TOOLS = frozenset({'write_file', 'edit_file'})
# 2026-11-26
# "Add deterministic rules-audit CLI and aggregate budget enforcement":
# https://github.com/dmitry-ai/harness/issues/244
def _check_local_rule(name: str, args: dict, path: str, normalized: str) -> str | None:
	r = None
	content = args.get('Content') if 'write_file' == name else args.get('Replacement')
	if content:
		byte_len = len(content.encode('utf-8'))
		if normalized.endswith('90-project.md') and 4000 < byte_len:
			# 2026-11-24
			# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
			# https://github.com/dmitry-ai/harness/issues/187
			from ..runtime import PRIMARY
			r = f"Size of 90-project.md ({byte_len} bytes) exceeds the 4,000-byte limit to avoid dropping out of the Antigravity system prompt. Run 'python {(PRIMARY / 'scripts/split_project_rules.py').as_posix()}' for automatic splitting or move the new section into a separate module .agents/rules/9X-<topic>.md."
		elif re.search('/9[1-9]-[^/]+\\.md$', normalized) and 6000 < byte_len:
			r = f'Size of rule module {path} ({byte_len} bytes) exceeds the 6,000-byte limit. Split it into smaller topical modules.'
	return r
# 2026-11-26
# "Add deterministic rules-audit CLI and aggregate budget enforcement":
# https://github.com/dmitry-ai/harness/issues/244
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	path = str(args.get('Path') or '')
	normalized = path.replace('\\', '/').lower() if path else ''
	if '/.agents/rules/' in normalized:
		r = _check_local_rule(name, args, path, normalized)
	elif re.search('/rules/[^/]+\\.md$', normalized):
		from ..rules_audit import check_shared_rule_edit
		r = check_shared_rule_edit(name, args)
	else:
		r = None
	return r
