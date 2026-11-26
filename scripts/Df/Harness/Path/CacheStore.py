# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import json
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class CacheStore:
	# @used-by :func:`agent_tools.path_cache.resolve_code_anchor()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_path_subsystem_classes()`
	def __init__(self, anchor_dir: Path) -> None:
		self.__anchor = Path(anchor_dir).resolve()
	# @used-by :meth:`CacheStore.run()`
	def __linked_worktree_main_repo(self) -> Path | None:
		r: Path | None = None
		dot_git = self.__anchor / '.git'
		if dot_git.is_file():
			try:
				txt = dot_git.read_text(encoding='utf-8', errors='replace').strip()
				if txt.lower().startswith('gitdir:'):
					raw = txt.split(':', 1)[1].strip()
					gitdir = Path(raw) if Path(raw).is_absolute() else (self.__anchor / raw).resolve()
					if 'worktrees' == gitdir.parent.name and '.git' == gitdir.parent.parent.name:
						r = gitdir.parent.parent.parent.resolve()
			except OSError:
				r = None
		return r
	# @used-by :meth:`CacheStore.run()`
	def __snapshot_canonical_primary(self, meta_file: Path) -> Path | None:
		r: Path | None = None
		try:
			meta = json.loads(meta_file.read_text(encoding='utf-8-sig'))
			canon = meta.get('canonical_primary') if isinstance(meta, dict) else None
			if isinstance(canon, str) and canon.strip():
				r = Path(canon.strip()).resolve()
		except (OSError, ValueError):
			r = None
		return r
	# @used-by :func:`agent_tools.path_cache.resolve_code_anchor()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_path_subsystem_classes()`
	def run(self) -> Path:
		meta_file = self.__anchor / 'snapshot.json'
		if meta_file.is_file():
			hit = self.__snapshot_canonical_primary(meta_file)
			r = hit if None is not hit else self.__anchor
		else:
			wt_main = self.__linked_worktree_main_repo()
			r = wt_main if None is not wt_main else self.__anchor
		return r
