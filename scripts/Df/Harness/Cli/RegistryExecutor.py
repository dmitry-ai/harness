# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any, Callable
from Df.Harness.lib.cli_registry_defs import REGISTRY, dfh_ensure_builtin_plugins
import sys
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class RegistryExecutor:
	# @used-by :func:`agent_tools.cli_registry.dispatch_registered()`
	# @used-by :func:`agent_tools.cli_registry.execute_registered()`
	def __init__(self, args: Any, *, mode: str='execute', dump_fn: Callable | None=None, exit_fn: Callable | None=None) -> None:
		self.__args = args
		self.__mode = mode
		self.__dump_fn = dump_fn
		self.__exit_fn = exit_fn
	# @used-by :meth:`RegistryExecutor.run()`
	def __dispatch(self, entry: dict | None) -> tuple[bool, int | None]:
		if None is entry:
			r: tuple[bool, int | None] = (False, None)
		else:
			res = entry['handler'](self.__args)
			txt_fn = entry.get('text_fn')
			txt = txt_fn(res, self.__args) if txt_fn else None
			if None is txt and None is not self.__dump_fn:
				self.__dump_fn(res)
			elif None is not txt:
				sys.stdout.write(txt)
			ec_fn = entry.get('exit_code_fn')
			code = int(ec_fn(res)) if ec_fn else (self.__exit_fn(res) if None is not self.__exit_fn else 0)
			r = (True, code)
		return r
	# @used-by :meth:`RegistryExecutor.run()`
	def __execute(self, entry: dict | None) -> tuple[bool, dict | None, int | None]:
		if None is entry:
			r: tuple[bool, dict | None, int | None] = (False, None, None)
		else:
			res = entry['handler'](self.__args)
			ec_fn = entry.get('exit_code_fn')
			r = (True, res, int(ec_fn(res)) if ec_fn else None)
		return r
	# @used-by :func:`agent_tools.cli_registry.dispatch_registered()`
	# @used-by :func:`agent_tools.cli_registry.execute_registered()`
	def run(self) -> Any:
		dfh_ensure_builtin_plugins()
		entry = REGISTRY.get(self.__args.command)
		return self.__dispatch(entry) if 'dispatch' == self.__mode else self.__execute(entry)