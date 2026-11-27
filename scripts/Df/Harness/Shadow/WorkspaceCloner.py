# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import os
import shutil
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class WorkspaceCloner:
	# @used-by :func:`Df.Harness.lib.shadow_command._stage_shadow_launcher()`
	# @used-by :func:`Df.Harness.lib.shadow_command.dfh_stage_command_shadow_copies()`
	# @used-by :func:`agent_tools.shadow_replay_clone.clone_project_tree()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.__prepare_stage()`
	# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_shadow_clone_and_command_ops()`
	def __init__(self, src_root: Path, dst_root: Path, *, hardlink_evidence: bool=True) -> None:
		self.__src = Path(src_root).resolve()
		self.__dst = Path(dst_root).resolve()
		self.__hardlink_evidence = hardlink_evidence
	# @used-by :meth:`WorkspaceCloner.run()`
	@staticmethod
	def __copy_file(src: Path, dst: Path, *, hardlink: bool) -> None:
		dst.parent.mkdir(parents=True, exist_ok=True)
		linked = False
		if hardlink:
			try:
				os.link(src, dst)
				linked = True
			except OSError:
				linked = False
		if not linked:
			shutil.copy2(src, dst)
	# @used-by :meth:`WorkspaceCloner.run()`
	@staticmethod
	def __is_evidence(rel: Path) -> bool:
		parts = rel.parts
		return 3 <= len(parts) and '\ua616' == parts[0] and 'KB' == parts[1] and 'Evidence' == parts[2]
	# @used-by :func:`Df.Harness.lib.shadow_command._stage_shadow_launcher()`
	# @used-by :func:`Df.Harness.lib.shadow_command.dfh_stage_command_shadow_copies()`
	# @used-by :func:`agent_tools.shadow_replay_clone.clone_project_tree()`
	# @used-by :meth:`Df.Harness.Shadow.ReplayRunner.ReplayRunner.__prepare_stage()`
	# @used-by :meth:`test_df_harness_s11_wave2d_shadow_runtime_cov.DfHarnessS11Wave2dShadowRuntimeCovTests.test_shadow_clone_and_command_ops()`
	def run(self) -> None:
		from Df.Harness.lib.project import dfh_is_skipped_rel
		self.__dst.mkdir(parents=True, exist_ok=True)
		for item in sorted(self.__src.rglob('*')):
			rel = item.relative_to(self.__src)
			if dfh_is_skipped_rel(rel):
				continue
			target = self.__dst / rel
			if item.is_dir():
				target.mkdir(parents=True, exist_ok=True)
			elif item.is_file():
				self.__copy_file(item, target, hardlink=self.__hardlink_evidence and self.__is_evidence(rel))
		(self.__dst / '\ua616/data/scratch').mkdir(parents=True, exist_ok=True)
