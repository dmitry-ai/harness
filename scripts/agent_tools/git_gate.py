# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
from .links import validate_file
from .path_registry import project_paths, tool_list, tool_path
from .shell_audit import READ_SUBCOMMANDS, ShellCommandInspector, _COMMIT_MESSAGE_ISSUE_URL_RE, _CYGDRIVE_RE, _GITHUB_ISSUE_URL_RE, _ISSUE_LINKED_CODE_SUFFIXES, _VALUE_GLOBAL_OPTS, _iter_shell_git_segments, _parse_commit_subcommand_args, _scan_git_global_opts, _split_shell_segments, _unquote, classify_git_argv, extract_comment_issue_urls, extract_issue_actions_from_outputs, extract_issue_urls, is_code_file, normalize_commit_message, normalize_host_path, parse_issue_url, prohibited_git_write_commands, unflagged_git_read_commands, unpersisted_http_fetch_commands
from .subprocess_hygiene_gate import run_staged_gate
# 2026-11-02
# "Eliminate flashing Git console windows on Windows by enforcing CREATE_NO_WINDOW and skipping redundant Git subprocesses in journal-watch":
# https://github.com/dmitry-ai/harness/issues/40
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-19
# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
# https://github.com/dmitry-ai/harness/issues/96
HOOKS_DIR = tool_path('git_hooks_dir')
# 2026-11-02
# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
# https://github.com/dmitry-ai/harness/issues/38
GITHUB_MAX_BLOB_BYTES = 100 * 1024 * 1024
EXTRACTED_MAX_BYTES = 16 * 1024 * 1024
_EXTRACTED_DERIVED_RE = re.compile('(?:^|/)(?:Evidence/HTTP/[^/]+/[^/]+/extracted-[^/]+\\.json|Evidence/Extracted/[0-9a-f]{64}/[^/]+\\.json|extracted-(?:html|text|json)(?:-[0-9a-f]{16})?\\.json)$')
# 2026-11-02
# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
# https://github.com/dmitry-ai/harness/issues/39
AGENT_ENV_KEYS = ('ANTIGRAVITY_AGENT', 'ANTIGRAVITY_CONVERSATION_ID', 'ANTIGRAVITY_TRAJECTORY_ID', 'ANTIGRAVITY_AGENTAPI_EXE', 'ANTIGRAVITY_SOURCE_METADATA', 'CODEX_HOME', 'CODEX_CLI_PATH', 'CODEX_SANDBOX', 'CODEX_THREAD_ID', 'CODEX_CI', 'CODEX_WINDOWS_REGISTERED_CORE', 'NODE_REPL_NODE_PATH', 'SKY_CUA_NATIVE_PIPE', 'HARNESS_AGENT_GIT', 'UPWORK_AGENT_GIT')
AGENT_PROCESS_NAMES = ('antigravity.exe', 'language_server.exe', 'codex.exe', 'codex-command-runner.exe', 'codex-code-mode-host.exe', 'codex-windows-sandbox-service.exe', 'codex-windows-sandbox-setup.exe', 'node_repl.exe', 'codex-computer-use.exe', 'codex-computer-use-swift.exe')
# 2026-11-14
# "Decompose git_gate.py into shell_audit.py, GitRepoGate, and single-pass pre-commit validation":
# https://github.com/dmitry-ai/harness/issues/67
class GitRepoGate:
	# @used-by :func:`_check_blob_size_limits()`
	# @used-by :func:`_extract_added_diff_urls()`
	# @used-by :func:`_main_repo_for_worktree()`
	# @used-by :func:`_normalize_repo_paths()`
	# @used-by :func:`agent_tools.gates.cdp_bypass._is_inside_harness_code()`
	# @used-by :func:`agent_tools.landing_lease._lease_file_for()`
	# @used-by :func:`agent_tools.polyglot_land._branch_touched_files()`
	# @used-by :func:`agent_tools.polyglot_land.dirty_blocking_main_files()`
	# @used-by :func:`agent_tools.repo_wait._dirty_files()`
	# @used-by :func:`agent_tools.repo_wait._map_touched_path_to_repo()`
	# @used-by :func:`agent_tools.repo_wait.wait_for_repo()`
	# @used-by :func:`agent_tools.worktree_flow._current_branch()`
	# @used-by :func:`agent_tools.worktree_flow._enrich_worktree_entry()`
	# @used-by :func:`agent_tools.worktree_flow._land_under_lease()`
	# @used-by :func:`agent_tools.worktree_flow._push_and_finish_land()`
	# @used-by :func:`agent_tools.worktree_flow._rev_distance()`
	# @used-by :func:`agent_tools.worktree_flow.git_config_file()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_begin()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_cleanup()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_status()`
	# @used-by :func:`agent_tools.worktree_land_flow._branch_sha()`
	# @used-by :func:`agent_tools.worktree_land_flow.execute_optimistic_worktree_land()`
	# @used-by :func:`check_commit()`
	# @used-by :func:`commit()`
	# @used-by :func:`commit_in_worktree()`
	# @used-by :func:`create_isolated_worktree()`
	# @used-by :func:`ensure_repo_hooks()`
	# @used-by :func:`git()`
	# @used-by :func:`is_issue_tracked_code_repo()`
	# @used-by :func:`read_git()`
	# @used-by :func:`remove_isolated_worktree()`
	# @used-by :func:`run_git_hook()`
	# @used-by :func:`verify_git_write_invocation()`
	# @used-by :func:`verify_issue_workflow()`
	# @used-by :func:`verify_push_blob_sizes()`
	# @used-by :func:`verify_repo_issue_ready_for_close()`
	# @used-by :func:`verify_staged_blob_sizes()`
	# @used-by :meth:`WorktreeCommitTransaction.commit()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_git_pre_commit_blocks_oversized_python_file()`
	# @used-by :meth:`test_code_style_gate.CodeStyleGateTests.test_pre_tool_use_gate_and_pre_commit_enforce_code_style()`
	# @used-by :meth:`test_cross_repo_issue_urls.CrossRepoIssueUrlsTests.test_staged_issue_urls_ignore_foreign_repo_urls_and_check_dotpy()`
	# @used-by :meth:`test_issue_comment_gate.IssueCommentGateTests.test_pre_tool_use_and_pre_commit_enforce_issue_comment_gate()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_ensure_hooks_uses_deployed_immutable_git_hooks_dir()`
	# @used-by :meth:`test_subprocess_hygiene_and_tree_kill.SubprocessHygieneAndTreeKillTests.test_pre_commit_and_pre_tool_use_enforce_subprocess_hygiene_ratchet()`
	# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_commit_transaction_create_protects_enclosing_repo()`
	# @used-by :meth:`test_xref_gate.XrefGateTests.test_pre_commit_blocks_stale_cross_file_xref_and_passes_after_sync()`
	def __init__(self, root: Path, *, strict: bool=False):
		self.root = normalize_host_path(root).resolve(strict=strict)
	# 2026-11-02
	# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
	# https://github.com/dmitry-ai/harness/issues/38
	# @used-by :func:`_check_blob_size_limits()`
	# @used-by :meth:`GitRepoGate.verify_push_blob_sizes()`
	# @used-by :meth:`GitRepoGate.verify_staged_blob_sizes()`
	def _check_blob_size_limits(self, rel_posix: str, size: int, *, kind: str, sha: str='') -> None:
		if rel_posix and _EXTRACTED_DERIVED_RE.search(rel_posix) and (EXTRACTED_MAX_BYTES < size):
			label = f'{rel_posix} ({sha[:12]})' if sha else rel_posix
			noun = 'derived extraction blob' if sha else 'derived extraction file'
			raise ValueError(f'{kind} {noun} {label} is {size} bytes, exceeding MAX_BYTES ({EXTRACTED_MAX_BYTES} bytes)')
		if GITHUB_MAX_BLOB_BYTES < size:
			label = (f'{rel_posix} ({sha[:12]})' if rel_posix else sha[:12]) if sha else rel_posix
			raise ValueError(f'{kind} Git blob {label} is {size} bytes, exceeding GitHub GH001 hard limit ({GITHUB_MAX_BLOB_BYTES} bytes)')
	# 2026-10-31
	# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
	# https://github.com/dmitry-ai/harness/issues/31
	# @used-by :func:`_extract_added_diff_urls()`
	# @used-by :func:`agent_tools.tdd.exemption._verify_single_file_issue_urls()`
	def _extract_added_diff_urls(self, rel_name: str) -> tuple[set[str], set[str]]:
		added_urls: set[str] = set()
		head_urls: set[str] = set()
		if (self.root / '.git').exists():
			diff_proc = self.run_read(['diff', '--cached', '-U0', '--', f':(literal){rel_name}'], check=False)
			if 0 == diff_proc.returncode and diff_proc.stdout:
				added_lines = [line[1:] for line in diff_proc.stdout.decode('utf-8', errors='replace').splitlines() if line.startswith('+') and (not line.startswith('+++'))]
				# 2026-11-13
				# "Extract issue_lifecycle.py from completion.py, fix open backlog-issue lifecycle gating, and consolidate Git/issue helpers in git_gate.py":
				# https://github.com/dmitry-ai/harness/issues/53
				added_urls.update(extract_comment_issue_urls('\n'.join(added_lines)))
			if added_urls:
				show_proc = self.run_read(['show', f'HEAD:{rel_name}'], check=False)
				if 0 == show_proc.returncode and show_proc.stdout:
					head_urls.update(extract_comment_issue_urls(show_proc.stdout.decode('utf-8', errors='replace')))
		return (added_urls, head_urls)
	# @used-by :meth:`GitRepoGate.check_commit()`
	# @used-by :meth:`GitRepoGate.run_hook()`
	# @used-by :meth:`GitRepoGate.verify_staged_blob_sizes()`
	# @used-by :meth:`GitRepoGate.verify_write_invocation()`
	def _staged_paths(self) -> list[str]:
		return [x.decode('utf-8') for x in self.git('diff', '--cached', '--name-only', '--no-renames', '-z').split(b'\x00') if x]
	# @used-by :meth:`GitRepoGate.check_commit()`
	def assert_toplevel(self) -> Path:
		actual = normalize_host_path(self.git('rev-parse', '--show-toplevel').decode('utf-8').strip()).resolve()
		if actual != self.root:
			raise ValueError(f'Expected repository root {self.root}, found {actual}')
		return self.root
	# 2026-10-11
	# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
	# https://github.com/dmitry-ai/harness/issues/2
	# @used-by :func:`check_commit()`
	# @used-by :meth:`GitRepoGate.commit()`
	# @used-by :meth:`WorktreeCommitTransaction.commit()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	def check_commit(self, paths: list[str], *, message: str | None=None) -> list[str]:
		self.assert_toplevel()
		self.ensure_hooks()
		r = self.normalize_paths(paths)
		staged = set(self._staged_paths())
		if staged != set(r):
			raise ValueError(f'Staged paths differ from explicit paths: {sorted(staged ^ set(r))}')
		specs = [f':(literal){p}' for p in r]
		if self.git('diff', '--name-only', '-z', '--', *specs):
			raise ValueError('Selected files have unstaged changes; review and stage the intended version')
		if self.git('diff', '--cached', '--name-only', '--diff-filter=U'):
			raise ValueError('Unresolved merge conflicts')
		for name in r:
			path = self.root / name
			if path.is_file() and '.md' == path.suffix.lower():
				# 2026-10-17
				# "Prohibit URL percent-encoding in authored Markdown links (LINK-5) and add --readable link validator":
				# https://github.com/dmitry-ai/harness/issues/9
				errors = validate_file(path, readable_links=True)
				if errors:
					raise ValueError('\n'.join(errors))
		self.git('diff', '--cached', '--check')
		# 2026-10-20
		# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
		# https://github.com/dmitry-ai/harness/issues/13
		from .text_workflow import gate_paths
		gate_paths([self.root / name for name in r])
		self.verify_staged_blob_sizes(r)
		if None is not message and (not message.strip()):
			raise ValueError('Empty commit message')
		# 2026-11-23
		# "Enforce AST function and file SLOC ratchet gate in PreToolUse and Git pre-commit":
		# https://github.com/dmitry-ai/harness/issues/161
		self._verify_agent_staged(r, message=message, use_index=True)
		return r
	# 2026-10-11
	# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
	# https://github.com/dmitry-ai/harness/issues/2
	# @used-by :func:`commit()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	def commit(self, paths: list[str], message: str, execute: bool=False, *, worktree: bool=False) -> list[str]:
		if worktree and execute:
			r = WorktreeCommitTransaction(self).commit(paths, message)
		else:
			r = self.check_commit(paths, message=message)
			if execute:
				self.git('commit', '--only', '-m', message, '--', *[f':(literal){p}' for p in r])
		return r
	# 2026-10-31
	# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
	# https://github.com/dmitry-ai/harness/issues/31
	# 2026-11-24
	# "Deploy immutable Harness runtime snapshots with LKG fallback":
	# https://github.com/dmitry-ai/harness/issues/184
	# @used-by :func:`ensure_repo_hooks()`
	# @used-by :meth:`GitRepoGate.check_commit()`
	# @used-by :meth:`GitRepoGate.verify_write_invocation()`
	# @used-by :meth:`test_runtime_snapshot.RuntimeSnapshotTests.test_ensure_hooks_uses_deployed_immutable_git_hooks_dir()`
	def ensure_hooks(self) -> Path | None:
		from .runtime_snapshot import ensure_repo_git_hooks
		return ensure_repo_git_hooks(self.root, self.main_repo(), HOOKS_DIR)
	# 2026-10-11
	# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
	# https://github.com/dmitry-ai/harness/issues/2
	# 2026-11-13
	# "Extract issue_lifecycle.py from completion.py, fix open backlog-issue lifecycle gating, and consolidate Git/issue helpers in git_gate.py":
	# https://github.com/dmitry-ai/harness/issues/53
	# @used-by :func:`agent_tools.polyglot_land.dirty_blocking_main_files()`
	# @used-by :func:`agent_tools.worktree_flow._land_under_lease()`
	# @used-by :func:`agent_tools.worktree_flow._push_and_finish_land()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_begin()`
	# @used-by :func:`agent_tools.worktree_land_flow._branch_sha()`
	# @used-by :func:`agent_tools.worktree_land_flow.execute_optimistic_worktree_land()`
	# @used-by :func:`git()`
	# @used-by :meth:`GitRepoGate._staged_paths()`
	# @used-by :meth:`GitRepoGate.assert_toplevel()`
	# @used-by :meth:`GitRepoGate.check_commit()`
	# @used-by :meth:`GitRepoGate.commit()`
	# @used-by :meth:`GitRepoGate.read_git()`
	# @used-by :meth:`WorktreeCommitTransaction.commit()`
	def git(self, *args) -> bytes:
		result = self.run_read(list(args), check=False)
		if 0 != result.returncode:
			raise RuntimeError(result.stderr.decode('utf-8', errors='replace').strip())
		return result.stdout
	# 2026-10-31
	# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
	# https://github.com/dmitry-ai/harness/issues/31
	# @used-by :func:`is_issue_tracked_code_repo()`
	# @used-by :meth:`GitRepoGate.verify_issue_workflow()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_live_five_projects_integration_across_harness_subsystems_and_cli()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_project_overlay_dag_cascades_and_remains_isolated_per_project()`
	# @used-by :meth:`test_path_registry.PathRegistryTests.test_v2_filesystem_auto_detection_journals_context_provenance_and_migration()`
	def is_issue_tracked(self) -> bool:
		resolved = self.main_repo()
		if not (resolved / '.git').exists():
			return False
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		try:
			# 2026-11-21
			# "Support V2 `𝐒`/`𝐖` software subtrees and cross-root project relocations in Harness":
			# https://github.com/dmitry-ai/harness/issues/113
			from .path_registry import canonicalize_root_dir
			pp = project_paths(resolved)
			# 2026-11-20
			# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
			# https://github.com/dmitry-ai/harness/issues/101
			if any((resolved == cr for cr in pp.code_repos)):
				return True
			canon = canonicalize_root_dir(resolved)
			if canon != resolved and 2 <= pp.fs_version:
				return True
		except (OSError, ValueError):
			pass
		# 2026-11-20
		# "Wire V2 filesystem layout across Harness runtime subsystems and shared projections":
		# https://github.com/dmitry-ai/harness/issues/101
		# 2026-11-20
		# "Replace V2 verbal directory names with Ⰿ/♕/♙ symbols and add Antigravity hook runner":
		# https://github.com/dmitry-ai/harness/issues/103
		if resolved.parts[-4:] in (('\u2c0f', '\u227b', '\u2655', '\u26ef'), ('Artifacts', '\u227b', 'Deliverables', '\u26ef')) and ((resolved.parents[3] / '\ua616').is_dir() or (resolved.parents[3] / '\U0001f56e').is_dir() or (resolved.parents[3] / '.agents').is_dir()):
			return True
		return 'code' == resolved.name and ((resolved.parent / '_').is_dir() or (resolved.parent / '.agents').is_dir())
	# 2026-10-31
	# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
	# https://github.com/dmitry-ai/harness/issues/31
	# @used-by :func:`_main_repo_for_worktree()`
	# @used-by :func:`agent_tools.gates.cdp_bypass._is_inside_harness_code()`
	# @used-by :func:`agent_tools.landing_lease._lease_file_for()`
	# @used-by :func:`agent_tools.repo_wait._map_touched_path_to_repo()`
	# @used-by :func:`agent_tools.repo_wait.wait_for_repo()`
	# @used-by :func:`agent_tools.worktree_flow.git_config_file()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_begin()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_cleanup()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_land()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_status()`
	# @used-by :meth:`GitRepoGate._tdd_project_root()`
	# @used-by :meth:`GitRepoGate.ensure_hooks()`
	# @used-by :meth:`GitRepoGate.is_issue_tracked()`
	def main_repo(self) -> Path:
		r = self.root
		dot_git = self.root / '.git'
		if dot_git.is_file():
			try:
				txt = dot_git.read_text(encoding='utf-8', errors='replace').strip()
				if txt.lower().startswith('gitdir:'):
					gitdir = normalize_host_path(txt.split(':', 1)[1].strip())
					if not gitdir.is_absolute():
						gitdir = (self.root / gitdir).resolve()
					if 'worktrees' == gitdir.parent.name and '.git' == gitdir.parent.parent.name:
						r = gitdir.parent.parent.parent.resolve()
			except OSError:
				pass
		return r
	# @used-by :func:`_normalize_repo_paths()`
	# @used-by :meth:`GitRepoGate.check_commit()`
	def normalize_paths(self, paths: list[str]) -> list[str]:
		if not paths:
			raise ValueError('An explicit file list is required')
		r = []
		for name in paths:
			path = (self.root / name).resolve()
			if not path.is_relative_to(self.root) or path == self.root or path.is_dir():
				raise ValueError(f'Not a repository file: {name}')
			r.append(path.relative_to(self.root).as_posix())
		if len(r) != len(set(r)):
			raise ValueError('Duplicate file paths')
		return r
	# 2026-10-24
	# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
	# https://github.com/dmitry-ai/harness/issues/17
	# @used-by :func:`read_git()`
	def read_git(self, subcommand: str='status', args: tuple[str, ...] | list[str]=()) -> dict:
		if subcommand not in READ_SUBCOMMANDS:
			raise ValueError(f'Unsupported read-only Git subcommand: {subcommand}')
		extra = [str(a) for a in args]
		output = self.git(subcommand, *extra)
		return {'valid': True, 'repo': str(self.root), 'subcommand': subcommand, 'args': extra, 'command': ['git', '--no-optional-locks', '-C', str(self.root), subcommand, *extra], 'git_optional_locks': '0', 'stdout': output.decode('utf-8', errors='replace')}
	# 2026-10-31
	# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
	# https://github.com/dmitry-ai/harness/issues/31
	# 2026-11-02
	# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
	# https://github.com/dmitry-ai/harness/issues/39
	# @used-by :func:`run_git_hook()`
	# @used-by :meth:`test_code_style_gate.CodeStyleGateTests.test_pre_tool_use_gate_and_pre_commit_enforce_code_style()`
	# @used-by :meth:`test_issue_comment_gate.IssueCommentGateTests.test_pre_tool_use_and_pre_commit_enforce_issue_comment_gate()`
	# @used-by :meth:`test_xref_gate.XrefGateTests.test_pre_commit_blocks_stale_cross_file_xref_and_passes_after_sync()`
	def run_hook(self, hook_name: str, argv: list[str] | tuple[str, ...]=(), *, stdin_text: str | None=None, agent_context: bool | None=None) -> int:
		is_agent = is_agent_git_context() if None is agent_context else bool(agent_context)
		r = 0
		try:
			if 'pre-commit' == hook_name:
				staged = self._staged_paths()
				if staged:
					self.verify_staged_blob_sizes(staged)
					if is_agent:
						self._verify_agent_staged(staged, use_index=True)
			elif 'commit-msg' == hook_name:
				if is_agent:
					if not argv:
						raise ValueError('commit-msg hook requires message file path argument')
					msg_path = normalize_host_path(argv[0])
					if not msg_path.is_absolute():
						msg_path = (self.root / msg_path).resolve()
					raw_msg = msg_path.read_text(encoding='utf-8', errors='replace')
					self.verify_issue_workflow(self._staged_paths(), message=raw_msg, agent_context=True)
			# 2026-11-02
			# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
			# https://github.com/dmitry-ai/harness/issues/38
			elif 'pre-push' == hook_name:
				lines = stdin_text.splitlines() if None is not stdin_text else (sys.stdin.read().splitlines() if not sys.stdin.isatty() else None)
				self.verify_push_blob_sizes(stdin_lines=lines)
		except (OSError, ValueError, RuntimeError) as exc:
			print(f'ERROR (Git hook {hook_name}): {exc}', file=sys.stderr)
			r = 2
		return r
	# @used-by :func:`agent_tools.polyglot_land._branch_touched_files()`
	# @used-by :func:`agent_tools.repo_wait._dirty_files()`
	# @used-by :func:`agent_tools.worktree_flow._current_branch()`
	# @used-by :func:`agent_tools.worktree_flow._enrich_worktree_entry()`
	# @used-by :func:`agent_tools.worktree_flow._rev_distance()`
	# @used-by :func:`agent_tools.worktree_flow.worktree_status()`
	# @used-by :meth:`GitRepoGate._extract_added_diff_urls()`
	# @used-by :meth:`GitRepoGate.git()`
	# @used-by :meth:`GitRepoGate.verify_push_blob_sizes()`
	# @used-by :meth:`GitRepoGate.verify_staged_blob_sizes()`
	def run_read(self, args: list[str] | tuple[str, ...], *, check: bool=True, input_bytes: bytes | None=None):
		# 2026-10-24
		# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
		# https://github.com/dmitry-ai/harness/issues/17
		env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
		# 2026-10-14
		# "Implement /upwork-init onboarding workflow, CDP job extraction, A.A/A.F delegation, and Folders tree registration":
		# https://github.com/dmitry-ai/harness/issues/3
		# 2026-11-02
		# "Eliminate flashing Git console windows on Windows by enforcing CREATE_NO_WINDOW and skipping redundant Git subprocesses in journal-watch":
		# https://github.com/dmitry-ai/harness/issues/40
		# 2026-11-24
		# "Detach inherited stdin pipes in Harness test runners and Git hook helpers":
		# https://github.com/dmitry-ai/harness/issues/204
		return subprocess.run(['git', '--no-optional-locks', '-C', str(self.root), *args], **({'input': input_bytes} if None is not input_bytes else {'stdin': subprocess.DEVNULL}), capture_output=True, env=env, check=check, creationflags=_NO_WINDOW)
	# 2026-10-31
	# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
	# https://github.com/dmitry-ai/harness/issues/31
	# @used-by :func:`verify_repo_issue_ready_for_close()`
	def verify_issue_ready_for_close(self, repo: str, number: int, *, project_root: str | Path | None=None, _visiting: set[int] | None=None, git_cache=None) -> dict:
		from .github_issue import find_tracked_child_issues
		# 2026-11-24
		# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
		# https://github.com/dmitry-ai/harness/issues/175
		from .issues.git_read_cache import RepoReadCache
		cache = git_cache if None is not git_cache else RepoReadCache()
		issue_url = f'https://github.com/{repo}/issues/{number}'
		dirty_referencing = cache.dirty_referencing_issue(self.root, issue_url, _ISSUE_LINKED_CODE_SUFFIXES, extract_issue_urls)
		if dirty_referencing:
			raise ValueError(f'EXEC-5 violation: uncommitted file(s) in {self.root} still reference {issue_url}: {", ".join(dirty_referencing)}; commit and push before closing the issue')
		commit_sha = cache.find_commit_for_issue(self.root, issue_url, extract_issue_urls)
		# 2026-11-18
		# "Enforce parent problem issues and per-subtask child issue commits across issue and Git lifecycle gates":
		# https://github.com/dmitry-ai/harness/issues/84
		children = find_tracked_child_issues(repo, number, project_root=project_root, code_repo=self.root)
		visiting = set(_visiting or ())
		if children and int(number) not in visiting:
			visiting.add(int(number))
			if commit_sha:
				raise ValueError(f'EXEC-5 violation: parent issue {issue_url} has child subtask issues and must document the original problem without direct monolithic code commits ({commit_sha[:12]})')
			open_children = [c['url'] for c in children if 'closed' != c['state']]
			if open_children:
				raise ValueError(f'EXEC-5 violation: parent issue {issue_url} cannot be closed as completed while child issue(s) remain open: {", ".join(open_children)}')
			completed_children = [c for c in children if 'closed' == c['state'] and 'not_planned' != str(c.get('state_reason') or '').lower() and c['number'] not in visiting]
			if not completed_children:
				raise ValueError(f'EXEC-5 violation: parent issue {issue_url} has no completed child issues with verified commits')
			child_shas: list[str] = []
			for child in completed_children:
				c_res = self.verify_issue_ready_for_close(repo, child['number'], project_root=project_root, _visiting=visiting, git_cache=cache)
				if c_res.get('commit_sha'):
					child_shas.append(c_res['commit_sha'])
			return {'verified': True, 'repo': str(self.root), 'issue_url': issue_url, 'commit_sha': child_shas[0] if child_shas else '', 'child_issues': [c['number'] for c in completed_children], 'pushed': True}
		if not commit_sha:
			raise ValueError(f'EXEC-5 violation: no commit in {self.root} references {issue_url}; commit and push changes before closing the issue as completed')
		# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
		from .repo_tag_gate import finalize_commit_close_check
		return finalize_commit_close_check(self.root, commit_sha, issue_url, cache)
	# 2026-11-23
	# "Enforce TDD test coverage and ratchet in Git pre-commit gate":
	# https://github.com/dmitry-ai/harness/issues/137
	# @used-by :meth:`GitRepoGate.verify_issue_workflow()`
	# @used-by :meth:`GitRepoGate.verify_tdd_commit()`
	def _tdd_project_root(self) -> Path:
		main_r = self.main_repo()
		try:
			pp = project_paths(main_r)
			if pp.root != main_r and (pp.root / '\ua616').is_dir():
				return pp.root
		except (OSError, ValueError):
			pass
		for anc in (main_r, *main_r.parents[:4]):
			if (anc / '\ua616').is_dir():
				return anc
		return main_r
	# 2026-11-23
	# "Enforce AST function and file SLOC ratchet gate in PreToolUse and Git pre-commit":
	# https://github.com/dmitry-ai/harness/issues/161
	# @used-by :meth:`GitRepoGate.check_commit()`
	# @used-by :meth:`GitRepoGate.run_hook()`
	# @used-by :meth:`GitRepoGate.verify_write_invocation()`
	# @uses :func:`agent_tools.staged_gates.verify_staged_extra_gates()`
	def _verify_agent_staged(self, relative: list[str], *, message: str | None=None, use_index: bool=True) -> None:
		self.verify_issue_workflow(relative, message=message, agent_context=True)
		self.verify_tdd_commit(relative, message=message, agent_context=True, use_index=use_index)
		self.verify_code_size_ratchet(relative, agent_context=True, use_index=use_index)
		# 2026-11-25
		# "Add CODE-1 Python style ratchet linter gate in PreToolUse and pre-commit":
		# https://github.com/dmitry-ai/harness/issues/243
		run_staged_gate('staged_gates', 'verify_staged_extra_gates', self.root, relative, use_index=use_index)
	# 2026-11-23
	# "Enforce AST function and file SLOC ratchet gate in PreToolUse and Git pre-commit":
	# https://github.com/dmitry-ai/harness/issues/161
	# 2026-11-24
	# "Unify process-tree termination in parallel_runner and enforce AST subprocess hygiene in pre-commit":
	# https://github.com/dmitry-ai/harness/issues/206
	# @used-by :meth:`GitRepoGate._verify_agent_staged()`
	# @used-by :meth:`test_code_size_gate.CodeSizeGateTests.test_git_pre_commit_blocks_oversized_python_file()`
	# @uses :func:`agent_tools.code_size_gate.verify_staged_code_size_ratchet()`
	def verify_code_size_ratchet(self, relative: list[str], *, agent_context: bool=True, use_index: bool=True) -> None:
		if agent_context and relative:
			run_staged_gate('code_size_gate', 'verify_staged_code_size_ratchet', self.root, relative, use_index=use_index)
	# 2026-11-24
	# "Unify process-tree termination in parallel_runner and enforce AST subprocess hygiene in pre-commit":
	# https://github.com/dmitry-ai/harness/issues/206
	# @used-by :meth:`test_subprocess_hygiene_and_tree_kill.SubprocessHygieneAndTreeKillTests.test_pre_commit_and_pre_tool_use_enforce_subprocess_hygiene_ratchet()`
	# @uses :func:`agent_tools.subprocess_hygiene_gate.verify_staged_subprocess_hygiene()`
	def verify_subprocess_hygiene(self, relative: list[str], *, agent_context: bool=True, use_index: bool=True) -> None:
		if agent_context and relative:
			run_staged_gate('subprocess_hygiene_gate', 'verify_staged_subprocess_hygiene', self.root, relative, use_index=use_index)
	# 2026-11-23
	# "Enforce TDD test coverage and ratchet in Git pre-commit gate":
	# https://github.com/dmitry-ai/harness/issues/137
	# 2026-11-24
	# "Unify process-tree termination in parallel_runner and enforce AST subprocess hygiene in pre-commit":
	# https://github.com/dmitry-ai/harness/issues/206
	# @used-by :meth:`GitRepoGate._verify_agent_staged()`
	# @uses :func:`agent_tools.tdd.enforcement.verify_staged_tdd_diff()`
	def verify_tdd_commit(self, relative: list[str], message: str | None=None, *, agent_context: bool=True, use_index: bool=True) -> None:
		if agent_context and relative:
			run_staged_gate('tdd_gate', 'verify_staged_tdd_diff', self.root, relative, message=message, project_root=self._tdd_project_root(), use_index=use_index)
	# 2026-10-31
	# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
	# https://github.com/dmitry-ai/harness/issues/31
	# 2026-11-02
	# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
	# https://github.com/dmitry-ai/harness/issues/39
	# @used-by :func:`verify_issue_workflow()`
	# @used-by :meth:`GitRepoGate._verify_agent_staged()`
	# @used-by :meth:`GitRepoGate.run_hook()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	def verify_issue_workflow(self, relative: list[str], message: str | None=None, *, agent_context: bool=True) -> None:
		if agent_context:
			stripped_msg = None
			if None is not message:
				stripped_msg = normalize_commit_message(message)
				if None is parse_issue_url(stripped_msg):
					raise ValueError('Commit message for an agent commit must contain only the GitHub Issue URL (https://github.com/<owner>/<repo>/issues/<N>)')
			# 2026-11-25
			# "Add comment-only diff lexer exemption for top 20 repository languages":
			# https://github.com/dmitry-ai/harness/issues/238
			from .tdd.exemption import verify_staged_issue_urls
			all_new_diff_urls = verify_staged_issue_urls(self, relative, stripped_msg, project_root=self._tdd_project_root())
			# 2026-11-23
			# "Enforce cross-platform Issue-First gate across turn completion and Git validation":
			# https://github.com/dmitry-ai/harness/issues/146
			if self.is_issue_tracked():
				from .github_issue import extract_parent_issue_number
				from .issue_lifecycle import evidence_issue_files, origin_repo_slug
				import json as _json
				repo_slug = origin_repo_slug(self.root)
				if repo_slug:
					check_urls: list[str] = []
					if None is not stripped_msg:
						check_urls.append(stripped_msg)
					for u in sorted(all_new_diff_urls):
						if u not in check_urls:
							check_urls.append(u)
					proj_root = self._tdd_project_root()
					for u in check_urls:
						parsed = parse_issue_url(u)
						if None is parsed:
							continue
						u_slug, u_num = parsed
						if u_slug.lower() != repo_slug.lower():
							raise ValueError(f'EXEC-5 ISSUE-FIRST-GATE: Referenced issue {u} does not match repository {repo_slug}')
						ev_files = evidence_issue_files(proj_root, u_slug, f'issue-{u_num}.json', candidate_repos=[self.root])
						if not ev_files:
							raise ValueError(f'EXEC-5 ISSUE-FIRST-GATE: Referenced issue {u} has no saved API read-back Evidence JSON (issue-{u_num}.json); create or fetch the parent issue via df_github_issue.py before writing tests or code')
						try:
							ev_data = _json.loads(ev_files[0].read_text(encoding='utf-8'))
						except (OSError, ValueError):
							continue
						if isinstance(ev_data, dict):
							iss_obj = ev_data.get('issue') if isinstance(ev_data.get('issue'), dict) else ev_data
							raw_p = ev_data.get('parent_number')
							if not isinstance(raw_p, int) or isinstance(raw_p, bool):
								raw_p = iss_obj.get('parent_number') if isinstance(iss_obj, dict) else None
							if not isinstance(raw_p, int) or isinstance(raw_p, bool):
								raw_p = extract_parent_issue_number(str((iss_obj or {}).get('body') or ''), u_slug)
							if isinstance(raw_p, int) and (not isinstance(raw_p, bool)) and raw_p != u_num:
								if not evidence_issue_files(proj_root, u_slug, f'issue-{raw_p}.json', candidate_repos=[self.root]):
									raise ValueError(f'EXEC-5 ISSUE-FIRST-GATE: Child issue {u} references parent #{raw_p}, which has no saved API read-back Evidence JSON (issue-{raw_p}.json)')
	# 2026-11-02
	# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
	# https://github.com/dmitry-ai/harness/issues/38
	# @used-by :func:`verify_push_blob_sizes()`
	# @used-by :meth:`GitRepoGate.run_hook()`
	# @used-by :meth:`GitRepoGate.verify_write_invocation()`
	def verify_push_blob_sizes(self, stdin_lines: list[str] | None=None) -> None:
		if (self.root / '.git').exists():
			rev_args: list[str] = []
			if None is stdin_lines:
				if 0 == self.run_read(['rev-parse', '--verify', 'HEAD'], check=False).returncode:
					rev_args = ['HEAD', '--not', '--remotes']
			else:
				zero_re = re.compile('^0+$')
				for raw_line in stdin_lines:
					parts = raw_line.strip().split()
					if 4 <= len(parts) and (not zero_re.match(parts[1])):
						if not zero_re.match(parts[3]):
							rev_args.append(f'{parts[3]}..{parts[1]}')
						else:
							rev_args.extend([parts[1], '--not', '--remotes'])
			if rev_args:
				rev_proc = self.run_read(['rev-list', '--objects', *rev_args], check=False)
				if 0 == rev_proc.returncode and rev_proc.stdout.strip():
					cat_proc = self.run_read(['cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize) %(rest)'], check=False, input_bytes=rev_proc.stdout)
					if 0 == cat_proc.returncode:
						for line in cat_proc.stdout.decode('utf-8', errors='replace').splitlines():
							parts = line.strip().split(' ', 3)
							if 3 <= len(parts) and 'blob' == parts[1] and parts[2].isdigit():
								rel_posix = (parts[3] if 3 < len(parts) else '').replace('\\', '/')
								self._check_blob_size_limits(rel_posix, int(parts[2]), kind='Unpushed', sha=parts[0])
	# 2026-11-02
	# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
	# https://github.com/dmitry-ai/harness/issues/38
	# @used-by :func:`verify_staged_blob_sizes()`
	# @used-by :meth:`GitRepoGate.check_commit()`
	# @used-by :meth:`GitRepoGate.run_hook()`
	# @used-by :meth:`GitRepoGate.verify_write_invocation()`
	def verify_staged_blob_sizes(self, staged_paths: list[str] | None=None) -> None:
		if (self.root / '.git').exists():
			paths = list(staged_paths) if None is not staged_paths else self._staged_paths()
			if paths:
				batch_in = ''.join((f':{p}\n' for p in paths)).encode('utf-8')
				proc = self.run_read(['cat-file', '--batch-check=%(objecttype) %(objectsize)'], check=False, input_bytes=batch_in)
				if 0 == proc.returncode:
					lines = proc.stdout.decode('utf-8', errors='replace').splitlines()
					for rel_raw, line in zip(paths, lines):
						parts = line.strip().split()
						if 2 <= len(parts) and 'blob' == parts[0] and parts[1].isdigit():
							self._check_blob_size_limits(rel_raw.replace('\\', '/'), int(parts[1]), kind='Staged')
	# 2026-10-31
	# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
	# https://github.com/dmitry-ai/harness/issues/31
	# 2026-11-02
	# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
	# https://github.com/dmitry-ai/harness/issues/39
	# @used-by :func:`verify_git_write_invocation()`
	def verify_write_invocation(self, argv: list[str] | tuple[str, ...], *, subcommand: str | None=None, cwd: Path | None=None, agent_context: bool | None=None) -> None:
		cmd_name = subcommand if None is not subcommand else classify_git_argv(argv)[0]
		if cmd_name in ('commit', 'push', 'filter-branch', 'merge', 'rebase', 'cherry-pick'):
			self.ensure_hooks()
			is_agent = is_agent_git_context() if None is agent_context else bool(agent_context)
			if 'filter-branch' == cmd_name:
				if is_agent:
					raise ValueError('EXEC-5 violation: git filter-branch is prohibited for agents')
			elif 'push' == cmd_name:
				if '--no-verify' in argv and is_agent:
					raise ValueError('EXEC-5 violation: git push --no-verify is prohibited for agents')
				self.verify_push_blob_sizes()
			elif 'commit' == cmd_name:
				_, msg, msg_file, no_verify, all_flag, pathspecs = _parse_commit_subcommand_args(argv)
				if is_agent:
					if no_verify:
						raise ValueError('EXEC-5 violation: git commit --no-verify/-n is prohibited for agents')
					if all_flag:
						raise ValueError('EXEC-5 violation: git commit -a/--all is prohibited for agents; stage and commit only an explicit file list')
					if None is msg and msg_file and ('-' != msg_file):
						mf = normalize_host_path(msg_file)
						if not mf.is_absolute():
							mf = (normalize_host_path(cwd or Path.cwd()) / mf).resolve()
						if mf.is_file():
							msg = mf.read_text(encoding='utf-8', errors='replace')
					if None is not msg and None is parse_issue_url(normalize_commit_message(msg)):
						raise ValueError('EXEC-5 violation: commit message for an agent commit must contain only the GitHub Issue URL (https://github.com/<owner>/<repo>/issues/<N>)')
				if (self.root / '.git').exists():
					clean_specs = []
					for sp in pathspecs:
						s = sp[len(':(literal)'):] if sp.startswith(':(literal)') else sp
						p = (self.root / normalize_host_path(s)).resolve()
						if p.is_relative_to(self.root):
							clean_specs.append(p.relative_to(self.root).as_posix())
					if not clean_specs:
						try:
							clean_specs = self._staged_paths()
						except RuntimeError:
							clean_specs = []
					if clean_specs:
						self.verify_staged_blob_sizes(clean_specs)
						if is_agent:
							self._verify_agent_staged(clean_specs, message=msg, use_index=not bool(pathspecs))
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-14
# "Decompose git_gate.py into shell_audit.py, GitRepoGate, and single-pass pre-commit validation":
# https://github.com/dmitry-ai/harness/issues/67
class WorktreeCommitTransaction:
	# @used-by :func:`commit_in_worktree()`
	# @used-by :func:`create_isolated_worktree()`
	# @used-by :func:`remove_isolated_worktree()`
	# @used-by :meth:`GitRepoGate.commit()`
	# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_commit_transaction_create_protects_enclosing_repo()`
	def __init__(self, gate: GitRepoGate, *, label: str='commit'):
		self.gate = gate
		self.label = label
	# @used-by :func:`commit_in_worktree()`
	# @used-by :meth:`GitRepoGate.commit()`
	def commit(self, paths: list[str], message: str) -> list[str]:
		self.gate.assert_toplevel()
		if not message.strip():
			raise ValueError('Empty commit message')
		self.gate.ensure_hooks()
		r = self.gate.normalize_paths(paths)
		has_head = 0 == self.gate.run_read(['rev-parse', '--verify', 'HEAD'], check=False).returncode
		wt_dir = self.create()
		try:
			for rel in r:
				src = self.gate.root / rel
				dst = wt_dir / rel
				if not src.exists():
					if dst.exists():
						dst.unlink()
				else:
					dst.parent.mkdir(parents=True, exist_ok=True)
					shutil.copy2(src, dst)
			specs = [f':(literal){p}' for p in r]
			wt_gate = GitRepoGate(wt_dir, strict=True)
			wt_gate.git('add', '-A', '--', *specs)
			wt_gate.check_commit(r, message=message)
			old_head = self.gate.git('rev-parse', 'HEAD').decode('utf-8').strip() if has_head else None
			wt_gate.git('commit', '--only', '-m', message, '--', *specs)
			new_head = wt_gate.git('rev-parse', 'HEAD').decode('utf-8').strip()
			if not old_head:
				self.gate.git('update-ref', '-m', f'commit (worktree): {message.strip()}', 'HEAD', new_head)
			else:
				self.gate.git('update-ref', '-m', f'commit (worktree): {message.strip()}', 'HEAD', new_head, old_head)
			self.gate.git('reset', '-q', 'HEAD', '--', *specs)
		finally:
			self.remove(wt_dir)
		return r
	# 2026-11-24
	# "Auto-exclude worktrees_dir in enclosing repo info/exclude on worktree creation":
	# https://github.com/dmitry-ai/harness/issues/201
	# @used-by :func:`create_isolated_worktree()`
	# @used-by :meth:`WorktreeCommitTransaction.commit()`
	# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_commit_transaction_create_protects_enclosing_repo()`
	def create(self) -> Path:
		from .git_ignore import prepare_worktrees_base_dir
		base, _ = prepare_worktrees_base_dir(self.gate.root)
		r = base / f'{self.label}-{uuid.uuid4().hex[:10]}'
		self.gate.git('worktree', 'add', '--detach', str(r), 'HEAD')
		return r
	# @used-by :func:`agent_tools.article.check_graph()`
	# @used-by :func:`agent_tools.cli_registry._exec_worktree_land()`
	# @used-by :func:`remove_isolated_worktree()`
	# @used-by :meth:`WorktreeCommitTransaction.commit()`
	# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._check_cycles()`
	# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_df_bootstrap_loads_dotpy_packages_and_sibling_modules()`
	# @used-by :meth:`test_experiments.ExperimentTests.test_native_actions_without_prior_plan_commit_receipt_cannot_be_verified()`
	# @used-by :meth:`test_worktree_ignore.WorktreeIgnoreInvariantTests.test_worktree_commit_transaction_create_protects_enclosing_repo()`
	def remove(self, wt_dir: Path) -> None:
		resolved_wt = Path(wt_dir).resolve()
		try:
			self.gate.git('worktree', 'remove', '--force', str(resolved_wt))
		finally:
			if resolved_wt.exists():
				shutil.rmtree(resolved_wt, ignore_errors=True)
			# 2026-11-02
			# "Eliminate flashing Git console windows on Windows by enforcing CREATE_NO_WINDOW and skipping redundant Git subprocesses in journal-watch":
			# https://github.com/dmitry-ai/harness/issues/40
			# 2026-11-24
			# "Detach inherited stdin pipes in Harness test runners and Git hook helpers":
			# https://github.com/dmitry-ai/harness/issues/204
			subprocess.run(['git', '-C', str(self.gate.root), 'worktree', 'prune'], stdin=subprocess.DEVNULL, capture_output=True, check=False, creationflags=_NO_WINDOW)
