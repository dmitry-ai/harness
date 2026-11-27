# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Issue.ScopeCompletenessChecker import ScopeCompletenessChecker
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
# @used-by unused
def find_open_deferred_children(auditor, slug: str) -> dict[int, list[str]]:
	return ScopeCompletenessChecker(auditor, slug).find_open_deferred_children()
# @used-by unused
def flag_parent_and_deferred_children(auditor, code_repo: Path, slug: str, parent_nums: set[int]) -> None:
	ScopeCompletenessChecker(auditor, slug).check(code_repo, parent_nums)
