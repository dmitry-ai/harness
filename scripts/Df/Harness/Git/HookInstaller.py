# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class HookInstaller:
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.ensure_hooks()`
	def __init__(self, gate, *, hooks_dir: Path | None=None) -> None:
		self.__gate = gate
		self.__hooks_dir = hooks_dir
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.ensure_hooks()`
	def install(self) -> Path | None:
		from agent_tools.runtime_snapshot import ensure_repo_git_hooks
		if None is not self.__hooks_dir:
			eff_dir = self.__hooks_dir
		else:
			from agent_tools.path_registry import tool_path
			eff_dir = tool_path('git_hooks_dir')
		return ensure_repo_git_hooks(self.__gate.root, self.__gate.main_repo(), eff_dir)
