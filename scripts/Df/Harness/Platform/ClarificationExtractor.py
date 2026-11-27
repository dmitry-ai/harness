# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from typing import Any
from Df.Core.lib.array.first import df_last
from Df.Harness.lib.clarifications_ops import dfh_extract_ask_question_clarifications
# 2026-11-26 "Move turn lifecycle subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/383
class ClarificationExtractor:
	# @used-by :func:`agent_tools.platforms.clarifications.extract_ask_question_clarifications()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_platform_subsystem_classes()`
	def __init__(self, segment: list[dict], *, last_fn=df_last) -> None:
		self.__segment = segment
		self.__last_fn = last_fn
	# @used-by :func:`agent_tools.platforms.clarifications.extract_ask_question_clarifications()`
	# @used-by :meth:`test_df_harness_s11_wave2d.DfHarnessS11Wave2DTests.test_platform_subsystem_classes()`
	def run(self) -> list[dict[str, Any]]:
		return dfh_extract_ask_question_clarifications(self.__segment, last_fn=self.__last_fn)
