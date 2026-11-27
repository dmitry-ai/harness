# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
_CYGDRIVE_RE = re.compile(r'^/(?:cygdrive|mnt)/([a-zA-Z])(?:/(.*))?$')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class HostPathNormalizer:
	# @used-by :func:`Df.Harness.lib.worktree.dfh_prepare_worktrees_base_dir()`
	# @used-by :func:`agent_tools.shell_audit.normalize_host_path()`
	# @used-by :meth:`Df.Harness.Git.CredentialLockCleaner.CredentialLockCleaner.__collect_candidates()`
	# @used-by :meth:`Df.Harness.Git.GitGlobalOptsScanner.GitGlobalOptsScanner.__advance_dir()`
	# @used-by :meth:`Df.Harness.Git.GlobalIgnoreSyncer.GlobalIgnoreSyncer.__configured_excludes_file()`
	# @used-by :meth:`Df.Harness.Git.GlobalIgnoreSyncer.GlobalIgnoreSyncer.__resolve_path()`
	# @used-by :meth:`Df.Harness.Git.HookRunner.HookRunner.__run_commit_msg()`
	# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.__read_commit_msg()`
	# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.__resolve_commit_specs()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.__init__()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.assert_toplevel()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.main_repo()`
	# @used-by :meth:`Df.Harness.Git.RepoResolver.RepoResolver.resolve()`
	# @used-by :meth:`Df.Harness.Git.WorktreeExcludeManager.WorktreeExcludeManager.__detect_enclosing()`
	# @used-by :meth:`Df.Harness.Git.WorktreeExcludeManager.WorktreeExcludeManager.__init__()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.__collect_write_target()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.__resolve_repo_rel()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.build_code_write_event()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def __init__(self, value: str | Path) -> None:
		self.__raw = str(value).strip()
	# @used-by :func:`Df.Harness.lib.worktree.dfh_prepare_worktrees_base_dir()`
	# @used-by :func:`agent_tools.shell_audit.normalize_host_path()`
	# @used-by :meth:`Df.Harness.Git.CredentialLockCleaner.CredentialLockCleaner.__collect_candidates()`
	# @used-by :meth:`Df.Harness.Git.GitGlobalOptsScanner.GitGlobalOptsScanner.__advance_dir()`
	# @used-by :meth:`Df.Harness.Git.GlobalIgnoreSyncer.GlobalIgnoreSyncer.__configured_excludes_file()`
	# @used-by :meth:`Df.Harness.Git.GlobalIgnoreSyncer.GlobalIgnoreSyncer.__resolve_path()`
	# @used-by :meth:`Df.Harness.Git.HookRunner.HookRunner.__run_commit_msg()`
	# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.__read_commit_msg()`
	# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.__resolve_commit_specs()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.__init__()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.assert_toplevel()`
	# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.main_repo()`
	# @used-by :meth:`Df.Harness.Git.RepoResolver.RepoResolver.resolve()`
	# @used-by :meth:`Df.Harness.Git.WorktreeExcludeManager.WorktreeExcludeManager.__detect_enclosing()`
	# @used-by :meth:`Df.Harness.Git.WorktreeExcludeManager.WorktreeExcludeManager.__init__()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.__collect_write_target()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.__resolve_repo_rel()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.build_code_write_event()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def normalize(self) -> Path:
		m = _CYGDRIVE_RE.match(self.__raw.replace('\\', '/'))
		if not m:
			r = Path(self.__raw)
		else:
			drive = m.group(1).upper()
			rest = m.group(2) or ''
			r = Path(f'{drive}:/{rest}')
		return r
