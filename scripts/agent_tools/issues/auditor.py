# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Issue.TurnAuditor import TurnAuditor
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
TurnIssueLifecycleAuditor = TurnAuditor
__all__ = ('TurnIssueLifecycleAuditor',)
