# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose git_gate.py into shell_audit.py, GitRepoGate, and single-pass pre-commit validation":
# https://github.com/dmitry-ai/harness/issues/67
# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Decompose experiments.py into ExperimentPlanStore, BrowserTraceInspector, and ExperimentRunValidator classes and unify raw_decode JSON object scanning":
# https://github.com/dmitry-ai/harness/issues/72
# 2026-11-13 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract issue_lifecycle.py from completion.py, fix open backlog-issue lifecycle gating, and consolidate Git/issue helpers in git_gate.py":
# https://github.com/dmitry-ai/harness/issues/53
# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce universal harness.py CLI, automatic CDP browser fallback on JS shells, and Evidence verification for external links/anchors/quotes":
# https://github.com/dmitry-ai/harness/issues/27
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Prevent rogue ꘖ directory outside harness meta repo, remove mirror logic, and recognize GIT_OPTIONAL_LOCKS in git gate":
# https://github.com/dmitry-ai/harness/issues/28
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate quadratic HTML extraction bloat, enforce output and Git blob size invariants, and protect Cygwin Git hooks and credential locks":
# https://github.com/dmitry-ai/harness/issues/38
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce GitHub Issue URL commit requirement across all repositories for agents while exempting human user commits by invocation context":
# https://github.com/dmitry-ai/harness/issues/39
# 2026-11-02 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Eliminate flashing Git console windows on Windows via CREATE_NO_WINDOW and journal-watch lifecycle skip":
# https://github.com/dmitry-ai/harness/issues/40
# 2026-11-06 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce defect-to-issue filing gate in code repository audits, open-issue lifecycle separation, and recursive subagent trace aggregation":
# https://github.com/dmitry-ai/harness/issues/48
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
from .links import validate_file
from .shell_audit import READ_SUBCOMMANDS, ShellCommandInspector, _COMMIT_MESSAGE_ISSUE_URL_RE, _CYGDRIVE_RE, _GITHUB_ISSUE_URL_RE, _ISSUE_LINKED_CODE_SUFFIXES, _VALUE_GLOBAL_OPTS, _iter_shell_git_segments, _parse_commit_subcommand_args, _scan_git_global_opts, _split_shell_segments, _unquote, classify_git_argv, extract_comment_issue_urls, extract_issue_actions_from_outputs, extract_issue_urls, is_code_file, normalize_commit_message, normalize_host_path, parse_issue_url, prohibited_git_write_commands, unflagged_git_read_commands, unpersisted_http_fetch_commands
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
HOOKS_DIR = Path(__file__).resolve().parents[1] / 'git_hooks'
GITHUB_MAX_BLOB_BYTES = 100 * 1024 * 1024
EXTRACTED_MAX_BYTES = 16 * 1024 * 1024
_EXTRACTED_DERIVED_RE = re.compile('(?:^|/)(?:Evidence/HTTP/[^/]+/[^/]+/extracted-[^/]+\\.json|Evidence/Extracted/[0-9a-f]{64}/[^/]+\\.json|extracted-(?:html|text|json)(?:-[0-9a-f]{16})?\\.json)$')
AGENT_ENV_KEYS = ('ANTIGRAVITY_AGENT', 'ANTIGRAVITY_CONVERSATION_ID', 'ANTIGRAVITY_TRAJECTORY_ID', 'ANTIGRAVITY_AGENTAPI_EXE', 'ANTIGRAVITY_SOURCE_METADATA', 'CODEX_HOME', 'CODEX_CLI_PATH', 'CODEX_SANDBOX', 'CODEX_THREAD_ID', 'CODEX_CI', 'CODEX_WINDOWS_REGISTERED_CORE', 'NODE_REPL_NODE_PATH', 'SKY_CUA_NATIVE_PIPE', 'HARNESS_AGENT_GIT', 'UPWORK_AGENT_GIT')
AGENT_PROCESS_NAMES = ('antigravity.exe', 'language_server.exe', 'codex.exe', 'codex-command-runner.exe', 'codex-code-mode-host.exe', 'codex-windows-sandbox-service.exe', 'codex-windows-sandbox-setup.exe', 'node_repl.exe', 'codex-computer-use.exe', 'codex-computer-use-swift.exe')
class GitRepoGate:
	def __init__(self, root: Path, *, strict: bool=False):
		self.root = normalize_host_path(root).resolve(strict=strict)
	def _check_blob_size_limits(self, rel_posix: str, size: int, *, kind: str, sha: str='') -> None:
		if rel_posix and _EXTRACTED_DERIVED_RE.search(rel_posix) and (EXTRACTED_MAX_BYTES < size):
			label = f'{rel_posix} ({sha[:12]})' if sha else rel_posix
			noun = 'derived extraction blob' if sha else 'derived extraction file'
			raise ValueError(f'{kind} {noun} {label} is {size} bytes, exceeding MAX_BYTES ({EXTRACTED_MAX_BYTES} bytes)')
		if GITHUB_MAX_BLOB_BYTES < size:
			label = (f'{rel_posix} ({sha[:12]})' if rel_posix else sha[:12]) if sha else rel_posix
			raise ValueError(f'{kind} Git blob {label} is {size} bytes, exceeding GitHub GH001 hard limit ({GITHUB_MAX_BLOB_BYTES} bytes)')
	def _extract_added_diff_urls(self, rel_name: str) -> tuple[set[str], set[str]]:
		added_urls: set[str] = set()
		head_urls: set[str] = set()
		if (self.root / '.git').exists():
			diff_proc = self.run_read(['diff', '--cached', '-U0', '--', f':(literal){rel_name}'], check=False)
			if 0 == diff_proc.returncode and diff_proc.stdout:
				added_lines = [line[1:] for line in diff_proc.stdout.decode('utf-8', errors='replace').splitlines() if line.startswith('+') and (not line.startswith('+++'))]
				added_urls.update(extract_comment_issue_urls('\n'.join(added_lines)))
			if added_urls:
				show_proc = self.run_read(['show', f'HEAD:{rel_name}'], check=False)
				if 0 == show_proc.returncode and show_proc.stdout:
					head_urls.update(extract_comment_issue_urls(show_proc.stdout.decode('utf-8', errors='replace')))
		return (added_urls, head_urls)
	def _staged_paths(self) -> list[str]:
		return [x.decode('utf-8') for x in self.git('diff', '--cached', '--name-only', '--no-renames', '-z').split(b'\x00') if x]
	def assert_toplevel(self) -> Path:
		actual = normalize_host_path(self.git('rev-parse', '--show-toplevel').decode('utf-8').strip()).resolve()
		if actual != self.root:
			raise ValueError(f'Expected repository root {self.root}, found {actual}')
		return self.root
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
				errors = validate_file(path, readable_links=True)
				if errors:
					raise ValueError('\n'.join(errors))
		self.git('diff', '--cached', '--check')
		from .text_workflow import gate_paths
		gate_paths([self.root / name for name in r])
		self.verify_staged_blob_sizes(r)
		if None is not message and (not message.strip()):
			raise ValueError('Empty commit message')
		self.verify_issue_workflow(r, message=message)
		return r
	def commit(self, paths: list[str], message: str, execute: bool=False, *, worktree: bool=False) -> list[str]:
		if worktree and execute:
			r = WorktreeCommitTransaction(self).commit(paths, message)
		else:
			r = self.check_commit(paths, message=message)
			if execute:
				self.git('commit', '--only', '-m', message, '--', *[f':(literal){p}' for p in r])
		return r
	def ensure_hooks(self) -> Path | None:
		r = None
		if (self.root / '.git').exists() and HOOKS_DIR.is_dir():
			main_repo = self.main_repo()
			try:
				for hname in ('pre-commit', 'commit-msg', 'pre-push'):
					hp = HOOKS_DIR / hname
					if hp.is_file():
						hp.chmod(hp.stat().st_mode | 0o755)
				proc = subprocess.run(['git', '--no-optional-locks', '-C', str(main_repo), 'config', '--local', '--get', 'core.hooksPath'], capture_output=True, text=True, check=False, creationflags=_NO_WINDOW)
				current = (proc.stdout or '').strip()
				if (normalize_host_path(current).resolve() != HOOKS_DIR.resolve()) if current else True:
					subprocess.run(['git', '-C', str(main_repo), 'config', '--local', 'core.hooksPath', str(HOOKS_DIR)], capture_output=True, check=False, creationflags=_NO_WINDOW)
				r = HOOKS_DIR
			except OSError:
				r = None
		return r
	def git(self, *args) -> bytes:
		result = self.run_read(list(args), check=False)
		if 0 != result.returncode:
			raise RuntimeError(result.stderr.decode('utf-8', errors='replace').strip())
		return result.stdout
	def is_issue_tracked(self) -> bool:
		resolved = self.main_repo()
		return 'code' == resolved.name and (resolved / '.git').exists() and ((resolved.parent / '_').is_dir() or (resolved.parent / '.agents').is_dir())
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
	def read_git(self, subcommand: str='status', args: tuple[str, ...] | list[str]=()) -> dict:
		if subcommand not in READ_SUBCOMMANDS:
			raise ValueError(f'Unsupported read-only Git subcommand: {subcommand}')
		extra = [str(a) for a in args]
		output = self.git(subcommand, *extra)
		return {'valid': True, 'repo': str(self.root), 'subcommand': subcommand, 'args': extra, 'command': ['git', '--no-optional-locks', '-C', str(self.root), subcommand, *extra], 'git_optional_locks': '0', 'stdout': output.decode('utf-8', errors='replace')}
	def run_hook(self, hook_name: str, argv: list[str] | tuple[str, ...]=(), *, stdin_text: str | None=None, agent_context: bool | None=None) -> int:
		is_agent = is_agent_git_context() if None is agent_context else bool(agent_context)
		r = 0
		try:
			if 'pre-commit' == hook_name:
				staged = self._staged_paths()
				if staged:
					self.verify_staged_blob_sizes(staged)
					if is_agent:
						self.verify_issue_workflow(staged, agent_context=True)
			elif 'commit-msg' == hook_name:
				if is_agent:
					if not argv:
						raise ValueError('commit-msg hook requires message file path argument')
					msg_path = normalize_host_path(argv[0])
					if not msg_path.is_absolute():
						msg_path = (self.root / msg_path).resolve()
					raw_msg = msg_path.read_text(encoding='utf-8', errors='replace')
					self.verify_issue_workflow(self._staged_paths(), message=raw_msg, agent_context=True)
			elif 'pre-push' == hook_name:
				lines = stdin_text.splitlines() if None is not stdin_text else (sys.stdin.read().splitlines() if not sys.stdin.isatty() else None)
				self.verify_push_blob_sizes(stdin_lines=lines)
		except (OSError, ValueError, RuntimeError) as exc:
			print(f'ERROR (Git hook {hook_name}): {exc}', file=sys.stderr)
			r = 2
		return r
	def run_read(self, args: list[str] | tuple[str, ...], *, check: bool=True, input_bytes: bytes | None=None):
		env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}
		return subprocess.run(['git', '--no-optional-locks', '-C', str(self.root), *args], input=input_bytes, capture_output=True, env=env, check=check, creationflags=_NO_WINDOW)
	def verify_issue_ready_for_close(self, repo: str, number: int) -> dict:
		issue_url = f'https://github.com/{repo}/issues/{number}'
		status_out = self.git('status', '--porcelain', '-z').decode('utf-8', errors='replace')
		dirty_referencing = []
		entries = [e for e in status_out.split('\x00') if e]
		idx = 0
		while idx < len(entries):
			entry = entries[idx]
			status_code = entry[:2]
			rel_path = entry[3:]
			if status_code.startswith(('R', 'C')) and idx + 1 < len(entries):
				idx += 1
			fpath = self.root / rel_path
			if fpath.is_file() and fpath.suffix.lower() in _ISSUE_LINKED_CODE_SUFFIXES:
				try:
					if issue_url in fpath.read_text(encoding='utf-8', errors='replace'):
						dirty_referencing.append(rel_path)
				except OSError:
					pass
			idx += 1
		if dirty_referencing:
			raise ValueError(f'EXEC-5 violation: uncommitted file(s) in {self.root} still reference {issue_url}: {", ".join(dirty_referencing)}; commit and push before closing the issue')
		commit_sha = self.git('log', f'--grep={issue_url}', '--fixed-strings', '-n', '1', '--format=%H').decode('utf-8', errors='replace').strip()
		if not commit_sha:
			raise ValueError(f'EXEC-5 violation: no commit in {self.root} references {issue_url}; commit and push changes before closing the issue as completed')
		up_proc = self.run_read(['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'], check=False)
		pushed = True
		if 0 == up_proc.returncode:
			anc_proc = self.run_read(['merge-base', '--is-ancestor', commit_sha, '@{u}'], check=False)
			unpushed_str = self.git('rev-list', '--count', '@{u}..HEAD').decode('utf-8', errors='replace').strip()
			unpushed = int(unpushed_str) if unpushed_str.isdigit() else 0
			if 0 != anc_proc.returncode or 0 < unpushed:
				pushed = False
				raise ValueError(f'EXEC-5 violation: commit {commit_sha[:12]} referencing {issue_url} in {self.root} has not been pushed to upstream (run git push before df_github_issue.py close)')
		return {'verified': True, 'repo': str(self.root), 'issue_url': issue_url, 'commit_sha': commit_sha, 'pushed': pushed}
	def verify_issue_workflow(self, relative: list[str], message: str | None=None, *, agent_context: bool=True) -> None:
		if agent_context:
			stripped_msg = None
			if None is not message:
				stripped_msg = normalize_commit_message(message)
				if None is parse_issue_url(stripped_msg):
					raise ValueError('Commit message for an agent commit must contain only the GitHub Issue URL (https://github.com/<owner>/<repo>/issues/<N>)')
			all_new_diff_urls: set[str] = set()
			for name in relative:
				path = self.root / name
				if path.is_file() and path.suffix.lower() in _ISSUE_LINKED_CODE_SUFFIXES:
					content = path.read_text(encoding='utf-8', errors='replace')
					if content.strip():
						file_urls = set(_GITHUB_ISSUE_URL_RE.findall(content))
						if not file_urls:
							raise ValueError(f'Issue-tracked code file lacks a GitHub Issue URL reference: {name}')
						if None is not stripped_msg and stripped_msg not in file_urls:
							raise ValueError(f'Issue-tracked code file {name} does not reference the commit GitHub Issue URL {stripped_msg}')
						added_urls, head_urls = self._extract_added_diff_urls(name)
						new_diff_urls = added_urls - head_urls
						if 1 < len(new_diff_urls):
							raise ValueError(f'Staged diff in {name} introduces multiple distinct GitHub Issue URLs: {sorted(new_diff_urls)}')
						if None is not stripped_msg and new_diff_urls and (new_diff_urls != {stripped_msg}):
							raise ValueError(f'Staged diff in {name} introduces GitHub Issue URL(s) {sorted(new_diff_urls)} not matching commit message {stripped_msg}')
						all_new_diff_urls.update(new_diff_urls)
			if 1 < len(all_new_diff_urls):
				raise ValueError(f'Staged files mix changes from multiple GitHub Issues: {sorted(all_new_diff_urls)}')
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
							self.verify_issue_workflow(clean_specs, message=msg, agent_context=True)
