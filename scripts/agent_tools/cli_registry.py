# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Callable
import argparse
import sys
from .cli_common import add_arg_specs
# 2026-11-23
# "Add deterministic FIFO repository landing lease with reactive wait":
# https://github.com/dmitry-ai/harness/issues/163
_REGISTRY: dict[str, dict] = {}
# @used-by :func:`add_registered_parsers()`
# @used-by :func:`dispatch_registered()`
# @used-by :func:`execute_registered()`
# @used-by :func:`registered_commands()`
# @used-by :func:`render_cli_index()`
# @used-by :meth:`test_worker_semaphore_and_xdist.WorkerSemaphoreAndXdistTests.test_pytest_worksteal_runner_and_cli_runner_option()`
def _ensure_builtin_plugins() -> None:
	if not _REGISTRY:
		_register_builtins()
# 2026-11-24
# "Enforce Markdown table ban and /df-analysis structural validation across response gates":
# https://github.com/dmitry-ai/harness/issues/181
# @used-by :func:`_register_analysis_builtins()`
def _exec_analysis_check(args) -> dict:
	from .cli_common import load_operation_input
	from .statements import markdown_table_issues, validate_df_analysis
	text = load_operation_input(args, args.response_file).decode('utf-8')
	issues = [*markdown_table_issues(text), *validate_df_analysis(text, mode=args.mode)]
	return {'valid': not issues, 'mode': args.mode, 'issue_count': len(issues), 'issues': issues}
# 2026-11-23
# "Replace monolithic CLI router with declarative registry and modular docs":
# https://github.com/dmitry-ai/harness/issues/168
# @used-by :func:`_register_analysis_builtins()`
def _exec_cli_docs(_args) -> dict:
	return {'valid': True, 'commands': list(registered_commands()), 'markdown': render_cli_index()}
# @used-by :func:`_register_analysis_builtins()`
def _exec_land_acquire(args) -> dict:
	from .landing_lease import acquire_lease
	return acquire_lease(args.repo, owner=args.owner, wait=bool(args.wait), timeout=args.timeout, ttl=args.ttl, poll_interval=args.poll_interval)
# @used-by :func:`_register_analysis_builtins()`
def _exec_land_release(args) -> dict:
	from .landing_lease import release_lease
	return release_lease(args.repo, owner=args.owner, force=bool(args.force))
# @used-by :func:`_register_analysis_builtins()`
def _exec_land_status(args) -> dict:
	from .landing_lease import lease_status
	return lease_status(args.repo)
# 2026-11-24
# "Add harness perf-profile-tests CLI for test suite and subprocess profiling":
# https://github.com/dmitry-ai/harness/issues/192
# @used-by :func:`_register_analysis_builtins()`
def _exec_perf_profile_tests(args) -> dict:
	from .perf.suite_profiler import run_perf_profile_cli
	return run_perf_profile_cli(args)
# 2026-11-24
# "Add harness perf-timesheet CLI for deterministic turn chronometry":
# https://github.com/dmitry-ai/harness/issues/191
# @used-by :func:`_register_analysis_builtins()`
def _exec_perf_timesheet(args) -> dict:
	from .perf.timesheet import run_perf_timesheet_cli
	return run_perf_timesheet_cli(args)
# 2026-11-24
# "Add structured problem metadata builder and CLI command":
# https://github.com/dmitry-ai/harness/issues/180
# @used-by :func:`_register_analysis_builtins()`
def _exec_problem_metadata(args) -> dict:
	from .metadata import build_problem_metadata, render_metadata_header
	meta = build_problem_metadata(issue_url=args.issue, project_root=args.project, source_project_root=args.source_project, allow_no_issue=bool(args.no_issue))
	return {'valid': True, 'metadata': meta, 'markdown': render_metadata_header(meta).rstrip('\n') + '\n'}
# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
# @used-by :func:`_register_analysis_builtins()`
def _exec_rename_project(args) -> dict:
	from .project_rename import rename_project
	return rename_project(args.project, domain=args.domain, topic=args.topic, daily_root=args.daily_root, register_native=False if args.no_register else None, launcher_root=args.launcher_root)
# 2026-11-26 "Implement daily-counter Git tag engine and repo-tag CLI commands": https://github.com/dmitry-ai/harness/issues/262
# @used-by :func:`_register_analysis_builtins()`
def _exec_repo_tag(args) -> dict:
	from .repo_tags import run_repo_tag_cli
	return run_repo_tag_cli(args)
