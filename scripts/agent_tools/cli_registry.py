# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add deterministic reactive wait primitive for transient repository and journal contention":
# https://github.com/dmitry-ai/harness/issues/199
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add harness perf-profile-tests CLI for test suite and subprocess profiling":
# https://github.com/dmitry-ai/harness/issues/192
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add harness perf-timesheet CLI for deterministic turn chronometry":
# https://github.com/dmitry-ai/harness/issues/191
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce Markdown table ban and /df-analysis structural validation across response gates":
# https://github.com/dmitry-ai/harness/issues/181
# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add structured problem metadata builder and CLI command":
# https://github.com/dmitry-ai/harness/issues/180
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Replace monolithic CLI router with declarative registry and modular docs":
# https://github.com/dmitry-ai/harness/issues/168
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add isolated git worktree task workflow and worktree-scoped issue gates":
# https://github.com/dmitry-ai/harness/issues/165
# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add deterministic FIFO repository landing lease with reactive wait":
# https://github.com/dmitry-ai/harness/issues/163
from __future__ import annotations
from pathlib import Path
from typing import Callable
import sys
from .cli_common import add_arg_specs
_REGISTRY: dict[str, dict] = {}
def _ensure_builtin_plugins() -> None:
	if not _REGISTRY:
		_register_builtins()
def _exec_analysis_check(args) -> dict:
	from .cli_common import load_operation_input
	from .statements import markdown_table_issues, validate_df_analysis
	text = load_operation_input(args, args.response_file).decode('utf-8')
	issues = [*markdown_table_issues(text), *validate_df_analysis(text, mode=args.mode)]
	return {'valid': not issues, 'mode': args.mode, 'issue_count': len(issues), 'issues': issues}
def _exec_cli_docs(_args) -> dict:
	return {'valid': True, 'commands': list(registered_commands()), 'markdown': render_cli_index()}
def _exec_land_acquire(args) -> dict:
	from .landing_lease import acquire_lease
	return acquire_lease(args.repo, owner=args.owner, wait=bool(args.wait), timeout=args.timeout, ttl=args.ttl, poll_interval=args.poll_interval)
def _exec_land_release(args) -> dict:
	from .landing_lease import release_lease
	return release_lease(args.repo, owner=args.owner, force=bool(args.force))
def _exec_land_status(args) -> dict:
	from .landing_lease import lease_status
	return lease_status(args.repo)
def _exec_perf_profile_tests(args) -> dict:
	from .perf.suite_profiler import run_perf_profile_cli
	return run_perf_profile_cli(args)
def _exec_perf_timesheet(args) -> dict:
	from .perf.timesheet import run_perf_timesheet_cli
	return run_perf_timesheet_cli(args)
def _exec_problem_metadata(args) -> dict:
	from .metadata import build_problem_metadata, render_metadata_header
	meta = build_problem_metadata(issue_url=args.issue, project_root=args.project, source_project_root=args.source_project, allow_no_issue=bool(args.no_issue))
	return {'valid': True, 'metadata': meta, 'markdown': render_metadata_header(meta).rstrip('\n') + '\n'}
def _exec_run_tests(args) -> dict:
	from .suite_runner import run_test_suite
	return run_test_suite(args.target, workers=args.workers, module_timeout=args.module_timeout, failfast=not args.no_failfast, pattern=args.pattern, modules=args.module)
def _exec_wait_repo(args) -> dict:
	from .repo_wait import wait_for_repo
	return wait_for_repo(args.repo, clean=bool(args.clean), lease_free=bool(args.lease_free), timeout=args.timeout, poll_interval=args.poll)
def _exec_worktree_begin(args) -> dict:
	from .worktree_flow import worktree_begin
	return worktree_begin(args.repo, args.task, base_ref=args.base, worktrees_dir=args.worktrees_dir)
def _exec_worktree_cleanup(args) -> dict:
	from .worktree_flow import worktree_cleanup
	return worktree_cleanup(args.repo, args.target, force=bool(args.force))
def _exec_worktree_land(args) -> dict:
	from .worktree_flow import worktree_land
	return worktree_land(args.worktree, target_branch=args.target, run_tests=not args.no_tests, push=bool(args.push), remove=bool(args.remove), owner=args.owner, wait_timeout=args.timeout, workers=args.workers)
def _exec_worktree_status(args) -> dict:
	from .worktree_flow import worktree_status
	return worktree_status(args.repo)
