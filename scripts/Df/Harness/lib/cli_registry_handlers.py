# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.Runtime.SnapshotPromoter import SnapshotPromoter
from Df.Harness.Shadow.ReplayRunner import ReplayRunner
from Df.Harness.lib.cli_input import dfh_load_operation_input
from Df.Harness.lib.path_resolve import dfh_var_value
from Df.Harness.lib.runtime_snapshot_ops import dfh_check_runtime_snapshot
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_analysis_check(args: Any) -> dict:
	from agent_tools.statements import markdown_table_issues, validate_df_analysis
	text = dfh_load_operation_input(args, args.response_file).decode('utf-8')
	issues = [*markdown_table_issues(text), *validate_df_analysis(text, mode=args.mode)]
	return {'valid': not issues, 'mode': args.mode, 'issue_count': len(issues), 'issues': issues}
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_land_acquire(args: Any) -> dict:
	from agent_tools.landing_lease import acquire_lease
	return acquire_lease(args.repo, owner=args.owner, wait=bool(args.wait), timeout=args.timeout, ttl=args.ttl, poll_interval=args.poll_interval)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_land_release(args: Any) -> dict:
	from agent_tools.landing_lease import release_lease
	return release_lease(args.repo, owner=args.owner, force=bool(args.force))
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_land_status(args: Any) -> dict:
	from agent_tools.landing_lease import lease_status
	return lease_status(args.repo)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_perf_profile_tests(args: Any) -> dict:
	from agent_tools.perf.suite_profiler import run_perf_profile_cli
	return run_perf_profile_cli(args)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_perf_timesheet(args: Any) -> dict:
	from agent_tools.perf.timesheet import run_perf_timesheet_cli
	return run_perf_timesheet_cli(args)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_problem_metadata(args: Any) -> dict:
	from agent_tools.metadata import build_problem_metadata, render_metadata_header
	meta = build_problem_metadata(issue_url=args.issue, project_root=args.project, source_project_root=args.source_project, allow_no_issue=bool(args.no_issue))
	return {'valid': True, 'metadata': meta, 'markdown': render_metadata_header(meta).rstrip('\n') + '\n'}
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_rename_project(args: Any) -> dict:
	from agent_tools.project_rename import rename_project
	return rename_project(args.project, domain=args.domain, topic=args.topic, daily_root=args.daily_root, register_native=False if args.no_register else None, launcher_root=args.launcher_root)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_repo_tag(args: Any) -> dict:
	from agent_tools.repo_tags import run_repo_tag_cli
	return run_repo_tag_cli(args)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_repo_tag_retro(args: Any) -> dict:
	from agent_tools.repo_tags import retro_tag_repo
	return retro_tag_repo(args.repo, apply=bool(args.apply), push=bool(args.push), include_task_groups=bool(args.include_task_groups), extra_commits=list(args.extra_commit or ()))
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_rules_audit(args: Any) -> dict:
	from agent_tools.rules_audit import audit_rules, build_semantic_audit_brief
	from agent_tools.rules_manifest import resolve_rules_primary
	prim = resolve_rules_primary(args.primary, Path(dfh_var_value('HARNESS_CODE')).resolve())
	rep = audit_rules(prim, workspace=args.workspace)
	if args.semantic_brief:
		rep['semantic_brief'] = build_semantic_audit_brief(prim, workspace=args.workspace)
	return rep
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_run_tests(args: Any) -> dict:
	from agent_tools.suite_runner import run_test_suite
	return run_test_suite(args.target, workers=args.workers, module_timeout=args.module_timeout, failfast=not args.no_failfast, pattern=args.pattern, modules=args.module, runner=args.runner)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_exec_runtime_promote(args: Any) -> dict:
	primary = args.primary or Path(dfh_var_value('HARNESS_CODE')).resolve()
	return SnapshotPromoter(primary, store_dir=args.store_dir, keep=args.keep).run()
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_runtime_status(args: Any) -> dict:
	primary = args.primary or Path(dfh_var_value('HARNESS_CODE')).resolve()
	return dfh_check_runtime_snapshot(primary, store_dir=args.store_dir)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_schema_help(args: Any) -> dict:
	from agent_tools.schema_help import schema_help_payload
	return schema_help_payload(args.topic)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_shadow_replay(args: Any) -> dict:
	return ReplayRunner(args.project, args.conversation, launcher=args.launcher, workspace=args.workspace, platform=args.platform or 'antigravity', backend=args.backend, response_file=args.response_file, keep=bool(args.keep), exec_rename_domain=args.exec_rename_domain, command=args.command_spec).run()
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_tdd_exempt_mechanical(args: Any) -> dict:
	from agent_tools.tdd.mechanical import record_mechanical_exemption
	return record_mechanical_exemption(args.project, repo=args.repo, issue_url=args.issue, pattern=args.pattern, replacement=args.replacement, reason=args.reason, is_regex=bool(args.regex), ignore_case=bool(args.ignore_case), conversation=args.conversation, turn_key=args.turn_key)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_test_watchdog(args: Any) -> dict:
	from agent_tools.watchdog_runner import run_watchdog_cli
	return run_watchdog_cli(args)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_wait_repo(args: Any) -> dict:
	from agent_tools.repo_wait import wait_for_repo
	return wait_for_repo(args.repo, clean=bool(args.clean), lease_free=bool(args.lease_free), timeout=args.timeout, poll_interval=args.poll)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_worktree_begin(args: Any) -> dict:
	from agent_tools.worktree_flow import worktree_begin
	return worktree_begin(args.repo, args.task, base_ref=args.base, worktrees_dir=args.worktrees_dir)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_worktree_cleanup(args: Any) -> dict:
	from agent_tools.worktree_flow import worktree_cleanup
	return worktree_cleanup(args.repo, args.target, force=bool(args.force))
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_worktree_land(args: Any) -> dict:
	from agent_tools.worktree_flow import worktree_land
	if args.keep and args.remove:
		raise ValueError('Cannot combine --keep and --remove in worktree-land')
	return worktree_land(args.worktree, target_branch=args.target, run_tests=not args.no_tests, push=bool(args.push), remove=not bool(args.keep), owner=args.owner, wait_timeout=args.timeout, workers=args.workers, tag=bool(args.tag), no_tests_reason=args.no_tests_reason)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_worktree_status(args: Any) -> dict:
	from agent_tools.worktree_flow import worktree_status
	return worktree_status(args.repo)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_xref_check(args: Any) -> dict:
	from agent_tools.xref import run_xref_check
	return run_xref_check(args.repo, lang=args.lang, files=args.file or None)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_exec_xref_sync(args: Any) -> dict:
	from agent_tools.xref import run_xref_sync
	return run_xref_sync(args.repo, lang=args.lang, apply=not bool(args.dry_run), files=args.file or None)
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_format_perf_profile_tests(res: dict, args: Any) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from agent_tools.perf.suite_profiler import format_profile_text
		r = format_profile_text(res)
	return r
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_format_perf_timesheet(res: dict, args: Any) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from agent_tools.perf.timesheet import format_timesheet_text
		r = format_timesheet_text(res)
	return r
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_format_problem_metadata(res: dict, args: Any) -> str | None:
	return res['markdown'] if 'markdown' == args.format else None
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_format_rules_audit(res: dict, args: Any) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from agent_tools.rules_audit import format_rules_audit_text
		r = format_rules_audit_text(res)
	return r
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_analysis_builtins()`
def dfh_format_run_tests(res: dict, args: Any) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from agent_tools.suite_runner import format_text_report
		r = format_text_report(res)
	return r
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_format_schema_help(res: dict, args: Any) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from agent_tools.schema_help import format_schema_help_text
		r = format_schema_help_text(res)
	return r
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_format_test_watchdog(_res: dict, args: Any) -> str | None:
	return None if 'json' == args.format else ''
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_runtime_builtins()`
def dfh_format_xref(res: dict, args: Any) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from agent_tools.xref import format_xref_text
		r = format_xref_text(res)
	return r