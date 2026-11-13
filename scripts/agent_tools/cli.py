# 2026-11-14 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Unify declarative CLI routers, scratch-verified --consume-input/stdin loading, and read-back mutations in cli_common.py":
# https://github.com/dmitry-ai/harness/issues/69
# 2026-10-11 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Extract self-contained .agents toolkit, deterministic validation CLI, and rule architecture from wayse.pt":
# https://github.com/dmitry-ai/harness/issues/2
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# 2026-10-31 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Enforce EXEC-5 code/issue lifecycle gate in answer-prepare, URL-only commit messages, git_shim/hook commit interception, and worktree isolation":
# https://github.com/dmitry-ai/harness/issues/31
# 2026-11-03 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Refactor generate_context.py to export only current timestamp and Agent KB excluding Evidence":
# https://github.com/dmitry-ai/harness/issues/42
import argparse
import json
from pathlib import Path
import sys
from .cli_common import add_arg_specs, dump_json, read_input_text
_LINK_SPECS = (('targets', {'nargs': '+', 'type': Path}), ('--local-anchors', {'action': 'store_true'}), ('--unique-urls', {'action': 'store_true'}), ('--include-code', {'action': 'store_true'}), ('--readable', {'action': 'store_true', 'help': 'Enforce LINK-5 on authored document references, before renderer URL normalization'}), (('--network', '--check-http'), {'action': 'store_true'}), ('--timeout', {'type': float, 'default': 15}))
def main(command: str, argv=None, *, context_default: Path | None=None, root_default: Path | None=None) -> int:
	parser = argparse.ArgumentParser(prog=command + '.py')
	ctx_specs = (('root_pos', {'nargs': '?', 'type': Path, 'default': None, 'help': 'Project root directory'}), ('--root', {'type': Path, 'default': root_default, 'help': 'Project root directory'}), ('--config', {'type': Path, 'default': context_default, 'help': 'Context configuration file'}), (('--output', '-o'), {'type': Path, 'help': 'Output path (defaults to \ua66e/0/Context.md)'}), ('--dry-run', {'action': 'store_true', 'help': 'Check inputs without writing output'}))
	specs_map = {
		'generate_context': ctx_specs,
		'rebuild_context': ctx_specs,
		'safe_commit': (('--repo', {'type': Path, 'required': True}), ('--file', {'action': 'append', 'required': True}), (('--message', '-m'), {'required': True}), ('--execute', {'action': 'store_true'}), ('--worktree', {'action': 'store_true', 'help': 'Commit explicit files in an isolated temporary linked git worktree'})),
		'snapshot_draft': (('target', {'type': Path}), ('--turn', {'required': True})),
		'validate_anchors': _LINK_SPECS,
		'validate_links': _LINK_SPECS,
		'validate_statements': (('directory', {'type': Path}),),
	}
	if 'record_step' == command:
		add_arg_specs(parser, (('--dir', {'type': Path, 'required': True}), ('--step', {'type': int}), ('--recover', {'type': int}), ('--token', {})))
		for name in ('req', 'res'):
			group = parser.add_mutually_exclusive_group()
			add_arg_specs(group, (('--' + name, {}), ('--' + name + '-file', {'type': Path})))
	elif 'validate_step' == command:
		add_arg_specs(parser, (('--dir', {'type': Path, 'required': True}), ('--file', {'type': Path, 'action': 'append', 'default': []})))
		group = parser.add_mutually_exclusive_group(required=True)
		add_arg_specs(group, (('--step', {'type': int}), ('--all', {'action': 'store_true'})))
	elif command in specs_map:
		add_arg_specs(parser, specs_map[command])
	else:
		raise ValueError(f'Unknown command: {command}')
	args = parser.parse_args(argv)
	r = 0
	try:
		if 'snapshot_draft' == command:
			from .snapshot import snapshot_draft
			print(snapshot_draft(args.target, args.turn))
		elif 'safe_commit' == command:
			from .git_gate import commit
			paths = commit(args.repo, args.file, args.message, args.execute, worktree=args.worktree)
			print(f"{('Committed' if args.execute else 'Checked; commit requires --execute')}: {json.dumps(paths, ensure_ascii=False)}")
		elif 'validate_statements' == command:
			from .statements import validate_statements
			errors = validate_statements(args.directory)
			if errors:
				raise ValueError('\n'.join(errors))
			print('Statement and Test.md files exist and are nonempty UTF-8; evidence truth was not checked')
		elif command in ('generate_context', 'rebuild_context'):
			from .context import generate
			root = args.root or args.root_pos or root_default or Path('.')
			target, content, sources = generate(root, args.config, args.output, args.dry_run)
			print(f"{len(sources)} sources; {len(content.encode('utf-8'))} bytes; {('dry run' if args.dry_run else 'saved')}: {target}")
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
		elif 'record_step' != command:
			from .links import check_network, references, validate_file
			errors = []
			urls = []
			for path in args.targets:
				errors.extend(validate_file(path, local_anchors=args.local_anchors, unique_urls=args.unique_urls, include_code=args.include_code, readable_links=args.readable))
				urls.extend(references(path.read_text(encoding='utf-8'), args.include_code)[0])
			if errors:
				raise ValueError('\n'.join(errors))
			if args.network or 'validate_anchors' == command:
				if 0 >= args.timeout:
					raise ValueError('Timeout must be positive')
				results = check_network(urls, anchors='validate_anchors' == command, timeout=args.timeout)
				dump_json(results)
				if not results:
					raise ValueError('No matching HTTP(S) links to check')
				if any((item['status'] not in ('http-ok', 'found-in-source') for item in results)):
					r = 2
			if 0 == r:
				print(f'Structural checks passed for {len(args.targets)} explicit files; browser behavior was not checked')
		else:
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
					text = read_input_text(path, encoding='utf-8') if path else getattr(args, name)
					if None is text:
						parser.error(f'Provide --{name} or --{name}-file')
					payload.append(text)
				step = record_step(args.dir, *payload, target_step=args.step)
			errors = step_errors(args.dir, step)
			if errors:
				raise ValueError('\n'.join(errors))
			print(f'Journal pair {step} saved and read back exactly')
	except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
		print(f'ERROR: {exc}', file=sys.stderr)
		r = 1
	return r