def _format_perf_profile_tests(res: dict, args) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from .perf.suite_profiler import format_profile_text
		r = format_profile_text(res)
	return r
def _format_perf_timesheet(res: dict, args) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from .perf.timesheet import format_timesheet_text
		r = format_timesheet_text(res)
	return r
def _format_problem_metadata(res: dict, args) -> str | None:
	return res['markdown'] if 'markdown' == args.format else None
def _format_run_tests(res: dict, args) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from .suite_runner import format_text_report
		r = format_text_report(res)
	return r
def _register_builtins() -> None:
	register_command('analysis-check', 'Validate multi-hypothesis /df-analysis structure and Markdown table ban', (('project', {'type': Path}), ('--response-file', {'type': Path, 'required': True, 'help': 'UTF-8 candidate Markdown file, or - for stdin'}), ('--mode', {'choices': ('auto', 'general', 'problem'), 'default': 'auto', 'help': 'Validation mode (default: auto)'})), _exec_analysis_check, exit_code_fn=lambda res: 0 if res.get('valid') else 2)
	register_command('cli-docs', 'Render Markdown command index directly from registered CLI commands', (), _exec_cli_docs)
	register_command('land-acquire', 'Acquire FIFO landing lease for a Git repository', (('repo', {'type': Path}), ('--owner', {'help': 'Lease owner identifier'}), ('--wait', {'action': 'store_true', 'help': 'Wait reactively in FIFO queue until acquired'}), ('--timeout', {'type': float, 'default': 600.0}), ('--ttl', {'type': float, 'default': 600.0}), ('--poll-interval', {'type': float, 'default': 2.0})), _exec_land_acquire)
	register_command('land-release', 'Release FIFO landing lease for a Git repository', (('repo', {'type': Path}), ('--owner', {'help': 'Lease owner identifier'}), ('--force', {'action': 'store_true'})), _exec_land_release)
	register_command('land-status', 'Inspect FIFO landing lease and queue for a Git repository', (('repo', {'type': Path}),), _exec_land_status)
	register_command('perf-profile-tests', 'Profile unittest modules in parallel with Popen, sleep, and optional cProfile telemetry', (('target', {'nargs': '?', 'type': Path, 'help': 'Optional tests directory or repo root'}), ('--workers', {'type': int, 'help': 'Worker process count (default: half logical CPUs, 2..6)'}), ('--module-timeout', {'type': float, 'default': 300.0, 'help': 'Per-module timeout in seconds (default: 300)'}), (('-p', '--pattern'), {'default': 'test_*.py', 'help': 'Test filename glob pattern (default: test_*.py)'}), ('--module', {'action': 'append', 'default': [], 'help': 'Optional specific test module filter; repeatable'}), ('--cprofile', {'action': 'store_true', 'help': 'Collect and aggregate cProfile hotspot functions across workers'}), ('--top', {'type': int, 'default': 15, 'help': 'Number of slowest files and tests to rank (default: 15)'}), ('--cprofile-top', {'type': int, 'default': 25, 'help': 'Number of cProfile hotspots to retain (default: 25)'}), ('--output', {'type': Path, 'help': 'Optional output path to persist tab-indented JSON profile'}), ('--format', {'choices': ('json', 'text'), 'default': 'json', 'help': 'Output format (default: json)'})), _exec_perf_profile_tests, exit_code_fn=lambda res: 0 if res.get('valid') else 1, text_fn=_format_perf_profile_tests)
	register_command('perf-timesheet', 'Build deterministic turn chronometry, cache, compaction, and wait telemetry from a trace', (('--trace', {'type': Path, 'help': 'Direct path to Antigravity transcript_full.jsonl or Codex rollout .jsonl'}), ('--conversation', {'help': 'Native conversation UUID (auto-resolved via runtime.json)'}), ('--project', {'type': Path, 'help': 'Project root for --journal-step lookup'}), ('--journal-step', {'type': int, 'help': 'Journal response step number whose Trace metadata identifies the trace'}), ('--summary-db', {'type': Path, 'help': 'Optional path to Antigravity conversation_summaries.db'}), ('--turn-start-step', {'type': int, 'help': 'Optional inclusive starting step index'}), ('--turn-end-step', {'type': int, 'help': 'Optional inclusive ending step index'}), ('--top-gaps', {'type': int, 'default': 10, 'help': 'Number of largest inter-step wall gaps to report (default: 10)'}), ('--output', {'type': Path, 'help': 'Optional output path to persist tab-indented JSON telemetry'}), ('--format', {'choices': ('json', 'text'), 'default': 'json', 'help': 'Output format (default: json)'})), _exec_perf_timesheet, text_fn=_format_perf_timesheet)
	register_command('problem-metadata', 'Build structured # 0 problem metadata with mandatory GitHub Issue key', (('project', {'type': Path}), ('--issue', {'help': 'Verified GitHub issue URL (mandatory unless --no-issue)'}), ('--no-issue', {'action': 'store_true', 'help': 'Allow null Issue key for non-GitHub workspaces'}), ('--source-project', {'type': Path, 'help': 'Optional distinct owning project root'}), ('--format', {'choices': ('json', 'markdown'), 'default': 'json', 'help': 'Output format (default: json)'})), _exec_problem_metadata, text_fn=_format_problem_metadata)
	register_command('run-tests', 'Run unittest modules in parallel with fail-fast and per-module watchdog timeout', (('target', {'nargs': '?', 'type': Path, 'help': 'Optional tests directory or repo root'}), ('--workers', {'type': int, 'help': 'Worker process count (default: half logical CPUs, 2..8)'}), ('--module-timeout', {'type': float, 'default': 300.0, 'help': 'Per-module timeout in seconds (default: 300)'}), ('--no-failfast', {'action': 'store_true', 'help': 'Run all modules instead of stopping on first failure'}), (('-p', '--pattern'), {'default': 'test_*.py', 'help': 'Test filename glob pattern (default: test_*.py)'}), ('--module', {'action': 'append', 'default': [], 'help': 'Optional specific test module filter; repeatable'}), ('--format', {'choices': ('text', 'json'), 'default': 'text', 'help': 'Output format (default: text)'})), _exec_run_tests, exit_code_fn=lambda res: int(res['exit_code']), text_fn=_format_run_tests)
	register_command('wait-repo', 'Wait reactively in foreground until a Git repository lease is free and/or working tree is clean', (('repo', {'type': Path}), ('--clean', {'action': 'store_true', 'help': 'Wait until git status --porcelain is empty'}), ('--lease-free', {'action': 'store_true', 'help': 'Wait until FIFO landing lease is free (with PID liveness checks)'}), ('--timeout', {'type': float, 'default': 180.0, 'help': 'Maximum wait seconds before timing out (default: 180)'}), ('--poll', {'type': float, 'default': 1.0, 'help': 'Polling interval in seconds (default: 1.0)'})), _exec_wait_repo)
	register_command('worktree-begin', 'Create an isolated linked git worktree and task branch', (('repo', {'type': Path}), ('--task', {'required': True}), ('--base', {'default': 'main'}), ('--worktrees-dir', {'type': Path})), _exec_worktree_begin)
	register_command('worktree-cleanup', 'Remove a linked git worktree and its merged task branch', (('repo', {'type': Path}), ('target', {'type': Path}), ('--force', {'action': 'store_true'})), _exec_worktree_cleanup)
	register_command('worktree-land', 'Rebase, test once, fast-forward merge, and optionally push a task worktree under FIFO lease', (('worktree', {'type': Path}), ('--target', {'default': 'main'}), ('--no-tests', {'action': 'store_true'}), ('--push', {'action': 'store_true'}), ('--remove', {'action': 'store_true'}), ('--owner', {}), ('--timeout', {'type': float, 'default': 600.0}), ('--workers', {'type': int})), _exec_worktree_land)
	register_command('worktree-status', 'List linked git worktrees and dirty status for a repository', (('repo', {'type': Path}),), _exec_worktree_status)
def add_registered_parsers(sub) -> None:
	_ensure_builtin_plugins()
	for name, entry in sorted(_REGISTRY.items()):
		add_arg_specs(sub.add_parser(name, help=entry['help']), entry['specs'])
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
def registered_commands() -> tuple[str, ...]:
	_ensure_builtin_plugins()
	return tuple(sorted(_REGISTRY))
def register_command(name: str, help_text: str, specs: tuple | list, handler: Callable, *, exit_code_fn: Callable | None=None, text_fn: Callable | None=None) -> None:
	_REGISTRY[name] = {'help': help_text, 'specs': specs, 'handler': handler, 'exit_code_fn': exit_code_fn, 'text_fn': text_fn}
def render_cli_index() -> str:
	_ensure_builtin_plugins()
	lines = ['# Registered CLI Commands', '']
	for name, entry in sorted(_REGISTRY.items()):
		lines.append(f"- `{name}` — {entry['help']}.  ")
	return '\n'.join(lines) + '\n'
