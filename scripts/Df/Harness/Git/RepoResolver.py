# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.GitGlobalOptsScanner import GitGlobalOptsScanner
from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class RepoResolver:
	# @used-by :func:`agent_tools.git_gate.resolve_git_repo_from_argv()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	def __init__(self, argv: list[str] | tuple[str, ...], cwd: Path | None=None) -> None:
		self.__argv = argv
		self.__cwd = cwd
	# @used-by :func:`agent_tools.git_gate.resolve_git_repo_from_argv()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	def resolve(self) -> Path | None:
		base_dir = HostPathNormalizer(self.__cwd).normalize().resolve() if None is not self.__cwd else Path.cwd().resolve()
		_, _, target_dir = GitGlobalOptsScanner(self.__argv, base_dir=base_dir).scan()
		r = None
		for anc in (target_dir, *target_dir.parents):
			if (anc / '.git').exists():
				r = anc
				break
		return r