# @used-by :func:`_register_analysis_builtins()`
def _exec_repo_tag_retro(args) -> dict:
	from .repo_tags import retro_tag_repo
	return retro_tag_repo(args.repo, apply=bool(args.apply), push=bool(args.push), include_task_groups=bool(args.include_task_groups), extra_commits=list(args.extra_commit or ()))
# 2026-11-26
# "Add deterministic rules-audit CLI and aggregate budget enforcement":
# https://github.com/dmitry-ai/harness/issues/244
# @used-by :func:`_register_analysis_builtins()`
def _exec_rules_audit(args) -> dict:
	from .rules_audit import audit_rules, build_semantic_audit_brief
	from .rules_manifest import resolve_rules_primary
	from .runtime import PRIMARY
	prim = resolve_rules_primary(args.primary, PRIMARY)
	rep = audit_rules(prim, workspace=args.workspace)
	if args.semantic_brief:
		rep['semantic_brief'] = build_semantic_audit_brief(prim, workspace=args.workspace)
	return rep
# 2026-11-26 "Add host test-worker semaphore and worksteal pytest mode": https://github.com/dmitry-ai/harness/issues/354
# @used-by :func:`_register_analysis_builtins()`
def _exec_run_tests(args) -> dict:
	from .suite_runner import run_test_suite
	return run_test_suite(args.target, workers=args.workers, module_timeout=args.module_timeout, failfast=not args.no_failfast, pattern=args.pattern, modules=args.module, runner=args.runner)
# 2026-11-24
# "Deploy immutable Harness runtime snapshots with LKG fallback":
# https://github.com/dmitry-ai/harness/issues/184
# @used-by :func:`_register_analysis_builtins()`
def _exec_runtime_promote(args) -> dict:
	from .runtime import PRIMARY
	from .runtime_snapshot import promote_runtime_snapshot
	return promote_runtime_snapshot(args.primary or PRIMARY, store_dir=args.store_dir, keep=args.keep)
# @used-by :func:`_register_runtime_builtins()`
def _exec_runtime_status(args) -> dict:
	from .runtime import PRIMARY
	from .runtime_snapshot import check_runtime_snapshot
	return check_runtime_snapshot(args.primary or PRIMARY, store_dir=args.store_dir)
# 2026-11-24
# "Prevent context compaction with schema-help CLI and staged analysis merge":
# https://github.com/dmitry-ai/harness/issues/217
# @used-by :func:`_register_runtime_builtins()`
def _exec_schema_help(args) -> dict:
	from .schema_help import schema_help_payload
	return schema_help_payload(args.topic)
# 2026-11-25
# "Add auditable mechanical replacement recipe exemption for TDD and per-file issue gates":
# https://github.com/dmitry-ai/harness/issues/239
# @used-by :func:`_register_runtime_builtins()`
def _exec_tdd_exempt_mechanical(args) -> dict:
	from .tdd.mechanical import record_mechanical_exemption
	return record_mechanical_exemption(args.project, repo=args.repo, issue_url=args.issue, pattern=args.pattern, replacement=args.replacement, reason=args.reason, is_regex=bool(args.regex), ignore_case=bool(args.ignore_case), conversation=args.conversation, turn_key=args.turn_key)
# 2026-11-25
# "Add workspace-local shadow-replay CLI command and EXEC-2 acceptance gate":
# https://github.com/dmitry-ai/harness/issues/237
# 2026-11-26 "Add mutating command execution mode to shadow-replay with isolated native profiles": https://github.com/dmitry-ai/harness/issues/289
# @used-by :func:`_register_runtime_builtins()`
def _exec_shadow_replay(args) -> dict:
	from .shadow_replay import run_shadow_replay
	return run_shadow_replay(args.project, args.conversation, launcher=args.launcher, workspace=args.workspace, platform=args.platform or 'antigravity', backend=args.backend, response_file=args.response_file, keep=bool(args.keep), exec_rename_domain=args.exec_rename_domain, command=args.command_spec)
# 2026-11-24
# "Enforce watchdog timeout and stdin isolation for unittest and pytest in failfast_gate":
# https://github.com/dmitry-ai/harness/issues/205
# @used-by :func:`_register_runtime_builtins()`
def _exec_test_watchdog(args) -> dict:
	from .watchdog_runner import run_watchdog_cli
	return run_watchdog_cli(args)
