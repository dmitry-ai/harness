# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
from Df.Harness.Completion.TurnRouter import TurnRouter
from Df.Harness.lib.turn_routing_ops import dfh_read_optional_transcript_rows as _read_optional_transcript_rows
# @used-by :meth:`test_turn_routing_and_handoff_m6.TurnRoutingAndHandoffM6Tests.test_stop_gate_deterministic_priority_prevents_alphabetical_shadowing()`
def resolve_active_turn_state(t_dir: Path, session_id: str, last_user_step: int, *, rows: list[dict] | None=None, user_text: str | None=None) -> dict | None:
	return TurnRouter(t_dir, session_id, last_user_step, rows=rows, user_text=user_text, mode='active').run()
# @used-by unused
def resolve_handoff_target_root(t_dir: Path, session_id: str, last_user_step: int, *, brain_dir: Path | None=None, conversations_dir: Path | None=None, t_path: Path | None=None, rows: list[dict] | None=None, user_text: str | None=None) -> Path | None:
	return TurnRouter(t_dir, session_id, last_user_step, rows=rows, user_text=user_text, mode='handoff', brain_dir=brain_dir, conversations_dir=conversations_dir, t_path=t_path).run()