class WorktreeCommitTransaction:
	def __init__(self, gate: GitRepoGate, *, label: str='commit'):
		self.gate = gate
		self.label = label
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
	def create(self) -> Path:
		base = (self.gate.root.parent / '_/ꘖ/data/worktrees') if (self.gate.root.parent / '_').is_dir() else (self.gate.root.parent / 'ꘖ/data/worktrees')
		base.mkdir(parents=True, exist_ok=True)
		r = base / f'{self.label}-{uuid.uuid4().hex[:10]}'
		self.gate.git('worktree', 'add', '--detach', str(r), 'HEAD')
		return r
	def remove(self, wt_dir: Path) -> None:
		resolved_wt = Path(wt_dir).resolve()
		try:
			self.gate.git('worktree', 'remove', '--force', str(resolved_wt))
		finally:
			if resolved_wt.exists():
				shutil.rmtree(resolved_wt, ignore_errors=True)
			subprocess.run(['git', '-C', str(self.gate.root), 'worktree', 'prune'], capture_output=True, check=False, creationflags=_NO_WINDOW)
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
def cleanup_stale_credential_locks(max_age_seconds: float=10.0, *, candidates: list[Path] | tuple[Path, ...] | None=None, check_running: bool=True) -> list[str]:
	if None is not candidates:
		lock_paths = [normalize_host_path(p) for p in candidates]
	else:
		roots = [Path.home(), Path('C:/tools/shell/home')]
		env_home = os.environ.get('HOME')
		if env_home:
			roots.append(normalize_host_path(env_home))
		seen: set[str] = set()
		lock_paths = []
		for base in roots:
			for rel in ('.git-credentials.lock', '.config/git/credentials.lock'):
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
				proc = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq git-credential-store.exe', '/NH'], capture_output=True, text=True, check=False, creationflags=_NO_WINDOW)
				running = 'git-credential-store' in (proc.stdout or '').lower()
			if not running:
				for lp in expired:
					try:
						lp.unlink(missing_ok=True)
						r.append(str(lp))
					except OSError:
						continue
	return r