# 2026-11-24
# "Add deterministic reactive wait primitive for transient repository and journal contention":
# https://github.com/dmitry-ai/harness/issues/199
# @used-by :func:`_register_runtime_builtins()`
def _exec_wait_repo(args) -> dict:
	from .repo_wait import wait_for_repo
	return wait_for_repo(args.repo, clean=bool(args.clean), lease_free=bool(args.lease_free), timeout=args.timeout, poll_interval=args.poll)
# 2026-11-23
# "Add isolated git worktree task workflow and worktree-scoped issue gates":
# https://github.com/dmitry-ai/harness/issues/165
# @used-by :func:`_register_runtime_builtins()`
def _exec_worktree_begin(args) -> dict:
	from .worktree_flow import worktree_begin
	return worktree_begin(args.repo, args.task, base_ref=args.base, worktrees_dir=args.worktrees_dir)
# @used-by :func:`_register_runtime_builtins()`
def _exec_worktree_cleanup(args) -> dict:
	from .worktree_flow import worktree_cleanup
	return worktree_cleanup(args.repo, args.target, force=bool(args.force))
# @used-by :func:`_register_runtime_builtins()`
def _exec_worktree_land(args) -> dict:
	from .worktree_flow import worktree_land
	# 2026-11-24
	# "Remove landed worktrees by default and flag stale worktrees in worktree-status":
	# https://github.com/dmitry-ai/harness/issues/203
	if args.keep and args.remove:
		raise ValueError('Cannot combine --keep and --remove in worktree-land')
	# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
	# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
	return worktree_land(args.worktree, target_branch=args.target, run_tests=not args.no_tests, push=bool(args.push), remove=not bool(args.keep), owner=args.owner, wait_timeout=args.timeout, workers=args.workers, tag=bool(args.tag), no_tests_reason=args.no_tests_reason)
# @used-by :func:`_register_runtime_builtins()`
def _exec_worktree_status(args) -> dict:
	from .worktree_flow import worktree_status
	return worktree_status(args.repo)
# 2026-11-26
# "Implement Python AST cross-reference analyzer and sync CLI":
# https://github.com/dmitry-ai/harness/issues/287
# @used-by :func:`_register_runtime_builtins()`
def _exec_xref_check(args) -> dict:
	from .xref import run_xref_check
	return run_xref_check(args.repo, lang=args.lang, files=args.file or None)
# @used-by :func:`_register_runtime_builtins()`
def _exec_xref_sync(args) -> dict:
	from .xref import run_xref_sync
	return run_xref_sync(args.repo, lang=args.lang, apply=not bool(args.dry_run), files=args.file or None)
# @used-by :func:`_register_analysis_builtins()`
def _format_perf_profile_tests(res: dict, args) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from .perf.suite_profiler import format_profile_text
		r = format_profile_text(res)
	return r
# @used-by :func:`_register_analysis_builtins()`
def _format_perf_timesheet(res: dict, args) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from .perf.timesheet import format_timesheet_text
		r = format_timesheet_text(res)
	return r
# @used-by :func:`_register_analysis_builtins()`
def _format_problem_metadata(res: dict, args) -> str | None:
	return res['markdown'] if 'markdown' == args.format else None
# @used-by :func:`_register_analysis_builtins()`
def _format_rules_audit(res: dict, args) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from .rules_audit import format_rules_audit_text
		r = format_rules_audit_text(res)
	return r
# @used-by :func:`_register_analysis_builtins()`
def _format_run_tests(res: dict, args) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from .suite_runner import format_text_report
		r = format_text_report(res)
	return r
# @used-by :func:`_register_runtime_builtins()`
def _format_schema_help(res: dict, args) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from .schema_help import format_schema_help_text
		r = format_schema_help_text(res)
	return r
# @used-by :func:`_register_runtime_builtins()`
def _format_test_watchdog(_res: dict, args) -> str | None:
	return None if 'json' == args.format else ''
# 2026-11-26
# "Implement Python AST cross-reference analyzer and sync CLI":
# https://github.com/dmitry-ai/harness/issues/287
# @used-by :func:`_register_runtime_builtins()`
def _format_xref(res: dict, args) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from .xref import format_xref_text
		r = format_xref_text(res)
	return r
