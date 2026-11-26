# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Git.CdpBypassAudit import CdpBypassAudit
from Df.Harness.Git.CommitArgsParser import CommitArgsParser
from Df.Harness.Git.GitGlobalOptsScanner import GitGlobalOptsScanner
from Df.Harness.Git.GitReadAudit import GitReadAudit
from Df.Harness.Git.GitWriteAudit import GitWriteAudit
from Df.Harness.Git.IssueActionExtractor import IssueActionExtractor
import re
_ADHOC_HTTP_CLIENT_RE = re.compile(r'(?:\burllib\.request\b|\burlopen\s*\(|\brequests\.(?:get|post|head|request|Session)\b|\bhttpx\.(?:get|post|Client)\b|\bInvoke-(?:WebRequest|RestMethod)\b|\b(?:iwr|irm|curl(?:\.exe)?|wget(?:\.exe)?)\s+)', re.I)
_EXTERNAL_URL_RE = re.compile(r'https?://(?!(?:localhost|127\.0\.0\.1|\[::1\])\b)[A-Za-z0-9.-]+', re.I)
_SANCTIONED_HTTP_RUNNER_RE = re.compile(r'(?:harness\.py|upwork_project\.py|validate_links\.py|df_github_issue\.py|\bunittest\b|\bpytest\b)', re.I)
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ShellInspector:
	# @used-by :func:`agent_tools.shell_audit.classify_git_argv()`
	# @used-by :meth:`Df.Harness.Git.PushValidator.PushValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def classify_git_argv(self, argv: list[str] | tuple[str, ...]) -> tuple[str | None, bool]:
		tokens = list(argv)
		sub_idx, has_flag, _ = self.scan_git_global_opts(tokens)
		return (tokens[sub_idx] if None is not sub_idx else None, has_flag)
	# @used-by :func:`agent_tools.shell_audit.extract_issue_actions_from_outputs()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def extract_issue_actions(self, outputs: list[str] | tuple[str, ...]) -> list[dict]:
		return IssueActionExtractor(outputs).extract()
	# @used-by :func:`agent_tools.shell_audit._parse_commit_subcommand_args()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def parse_commit_subcommand_args(self, argv: list[str] | tuple[str, ...]) -> tuple[list[str], str | None, str | None, bool, bool, list[str]]:
		return CommitArgsParser(argv).parse()
	# @used-by :func:`agent_tools.shell_audit.prohibited_cdp_bypass_commands()`
	# @used-by :meth:`ShellInspector.unpersisted_http_fetch_commands()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	# @used-by :meth:`test_turn_completion.AntigravityAddonsIntegrationTests.test_sanctioned_addon_roots_and_cdp_bypass_gate()`
	def prohibited_cdp_bypass_commands(self, text: str, *, config=None) -> list[str]:
		return CdpBypassAudit(text, config=config).detect()
	# @used-by :func:`agent_tools.shell_audit.prohibited_git_write_commands()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def prohibited_git_write_commands(self, text: str) -> list[str]:
		return GitWriteAudit(text).detect()
	# @used-by :func:`agent_tools.shell_audit._scan_git_global_opts()`
	# @used-by :meth:`ShellInspector.classify_git_argv()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def scan_git_global_opts(self, argv: list[str] | tuple[str, ...], *, base_dir: Path | None=None) -> tuple[int | None, bool, Path | None]:
		return GitGlobalOptsScanner(argv, base_dir=base_dir).scan()
	# @used-by :func:`agent_tools.shell_audit.unflagged_git_read_commands()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def unflagged_git_read_commands(self, text: str) -> list[str]:
		return GitReadAudit(text).detect()
	# @used-by :func:`agent_tools.shell_audit.unpersisted_http_fetch_commands()`
	# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
	# @used-by :meth:`test_df_harness_s11_wave2c_git.DfHarnessS11Wave2CGitTests.test_shell_audit_single_class_modules_and_facade()`
	def unpersisted_http_fetch_commands(self, text: str) -> list[str]:
		r = list(self.prohibited_cdp_bypass_commands(text))
		if isinstance(text, str) and text.strip() and (not _SANCTIONED_HTTP_RUNNER_RE.search(text)) and _EXTERNAL_URL_RE.search(text) and _ADHOC_HTTP_CLIENT_RE.search(text):
			snippet = ' '.join(text.strip().split())[:240]
			if snippet not in r:
				r.append(snippet)
		return r
