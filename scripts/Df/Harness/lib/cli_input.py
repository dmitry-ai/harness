# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.path_resolve import dfh_project_paths
from Df.Harness.lib.storage import dfh_data_dir_for
import hashlib
import json
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
# @used-by :func:`dfh_load_operation_input()`
def _check_parallel_answer_md_guard(args: Any, path: Any) -> None:
	if 'answer-prepare' == getattr(args, 'command', None) and '-' != str(path) and 'answer.md' == Path(path).resolve().name.lower():
		turns_dir = dfh_data_dir_for(args.project) / 'turns'
		cur_conv = getattr(args, 'conversation', None)
		if turns_dir.is_dir():
			for tf in turns_dir.glob('*.json'):
				if '-' in tf.stem:
					continue
				try:
					tdata = json.loads(tf.read_text(encoding='utf-8'))
				except (OSError, ValueError):
					continue
				if isinstance(tdata, dict) and tdata.get('status') in ('open', 'prepared', 'preparation_unverified') and (None is cur_conv or tdata.get('conversation_id') != cur_conv):
					raise ValueError('Shared \ua616/data/scratch/answer.md is prohibited when parallel turns are active; write to \ua616/data/scratch/answer-<turn_key>.md')
# @used-by :func:`Df.Harness.lib.cli_operation_defs._add_single_operation_parser()`
# @used-by :func:`Df.Harness.lib.cli_registry_defs.dfh_add_registered_parsers()`
# @used-by :func:`Df.Harness.lib.completion_commands.dfh_add_completion_parser_arguments()`
# @used-by :func:`agent_tools.issues.batch_commands.register_issue_subparsers()`
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :func:`agent_tools.upwork_project.main()`
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__build_parser()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_declarative_arg_specs_and_routers_parse_expected_flags()`
def dfh_add_arg_specs(parser: Any, specs: tuple | list) -> None:
	for flags, kwargs in specs:
		names = flags if isinstance(flags, tuple) else (flags,)
		parser.add_argument(*names, **kwargs)
# @used-by :func:`Df.Harness.lib.cli_domain_ops._load_consumed()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_prepare_review()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_record_answer()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_record_review()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_execute_collect()`
# @used-by :func:`Df.Harness.lib.completion_commands._execute_prepare_or_check()`
# @used-by :func:`agent_tools.arch.review_cli._exec_arch_prepare()`
# @used-by :func:`agent_tools.arch.review_cli._exec_arch_record_review()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_scratch_consumption_sha256_and_parallel_answer_guard()`
# @used-by :meth:`test_publication_lifecycle.PublicationLifecycleTests.test_failed_or_changed_input_is_retained()`
def dfh_consume_scratch_input(args: Any, path: Any, payload: bytes, result: dict) -> dict:
	if not getattr(args, 'consume_input', False) or '-' == str(path):
		r = result
	else:
		target = dfh_verify_scratch_input_path(args.project, path)
		if 'conflict' == result.get('status') or False is result.get('complete') or False is result.get('valid'):
			r = result
		else:
			if target.exists() and target.read_bytes() == payload:
				target.unlink()
				result['consumed_input'] = str(target)
			r = result
	return r
# @used-by :func:`agent_tools.issues.batch_commands._run_batch_items()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._finalize_close()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._verify_mutation_readback()`
# @used-by :mod:`agent_tools.github_issue`
def dfh_consume_unchanged_files(files: list[tuple[Path, bytes]]) -> list[str]:
	r: list[str] = []
	for path, expected_bytes in files:
		if path.exists() and path.read_bytes() == expected_bytes:
			path.unlink()
			r.append(str(path))
	return r
# @used-by :func:`agent_tools.github_issue.main()`
# @used-by :func:`agent_tools.issues.batch_commands._run_batch_items()`
# @used-by :func:`agent_tools.issues.comment_grounding.check_comment_preflight()`
# @used-by :func:`agent_tools.issues.comment_grounding.emit_grounding_failure()`
# @used-by :func:`agent_tools.issues.comment_grounding.validate_close_comment()`
# @used-by :func:`agent_tools.issues.repo_commands.run_audit_repo()`
# @used-by :func:`agent_tools.issues.repo_commands.run_fetch()`
# @used-by :func:`agent_tools.issues.repo_commands.run_lint()`
# @used-by :func:`agent_tools.issues.repo_commands.run_transfer_repo()`
# @used-by :func:`agent_tools.text_cli.findings_output()`
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__run_validate_links()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._edit_parent_only()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._execute_edit()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._finalize_close()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._post_close_comment()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._verify_close_prereqs()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._verify_mutation_readback()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService.cmd_create()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService.run_verified_mutation()`
def dfh_dump_json(payload: Any, *, stream: Any=None) -> None:
	print(json.dumps(payload, ensure_ascii=False, indent=2), file=stream or sys.stdout)
