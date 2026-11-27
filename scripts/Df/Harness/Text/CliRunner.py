# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import argparse
from dataclasses import asdict
import difflib
from pathlib import Path
import re
import sys
from Df.Harness.Text.Article.Renderer import Renderer as ArticleRenderer
from Df.Harness.Text.Article.SourceExporter import SourceExporter as ArticleExporter
from Df.Harness.Text.Browser.PreflightChecker import PreflightChecker
from Df.Harness.Text.ClaimRegistryStore import ClaimRegistryStore
from Df.Harness.Text.CommandReplayer import CommandReplayer
from Df.Harness.Text.DiagnosticsScanner import DiagnosticsScanner
from Df.Harness.Text.Proposal.FieldLinter import FieldLinter
from Df.Harness.Text.Proposal.Renderer import Renderer as ProposalRenderer
from Df.Harness.Text.Proposal.SourceExporter import SourceExporter as ProposalExporter
from Df.Harness.Text.ResponseChecker import ResponseChecker
from Df.Harness.Text.ReviewAuthorizer import ReviewAuthorizer
from Df.Harness.Text.ReviewPreparer import ReviewPreparer
from Df.Harness.Text.ReviewRecorder import ReviewRecorder
from Df.Harness.Text.SourceProber import SourceProber
from Df.Harness.Text.SourceReceiptStore import SourceReceiptStore
from Df.Harness.Text.Workspace import Workspace
from Df.Harness.lib.text_sections import dfh_lint_document
from Df.Harness.lib.text_sources import dfh_check_claim_sources
from Df.Harness.lib.text_workflow import dfh_record_text_answer, dfh_write_candidate_output
from agent_tools.cli_common import add_arg_specs, dump_json, read_input_json, read_input_text
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_DOC_SPECS = {
	'lint': (('--lang', {'choices': ('en', 'ru')}), ('--bans', {'type': Path}), ('--profile', {'type': Path}), ('--errors-only', {'action': 'store_true'}), ('--network', {'action': 'store_true', 'help': 'Also fetch HTTP links and check source anchors; unavailable is not verified'}), ('--project', {'type': Path, 'help': 'Exact evidence root; required for --network'})),
	'render': ((('-o', '--output'), {'type': Path}), ('--expected-sha256', {}), ('--previous', {'type': Path}), ('--stdout', {'action': 'store_true'}), ('--diff', {'action': 'store_true'}), ('--force', {'action': 'store_true', 'help': argparse.SUPPRESS})),
	'replay': (('--shell', {}), ('--timeout', {'type': float, 'default': 60}), ('--line', {'type': int, 'action': 'append'}), ('--expected-exit', {'type': int}), ('--contracts', {'type': Path})),
	'response': (('--against', {'type': Path, 'action': 'append', 'default': []}), ('--journal', {'type': Path})),
	'source': ((('-o', '--output'), {'type': Path}), ('--expected-sha256', {})),
}
_EXTRA_FLOW = {
	'check': (('--run-replay', {'action': 'store_true'}),),
	'finalize': (('--publication', {'action': 'store_true'}),),
	'record-answer': (('--request-file', {'action': 'append', 'required': True}),),
	'sources': (('--claim', {'action': 'append', 'required': True}),),
}
_FLOW_OPTIONS = {
	'apply': (('check', True),),
	'begin': (('spec', True),),
	'browser-check': (('spec', True),),
	'check': (('operation', True), ('candidate', True), ('manifest', False), ('warnings', False), ('replay-record', False)),
	'claims-save': (('candidate', True), ('registry', False), ('expected-sha256', False)),
	'diagnose': (('platform', False), ('profile', False)),
	'finalize': (),
	'guard': (('spec', True),),
	'record-answer': (('journal', True), ('response-file', True), ('turn', True)),
	'review-input': (('package', True),),
	'review-prepare': (('check', True), ('parent', True), ('spec', False)),
	'review-record': (('report', True), ('parent', True), ('reviewer', True), ('native-evidence', True)),
	'review-status': (('check', True),),
	'source-check': (('candidate', True), ('spec', True)),
	'sources': (('registry', False),),
}
class CliRunner:
	# @used-by :func:`agent_tools.text_cli.main()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
	def __init__(self, argv=None, *, default_kind: str | None='article') -> None:
		self.__argv = argv
		self.__default_kind = default_kind
	# @used-by :meth:`CliRunner.run()`
	def __build_parser(self) -> argparse.ArgumentParser:
		parser = argparse.ArgumentParser(prog='df_' + ('text' if None is self.__default_kind else self.__default_kind) + '.py', description=__doc__)
		sub = parser.add_subparsers(dest='command', required=True)
		for command in ('lint', 'source', 'render', 'replay', 'response'):
			specs = [('targets' if 'lint' == command else 'target', {'nargs': '+' if 'lint' == command else None, 'type': Path})]
			if command in ('lint', 'source', 'render'):
				specs.append(('--kind', {'choices': ('article', 'proposal', 'letter', 'response'), 'default': self.__default_kind or 'article'}))
			if command in ('lint', 'response'):
				specs.append(('--json', {'action': 'store_true'}))
			add_arg_specs(sub.add_parser(command), [*specs, *_DOC_SPECS[command]])
		add_arg_specs(sub.add_parser('fields'), (('--fields', {'type': Path, 'required': True}), ('--limits', {'type': Path, 'required': True}), ('--count-mode', {'choices': ('utf16', 'unicode'), 'default': 'utf16'})))
		for command, flags in _FLOW_OPTIONS.items():
			add_arg_specs(sub.add_parser(command), [('project', {'type': Path}), *(('--' + flag, {'required': req}) for flag, req in flags), *_EXTRA_FLOW.get(command, ())])
		return parser
	# @used-by :meth:`CliRunner.run()`
	def __dispatch(self, args) -> int:
		cmd = args.command
		if 'response' == cmd:
			r = self.findings_output(ResponseChecker(args.target, against=args.against, journal=args.journal).check(), args.target, args.json)
		elif 'fields' == cmd:
			r = self.findings_output(FieldLinter(read_input_json(args.fields), read_input_json(args.limits), count_mode=args.count_mode).lint(), args.fields)
		elif 'replay' == cmd:
			res = CommandReplayer(read_input_text(args.target), shell=args.shell, timeout=args.timeout, only=args.line, expected_exit=args.expected_exit, contracts=read_input_json(args.contracts)).replay()
			dump_json(res)
			r = int(not res or any(('match' != item['status'] for item in res)))
		elif 'lint' == cmd:
			r = self.__handle_lint(args)
		elif cmd in ('source', 'render'):
			r = self.__handle_source_or_render(args)
		else:
			r = self.__dispatch_flow(args)
		return r
	# @used-by :meth:`CliRunner.__dispatch()`
	def __dispatch_flow(self, args) -> int:
		handlers = {**self.__workspace_handlers(args), **self.__review_source_handlers(args)}
		if args.command not in handlers:
			raise ValueError('Unknown client-text operation')
		result = handlers[args.command]()
		dump_json(result)
		return int(False is result.get('valid'))
	# @used-by :meth:`CliRunner.__dispatch()`
	def __handle_lint(self, args) -> int:
		r = 0
		for target in args.targets:
			text = read_input_text(target)
			bans = read_input_json(args.bans)
			bans = bans.get('bans', []) if isinstance(bans, dict) else bans
			findings = dfh_lint_document(text, args.kind, path=target, lang=args.lang, bans=bans, profile=read_input_json(args.profile))
			if args.network:
				if None is args.project or not target.resolve().is_relative_to(args.project.resolve()):
					raise ValueError('--network requires the exact --project containing this candidate')
				findings.extend(SourceProber(args.project, text).probe()['findings'])
			r |= self.findings_output([f for f in findings if not args.errors_only or 'error' == f.severity], target, args.json)
		return r
	# @used-by :meth:`CliRunner.__dispatch()`
	def __handle_source_or_render(self, args) -> int:
		if args.kind not in ('article', 'proposal'):
			raise ValueError('Keyed numbering is available for article or proposal; a letter preserves its own form')
		previous = read_input_text(args.previous) if 'render' == args.command and args.previous else None
		value, report, findings = self.__transform_keyed(args, read_input_text(args.target), previous)
		for finding in findings:
			print(finding.format(str(args.target)), file=sys.stderr)
		if any(('error' == f.severity for f in findings)):
			r = 1
		else:
			self.__write_rendered(args, value, previous, report)
			r = 0
		return r
	# @used-by :meth:`CliRunner.__dispatch_flow()`
	@staticmethod
	def __review_source_handlers(args) -> dict:
		from agent_tools import review
		return {
			'browser-check': lambda: PreflightChecker(read_input_json(args.spec)).check(),
			'claims-save': lambda: ClaimRegistryStore(args.project, read_input_json(args.candidate), expected_sha256=args.expected_sha256, **({'reference': args.registry} if args.registry else {})).save(),
			'diagnose': lambda: DiagnosticsScanner(args.project, platform=args.platform, profile=args.profile).run(),
			'review-input': lambda: review.input_receipt(args.project, args.package),
			'review-prepare': lambda: ReviewPreparer(args.project, args.check, args.parent, read_input_json(args.spec)).prepare(),
			'review-record': lambda: ReviewRecorder(args.project, args.report, parent_id=args.parent, reviewer_id=args.reviewer, native_evidence=args.native_evidence).record(),
			'review-status': lambda: ReviewAuthorizer(args.project, args.check).authorize(),
			'source-check': lambda: SourceReceiptStore(args.project, read_input_text(args.candidate), read_input_json(args.spec)).save(),
			'sources': lambda: dfh_check_claim_sources(args.project, args.claim, reference=args.registry or '\ua616/KB/TextClaims.json'),
		}
	# @used-by :meth:`CliRunner.__handle_source_or_render()`
	@staticmethod
	def __transform_keyed(args, original: str, previous: str | None):
		if 'source' == args.command:
			exporter = ProposalExporter(original) if 'proposal' == args.kind else ArticleExporter(original)
			r = (exporter.export(), {}, [])
		else:
			if not (args.output or args.stdout or args.diff):
				raise ValueError('render needs --stdout, --diff, or --output')
			renderer = ProposalRenderer(original, previous) if 'proposal' == args.kind else ArticleRenderer(original, previous)
			r = renderer.render()
		return r
	# @used-by :meth:`CliRunner.__dispatch_flow()`
	@staticmethod
	def __workspace_handlers(args) -> dict:
		return {
			'apply': lambda: Workspace(args.project).apply(args.check),
			'begin': lambda: Workspace(args.project, strict=True).begin(read_input_json(args.spec)),
			'check': lambda: Workspace(args.project).check(args.operation, read_input_text(args.candidate), read_input_json(args.manifest), run_replay=args.run_replay, replay_record=args.replay_record, warning_dispositions=read_input_json(args.warnings)),
			'finalize': lambda: Workspace(args.project).gate(publication=args.publication),
			'guard': lambda: Workspace(args.project, strict=True).begin(read_input_json(args.spec)),
			'record-answer': lambda: dfh_record_text_answer(args.project, args.journal, [read_input_text(p) for p in args.request_file], read_input_text(args.response_file), args.turn),
		}
	# @used-by :meth:`CliRunner.__handle_source_or_render()`
	@staticmethod
	def __write_rendered(args, value: str, previous: str | None, report: dict) -> None:
		if 'render' == args.command and args.diff:
			before = previous if None is not previous else read_input_text(args.output) if args.output and args.output.exists() else ''
			sys.stdout.writelines(difflib.unified_diff(before.splitlines(True), value.splitlines(True), fromfile=str(args.previous or args.output or 'previous'), tofile='proposed'))
		elif not (args.output and (not getattr(args, 'stdout', False))):
			sys.stdout.write(value)
		else:
			dump_json({**dfh_write_candidate_output(args.output, value.encode(), expected_sha256=args.expected_sha256), 'changes': report})
	# @used-by :func:`agent_tools.text_cli.findings_output()`
	# @used-by :meth:`CliRunner.__dispatch()`
	# @used-by :meth:`CliRunner.__handle_lint()`
	@staticmethod
	def findings_output(findings, path, as_json: bool=False) -> int:
		if as_json:
			dump_json([asdict(f) for f in findings])
		else:
			for finding in findings:
				print(finding.format(str(path)))
			print(f'{path}: ' + ', '.join((f'{sum((f.severity == level for f in findings))} {level}(s)' for level in ('error', 'warning', 'note'))))
		return int(any(('error' == f.severity for f in findings)))
	# @used-by :func:`agent_tools.text_cli.main()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
	def run(self) -> int:
		if hasattr(sys.stdout, 'reconfigure'):
			sys.stdout.reconfigure(encoding='utf-8')
		args = self.__build_parser().parse_args(self.__argv)
		try:
			r = self.__dispatch(args)
		except (OSError, ValueError, KeyError, TypeError, re.error) as exc:
			print('ERROR: ' + str(exc), file=sys.stderr)
			r = 2
		return r
