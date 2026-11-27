# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from dataclasses import dataclass
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
@dataclass(frozen=True)
class Page:
	url: str
	status: int
	content_type: str
	text: str
