# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_EQUALITY_RE = re.compile('(?i)\\u0440\\u0430\\u0432\\u043d\\w*\\s+(?:\\u043f\\u0440\\u043e\\u0446\\u0435\\u043d\\u0442\\w*|\\u0432\\u0435\\u0440\\u043e\\u044f\\u0442\\u043d\\u043e\\u0441\\u0442\\w*|\\u043e\\u0446\\u0435\\u043d\\u043a\\w*)|\\u0440\\u0430\\u0432\\u043d\\u043e\\u0432\\u0435\\u0440\\u043e\\u044f\\u0442\\w*|equal\\s+(?:probabilit\\w*|likelihood\\w*|percentage\\w*)|50\\s*[/\u2014\u2013:-]\\s*50')
_IGNORANCE_RE = re.compile('(?i)\\u043e\\u0442\\u0441\\u0443\\u0442\\u0441\\u0442\\u0432\\w*\\s+(?:\\u0434\\u043e\\u043a\\u0430\\u0437\\u0430\\u0442\\u0435\\u043b\\u044c\\w*\\s+)?(?:\\u043e\\u0441\\u043d\\u043e\\u0432\\u0430\\u043d\\w*|\\u0434\\u0430\\u043d\\u043d\\w*|\\u0441\\u0432\\u0438\\u0434\\u0435\\u0442\\u0435\\u043b\\u044c\\u0441\\u0442\\u0432\\w*)|\\u043d\\u0435\\s+(?:\\u0437\\u043d\\u0430\\w*|\\u043d\\u0430\\u0445\\u043e\\u0436\\u0443\\s+\\u043e\\u0441\\u043d\\u043e\\u0432\\u0430\\u043d\\w*)|(?:lack|absence)\\s+of\\s+(?:evidentiary\\s+)?(?:basis|data|evidence|information)|no\\s+(?:evidentiary\\s+)?(?:basis|evidence)')
_LINK_RE = re.compile('(?i)\\u043e\\u0437\\u043d\\u0430\\u0447\\u0430\\w*|\\u0441\\u043b\\u0435\\u0434\\u043e\\u0432\\u0430\\u0442\\w*|\\u043f\\u043e\\u044d\\u0442\\u043e\\u043c\\u0443|\\u043f\\u043e\\u0442\\u043e\\u043c\\u0443\\s+\\u0447\\u0442\\u043e|\\u043f\\u043e\\u0441\\u043a\\u043e\\u043b\\u044c\\u043a\\u0443|because|therefore|implies|mean\\w*')
_NEGATION_RE = re.compile('(?i)\\b(?:\\u043d\\u0435\\s+(?:\\u043e\\u0437\\u043d\\u0430\\u0447\\u0430\\w*|\\u0434\\u043e\\u043a\\u0430\\u0437\\u044b\\u0432\\u0430\\w*|\\u0443\\u0441\\u0442\\u0430\\u043d\\u0430\\u0432\\u043b\\u0438\\u0432\\u0430\\w*|\\u0441\\u043b\\u0435\\u0434\\u0443\\w*)|does\\s+not|cannot\\s+(?:establish|prove|imply))\\b')
class ProbabilityClaimChecker:
	# @used-by :func:`agent_tools.causal_checks.unsupported_probability_claims()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_locale_verifier_probability_and_scope_deferral()`
	def __init__(self, text: str) -> None:
		self.__text = text
	# @used-by :func:`agent_tools.causal_checks.unsupported_probability_claims()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_locale_verifier_probability_and_scope_deferral()`
	def check(self) -> list[str]:
		from agent_tools.text_core import scan
		r: list[str] = []
		for line in (ln for ln in scan(self.__text) if 'prose' == ln.kind):
			value = re.sub('\\[[^\\]]*\\]\\([^)]*\\)', ' ', re.sub('`[^`]*`|\u00ab[^\u00bb]*\u00bb|"[^"\\n]*"', ' ', line.raw))
			if (not _NEGATION_RE.search(value)) and _EQUALITY_RE.search(value) and _IGNORANCE_RE.search(value) and _LINK_RE.search(value):
				r.append(f'CAUSAL-PROBABILITY:{line.no}: absence of discriminating evidence does not establish equal probabilities; state the prior/basis or leave the cause unresolved')
		return r
