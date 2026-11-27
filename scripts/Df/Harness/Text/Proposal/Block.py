# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from dataclasses import dataclass, field
from Df.Harness.Text.AddressedSection import AddressedSection
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
@dataclass
class Block(AddressedSection):
	name: str
	number: tuple[int, ...]
	line: int
	end: int
	prefix: str = ''
	body: str = ''
	parent: 'Block | None' = None
	gap: str = ' '
	part: str = ''
	children: list = field(default_factory=list)
