# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.lib.grounding import ALLOWED_MATH_GREEK, EN_FUNCTION_WORDS, NON_EN_LATIN_STOPWORDS, dfh_markdown_parser
import re
import unicodedata
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_EXPLICIT_EN_REQ_RE = re.compile('(?i)\\b(?:in\\s+english|translate\\s+to\\s+english|\\u043d\\u0430\\s+\\u0430\\u043d\\u0433\\u043b\\u0438\\u0439\\u0441\\u043a\\u043e\\u043c|\\u043f\\u043e-\\u0430\\u043d\\u0433\\u043b\\u0438\\u0439\\u0441\\u043a\\u043e\\u043c|\\u043f\\u043e-\\u0430\\u043d\\u0433\\u043b\\u0438\\u0439\\u0441\\u043a\\u0438)\\b')
_LOCALE_SCRIPT_MAP = {'ru': 'cyrillic', 'uk': 'cyrillic', 'be': 'cyrillic', 'bg': 'cyrillic', 'sr': 'cyrillic', 'mk': 'cyrillic', 'kk': 'cyrillic', 'ky': 'cyrillic', 'mn': 'cyrillic', 'cyrillic': 'cyrillic', 'el': 'greek', 'greek': 'greek', 'he': 'hebrew', 'iw': 'hebrew', 'hebrew': 'hebrew', 'ar': 'arabic', 'fa': 'arabic', 'ur': 'arabic', 'arabic': 'arabic', 'hi': 'devanagari', 'mr': 'devanagari', 'ne': 'devanagari', 'devanagari': 'devanagari', 'ko': 'hangul', 'hangul': 'hangul', 'ja': 'cjk', 'zh': 'cjk', 'cjk': 'cjk'}
class LocaleVerifier:
	# @used-by :func:`agent_tools.source_grounding.verify_target_locale()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.lint()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_grounding.DfHarnessS11Wave2CCovGroundingTests.test_locale_problem_track_scope_deferral_tier0_and_facade()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_tail.DfHarnessS11Wave2CCovTailTests.test_grounding_ingestor_kb_membership_and_locale_fallback()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_locale_verifier_probability_and_scope_deferral()`
	def __init__(self, text: str, *, target_locale: str='en-US', container_text: str | None=None, is_title: bool=False, allow_explicit_english_request: bool=False, min_target_ratio: float=0.35, min_alpha: int=15, default_locale: str | None=None) -> None:
		self.__text = text
		self.__target_locale = target_locale
		self.__container_text = container_text
		self.__is_title = is_title
		self.__allow_explicit_en = allow_explicit_english_request
		self.__min_target_ratio = min_target_ratio
		self.__min_alpha = min_alpha
		self.__default_locale = default_locale
	# @used-by :meth:`LocaleVerifier.detect_prose_locale()`
	@staticmethod
	def __char_script(ch: str) -> str:
		name = unicodedata.name(ch, '')
		if not name:
			r = 'UNKNOWN'
		else:
			head = name.split()[0]
			r = 'CJK' if head in ('CJK', 'IDEOGRAPHIC', 'HIRAGANA', 'KATAKANA', 'HANGUL') else head
		return r
	# @used-by :meth:`LocaleVerifier.verify()`
	@staticmethod
	def __check_english_target(info: dict, eff_target: str) -> list[dict]:
		r: list[dict] = []
		non_latin = {sc: cnt for sc, cnt in info['script_counts'].items() if 'LATIN' != sc and 2 <= cnt}
		if non_latin:
			desc = ', '.join((f'{sc} ({cnt} chars)' for sc, cnt in sorted(non_latin.items())))
			r.append({'code': 'LOCALE_MISMATCH', 'target_locale': eff_target, 'detected_scripts': non_latin, 'message': f'TEXT-1: Authored prose contains non-Latin script characters [{desc}] in a target "{eff_target}" container; write in {eff_target} and place foreign logs/quotes inside fenced code blocks or blockquotes'})
		elif 'latin-non-en' == info['locale_family'] and 6 <= info['word_count']:
			en_h, non_h, diac = (info['en_hits'], info['non_en_hits'], info['diacritic_words'])
			r.append({'code': 'LOCALE_MISMATCH', 'target_locale': eff_target, 'detected_locale': info['locale_family'], 'message': f'TEXT-1: Authored prose is in a non-English Latin language (en_hits={en_h}, non_en_hits={non_h}, diacritic_words={diac}) in a target "{eff_target}" container'})
		return r
	# @used-by :meth:`LocaleVerifier.verify()`
	@staticmethod
	def __check_script_target(info: dict, eff_target: str, min_alpha: int, min_target_ratio: float) -> list[dict]:
		r: list[dict] = []
		expected_script = eff_target.upper()
		target_chars = info['script_counts'].get(expected_script, 0)
		if min_alpha <= info['total_alpha'] and target_chars / info['total_alpha'] < min_target_ratio:
			dom, total = (info['dominant_script'], info['total_alpha'])
			r.append({'code': 'LOCALE_MISMATCH', 'target_locale': eff_target, 'detected_script': dom, 'message': f'TEXT-1: Target container/request script is {expected_script}, but authored prose is predominantly {dom} ({target_chars}/{total} target script chars)'})
		return r
	# @used-by :meth:`LocaleVerifier.extract_authored_prose()`
	@classmethod
	def __extract_body_prose(cls, text: str) -> str:
		quote_depth = 0
		chunks: list[str] = []
		for token in dfh_markdown_parser().parse(text):
			if 'blockquote_open' == token.type:
				quote_depth += 1
			elif 'blockquote_close' == token.type:
				quote_depth = max(0, quote_depth - 1)
			elif 0 == quote_depth and token.type not in ('fence', 'code_block', 'html_block') and 'inline' == token.type and token.children:
				cls.__extract_inline_chunks(token.children, chunks)
		joined = re.sub('\\u00ab[^\\u00bb]*\\u00bb|\\u201c[^\\u201d]*\\u201d|"[^"\\n]{8,}"', ' ', ' '.join(chunks))
		joined = re.sub('https?://\\S+|file://\\S+', ' ', joined)
		joined = re.sub('(?<![A-Za-z0-9])[A-Za-z]:[/\\\\][^\\s)\\]>]+', ' ', joined)
		joined = re.sub('(?:^|(?<=\\s))/(?:[A-Za-z0-9._-]+/)+[A-Za-z0-9._-]*', ' ', joined)
		joined = re.sub('(?:^|(?<=\\s))(?:/|\\$)[A-Za-z][A-Za-z0-9_:-]*(?=$|\\s)', ' ', joined)
		return ' '.join(joined.split())
	# @used-by :meth:`LocaleVerifier.__extract_body_prose()`
	@staticmethod
	def __extract_inline_chunks(children, chunks: list[str]) -> None:
		link_skip: list[bool] = []
		for child in children:
			if 'link_open' == child.type:
				link_skip.append(str(child.attrGet('href') or '').strip().lower().startswith('slashcommand;'))
			elif 'link_close' == child.type:
				if link_skip:
					link_skip.pop()
			elif 'text' == child.type:
				val = child.content or ''
				if not (any(link_skip) or (link_skip and re.match('^(?:https?://|file://|[A-Za-z]:[/\\\\]|/)', val.strip()))):
					chunks.append(val)
	# @used-by :meth:`LocaleVerifier.__target_from_container()`
	@staticmethod
	def __locale_to_target(locale_code: str | None) -> str | None:
		r: str | None = None
		if isinstance(locale_code, str) and locale_code.strip():
			norm = locale_code.strip().replace('_', '-').lower()
			if 'und' != norm:
				base = norm.split('-', 1)[0]
				r = _LOCALE_SCRIPT_MAP.get(norm) or _LOCALE_SCRIPT_MAP.get(base) or ('en-US' if 'en' == base else norm)
		return r
	# @used-by :meth:`LocaleVerifier.verify()`
	def __resolve_effective_target(self) -> str:
		eff = (self.__target_locale or 'en-US').strip()
		ct = self.__container_text
		if ct and isinstance(ct, str) and ct.strip():
			if self.__allow_explicit_en and _EXPLICIT_EN_REQ_RE.search(ct):
				eff = 'und'
			else:
				eff = self.__target_from_container(eff, self.detect_prose_locale(self.extract_authored_prose(ct, is_title=False)))
		return eff
	# @used-by :meth:`LocaleVerifier.detect_prose_locale()`
	@staticmethod
	def __resolve_locale_family(dominant_script: str, word_count: int, en_hits: int, non_en_hits: int, diacritic_words: int) -> str:
		if 'LATIN' != dominant_script:
			r = dominant_script.lower()
		elif 6 <= word_count and (non_en_hits > en_hits or (0 == en_hits and 2 <= diacritic_words)):
			r = 'latin-non-en'
		else:
			r = 'en'
		return r
	# @used-by :meth:`LocaleVerifier.__resolve_effective_target()`
	def __target_from_container(self, eff: str, c_info: dict) -> str:
		r = eff
		if 'und' == eff.lower():
			c_dom = c_info['dominant_script']
			if c_dom not in ('NONE', 'LATIN') and 6 <= c_info['script_counts'].get(c_dom, 0):
				r = c_dom.lower()
			elif 0 == c_info['total_alpha'] or 0 == c_info.get('word_count', 0):
				r = self.__locale_to_target(self.__default_locale) or eff
		elif 12 <= c_info['total_alpha'] and 'NONE' != c_info['dominant_script']:
			r = c_info['dominant_script'].lower() if 'LATIN' != c_info['dominant_script'] else ('en-US' if 'en' == c_info['locale_family'] else eff)
		return r
	# @used-by :func:`agent_tools.source_grounding.detect_prose_locale()`
	# @used-by :meth:`LocaleVerifier.__resolve_effective_target()`
	# @used-by :meth:`LocaleVerifier.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_locale_verifier_probability_and_scope_deferral()`
	@classmethod
	def detect_prose_locale(cls, prose: str) -> dict:
		script_counts: dict[str, int] = {}
		for ch in prose or '':
			if ch.isalpha() and ch not in ALLOWED_MATH_GREEK:
				sc = cls.__char_script(ch)
				script_counts[sc] = script_counts.get(sc, 0) + 1
		total_alpha = sum(script_counts.values())
		if 0 == total_alpha:
			r = {'dominant_script': 'NONE', 'dominant_ratio': 1.0, 'total_alpha': 0, 'script_counts': {}, 'locale_family': 'und'}
		else:
			dom = max(script_counts.items(), key=lambda item: item[1])[0]
			words = [w.lower() for w in re.findall('[^\\W\\d_]{2,}', prose, flags=re.UNICODE)]
			en_hits = sum((1 for w in words if w in EN_FUNCTION_WORDS))
			non_en = sum((1 for w in words if w in NON_EN_LATIN_STOPWORDS))
			diac = sum((1 for w in words if any((127 < ord(c) and 'LATIN' == cls.__char_script(c) for c in w))))
			fam = cls.__resolve_locale_family(dom, len(words), en_hits, non_en, diac)
			r = {'dominant_script': dom, 'dominant_ratio': script_counts[dom] / total_alpha, 'total_alpha': total_alpha, 'script_counts': script_counts, 'word_count': len(words), 'en_hits': en_hits, 'non_en_hits': non_en, 'diacritic_words': diac, 'locale_family': fam}
		return r
	# @used-by :func:`agent_tools.source_grounding.extract_authored_prose()`
	# @used-by :meth:`LocaleVerifier.__resolve_effective_target()`
	# @used-by :meth:`LocaleVerifier.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_locale_verifier_probability_and_scope_deferral()`
	@classmethod
	def extract_authored_prose(cls, text: str, *, is_title: bool=False) -> str:
		if not isinstance(text, str) or (not text.strip()):
			r = ''
		elif is_title:
			clean = re.sub('`[^`]*`', ' ', text)
			clean = re.sub('\\u00ab[^\\u00bb]*\\u00bb|\\u201c[^\\u201d]*\\u201d|"[^"]*"', ' ', clean)
			r = ' '.join(re.sub('https?://\\S+|file://\\S+', ' ', clean).split())
		else:
			r = cls.__extract_body_prose(text)
		return r
	# @used-by :func:`agent_tools.source_grounding.verify_target_locale()`
	# @used-by :meth:`Df.Harness.Issue.Linter.Linter.lint()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_grounding.DfHarnessS11Wave2CCovGroundingTests.test_locale_problem_track_scope_deferral_tier0_and_facade()`
	# @used-by :meth:`test_df_harness_s11_wave2c_cov_tail.DfHarnessS11Wave2CCovTailTests.test_grounding_ingestor_kb_membership_and_locale_fallback()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_locale_verifier_probability_and_scope_deferral()`
	def verify(self) -> list[dict]:
		r: list[dict] = []
		eff_target = self.__resolve_effective_target()
		info = self.detect_prose_locale(self.extract_authored_prose(self.__text, is_title=self.__is_title))
		if 0 < info['total_alpha'] and 'und' != eff_target.lower():
			r = self.__check_english_target(info, eff_target) if eff_target.lower().startswith('en') else self.__check_script_target(info, eff_target, self.__min_alpha, self.__min_target_ratio)
		return r