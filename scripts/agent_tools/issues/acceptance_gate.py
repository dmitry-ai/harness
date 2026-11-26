# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Require passing shadow-replay acceptance receipt in df_github_issue close gate":
# https://github.com/dmitry-ai/harness/issues/291
from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import re
import subprocess
from ..git_gate import _NO_WINDOW, is_issue_tracked_code_repo, verify_repo_issue_ready_for_close
from ..path_registry import project_paths
_REG_CMD_ADD_RE = re.compile(r'^\+\s*register_command\(', re.MULTILINE)
_UPWORK_INIT_PREFIXES = ('skills/upwork-init/', 'scripts/agent_tools/project_rename', 'scripts/agent_tools/upwork_project.py', 'scripts/agent_tools/shadow_replay')
# @used-by :func:`_commit_covered_by_receipt()`, :func:`_commit_requires_acceptance()`
def _git_read(code_repo: Path, *args: str) -> subprocess.CompletedProcess:
	return subprocess.run(['git', '--no-optional-locks', '-C', str(code_repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15, creationflags=_NO_WINDOW, check=False)
# @used-by :func:`check_close_acceptance_receipt()`
def _commit_covered_by_receipt(code_repo: Path, commit_sha: str, repo_head: str) -> bool:
	if not commit_sha:
		r = True
	elif not repo_head:
		r = False
	elif commit_sha.lower() == repo_head.lower():
		r = True
	else:
		r = 0 == _git_read(code_repo, 'merge-base', '--is-ancestor', commit_sha, repo_head).returncode
	return r
# @used-by :func:`check_close_acceptance_receipt()`
def _commit_requires_acceptance(code_repo: Path, commit_sha: str) -> tuple[bool, str]:
	r = (False, '')
	if commit_sha:
		files = [ln.strip() for ln in _git_read(code_repo, 'diff-tree', '--root', '--no-commit-id', '--name-only', '-r', commit_sha).stdout.splitlines() if ln.strip()]
		if 'scripts/agent_tools/cli_registry.py' in files:
			diff_txt = _git_read(code_repo, 'show', '--format=', '--unified=0', commit_sha, '--', 'scripts/agent_tools/cli_registry.py').stdout
			if _REG_CMD_ADD_RE.search(diff_txt):
				r = (True, 'new CLI command in cli_registry.py')
		if (not r[0]) and any((f.startswith(_UPWORK_INIT_PREFIXES) for f in files)):
			r = (True, '/upwork-init runtime or rename/shadow-replay change')
	return r
# @used-by :func:`check_close_acceptance_receipt()`
def _load_acceptance_receipt(code_repo: Path, project_root: str | Path | None) -> dict[str, Any] | None:
	cands: list[Path] = []
	if None is not project_root:
		cands.append(Path(project_root).resolve())
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
# @used-by :func:`check_close_readiness()`
def check_close_acceptance_receipt(code_repo: Path, repo: str, number: int, commit_sha: str, *, project_root: str | Path | None=None) -> str | None:
	receipt = _load_acceptance_receipt(code_repo, project_root)
	required, reason = _commit_requires_acceptance(code_repo, commit_sha)
	r: str | None = None
	if None is not receipt:
		covered = _commit_covered_by_receipt(code_repo, commit_sha, str(receipt.get('repo_head') or '').strip())
		is_fail = False is receipt.get('valid') or 0 != int(receipt.get('exit_code', 0))
		if covered and is_fail:
			r = f"EXEC-2 acceptance gate: latest shadow-replay receipt failed (valid={receipt.get('valid')}, exit_code={receipt.get('exit_code')}) for {repo}#{number}; fix and re-run passing shadow-replay before closing"
		elif required and (not covered):
			r = f'EXEC-2 acceptance gate: shadow-replay receipt is stale (repo_head does not cover closing commit {commit_sha[:12]}) for {reason} in {repo}#{number}; run passing shadow-replay before closing'
	elif required:
		r = f'EXEC-2 acceptance gate: missing passing shadow-replay receipt (\ua616/data/shadow-replay-receipt.json) for {reason} in {repo}#{number}; run passing shadow-replay before closing'
	return r
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._check_close_commit_readiness()`
def check_close_readiness(workspace, args, repo: str, number: int, consumable: list[tuple[Path, bytes]], project_root: str | Path | None) -> tuple[Path | None, str | None, str]:
	from ..addon_observability import check_close_companion_health
	code_repo = workspace.find_local_code_repo(repo, project_root=project_root, source_files=consumable, repo_root=getattr(args, 'repo_root', None))
	err: str | None = None
	stage = 'pre_flight_commit_check'
	if None is not code_repo and is_issue_tracked_code_repo(code_repo):
		try:
			res = verify_repo_issue_ready_for_close(code_repo, repo, number, project_root=project_root)
		except (ValueError, RuntimeError) as exc:
			err, stage = (str(exc), 'pre_flight_commit_check')
		else:
			if not res.get('child_issues'):
				acc_err = check_close_acceptance_receipt(code_repo, repo, number, str(res.get('commit_sha') or ''), project_root=project_root)
				if None is not acc_err:
					err, stage = (acc_err, 'pre_flight_acceptance_check')
	if None is err:
		comp_err = check_close_companion_health(repo, code_repo)
		if None is not comp_err:
			err, stage = (comp_err, 'pre_flight_companion_health')
	return (code_repo, err, stage)
__all__ = ['check_close_acceptance_receipt', 'check_close_readiness']