# @used-by :func:`_register_builtins()`
def _register_analysis_builtins() -> None:
	register_command('analysis-check', 'Validate multi-hypothesis /df-analysis structure and Markdown table ban', (('project', {'type': Path}), ('--response-file', {'type': Path, 'required': True, 'help': 'UTF-8 candidate Markdown file, or - for stdin'}), ('--mode', {'choices': ('auto', 'general', 'problem'), 'default': 'auto', 'help': 'Validation mode (default: auto)'})), _exec_analysis_check, exit_code_fn=lambda res: 0 if res.get('valid') else 2)
	register_command('cli-docs', 'Render Markdown command index directly from registered CLI commands', (), _exec_cli_docs)
	register_command('land-acquire', 'Acquire FIFO landing lease for a Git repository', (('repo', {'type': Path}), ('--owner', {'help': 'Lease owner identifier'}), ('--wait', {'action': 'store_true', 'help': 'Wait reactively in FIFO queue until acquired'}), ('--timeout', {'type': float, 'default': 600.0}), ('--ttl', {'type': float, 'default': 600.0}), ('--poll-interval', {'type': float, 'default': 2.0})), _exec_land_acquire)
	register_command('land-release', 'Release FIFO landing lease for a Git repository', (('repo', {'type': Path}), ('--owner', {'help': 'Lease owner identifier'}), ('--force', {'action': 'store_true'})), _exec_land_release)
	register_command('land-status', 'Inspect FIFO landing lease and queue for a Git repository', (('repo', {'type': Path}),), _exec_land_status)
	register_command('perf-profile-tests', 'Profile unittest modules in parallel with Popen, sleep, and optional cProfile telemetry', (('target', {'nargs': '?', 'type': Path, 'help': 'Optional tests directory or repo root'}), ('--workers', {'type': int, 'help': 'Worker process count (default: half logical CPUs, 2..6)'}), ('--module-timeout', {'type': float, 'default': 300.0, 'help': 'Per-module timeout in seconds (default: 300)'}), (('-p', '--pattern'), {'default': 'test_*.py', 'help': 'Test filename glob pattern (default: test_*.py)'}), ('--module', {'action': 'append', 'default': [], 'help': 'Optional specific test module filter; repeatable'}), ('--cprofile', {'action': 'store_true', 'help': 'Collect and aggregate cProfile hotspot functions across workers'}), ('--top', {'type': int, 'default': 15, 'help': 'Number of slowest files and tests to rank (default: 15)'}), ('--cprofile-top', {'type': int, 'default': 25, 'help': 'Number of cProfile hotspots to retain (default: 25)'}), ('--output', {'type': Path, 'help': 'Optional output path to persist tab-indented JSON profile'}), ('--format', {'choices': ('json', 'text'), 'default': 'json', 'help': 'Output format (default: json)'})), _exec_perf_profile_tests, exit_code_fn=lambda res: 0 if res.get('valid') else 1, text_fn=_format_perf_profile_tests)
	register_command('perf-timesheet', 'Build deterministic turn chronometry, cache, compaction, and wait telemetry from a trace', (('--trace', {'type': Path, 'help': 'Direct path to Antigravity transcript_full.jsonl or Codex rollout .jsonl'}), ('--conversation', {'help': 'Native conversation UUID (auto-resolved via runtime.json)'}), ('--project', {'type': Path, 'help': 'Project root for --journal-step lookup'}), ('--journal-step', {'type': int, 'help': 'Journal response step number whose Trace metadata identifies the trace'}), ('--summary-db', {'type': Path, 'help': 'Optional path to Antigravity conversation_summaries.db'}), ('--turn-start-step', {'type': int, 'help': 'Optional inclusive starting step index'}), ('--turn-end-step', {'type': int, 'help': 'Optional inclusive ending step index'}), ('--top-gaps', {'type': int, 'default': 10, 'help': 'Number of largest inter-step wall gaps to report (default: 10)'}), ('--output', {'type': Path, 'help': 'Optional output path to persist tab-indented JSON telemetry'}), ('--format', {'choices': ('json', 'text'), 'default': 'json', 'help': 'Output format (default: json)'})), _exec_perf_timesheet, text_fn=_format_perf_timesheet)
	register_command('problem-metadata', 'Build structured # 0 problem metadata with mandatory GitHub Issue key', (('project', {'type': Path}), ('--issue', {'help': 'Verified GitHub issue URL (mandatory unless --no-issue)'}), ('--no-issue', {'action': 'store_true', 'help': 'Allow null Issue key for non-GitHub workspaces'}), ('--source-project', {'type': Path, 'help': 'Optional distinct owning project root'}), ('--format', {'choices': ('json', 'markdown'), 'default': 'json', 'help': 'Output format (default: json)'})), _exec_problem_metadata, text_fn=_format_problem_metadata)
	# 2026-11-26 "Add transactional rename-project command with automatic domain promotion": https://github.com/dmitry-ai/harness/issues/267
	# 2026-11-26 "Auto-detect launcher root and enforce post-rename invariant verification with rollback": https://github.com/dmitry-ai/harness/issues/288
	register_command('rename-project', 'Transactionally rename an Upwork project directory and synchronize indexes, registrations, and journal state', (('project', {'type': Path}), ('--domain', {'help': 'Verified target domain hostname without scheme or www.'}), ('--topic', {'help': 'Human-readable provisional topic title'}), ('--daily-root', {'type': Path, 'help': 'Optional explicit daily proposals root'}), ('--no-register', {'action': 'store_true', 'help': 'Skip native Antigravity/Codex registration sync (testing only)'}), ('--launcher-root', {'type': Path, 'help': 'Optional launcher workspace root whose handed-off turns should be rewritten'})), _exec_rename_project, exit_code_fn=lambda res: 0 if res.get('valid') else 2)
	# 2026-11-26 "Implement daily-counter Git tag engine and repo-tag CLI commands": https://github.com/dmitry-ai/harness/issues/262
	register_command('repo-tag', 'Allocate or reuse a daily-counter Git tag on a commit and optionally build a verified GitHub blob URL', (('repo', {'type': Path}), ('--commit', {'default': 'HEAD', 'help': 'Commit-ish to tag (default: HEAD)'}), ('--date', {'help': 'Optional YYYY-MM-DD override'}), ('--push', {'action': 'store_true', 'help': 'Push created/existing tag to origin'}), ('--file', {'help': 'Optional repository-relative file path to build a verified GitHub URL'}), ('--lines', {'help': 'Optional line range anchor such as L19-L23'}), ('--anchor', {'help': 'Optional heading anchor for Markdown files'})), _exec_repo_tag)
	register_command('repo-tag-retro', 'Preview or apply chronological daily-counter Git tags across historical issue-closing commits', (('repo', {'type': Path}), ('--apply', {'action': 'store_true', 'help': 'Create planned lightweight tags locally'}), ('--push', {'action': 'store_true', 'help': 'Push tags to origin after applying'}), ('--include-task-groups', {'action': 'store_true', 'help': 'Also tag final commits of reconstructed non-issue task groups'}), ('--extra-commit', {'action': 'append', 'default': [], 'help': 'Additional commit SHA to tag; repeatable'})), _exec_repo_tag_retro)
	register_command('rules-audit', 'Run deterministic offline rules configuration smell audit and optional neutral A.A semantic brief', (('--primary', {'type': Path, 'help': 'Optional Harness code repository path (default: PRIMARY)'}), ('--workspace', {'type': Path, 'help': 'Optional workspace root to inspect auto-loaded AGENTS.md/GEMINI.md'}), ('--semantic-brief', {'action': 'store_true', 'help': 'Generate a neutral read-only A.A semantic audit brief'}), ('--format', {'choices': ('json', 'text'), 'default': 'json', 'help': 'Output format (default: json)'})), _exec_rules_audit, exit_code_fn=lambda res: 0 if res.get('valid') else 2, text_fn=_format_rules_audit)
	# 2026-11-26 "Add host test-worker semaphore and worksteal pytest mode": https://github.com/dmitry-ai/harness/issues/354
	register_command('run-tests', 'Run unittest modules in parallel with fail-fast and per-module watchdog timeout', (('target', {'nargs': '?', 'type': Path, 'help': 'Optional tests directory or repo root'}), ('--workers', {'type': int, 'help': 'Worker process count (default: half logical CPUs, 2..8)'}), ('--module-timeout', {'type': float, 'default': 300.0, 'help': 'Per-module timeout in seconds (default: 300)'}), ('--no-failfast', {'action': 'store_true', 'help': 'Run all modules instead of stopping on first failure'}), (('-p', '--pattern'), {'default': 'test_*.py', 'help': 'Test filename glob pattern (default: test_*.py)'}), ('--module', {'action': 'append', 'default': [], 'help': 'Optional specific test module filter; repeatable'}), ('--runner', {'choices': ('auto', 'unittest', 'pytest'), 'default': 'auto', 'help': 'Test runner backend (default: auto)'}), ('--format', {'choices': ('text', 'json'), 'default': 'text', 'help': 'Output format (default: text)'})), _exec_run_tests, exit_code_fn=lambda res: int(res['exit_code']), text_fn=_format_run_tests)
	register_command('runtime-promote', 'Export, validate, and atomically activate an immutable HEAD runtime snapshot with LKG fallback', (('--primary', {'type': Path, 'help': 'Optional Harness code repository path (default: PRIMARY)'}), ('--store-dir', {'type': Path, 'help': 'Optional runtime snapshot store directory'}), ('--keep', {'type': int, 'default': 5, 'help': 'Number of recent releases to retain (default: 5)'})), _exec_runtime_promote)
