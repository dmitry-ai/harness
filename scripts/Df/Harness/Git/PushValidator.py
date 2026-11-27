# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.AgentContextDetector import AgentContextDetector
from Df.Harness.Git.CommitArgsParser import CommitArgsParser
from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
from Df.Harness.Git.ShellInspector import ShellInspector
from Df.Harness.lib.shell import dfh_normalize_commit_message, dfh_parse_issue_url
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class PushValidator:
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_write_invocation()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_git.DfHarnessS11Wave2CCovGitTests.test_push_validator_commit_msg_file_and_specs()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def __init__(self, gate) -> None:
		self.__gate = gate
	# @used-by :meth:`PushValidator.__verify_commit()`
	@staticmethod
	def __read_commit_msg(msg: str | None, msg_file: str | None, cwd: Path | None) -> str | None:
		r = msg
		if None is r and msg_file and '-' != msg_file:
			mf = HostPathNormalizer(msg_file).normalize()
			if not mf.is_absolute():
				mf = (HostPathNormalizer(cwd or Path.cwd()).normalize() / mf).resolve()
			if mf.is_file():
				r = mf.read_text(encoding='utf-8', errors='replace')
		return r
	# @used-by :meth:`PushValidator.__verify_commit()`
	def __resolve_commit_specs(self, pathspecs: list[str]) -> list[str]:
		clean: list[str] = []
		for sp in pathspecs:
			s = sp[len(':(literal)'):] if sp.startswith(':(literal)') else sp
			p = (self.__gate.root / HostPathNormalizer(s).normalize()).resolve()
			if p.is_relative_to(self.__gate.root):
				clean.append(p.relative_to(self.__gate.root).as_posix())
		if not clean:
			try:
				clean = self.__gate.staged_paths()
			except RuntimeError:
				clean = []
		return clean
	# @used-by :meth:`PushValidator.validate()`
	def __verify_commit(self, argv: list[str] | tuple[str, ...], cwd: Path | None, is_agent: bool) -> None:
		_, msg, msg_file, no_verify, all_flag, pathspecs = CommitArgsParser(argv).parse()
		if is_agent:
			if no_verify:
				raise ValueError('EXEC-5 violation: git commit --no-verify/-n is prohibited for agents')
			if all_flag:
				raise ValueError('EXEC-5 violation: git commit -a/--all is prohibited for agents; stage and commit only an explicit file list')
			msg = self.__read_commit_msg(msg, msg_file, cwd)
			if None is not msg and None is dfh_parse_issue_url(dfh_normalize_commit_message(msg)):
				raise ValueError('EXEC-5 violation: commit message for an agent commit must contain only the GitHub Issue URL (https://github.com/<owner>/<repo>/issues/<N>)')
		if (self.__gate.root / '.git').exists():
			clean = self.__resolve_commit_specs(pathspecs)
			if clean:
				self.__gate.verify_staged_blob_sizes(clean)
				if is_agent:
					self.__gate.verify_agent_staged(clean, message=msg, use_index=not bool(pathspecs))
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.verify_write_invocation()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_git.DfHarnessS11Wave2CCovGitTests.test_push_validator_commit_msg_file_and_specs()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def validate(self, argv: list[str] | tuple[str, ...], *, subcommand: str | None=None, cwd: Path | None=None, agent_context: bool | None=None) -> None:
		cmd_name = subcommand if None is not subcommand else ShellInspector().classify_git_argv(argv)[0]
		if cmd_name in ('commit', 'push', 'filter-branch', 'merge', 'rebase', 'cherry-pick'):
			self.__gate.ensure_hooks()
			is_agent = AgentContextDetector().detect() if None is agent_context else bool(agent_context)
			if 'filter-branch' == cmd_name and is_agent:
				raise ValueError('EXEC-5 violation: git filter-branch is prohibited for agents')
			if 'push' == cmd_name:
				if '--no-verify' in argv and is_agent:
					raise ValueError('EXEC-5 violation: git push --no-verify is prohibited for agents')
				self.__gate.verify_push_blob_sizes()
			elif 'commit' == cmd_name:
				self.__verify_commit(argv, cwd, is_agent)