# 2026-11-02
# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
# https://github.com/dmitry-ai/harness/issues/39
# @used-by :func:`is_agent_git_context()`
def _ancestor_process_names(pid: int | None=None) -> list[str]:
	r: list[str] = []
	if 'nt' == os.name:
		import ctypes
		from ctypes import wintypes
		class _PROCESSENTRY32W(ctypes.Structure):
			_fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD), ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG), ('dwFlags', wintypes.DWORD), ('szExeFile', ctypes.c_wchar * wintypes.MAX_PATH)]
		kernel32 = ctypes.windll.kernel32
		snap = kernel32.CreateToolhelp32Snapshot(2, 0)
		if None is not snap and snap != wintypes.HANDLE(-1).value:
			table: dict[int, tuple[int, str]] = {}
			try:
				entry = _PROCESSENTRY32W()
				entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
				if kernel32.Process32FirstW(snap, ctypes.byref(entry)):
					while True:
						table[int(entry.th32ProcessID)] = (int(entry.th32ParentProcessID), str(entry.szExeFile).lower())
						if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
							break
			finally:
				kernel32.CloseHandle(snap)
			curr = os.getpid() if None is pid else int(pid)
			visited: set[int] = set()
			while curr and curr not in visited and (curr in table):
				visited.add(curr)
				ppid, name = table[curr]
				r.append(name)
				curr = ppid
	return r
