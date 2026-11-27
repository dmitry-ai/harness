# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Issue.CompetingTurnChecker import CompetingTurnChecker
from Df.Harness.Issue.SessionDetector import SessionDetector
from Df.Harness.Issue.TurnScopeResolver import TurnScopeResolver
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by unused
def detect_active_session(conversation_id: str | None=None, env: dict[str, str] | None=None) -> tuple[str, str]:
	return SessionDetector(conversation_id, env).detect()
# @used-by unused
def has_competing_open_turns(root: Path, current_cid: str) -> bool:
	return CompetingTurnChecker(root, current_cid).has_competing()
# @used-by unused
def select_target_open_turns(open_files: list[tuple[Path, str, str]], active_plat: str, active_cid: str, *, env: dict[str, str] | None=None) -> tuple[list[Path], str, str]:
	return TurnScopeResolver(open_files, active_plat, active_cid, env=env).select()
