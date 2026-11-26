# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move verification gate subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/381
from Df.Harness.Gate.BulkSourceReadGate import BulkSourceReadGate
MAX_UNPERSISTED_SOURCE_READS = BulkSourceReadGate.MAX_UNPERSISTED_SOURCE_READS
NAME = BulkSourceReadGate.NAME
PRIORITY = BulkSourceReadGate.PRIORITY
TOOLS = BulkSourceReadGate.TOOLS
# @used-by :mod:`agent_tools.gates.bulk_source_read`
def _parse_call_args(raw) -> dict:
	return BulkSourceReadGate.parse_call_args(raw)
# @used-by :mod:`agent_tools.gates.bulk_source_read`
def _recent_segment_rows(t_path: Path) -> list[dict]:
	return BulkSourceReadGate.recent_segment_rows(t_path)
# @used-by :meth:`Df.Harness.Gate.PreToolRegistry.PreToolRegistry.__load_builtin_entry()`
# @used-by :mod:`agent_tools.gates.bulk_source_read`
def check(name: str, args: dict, payload: dict | None=None) -> str | None:
	return BulkSourceReadGate().check(name, args, payload)
__all__ = ['MAX_UNPERSISTED_SOURCE_READS', 'NAME', 'PRIORITY', 'TOOLS', '_parse_call_args', '_recent_segment_rows', 'check']
