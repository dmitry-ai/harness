# 2026-11-25 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from __future__ import annotations
from Df.Harness.Grounding.ProblemTrackAuditor import ProblemTrackAuditor
# @used-by unused
def companion_track_issues(blocks: list[dict]) -> list[str]:
	return ProblemTrackAuditor(blocks).audit()
# @used-by unused
def extract_problem_blocks(text: str, mask_fn, top_head_re) -> list[dict]:
	return ProblemTrackAuditor.extract_blocks(text, mask_fn, top_head_re)