# 2026-11-02
# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
# https://github.com/dmitry-ai/harness/issues/39
# @used-by :func:`git_shim.main()`
# @used-by :meth:`GitRepoGate.run_hook()`
# @used-by :meth:`GitRepoGate.verify_write_invocation()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def is_agent_git_context(env: dict[str, str] | None=None, *, ancestor_names: list[str] | tuple[str, ...] | None=None) -> bool:
	environ = os.environ if None is env else env
	has_env = any((isinstance(val, str) and bool(val.strip()) and (val.strip().lower() not in ('0', 'false', 'no')) for key in AGENT_ENV_KEYS for val in (environ.get(key),)))
	if has_env:
		r = True
	else:
		ancestors = [str(n).lower() for n in ancestor_names] if None is not ancestor_names else _ancestor_process_names()
		agent_procs = {p.lower() for p in AGENT_PROCESS_NAMES}
		r = any((name in agent_procs for name in ancestors))
	return r
# 2026-11-02
# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
# https://github.com/dmitry-ai/harness/issues/38
# @used-by :func:`git_shim.main()`
# @used-by :func:`run_git_hook()`
# @used-by :func:`verify_git_write_invocation()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def cleanup_stale_credential_locks(max_age_seconds: float=10.0, *, candidates: list[Path] | tuple[Path, ...] | None=None, check_running: bool=True) -> list[str]:
	if None is not candidates:
		lock_paths = [normalize_host_path(p) for p in candidates]
	else:
		# 2026-11-19
		# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
		# https://github.com/dmitry-ai/harness/issues/96
		roots = [Path(h) for h in tool_list('git_credential_lock_homes')]
		try:
			roots.insert(0, Path.home())
		except RuntimeError:
			pass
		env_home = os.environ.get('HOME')
		if env_home:
			roots.append(normalize_host_path(env_home))
		seen: set[str] = set()
		lock_paths = []
		lock_rels = tuple(tool_list('git_credential_lock_relpaths'))
		for base in roots:
			for rel in lock_rels:
				cand = base / rel
				key = str(cand).replace('\\', '/').lower()
				if key not in seen:
					seen.add(key)
					lock_paths.append(cand)
	existing = [lp for lp in lock_paths if lp.is_file()]
	r: list[str] = []
	if existing:
		now = time.time()
		expired: list[Path] = []
		for lp in existing:
			try:
				if max_age_seconds <= now - lp.stat().st_mtime:
					expired.append(lp)
			except OSError:
				continue
		if expired:
			running = False
			if check_running and 'nt' == os.name:
				# 2026-11-02
				# "Eliminate flashing Git console windows on Windows by enforcing CREATE_NO_WINDOW and skipping redundant Git subprocesses in journal-watch":
				# https://github.com/dmitry-ai/harness/issues/40
				# 2026-11-24
				# "Detach inherited stdin pipes in Harness test runners and Git hook helpers":
				# https://github.com/dmitry-ai/harness/issues/204
				proc = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq git-credential-store.exe', '/NH'], stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False, creationflags=_NO_WINDOW)
				running = 'git-credential-store' in (proc.stdout or '').lower()
			if not running:
				for lp in expired:
					try:
						lp.unlink(missing_ok=True)
						r.append(str(lp))
					except OSError:
						continue
	return r
