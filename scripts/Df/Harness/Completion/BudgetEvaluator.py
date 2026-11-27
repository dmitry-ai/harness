# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_resolve import dfh_project_paths
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_TERMINAL_STATUSES = frozenset({'conflict', 'delivered', 'handed_off'})
_WINDOW_5H_SECONDS = 18000
class BudgetEvaluator:
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_budget_status()`
	# @used-by :func:`agent_tools.budget.compute_budget_status()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_completion_subsystem_classes()`
	def __init__(self, root: str | Path, turn: dict[str, Any], *, turns_dir: Path | None=None, read_fn=None, max_checkpoints: int=2, max_tool_steps: int=120, max_window_5h_steps: int=400) -> None:
		self.__root = Path(root)
		self.__turn = turn
		self.__turns_dir = turns_dir
		self.__read_fn = read_fn or (lambda p: json.loads(p.read_bytes().decode('utf-8')))
		self.__max_checkpoints = max_checkpoints
		self.__max_tool_steps = max_tool_steps
		self.__max_window_5h_steps = max_window_5h_steps
	# @used-by :meth:`BudgetEvaluator.run()`
	def __active_window_5h_steps(self, turns_dir: Path, cur_tid: Any, tool_steps: int) -> int:
		now_ts = datetime.now(timezone.utc).timestamp()
		total = tool_steps
		if turns_dir.is_dir():
			for tf in turns_dir.glob('*.json'):
				if '-' in tf.stem:
					continue
				try:
					if _WINDOW_5H_SECONDS >= now_ts - tf.stat().st_mtime:
						td = self.__read_fn(tf)
						if td.get('native_turn_id') != cur_tid and td.get('status') not in _TERMINAL_STATUSES:
							total += int((td.get('delegation_check') or {}).get('tool_step_count') or 0)
				except (OSError, ValueError):
					pass
		return total
	# @used-by :func:`Df.Harness.lib.completion_checks.dfh_budget_status()`
	# @used-by :func:`agent_tools.budget.compute_budget_status()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_completion_subsystem_classes()`
	def run(self) -> dict[str, Any]:
		pp = dfh_project_paths(self.__root, exact_root=True)
		turns_dir = self.__turns_dir if None is not self.__turns_dir else (pp.turns_dir if pp.has_explicit_path('turns_dir') else pp.data_dir / 'turns')
		is_client_proj = pp.project_json.is_file()
		cp_count = len((self.__turn.get('compaction') or {}).get('checkpoint_steps') or ())
		tool_steps = int((self.__turn.get('delegation') or {}).get('tool_step_count') or 0)
		window_5h_steps = self.__active_window_5h_steps(turns_dir, self.__turn.get('turn_id'), tool_steps) if is_client_proj else tool_steps
		cont_low = pp.continuation_md.as_posix().lower()
		kb_prefix = pp.kb_dir.as_posix().lower().rstrip('/') + '/'
		touched = [str(x).replace('\\', '/').lower() for x in (self.__turn.get('touched_files') or ())]
		continuation_saved = any((x.endswith('/data/continuation.md') or x.endswith('\ua616/data/continuation.md') or x == cont_low for x in touched))
		kb_saved = any(('/\ua616/kb/' in x or x.endswith('/kb/analysis.md') or x.endswith('/kb/analysis.json') or x.startswith(kb_prefix) for x in touched))
		exceeded = bool(is_client_proj and (cp_count >= self.__max_checkpoints or tool_steps >= self.__max_tool_steps or window_5h_steps >= self.__max_window_5h_steps))
		return {'verified': True, 'checkpoint_count': cp_count, 'max_checkpoints': self.__max_checkpoints, 'tool_step_count': tool_steps, 'max_tool_steps': self.__max_tool_steps, 'window_5h_tool_steps': window_5h_steps, 'max_window_5h_tool_steps': self.__max_window_5h_steps, 'client_artifacts_scoped': is_client_proj, 'graceful_checkpoint_required': exceeded, 'continuation_saved': continuation_saved, 'kb_saved': kb_saved}
