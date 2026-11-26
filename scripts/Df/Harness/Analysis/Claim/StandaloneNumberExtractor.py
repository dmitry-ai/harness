# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class StandaloneNumberExtractor:
	# @used-by :func:`agent_tools.claims.standalone_numbers()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_numbers()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	def __init__(self, text) -> None:
		self.__text = text
	# @used-by :func:`agent_tools.claims.standalone_numbers()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__check_numbers()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_claim_arithmetic_and_grounding_classes()`
	def extract(self) -> set[str]:
		if not isinstance(self.__text, str) or not self.__text:
			r: set[str] = set()
		else:
			from agent_tools.markdown_links import numeric_text
			cleaned = numeric_text(self.__text)
			cleaned = re.sub('https?://\\S+', ' ', cleaned)
			cleaned = re.sub('\\b[a-f0-9]{8,64}\\b', ' ', cleaned, flags=re.I)
			cleaned = re.sub('\\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\\b', ' ', cleaned)
			cleaned = re.sub('(?m)^\\s*#{1,6}\\s+\\d+(?:\\.\\d+)*\\.?\\b', ' ', cleaned)
			cleaned = re.sub('(?m)^\\s*\\d+(?:\\.\\d+)*[.)]\\s+', ' ', cleaned)
			cleaned = re.sub('\u00a7+\\s*\\d+(?:\\.\\d+)*', ' ', cleaned)
			tokens = re.findall('(?<![A-Za-z0-9_./~+-])\\d+(?:[.,]\\d+)*(?![A-Za-z0-9_./~+-])', cleaned)
			r = {t.replace(',', '.') for t in tokens}
		return r