def git(root: Path, *args) -> bytes:
	return GitRepoGate(root).git(*args)
def read_git(root: Path, subcommand: str='status', args: tuple[str, ...] | list[str]=()) -> dict:
	if subcommand not in READ_SUBCOMMANDS:
		raise ValueError(f'Unsupported read-only Git subcommand: {subcommand}')
	return GitRepoGate(root, strict=True).read_git(subcommand, args)
def run_git_read(root: Path, args: list[str] | tuple[str, ...], *, check: bool=True, input_bytes: bytes | None=None):
	return subprocess.run(['git', '--no-optional-locks', '-C', str(normalize_host_path(root)), *args], input=input_bytes, capture_output=True, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}, check=check, creationflags=_NO_WINDOW)
def _main_repo_for_worktree(root: Path) -> Path:
	return GitRepoGate(root).main_repo()
def is_issue_tracked_code_repo(root: Path) -> bool:
	return GitRepoGate(root).is_issue_tracked()
def ensure_repo_hooks(root: Path) -> Path | None:
	return GitRepoGate(root).ensure_hooks()
def _check_blob_size_limits(rel_posix: str, size: int, *, kind: str, sha: str='') -> None:
	GitRepoGate(Path.cwd())._check_blob_size_limits(rel_posix, size, kind=kind, sha=sha)
