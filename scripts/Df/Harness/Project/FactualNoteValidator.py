# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class FactualNoteValidator:
	# @used-by :func:`agent_tools.knowledge.validate_kb_factual_note()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def __init__(self, path: Path | str, text: str) -> None:
		self.__name = Path(path).name
		self.__text = text
	# @used-by :meth:`FactualNoteValidator.issues()`
	def __check_causal_lines(self, out: list[str]) -> None:
		for lineno, line in enumerate((self.__text or '').splitlines(), 1):
			sline = line.strip()
			if not sline or sline.startswith(('#', '```', '|', '>')):
				continue
			m_cause = re.search(r'(?i)\b(?:причиной\s+(?:является|была|было|служит)|первопричина|root\s+cause)\b', sline)
			if m_cause:
				out.append(f"{self.__name}:{lineno}: Causal assertion '{m_cause.group(0)}' requires H-* hypothesis in Analysis.json per DOC-2")
	# @used-by :func:`agent_tools.knowledge.validate_kb_factual_note()`
	# @used-by :meth:`test_df_harness_s11_wave2a_project_ext.DfHarnessS11Wave2aProjectExtTests.test_project_knowledge_classes()`
	def issues(self) -> list[str]:
		from agent_tools.causal_checks import unsupported_probability_claims
		r: list[str] = []
		m_id = re.search(r'\b(?:H|M)-(?:[A-Za-z0-9]+-)*\d+\b', self.__text)
		if m_id:
			r.append(f"{self.__name}: Hypothesis/method identifier '{m_id.group(0)}' forbidden in factual research note; hypotheses must be registered in Analysis.json/Analysis.md per KB-2/DOC-1")
		m_head = re.search(r'(?im)^#{1,6}\s*(?:H-\d+|Гипотез\w*|Hypothes\w*|Причин\w*|Causes?|Misconceptions?|Заблужден\w*|Метод\w*|Methods?)\b', self.__text)
		if m_head:
			r.append(f"{self.__name}: Analytical heading '{m_head.group(0).strip()}' forbidden in factual research note per KB-2/DOC-1")
		if re.search(r'(?i)(?:довод\w*\s+за|arguments?\s+for)\b', self.__text) and re.search(r'(?i)(?:довод\w*\s+против|arguments?\s+against|counterevidence)\b', self.__text):
			r.append(f'{self.__name}: Structured pro/con arguments (DOC-2/DOC-3) forbidden in factual research note')
		r.extend((f'{self.__name}: {c_issue}' for c_issue in unsupported_probability_claims(self.__text)))
		self.__check_causal_lines(r)
		return r
