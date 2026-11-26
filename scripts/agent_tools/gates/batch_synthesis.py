# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-23
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
NAME = 'VERIFY-1-BATCH-SYNTHESIS-GATE'
PRIORITY = 60
# 2026-11-24
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
TOOLS = frozenset({'run_command', 'write_file', 'edit_file'})
_ANALYSIS_RE = re.compile('analysis' + '\\.md', re.I)
_WRITE_CALL_RE = re.compile('\\b(?:write_' + 'text|write_' + 'bytes|open\\s*\\()\\b')
# @used-by :func:`agent_tools.gates._load_builtin_entry()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r = None
	if name in ('write_file', 'edit_file'):
		path = (args.get('Path') or '').replace('\\', '/').lower()
		content = args.get('Content') if 'write_file' == name else args.get('Replacement')
		in_staging = ('/scratch/' in path or '/\ua616/' in path) and ('/data/worktrees/' not in path)
		if path.endswith('.py') and in_staging and isinstance(content, str) and _ANALYSIS_RE.search(content) and _WRITE_CALL_RE.search(content):
			r = 'FILE-5 / EXEC-1 / VERIFY-1: Writing batch Python generator scripts in scratch/ to synthesize analysis.md files from memory is prohibited. Write each analysis.md directly from its primary source.md or delegate via invoke_subagent.'
	elif 'run_command' == name and re.search('build_analyses\\.py', args.get('CommandLine') or '', re.I):
		r = 'FILE-5 / EXEC-1 / VERIFY-1: Executing batch analysis.md synthesis scripts is prohibited.'
	return r
