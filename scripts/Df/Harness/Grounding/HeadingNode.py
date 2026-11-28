# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-28 "Implement hierarchical mixed-turn DOC-5 parser and problem-issue specification": https://github.com/dmitry-ai/harness/issues/428
# @used-by :class:`Df.Harness.Grounding.HeadingTreeParser.HeadingTreeParser`
# @used-by :class:`Df.Harness.Grounding.MixedTurnProblemSchema.MixedTurnProblemSchema`
# @used-by :class:`Df.Harness.Grounding.StandaloneProblemSchema.StandaloneProblemSchema`
class HeadingNode:
	# @used-by :meth:`Df.Harness.Grounding.HeadingTreeParser.HeadingTreeParser.parse()`
	def __init__(self, level: int, title: str, raw_line: str, line_no: int) -> None:
		self.level = int(level)
		self.title = title
		self.raw_line = raw_line
		self.line_no = int(line_no)
		self.body_lines: list[str] = []
		self.children: list[HeadingNode] = []
	# @used-by :meth:`Df.Harness.Grounding.MixedTurnProblemSchema.MixedTurnProblemSchema.__extract_problem()`
	# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__parse_standalone()`
	# @used-by :meth:`Df.Harness.Grounding.StandaloneProblemSchema.StandaloneProblemSchema.__add_flat_section()`
	# @used-by :meth:`Df.Harness.Grounding.StandaloneProblemSchema.StandaloneProblemSchema.__extract_nested_block()`
	@property
	def full_body(self) -> str:
		parts = list(self.body_lines)
		for child in self.children:
			parts.append(child.raw_line)
			child_body = child.full_body
			if child_body:
				parts.append(child_body)
		return '\n'.join(parts)
	# @used-by :meth:`Df.Harness.Grounding.HeadingTreeParser.HeadingTreeParser.iter_all()`
	def iter_descendants(self) -> list[HeadingNode]:
		out: list[HeadingNode] = []
		for child in self.children:
			out.append(child)
			out.extend(child.iter_descendants())
		return out