# 2026-11-26 "Add arch-auditor subagent role and content-addressed review CLI": https://github.com/dmitry-ai/harness/issues/361
# @used-by :func:`_ensure_builtin_plugins()`
def _register_builtins() -> None:
	from .arch.review_cli import register_arch_commands
	_register_analysis_builtins()
	_register_runtime_builtins()
	register_arch_commands(register_command)
# @used-by :func:`_register_builtins()`
def _register_runtime_builtins() -> None:
	register_command('runtime-status', 'Inspect active and LKG immutable runtime snapshots', (('--primary', {'type': Path, 'help': 'Optional Harness code repository path (default: PRIMARY)'}), ('--store-dir', {'type': Path, 'help': 'Optional runtime snapshot store directory'})), _exec_runtime_status)
	register_command('schema-help', 'Print compact JSON or text contract, enums, and minimal example for analysis, experiment, or review schemas', (('topic', {'choices': ('analysis', 'experiment', 'review'), 'help': 'Schema topic'}), ('--format', {'choices': ('json', 'text'), 'default': 'json', 'help': 'Output format (default: json)'})), _exec_schema_help, exit_code_fn=lambda res: 0 if res.get('valid') else 1, text_fn=_format_schema_help)
	# 2026-11-26 "Add mutating command execution mode to shadow-replay with isolated native profiles": https://github.com/dmitry-ai/harness/issues/289
	register_command('shadow-replay', 'Replay remaining downstream /upwork-init CLI and hook stages or candidate mutating commands on a workspace-local shadow copy without mutating live files', (('project', {'type': Path, 'help': 'Source project directory to clone and replay'}), ('--conversation', {'help': 'Native conversation UUID to replay (optional with --exec-rename-domain or --command)'}), ('--launcher', {'type': Path, 'help': 'Optional launcher project directory to clone for PreInvocation and Stop Gate handoff checks'}), ('--workspace', {'type': Path, 'help': 'Optional workspace root hosting ꘖ/data/scratch/shadow-replay (defaults to project)'}), ('--backend', {'type': Path, 'help': 'Optional explicit native backend directory override'}), ('--response-file', {'type': Path, 'help': 'Optional candidate response file overriding prepared journal reply'}), ('--exec-rename-domain', {'help': 'Execute rename-project --domain <host> inside the shadow copy with isolated native profiles and post-invariant verification'}), ('--command', {'dest': 'command_spec', 'help': 'Execute a candidate Harness CLI command inside the shadow copy with post-invariant verification'}), ('--keep', {'action': 'store_true', 'help': 'Retain workspace-local shadow copy after replay instead of cleaning it up'})), _exec_shadow_replay, exit_code_fn=lambda res: 0 if res.get('valid') else 2)
	register_command('tdd-exempt-mechanical', 'Record an audited turn-scoped mechanical replacement recipe bound to an open GitHub Issue', (('project', {'type': Path}), ('--repo', {'help': 'Optional target repository path or GitHub owner/repo slug (defaults to --issue repo)'}), ('--issue', {'required': True, 'help': 'Open GitHub Issue URL governing this mechanical replacement'}), ('--pattern', {'required': True, 'help': 'Exact literal pattern (or regex with --regex) being replaced'}), ('--replacement', {'required': True, 'help': 'Exact replacement string'}), ('--reason', {'required': True, 'help': 'Audited justification (>= 30 chars) explaining the mechanical replacement scope'}), ('--regex', {'action': 'store_true', 'help': 'Interpret --pattern as a regular expression'}), ('--ignore-case', {'action': 'store_true', 'help': 'Match --pattern case-insensitively'}), ('--conversation', {'help': 'Actual current native conversation UUID; Codex can use CODEX_THREAD_ID'}), ('--turn-key', {'help': 'Optional explicit turn key override'})), _exec_tdd_exempt_mechanical)
	register_command('test-watchdog', 'Run a test command with stdin detached and a hard process-tree watchdog timeout', ((('--timeout', '--module-timeout'), {'dest': 'timeout', 'type': float, 'default': 300.0, 'help': 'Watchdog timeout in seconds (default: 300)'}), ('--cwd', {'type': Path, 'help': 'Optional working directory'}), ('--format', {'choices': ('passthrough', 'json'), 'default': 'passthrough', 'help': 'Output format (default: passthrough)'}), ('cmd', {'nargs': argparse.REMAINDER, 'help': 'Command and arguments to execute under watchdog'})), _exec_test_watchdog, exit_code_fn=lambda res: int(res['exit_code']), text_fn=_format_test_watchdog)
	register_command('wait-repo', 'Wait reactively in foreground until a Git repository lease is free and/or working tree is clean', (('repo', {'type': Path}), ('--clean', {'action': 'store_true', 'help': 'Wait until git status --porcelain is empty'}), ('--lease-free', {'action': 'store_true', 'help': 'Wait until FIFO landing lease is free (with PID liveness checks)'}), ('--timeout', {'type': float, 'default': 180.0, 'help': 'Maximum wait seconds before timing out (default: 180)'}), ('--poll', {'type': float, 'default': 1.0, 'help': 'Polling interval in seconds (default: 1.0)'})), _exec_wait_repo)
	register_command('worktree-begin', 'Create an isolated linked git worktree and task branch', (('repo', {'type': Path}), ('--task', {'required': True}), ('--base', {'default': 'main'}), ('--worktrees-dir', {'type': Path})), _exec_worktree_begin)
	register_command('worktree-cleanup', 'Remove a linked git worktree and its merged task branch', (('repo', {'type': Path}), ('target', {'type': Path}), ('--force', {'action': 'store_true'})), _exec_worktree_cleanup)
	# 2026-11-26 "Enforce pushed Git tags on issue-closing commits in lifecycle gates": https://github.com/dmitry-ai/harness/issues/263
	# 2026-11-26 "Implement diff executability classifier and automatic test skip": https://github.com/dmitry-ai/harness/issues/358
	register_command('worktree-land', 'Rebase, test once, fast-forward merge, and remove (unless --keep) a task worktree under FIFO lease', (('worktree', {'type': Path}), ('--target', {'default': 'main'}), ('--no-tests', {'action': 'store_true'}), ('--no-tests-reason', {'help': 'Audited justification (>= 30 chars) required when passing --no-tests on an executable diff'}), ('--push', {'action': 'store_true'}), ('--tag', {'action': 'store_true', 'help': 'Assign a daily-counter Git tag on the landed commit and push it when --push is set'}), ('--keep', {'action': 'store_true', 'help': 'Keep the linked worktree and task branch after landing'}), ('--remove', {'action': 'store_true', 'help': 'Remove the linked worktree after landing (default)'}), ('--owner', {}), ('--timeout', {'type': float, 'default': 600.0}), ('--workers', {'type': int})), _exec_worktree_land)
	register_command('worktree-status', 'List linked git worktrees and dirty status for a repository', (('repo', {'type': Path}),), _exec_worktree_status)
	# 2026-11-26
	# "Implement Python AST cross-reference analyzer and sync CLI":
	# https://github.com/dmitry-ai/harness/issues/287
	register_command('xref-check', 'Validate navigable cross-reference annotations (@used-by, @uses, @see, @override)', (('repo', {'type': Path}), ('--lang', {'choices': ('all', 'python', 'js', 'java'), 'default': 'all'}), ('--file', {'action': 'append', 'default': []}), ('--format', {'choices': ('json', 'text'), 'default': 'json'})), _exec_xref_check, exit_code_fn=lambda res: 0 if res.get('valid') else 2, text_fn=_format_xref)
	register_command('xref-sync', 'Synchronize navigable @used-by and @override/@see cross-reference annotations', (('repo', {'type': Path}), ('--lang', {'choices': ('all', 'python', 'js', 'java'), 'default': 'all'}), ('--dry-run', {'action': 'store_true'}), ('--file', {'action': 'append', 'default': []}), ('--format', {'choices': ('json', 'text'), 'default': 'json'})), _exec_xref_sync, text_fn=_format_xref)
