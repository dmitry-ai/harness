# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
ISSUE_LINKED_CODE_SUFFIXES = ('.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.cs', '.ps1', '.sh', '.bash', '.cmd', '.bat', '.vbs')
READ_SUBCOMMANDS = ('status', 'diff', 'log', 'rev-parse', 'show', 'ls-files')
_COMMIT_MESSAGE_ISSUE_URL_RE = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\d+)$')
_GITHUB_ISSUE_URL_RE = re.compile(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+\b')
# @used-by :func:`agent_tools.shell_audit.extract_comment_issue_urls()`
# @used-by :meth:`Df.Harness.Git.RepoGate.RepoGate.extract_added_diff_urls()`
# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
def dfh_extract_comment_issue_urls(text: str) -> set[str]:
	r: set[str] = set()
	for line in (text or '').splitlines():
		if re.match(r'^\s*(?:#|//|REM\b|/\*|\*)', line, re.I):
			r.update(_GITHUB_ISSUE_URL_RE.findall(line))
	return r
# @used-by :meth:`Df.Harness.Git.IssueCloseVerifier.IssueCloseVerifier.__ensure_clean()`
# @used-by :meth:`Df.Harness.Git.IssueCloseVerifier.IssueCloseVerifier.verify()`
# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
def dfh_extract_issue_urls(text: str) -> list[str]:
	return dfa_unique_fast(_GITHUB_ISSUE_URL_RE.findall(text or ''))
# @used-by :func:`agent_tools.shell_audit.normalize_commit_message()`
# @used-by :meth:`Df.Harness.Git.IssueWorkflowVerifier.IssueWorkflowVerifier.verify()`
# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.__verify_commit()`
# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
def dfh_normalize_commit_message(message: str | None) -> str:
	return '\n'.join((line for line in (message or '').splitlines() if not line.startswith('#'))).strip()
# @used-by :func:`agent_tools.shell_audit.parse_issue_url()`
# @used-by :meth:`Df.Harness.Git.IssueWorkflowVerifier.IssueWorkflowVerifier.__verify_single_url()`
# @used-by :meth:`Df.Harness.Git.IssueWorkflowVerifier.IssueWorkflowVerifier.verify()`
# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.__verify_commit()`
# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
def dfh_parse_issue_url(url: str) -> tuple[str, int] | None:
	m = _COMMIT_MESSAGE_ISSUE_URL_RE.fullmatch((url or '').strip())
	return (m.group(1), int(m.group(2))) if m else None
# @used-by :func:`agent_tools.shell_audit.protected_browser_perimeter()`
# @used-by :meth:`Df.Harness.Git.CdpBypassAudit.CdpBypassAudit.detect()`
# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_landing_lease_and_polyglot_land()`
def dfh_protected_browser_perimeter(config=None) -> dict:
	from agent_tools import runtime as _rt
	from agent_tools.runtime_cache import cached_browser_perimeter
	return cached_browser_perimeter(config, _rt)
