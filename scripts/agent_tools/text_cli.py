# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
import argparse
from dataclasses import asdict
import difflib
from pathlib import Path
import re
import sys
from .cli_common import add_arg_specs, dump_json, read_input_json, read_input_text
data = read_input_json
read = read_input_text
_DOC_SPECS = {
	'lint': (('--lang', {'choices': ('en', 'ru')}), ('--bans', {'type': Path}), ('--profile', {'type': Path}), ('--errors-only', {'action': 'store_true'}), ('--network', {'action': 'store_true', 'help': 'Also fetch HTTP links and check source anchors; unavailable is not verified'}), ('--project', {'type': Path, 'help': 'Exact evidence root; required for --network'})),
	'render': ((('-o', '--output'), {'type': Path}), ('--expected-sha256', {}), ('--previous', {'type': Path}), ('--stdout', {'action': 'store_true'}), ('--diff', {'action': 'store_true'}), ('--force', {'action': 'store_true', 'help': argparse.SUPPRESS})),
	'replay': (('--shell', {}), ('--timeout', {'type': float, 'default': 60}), ('--line', {'type': int, 'action': 'append'}), ('--expected-exit', {'type': int}), ('--contracts', {'type': Path})),
	'response': (('--against', {'type': Path, 'action': 'append', 'default': []}), ('--journal', {'type': Path})),
	'source': ((('-o', '--output'), {'type': Path}), ('--expected-sha256', {})),
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
def findings_output(findings, path, as_json=False):
	if as_json:
		dump_json([asdict(f) for f in findings])
	else:
		for finding in findings:
			print(finding.format(str(path)))
		print(f'{path}: ' + ', '.join((f'{sum((f.severity == level for f in findings))} {level}(s)' for level in ('error', 'warning', 'note'))))
	return int(any(('error' == f.severity for f in findings)))
def main(argv=None, *, default_kind='article'):
	from . import text_core as core, text_workflow as flow
	if hasattr(sys.stdout, 'reconfigure'):
		sys.stdout.reconfigure(encoding='utf-8')
	parser = argparse.ArgumentParser(prog='df_' + ('text' if None is default_kind else default_kind) + '.py', description=__doc__)
	sub = parser.add_subparsers(dest='command', required=True)
	for command in ('lint', 'source', 'render', 'replay', 'response'):
		p = sub.add_parser(command)
		specs = [('targets' if 'lint' == command else 'target', {'nargs': '+' if 'lint' == command else None, 'type': Path})]
		if command in ('lint', 'source', 'render'):
			specs.append(('--kind', {'choices': ('article', 'proposal', 'letter', 'response'), 'default': default_kind or 'article'}))
		if command in ('lint', 'response'):
			specs.append(('--json', {'action': 'store_true'}))
		specs.extend(_DOC_SPECS[command])
		add_arg_specs(p, specs)
	add_arg_specs(sub.add_parser('fields'), (('--fields', {'type': Path, 'required': True}), ('--limits', {'type': Path, 'required': True}), ('--count-mode', {'choices': ('utf16', 'unicode'), 'default': 'utf16'})))
	extra_flow = {'check': (('--run-replay', {'action': 'store_true'}),), 'finalize': (('--publication', {'action': 'store_true'}),), 'record-answer': (('--request-file', {'action': 'append', 'required': True}),), 'sources': (('--claim', {'action': 'append', 'required': True}),)}
	for command, flags in _FLOW_OPTIONS.items():
		add_arg_specs(sub.add_parser(command), [('project', {'type': Path}), *(('--' + flag, {'required': req}) for flag, req in flags), *extra_flow.get(command, ())])
	args = parser.parse_args(argv)
	try:
		command = args.command
		if 'response' == command:
			r = findings_output(core.check_response(args.target, against=args.against, journal=args.journal), args.target, args.json)
		elif 'fields' == command:
			from .proposal import lint_fields
			r = findings_output(lint_fields(data(args.fields), data(args.limits), count_mode=args.count_mode), args.fields)
		elif 'replay' == command:
			res = core.replay(read(args.target), shell=args.shell, timeout=args.timeout, only=args.line, expected_exit=args.expected_exit, contracts=data(args.contracts))
			dump_json(res)
			r = int(not res or any(('match' != item['status'] for item in res)))
		elif 'lint' == command:
			r = 0
			for target in args.targets:
				text = read(target)
				bans = data(args.bans)
				bans = bans.get('bans', []) if isinstance(bans, dict) else bans
				profile = data(args.profile)
				if 'proposal' == args.kind:
					from .proposal import lint_text
					findings = lint_text(text, path=target, lang=args.lang, bans=bans, profile=profile)
				else:
					from .article import lint_text
					findings = lint_text(text, kind=args.kind, path=target, lang=args.lang, bans=bans, **{'link_style': profile['link_style']} if (profile or {}).get('link_style') else {})
				if args.network:
					from .text_sources import probe_links
					if None is args.project or not target.resolve().is_relative_to(args.project.resolve()):
						raise ValueError('--network requires the exact --project containing this candidate')
					findings.extend(probe_links(args.project, text)['findings'])
				r |= findings_output([f for f in findings if not args.errors_only or 'error' == f.severity], target, args.json)
		elif command in ('source', 'render'):
			if args.kind not in ('article', 'proposal'):
				raise ValueError('Keyed numbering is available for article or proposal; a letter preserves its own form')
			from . import article, proposal
			engine = proposal if 'proposal' == args.kind else article
			original = read(args.target)
			previous = read(args.previous) if 'render' == command and args.previous else None
			if 'source' == command:
				value, report, findings = (engine.to_source(original), {}, [])
			else:
				if not (args.output or args.stdout or args.diff):
					raise ValueError('render needs --stdout, --diff, or --output')
				value, report, findings = engine.render(original, previous)
			for finding in findings:
				print(finding.format(str(args.target)), file=sys.stderr)
			if any(('error' == f.severity for f in findings)):
				r = 1
			else:
				if 'render' == command and args.diff:
					before = previous if None is not previous else read(args.output) if args.output and args.output.exists() else ''
					sys.stdout.writelines(difflib.unified_diff(before.splitlines(True), value.splitlines(True), fromfile=str(args.previous or args.output or 'previous'), tofile='proposed'))
				elif not (args.output and (not getattr(args, 'stdout', False))):
					sys.stdout.write(value)
				else:
					dump_json({**flow.write_candidate_output(args.output, value.encode(), expected_sha256=args.expected_sha256), 'changes': report})
				r = 0
		else:
			if command in ('begin', 'guard'):
				result = flow.begin(args.project, data(args.spec))
			elif 'check' == command:
				result = flow.check(args.project, args.operation, read(args.candidate), data(args.manifest), run_replay=args.run_replay, replay_record=args.replay_record, warning_dispositions=data(args.warnings))
			elif 'apply' == command:
				result = flow.apply(args.project, args.check)
			elif 'diagnose' == command:
				from .text_diagnostics import diagnose_sources
				result = diagnose_sources(args.project, platform=args.platform, profile=args.profile)
			elif 'browser-check' == command:
				from .text_browser import preflight
				result = preflight(data(args.spec))
			elif 'claims-save' == command:
				from .text_claims import save_registry
				result = save_registry(args.project, data(args.candidate), expected_sha256=args.expected_sha256, **{'reference': args.registry} if args.registry else {})
			elif 'sources' == command:
				from .text_sources import check_claim_sources
				result = check_claim_sources(args.project, args.claim, reference=args.registry or '\ua616/KB/TextClaims.json')
			elif 'source-check' == command:
				from .text_sources import save_source_check
				result = save_source_check(args.project, read(args.candidate), data(args.spec))
			elif 'review-input' == command:
				from .review import input_receipt
				result = input_receipt(args.project, args.package)
			elif command.startswith('review-'):
				from . import text_review
				if 'review-prepare' == command:
					result = text_review.prepare(args.project, args.check, args.parent, data(args.spec))
				elif 'review-record' != command:
					result = text_review.authorize(args.project, args.check)
				else:
					result = text_review.record(args.project, args.report, parent_id=args.parent, reviewer_id=args.reviewer, native_evidence=args.native_evidence)
			elif 'record-answer' == command:
				result = flow.record_answer(args.project, args.journal, [read(p) for p in args.request_file], read(args.response_file), args.turn)
			elif 'finalize' != command:
				raise ValueError('Unknown client-text operation')
			else:
				result = flow.gate(args.project, publication=args.publication)
			dump_json(result)
			r = int(False is result.get('valid'))
	except (OSError, ValueError, KeyError, TypeError, re.error) as exc:
		print('ERROR: ' + str(exc), file=sys.stderr)
		r = 2
	return r