# @used-by :func:`agent_tools.upwork_project.main()`
# @used-by :func:`test_arch_review_cli._run_arch_cli()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_cli_parser_dispatches_tdd_exempt_mechanical_with_turn_key()`
def add_registered_parsers(sub) -> None:
	_ensure_builtin_plugins()
	for name, entry in sorted(_REGISTRY.items()):
		add_arg_specs(sub.add_parser(name, help=entry['help']), entry['specs'])
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :func:`test_arch_review_cli._run_arch_cli()`
def dispatch_registered(args, dump_fn: Callable, exit_fn: Callable) -> tuple[bool, int | None]:
	_ensure_builtin_plugins()
	entry = _REGISTRY.get(args.command)
	if None is entry:
		r = (False, None)
	else:
		res = entry['handler'](args)
		txt_fn = entry.get('text_fn')
		txt = txt_fn(res, args) if txt_fn else None
		if None is txt:
			dump_fn(res)
		else:
			sys.stdout.write(txt)
		ec_fn = entry.get('exit_code_fn')
		r = (True, int(ec_fn(res)) if ec_fn else exit_fn(res))
	return r
# @used-by :meth:`test_cli_registry.CliRegistryTests.test_dynamic_command_registration_roundtrip()`
# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_schema_help_command_returns_contract_for_all_topics()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_cli_parser_dispatches_tdd_exempt_mechanical_with_turn_key()`
def execute_registered(args) -> tuple[bool, dict | None, int | None]:
	_ensure_builtin_plugins()
	entry = _REGISTRY.get(args.command)
	if None is entry:
		r = (False, None, None)
	else:
		res = entry['handler'](args)
		ec_fn = entry.get('exit_code_fn')
		r = (True, res, int(ec_fn(res)) if ec_fn else None)
	return r
