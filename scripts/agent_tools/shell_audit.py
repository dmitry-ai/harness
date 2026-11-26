# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from pathlib import Path
from Df.Core.lib.array.other.unique_fast import dfa_unique_fast
from Df.Harness.Git.CdpBypassAudit import _CDP_PROTOCOL_RE
from Df.Harness.Git.GitSegmentExtractor import GitSegmentExtractor
from Df.Harness.Git.HostPathNormalizer import HostPathNormalizer
from Df.Harness.Git.ShellInspector import ShellInspector as ShellCommandInspector
from Df.Harness.Git.ShellSegmenter import ShellSegmenter
from Df.Harness.lib.shell import ISSUE_LINKED_CODE_SUFFIXES as _ISSUE_LINKED_CODE_SUFFIXES, READ_SUBCOMMANDS, dfh_extract_comment_issue_urls, dfh_normalize_commit_message, dfh_parse_issue_url, dfh_protected_browser_perimeter
from .runtime_cache import run_shell_violation_scan
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_COMMIT_MESSAGE_ISSUE_URL_RE = re.compile('^https://github\\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\\d+)$')
_CYGDRIVE_RE = re.compile('^/(?:cygdrive|mnt)/([a-zA-Z])(?:/(.*))?$')
_GITHUB_ISSUE_URL_RE = re.compile('https://github\\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\\d+\\b')
_VALUE_GLOBAL_OPTS = ('-C', '--git-dir', '--work-tree', '-c', '--exec-path', '--namespace', '--super-prefix', '--config-env')
_INSPECTOR = ShellCommandInspector()
# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.is_git_commit_command()`
def _iter_shell_git_segments(candidate: str) -> list[tuple[str, list[str]]]:
	return GitSegmentExtractor(candidate).extract()
# @used-by unused
def _parse_commit_subcommand_args(argv: list[str] | tuple[str, ...]) -> tuple[list[str], str | None, str | None, bool, bool, list[str]]:
	return _INSPECTOR.parse_commit_subcommand_args(argv)
# @used-by unused
def _scan_git_global_opts(argv: list[str] | tuple[str, ...], *, base_dir: Path | None=None) -> tuple[int | None, bool, Path | None]:
	return _INSPECTOR.scan_git_global_opts(argv, base_dir=base_dir)
# @used-by :func:`agent_tools.issue_first_bg.is_df_issue_command_text()`
# @used-by :meth:`Df.Harness.Gate.FailfastGate.FailfastGate.__normalize_test_cmd()`
# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.__collect_write_matches()`
# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.classify_test_command()`
# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.shell_test_delete_targets()`
# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__collect_failfast_warnings()`
# @used-by :meth:`Df.Harness.Tdd.ServiceExempt.ServiceExempt.__is_service_command()`
def _split_shell_segments(cmd: str) -> list[str]:
	return ShellSegmenter(cmd).split()
# @used-by unused
def _unquote(token: str) -> str:
	if not (2 <= len(token) and token[0] == token[-1] and token[0] in ('"', "'")):
		r = token
	else:
		r = token[1:-1].replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
	return r
