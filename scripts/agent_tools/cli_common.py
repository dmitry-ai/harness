# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
import hashlib
import json
from pathlib import Path
import sys
# 2026-11-14
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
# @used-by :func:`agent_tools.cli.main()`
# @used-by :func:`agent_tools.cli_registry.add_registered_parsers()`
# @used-by :func:`agent_tools.completion.add_parser_arguments()`
# @used-by :func:`agent_tools.github_issue.build_parser()`
# @used-by :func:`agent_tools.operations.add_parsers()`
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :func:`agent_tools.upwork_project.main()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_declarative_arg_specs_and_routers_parse_expected_flags()`
def add_arg_specs(parser, specs: tuple | list) -> None:
	for flags, kwargs in specs:
		names = flags if isinstance(flags, tuple) else (flags,)
		parser.add_argument(*names, **kwargs)
# @used-by :func:`agent_tools.cli_domains._load_consumed()`
# @used-by :func:`agent_tools.cli_domains._op_prepare_review()`
# @used-by :func:`agent_tools.cli_domains._op_record_answer()`
# @used-by :func:`agent_tools.cli_domains._op_record_review()`
# @used-by :func:`agent_tools.completion.execute()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_scratch_consumption_sha256_and_parallel_answer_guard()`
# @used-by :mod:`agent_tools.operations`
def consume_scratch_input(args, path, payload: bytes, result: dict) -> dict:
	if not getattr(args, 'consume_input', False) or '-' == str(path):
		r = result
	else:
		target = verify_scratch_input_path(args.project, path)
		if 'conflict' == result.get('status') or False is result.get('complete') or False is result.get('valid'):
			r = result
		else:
			if target.exists() and target.read_bytes() == payload:
				target.unlink()
				result['consumed_input'] = str(target)
			r = result
	return r
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._finalize_close()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._verify_mutation_readback()`
# @used-by :mod:`agent_tools.github_issue`
def consume_unchanged_files(files: list[tuple[Path, bytes]]) -> list[str]:
	r: list[str] = []
	for path, expected_bytes in files:
		if path.exists() and path.read_bytes() == expected_bytes:
			path.unlink()
			r.append(str(path))
	return r
# @used-by :func:`agent_tools.cli.main()`
# @used-by :func:`agent_tools.github_issue.main()`
# @used-by :func:`agent_tools.issues.repo_commands.run_audit_repo()`
# @used-by :func:`agent_tools.issues.repo_commands.run_fetch()`
# @used-by :func:`agent_tools.issues.repo_commands.run_lint()`
# @used-by :func:`agent_tools.issues.repo_commands.run_transfer_repo()`
# @used-by :func:`agent_tools.text_cli.findings_output()`
# @used-by :func:`agent_tools.text_cli.main()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._edit_parent_only()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._execute_edit()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._finalize_close()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._post_close_comment()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._verify_close_prereqs()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService._verify_mutation_readback()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService.cmd_comment()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService.cmd_create()`
# @used-by :meth:`agent_tools.issues.service.GitHubIssueService.run_verified_mutation()`
def dump_json(payload, *, stream=None) -> None:
	print(json.dumps(payload, ensure_ascii=False, indent=2), file=stream or sys.stdout)
# @used-by :func:`agent_tools.cli_domains._load_consumed()`
# @used-by :func:`agent_tools.cli_domains._op_prepare_review()`
# @used-by :func:`agent_tools.cli_domains._op_record_answer()`
# @used-by :func:`agent_tools.cli_domains._op_record_review()`
# @used-by :func:`agent_tools.cli_registry._exec_analysis_check()`
# @used-by :func:`agent_tools.completion.execute()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_scratch_consumption_sha256_and_parallel_answer_guard()`
# @used-by :mod:`agent_tools.operations`
def load_operation_input(args, path) -> bytes:
	if getattr(args, 'consume_input', False) and '-' != str(path):
		verify_scratch_input_path(args.project, path)
	if 'answer-prepare' == getattr(args, 'command', None) and '-' != str(path):
		from .storage import data_dir_for
		target = Path(path).resolve()
		if 'answer.md' == target.name.lower():
			turns_dir = data_dir_for(args.project) / 'turns'
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
	r = read_input_bytes(path)
	expected_sha = getattr(args, 'expected_sha256', None)
	if expected_sha and 'save-analysis' != getattr(args, 'command', None):
		actual_sha = hashlib.sha256(r).hexdigest().lower()
		if actual_sha != str(expected_sha).strip().lower():
			raise ValueError(f'Input SHA-256 mismatch against --expected-sha256: expected {expected_sha}, got {actual_sha}')
	return r
# 2026-11-24
# "Add deterministic reactive wait primitive for transient repository and journal contention":
# https://github.com/dmitry-ai/harness/issues/199
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_review_target_claim_and_wait_m5.ReviewTargetClaimAndWaitM5Tests.test_native_review_proof_retryable_flag_and_bounded_wait_for_final_response()`
def operation_error_payload(exc: BaseException) -> dict:
	from .repo_wait import is_transient_contention_error
	return {'valid': False, 'retryable': is_transient_contention_error(exc), 'issues': [{'code': 'operation.input', 'field': '/', 'message': str(exc)}]}
