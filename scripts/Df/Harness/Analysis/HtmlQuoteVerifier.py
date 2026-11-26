# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class HtmlQuoteVerifier:
	# @used-by :func:`agent_tools.evidence.verify_html_quote_scope()`
	# @used-by :meth:`Df.Harness.Analysis.SavedQuoteVerifier.SavedQuoteVerifier.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	def __init__(self, saved: dict, quote: str, mode: str='exact', *, documentation: bool=False, exception=None, observation=None, require_bound_observation: bool=False) -> None:
		self.__saved = saved
		self.__quote = quote
		self.__mode = mode
		self.__documentation = documentation
		self.__exception = exception
		self.__observation = observation
		self.__require_bound = require_bound_observation
	# @used-by :meth:`HtmlQuoteVerifier.verify()`
	def __check_doc_exception(self, data: dict) -> str:
		if not isinstance(self.__exception, dict):
			raise ValueError('Documentation without an anchor needs a named saved section')
		if self.__require_bound and (not self.__observation or self.__exception.get('observation') != self.__observation):
			raise ValueError('Documentation anchor exception must bind the exact primary observation')
		matches = [s for s in data['sections'] if s['text'] == self.__exception.get('section')]
		if 1 != len(matches):
			raise ValueError('Documentation section is missing or ambiguous')
		if matches[0].get('section_anchors') or matches[0].get('anchor') or any((self.__contains(s) for ca in matches[0].get('container_anchors') or [] for s in data['anchor_content'].get(ca, []))):
			raise ValueError('Documentation section has an available anchor; use its verified address')
		if not self.__contains(matches[0]['content']):
			raise ValueError('Quote does not match the documented section')
		return matches[0]['content']
	# @used-by :meth:`HtmlQuoteVerifier.verify()`
	def __check_fragment(self, data: dict, fragment: str) -> str:
		if fragment not in data['anchors'] or fragment in data.get('ambiguous_anchors', []):
			raise ValueError('Primary anchor is absent or ambiguous')
		scopes = [h['content'] for h in data['sections'] if fragment in (h.get('section_anchors') or ([h['anchor']] if h.get('anchor') else []))] or data['anchor_content'].get(fragment, [])
		if not scopes or not any((self.__contains(s) for s in scopes)):
			raise ValueError('Quote does not belong to the primary anchor')
		return '\n'.join(scopes)
	# @used-by :meth:`HtmlQuoteVerifier.verify()`
	def __check_plain(self, data: dict, is_md: bool) -> str:
		raw = self.__saved['raw']
		if is_md:
			if not (self.__contains(raw) or self.__contains(data['text'])):
				raise ValueError('Quote is absent from the saved page')
			r = raw if self.__contains(raw) else data['text']
		else:
			combined = data['text'] + '\n' + raw
			if not (self.__contains(data['text']) or self.__contains(raw) or self.__contains(combined)):
				raise ValueError('Quote is absent from the saved page')
			r = combined
		return r
	# @used-by :meth:`HtmlQuoteVerifier.__check_doc_exception()`
	# @used-by :meth:`HtmlQuoteVerifier.__check_fragment()`
	# @used-by :meth:`HtmlQuoteVerifier.__check_plain()`
	def __contains(self, text: str) -> bool:
		if 'exact' == self.__mode:
			r = self.__quote in text
		elif 'whitespace' != self.__mode:
			raise ValueError('quote_match must be exact or whitespace')
		else:
			r = ' '.join(self.__quote.split()) in ' '.join(text.split())
		return r
	# @used-by :func:`agent_tools.evidence.verify_html_quote_scope()`
	# @used-by :meth:`Df.Harness.Analysis.SavedQuoteVerifier.SavedQuoteVerifier.verify()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_evidence_manifest_and_loader_paths()`
	def verify(self) -> str:
		from agent_tools.research import classify_html_challenge
		data, fragment = (self.__saved['data'], self.__saved.get('fragment'))
		is_md = bool(self.__saved.get('is_markdown'))
		meta_status = (self.__saved.get('meta') or {}).get('status')
		if data.get('browser_check_required') or ((not is_md) and (not self.__saved.get('challenge_checked')) and classify_html_challenge(self.__saved['raw'], parsed=data, status=meta_status)):
			raise ValueError('Challenge page requires browser verification; it cannot establish the intended page content')
		if fragment:
			r = self.__check_fragment(data, fragment)
		elif not self.__documentation:
			r = self.__check_plain(data, is_md)
		else:
			r = self.__check_doc_exception(data)
		return r