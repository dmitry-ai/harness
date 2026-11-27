# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Issue.TurnAuditor import TurnAuditor
from ..git_gate import verify_repo_issue_ready_for_close
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
TurnIssueLifecycleAuditor = TurnAuditor
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
TurnAuditor.bind_runtime_hooks(verify_fn=lambda *a, **kw: verify_repo_issue_ready_for_close(*a, **kw))
__all__ = ('TurnIssueLifecycleAuditor', 'verify_repo_issue_ready_for_close')
