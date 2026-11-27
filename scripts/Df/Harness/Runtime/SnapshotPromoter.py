# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from Df.Harness.lib.runtime_snapshot_ops import REQUIRED_ENTRYPOINTS, dfh_deploy_git_hooks, dfh_export_git_archive, dfh_has_git_head, dfh_read_pointer, dfh_rotate_releases, dfh_runtime_store_dir, dfh_set_local_hooks_path, dfh_validate_staged_release
from Df.Harness.lib.snapshot_canary_ops import dfh_finalize_snapshot_promotion
from Df.Harness.lib.storage import dfh_locked, dfh_replace_bytes
import json
import os
import shutil
import uuid
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class SnapshotPromoter:
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_runtime_promote()`
	# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_finalize_native_install()`
	# @used-by :func:`agent_tools.runtime_snapshot.promote_runtime_snapshot()`
	def __init__(self, primary: str | Path, *, store_dir: str | Path | None=None, keep: int=5, entrypoints: tuple[str, ...]=(), configure_repo_hooks: bool=True, fail_on_fallback_spike: bool=False, base_ref: str | None=None, canary_fn: Any=None) -> None:
		self.__primary = Path(primary).resolve()
		self.__store_dir = store_dir
		self.__keep = keep
		self.__entrypoints = entrypoints
		self.__configure_repo_hooks = configure_repo_hooks
		self.__fail_on_fallback_spike = fail_on_fallback_spike
		self.__base_ref = base_ref
		self.__canary_fn = canary_fn
	# @used-by :meth:`SnapshotPromoter.__promote_locked()`
	def __activate_release(self, store: Path, staging: Path, sha: str) -> dict:
		releases_dir = store / 'releases'
		releases_dir.mkdir(parents=True, exist_ok=True)
		release_dir = releases_dir / sha
		if not release_dir.exists():
			os.replace(staging, release_dir)
		prior = dfh_read_pointer(store)
		old_cur, old_prev = (str(prior.get('current') or '').strip() or None, str(prior.get('previous') or '').strip() or None)
		new_prev = old_cur if old_cur and old_cur != sha else old_prev
		ptr = {'canonical_primary': self.__primary.as_posix(), 'current': sha, 'previous': new_prev, 'updated_at': datetime.now(timezone.utc).isoformat(), 'version': 1}
		dfh_replace_bytes(store / 'current.json', (json.dumps(ptr, ensure_ascii=False, indent='\t', sort_keys=True) + '\n').encode('utf-8'))
		gh_dir = dfh_deploy_git_hooks(store, self.__primary)
		if self.__configure_repo_hooks:
			dfh_set_local_hooks_path(self.__primary, gh_dir)
		pruned = dfh_rotate_releases(releases_dir, self.__keep, {s for s in (sha, new_prev) if s})
		return {'commit_sha': sha, 'git_hooks_dir': gh_dir.as_posix(), 'previous': new_prev, 'promoted': True, 'pruned': pruned, 'release_dir': release_dir.as_posix(), 'store_dir': store.as_posix(), 'valid': True}
	# @used-by :meth:`SnapshotPromoter.run()`
	def __promote_locked(self, store: Path) -> dict:
		from agent_tools.tdd.diff_executability import should_run_snapshot_canary
		staging = store / f'.staging-{uuid.uuid4().hex[:10]}'
		eps = self.__entrypoints or REQUIRED_ENTRYPOINTS
		try:
			sha = dfh_export_git_archive(self.__primary, staging)
			meta = {'canonical_primary': self.__primary.as_posix(), 'commit_sha': sha, 'created_at': datetime.now(timezone.utc).isoformat(), 'schema_version': 1}
			dfh_replace_bytes(staging / 'snapshot.json', (json.dumps(meta, ensure_ascii=False, indent='\t', sort_keys=True) + '\n').encode('utf-8'))
			run_canary, canary_reason = should_run_snapshot_canary(self.__primary, self.__base_ref)
			ok, detail = dfh_validate_staged_release(staging, self.__primary, eps, run_canary=run_canary, canary_fn=self.__canary_fn)
			r = dfh_finalize_snapshot_promotion(store, dfh_read_pointer(store), sha, ok, detail, lambda: self.__activate_release(store, staging, sha), fail_on_fallback_spike=self.__fail_on_fallback_spike)
			r.update(canary_reason=canary_reason, canary_skipped=not run_canary)
		finally:
			shutil.rmtree(staging, ignore_errors=True)
		return r
	# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_runtime_promote()`
	# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_finalize_native_install()`
	# @used-by :func:`agent_tools.runtime_snapshot.promote_runtime_snapshot()`
	def run(self) -> dict:
		if not dfh_has_git_head(self.__primary):
			r = {'promoted': False, 'reason': 'not_a_git_repo', 'skipped': True, 'valid': True}
		else:
			store = dfh_runtime_store_dir(self.__primary, store_dir=self.__store_dir)
			store.mkdir(parents=True, exist_ok=True)
			with dfh_locked(store / 'promote.lock'):
				r = self.__promote_locked(store)
		return r
