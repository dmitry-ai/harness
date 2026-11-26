# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.RepoTagGate import RepoTagGate
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_ready_for_close()`
# @used-by :mod:`agent_tools.repo_tag_gate`
def finalize_commit_close_check(repo: Path, commit_sha: str, issue_url: str, git_cache) -> dict:
	return RepoTagGate.finalize_close_check(repo, commit_sha, issue_url, git_cache)
# @used-by :meth:`test_repo_tag_close_gate.RepoTagCloseGateTests.test_verify_closing_commit_tag_reads_origin_from_config_without_git_config_spawn()`
# @used-by :mod:`agent_tools.repo_tag_gate`
def verify_closing_commit_tag(repo: Path, commit_sha: str, issue_url: str, *, git_cache=None) -> str:
	return RepoTagGate(repo, commit_sha, issue_url, git_cache=git_cache).verify()
__all__ = ['finalize_commit_close_check', 'verify_closing_commit_tag']