# 2026-10-11
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by unused
def git(root: Path, *args) -> bytes:
	return GitRepoGate(root).git(*args)
# 2026-10-24
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`agent_tools.cli_domains._op_git_read()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_read_git_and_git_shim_and_unflagged_detector()`
def read_git(root: Path, subcommand: str='status', args: tuple[str, ...] | list[str]=()) -> dict:
	if subcommand not in READ_SUBCOMMANDS:
		raise ValueError(f'Unsupported read-only Git subcommand: {subcommand}')
	return GitRepoGate(root, strict=True).read_git(subcommand, args)
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-02
# "Eliminate flashing Git console windows on Windows by enforcing CREATE_NO_WINDOW and skipping redundant Git subprocesses in journal-watch":
# https://github.com/dmitry-ai/harness/issues/40
# 2026-11-24
# "Detach inherited stdin pipes in Harness test runners and Git hook helpers":
# https://github.com/dmitry-ai/harness/issues/204
# @used-by :func:`agent_tools.issues.repo_locator.origin_repo_slug()`
# @used-by :func:`agent_tools.issues.service_helpers.dirty_issue_first_files()`
# @used-by :func:`agent_tools.repo_link_gate._cat_file_type()`
# @used-by :func:`agent_tools.repo_link_gate._is_gitignored()`
# @used-by :func:`agent_tools.repo_link_gate._load_blob_text()`
# @used-by :func:`agent_tools.repo_link_gate._read_staged_markdown()`
# @used-by :func:`agent_tools.repo_link_gate._repo_has_tag()`
# @used-by :func:`agent_tools.repo_tag_gate._has_upstream()`
# @used-by :func:`agent_tools.repo_tag_gate._read_local_tag_map()`
# @used-by :func:`agent_tools.repo_tag_gate._read_remote_tags()`
# @used-by :func:`agent_tools.repo_tags._commit_sha_and_day()`
# @used-by :func:`agent_tools.repo_tags._read_tag_refs()`
# @used-by :func:`agent_tools.repo_tags._resolve_commit_sha()`
# @used-by :func:`agent_tools.repo_tags._validate_blob_fragment()`
# @used-by :func:`agent_tools.repo_tags.commit_date_day()`
# @used-by :func:`agent_tools.repo_tags.has_origin_remote()`
# @used-by :func:`agent_tools.repo_tags.list_repo_tags()`
# @used-by :func:`agent_tools.repo_tags.plan_retro_tags()`
# @used-by :func:`agent_tools.repo_tags.remote_has_tag()`
# @used-by :func:`agent_tools.repo_tags.tags_at_commit()`
# @used-by :func:`agent_tools.repo_tags.validate_tree_path_and_fragment()`
def run_git_read(root: Path, args: list[str] | tuple[str, ...], *, check: bool=True, input_bytes: bytes | None=None):
	return subprocess.run(['git', '--no-optional-locks', '-C', str(normalize_host_path(root)), *args], **({'input': input_bytes} if None is not input_bytes else {'stdin': subprocess.DEVNULL}), capture_output=True, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}, check=check, creationflags=_NO_WINDOW)