# @used-by :func:`agent_tools.git_gate.verify_git_write_invocation()`
# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__prepare()`
# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.is_git_commit_command()`
def classify_git_argv(argv: list[str] | tuple[str, ...]) -> tuple[str | None, bool]:
	return _INSPECTOR.classify_git_argv(argv)
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_touched_code_file()`
def extract_comment_issue_urls(text: str) -> set[str]:
	return dfh_extract_comment_issue_urls(text)
# @used-by :func:`Df.Harness.lib.completion_child_trace._process_tool_calls_row()`
# @used-by :func:`agent_tools.issue_first_bg._record_bg_seg_issues()`
# @used-by :func:`agent_tools.issue_first_gate.build_issue_action_events()`
# @used-by :func:`test_doc5_golden_feature_turn._extract_fixture_issue_actions()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__record_subagent_tool_calls()`
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__record_tool_calls()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__finalize_turn()`
# @used-by :meth:`Df.Harness.Platform.Codex.TurnScanner.TurnScanner.__visit_subagent_rows()`
# @used-by :meth:`test_issue_first_gate.IssueFirstGateCoreTests.test_extract_issue_actions_recognizes_fetch_and_anti_spoofing_command_check()`
# @used-by :meth:`test_issue_preflight_and_batch.IssuePreflightAndBatchTests.test_batch_close_enforces_grounding_consumes_inputs_and_extracts_actions()`
# @used-by :meth:`test_issue_preflight_and_batch.IssuePreflightAndBatchTests.test_batch_create_verifies_readback_and_action_extraction()`
def extract_issue_actions_from_outputs(outputs: list[str] | tuple[str, ...]) -> list[dict]:
	return _INSPECTOR.extract_issue_actions(outputs)
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._has_workspace_parent_issue()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_latest_commits()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_touched_code_file()`
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_git_read_cache_detects_issue_url_in_untracked_dotpy()`
# @used-by :meth:`test_df_harness_dedup_s8.DfHarnessDedupS8Tests.test_clean_null_and_unique_fast_delegation_to_df()`
# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_diff_cache_runs_once_for_dirty_repo_and_zero_times_for_clean_repo()`
# @used-by :meth:`test_dirty_diff_issue_scope.DirtyDiffIssueScopeTests.test_historical_header_ignored_while_added_removed_and_untracked_refs_caught()`
def extract_issue_urls(text: str) -> list[str]:
	return dfa_unique_fast(_GITHUB_ISSUE_URL_RE.findall(text or ''))
# @used-by :meth:`Df.Harness.Gate.CdpBypassGate.CdpBypassGate.__check_write_content()`
# @used-by :meth:`Df.Harness.Tdd.Exemption.Exemption.verify_staged_issue_urls()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._inspect_touched_code_file()`
# @used-by :meth:`test_df_dotpy_bootstrap.DfDotPyBootstrapTests.test_gates_and_classifiers_recognize_dotpy_files()`
def is_code_file(rel_path: str | Path) -> bool:
	return (Path(rel_path).suffix.lower() or (Path(rel_path).name.lower() if Path(rel_path).name.startswith('.') else '')) in _ISSUE_LINKED_CODE_SUFFIXES
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.find_matching_recipes()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_shell_audit_inspector_and_single_pass_repo_gate_commit()`
def normalize_commit_message(message: str | None) -> str:
	return dfh_normalize_commit_message(message)
# @used-by :func:`Df.Harness.lib.runtime_snapshot_ops.dfh_set_local_hooks_path()`
# @used-by :func:`agent_tools.git_gate.run_git_read()`
# @used-by :func:`agent_tools.git_ignore.resolve_global_git_ignore_path()`
# @used-by :func:`agent_tools.git_ignore.resolve_managed_git_ignore_target()`
# @used-by :func:`agent_tools.issue_first_gate.build_code_write_issue_first_event()`
# @used-by :func:`agent_tools.issue_first_gate.evaluate_pre_tool_use_issue_first()`
# @used-by :func:`agent_tools.issue_first_gate.resolve_issue_first_target()`
# @used-by :meth:`Df.Harness.Arch.Enforcement.Enforcement.__resolve_pre_tool_target()`
# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__normalize_arg_token()`
# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__resolve_git_from_path()`
# @used-by :meth:`Df.Harness.Cli.GitShim.GitShim.__resolve_system_git()`
# @used-by :meth:`Df.Harness.Gate.CodeSizeAnalyzer.CodeSizeAnalyzer.resolve_python_target()`
# @used-by :meth:`Df.Harness.Gate.IssueCommentScanner.IssueCommentScanner.resolve_target()`
# @used-by :meth:`Df.Harness.Gate.XrefChecker.XrefChecker.resolve_target()`
# @used-by :meth:`Df.Harness.Tdd.CodeClassifier.CodeClassifier.resolve_code_scope()`
# @used-by :meth:`Df.Harness.Tdd.CommandInspector.CommandInspector.__resolve_shell_target()`
# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__eval_pre_write()`
# @used-by :meth:`Df.Harness.Tdd.Enforcement.Enforcement.__resolve_worktree_git_dirs()`
# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.__resolve_event_target_scopes()`
# @used-by :meth:`Df.Harness.Tdd.Evaluator.Evaluator.git_main_repo_root()`
# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.build_file_write_event()`
# @used-by :meth:`Df.Harness.Tdd.EventsExtractor.EventsExtractor.is_git_commit_command()`
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.__resolve_repo_binding()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_git_blob_size_gates_cygwin_paths_and_stale_credential_locks()`
def normalize_host_path(value: str | Path) -> Path:
	return HostPathNormalizer(value).normalize()
# @used-by :func:`agent_tools.issue_first_gate._seed_open_issues_from_requests()`
# @used-by :func:`agent_tools.issues.parity.merge_turn_issue_item()`
# @used-by :meth:`Df.Harness.Tdd.Exemption.Exemption.__is_same_repo_url()`
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.__recipe_matches_repo()`
# @used-by :meth:`Df.Harness.Tdd.MechanicalExemption.MechanicalExemption.__validate_recipe_inputs()`
# @used-by :meth:`Df.Harness.Tdd.RatchetGuard.RatchetGuard.__find_issue_approval()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._committed_parent_numbers()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._has_workspace_parent_issue()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._parent_linked_committed_urls()`
# @used-by :meth:`agent_tools.issues.auditor.TurnIssueLifecycleAuditor._verify_required_repo_issues()`
def parse_issue_url(url: str) -> tuple[str, int] | None:
	return dfh_parse_issue_url(url)
