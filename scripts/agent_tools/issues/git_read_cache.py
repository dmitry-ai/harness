# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Issue.ReadCache import ReadCache
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
RepoReadCache = ReadCache
# @used-by :mod:`agent_tools.issues.git_read_cache`
def _parse_porcelain_z(raw: str) -> list[str]:
	return ReadCache.parse_porcelain_z(raw)
__all__ = ('RepoReadCache', '_parse_porcelain_z')