# @used-by unused
def _main_repo_for_worktree(root: Path) -> Path:
	return GitRepoGate(root).main_repo()
# @used-by :func:`agent_tools.issue_first_gate.resolve_issue_first_target()`
# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_readiness()`
# @used-by :func:`agent_tools.issues.parity._peer_code_repo_candidates()`
# @used-by :func:`agent_tools.issues.service_helpers._parse_dirty_porcelain()`
# @used-by :func:`agent_tools.tdd.diff_coverage._touched_git_repos()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._bind_issue_repos()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._collect_repos_and_issues()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._collect_touched_repos()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._check_close_commit_readiness()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message()`
def is_issue_tracked_code_repo(root: Path) -> bool:
	return GitRepoGate(root).is_issue_tracked()
# @used-by unused
def ensure_repo_hooks(root: Path) -> Path | None:
	return GitRepoGate(root).ensure_hooks()
# @used-by unused
def _check_blob_size_limits(rel_posix: str, size: int, *, kind: str, sha: str='') -> None:
	GitRepoGate(Path.cwd())._check_blob_size_limits(rel_posix, size, kind=kind, sha=sha)
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def verify_staged_blob_sizes(root: Path, staged_paths: list[str] | None=None) -> None:
	GitRepoGate(root).verify_staged_blob_sizes(staged_paths)
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def verify_push_blob_sizes(root: Path, stdin_lines: list[str] | None=None) -> None:
	GitRepoGate(root).verify_push_blob_sizes(stdin_lines=stdin_lines)
