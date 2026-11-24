# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Convert PreToolUse hook entry points to lazy tool-scoped imports":
# https://github.com/dmitry-ai/harness/issues/187
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# https://github.com/dmitry-ai/harness/issues/79
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract PreToolUse and completion gates into priority plugin registry":
# https://github.com/dmitry-ai/harness/issues/167
from __future__ import annotations
import json
from pathlib import Path
from ..hook_runtime import read_last_user_segment
NAME = 'REVIEW-1-BULK-SOURCE-GATE'
PRIORITY = 70
TOOLS = frozenset({'read_file'})
MAX_UNPERSISTED_SOURCE_READS = 10
def _parse_call_args(raw) -> dict:
	r = raw if isinstance(raw, dict) else {}
	if isinstance(raw, str):
		try:
			parsed = json.loads(raw)
			r = parsed if isinstance(parsed, dict) else {}
		except ValueError:
			r = {}
	return r
def _recent_segment_rows(t_path: Path) -> list[dict]:
	return read_last_user_segment(t_path)[2]
def _update_streak(streak: set[str], cname: str, cargs: dict) -> None:
	if 'invoke_subagent' == cname:
		streak.clear()
	elif cname in ('write_file', 'edit_file'):
		wpath = (cargs.get('Path') or '').replace('\\', '/').lower()
		if wpath.endswith('/kb/analysis.md') or '/\ua616/kb/' in wpath:
			streak.clear()
	elif 'read_file' == cname:
		rpath = (cargs.get('Path') or '').replace('\\', '/').lower()
		if rpath.endswith('/kb/source.md'):
			streak.add(rpath)
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	r = None
	target = (args.get('Path') or '').replace('\\', '/').lower() if 'read_file' == name else ''
	t_raw = (payload or {}).get('transcriptPath') or ''
	if target.endswith('/kb/source.md') and t_raw:
		streak: set[str] = set()
		for row in _recent_segment_rows(Path(t_raw)):
			for call in row.get('tool_calls') or []:
				if isinstance(call, dict):
					_update_streak(streak, call.get('name', ''), _parse_call_args(call.get('args')))
		if target not in streak and len(streak) >= MAX_UNPERSISTED_SOURCE_READS:
			r = f'REVIEW-1 / KB-3: Already read {len(streak)} source.md files in a row without persisting analysis.md or delegating to af-worker (limit: {MAX_UNPERSISTED_SOURCE_READS}). Persist analysis.md for already-read cases or delegate via invoke_subagent before reading more source.md files.'
	return r
