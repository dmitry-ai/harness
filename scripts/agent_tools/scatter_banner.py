# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
from __future__ import annotations
from Df.Harness.Grounding.ScatterBannerAuditor import ScatterBannerAuditor
from Df.Harness.lib.grounding import SCATTER_BANNER, SCATTER_BANNER_BORDER, SCATTER_BANNER_LINE, SCATTER_BANNER_LINES
# @used-by :mod:`agent_tools.scatter_banner`
def has_leading_scatter_banner(body: str) -> bool:
	return ScatterBannerAuditor.has_leading_banner(body)
# @used-by :mod:`agent_tools.scatter_banner`
def proposes_external_scattering(body: str) -> bool:
	return ScatterBannerAuditor.proposes_external_scattering(body)
# @used-by :mod:`agent_tools.scatter_banner`
def validate_scatter_banners(body: str, *, sections: dict[int, tuple[str, str]] | None=None, blocks: list[dict] | None=None, mode: str='auto') -> list[str]:
	return ScatterBannerAuditor(body, sections=sections, blocks=blocks, mode=mode).audit()
__all__ = ['SCATTER_BANNER', 'SCATTER_BANNER_BORDER', 'SCATTER_BANNER_LINE', 'SCATTER_BANNER_LINES', 'has_leading_scatter_banner', 'proposes_external_scattering', 'validate_scatter_banners']