# @used-by unused
def _extract_added_diff_urls(root: Path, rel_name: str) -> tuple[set[str], set[str]]:
	return GitRepoGate(root)._extract_added_diff_urls(rel_name)
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_git_gate_verify_issue_workflow_enforces_slug_and_saved_evidence_in_github_code_repo()`
def verify_issue_workflow(root: Path, relative: list[str], message: str | None=None, *, agent_context: bool=True) -> None:
	GitRepoGate(root).verify_issue_workflow(relative, message=message, agent_context=agent_context)
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-13
# "Extract issue_lifecycle.py from completion.py, fix open backlog-issue lifecycle gating, and consolidate Git/issue helpers in git_gate.py":
# https://github.com/dmitry-ai/harness/issues/53
# @used-by :func:`agent_tools.tdd.events._is_git_commit_command()`
# @used-by :func:`run_git_hook()`
# @used-by :func:`verify_git_write_invocation()`
def resolve_git_repo_from_argv(argv: list[str] | tuple[str, ...], cwd: Path | None=None) -> Path | None:
	base_dir = normalize_host_path(cwd).resolve() if None is not cwd else Path.cwd().resolve()
	_, _, target_dir = _scan_git_global_opts(argv, base_dir=base_dir)
	r = None
	for anc in (target_dir, *target_dir.parents):
		if (anc / '.git').exists():
			r = anc
			break
	return r
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-02
# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
# https://github.com/dmitry-ai/harness/issues/39
# @used-by :func:`git_shim.prepare_git_invocation()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_git_gate_allows_comment_only_commit_and_blocks_code_change()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_agent_commit_requires_behavioral_test_for_production_code()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_git_gate_enforces_exact_recipe_issue_binding_and_mixed_m2_commit()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def verify_git_write_invocation(argv: list[str] | tuple[str, ...], cwd: Path | None=None, *, agent_context: bool | None=None) -> None:
	cleanup_stale_credential_locks()
	subcommand, _ = classify_git_argv(argv)
	if subcommand in ('commit', 'push', 'filter-branch', 'merge', 'rebase', 'cherry-pick'):
		repo_root = resolve_git_repo_from_argv(argv, cwd=cwd)
		if None is not repo_root:
			GitRepoGate(repo_root).verify_write_invocation(argv, subcommand=subcommand, cwd=cwd, agent_context=agent_context)
