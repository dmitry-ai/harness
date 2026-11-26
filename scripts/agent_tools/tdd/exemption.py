# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Tdd.Exemption import Exemption
from . import diff_executability
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_touched_code_file()`
# @used-by :mod:`agent_tools.tdd.exemption`
def filter_repo_turn_issue_urls(comment_urls: set[str], turn_issues: dict, repo_slug: str | None) -> list[str]:
	return Exemption.filter_repo_turn_issue_urls(comment_urls, turn_issues, repo_slug)
# @used-by :mod:`agent_tools.tdd.exemption`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_diff_exempt(path: str | Path, old_text: str | None, new_text: str | None, *, repo_root: Path | None=None, message: str | None=None, project_root: Path | None=None) -> bool:
	return diff_executability.is_non_executable_diff(path, old_text, new_text, repo_root=repo_root, message=message, project_root=project_root)
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_touched_code_file()`
# @used-by :mod:`agent_tools.tdd.exemption`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_git_path_exempt(repo_root: Path, rel_posix: str, *, disk_text: str | None=None, use_index: bool=False, message: str | None=None, project_root: Path | None=None) -> bool:
	return diff_executability.is_git_path_non_executable(repo_root, rel_posix, disk_text=disk_text, use_index=use_index, message=message, project_root=project_root)
# @used-by :func:`agent_tools.tdd.evaluator.evaluate_tdd_events()`
# @used-by :meth:`test_tdd_fast_path.TddFastPathTests.test_evaluator_memoizes_exemption_and_allows_exempt_only_edits()`
# @used-by :mod:`agent_tools.tdd.exemption`
# @used-by :mod:`agent_tools.tdd_gate`
# @used-by :mod:`agent_tools.tdd`
def is_write_event_exempt(raw_path: str | Path, scope_str: str, *, project_root: Path | None=None) -> bool:
	return Exemption.is_write_event_exempt(raw_path, scope_str, project_root=project_root, git_non_exec_fn=diff_executability.is_git_path_non_executable)
# @used-by :meth:`agent_tools.git_gate.GitRepoGate.verify_issue_workflow()`
# @used-by :meth:`test_cross_repo_issue_urls.CrossRepoIssueUrlsTests.test_staged_issue_urls_ignore_foreign_repo_urls_and_check_dotpy()`
# @used-by :mod:`agent_tools.tdd.exemption`
def verify_staged_issue_urls(gate, relative: list[str], stripped_msg: str | None, *, project_root: Path | None=None) -> set[str]:
	return Exemption.verify_staged_issue_urls(gate, relative, stripped_msg, project_root=project_root)
__all__ = ['filter_repo_turn_issue_urls', 'is_diff_exempt', 'is_git_path_exempt', 'is_write_event_exempt', 'verify_staged_issue_urls']
