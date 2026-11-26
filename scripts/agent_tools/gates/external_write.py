# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.ExternalWriteGate import ExternalWriteGate
EXTERNAL_WRITE_INTENT_RE = ExternalWriteGate.EXTERNAL_WRITE_INTENT_RE
NAME = ExternalWriteGate.NAME
PRIORITY = ExternalWriteGate.PRIORITY
TOOLS = ExternalWriteGate.TOOLS
# @used-by :mod:`agent_tools.gates.external_write`
def _upwork_project_root_for_command(cmd: str) -> Path | None:
	return ExternalWriteGate.upwork_project_root_for_command(cmd)
# @used-by :meth:`Df.Harness.Gate.PreToolRegistry.PreToolRegistry.__load_builtin_entry()`
# @used-by :mod:`agent_tools.gates.external_write`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return ExternalWriteGate().check(name, args, payload)
__all__ = ['EXTERNAL_WRITE_INTENT_RE', 'NAME', 'PRIORITY', 'TOOLS', '_upwork_project_root_for_command', 'check']