# 2026-10-31
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-02
# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
# https://github.com/dmitry-ai/harness/issues/39
# @used-by :func:`git_shim.main()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_git_gate_verify_issue_workflow_enforces_slug_and_saved_evidence_in_github_code_repo()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_git_gate_allows_comment_only_commit_and_blocks_code_change()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_agent_commit_requires_behavioral_test_for_production_code()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_doc_only_agent_commit_allowed_without_tests()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_ratchet_enforced_on_staged_test_edits_and_unlocked_by_ratchet_ok()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_git_gate_enforces_exact_recipe_issue_binding_and_mixed_m2_commit()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def run_git_hook(hook_name: str, argv: list[str] | tuple[str, ...]=(), cwd: Path | None=None, *, stdin_text: str | None=None, agent_context: bool | None=None) -> int:
	cleanup_stale_credential_locks()
	repo_root = resolve_git_repo_from_argv((), cwd=cwd)
	return GitRepoGate(repo_root).run_hook(hook_name, argv, stdin_text=stdin_text, agent_context=agent_context) if None is not repo_root else 0
# @used-by unused
def _normalize_repo_paths(root: Path, paths: list[str]) -> list[str]:
	return GitRepoGate(root).normalize_paths(paths)
# 2026-10-11
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-11-25
# "Add comment-only diff lexer exemption for top 20 repository languages":
# https://github.com/dmitry-ai/harness/issues/238
# @used-by :meth:`test_agent_tools.GitTests.test_unrelated_staged_change_is_rejected()`
# @used-by :meth:`test_agent_tools.GitTests.test_unstaged_change_rejected_and_explicit_commit_works()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_git_gate_verify_issue_workflow_enforces_slug_and_saved_evidence_in_github_code_repo()`
# @used-by :meth:`test_tdd_comment_exemption.CommentOnlyExemptionTests.test_git_gate_allows_comment_only_commit_and_blocks_code_change()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_agent_commit_requires_behavioral_test_for_production_code()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_doc_only_agent_commit_allowed_without_tests()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_ratchet_enforced_on_staged_test_edits_and_unlocked_by_ratchet_ok()`
def check_commit(root: Path, paths: list[str], *, message: str | None=None) -> list[str]:
	return GitRepoGate(root, strict=True).check_commit(paths, message=message)