# @used-by :func:`_exec_cli_docs()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_cli_registry_and_send_message_gate_expose_arch_commands_and_block_verdict_duplication()`
# @used-by :meth:`test_repo_tags.RepoTagsTests.test_cli_repo_tag_and_repo_tag_retro_registered()`
# @used-by :meth:`test_repo_wait_and_retry.RepoWaitAndRetryTests.test_wait_repo_cli_and_registry_expose_wait_repo()`
# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_schema_help_command_returns_contract_for_all_topics()`
# @used-by :meth:`test_shadow_replay_m3.ShadowReplayM3Tests.test_exec2_rules_and_readme_document_shadow_replay_gate()`
# @used-by :meth:`test_tdd_mechanical_exemption.MechanicalExemptionTests.test_cli_registration_and_validation_errors()`
def registered_commands() -> tuple[str, ...]:
	_ensure_builtin_plugins()
	return tuple(sorted(_REGISTRY))
# @used-by :func:`_register_analysis_builtins()`
# @used-by :func:`_register_builtins()`
# @used-by :func:`_register_runtime_builtins()`
# @used-by :meth:`test_cli_registry.CliRegistryTests.test_dynamic_command_registration_roundtrip()`
def register_command(name: str, help_text: str, specs: tuple | list, handler: Callable, *, exit_code_fn: Callable | None=None, text_fn: Callable | None=None) -> None:
	_REGISTRY[name] = {'help': help_text, 'specs': specs, 'handler': handler, 'exit_code_fn': exit_code_fn, 'text_fn': text_fn}
# @used-by :func:`_exec_cli_docs()`
# @used-by :meth:`test_cli_registry.CliRegistryTests.test_cli_docs_renders_registered_commands_and_runs_via_cli()`
def render_cli_index() -> str:
	_ensure_builtin_plugins()
	lines = ['# Registered CLI Commands', '']
	for name, entry in sorted(_REGISTRY.items()):
		lines.append(f"- `{name}` — {entry['help']}.  ")
	return '\n'.join(lines) + '\n'
