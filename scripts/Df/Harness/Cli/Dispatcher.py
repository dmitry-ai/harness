# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Any
from Df.Harness.lib.cli_input import dfh_add_arg_specs, dfh_dump_json, dfh_read_input_text
import argparse
import json
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
_LINK_SPECS = (('targets', {'nargs': '+', 'type': Path}), ('--local-anchors', {'action': 'store_true'}), ('--unique-urls', {'action': 'store_true'}), ('--include-code', {'action': 'store_true'}), ('--readable', {'action': 'store_true', 'help': 'Enforce LINK-5 on authored document references, before renderer URL normalization'}), (('--network', '--check-http'), {'action': 'store_true'}), ('--timeout', {'type': float, 'default': 15}))
class Dispatcher:
	# @used-by :func:`agent_tools.cli.main()`
	def __init__(self, command: str, argv: list[str] | None=None, *, context_default: Path | None=None, root_default: Path | None=None) -> None:
		self.__command = command
		self.__argv = argv
		self.__context_default = context_default
		self.__root_default = root_default
	# @used-by :meth:`Dispatcher.run()`
	def __build_parser(self) -> argparse.ArgumentParser:
		parser = argparse.ArgumentParser(prog=self.__command + '.py')
		ctx_specs = (('root_pos', {'nargs': '?', 'type': Path, 'default': None, 'help': 'Project root directory'}), ('--root', {'type': Path, 'default': self.__root_default, 'help': 'Project root directory'}), ('--config', {'type': Path, 'default': self.__context_default, 'help': 'Context configuration file'}), (('--output', '-o'), {'type': Path, 'help': 'Output path (defaults to \ua66e/0/Context.md)'}), ('--dry-run', {'action': 'store_true', 'help': 'Check inputs without writing output'}))
		specs_map = {'generate_context': ctx_specs, 'safe_commit': (('--repo', {'type': Path, 'required': True}), ('--file', {'action': 'append', 'required': True}), (('--message', '-m'), {'required': True}), ('--execute', {'action': 'store_true'}), ('--worktree', {'action': 'store_true', 'help': 'Commit explicit files in an isolated temporary linked git worktree'})), 'snapshot_draft': (('target', {'type': Path}), ('--turn', {'required': True})), 'validate_anchors': _LINK_SPECS, 'validate_links': _LINK_SPECS, 'validate_statements': (('directory', {'type': Path}),)}
		if 'record_step' == self.__command:
			dfh_add_arg_specs(parser, (('--dir', {'type': Path, 'required': True}), ('--step', {'type': int}), ('--recover', {'type': int}), ('--token', {})))
			for name in ('req', 'res'):
				dfh_add_arg_specs(parser.add_mutually_exclusive_group(), (('--' + name, {}), ('--' + name + '-file', {'type': Path})))
		elif 'validate_step' == self.__command:
			dfh_add_arg_specs(parser, (('--dir', {'type': Path, 'required': True}), ('--file', {'type': Path, 'action': 'append', 'default': []}), ('--strict-sequence', {'action': 'store_true', 'help': 'Fail on missing contiguous steps 1..max(ids) (unless documented in sequence-recovery.json) or orphaned reservations'})))
			dfh_add_arg_specs(parser.add_mutually_exclusive_group(required=True), (('--step', {'type': int}), ('--all', {'action': 'store_true'})))
		elif self.__command in specs_map:
			dfh_add_arg_specs(parser, specs_map[self.__command])
		else:
			raise ValueError(f'Unknown command: {self.__command}')
		return parser
	# @used-by :meth:`Dispatcher.run()`
	def __dispatch(self, parser: argparse.ArgumentParser, args: Any) -> int:
		r = 0
		if 'snapshot_draft' == self.__command:
			from agent_tools.snapshot import snapshot_draft
			print(snapshot_draft(args.target, args.turn))
		elif 'safe_commit' == self.__command:
			self.__run_safe_commit(args)
		elif 'validate_statements' == self.__command:
			self.__run_validate_statements(args)
		elif 'generate_context' == self.__command:
			self.__run_generate_context(args)
		elif 'validate_step' == self.__command:
			from Df.Harness.lib.journal_integrity_ops import dfh_validate_step_cli
			print(dfh_validate_step_cli(args))
		elif 'record_step' == self.__command:
			self.__run_record_step(parser, args)
		else:
			r = self.__run_validate_links(args)
		return r
	# @used-by :meth:`Dispatcher.__run_record_step()`
	def __read_step_payloads(self, parser: argparse.ArgumentParser, args: Any) -> list[str]:
		payload: list[str] = []
		for name in ('req', 'res'):
			path = getattr(args, name + '_file')
			text = dfh_read_input_text(path, encoding='utf-8') if path else getattr(args, name)
			if None is text:
				parser.error(f'Provide --{name} or --{name}-file')
			payload.append(text)
		return payload
	# @used-by :meth:`Dispatcher.__dispatch()`
	def __run_generate_context(self, args: Any) -> None:
		from agent_tools.context import generate
		root = args.root or args.root_pos or self.__root_default or Path('.')
		target, content, sources = generate(root, args.config, args.output, args.dry_run)
		print(f"{len(sources)} sources; {len(content.encode('utf-8'))} bytes; {('dry run' if args.dry_run else 'saved')}: {target}")
	# @used-by :meth:`Dispatcher.__dispatch()`
	def __run_record_step(self, parser: argparse.ArgumentParser, args: Any) -> None:
		from Df.Harness.lib.journal_records import dfh_record_step, dfh_recover_step, dfh_step_errors
		if None is not args.recover:
			if not args.token or any((None is not getattr(args, k) for k in ('req', 'res', 'req_file', 'res_file', 'step'))):
				parser.error('--recover needs --token and cannot be combined with new payloads or --step')
			dfh_recover_step(args.dir, args.recover, args.token)
			step = args.recover
		else:
			if args.token:
				parser.error('--token requires --recover')
			step = dfh_record_step(args.dir, *self.__read_step_payloads(parser, args), target_step=args.step)
		errors = dfh_step_errors(args.dir, step)
		if errors:
			raise ValueError('\n'.join(errors))
		print(f'Journal pair {step} saved and read back exactly')
	# @used-by :meth:`Dispatcher.__dispatch()`
	def __run_safe_commit(self, args: Any) -> None:
		from agent_tools.git_gate import commit
		paths = commit(args.repo, args.file, args.message, args.execute, worktree=args.worktree)
		print(f"{('Committed' if args.execute else 'Checked; commit requires --execute')}: {json.dumps(paths, ensure_ascii=False)}")
	# @used-by :meth:`Dispatcher.__dispatch()`
	def __run_validate_links(self, args: Any) -> int:
		from agent_tools.links import check_network, references, validate_file
		errors, urls, r = ([], [], 0)
		for path in args.targets:
			errors.extend(validate_file(path, local_anchors=args.local_anchors, unique_urls=args.unique_urls, include_code=args.include_code, readable_links=args.readable))
			urls.extend(references(path.read_text(encoding='utf-8'), args.include_code)[0])
		if errors:
			raise ValueError('\n'.join(errors))
		if args.network or 'validate_anchors' == self.__command:
			if 0 >= args.timeout:
				raise ValueError('Timeout must be positive')
			results = check_network(urls, anchors='validate_anchors' == self.__command, timeout=args.timeout)
			dfh_dump_json(results)
			if not results:
				raise ValueError('No matching HTTP(S) links to check')
			if any((item['status'] not in ('http-ok', 'found-in-source') for item in results)):
				r = 2
		if 0 == r:
			print(f'Structural checks passed for {len(args.targets)} explicit files; browser behavior was not checked')
		return r
	# @used-by :meth:`Dispatcher.__dispatch()`
	def __run_validate_statements(self, args: Any) -> None:
		from agent_tools.statements import validate_statements
		errors = validate_statements(args.directory)
		if errors:
			raise ValueError('\n'.join(errors))
		print('Statement and Test.md files exist and are nonempty UTF-8; evidence truth was not checked')
	# @used-by :func:`agent_tools.cli.main()`
	def run(self) -> int:
		parser = self.__build_parser()
		args = parser.parse_args(self.__argv)
		try:
			r = self.__dispatch(parser, args)
		except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
			print(f'ERROR: {exc}', file=sys.stderr)
			r = 1
		return r