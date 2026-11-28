# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Grounding.HeadingNode import HeadingNode
import re
# 2026-11-28 "Implement hierarchical mixed-turn DOC-5 parser and problem-issue specification": https://github.com/dmitry-ai/harness/issues/428
_NUM_SEC_RE = re.compile(r'^([0-4])\.?(?:\s+(.*))?$')
# @used-by :func:`Df.Harness.lib.blocked_report_ops._is_doc5_blocker_analysis()`
# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
# @used-by :meth:`Df.Harness.Grounding.Doc5ReplayAuditor.Doc5ReplayAuditor.__is_problem_response()`
# @used-by :meth:`Df.Harness.Grounding.ProblemTrackAuditor.ProblemTrackAuditor.extract_blocks()`
# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.audit()`
class StandaloneProblemSchema:
	# @used-by :func:`Df.Harness.lib.blocked_report_ops._is_doc5_blocker_analysis()`
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
	# @used-by :meth:`Df.Harness.Grounding.ProblemTrackAuditor.ProblemTrackAuditor.extract_blocks()`
	# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__resolve_method_bodies()`
	# @used-by :meth:`StandaloneProblemSchema.has_any_problem_block()`
	def __init__(self, roots: list[HeadingNode]) -> None:
		self.__roots = roots
	# @used-by :meth:`StandaloneProblemSchema.__process_h1()`
	@staticmethod
	def __add_flat_section(blocks: list[dict], errs: list[str], method_bodies: list[str], match: re.Match[str], node: HeadingNode, state: dict) -> None:
		num = int(match.group(1))
		if not state['flat_reported']:
			errs.append(f'DOC-5 / df-analysis: Flat level-1 subsection heading "# {node.title}" is forbidden; nest sections as ## 0..## 4 inside each level-1 track heading (# <Track>)')
			state['flat_reported'] = True
		if not blocks or 0 == num or num in blocks[-1]['sections'] or state['pending']:
			blocks.append({'header': state['pending'], 'sections': {}, 'is_flat': True})
			state['pending'] = ''
		body = node.full_body
		blocks[-1]['sections'][num] = ((match.group(2) or '').strip(), body)
		if 4 == num:
			method_bodies.append(body)
	# @used-by :meth:`StandaloneProblemSchema.__process_h1()`
	@staticmethod
	def __extract_nested_block(node: HeadingNode) -> dict | None:
		sections: dict[int, tuple[str, str]] = {}
		for child in node.children:
			if 2 != child.level:
				continue
			m = _NUM_SEC_RE.match(child.title)
			if None is not m:
				sections[int(m.group(1))] = ((m.group(2) or '').strip(), child.full_body)
		return {'header': node.title, 'sections': sections, 'is_nested': True} if sections else None
	# @used-by :meth:`StandaloneProblemSchema.extract()`
	@classmethod
	def __process_h1(cls, node: HeadingNode, blocks: list[dict], errs: list[str], method_bodies: list[str], state: dict) -> None:
		m_num = _NUM_SEC_RE.match(node.title)
		if None is not m_num:
			cls.__add_flat_section(blocks, errs, method_bodies, m_num, node, state)
		else:
			nested = cls.__extract_nested_block(node)
			if None is nested:
				state['pending'] = node.title
			else:
				blocks.append(nested)
				if 4 in nested['sections']:
					method_bodies.append(nested['sections'][4][1])
				state['pending'] = ''
	# @used-by :func:`Df.Harness.lib.blocked_report_ops._is_doc5_blocker_analysis()`
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
	# @used-by :meth:`Df.Harness.Grounding.ProblemTrackAuditor.ProblemTrackAuditor.extract_blocks()`
	# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__resolve_method_bodies()`
	def extract(self) -> dict:
		blocks: list[dict] = []
		errs: list[str] = []
		method_bodies: list[str] = []
		state = {'pending': '', 'flat_reported': False}
		for node in self.__roots:
			if 1 == node.level:
				self.__process_h1(node, blocks, errs, method_bodies, state)
		return {'blocks': blocks, 'errors': errs, 'method_bodies': method_bodies}
	# @used-by :meth:`Df.Harness.Grounding.Doc5ReplayAuditor.Doc5ReplayAuditor.__is_problem_response()`
	@classmethod
	def has_any_problem_block(cls, roots: list[HeadingNode]) -> bool:
		return any((0 in blk['sections'] for blk in cls(roots).extract()['blocks']))
