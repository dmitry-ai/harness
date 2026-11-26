# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from collections.abc import Callable
from pathlib import Path
from Df.Harness.Arch.ReviewStore import ReviewStore
from agent_tools.cli_common import consume_scratch_input, load_operation_input, read_input_text
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
class ReviewCli:
	# @used-by :meth:`ReviewCli.register()`
	@staticmethod
	def __exec_arch_check(args) -> dict:
		resp_txt = read_input_text(args.response_file, encoding='utf-8') if args.response_file else None
		return ReviewStore.inspect_status(args.project, repo=args.repo, response_text=resp_txt, issue_url=args.issue)
	# @used-by :meth:`ReviewCli.register()`
	@staticmethod
	def __exec_arch_prepare(args) -> dict:
		resp_bytes = load_operation_input(args, args.response_file) if args.response_file else None
		spec_bytes = load_operation_input(args, args.spec_file) if args.spec_file else None
		res = ReviewStore.prepare_package(args.project, args.parent, kind=args.kind, response_text=resp_bytes.decode('utf-8') if None is not resp_bytes else None, spec_text=spec_bytes.decode('utf-8') if None is not spec_bytes else None, repo=args.repo, files=args.file or None, issue_url=args.issue)
		if None is not resp_bytes:
			res = consume_scratch_input(args, args.response_file, resp_bytes, res)
		if None is not spec_bytes:
			res = consume_scratch_input(args, args.spec_file, spec_bytes, res)
		return res
	# @used-by :meth:`ReviewCli.register()`
	@staticmethod
	def __exec_arch_record_review(args) -> dict:
		payload = load_operation_input(args, args.report)
		res = ReviewStore(args.project).record_review(payload, parent_id=args.parent, reviewer_id=args.reviewer, native_evidence=args.native_evidence, wait_timeout=float(getattr(args, 'wait_timeout', 0.0)), platform=getattr(args, 'platform', None), instance=getattr(args, 'instance', None))
		return consume_scratch_input(args, args.report, payload, res)
	# @used-by :meth:`ReviewCli.register()`
	@staticmethod
	def __exec_arch_review_input(args) -> dict:
		return ReviewStore.read_review_input(args.project, args.package, parent_id=args.parent, reviewer_id=args.reviewer)
	# @used-by :meth:`ReviewCli.register()`
	@staticmethod
	def __format_arch_check(res: dict, args) -> str | None:
		if 'json' == args.format:
			r = None
		else:
			status = 'PASS' if res.get('valid') else 'FAIL'
			lines = [f"arch-check {status}: approved_modules={res.get('approved_module_count', 0)} approved_subjects={res.get('approved_subject_count', 0)} blocking={len(res.get('blocking_findings') or ())}"]
			for msg in res.get('issues') or ():
				lines.append(f'- {msg}')
			r = '\n'.join(lines) + '\n'
		return r
	# @used-by :func:`agent_tools.arch.review_cli.register_arch_commands()`
	# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_review_cli_registers_and_executes_all_arch_commands()`
	def register(self, register_fn: Callable) -> None:
		register_fn('arch-check', 'Run read-only architecture pattern specification and arch-auditor receipt diagnostics', (('project', {'type': Path}), ('--repo', {'type': Path, 'help': 'Optional code repository root to check structural triggers and cached modules'}), ('--response-file', {'type': Path, 'help': 'Optional UTF-8 candidate response Markdown file'}), ('--issue', {'help': 'Optional parent GitHub Issue URL'}), ('--format', {'choices': ('json', 'text'), 'default': 'json', 'help': 'Output format (default: json)'})), ReviewCli.__exec_arch_check, exit_code_fn=lambda res: 0 if res.get('valid') else 2, text_fn=ReviewCli.__format_arch_check)
		register_fn('arch-prepare', 'Freeze an immutable architecture review package for independent arch-auditor verification', (('project', {'type': Path}), ('--parent', {'required': True, 'help': 'Parent conversation UUID'}), ('--kind', {'choices': ('design', 'code_diff', 'response'), 'required': True, 'help': 'Subject kind to freeze'}), ('--response-file', {'type': Path, 'help': 'Candidate response Markdown file (for --kind response)'}), ('--spec-file', {'type': Path, 'help': 'Architecture specification Markdown file (for --kind design or code_diff)'}), ('--repo', {'type': Path, 'help': 'Code repository root (for --kind code_diff)'}), ('--file', {'action': 'append', 'default': [], 'help': 'Explicit repo-relative production file path; repeatable'}), ('--issue', {'help': 'Optional parent GitHub Issue URL'}), ('--consume-input', {'action': 'store_true', 'help': 'Delete verified scratch input file(s) after success'})), ReviewCli.__exec_arch_prepare)
		register_fn('arch-record-review', 'Validate and record an immutable arch-auditor falsifier verdict with native provenance proof', (('project', {'type': Path}), ('--report', {'type': Path, 'required': True, 'help': 'UTF-8 JSON verdict file emitted by arch-auditor'}), ('--parent', {'required': True, 'help': 'Parent conversation UUID'}), ('--reviewer', {'required': True, 'help': 'Independent arch-auditor subagent conversation UUID'}), ('--native-evidence', {'type': Path, 'help': 'Optional saved native-review-proof JSON path'}), ('--wait-timeout', {'type': float, 'default': 0.0, 'help': 'Bounded wait seconds for reviewer completion'}), ('--consume-input', {'action': 'store_true', 'help': 'Delete verified scratch report file after recording'})), ReviewCli.__exec_arch_record_review)
		register_fn('arch-review-input', 'Read and cryptographically verify an immutable architecture review package inside arch-auditor', (('project', {'type': Path}), ('--package', {'required': True, 'help': 'Project-relative path to frozen package under ꘖ/data/arch-reviews/packages/'}), ('--parent', {'help': 'Optional parent conversation UUID'}), ('--reviewer', {'help': 'Optional reviewer conversation UUID'})), ReviewCli.__exec_arch_review_input)
