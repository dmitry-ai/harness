# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Grounding.HeadingNode import HeadingNode
import re
# 2026-11-28 "Implement hierarchical mixed-turn DOC-5 parser and problem-issue specification": https://github.com/dmitry-ai/harness/issues/428
_PART1_RE = re.compile(r'(?i)^(?:I|\u2160|\U0001d678|1)\.?\s+(?:\u0447\u0442\u043e\s+\u0441\u0434\u0435\u043b\u0430\u043d\u043e|\u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u043e|\u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\w*|completed\s+work|work\s+completed|done|what\s+was\s+done)\b')
_PART2_RE = re.compile(r'(?i)^(?:II|\u2161|\U0001d678\U0001d678|2)\.?\s+(?:\u043d\u043e\u0432\u044b\u0435\s+\u043f\u0440\u043e\u0431\u043b\u0435\u043c\u044b|\u043e\u0431\u043d\u0430\u0440\u0443\u0436\u0435\u043d\u043d\u044b\u0435\s+\u043f\u0440\u043e\u0431\u043b\u0435\u043c\u044b|\u0432\u044b\u044f\u0432\u043b\u0435\u043d\u043d\u044b\u0435\s+\u043f\u0440\u043e\u0431\u043b\u0435\u043c\u044b|newly\s+discovered\s+problems|new\s+problems|discovered\s+problems)\b')
_SLOT_LABELS = {1: 'Metadata (Метаданные)', 2: 'Description (Описание)', 3: 'Causes (Причины)', 4: 'Culprit (Виновник)', 5: 'Solutions (Способы устранения)', 6: 'Recommended Plan (Рекомендуемый план устранения)'}
_SLOT_NUM_RE = re.compile(r'^\d+\.([1-6])\.?(?:\s|$)')
_SLOT_PATTERNS = (
	(1, re.compile(r'(?i)(?:\u043c\u0435\u0442\u0430-?\u0434\u0430\u043d\u043d|metadata)')),
	(2, re.compile(r'(?i)(?:\u043e\u043f\u0438\u0441\u0430\u043d|description|\u0441\u0438\u043c\u043f\u0442\u043e\u043c|symptom)')),
	(3, re.compile(r'(?i)(?:\u043f\u0440\u0438\u0447\u0438\u043d|root\s+cause|\bcauses?\b)')),
	(4, re.compile(r'(?i)(?:\u0432\u0438\u043d\u043e\u0432\u043d\u0438\u043a|culprit|\u043f\u0440\u043e\u0438\u0441\u0445\u043e\u0436\u0434\u0435\u043d|provenance)')),
	(6, re.compile(r'(?i)(?:\u043f\u043b\u0430\u043d|\bplan\b)')),
	(5, re.compile(r'(?i)(?:\u0441\u043f\u043e\u0441\u043e\u0431|\u043c\u0435\u0442\u043e\u0434|\u0443\u0441\u0442\u0440\u0430\u043d\u0435\u043d|solution|remediation)')),
)
# @used-by :func:`Df.Harness.lib.blocked_report_ops._is_doc5_blocker_analysis()`
# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
# @used-by :meth:`Df.Harness.Grounding.Doc5ContextDetector.Doc5ContextDetector.detect()`
class MixedTurnProblemSchema:
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.__dispatch_mode()`
	def __init__(self, roots: list[HeadingNode]) -> None:
		self.__roots = roots
	# @used-by :meth:`MixedTurnProblemSchema.__extract_problem()`
	@staticmethod
	def __classify_slot(title: str) -> int | None:
		m = _SLOT_NUM_RE.match(title)
		if None is not m:
			r: int | None = int(m.group(1))
		else:
			r = next((slot for slot, pat in _SLOT_PATTERNS if pat.search(title)), None)
		return r
	# @used-by :meth:`MixedTurnProblemSchema.extract()`
	@classmethod
	def __extract_problem(cls, idx: int, pnode: HeadingNode, errs: list[str], method_bodies: list[str]) -> dict:
		slots: dict[int, tuple[str, str]] = {}
		for sub in pnode.children:
			if 3 != sub.level:
				errs.append(f'[Problem #{idx}] DOC-5 / df-analysis: Subsection "{sub.title}" must use level-3 heading (### {idx}.1..### {idx}.6), found H{sub.level}')
				continue
			slot = cls.__classify_slot(sub.title)
			if None is not slot and slot not in slots:
				slots[slot] = (sub.title, sub.full_body)
		for req in range(1, 7):
			if req not in slots:
				errs.append(f'[Problem #{idx}] DOC-5 / df-analysis: Mixed-turn problem "{pnode.title}" is missing required subsection ### {idx}.{req}. {_SLOT_LABELS[req]}')
		cls.__check_narrative_slots(idx, slots, errs)
		if 5 in slots:
			method_bodies.append(slots[5][1])
		sections = {dst: slots[src] for src, dst in ((1, 0), (2, 1), (3, 2), (5, 4)) if src in slots}
		return {'index': idx, 'header': pnode.title, 'sections': sections, 'slots': slots, 'is_mixed': True}
	# @used-by :meth:`MixedTurnProblemSchema.__extract_problem()`
	@staticmethod
	def __check_narrative_slots(idx: int, slots: dict[int, tuple[str, str]], errs: list[str]) -> None:
		if 4 in slots and 15 > len(slots[4][1].strip()):
			errs.append(f'[Problem #{idx}] DOC-5 / df-analysis: Subsection ### {idx}.4 (Culprit) must document culprit provenance, test escape, and Journal integrity')
		if 6 in slots and 15 > len(slots[6][1].strip()):
			errs.append(f'[Problem #{idx}] DOC-5 / df-analysis: Subsection ### {idx}.6 (Recommended Plan) must provide a concrete remediation plan')
	# @used-by :meth:`MixedTurnProblemSchema.extract()`
	def __check_top_h1(self, errs: list[str]) -> list[HeadingNode]:
		part2_nodes: list[HeadingNode] = []
		for node in self.__roots:
			if 1 != node.level:
				continue
			if _PART2_RE.match(node.title):
				part2_nodes.append(node)
			elif not _PART1_RE.match(node.title):
				errs.append(f'DOC-5 / df-analysis: Extra top-level H1 heading "# {node.title}" is forbidden in mixed-turn reports; keep only "# \U0001d678. Что сделано" and "# \U0001d678\U0001d678. Новые проблемы" at level 1')
		if 1 < len(part2_nodes):
			errs.append('DOC-5 / df-analysis: Mixed-turn report must contain only one "# \U0001d678\U0001d678. Новые проблемы" top-level section')
		return part2_nodes
	# @used-by :func:`Df.Harness.lib.blocked_report_ops._is_doc5_blocker_analysis()`
	# @used-by :meth:`Df.Harness.Grounding.Doc5ContextDetector.Doc5ContextDetector.detect()`
	# @used-by :meth:`Df.Harness.Grounding.Doc5ReplayAuditor.Doc5ReplayAuditor.__is_problem_response()`
	# @used-by :meth:`Df.Harness.Grounding.ProblemReportEvaluator.ProblemReportEvaluator.has_problem_sections()`
	@staticmethod
	def has_mixed_sections(roots: list[HeadingNode]) -> bool:
		return any((1 == n.level and bool(_PART2_RE.match(n.title)) for n in roots))
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.__dispatch_mode()`
	def extract(self) -> dict:
		errs: list[str] = []
		blocks: list[dict] = []
		method_bodies: list[str] = []
		p2_nodes = self.__check_top_h1(errs)
		if p2_nodes:
			p_nodes = [ch for ch in p2_nodes[0].children if 2 == ch.level]
			for bad in [ch for ch in p2_nodes[0].children if 2 != ch.level]:
				errs.append(f'DOC-5 / df-analysis: Problem heading "{bad.title}" under "# \U0001d678\U0001d678. Новые проблемы" must be level-2 (## N.), found H{bad.level}')
			if not p_nodes:
				errs.append('DOC-5 / df-analysis: "# \U0001d678\U0001d678. Новые проблемы" must contain at least one level-2 problem block (## 1. ...)')
			for idx, pnode in enumerate(p_nodes, 1):
				blocks.append(self.__extract_problem(idx, pnode, errs, method_bodies))
		return {'blocks': blocks, 'errors': errs, 'method_bodies': method_bodies}