# @used-by :meth:`Df.Harness.Gate.CdpBypassGate.CdpBypassGate.check()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m4_cdp_bypass_gate_and_m5_browser_mcp_gate()`
def prohibited_cdp_bypass_commands(text: str, *, config=None) -> list[str]:
	return _INSPECTOR.prohibited_cdp_bypass_commands(text, config=config)
# @used-by :meth:`Df.Harness.Gate.GitWriteGate.GitWriteGate.check()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_issue_tracked_code_repo_requires_github_issue_url_in_code_and_commit_message()`
def prohibited_git_write_commands(text: str) -> list[str]:
	return _INSPECTOR.prohibited_git_write_commands(text)
# @used-by :meth:`Df.Harness.Gate.CdpBypassGate.CdpBypassGate.__check_read_perimeter()`
# @used-by :meth:`test_runtime_cache_and_evidence_fastpath_m9.RuntimeCacheAndEvidenceFastpathM9Tests.test_runtime_settings_cache_invalidates_on_file_or_env_change_and_isolates_mutations()`
def protected_browser_perimeter(config=None) -> dict:
	return dfh_protected_browser_perimeter(config)
# @used-by :func:`Df.Harness.lib.trace_effects.dfh_collect_shell_violations()`
# @used-by :meth:`test_agents_loader.AgentsLoaderTests.test_read_git_and_git_shim_and_unflagged_detector()`
# @used-by :meth:`test_turn_completion.CompletionCase.test_unflagged_git_read_allows_env_assignment()`
def unflagged_git_read_commands(text: str) -> list[str]:
	return _INSPECTOR.unflagged_git_read_commands(text)
# @used-by :func:`Df.Harness.lib.trace_effects.dfh_collect_shell_violations()`
# @used-by :meth:`test_text_browser.TextBrowserTests.test_m4_cdp_bypass_gate_and_m5_browser_mcp_gate()`
def unpersisted_http_fetch_commands(text: str) -> list[str]:
	return _INSPECTOR.unpersisted_http_fetch_commands(text)