def verify_staged_blob_sizes(root: Path, staged_paths: list[str] | None=None) -> None:
	GitRepoGate(root).verify_staged_blob_sizes(staged_paths)
def verify_push_blob_sizes(root: Path, stdin_lines: list[str] | None=None) -> None:
	GitRepoGate(root).verify_push_blob_sizes(stdin_lines=stdin_lines)
def _extract_added_diff_urls(root: Path, rel_name: str) -> tuple[set[str], set[str]]:
	return GitRepoGate(root)._extract_added_diff_urls(rel_name)
def verify_issue_workflow(root: Path, relative: list[str], message: str | None=None, *, agent_context: bool=True) -> None:
	GitRepoGate(root).verify_issue_workflow(relative, message=message, agent_context=agent_context)
def resolve_git_repo_from_argv(argv: list[str] | tuple[str, ...], cwd: Path | None=None) -> Path | None:
	base_dir = normalize_host_path(cwd).resolve() if None is not cwd else Path.cwd().resolve()
	_, _, target_dir = _scan_git_global_opts(argv, base_dir=base_dir)
	r = None
	for anc in (target_dir, *target_dir.parents):
		if (anc / '.git').exists():
			r = anc
			break
	return r
def verify_git_write_invocation(argv: list[str] | tuple[str, ...], cwd: Path | None=None, *, agent_context: bool | None=None) -> None:
	cleanup_stale_credential_locks()
	subcommand, _ = classify_git_argv(argv)
	if subcommand in ('commit', 'push', 'filter-branch', 'merge', 'rebase', 'cherry-pick'):
		repo_root = resolve_git_repo_from_argv(argv, cwd=cwd)
		if None is not repo_root:
			GitRepoGate(repo_root).verify_write_invocation(argv, subcommand=subcommand, cwd=cwd, agent_context=agent_context)
