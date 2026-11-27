# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.BlobSizeValidator import BlobSizeValidator
from Df.Harness.Git.CommitVerifier import CommitVerifier
from Df.Harness.Git.HookInstaller import HookInstaller
from Df.Harness.Git.HookRunner import HookRunner
from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
from Df.Harness.Git.IssueCloseVerifier import IssueCloseVerifier
from Df.Harness.Git.IssueWorkflowVerifier import IssueWorkflowVerifier
from Df.Harness.Git.PushValidator import PushValidator
from Df.Harness.Git.WorktreeTransaction import WorktreeTransaction
from Df.Harness.lib.shell import READ_SUBCOMMANDS, dfh_extract_comment_issue_urls
import os
import subprocess
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class RepoGate:
	# @used-by :func:`Df.Harness.lib.worktree.dfh_git_config_file()`
	# @used-by :func:`Df.Harness.lib.worktree.dfh_has_origin_remote()`
	# @used-by :func:`agent_tools.git_gate._check_blob_size_limits()`
	# @used-by :func:`agent_tools.git_gate._extract_added_diff_urls()`
	# @used-by :func:`agent_tools.git_gate._main_repo_for_worktree()`
	# @used-by :func:`agent_tools.git_gate._normalize_repo_paths()`
	# @used-by :func:`agent_tools.git_gate.check_commit()`
	# @used-by :func:`agent_tools.git_gate.commit()`
	# @used-by :func:`agent_tools.git_gate.commit_in_worktree()`
	# @used-by :func:`agent_tools.git_gate.create_isolated_worktree()`
	# @used-by :func:`agent_tools.git_gate.ensure_repo_hooks()`
	# @used-by :func:`agent_tools.git_gate.git()`
	# @used-by :func:`agent_tools.git_gate.is_issue_tracked_code_repo()`
	# @used-by :func:`agent_tools.git_gate.read_git()`
	# @used-by :func:`agent_tools.git_gate.remove_isolated_worktree()`
	# @used-by :func:`agent_tools.git_gate.run_git_hook()`
	# @used-by :func:`agent_tools.git_gate.verify_git_write_invocation()`
	# @used-by :func:`agent_tools.git_gate.verify_issue_workflow()`
	# @used-by :func:`agent_tools.git_gate.verify_push_blob_sizes()`
	# @used-by :func:`agent_tools.git_gate.verify_repo_issue_ready_for_close()`
	# @used-by :func:`agent_tools.git_gate.verify_staged_blob_sizes()`
	# @used-by :func:`agent_tools.worktree_flow._current_branch()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
	# @used-by :meth:`Df.Harness.Gate.CdpBypassGate.CdpBypassGate.is_inside_harness_code()`
	# @used-by :meth:`Df.Harness.Git.BlobUrlBuilder.BlobUrlBuilder.__validate_blob_fragment()`
	# @used-by :meth:`Df.Harness.Git.BlobUrlBuilder.BlobUrlBuilder.__validate_tree_path()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.__commit_sha_and_day()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.__read_tag_refs()`
	# @used-by :meth:`Df.Harness.Git.DirtyMainChecker.DirtyMainChecker.__branch_touched()`
	# @used-by :meth:`Df.Harness.Git.DirtyMainChecker.DirtyMainChecker.find_blocking()`
	# @used-by :meth:`Df.Harness.Git.LandingLease.LandingLease.__init__()`
	# @used-by :meth:`Df.Harness.Git.RepoWaiter.RepoWaiter.__dirty_files()`
	# @used-by :meth:`Df.Harness.Git.RepoWaiter.RepoWaiter.__init__()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__plan()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__read_tag_refs()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__resolve_sha()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__map_path_to_repo()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCleaner.WorktreeCleaner.__current_branch()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCleaner.WorktreeCleaner.cleanup()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCreator.WorktreeCreator.__current_branch()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCreator.WorktreeCreator.begin()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__branch_sha()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__land_under_lease()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.land()`
	# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__push_and_finish()`
	# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.merge()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.__current_branch()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.__enrich_entry()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.__rev_distance()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.inspect()`
	# @used-by :meth:`Df.Harness.Git.WorktreeTransaction.WorktreeTransaction.__commit_in_wt()`
	# @used-by :meth:`Df.Harness.Issue.AcceptanceGate.AcceptanceGate.__verify_repo_close()`
	# @used-by :meth:`Df.Harness.Issue.AcceptanceGate.AcceptanceGate.check_readiness()`
	# @used-by :meth:`Df.Harness.Issue.DirtyIssueFirstScanner.DirtyIssueFirstScanner.__parse_dirty_porcelain()`
	# @used-by :meth:`Df.Harness.Issue.DirtyIssueFirstScanner.DirtyIssueFirstScanner.scan()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.resolve_target()`
	# @used-by :meth:`Df.Harness.Issue.ParityAuditor.ParityAuditor.peer_code_repo_candidates()`
	# @used-by :meth:`Df.Harness.Issue.RepoLocator.RepoLocator.origin_repo_slug()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.__check_close_commit_readiness()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__bind_issue_repos()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__collect_repos_and_issues()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__collect_touched_repos()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__verify_close_ready()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_git_pre_commit_blocks_oversized_python_file()`
	# @used-by :meth:`test_code_style_gate.CodeStyleGateTests.test_pre_tool_use_gate_and_pre_commit_enforce_code_style()`
	# @used-by :meth:`test_cross_repo_issue_urls.CrossRepoIssueUrlsTests.test_staged_issue_urls_ignore_foreign_repo_urls_and_check_dotpy()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	# @used-by :meth:`test_issue_comment_gate.IssueCommentGateTests.test_pre_tool_use_and_pre_commit_enforce_issue_comment_gate()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_ensure_hooks_uses_deployed_immutable_git_hooks_dir()`
	# @used-by :meth:`test_subprocess_hygiene_and_tree_kill.SubprocessHygieneAndTreeKillTests.test_pre_commit_and_pre_tool_use_enforce_subprocess_hygiene_ratchet()`
	# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_commit_transaction_create_protects_enclosing_repo()`
	# @used-by :meth:`test_xref_gate.XrefGateTests.test_pre_commit_blocks_stale_cross_file_xref_and_passes_after_sync()`
	def __init__(self, root: Path, *, strict: bool=False) -> None:
		self.root = HostPathNormalizer(root).normalize().resolve(strict=strict)
	# @used-by :meth:`Df.Harness.Git.IssueWorkflowVerifier.IssueWorkflowVerifier.verify()`
	def __getattr__(self, name: str):
		if '_extract_added_diff_urls' == name:
			r = self.extract_added_diff_urls
		else:
			raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
		return r
	# @used-by :meth:`Df.Harness.Git.CommitVerifier.CommitVerifier.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	def assert_toplevel(self) -> Path:
		actual = HostPathNormalizer(self.git('rev-parse', '--show-toplevel').decode('utf-8').strip()).normalize().resolve()
		if actual != self.root:
			raise ValueError(f'Expected repository root {self.root}, found {actual}')
		return self.root
	# @used-by :func:`agent_tools.git_gate.check_commit()`
	# @used-by :meth:`Df.Harness.Git.WorktreeTransaction.WorktreeTransaction.__commit_in_wt()`
	# @used-by :meth:`RepoGate.commit()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	def check_commit(self, paths: list[str], *, message: str | None=None) -> list[str]:
		return CommitVerifier(self).verify(paths, message=message)
	# @used-by :func:`agent_tools.git_gate.commit()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	def commit(self, paths: list[str], message: str, execute: bool=False, *, worktree: bool=False) -> list[str]:
		if worktree and execute:
			r = WorktreeTransaction(self).commit(paths, message)
		else:
			r = self.check_commit(paths, message=message)
			if execute:
				self.git('commit', '--only', '-m', message, '--', *[f':(literal){p}' for p in r])
		return r
	# @used-by :func:`agent_tools.git_gate.ensure_repo_hooks()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_ensure_hooks_uses_deployed_immutable_git_hooks_dir()`
	def ensure_hooks(self, *, hooks_dir: Path | None=None) -> Path | None:
		return HookInstaller(self, hooks_dir=hooks_dir).install()
	# @used-by :func:`agent_tools.git_gate._extract_added_diff_urls()`
	# @used-by :meth:`RepoGate.__getattr__()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	def extract_added_diff_urls(self, rel_name: str) -> tuple[set[str], set[str]]:
		added_urls: set[str] = set()
		head_urls: set[str] = set()
		if (self.root / '.git').exists():
			diff_proc = self.run_read(['diff', '--cached', '-U0', '--', f':(literal){rel_name}'], check=False)
			if 0 == diff_proc.returncode and diff_proc.stdout:
				lines = [ln[1:] for ln in diff_proc.stdout.decode('utf-8', errors='replace').splitlines() if ln.startswith('+') and (not ln.startswith('+++'))]
				added_urls.update(dfh_extract_comment_issue_urls('\n'.join(lines)))
			if added_urls:
				show_proc = self.run_read(['show', f'HEAD:{rel_name}'], check=False)
				if 0 == show_proc.returncode and show_proc.stdout:
					head_urls.update(dfh_extract_comment_issue_urls(show_proc.stdout.decode('utf-8', errors='replace')))
		return (added_urls, head_urls)
	# @used-by :func:`agent_tools.git_gate.git()`
	# @used-by :meth:`Df.Harness.Git.DirtyMainChecker.DirtyMainChecker.find_blocking()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCreator.WorktreeCreator.begin()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__branch_sha()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.__land_under_lease()`
	# @used-by :meth:`Df.Harness.Git.WorktreeLander.WorktreeLander.land()`
	# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.__push_and_finish()`
	# @used-by :meth:`Df.Harness.Git.WorktreeMerger.WorktreeMerger.merge()`
	# @used-by :meth:`Df.Harness.Git.WorktreeTransaction.WorktreeTransaction.__commit_in_wt()`
	# @used-by :meth:`RepoGate.assert_toplevel()`
	# @used-by :meth:`RepoGate.commit()`
	# @used-by :meth:`RepoGate.read_git()`
	# @used-by :meth:`RepoGate.staged_paths()`
	def git(self, *args) -> bytes:
		result = self.run_read(list(args), check=False)
		if 0 != result.returncode:
			raise RuntimeError(result.stderr.decode('utf-8', errors='replace').strip())
		return result.stdout
	# @used-by :func:`agent_tools.git_gate.is_issue_tracked_code_repo()`
	# @used-by :meth:`Df.Harness.Issue.AcceptanceGate.AcceptanceGate.check_readiness()`
	# @used-by :meth:`Df.Harness.Issue.DirtyIssueFirstScanner.DirtyIssueFirstScanner.__parse_dirty_porcelain()`
	# @used-by :meth:`Df.Harness.Issue.IssueFirstPreToolEvaluator.IssueFirstPreToolEvaluator.resolve_target()`
	# @used-by :meth:`Df.Harness.Issue.ParityAuditor.ParityAuditor.peer_code_repo_candidates()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.__check_close_commit_readiness()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__bind_issue_repos()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__collect_repos_and_issues()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__collect_touched_repos()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	def is_issue_tracked(self) -> bool:
		from agent_tools.path_registry import canonicalize_root_dir, project_paths
		resolved = self.main_repo()
		r = False
		if (resolved / '.git').exists():
			try:
				pp = project_paths(resolved)
				r = any((resolved == cr for cr in pp.code_repos)) or (canonicalize_root_dir(resolved) != resolved and 2 <= pp.fs_version)
			except (OSError, ValueError):
				r = False
			if not r:
				v2_tail = resolved.parts[-4:] in (('\u2c0f', '\u227b', '\u2655', '\u26ef'), ('Artifacts', '\u227b', 'Deliverables', '\u26ef')) and any(((resolved.parents[3] / d).is_dir() for d in ('\ua616', '\U0001f56e', '.agents')))
				r = v2_tail or ('code' == resolved.name and ((resolved.parent / '_').is_dir() or (resolved.parent / '.agents').is_dir()))
		return r
	# @used-by :func:`Df.Harness.lib.worktree.dfh_git_config_file()`
	# @used-by :func:`agent_tools.git_gate._main_repo_for_worktree()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
	# @used-by :meth:`Df.Harness.Gate.CdpBypassGate.CdpBypassGate.is_inside_harness_code()`
	# @used-by :meth:`Df.Harness.Git.LandingLease.LandingLease.__init__()`
	# @used-by :meth:`Df.Harness.Git.RepoWaiter.RepoWaiter.__init__()`
	# @used-by :meth:`Df.Harness.Git.TransientWaitRunner.TransientWaitRunner.__map_path_to_repo()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCleaner.WorktreeCleaner.cleanup()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCreator.WorktreeCreator.begin()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.inspect()`
	# @used-by :meth:`RepoGate.is_issue_tracked()`
	# @used-by :meth:`RepoGate.tdd_project_root()`
	def main_repo(self) -> Path:
		r = self.root
		dot_git = self.root / '.git'
		if dot_git.is_file():
			try:
				txt = dot_git.read_text(encoding='utf-8', errors='replace').strip()
				if txt.lower().startswith('gitdir:'):
					gitdir = HostPathNormalizer(txt.split(':', 1)[1].strip()).normalize()
					gitdir = gitdir if gitdir.is_absolute() else (self.root / gitdir).resolve()
					if 'worktrees' == gitdir.parent.name and '.git' == gitdir.parent.parent.name:
						r = gitdir.parent.parent.parent.resolve()
			except OSError:
				pass
		return r
	# @used-by :func:`agent_tools.git_gate._normalize_repo_paths()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	def normalize_paths(self, paths: list[str]) -> list[str]:
		if not paths:
			raise ValueError('An explicit file list is required')
		r: list[str] = []
		for name in paths:
			path = (self.root / name).resolve()
			if (not path.is_relative_to(self.root)) or path == self.root or path.is_dir():
				raise ValueError(f'Not a repository file: {name}')
			r.append(path.relative_to(self.root).as_posix())
		if len(r) != len(set(r)):
			raise ValueError('Duplicate file paths')
		return r
	# @used-by :func:`agent_tools.git_gate.read_git()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	def read_git(self, subcommand: str='status', args: tuple[str, ...] | list[str]=()) -> dict:
		if subcommand not in READ_SUBCOMMANDS:
			raise ValueError(f'Unsupported read-only Git subcommand: {subcommand}')
		extra = [str(a) for a in args]
		output = self.git(subcommand, *extra)
		return {'valid': True, 'repo': str(self.root), 'subcommand': subcommand, 'args': extra, 'command': ['git', '--no-optional-locks', '-C', str(self.root), subcommand, *extra], 'git_optional_locks': '0', 'stdout': output.decode('utf-8', errors='replace')}
	# @used-by :func:`agent_tools.git_gate.run_git_hook()`
	# @used-by :meth:`test_code_style_gate.CodeStyleGateTests.test_pre_tool_use_gate_and_pre_commit_enforce_code_style()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	# @used-by :meth:`test_issue_comment_gate.IssueCommentGateTests.test_pre_tool_use_and_pre_commit_enforce_issue_comment_gate()`
	# @used-by :meth:`test_xref_gate.XrefGateTests.test_pre_commit_blocks_stale_cross_file_xref_and_passes_after_sync()`
	def run_hook(self, hook_name: str, argv: list[str] | tuple[str, ...]=(), *, stdin_text: str | None=None, agent_context: bool | None=None) -> int:
		return HookRunner(self).run(hook_name, argv, stdin_text=stdin_text, agent_context=agent_context)
	# @used-by :func:`Df.Harness.lib.worktree.dfh_has_origin_remote()`
	# @used-by :func:`agent_tools.worktree_flow._current_branch()`
	# @used-by :meth:`Df.Harness.Git.BlobUrlBuilder.BlobUrlBuilder.__validate_blob_fragment()`
	# @used-by :meth:`Df.Harness.Git.BlobUrlBuilder.BlobUrlBuilder.__validate_tree_path()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.__commit_sha_and_day()`
	# @used-by :meth:`Df.Harness.Git.CommitTagger.CommitTagger.__read_tag_refs()`
	# @used-by :meth:`Df.Harness.Git.DirtyMainChecker.DirtyMainChecker.__branch_touched()`
	# @used-by :meth:`Df.Harness.Git.RepoWaiter.RepoWaiter.__dirty_files()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__plan()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__read_tag_refs()`
	# @used-by :meth:`Df.Harness.Git.RetroTagger.RetroTagger.__resolve_sha()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCleaner.WorktreeCleaner.__current_branch()`
	# @used-by :meth:`Df.Harness.Git.WorktreeCreator.WorktreeCreator.__current_branch()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.__current_branch()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.__enrich_entry()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.__rev_distance()`
	# @used-by :meth:`Df.Harness.Git.WorktreeStatusInspector.WorktreeStatusInspector.inspect()`
	# @used-by :meth:`Df.Harness.Issue.DirtyIssueFirstScanner.DirtyIssueFirstScanner.scan()`
	# @used-by :meth:`Df.Harness.Issue.RepoLocator.RepoLocator.origin_repo_slug()`
	# @used-by :meth:`RepoGate.extract_added_diff_urls()`
	# @used-by :meth:`RepoGate.git()`
	def run_read(self, args: list[str] | tuple[str, ...], *, check: bool=True, input_bytes: bytes | None=None):
		env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
		return subprocess.run(['git', '--no-optional-locks', '-C', str(self.root), *args], **({'input': input_bytes} if None is not input_bytes else {'stdin': subprocess.DEVNULL}), capture_output=True, env=env, check=check, creationflags=_NO_WINDOW)
	# @used-by :meth:`Df.Harness.Git.CommitVerifier.CommitVerifier.__check_staged_diff()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	def staged_paths(self) -> list[str]:
		return [x.decode('utf-8') for x in self.git('diff', '--cached', '--name-only', '--no-renames', '-z').split(b'\x00') if x]
	# @used-by :meth:`RepoGate.verify_tdd_commit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_worktree_locks_and_issues()`
	def tdd_project_root(self) -> Path:
		from agent_tools.path_registry import project_paths
		main_r = self.main_repo()
		r = main_r
		try:
			pp = project_paths(main_r)
			if pp.root != main_r and (pp.root / '\ua616').is_dir():
				r = pp.root
		except (OSError, ValueError):
			pass
		if r == main_r:
			for anc in (main_r, *main_r.parents[:4]):
				if (anc / '\ua616').is_dir():
					r = anc
					break
		return r
	# @used-by :meth:`RepoGate.verify_agent_staged()`
	# @used-by :meth:`RepoGate.verify_code_size_ratchet()`
	# @used-by :meth:`RepoGate.verify_subprocess_hygiene()`
	# @used-by :meth:`RepoGate.verify_tdd_commit()`
	@staticmethod
	def __run_staged_gate(mod_name: str, fn_name: str, *args, **kwargs) -> None:
		from agent_tools.subprocess_hygiene_gate import run_staged_gate
		run_staged_gate(mod_name, fn_name, *args, **kwargs)
	# @used-by :meth:`Df.Harness.Git.CommitVerifier.CommitVerifier.verify()`
	# @uses :func:`agent_tools.staged_gates.verify_staged_extra_gates()`
	def verify_agent_staged(self, relative: list[str], *, message: str | None=None, use_index: bool=True) -> None:
		self.verify_issue_workflow(relative, message=message, agent_context=True)
		self.verify_tdd_commit(relative, message=message, agent_context=True, use_index=use_index)
		self.verify_code_size_ratchet(relative, agent_context=True, use_index=use_index)
		self.__run_staged_gate('staged_gates', 'verify_staged_extra_gates', self.root, relative, use_index=use_index)
	# @used-by :meth:`RepoGate.verify_agent_staged()`
	# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_git_pre_commit_blocks_oversized_python_file()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	# @uses :func:`agent_tools.code_size_gate.verify_staged_code_size_ratchet()`
	def verify_code_size_ratchet(self, relative: list[str], *, agent_context: bool=True, use_index: bool=True) -> None:
		if agent_context and relative:
			self.__run_staged_gate('code_size_gate', 'verify_staged_code_size_ratchet', self.root, relative, use_index=use_index)
	# @used-by :func:`agent_tools.git_gate.verify_repo_issue_ready_for_close()`
	# @used-by :meth:`Df.Harness.Issue.AcceptanceGate.AcceptanceGate.__verify_repo_close()`
	# @used-by :meth:`Df.Harness.Issue.TurnAuditor.TurnAuditor.__verify_close_ready()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_worktree_helper_branches_audit_and_tags()`
	def verify_issue_ready_for_close(self, repo: str, number: int, *, project_root: str | Path | None=None, _visiting: set[int] | None=None, git_cache=None) -> dict:
		return IssueCloseVerifier(self).verify(repo, number, project_root=project_root, visiting=_visiting, git_cache=git_cache)
	# @used-by :func:`agent_tools.git_gate.verify_issue_workflow()`
	# @used-by :meth:`RepoGate.verify_agent_staged()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	def verify_issue_workflow(self, relative: list[str], message: str | None=None, *, agent_context: bool=True) -> None:
		IssueWorkflowVerifier(self).verify(relative, message=message, agent_context=agent_context)
	# @used-by :func:`agent_tools.git_gate.verify_push_blob_sizes()`
	def verify_push_blob_sizes(self, stdin_lines: list[str] | None=None, *, extracted_max: int | None=None, github_max: int | None=None) -> None:
		BlobSizeValidator(self, extracted_max=extracted_max, github_max=github_max).validate(mode='push', stdin_lines=stdin_lines)
	# @used-by :func:`agent_tools.git_gate.verify_staged_blob_sizes()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	def verify_staged_blob_sizes(self, staged_paths: list[str] | None=None, *, extracted_max: int | None=None, github_max: int | None=None) -> None:
		BlobSizeValidator(self, extracted_max=extracted_max, github_max=github_max).validate(mode='staged', staged_paths=staged_paths)
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	# @used-by :meth:`test_subprocess_hygiene_and_tree_kill.SubprocessHygieneAndTreeKillTests.test_pre_commit_and_pre_tool_use_enforce_subprocess_hygiene_ratchet()`
	# @uses :func:`agent_tools.subprocess_hygiene_gate.verify_staged_subprocess_hygiene()`
	def verify_subprocess_hygiene(self, relative: list[str], *, agent_context: bool=True, use_index: bool=True) -> None:
		if agent_context and relative:
			self.__run_staged_gate('subprocess_hygiene_gate', 'verify_staged_subprocess_hygiene', self.root, relative, use_index=use_index)
	# @used-by :meth:`RepoGate.verify_agent_staged()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	# @uses :func:`agent_tools.tdd.enforcement.verify_staged_tdd_diff()`
	def verify_tdd_commit(self, relative: list[str], message: str | None=None, *, agent_context: bool=True, use_index: bool=True) -> None:
		if agent_context and relative:
			self.__run_staged_gate('tdd_gate', 'verify_staged_tdd_diff', self.root, relative, message=message, project_root=self.tdd_project_root(), use_index=use_index)
	# @used-by :func:`agent_tools.git_gate.verify_git_write_invocation()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_git_gate_commit_and_hooks()`
	def verify_write_invocation(self, argv: list[str] | tuple[str, ...], *, subcommand: str | None=None, cwd: Path | None=None, agent_context: bool | None=None) -> None:
		PushValidator(self).validate(argv, subcommand=subcommand, cwd=cwd, agent_context=agent_context)
