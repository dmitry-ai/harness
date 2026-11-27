# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.journal_integrity_ops import dfh_prune_terminal_conflict_reservations
from Df.Harness.lib.journal_sync_ops import dfh_rebuild_pending_index, dfh_run_all_open_sweep
from Df.Harness.lib.path_resolve import dfh_load_registry
from Df.Harness.lib.path_schema import dfh_canonicalize_root_dir
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class OpenTurnSyncer:
	# @used-by :func:`Df.Harness.lib.completion_commands.dfh_sync()`
	# @used-by :func:`agent_tools.journal_sync_all.sync_all_open()`
	def __init__(self, root: Path, *, journal_directory: Any=None, adopt_conflict: bool=False, from_step: int=0, folder_fn: Any, dir_fn: Any, read_fn: Any, sync_fn: Any) -> None:
		self.__root = Path(root)
		self.__journal_directory = journal_directory
		self.__adopt_conflict = adopt_conflict
		self.__from_step = from_step
		self.__folder_fn = folder_fn
		self.__dir_fn = dir_fn
		self.__read_fn = read_fn
		self.__sync_fn = sync_fn
	# @used-by :func:`Df.Harness.lib.completion_commands.dfh_sync()`
	# @used-by :func:`agent_tools.journal_sync_all.sync_all_open()`
	def run(self) -> dict[str, Any]:
		root_p = dfh_canonicalize_root_dir(self.__root, dfh_load_registry())
		jdir = self.__dir_fn(root_p, self.__journal_directory)
		pruned_conflicts = dfh_prune_terminal_conflict_reservations(root_p, jdir, folder_fn=self.__folder_fn, read_fn=self.__read_fn)
		synced, skipped = dfh_run_all_open_sweep(root_p, jdir, self.__journal_directory, adopt_conflict=self.__adopt_conflict, from_step=self.__from_step, folder_fn=self.__folder_fn, read_fn=self.__read_fn, sync_fn=self.__sync_fn)
		dfh_rebuild_pending_index(root_p, folder_fn=self.__folder_fn, read_fn=self.__read_fn)
		valid = all((bool((item.get('result') or {}).get('valid')) for item in synced))
		return {'adopt_conflict': bool(self.__adopt_conflict), 'all_open': True, 'journal': str(jdir), 'pruned_conflict_reservations': pruned_conflicts, 'skipped': skipped, 'skipped_count': len(skipped), 'synced': synced, 'synced_count': len(synced), 'valid': valid}
