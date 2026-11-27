# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from Df.Harness.Cleanup.LifecycleEvaluator import LifecycleEvaluator
from Df.Harness.lib.cleanup_lifecycle_ops import dfh_best_activity as _best_activity, dfh_collect_handoff_activity as _collect_handoff_activity, dfh_collect_rename_activity as _collect_rename_activity, dfh_collect_workflow_finalize as _collect_workflow_finalize, dfh_count_post_init_work, dfh_count_project_conversations, dfh_journal_pair_activity as _journal_pair_activity, dfh_load_codex_history_rows, dfh_project_canonical_keys, dfh_resolve_codex_state_dbs, dfh_resolve_readonly_history
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by unused
def count_post_init_work(root: Path) -> int:
	return dfh_count_post_init_work(root)
# @used-by unused
def count_project_conversations(root, ag_projects, homes, catalog, index, path_key_fn, belongs_fn) -> dict[str, int]:
	return dfh_count_project_conversations(root, ag_projects, homes, catalog, index, path_key_fn, belongs_fn)
# @used-by unused
def effective_project_activity(root, state: dict, config: dict, base_dt: datetime, base_basis: str, path_key_fn) -> tuple[datetime, str]:
	return LifecycleEvaluator(root, state, config, base_dt, base_basis, path_key_fn).run()
# @used-by unused
def load_codex_history_rows(homes: dict, globs: dict, guard_fn) -> dict[str, list]:
	return dfh_load_codex_history_rows(homes, globs, guard_fn)
# @used-by unused
def project_canonical_keys(root, path_key_fn) -> list[str]:
	return dfh_project_canonical_keys(root, path_key_fn)
# @used-by unused
def resolve_codex_state_dbs(home: Path | None, glob_raw: str | None) -> list[Path]:
	return dfh_resolve_codex_state_dbs(home, glob_raw)
# @used-by unused
def resolve_readonly_history(config: dict, daily: Path, active_ag: dict, active_homes: dict, *, single_ag_mode: bool=False) -> dict:
	return dfh_resolve_readonly_history(config, daily, active_ag, active_homes, single_ag_mode=single_ag_mode)
