# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Harness.lib.cli_domain_ops import OPERATION_HANDLERS
from Df.Harness.lib.completion_core import COMMANDS as COMPLETION_COMMANDS
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class DomainExecutor:
	# @used-by :func:`agent_tools.operations.execute()`
	def __init__(self, args: Any, *, completion_execute_fn=None, handlers: dict[str, Any] | None=None) -> None:
		self.__args = args
		self.__completion_execute_fn = completion_execute_fn
		self.__handlers = handlers if None is not handlers else OPERATION_HANDLERS
	# @used-by :func:`agent_tools.operations.execute()`
	def run(self) -> Any:
		command = self.__args.command
		if command in COMPLETION_COMMANDS:
			if None is not self.__completion_execute_fn:
				r = self.__completion_execute_fn(self.__args)
			else:
				from Df.Harness.lib.completion_commands import dfh_execute_completion
				r = dfh_execute_completion(self.__args)
		else:
			handler = self.__handlers.get(command)
			if None is handler:
				raise ValueError('Unknown workflow command')
			r = handler(self.__args)
		return r