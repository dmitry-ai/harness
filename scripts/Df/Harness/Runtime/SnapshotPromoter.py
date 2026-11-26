# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
import uuid
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class SnapshotPromoter:
	# @used-by :func:`agent_tools.runtime_snapshot.promote_runtime_snapshot()`
	def __init__(self, primary: str | Path, *, store_dir: str | Path | None=None, keep: int=5, entrypoints: tuple[str, ...]=(), configure_repo_hooks: bool=True, fail_on_fallback_spike: bool=False, base_ref: str | None=None) -> None:
		self.__primary = Path(primary).resolve()
		self.__store_dir = store_dir
		self.__keep = keep
		self.__entrypoints = entrypoints
		self.__configure_repo_hooks = configure_repo_hooks
		self.__fail_on_fallback_spike = fail_on_fallback_spike
		self.__base_ref = base_ref
	# @used-by :meth:`SnapshotPromoter.__promote_locked()`
	def __activate_release(self, store: Path, staging: Path, sha: str) -> dict:
		from agent_tools import runtime_snapshot as rs
		releases_dir = store / 'releases'
		releases_dir.mkdir(parents=True, exist_ok=True)
		release_dir = releases_dir / sha
		if not release_dir.exists():
			os.replace(staging, release_dir)
		prior = rs._read_pointer(store)
		old_cur, old_prev = (str(prior.get('current') or '').strip() or None, str(prior.get('previous') or '').strip() or None)
		new_prev = old_cur if old_cur and old_cur != sha else old_prev
		ptr = {'canonical_primary': self.__primary.as_posix(), 'current': sha, 'previous': new_prev, 'updated_at': datetime.now(timezone.utc).isoformat(), 'version': 1}
		rs.replace_bytes(store / 'current.json', (json.dumps(ptr, ensure_ascii=False, indent='\t', sort_keys=True) + '\n').encode('utf-8'))
		gh_dir = rs._deploy_git_hooks(store, self.__primary)
		if self.__configure_repo_hooks:
			rs._set_local_hooks_path(self.__primary, gh_dir)
		pruned = rs._rotate_releases(releases_dir, self.__keep, {s for s in (sha, new_prev) if s})
		return {'commit_sha': sha, 'git_hooks_dir': gh_dir.as_posix(), 'previous': new_prev, 'promoted': True, 'pruned': pruned, 'release_dir': release_dir.as_posix(), 'store_dir': store.as_posix(), 'valid': True}
	# @used-by :meth:`SnapshotPromoter.run()`
	def __promote_locked(self, store: Path) -> dict:
		from agent_tools import runtime_snapshot as rs
		from agent_tools.snapshot_latency_canary import finalize_snapshot_promotion
		from agent_tools.tdd.diff_executability import should_run_snapshot_canary
		staging = store / f'.staging-{uuid.uuid4().hex[:10]}'
		eps = self.__entrypoints or rs.REQUIRED_ENTRYPOINTS
		try:
			sha = rs._export_git_archive(self.__primary, staging)
			meta = {'canonical_primary': self.__primary.as_posix(), 'commit_sha': sha, 'created_at': datetime.now(timezone.utc).isoformat(), 'schema_version': 1}
			rs.replace_bytes(staging / 'snapshot.json', (json.dumps(meta, ensure_ascii=False, indent='\t', sort_keys=True) + '\n').encode('utf-8'))
			run_canary, canary_reason = should_run_snapshot_canary(self.__primary, self.__base_ref)
			ok, detail = rs._validate_staged_release(staging, self.__primary, eps, run_canary=run_canary)
			r = finalize_snapshot_promotion(store, rs._read_pointer(store), sha, ok, detail, lambda: self.__activate_release(store, staging, sha), fail_on_fallback_spike=self.__fail_on_fallback_spike)
			r.update(canary_reason=canary_reason, canary_skipped=not run_canary)
		finally:
			shutil.rmtree(staging, ignore_errors=True)
		return r
	# @used-by :func:`agent_tools.runtime_snapshot.promote_runtime_snapshot()`
	def run(self) -> dict:
		from agent_tools import runtime_snapshot as rs
		if not rs._has_git_head(self.__primary):
			r = {'promoted': False, 'reason': 'not_a_git_repo', 'skipped': True, 'valid': True}
		else:
			store = rs.runtime_store_dir(self.__primary, store_dir=self.__store_dir)
			store.mkdir(parents=True, exist_ok=True)
			with rs.locked(store / 'promote.lock'):
				r = self.__promote_locked(store)
		return r
