# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.SendMessageGate import SendMessageGate
NAME = SendMessageGate.NAME
PRIORITY = SendMessageGate.PRIORITY
TOOLS = SendMessageGate.TOOLS
# @used-by :meth:`Df.Harness.Gate.PreToolRegistry.PreToolRegistry.__load_builtin_entry()`
# @used-by :meth:`test_arch_review_cli.ArchReviewCliTests.test_cli_registry_and_send_message_gate_expose_arch_commands_and_block_verdict_duplication()`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return SendMessageGate().check(name, args, payload)
