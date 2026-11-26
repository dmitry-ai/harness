# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Scope budget_check graceful checkpoint flag to client-artifact projects":
# https://github.com/dmitry-ai/harness/issues/369
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .path_registry import project_paths
_TERMINAL_STATUSES = frozenset({'conflict', 'delivered', 'handed_off'})
_WINDOW_5H_SECONDS = 18000
# @used-by :func:`compute_budget_status()`
def _active_window_5h_steps(turns_dir: Path, cur_tid: Any, tool_steps: int, read_fn) -> int:
	now_ts = datetime.now(timezone.utc).timestamp()
	total = tool_steps
	if turns_dir.is_dir():
		for tf in turns_dir.glob('*.json'):
			if '-' in tf.stem:
				continue
			try:
				if _WINDOW_5H_SECONDS >= now_ts - tf.stat().st_mtime:
					td = read_fn(tf)
					if td.get('native_turn_id') != cur_tid and td.get('status') not in _TERMINAL_STATUSES:
						total += int((td.get('delegation_check') or {}).get('tool_step_count') or 0)
			except (OSError, ValueError):
				pass
	return total
# @used-by :func:`agent_tools.completion._budget_status()`
def compute_budget_status(root: Path, turn: dict[str, Any], *, turns_dir: Path, read_fn, max_checkpoints: int, max_tool_steps: int, max_window_5h_steps: int) -> dict[str, Any]:
	pp = project_paths(root, exact_root=True)
	is_client_proj = pp.project_json.is_file()
	cp_count = len((turn.get('compaction') or {}).get('checkpoint_steps') or ())
	tool_steps = int((turn.get('delegation') or {}).get('tool_step_count') or 0)
	window_5h_steps = _active_window_5h_steps(turns_dir, turn.get('turn_id'), tool_steps, read_fn) if is_client_proj else tool_steps
	cont_low = pp.continuation_md.as_posix().lower()
	kb_prefix = pp.kb_dir.as_posix().lower().rstrip('/') + '/'
	touched = [str(x).replace('\\', '/').lower() for x in (turn.get('touched_files') or ())]
	continuation_saved = any((x.endswith('/data/continuation.md') or x.endswith('\ua616/data/continuation.md') or x == cont_low for x in touched))
	kb_saved = any(('/\ua616/kb/' in x or x.endswith('/kb/analysis.md') or x.endswith('/kb/analysis.json') or x.startswith(kb_prefix) for x in touched))
	exceeded = bool(is_client_proj and (cp_count >= max_checkpoints or tool_steps >= max_tool_steps or window_5h_steps >= max_window_5h_steps))
	return {'verified': True, 'checkpoint_count': cp_count, 'max_checkpoints': max_checkpoints, 'tool_step_count': tool_steps, 'max_tool_steps': max_tool_steps, 'window_5h_tool_steps': window_5h_steps, 'max_window_5h_tool_steps': max_window_5h_steps, 'client_artifacts_scoped': is_client_proj, 'graceful_checkpoint_required': exceeded, 'continuation_saved': continuation_saved, 'kb_saved': kb_saved}
