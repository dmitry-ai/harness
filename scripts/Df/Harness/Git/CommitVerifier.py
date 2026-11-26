# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class CommitVerifier:
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.check_commit()`
	def __init__(self, gate) -> None:
		self.__gate = gate
	# @used-by :meth:`CommitVerifier.verify()`
	def __check_markdown(self, relative: list[str]) -> None:
		from agent_tools.links import validate_file
		for name in relative:
			path = self.__gate.root / name
			if path.is_file() and '.md' == path.suffix.lower():
				errors = validate_file(path, readable_links=True)
				if errors:
					raise ValueError('\n'.join(errors))
	# @used-by :meth:`CommitVerifier.verify()`
	# @uses :meth:`Df.Harness.Git.RepoGate.RepoGate.staged_paths()`
	def __check_staged_diff(self, relative: list[str]) -> None:
		staged = set(self.__gate.staged_paths())
		if staged != set(relative):
			raise ValueError(f'Staged paths differ from explicit paths: {sorted(staged ^ set(relative))}')
		specs = [f':(literal){p}' for p in relative]
		if self.__gate.git('diff', '--name-only', '-z', '--', *specs):
			raise ValueError('Selected files have unstaged changes; review and stage the intended version')
		if self.__gate.git('diff', '--cached', '--name-only', '--diff-filter=U'):
			raise ValueError('Unresolved merge conflicts')
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.check_commit()`
	# @uses :meth:`Df.Harness.Git.RepoGate.RepoGate.assert_toplevel()`
	# @uses :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_agent_staged()`
	def verify(self, paths: list[str], *, message: str | None=None) -> list[str]:
		from agent_tools.text_workflow import gate_paths
		self.__gate.assert_toplevel()
		self.__gate.ensure_hooks()
		r = self.__gate.normalize_paths(paths)
		self.__check_staged_diff(r)
		self.__check_markdown(r)
		self.__gate.git('diff', '--cached', '--check')
		gate_paths([self.__gate.root / name for name in r])
		self.__gate.verify_staged_blob_sizes(r)
		if None is not message and (not message.strip()):
			raise ValueError('Empty commit message')
		self.__gate.verify_agent_staged(r, message=message, use_index=True)
		return r
