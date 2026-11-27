# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from dataclasses import dataclass, field
from Df.Harness.Text.AddressedSection import AddressedSection
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
@dataclass
class Section(AddressedSection):
	part: str
	number: tuple
	title: str | None
	line: int
	level: int
	parent: 'Section | None' = None
	children: list = field(default_factory=list)
	end: int = 0
	anchor: str | None = None
	name: str = ''