# 2026-11-14
# "Consolidate token/stage summarize, native_review_proof, read-only SQLite, file:// helpers, and ProjectCleanupScanner across trace_common.py, antigravity.py, codex.py, metrics.py, and cleanup.py":
# https://github.com/dmitry-ai/harness/issues/75
# @used-by :func:`agent_tools.cleanup_audit.run_cleanup_report_cli()`
# @used-by :func:`load_operation_input()`
# @used-by :func:`read_input_text()`
# @used-by :mod:`agent_tools.operations`
def read_input_bytes(path) -> bytes:
	if '-' != str(path):
		r = Path(path).read_bytes()
	else:
		buf = getattr(sys.stdin, 'buffer', None)
		r = buf.read() if None is not buf else sys.stdin.read().encode('utf-8')
	return r
# @used-by :func:`agent_tools.cli_domains._op_metrics()`
# @used-by :func:`agent_tools.cli_domains._op_question_finish()`
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :mod:`agent_tools.text_cli`
def read_input_json(path, *, encoding: str='utf-8-sig'):
	return json.loads(read_input_text(path, encoding=encoding)) if None is not path else None
# @used-by :func:`agent_tools.cli.main()`
# @used-by :func:`agent_tools.cli_domains._op_resume()`
# @used-by :func:`read_input_json()`
# @used-by :mod:`agent_tools.text_cli`
def read_input_text(path, *, encoding: str='utf-8-sig') -> str:
	return read_input_bytes(path).decode(encoding)
# @used-by :func:`agent_tools.upwork_project.run()`
# @used-by :meth:`test_cli_common.CliCommonTests.test_declarative_arg_specs_and_routers_parse_expected_flags()`
def result_exit_code(result: dict, *, extra_failures: tuple=()) -> int:
	failed = False is result.get('valid') or False is result.get('complete') or 'conflict' == result.get('status') or any(extra_failures)
	return 2 if failed else 0
# @used-by :func:`agent_tools.cleanup_audit.run_cleanup_report_cli()`
# @used-by :func:`consume_scratch_input()`
# @used-by :func:`load_operation_input()`
def verify_scratch_input_path(project, path) -> Path:
	# 2026-11-19
	# "Wire project path overlays across Harness subsystems with paths CLI and regression tests":
	# https://github.com/dmitry-ai/harness/issues/96
	from .path_registry import project_paths
	from .storage import data_dir_for
	r = Path(path).resolve()
	scratch_dirs = [project_paths(project).scratch_dir, data_dir_for(project) / 'scratch', Path(project).resolve() / '\ua616/data/scratch']
	if not any((r.is_relative_to(s) for s in scratch_dirs)) or Path(path).is_symlink() or any((p.is_junction() for p in (r, *r.parents) if p.exists())):
		raise ValueError('Consumed input must be an ordinary file inside project \ua616/data/scratch')
	return r
