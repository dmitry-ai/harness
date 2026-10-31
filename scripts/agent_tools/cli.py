# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
import argparse
import json
from pathlib import Path
import sys
def main(command: str, argv=None, *, context_default: Path | None=None, root_default: Path | None=None) -> int:
	parser = argparse.ArgumentParser(prog=command + '.py')
	if 'record_step' == command:
		parser.add_argument('--dir', type=Path, required=True)
		parser.add_argument('--step', type=int)
		parser.add_argument('--recover', type=int)
		parser.add_argument('--token')
		for name in ('req', 'res'):
			group = parser.add_mutually_exclusive_group()
			group.add_argument('--' + name)
			group.add_argument('--' + name + '-file', type=Path)
	elif 'validate_step' == command:
		parser.add_argument('--dir', type=Path, required=True)
		group = parser.add_mutually_exclusive_group(required=True)
		group.add_argument('--step', type=int)
		group.add_argument('--all', action='store_true')
		parser.add_argument('--file', type=Path, action='append', default=[])
	elif command in ('validate_links', 'validate_anchors'):
		parser.add_argument('targets', nargs='+', type=Path)
		parser.add_argument('--local-anchors', action='store_true')
		parser.add_argument('--unique-urls', action='store_true')
		parser.add_argument('--include-code', action='store_true')
		parser.add_argument('--readable', action='store_true', help='Enforce LINK-5 on authored document references, before renderer URL normalization')
		parser.add_argument('--network', '--check-http', action='store_true')
		parser.add_argument('--timeout', type=float, default=15)
	elif command in ('generate_context', 'rebuild_context'):
		parser.add_argument('--root', type=Path, default=root_default, required=None is root_default)
		parser.add_argument('--config', type=Path, default=context_default, required=None is context_default)
		parser.add_argument('--output', '-o', type=Path)
		parser.add_argument('--dry-run', action='store_true')
	elif 'snapshot_draft' == command:
		parser.add_argument('target', type=Path)
		parser.add_argument('--turn', required=True)
	elif 'safe_commit' == command:
		parser.add_argument('--repo', type=Path, required=True)
		parser.add_argument('--file', action='append', required=True)
		parser.add_argument('--message', '-m', required=True)
		parser.add_argument('--execute', action='store_true')
	elif 'validate_statements' == command:
		parser.add_argument('directory', type=Path)
	else:
		raise ValueError(f'Unknown command: {command}')
	args = parser.parse_args(argv)
	try:
		if 'record_step' == command:
			from .journal import record_step, recover_step, step_errors
			if None is not args.recover:
				if not args.token or any((None is not getattr(args, k) for k in ('req', 'res', 'req_file', 'res_file', 'step'))):
					parser.error('--recover needs --token and cannot be combined with new payloads or --step')
				recover_step(args.dir, args.recover, args.token)
				step = args.recover
			else:
				if args.token:
					parser.error('--token requires --recover')
				payload = []
				for name in ('req', 'res'):
					path = getattr(args, name + '_file')
					text = path.read_bytes().decode('utf-8') if path else getattr(args, name)
					if None is text:
						parser.error(f'Provide --{name} or --{name}-file')
					payload.append(text)
				step = record_step(args.dir, *payload, target_step=args.step)
			errors = step_errors(args.dir, step)
			if errors:
				raise ValueError('\n'.join(errors))
			print(f'Journal pair {step} saved and read back exactly')
		elif 'validate_step' == command:
			from .journal import get_existing_step_ids, step_errors
			steps = sorted(get_existing_step_ids(args.dir)) if args.all else [args.step]
			if not steps:
				raise ValueError('No journal steps found')
			errors = [error for step in steps for error in step_errors(args.dir, step)]
			if args.file:
				from .links import validate_file
				errors += [e for path in args.file for e in validate_file(path)]
			if errors:
				raise ValueError('\n'.join(errors))
			print(f'Checked {len(steps)} journal pairs and {len(args.file)} explicit files; content truth and authorization require review')
		elif command in ('validate_links', 'validate_anchors'):
			from .links import check_network, references, validate_file
			errors = []
			urls = []
			for path in args.targets:
				errors.extend(validate_file(path, local_anchors=args.local_anchors, unique_urls=args.unique_urls, include_code=args.include_code, readable_links=args.readable))
				urls.extend(references(path.read_text(encoding='utf-8'), args.include_code)[0])
			if errors:
				raise ValueError('\n'.join(errors))
			if args.network or 'validate_anchors' == command:
				if args.timeout <= 0:
					raise ValueError('Timeout must be positive')
				results = check_network(urls, anchors='validate_anchors' == command, timeout=args.timeout)
				print(json.dumps(results, ensure_ascii=False, indent=2))
				if not results:
					raise ValueError('No matching HTTP(S) links to check')
				if any((r['status'] not in ('http-ok', 'found-in-source') for r in results)):
					return 2
			print(f'Structural checks passed for {len(args.targets)} explicit files; browser behavior was not checked')
		elif command in ('generate_context', 'rebuild_context'):
			from .context import generate
			target, content, sources = generate(args.root, args.config, args.output, args.dry_run)
			print(f"{len(sources)} sources; {len(content.encode('utf-8'))} bytes; {('dry run' if args.dry_run else 'saved')}: {target}")
		elif 'snapshot_draft' == command:
			from .snapshot import snapshot_draft
			print(snapshot_draft(args.target, args.turn))
		elif 'safe_commit' == command:
			from .git_gate import commit
			paths = commit(args.repo, args.file, args.message, args.execute)
			print(f"{('Committed' if args.execute else 'Checked; commit requires --execute')}: {json.dumps(paths, ensure_ascii=False)}")
		elif 'validate_statements' == command:
			from .statements import validate_statements
			errors = validate_statements(args.directory)
			if errors:
				raise ValueError('\n'.join(errors))
			print('Statement and Test.md files exist and are nonempty UTF-8; evidence truth was not checked')
		return 0
	except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
		print(f'ERROR: {exc}', file=sys.stderr)
		return 1