# @used-by :func:`Df.Harness.lib.cli_domain_ops._load_consumed()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_prepare_review()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_record_answer()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_record_review()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops.dfh_execute_collect()`
# @used-by :func:`Df.Harness.lib.cli_registry_handlers.dfh_exec_analysis_check()`
# @used-by :func:`Df.Harness.lib.completion_commands._execute_prepare_or_check()`
# @used-by :func:`agent_tools.arch.review_cli._exec_arch_prepare()`
# @used-by :func:`agent_tools.arch.review_cli._exec_arch_record_review()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_scratch_consumption_sha256_and_parallel_answer_guard()`
# @used-by :meth:`test_turn_completion.AntigravityCompletionTests.test_parallel_turn_scratch_isolation_and_budget_gate()`
def dfh_load_operation_input(args: Any, path: Any) -> bytes:
	if getattr(args, 'consume_input', False) and '-' != str(path):
		dfh_verify_scratch_input_path(args.project, path)
	_check_parallel_answer_md_guard(args, path)
	r = dfh_read_input_bytes(path)
	expected_sha = getattr(args, 'expected_sha256', None)
	if expected_sha and 'save-analysis' != getattr(args, 'command', None):
		actual_sha = hashlib.sha256(r).hexdigest().lower()
		if actual_sha != str(expected_sha).strip().lower():
			raise ValueError(f'Input SHA-256 mismatch against --expected-sha256: expected {expected_sha}, got {actual_sha}')
	return r
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_review_target_claim_and_wait_m5.ReviewTargetClaimAndWaitM5Tests.test_native_review_proof_retryable_flag_and_bounded_wait_for_final_response()`
def dfh_operation_error_payload(exc: BaseException) -> dict[str, Any]:
	from agent_tools.repo_wait import is_transient_contention_error
	return {'valid': False, 'retryable': is_transient_contention_error(exc), 'issues': [{'code': 'operation.input', 'field': '/', 'message': str(exc)}]}
# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_run_cleanup_report_cli()`
# @used-by :func:`dfh_load_operation_input()`
# @used-by :func:`dfh_read_input_text()`
def dfh_read_input_bytes(path: Any) -> bytes:
	if '-' != str(path):
		r = Path(path).read_bytes()
	else:
		buf = getattr(sys.stdin, 'buffer', None)
		r = buf.read() if None is not buf else sys.stdin.read().encode('utf-8')
	return r
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_metrics()`
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_question_finish()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_cli_subsystem_classes()`
# @used-by :mod:`agent_tools.text_cli`
def dfh_read_input_json(path: Any, *, encoding: str='utf-8-sig') -> Any:
	return json.loads(dfh_read_input_text(path, encoding=encoding)) if None is not path else None
# @used-by :func:`Df.Harness.lib.cli_domain_ops._op_resume()`
# @used-by :func:`agent_tools.arch.review_cli._exec_arch_check()`
# @used-by :func:`dfh_read_input_json()`
# @used-by :meth:`Df.Harness.Cli.Dispatcher.Dispatcher.__read_step_payloads()`
# @used-by :mod:`agent_tools.text_cli`
def dfh_read_input_text(path: Any, *, encoding: str='utf-8-sig') -> str:
	return dfh_read_input_bytes(path).decode(encoding)
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_declarative_arg_specs_and_routers_parse_expected_flags()`
def dfh_result_exit_code(result: dict, *, extra_failures: tuple=()) -> int:
	failed = False is result.get('valid') or False is result.get('complete') or 'conflict' == result.get('status') or any(extra_failures)
	return 2 if failed else 0
# @used-by :func:`Df.Harness.lib.cleanup_audit_ops.dfh_run_cleanup_report_cli()`
# @used-by :func:`dfh_consume_scratch_input()`
# @used-by :func:`dfh_load_operation_input()`
def dfh_verify_scratch_input_path(project: Any, path: Any) -> Path:
	r = Path(path).resolve()
	scratch_dirs = [dfh_project_paths(project).scratch_dir, dfh_data_dir_for(project) / 'scratch', Path(project).resolve() / '\ua616/data/scratch']
	if not any((r.is_relative_to(s) for s in scratch_dirs)) or Path(path).is_symlink() or any((p.is_junction() for p in (r, *r.parents) if p.exists())):
		raise ValueError('Consumed input must be an ordinary file inside project \ua616/data/scratch')
	return r