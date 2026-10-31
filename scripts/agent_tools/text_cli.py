# 2026-10-20 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Implement /df-article and /df-proposal client-text skills, AI-slop linter, scoped baseline diffs, and semantic § rendering":
# https://github.com/dmitry-ai/harness/issues/13
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
import argparse
from dataclasses import asdict
import difflib
import json
from pathlib import Path
import re
import sys
def read(path):
	return sys.stdin.buffer.read().decode('utf-8-sig') if '-' == str(path) else Path(path).read_bytes().decode('utf-8-sig')
def data(path):
	return json.loads(read(path)) if None is not path else None
def findings_output(findings, path, as_json=False):
	if as_json:
		print(json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2))
	else:
		for finding in findings:
			print(finding.format(str(path)))
		print(f'{path}: ' + ', '.join((f'{sum((f.severity == level for f in findings))} {level}(s)' for level in ('error', 'warning', 'note'))))
	r = int(any(('error' == f.severity for f in findings)))
	return r
def main(argv=None, *, default_kind='article'):
	from . import text_core as core, text_workflow as flow
	if hasattr(sys.stdout, 'reconfigure'):
		sys.stdout.reconfigure(encoding='utf-8')
	parser = argparse.ArgumentParser(prog='df_' + ('text' if None is default_kind else default_kind) + '.py', description=__doc__)
	sub = parser.add_subparsers(dest='command', required=True)
	for command in ('lint', 'source', 'render', 'replay', 'response'):
		p = sub.add_parser(command)
		p.add_argument('targets' if 'lint' == command else 'target', nargs='+' if 'lint' == command else None, type=Path)
		if command in ('lint', 'source', 'render'):
			p.add_argument('--kind', choices=('article', 'proposal', 'letter', 'response'), default=default_kind or 'article')
		if command in ('lint', 'response'):
			p.add_argument('--json', action='store_true')
		if 'lint' == command:
			p.add_argument('--lang', choices=('en', 'ru'))
			p.add_argument('--bans', type=Path)
			p.add_argument('--profile', type=Path)
			p.add_argument('--errors-only', action='store_true')
			p.add_argument('--network', action='store_true', help='Also fetch HTTP links and check source anchors; unavailable is not verified')
			p.add_argument('--project', type=Path, help='Exact evidence root; required for --network')
		elif command in ('source', 'render'):
			p.add_argument('-o', '--output', type=Path)
			p.add_argument('--expected-sha256')
			if 'render' == command:
				p.add_argument('--previous', type=Path)
				p.add_argument('--stdout', action='store_true')
				p.add_argument('--diff', action='store_true')
				p.add_argument('--force', action='store_true', help=argparse.SUPPRESS)
		elif 'replay' == command:
			p.add_argument('--shell')
			p.add_argument('--timeout', type=float, default=60)
			p.add_argument('--line', type=int, action='append')
			p.add_argument('--expected-exit', type=int)
			p.add_argument('--contracts', type=Path)
		elif 'response' == command:
			p.add_argument('--against', type=Path, action='append', default=[])
			p.add_argument('--journal', type=Path)
	p = sub.add_parser('fields')
	p.add_argument('--fields', type=Path, required=True)
	p.add_argument('--limits', type=Path, required=True)
	p.add_argument('--count-mode', choices=('utf16', 'unicode'), default='utf16')
	options = {'diagnose': (('platform', False), ('profile', False)), 'browser-check': (('spec', True),), 'begin': (('spec', True),), 'guard': (('spec', True),), 'check': (('operation', True), ('candidate', True), ('manifest', False), ('warnings', False), ('replay-record', False)), 'apply': (('check', True),), 'claims-save': (('candidate', True), ('registry', False), ('expected-sha256', False)), 'sources': (('registry', False),), 'source-check': (('candidate', True), ('spec', True)), 'review-prepare': (('check', True), ('parent', True), ('spec', False)), 'review-input': (('package', True),), 'review-record': (('report', True), ('parent', True), ('reviewer', True), ('native-evidence', True)), 'review-status': (('check', True),), 'record-answer': (('journal', True), ('response-file', True), ('turn', True)), 'finalize': ()}
	for command, flags in options.items():
		p = sub.add_parser(command)
		p.add_argument('project', type=Path)
		for flag, required in flags:
			p.add_argument('--' + flag, required=required)
		if 'check' == command:
			p.add_argument('--run-replay', action='store_true')
		if 'record-answer' == command:
			p.add_argument('--request-file', action='append', required=True)
		if 'finalize' == command:
			p.add_argument('--publication', action='store_true')
		if 'sources' == command:
			p.add_argument('--claim', action='append', required=True)
	args = parser.parse_args(argv)
	try:
		command = args.command
		if 'lint' == command:
			status = 0
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
				status |= findings_output([f for f in findings if not args.errors_only or 'error' == f.severity], target, args.json)
			return status
		if command in ('source', 'render'):
			if args.kind not in ('article', 'proposal'):
				raise ValueError('Keyed numbering is available for article or proposal; a letter preserves its own form')
			from . import article, proposal
			engine = proposal if 'proposal' == args.kind else article
			original = read(args.target)
			if 'source' == command:
				value, report, findings = (engine.to_source(original), {}, [])
			else:
				if not (args.output or args.stdout or args.diff):
					raise ValueError('render needs --stdout, --diff, or --output')
				previous = read(args.previous) if args.previous else None
				value, report, findings = engine.render(original, previous)
			for finding in findings:
				print(finding.format(str(args.target)), file=sys.stderr)
			if any(('error' == f.severity for f in findings)):
				return 1
			if 'render' == command and args.diff:
				before = previous if None is not previous else read(args.output) if args.output and args.output.exists() else ''
				sys.stdout.writelines(difflib.unified_diff(before.splitlines(True), value.splitlines(True), fromfile=str(args.previous or args.output or 'previous'), tofile='proposed'))
			elif not (args.output and (not getattr(args, 'stdout', False))):
				sys.stdout.write(value)
			else:
				result = flow.write_candidate_output(args.output, value.encode(), expected_sha256=args.expected_sha256)
				print(json.dumps({**result, 'changes': report}, ensure_ascii=False, indent=2))
			return 0
		if 'replay' == command:
			result = core.replay(read(args.target), shell=args.shell, timeout=args.timeout, only=args.line, expected_exit=args.expected_exit, contracts=data(args.contracts))
			print(json.dumps(result, ensure_ascii=False, indent=2))
			return int(not result or any(('match' != r['status'] for r in result)))
		if 'response' == command:
			return findings_output(core.check_response(args.target, against=args.against, journal=args.journal), args.target, args.json)
		if 'fields' == command:
			from .proposal import lint_fields
			return findings_output(lint_fields(data(args.fields), data(args.limits), count_mode=args.count_mode), args.fields)
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
			result = check_claim_sources(args.project, args.claim, reference=args.registry or 'ꘖ/KB/TextClaims.json')
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
		print(json.dumps(result, ensure_ascii=False, indent=2))
		return int(False is result.get('valid'))
	except (OSError, ValueError, KeyError, TypeError, re.error) as exc:
		print('ERROR: ' + str(exc), file=sys.stderr)
		return 2
