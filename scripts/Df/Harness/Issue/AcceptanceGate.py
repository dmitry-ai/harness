# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Git.RepoGate import RepoGate
from agent_tools.path_registry import project_paths
import json
import re
import subprocess
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_REG_CMD_ADD_RE = re.compile(r'^\+\s*register_command\(', re.MULTILINE)
_UPWORK_INIT_PREFIXES = ('skills/upwork-init/', 'scripts/agent_tools/project_rename', 'scripts/agent_tools/upwork_project.py', 'scripts/agent_tools/shadow_replay')
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class AcceptanceGate:
	# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_acceptance_receipt()`
	# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_readiness()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.__check_close_commit_readiness()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_a.DfHarnessS11Wave2CCovIssuesATests.test_acceptance_gate_and_batch_runner_close_and_subparsers()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_service_metadata_prepender_and_comment_validators()`
	def __init__(self, code_repo: Path | None, repo: str, number: int, *, project_root: str | Path | None=None) -> None:
		self.__code_repo = code_repo
		self.__repo = repo
		self.__number = number
		self.__project_root = project_root
	# @used-by :meth:`AcceptanceGate.check_receipt()`
	@classmethod
	def __commit_covered(cls, code_repo: Path, commit_sha: str, repo_head: str) -> bool:
		if not commit_sha:
			r = True
		elif not repo_head:
			r = False
		elif commit_sha.lower() == repo_head.lower():
			r = True
		else:
			r = 0 == cls.__git_read(code_repo, 'merge-base', '--is-ancestor', commit_sha, repo_head).returncode
		return r
	# @used-by :meth:`AcceptanceGate.check_receipt()`
	@classmethod
	def __commit_requires_acceptance(cls, code_repo: Path, commit_sha: str) -> tuple[bool, str]:
		r = (False, '')
		if commit_sha:
			files = [ln.strip() for ln in cls.__git_read(code_repo, 'diff-tree', '--root', '--no-commit-id', '--name-only', '-r', commit_sha).stdout.splitlines() if ln.strip()]
			if 'scripts/agent_tools/cli_registry.py' in files:
				diff_txt = cls.__git_read(code_repo, 'show', '--format=', '--unified=0', commit_sha, '--', 'scripts/agent_tools/cli_registry.py').stdout
				if _REG_CMD_ADD_RE.search(diff_txt):
					r = (True, 'new CLI command in cli_registry.py')
			if (not r[0]) and any((f.startswith(_UPWORK_INIT_PREFIXES) for f in files)):
				r = (True, '/upwork-init runtime or rename/shadow-replay change')
		return r
	# @used-by :meth:`AcceptanceGate.__commit_covered()`
	# @used-by :meth:`AcceptanceGate.__commit_requires_acceptance()`
	@staticmethod
	def __git_read(code_repo: Path, *args: str) -> subprocess.CompletedProcess:
		return subprocess.run(['git', '--no-optional-locks', '-C', str(code_repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15, creationflags=_NO_WINDOW, check=False)
	# @used-by :meth:`AcceptanceGate.check_receipt()`
	def __load_receipt(self, code_repo: Path) -> dict[str, Any] | None:
		cands: list[Path] = []
		if None is not self.__project_root:
			cands.append(Path(self.__project_root).resolve())
		cands.extend((project_paths(code_repo).root, code_repo.parent))
		if 4 <= len(code_repo.parents):
			cands.append(code_repo.parents[3])
		r: dict[str, Any] | None = None
		for root in cands:
			rf = root / '\ua616/data/shadow-replay-receipt.json'
			if rf.is_file():
				try:
					parsed = json.loads(rf.read_text(encoding='utf-8-sig'))
					if isinstance(parsed, dict):
						r = parsed
						break
				except (OSError, ValueError):
					continue
		return r
	# @used-by :meth:`AcceptanceGate.check_readiness()`
	def __verify_repo_close(self, code_repo: Path, verify_fn) -> tuple[str | None, str]:
		err, stage = (None, 'pre_flight_commit_check')
		try:
			res = verify_fn(code_repo, self.__repo, self.__number, project_root=self.__project_root) if None is not verify_fn else RepoGate(code_repo, strict=True).verify_issue_ready_for_close(self.__repo, self.__number, project_root=self.__project_root)
		except (ValueError, RuntimeError) as exc:
			err = str(exc)
		else:
			if not res.get('child_issues'):
				acc_err = self.check_receipt(str(res.get('commit_sha') or ''), code_repo=code_repo)
				if None is not acc_err:
					err, stage = (acc_err, 'pre_flight_acceptance_check')
		return (err, stage)
	# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_readiness()`
	# @used-by :meth:`Df.Harness.Issue.Service.Service.__check_close_commit_readiness()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_issues_a.DfHarnessS11Wave2CCovIssuesATests.test_acceptance_gate_and_batch_runner_close_and_subparsers()`
	# @used-by :meth:`test_df_harness_s11_wave2c_issues.DfHarnessS11Wave2CIssuesTests.test_service_metadata_prepender_and_comment_validators()`
	def check_readiness(self, workspace, args, consumable: list[tuple[Path, bytes]], *, verify_fn=None, is_tracked_fn=None) -> tuple[Path | None, str | None, str]:
		from agent_tools.addon_observability import check_close_companion_health
		code_repo = self.__code_repo if None is not self.__code_repo else workspace.find_local_code_repo(self.__repo, project_root=self.__project_root, source_files=consumable, repo_root=getattr(args, 'repo_root', None))
		tracked = None is not code_repo and (is_tracked_fn(code_repo) if None is not is_tracked_fn else RepoGate(code_repo).is_issue_tracked())
		err, stage = self.__verify_repo_close(code_repo, verify_fn) if tracked else (None, 'pre_flight_commit_check')
		if None is err:
			comp_err = check_close_companion_health(self.__repo, code_repo)
			if None is not comp_err:
				err, stage = (comp_err, 'pre_flight_companion_health')
		return (code_repo, err, stage)
	# @used-by :func:`agent_tools.issues.acceptance_gate.check_close_acceptance_receipt()`
	# @used-by :meth:`AcceptanceGate.__verify_repo_close()`
	def check_receipt(self, commit_sha: str, *, code_repo: Path | None=None) -> str | None:
		eff_repo = code_repo if None is not code_repo else self.__code_repo
		receipt = self.__load_receipt(eff_repo)
		required, reason = self.__commit_requires_acceptance(eff_repo, commit_sha)
		r: str | None = None
		if None is not receipt:
			covered = self.__commit_covered(eff_repo, commit_sha, str(receipt.get('repo_head') or '').strip())
			is_fail = False is receipt.get('valid') or 0 != int(receipt.get('exit_code', 0))
			if covered and is_fail:
				r = f"EXEC-2 acceptance gate: latest shadow-replay receipt failed (valid={receipt.get('valid')}, exit_code={receipt.get('exit_code')}) for {self.__repo}#{self.__number}; fix and re-run passing shadow-replay before closing"
			elif required and (not covered):
				r = f'EXEC-2 acceptance gate: shadow-replay receipt is stale (repo_head does not cover closing commit {commit_sha[:12]}) for {reason} in {self.__repo}#{self.__number}; run passing shadow-replay before closing'
		elif required:
			r = f'EXEC-2 acceptance gate: missing passing shadow-replay receipt (\ua616/data/shadow-replay-receipt.json) for {reason} in {self.__repo}#{self.__number}; run passing shadow-replay before closing'
		return r
