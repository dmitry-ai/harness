# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Grounding.HeadingNode import HeadingNode
from Df.Harness.lib.grounding_md import dfh_mask_fenced_lines
import re
# 2026-11-28 "Implement hierarchical mixed-turn DOC-5 parser and problem-issue specification": https://github.com/dmitry-ai/harness/issues/428
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
# @used-by :func:`Df.Harness.lib.blocked_report_ops._is_doc5_blocker_analysis()`
# @used-by :meth:`Df.Harness.Grounding.CliCommandAuditor.CliCommandAuditor.__extract_recommended()`
# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
# @used-by :meth:`Df.Harness.Grounding.Doc5ReplayAuditor.Doc5ReplayAuditor.__is_problem_response()`
# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__collect_candidates()`
# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.audit()`
class HeadingTreeParser:
	# @used-by :func:`Df.Harness.lib.blocked_report_ops._is_doc5_blocker_analysis()`
	# @used-by :meth:`Df.Harness.Grounding.CliCommandAuditor.CliCommandAuditor.__desc_line_set()`
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
	# @used-by :meth:`Df.Harness.Grounding.Doc5ReplayAuditor.Doc5ReplayAuditor.__is_problem_response()`
	# @used-by :meth:`Df.Harness.Grounding.ProblemReportEvaluator.ProblemReportEvaluator.has_problem_sections()`
	# @used-by :meth:`Df.Harness.Grounding.ProblemTrackAuditor.ProblemTrackAuditor.extract_blocks()`
	# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__parse_standalone()`
	# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__resolve_method_bodies()`
	def __init__(self, text: str) -> None:
		self.__text = text or ''
	# @used-by :meth:`Df.Harness.Grounding.CliCommandAuditor.CliCommandAuditor.__desc_line_set()`
	# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__parse_standalone()`
	@staticmethod
	def iter_all(roots: list[HeadingNode]) -> list[HeadingNode]:
		out: list[HeadingNode] = []
		for node in roots:
			out.append(node)
			out.extend(node.iter_descendants())
		return out
	# @used-by :func:`Df.Harness.lib.blocked_report_ops._is_doc5_blocker_analysis()`
	# @used-by :meth:`Df.Harness.Grounding.CliCommandAuditor.CliCommandAuditor.__desc_line_set()`
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
	# @used-by :meth:`Df.Harness.Grounding.Doc5ReplayAuditor.Doc5ReplayAuditor.__is_problem_response()`
	# @used-by :meth:`Df.Harness.Grounding.ProblemReportEvaluator.ProblemReportEvaluator.has_problem_sections()`
	# @used-by :meth:`Df.Harness.Grounding.ProblemTrackAuditor.ProblemTrackAuditor.extract_blocks()`
	# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__parse_standalone()`
	# @used-by :meth:`Df.Harness.Grounding.ScatterBannerAuditor.ScatterBannerAuditor.__resolve_method_bodies()`
	def parse(self) -> list[HeadingNode]:
		roots: list[HeadingNode] = []
		stack: list[HeadingNode] = []
		for line_no, raw, fenced in dfh_mask_fenced_lines(self.__text):
			m = None if fenced else _HEADING_RE.match(raw.strip())
			if None is not m:
				node = HeadingNode(len(m.group(1)), m.group(2).strip(), raw, line_no)
				while stack and stack[-1].level >= node.level:
					stack.pop()
				(stack[-1].children if stack else roots).append(node)
				stack.append(node)
			elif stack:
				stack[-1].body_lines.append(raw)
		return roots
