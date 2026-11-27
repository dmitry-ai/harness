# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Grounding.Doc5RequirementChecker import Doc5RequirementChecker
import sys
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class Doc5ContextDetector:
	# @used-by :func:`agent_tools.doc5_context.detect_df_analysis_mode()`
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_cli_command_and_doc5_requirement_auditors()`
	def __init__(self, text: str, blocks: list[dict], requests: list | tuple, mode: str, *, turn_context: dict | None, prob_head_re, req_cmd_fn, explicit_fn) -> None:
		self.__text = text
		self.__blocks = blocks
		self.__requests = requests
		self.__mode = mode
		self.__turn_context = turn_context
		self.__prob_head_re = prob_head_re
		self.__req_cmd_fn = req_cmd_fn
		self.__explicit_fn = explicit_fn
	# @used-by :meth:`Doc5ContextDetector.detect()`
	def __requires_doc5(self) -> bool:
		mod = sys.modules.get('agent_tools.doc5_context')
		fn = getattr(mod, 'turn_requires_doc5_problem_analysis', None) if None is not mod else None
		if callable(fn) and not getattr(fn, '_df_default_doc5_facade', False):
			r = bool(fn(self.__turn_context))
		else:
			r = Doc5RequirementChecker(self.__turn_context).is_required()
		return r
	# @used-by :func:`agent_tools.doc5_context.detect_df_analysis_mode()`
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_cli_command_and_doc5_requirement_auditors()`
	def detect(self) -> str:
		if self.__mode in ('general', 'problem'):
			r = self.__mode
		else:
			has_s0_meta = any((0 in b['sections'] and bool(self.__prob_head_re.search(b['sections'][0][0])) for b in self.__blocks))
			has_s1_prob = any((1 in b['sections'] and bool(self.__prob_head_re.search(b['sections'][1][0])) and bool({2, 3, 4} & set(b['sections'])) for b in self.__blocks))
			if has_s0_meta or has_s1_prob or self.__requires_doc5():
				r = 'problem'
			elif self.__req_cmd_fn(self.__requests):
				r = 'problem' if any((0 in b['sections'] for b in self.__blocks)) else 'general'
			else:
				hyps, mets = self.__explicit_fn(self.__text)
				r = 'general' if hyps or mets else 'none'
		return r