# @used-by unused
def create_isolated_worktree(root: Path, label: str='isolated') -> Path:
	return WorktreeCommitTransaction(GitRepoGate(root, strict=True), label=label).create()
# @used-by unused
def remove_isolated_worktree(root: Path, wt_dir: Path) -> None:
	WorktreeCommitTransaction(GitRepoGate(root, strict=True)).remove(wt_dir)
# @used-by unused
def commit_in_worktree(root: Path, paths: list[str], message: str) -> list[str]:
	return WorktreeCommitTransaction(GitRepoGate(root, strict=True)).commit(paths, message)
# 2026-10-11
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# @used-by :func:`agent_tools.cli.main()`
# @used-by :meth:`test_agent_tools.GitTests.test_unstaged_change_rejected_and_explicit_commit_works()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message()`
# @used-by :meth:`test_issue_first_completion.IssueFirstTurnCompletionAndGitTests.test_git_gate_verify_issue_workflow_enforces_slug_and_saved_evidence_in_github_code_repo()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_agent_commit_requires_behavioral_test_for_production_code()`
# @used-by :meth:`test_tdd_git_gate.TddGitGateTests.test_ratchet_enforced_on_staged_test_edits_and_unlocked_by_ratchet_ok()`
def commit(root: Path, paths: list[str], message: str, execute=False, *, worktree: bool=False):
	return GitRepoGate(root, strict=True).commit(paths, message, execute=execute, worktree=worktree)
# 2026-11-24
# "Reduce subprocess overhead in PreToolUse tests and Git lifecycle checks":
# https://github.com/dmitry-ai/harness/issues/175
# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_readiness()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._verify_required_repo_issues()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._check_close_commit_readiness()`
# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_verify_issue_ready_for_close_allows_committed_header_issue_during_sibling_edit()`
# @used-by :meth:`test_git_lifecycle_memoization.GitLifecycleMemoizationTests.test_verify_issue_ready_for_close_memoizes_parent_child_and_catches_defects()`
# @used-by :meth:`test_github_issue.TestGitHubIssueTool.test_parent_child_issue_linking_bundled_subtasks_and_parent_closure()`
# @used-by :meth:`test_repo_tag_close_gate.RepoTagCloseGateTests.test_verify_close_rejects_untagged_invalid_and_unpushed_tags_and_accepts_pushed_valid()`
def verify_repo_issue_ready_for_close(code_repo: Path, repo: str, number: int, *, project_root: str | Path | None=None, git_cache=None) -> dict:
	return GitRepoGate(code_repo, strict=True).verify_issue_ready_for_close(repo, number, project_root=project_root, git_cache=git_cache)
