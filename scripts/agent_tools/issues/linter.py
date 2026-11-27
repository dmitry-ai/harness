# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.text.n.normalize import df_normalize
from Df.Harness.Issue.Linter import Linter, REPO_RE
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
IssueMarkdownLinter = Linter
Linter.bind_normalize_fn(lambda text: df_normalize(text))
# @used-by :meth:`test_arch_spec_and_triggers.ArchSpecAndTriggersTests.test_issue_linter_enforces_architecture_pattern_specs_on_structural_parent_issues()`
# @used-by :mod:`agent_tools.issues.linter`
def _check_arch_policy(text: str, out: list[dict[str, Any]]) -> None:
	Linter.check_arch_policy(text, out)
__all__ = ('IssueMarkdownLinter', 'REPO_RE', '_check_arch_policy')
