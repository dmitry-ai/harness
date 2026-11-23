# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add deterministic FIFO repository landing lease with reactive wait":
# https://github.com/dmitry-ai/harness/issues/163
from __future__ import annotations
from pathlib import Path
from typing import Callable
import sys
from .cli_common import add_arg_specs
_REGISTRY: dict[str, dict] = {}
def _ensure_builtin_plugins() -> None:
	if not _REGISTRY:
		_register_builtins()
def _exec_land_acquire(args) -> dict:
	from .landing_lease import acquire_lease
	return acquire_lease(args.repo, owner=args.owner, wait=bool(args.wait), timeout=args.timeout, ttl=args.ttl, poll_interval=args.poll_interval)
def _exec_land_release(args) -> dict:
	from .landing_lease import release_lease
	return release_lease(args.repo, owner=args.owner, force=bool(args.force))
def _exec_land_status(args) -> dict:
	from .landing_lease import lease_status
	return lease_status(args.repo)
def _exec_run_tests(args) -> dict:
	from .suite_runner import run_test_suite
	return run_test_suite(args.target, workers=args.workers, module_timeout=args.module_timeout, failfast=not args.no_failfast, pattern=args.pattern, modules=args.module)
def _format_run_tests(res: dict, args) -> str | None:
	if 'json' == args.format:
		r = None
	else:
		from .suite_runner import format_text_report
		r = format_text_report(res)
	return r
def _register_builtins() -> None:
	register_command('land-acquire', 'Acquire FIFO landing lease for a Git repository', (('repo', {'type': Path}), ('--owner', {'help': 'Lease owner identifier'}), ('--wait', {'action': 'store_true', 'help': 'Wait reactively in FIFO queue until acquired'}), ('--timeout', {'type': float, 'default': 600.0}), ('--ttl', {'type': float, 'default': 600.0}), ('--poll-interval', {'type': float, 'default': 2.0})), _exec_land_acquire)
	register_command('land-release', 'Release FIFO landing lease for a Git repository', (('repo', {'type': Path}), ('--owner', {'help': 'Lease owner identifier'}), ('--force', {'action': 'store_true'})), _exec_land_release)
	register_command('land-status', 'Inspect FIFO landing lease and queue for a Git repository', (('repo', {'type': Path}),), _exec_land_status)
	register_command('run-tests', 'Run unittest modules in parallel with fail-fast and per-module watchdog timeout', (('target', {'nargs': '?', 'type': Path, 'help': 'Optional tests directory or repo root'}), ('--workers', {'type': int, 'help': 'Worker process count (default: half logical CPUs, 2..8)'}), ('--module-timeout', {'type': float, 'default': 300.0, 'help': 'Per-module timeout in seconds (default: 300)'}), ('--no-failfast', {'action': 'store_true', 'help': 'Run all modules instead of stopping on first failure'}), (('-p', '--pattern'), {'default': 'test_*.py', 'help': 'Test filename glob pattern (default: test_*.py)'}), ('--module', {'action': 'append', 'default': [], 'help': 'Optional specific test module filter; repeatable'}), ('--format', {'choices': ('text', 'json'), 'default': 'text', 'help': 'Output format (default: text)'})), _exec_run_tests, exit_code_fn=lambda res: int(res['exit_code']), text_fn=_format_run_tests)
def add_registered_parsers(sub) -> None:
	_ensure_builtin_plugins()
	for name, entry in sorted(_REGISTRY.items()):
		add_arg_specs(sub.add_parser(name, help=entry['help']), entry['specs'])
def dispatch_registered(args, dump_fn: Callable, exit_fn: Callable) -> tuple[bool, int | None]:
	_ensure_builtin_plugins()
	entry = _REGISTRY.get(args.command)
	if None is entry:
		r = (False, None)
	else:
		res = entry['handler'](args)
		txt_fn = entry.get('text_fn')
		txt = txt_fn(res, args) if txt_fn else None
		if None is txt:
			dump_fn(res)
		else:
			sys.stdout.write(txt)
		ec_fn = entry.get('exit_code_fn')
		r = (True, int(ec_fn(res)) if ec_fn else exit_fn(res))
	return r
def execute_registered(args) -> tuple[bool, dict | None, int | None]:
	_ensure_builtin_plugins()
	entry = _REGISTRY.get(args.command)
	if None is entry:
		r = (False, None, None)
	else:
		res = entry['handler'](args)
		ec_fn = entry.get('exit_code_fn')
		r = (True, res, int(ec_fn(res)) if ec_fn else None)
	return r
def registered_commands() -> tuple[str, ...]:
	_ensure_builtin_plugins()
	return tuple(sorted(_REGISTRY))
def register_command(name: str, help_text: str, specs: tuple | list, handler: Callable, *, exit_code_fn: Callable | None=None, text_fn: Callable | None=None) -> None:
	_REGISTRY[name] = {'help': help_text, 'specs': specs, 'handler': handler, 'exit_code_fn': exit_code_fn, 'text_fn': text_fn}
