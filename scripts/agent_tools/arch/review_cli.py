# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# "Add arch-auditor subagent role and content-addressed review CLI":
# https://github.com/dmitry-ai/harness/issues/361
from __future__ import annotations
from collections.abc import Callable
# 2026-11-27 "Reorganize Harness scripts into single-class Mage2Pro modules": https://github.com/dmitry-ai/harness/issues/338
from Df.Harness.Arch.ReviewCli import ReviewCli
# @used-by :func:`Df.Harness.lib.cli_registry_defs._register_builtins()`
# @used-by :meth:`test_df_harness_s11_wave2e_arch.DfHarnessArchWave2eTests.test_review_cli_registers_and_executes_all_arch_commands()`
# @used-by :mod:`agent_tools.arch.review_cli`
def register_arch_commands(register_fn: Callable) -> None:
	ReviewCli().register(register_fn)
__all__ = ['register_arch_commands']
