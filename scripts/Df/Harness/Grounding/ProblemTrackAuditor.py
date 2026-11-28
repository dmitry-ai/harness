# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Grounding.HeadingTreeParser import HeadingTreeParser
from Df.Harness.Grounding.StandaloneProblemSchema import StandaloneProblemSchema
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_COMPANION_ORDER = ('culprit', 'test_escape', 'journal_reporting')
_CULPRIT_RE = re.compile(r'(?i)(?:\u0432\u0438\u043d\u043e\u0432\u043d\u0438\u043a\w*|\u043a\u0442\u043e\s+(?:\u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u043e\s+)?(?:\u043f\u043e\u0445\u0435\u0440\u0438\u043b|\u0441\u043b\u043e\u043c\u0430\u043b|\u0432\u043d[\u0435\u0451]\u0441|\u0432\u044b\u0437\u0432\u0430\u043b|\u0438\u0441\u043f\u043e\u0440\u0442\u0438\u043b|\u0443\u0440\u043e\u043d\u0438\u043b|\u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043b|\u0437\u0430\u043f\u0443\u0441\u0442\u0438\u043b|\u0432\u044b\u043a\u0430\u0442\u0438\u043b|\u043f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u043b)|\u0430\u0432\u0442\u043e\u0440\w*\s+(?:\u0440\u0435\u0433\u0440\u0435\u0441\u0441\u0438\w*|\u0434\u0435\u0444\u0435\u043a\u0442\w*|\u0441\u0431\u043e\w*|\u0431\u0430\u0433\w*|\u043e\u0448\u0438\u0431\u043a\w*|\u043a\u043e\u043c\u043c\u0438\u0442\w*|\u043f\u043e\u043b\u043e\u043c\u043a\w*|\u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\w*)|\u0430\u0442\u0440\u0438\u0431\u0443\u0446\u0438\w*\s+(?:\u0432\u0438\u043d\u043e\u0432\u043d\u0438\u043a\w*|\u0430\u0432\u0442\u043e\u0440\w*|\u043f\u0440\u043e\u0438\u0441\u0445\u043e\u0436\u0434\u0435\u043d\u0438\w*|\u0432\u043d\u0435\u0441\u0435\u043d\u0438\w*|\u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\w*)|\u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\w*\s+\u0432\u043d\u0435\u0441\u0435\u043d\u0438\w*|\u043f\u0440\u043e\u0438\u0441\u0445\u043e\u0436\u0434\u0435\u043d\u0438\w*\s+(?:\u0434\u0435\u0444\u0435\u043a\u0442\w*|\u0440\u0435\u0433\u0440\u0435\u0441\u0441\u0438\w*|\u0441\u0431\u043e\w*|\u043e\u0448\u0438\u0431\u043a\w*|\u043f\u043e\u043b\u043e\u043c\u043a\w*)|culprit\w*|who\s+(?:specifically\s+)?(?:broke|introduced|caused|shipped|triggered|merged|promoted)|(?:change|provenance|fault|culprit|blame)\s+attribution|introducing\s+(?:commit|agent|change|actor|pr|issue)|regression\s+(?:author|origin|provenance))')
_JOURNAL_RE = re.compile(r'(?i)(?:\u0436\u0443\u0440\u043d\u0430\u043b\w*|\ua66e|\bfile-3\b|\bturn-reservations(?:\.json)?\b|\bstop[- ]?(?:gate|hook|\u0445\u0443\u043a)\b|\u0432\s+\u043e\u0431\u0445\u043e\u0434\s+\u0436\u0443\u0440\u043d\u0430\u043b\w*|\u043e\u0431\u0445\u043e\u0434\w*\s+(?:\u0436\u0443\u0440\u043d\u0430\u043b\w*|\u043f\u0440\u043e\u0442\u043e\u043a\u043e\u043b\w*\s+\u0444\u0438\u043a\u0441\u0430\u0446\u0438\u0438|\u043e\u0442\u0447[\u0435\u0451]\u0442\u043d\u043e\u0441\u0442\w*)|(?:\u043a\u043e\u043d\u0442\u0443\u0440|\u0430\u0443\u0434\u0438\u0442|\u0446\u0435\u043b\u043e\u0441\u0442\u043d\u043e\u0441\u0442\w*|\u043d\u0430\u0440\u0443\u0448\u0435\u043d\u0438\w*)\s+(?:\u0436\u0443\u0440\u043d\u0430\u043b\w*|\u043e\u0442\u0447[\u0435\u0451]\u0442\u043d\u043e\u0441\u0442\w*|\u043d\u0430\u0431\u043b\u044e\u0434\u0430\u0435\u043c\u043e\u0441\u0442\w*|\u0444\u0438\u043a\u0441\u0430\u0446\u0438\w*)|\bjournal(?:ing|ed)?\b|\bunjournaled\b|\bbypass(?:ed|ing)?\s+(?:the\s+)?journal\b|(?:reporting|observability)\s+(?:integrity|audit|bypass|gap|failure))')
_TEST_ESCAPE_RE = re.compile(r'(?i)(?:\u043f\u043e\u0447\u0435\u043c\u0443\s+[^\n.!?]{0,70}(?:\u0442\u0435\u0441\u0442\w*|\u043f\u0440\u043e\u0432\u0435\u0440\u043a\w*|\u0433\u0435\u0439\u0442\w*|\u043b\u0438\u043d\u0442\u0435\u0440\w*|ci\b)|(?:\u0442\u0435\u0441\u0442\w*|\u0430\u0432\u0442\u043e\u0442\u0435\u0441\u0442\w*|\u043f\u0440\u043e\u0432\u0435\u0440\u043a\w*|\u0433\u0435\u0439\u0442\w*|\u043b\u0438\u043d\u0442\u0435\u0440\w*|ci\b)[^\n.!?]{0,50}\u043d\u0435\s+(?:\u043f\u043e\u043c\u0435\u0448\u0430\u043b\w*|\u043f\u043e\u0439\u043c\u0430\u043b\w*|\u043f\u0440\u0435\u0434\u043e\u0442\u0432\u0440\u0430\u0442\u0438\u043b\w*|\u043e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u043b\w*|\u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043b\w*|\u0432\u044b\u044f\u0432\u0438\u043b\w*|\u0443\u043f\u0430\u043b\w*|\u043e\u0431\u043d\u0430\u0440\u0443\u0436\u0438\u043b\w*|\u0441\u0440\u0430\u0431\u043e\u0442\u0430\u043b\w*)|(?:\u043f\u0440\u043e\u0431\u0435\u043b\w*|\u043f\u0440\u043e\u043f\u0443\u0441\u043a\w*|\u0443\u0442\u0435\u0447\u043a\w*|\u0441\u043b\u0435\u043f\w*\s+\u0437\u043e\u043d\w*)\s+(?:\u0432\s+|\u043c\u0438\u043c\u043e\s+|\u0447\u0435\u0440\u0435\u0437\s+)?(?:\u0442\u0435\u0441\u0442\w*|\u043f\u0440\u043e\u0432\u0435\u0440\u043a\w*|\u043f\u043e\u043a\u0440\u044b\u0442\u0438\w*|\u0433\u0435\u0439\u0442\w*)|\u043f\u043e\u043a\u0440\u044b\u0442\u0438\w*\s+\u0442\u0435\u0441\u0442\w*|why\s+[^\n.!?]{0,70}(?:tests?|test\s+suite|checks?|gates?|linters?|ci\b)|(?:tests?|test\s+suite|checks?|gates?|linters?|verification)\s+(?:escape|gap|blind\s*spot|miss(?:ed)?|did\s+not|didn[\'\u2019]t|failed\s+to)|missed\s+by\s+(?:existing\s+)?(?:tests?|checks?|gates?|ci\b)|verification\s+(?:escape|gap|blind\s*spot))')
_TRACK_LABELS = {
	'culprit': 'Culprit & Provenance Attribution (who/what specifically introduced or caused the problem)',
	'journal_reporting': 'Journal & Reporting Integrity (whether outputs/reports bypassed Journal \ua66e / FILE-3 or broke observability)',
	'test_escape': 'Test & Verification Escape (why existing tests, checks, or gates failed to catch or block the culprit)',
}
_TRACK_RES = {'culprit': _CULPRIT_RE, 'journal_reporting': _JOURNAL_RE, 'test_escape': _TEST_ESCAPE_RE}
class ProblemTrackAuditor:
	# @used-by :func:`agent_tools.problem_tracks.companion_track_issues()`
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.__check_problem_blocks()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_grounding.DfHarnessS11Wave2CCovGroundingTests.test_locale_problem_track_scope_deferral_tier0_and_facade()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
	def __init__(self, blocks: list[dict]) -> None:
		self.__blocks = blocks
	# @used-by :meth:`ProblemTrackAuditor.__block_track_matches()`
	@staticmethod
	def __block_scope_text(block: dict) -> str:
		secs = block.get('sections') or {}
		s0, s1 = (secs.get(0, ('', '')), secs.get(1, ('', '')))
		return '\n'.join((str(block.get('header') or ''), str(s0[0] or ''), str(s1[0] or ''), str(s1[1] or '')))
	# @used-by :meth:`ProblemTrackAuditor.audit()`
	@classmethod
	def __block_track_matches(cls, block: dict) -> set[str]:
		scope = cls.__block_scope_text(block)
		return {name for name, pat in _TRACK_RES.items() if pat.search(scope)}
	# @used-by :meth:`ProblemTrackAuditor.audit()`
	@staticmethod
	def __has_distinct_assignment(track_indices: dict[str, list[int]]) -> bool:
		return any((ic != it and ic != ij and it != ij for ic in track_indices['culprit'] for it in track_indices['test_escape'] for ij in track_indices['journal_reporting']))
	# 2026-11-28 "Implement hierarchical mixed-turn DOC-5 parser and problem-issue specification": https://github.com/dmitry-ai/harness/issues/428
	# @used-by :func:`agent_tools.problem_tracks.companion_track_issues()`
	# @used-by :meth:`Df.Harness.Grounding.DfAnalysisValidator.DfAnalysisValidator.__check_problem_blocks()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_grounding.DfHarnessS11Wave2CCovGroundingTests.test_locale_problem_track_scope_deferral_tier0_and_facade()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_df_analysis_problem_tracks_scatter_banner_and_statements()`
	def audit(self) -> list[str]:
		matches = [self.__block_track_matches(blk) for blk in self.__blocks]
		track_indices = {name: [idx for idx, m in enumerate(matches) if name in m] for name in _COMPANION_ORDER}
		errs: list[str] = []
		if 4 > len(self.__blocks):
			errs.append(f'DOC-5 / df-analysis: Complex problem analysis must include at least 4 separate ## 0..## 4 analyses (Primary Problem + separate Culprit/Provenance, Test & Verification Escape, and Journal & Reporting Integrity analyses; found {len(self.__blocks)})')
		for name in _COMPANION_ORDER:
			if not track_indices[name]:
				errs.append(f'DOC-5 / df-analysis: Missing separate ## 0..## 4 companion analysis for {_TRACK_LABELS[name]}')
		if 4 <= len(self.__blocks) and all(track_indices.values()) and (not self.__has_distinct_assignment(track_indices)):
			errs.append('DOC-5 / df-analysis: Culprit/Provenance, Test & Verification Escape, and Journal & Reporting Integrity must each occupy a distinct ## 0..## 4 analysis separate from the Primary Problem and from each other')
		return errs
	# @used-by :func:`agent_tools.problem_tracks.extract_problem_blocks()`
	@classmethod
	def extract_blocks(cls, text: str, _mask_fn=None, _top_head_re=None) -> list[dict]:
		return StandaloneProblemSchema(HeadingTreeParser(text).parse()).extract()['blocks']
