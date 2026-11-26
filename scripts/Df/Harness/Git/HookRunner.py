# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Git.AgentContextDetector import AgentContextDetector
from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
import sys
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class HookRunner:
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.run_hook()`
	def __init__(self, gate) -> None:
		self.__gate = gate
	# @used-by :meth:`HookRunner.run()`
	def __run_commit_msg(self, argv: list[str] | tuple[str, ...]) -> None:
		if not argv:
			raise ValueError('commit-msg hook requires message file path argument')
		msg_path = HostPathNormalizer(argv[0]).normalize()
		if not msg_path.is_absolute():
			msg_path = (self.__gate.root / msg_path).resolve()
		raw_msg = msg_path.read_text(encoding='utf-8', errors='replace')
		self.__gate.verify_issue_workflow(self.__gate.staged_paths(), message=raw_msg, agent_context=True)
	# @used-by :meth:`HookRunner.run()`
	def __run_pre_commit(self, is_agent: bool) -> None:
		staged = self.__gate.staged_paths()
		if staged:
			self.__gate.verify_staged_blob_sizes(staged)
			if is_agent:
				self.__gate.verify_agent_staged(staged, use_index=True)
	# @used-by :meth:`HookRunner.run()`
	def __run_pre_push(self, stdin_text: str | None) -> None:
		lines = stdin_text.splitlines() if None is not stdin_text else (sys.stdin.read().splitlines() if not sys.stdin.isatty() else None)
		self.__gate.verify_push_blob_sizes(stdin_lines=lines)
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.run_hook()`
	def run(self, hook_name: str, argv: list[str] | tuple[str, ...]=(), *, stdin_text: str | None=None, agent_context: bool | None=None) -> int:
		is_agent = AgentContextDetector().detect() if None is agent_context else bool(agent_context)
		r = 0
		try:
			if 'pre-commit' == hook_name:
				self.__run_pre_commit(is_agent)
			elif 'commit-msg' == hook_name and is_agent:
				self.__run_commit_msg(argv)
			elif 'pre-push' == hook_name:
				self.__run_pre_push(stdin_text)
		except (OSError, ValueError, RuntimeError) as exc:
			print(f'ERROR (Git hook {hook_name}): {exc}', file=sys.stderr)
			r = 2
		return r
