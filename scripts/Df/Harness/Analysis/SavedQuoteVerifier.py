# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from urllib.parse import urldefrag
from Df.Harness.Analysis.HtmlQuoteVerifier import HtmlQuoteVerifier
from Df.Harness.Analysis.SavedSourceLoader import SavedSourceLoader
import re
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class SavedQuoteVerifier:
	# @used-by :func:`agent_tools.evidence.verify_saved_quote()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.PrimaryCapabilities.PrimaryCapabilities.__verify_quote()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_arguments()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def __init__(self, root, source: str, quote: str, *, mode: str='exact', expected_hash=None, require_hash: bool=False, observation=None, documentation: bool=False, exception=None, locator=None, require_bound_observation: bool=False, hash_error: str='Source hash differs from the referenced observation', absent_error: str='Quote is absent from the referenced source fragment', extract_fn=None) -> None:
		self.__root = root
		self.__source = source
		self.__quote = quote
		self.__mode = mode
		self.__expected_hash = expected_hash
		self.__require_hash = require_hash
		self.__observation = observation
		self.__documentation = documentation
		self.__exception = exception
		self.__locator = locator
		self.__require_bound = require_bound_observation
		self.__hash_error = hash_error
		self.__absent_error = absent_error
		self.__extract_fn = extract_fn
	# @used-by :meth:`SavedQuoteVerifier.verify()`
	def __apply_locator(self, text: str) -> str:
		r = text
		if isinstance(self.__locator, dict) and 'text' == self.__locator.get('type'):
			if not self.__contains(text, self.__locator['value']):
				raise ValueError('Exact text locator is absent from primary source')
			r = self.__locator['value']
		elif isinstance(self.__locator, dict) and 'lines' == self.__locator.get('type'):
			match = re.fullmatch('([1-9][0-9]*)-([1-9][0-9]*)', self.__locator['value'])
			if not match or int(match[2]) < int(match[1]) or int(match[2]) > len(text.splitlines()):
				raise ValueError('Line locator must name an existing inclusive line range')
			r = '\n'.join(text.splitlines()[int(match[1]) - 1:int(match[2])])
		return r
	# @used-by :meth:`SavedQuoteVerifier.__apply_locator()`
	# @used-by :meth:`SavedQuoteVerifier.verify()`
	def __contains(self, text: str, needle: str) -> bool:
		if 'exact' == self.__mode:
			r = needle in text
		elif 'whitespace' != self.__mode:
			raise ValueError('quote_match must be exact or whitespace')
		else:
			r = ' '.join(needle.split()) in ' '.join(text.split())
		return r
	# @used-by :func:`agent_tools.evidence.verify_saved_quote()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.PrimaryCapabilities.PrimaryCapabilities.__verify_quote()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_arguments()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_evidence_and_observation_classes()`
	def verify(self) -> dict:
		r = SavedSourceLoader(self.__root, self.__source, self.__observation, need_sections=bool(urldefrag(self.__source)[1] or self.__documentation), extract_fn=self.__extract_fn).load()
		actual_hash = r.get('sha256') or r.get('meta', {}).get('body_sha256')
		if (self.__require_hash or self.__expected_hash) and self.__expected_hash != actual_hash:
			raise ValueError(self.__hash_error)
		if 'html' == r['kind']:
			text = HtmlQuoteVerifier(r, self.__quote, self.__mode, documentation=self.__documentation, exception=self.__exception, observation=self.__observation, require_bound_observation=self.__require_bound).verify()
		else:
			text = r['text']
			if self.__documentation and (not r.get('fragment')) and (None is not self.__locator or self.__contains(text, self.__quote)):
				raise ValueError('No-anchor documentation exception requires a verifiable saved HTML section')
		r['quantity_context'] = r['data']['text'] if 'html' == r['kind'] and (not r.get('fragment')) and (not self.__documentation) else text
		text = self.__apply_locator(text)
		if not self.__contains(text, self.__quote):
			raise ValueError(self.__absent_error)
		return r