def run_git_hook(hook_name: str, argv: list[str] | tuple[str, ...]=(), cwd: Path | None=None, *, stdin_text: str | None=None, agent_context: bool | None=None) -> int:
	cleanup_stale_credential_locks()
	repo_root = resolve_git_repo_from_argv((), cwd=cwd)
	return GitRepoGate(repo_root).run_hook(hook_name, argv, stdin_text=stdin_text, agent_context=agent_context) if None is not repo_root else 0
def _normalize_repo_paths(root: Path, paths: list[str]) -> list[str]:
	return GitRepoGate(root).normalize_paths(paths)
# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
def check_commit(root: Path, paths: list[str]) -> list[str]:
	return GitRepoGate(root, strict=True).check_commit(paths)
def create_isolated_worktree(root: Path, label: str='isolated') -> Path:
	return WorktreeCommitTransaction(GitRepoGate(root, strict=True), label=label).create()
def remove_isolated_worktree(root: Path, wt_dir: Path) -> None:
	WorktreeCommitTransaction(GitRepoGate(root, strict=True)).remove(wt_dir)
def commit_in_worktree(root: Path, paths: list[str], message: str) -> list[str]:
	return WorktreeCommitTransaction(GitRepoGate(root, strict=True)).commit(paths, message)
# 2026-10-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Git --no-optional-locks read gate, add git_shim.py wrapper, and add PreToolUse rules budget and server hygiene gates":
# https://github.com/dmitry-ai/harness/issues/17
def commit(root: Path, paths: list[str], message: str, execute=False, *, worktree: bool=False):
	return GitRepoGate(root, strict=True).commit(paths, message, execute=execute, worktree=worktree)
def verify_repo_issue_ready_for_close(code_repo: Path, repo: str, number: int) -> dict:
	return GitRepoGate(code_repo, strict=True).verify_issue_ready_for_close(repo, number)
