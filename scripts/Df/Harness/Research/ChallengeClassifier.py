# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Research.SitemapExtractor import SitemapExtractor
import html as html_lib
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
_CHALLENGE_ACTIVE_SCRIPT_RE = re.compile('(?is)<script\\b[^>]*>[^<]*\\b_cf_chl_opt\\s*=|<iframe\\b[^>]*\\bsrc=["\\\'][^"\\\']*challenges\\.cloudflare\\.com/cdn-cgi/challenge-platform/')
_CHALLENGE_COPY_RE = re.compile('(?i)verify you are human|checking your browser|checking if the site connection is secure|enable javascript and cookies to continue|please stand by,? while we are checking your browser')
_CHALLENGE_DOM_RE = re.compile('(?is)__LS_SEQ_LOADER__|<[^>]+\\b(?:name=["\\\']?(?:js_challenge|jsc_token|cf_captcha_kind|md_challenge)\\b|id=["\\\']?(?:challenge-form|challenge-running|cf-challenge-running|challenge-error-text|trk_jschal_js)\\b|class=["\\\'][^"\\\']*\\bcf-browser-verification\\b)')
_CHALLENGE_TITLE_RE = re.compile('(?i)^(?:just a moment\\.{0,3}|attention required!\\s*\\|\\s*cloudflare|verify you are human|checking your (?:browser|site connection)(?:\\.{0,3}| before accessing.*)|one more step|ddos-guard|security check|access denied)$')
_CHALLENGE_TOKEN_RE = re.compile('(?i)_cf_chl_opt|challenge-platform|challenges\\.cloudflare\\.com/turnstile|cf-chl-bypass|ray id')
_PASSIVE_JSD_SCRIPT_RE = re.compile('(?is)<script\\b[^>]*\\bsrc=["\\\'][^"\\\']*/cdn-cgi/challenge-platform/[^"\\\']*/(?:jsd|precursor)/[^"\\\']*["\\\'][^>]*>\\s*</script>')
class ChallengeClassifier:
	# @used-by :func:`agent_tools.research.classify_html_challenge()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_html()`
	# @used-by :meth:`Df.Harness.Research.ObservationBundleScanner.ObservationBundleScanner.__scan_raw_html()`
	# @used-by :meth:`Df.Harness.Text.Browser.DomPoller.DomPoller.__is_settled()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_extractor_json_summarizer_and_challenge_classifier()`
	def __init__(self, raw_html: str, *, parsed: dict | None=None, status: int | None=None) -> None:
		self.__raw_html = raw_html
		self.__parsed = parsed
		self.__status = status
	# @used-by :meth:`ChallengeClassifier.__has_challenge_signals()`
	def __extract_title(self, no_comments: str) -> str:
		title_str = (self.__parsed.get('title') or '').strip() if isinstance(self.__parsed, dict) else ''
		if not title_str:
			m_title = re.search('<title\\b[^>]*>(.*?)</title>', no_comments[:16000], flags=re.I | re.S)
			if m_title:
				title_str = ' '.join(html_lib.unescape(re.sub('<[^>]+>', ' ', m_title.group(1))).split())
		return title_str
	# @used-by :meth:`ChallengeClassifier.is_challenge()`
	def __has_challenge_signals(self, no_comments: str, visible_words: int) -> bool:
		non_code_raw = _PASSIVE_JSD_SCRIPT_RE.sub(' ', re.sub('(?is)<(?:code|pre)\\b[^>]*>.*?</(?:code|pre)>', ' ', no_comments))
		if _CHALLENGE_ACTIVE_SCRIPT_RE.search(non_code_raw):
			r = True
		else:
			non_code_html = re.sub('(?is)<(?:script|style|noscript|template)\\b[^>]*>.*?</(?:script|style|noscript|template)>', ' ', non_code_raw)
			non_code_plain = re.sub('(?is)<(?:head|title)\\b[^>]*>.*?</(?:head|title)>|<[^>]+>', ' ', non_code_html)
			title_str = self.__extract_title(no_comments)
			r = bool(
				_CHALLENGE_DOM_RE.search(non_code_html)
				or ('__LS_SEQ_LOADER__' in non_code_raw and 200 > visible_words)
				or (title_str and _CHALLENGE_TITLE_RE.fullmatch(title_str))
				or (self.__status in (401, 403, 429, 503) and (_CHALLENGE_TOKEN_RE.search(non_code_raw) or _CHALLENGE_COPY_RE.search(non_code_plain)))
				or (160 > visible_words and _CHALLENGE_COPY_RE.search(non_code_plain) and (_CHALLENGE_TOKEN_RE.search(non_code_raw) or 60 > visible_words))
			)
		return r
	# @used-by :meth:`ChallengeClassifier.is_challenge()`
	def __is_sitemap_input(self) -> bool:
		if None is not self.__parsed and None is not self.__parsed.get('sitemap'):
			r = True
		else:
			stripped = self.__raw_html.lstrip()
			r = None is self.__parsed and (stripped.startswith('<?xml') or '<urlset' in stripped[:1500] or '<sitemapindex' in stripped[:1500]) and (None is not SitemapExtractor(self.__raw_html).extract())
		return r
	# @used-by :func:`agent_tools.research.classify_html_challenge()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.__extract_html()`
	# @used-by :meth:`Df.Harness.Research.ObservationBundleScanner.ObservationBundleScanner.__scan_raw_html()`
	# @used-by :meth:`Df.Harness.Text.Browser.DomPoller.DomPoller.__is_settled()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_extractor_json_summarizer_and_challenge_classifier()`
	def is_challenge(self) -> bool:
		if not isinstance(self.__raw_html, str) or self.__is_sitemap_input():
			r = False
		else:
			no_comments = re.sub('<!--.*?-->', ' ', self.__raw_html, flags=re.S)
			visible_html = re.sub('(?is)<(?:script|style|noscript|template)\\b[^>]*>.*?</(?:script|style|noscript|template)>', ' ', no_comments)
			visible_plain = re.sub('(?is)<(?:head|title)\\b[^>]*>.*?</(?:head|title)>|<[^>]+>', ' ', visible_html)
			visible_words = len(re.findall('\\w+', html_lib.unescape(visible_plain)))
			if 0 == visible_words or (None is not self.__parsed and None is self.__parsed.get('sitemap') and (0 == self.__parsed.get('word_count', 0))):
				r = True
			else:
				r = self.__has_challenge_signals(no_comments, visible_words)
		return r
