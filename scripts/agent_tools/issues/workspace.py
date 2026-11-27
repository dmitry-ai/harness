# 2026-11-23 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Issue.EvidenceWorkspace import EvidenceWorkspace, _SKIP_TURN_SUFFIXES
from Df.Harness.Issue.RepoLocator import V2_CODE_RELS
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
IssueEvidenceWorkspace = EvidenceWorkspace
_V2_CODE_RELS = V2_CODE_RELS
__all__ = ('IssueEvidenceWorkspace', '_SKIP_TURN_SUFFIXES', '_V2_CODE_RELS')
