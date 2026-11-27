# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Completion.BudgetEvaluator import BudgetEvaluator
# @used-by unused
def compute_budget_status(root: str | Path, turn: dict[str, Any], *, turns_dir: Path | None=None, read_fn=None, max_checkpoints: int=2, max_tool_steps: int=120, max_window_5h_steps: int=400) -> dict[str, Any]:
	return BudgetEvaluator(root, turn, turns_dir=turns_dir, read_fn=read_fn, max_checkpoints=max_checkpoints, max_tool_steps=max_tool_steps, max_window_5h_steps=max_window_5h_steps).run()