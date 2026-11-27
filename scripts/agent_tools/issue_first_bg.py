# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Issue.BgTaskRecorder import BgTaskRecorder
from Df.Harness.Issue.IssueFirstBgScanner import IssueFirstBgScanner
from Df.Harness.lib.issue import dfh_is_df_issue_command_text
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by unused
def extract_segment_issue_first_events(segment: list[dict], cwd: Path | None, build_write_fn, build_action_fn) -> list[dict]:
	return IssueFirstBgScanner(segment, cwd, build_write_fn, build_action_fn).extract()
# @used-by :meth:`Df.Harness.Platform.Antigravity.TurnScanner.TurnScanner.__handle_system_message()`
def handle_antigravity_bg_task_message(c_str: str, step_idx, seg: dict, parse_command_outcome) -> None:
	BgTaskRecorder(c_str, step_idx, seg, parse_command_outcome).record()
# @used-by unused
def is_df_issue_command_text(cmd: str, direct_re) -> bool:
	return dfh_is_df_issue_command_text(cmd, direct_re)
