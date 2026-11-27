# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Issue.IssueFirstInheritor import IssueFirstInheritor
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by unused
def has_inherited_open_parent_issue(payload: dict, info: dict, cwd: Path | None, t_path: Path | None) -> bool:
	return IssueFirstInheritor(payload, info, cwd, t_path).has_inherited_open_parent()
# @used-by unused
def missing_transcript_issue_first_error(pending_targets: list[tuple[Path, dict]], payload: dict, cwd: Path | None) -> str | None:
	return IssueFirstInheritor.missing_transcript_error(pending_targets, payload, cwd)
