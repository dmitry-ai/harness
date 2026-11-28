# 2026-11-28 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit
import json
# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
class UserUrlPolicy:
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_external_refs()`
	# @used-by :meth:`UserUrlPolicy.from_evidence_dir()`
	def __init__(self, *, working_apex_hosts: Iterable[str]=(), failed_apex_hosts: Iterable[str]=(), client_site_hosts: Iterable[str]=()) -> None:
		working = frozenset((UserUrlPolicy.apex_host(h) for h in working_apex_hosts if h))
		failed = frozenset((UserUrlPolicy.apex_host(h) for h in failed_apex_hosts if h)) - working
		clients = frozenset((UserUrlPolicy.apex_host(h) for h in client_site_hosts if h))
		self.__working_apex_hosts, self.__failed_apex_hosts, self.__client_site_hosts = (working, failed, clients)
	# @used-by :meth:`UserUrlPolicy.classify_observation()`
	@staticmethod
	def __is_root_path(path: str, query: str) -> bool:
		return path in ('', '/') and (not query)
	# @used-by :meth:`UserUrlPolicy.collect_client_site_hosts()`
	@staticmethod
	def __read_json_dict(path: Path) -> dict:
		r: dict = {}
		if path.is_file():
			try:
				data = json.loads(path.read_text(encoding='utf-8-sig'))
				if isinstance(data, dict):
					r = data
			except (OSError, ValueError):
				pass
		return r
	# @used-by :meth:`UserUrlPolicy.strip_www()`
	@staticmethod
	def __slice_www_prefix(url: str) -> str:
		sep = url.find('://')
		r = url
		if 0 <= sep:
			auth_start = sep + 3
			tail = url[auth_start:]
			stops = [i for i in (tail.find('/'), tail.find('?'), tail.find('#')) if 0 <= i]
			auth_end = auth_start + (min(stops) if stops else len(tail))
			at_pos = url.rfind('@', auth_start, auth_end)
			host_start = at_pos + 1 if 0 <= at_pos else auth_start
			if 'www.' == url[host_start:host_start + 4].lower():
				r = url[:host_start] + url[host_start + 4:]
		return r
	# @used-by :meth:`Df.Harness.Grounding.EvidenceBundleIngestor.EvidenceBundleIngestor.__expand_non_www_aliases()`
	# @used-by :meth:`Df.Harness.Grounding.EvidenceBundleIngestor.EvidenceBundleIngestor.__expand_topic_aliases()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__expand_client_url_aliases()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__record_kb_url()`
	# @used-by :meth:`UserUrlPolicy.__init__()`
	# @used-by :meth:`UserUrlPolicy.check_urls()`
	# @used-by :meth:`UserUrlPolicy.collect_client_site_hosts()`
	# @used-by :meth:`UserUrlPolicy.format_card_url()`
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_policy_helpers_classification_and_immutability()`
	@staticmethod
	def apex_host(url_or_host: str) -> str:
		raw = (url_or_host or '').strip()
		host = (urlsplit(raw).hostname or '').lower() if '://' in raw else raw.lower().split('/', 1)[0].split(':', 1)[0]
		return host[4:] if host.startswith('www.') and '.' in host[4:] else host
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_external_refs()`
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_policy_helpers_classification_and_immutability()`
	def check_urls(self, urls: Iterable[str]) -> list[str]:
		errors: list[str] = []
		for url in dict.fromkeys(urls or ()):
			if not self.is_www_host(url):
				continue
			apex = self.apex_host(url)
			if apex in self.__failed_apex_hosts:
				continue
			clean = self.strip_www(url)
			if apex in self.__working_apex_hosts:
				errors.append(f'LINK-5: Omit leading www. in user-facing URL {url} -> use {clean} (\ua616/KB/Evidence confirms non-www. works)')
			elif apex in self.__client_site_hosts:
				errors.append(f'LINK-5: Omit leading www. in user-facing client URL {url} -> use {clean} (or record failing non-www. root observation in \ua616/KB/Evidence)')
		return errors
	# @used-by :meth:`Df.Harness.Grounding.EvidenceBundleIngestor.EvidenceBundleIngestor.__ingest_observation_bundle()`
	# @used-by :meth:`UserUrlPolicy.from_evidence_dir()`
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_policy_helpers_classification_and_immutability()`
	@staticmethod
	def classify_observation(data: dict) -> tuple[str | None, str | None]:
		req_url = data.get('url') if isinstance(data, dict) else None
		r: tuple[str | None, str | None] = (None, None)
		if isinstance(req_url, str) and req_url.startswith(('http://', 'https://')) and (not UserUrlPolicy.is_www_host(req_url)):
			parsed = urlsplit(req_url)
			host = (parsed.hostname or '').lower()
			status, err, kind = (data.get('status'), data.get('error'), data.get('kind'))
			if host and (not err) and ('dom' == kind or (isinstance(status, int) and 200 <= status < 300)):
				r = ('working', host)
			elif host and UserUrlPolicy.__is_root_path(parsed.path, parsed.query) and (bool(err) or (isinstance(status, int) and 400 <= status)):
				r = ('failed', host)
		return r
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_policy_helpers_classification_and_immutability()`
	@property
	def client_site_hosts(self) -> frozenset[str]:
		return self.__client_site_hosts
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__collect_client_site_hosts()`
	@staticmethod
	def collect_client_site_hosts(analysis_json: Path, project_json: Path) -> frozenset[str]:
		hosts: set[str] = set()
		for site in UserUrlPolicy.__read_json_dict(analysis_json).get('websites') or ():
			apex = UserUrlPolicy.apex_host(site['url']) if isinstance(site, dict) and isinstance(site.get('url'), str) else ''
			if apex and 'upwork.com' != apex:
				hosts.add(apex)
		pdata = UserUrlPolicy.__read_json_dict(project_json)
		lbl = pdata.get('label', '').strip().lower() if isinstance(pdata.get('label'), str) else ''
		if '.' in lbl and ' ' not in lbl and '/' not in lbl:
			apex = UserUrlPolicy.apex_host(lbl)
			if apex and 'upwork.com' != apex:
				hosts.add(apex)
		return frozenset(hosts)
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_policy_helpers_classification_and_immutability()`
	@property
	def failed_apex_hosts(self) -> frozenset[str]:
		return self.__failed_apex_hosts
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_policy_helpers_classification_and_immutability()`
	@staticmethod
	def format_card_url(url: str, *, failed_apex_hosts: frozenset[str]=frozenset()) -> str:
		text = (url or '').strip()
		if UserUrlPolicy.is_www_host(text) and UserUrlPolicy.apex_host(text) not in failed_apex_hosts:
			text = UserUrlPolicy.strip_www(text)
		parsed = urlsplit(text)
		if '/' == parsed.path and (not parsed.query) and (not parsed.fragment) and text.endswith('/'):
			text = text[:-1]
		return text
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_policy_helpers_classification_and_immutability()`
	@classmethod
	def from_evidence_dir(cls, evidence_dir: Path, *, client_site_hosts: Iterable[str]=()) -> UserUrlPolicy:
		working: set[str] = set()
		failed: set[str] = set()
		ev_path = Path(evidence_dir)
		if ev_path.is_dir():
			for obs in ev_path.rglob('observation.json'):
				try:
					data = json.loads(obs.read_text(encoding='utf-8'))
				except (OSError, ValueError):
					continue
				kind, apex = cls.classify_observation(data)
				if 'working' == kind and apex:
					working.add(apex)
				elif 'failed' == kind and apex:
					failed.add(apex)
		return cls(working_apex_hosts=working, failed_apex_hosts=failed, client_site_hosts=client_site_hosts)
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__needs_evidence_scan()`
	# @used-by :meth:`UserUrlPolicy.check_urls()`
	# @used-by :meth:`UserUrlPolicy.classify_observation()`
	# @used-by :meth:`UserUrlPolicy.format_card_url()`
	# @used-by :meth:`UserUrlPolicy.non_www_alias()`
	# @used-by :meth:`UserUrlPolicy.strip_www()`
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_policy_helpers_classification_and_immutability()`
	@staticmethod
	def is_www_host(url: str) -> bool:
		raw = (url or '').strip()
		host = (urlsplit(raw).hostname or '').lower() if '://' in raw else ''
		return bool(host and host.startswith('www.') and '.' in host[4:])
	# @used-by :meth:`Df.Harness.Grounding.EvidenceBundleIngestor.EvidenceBundleIngestor.__expand_non_www_aliases()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__expand_client_url_aliases()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__record_kb_url()`
	@staticmethod
	def non_www_alias(norm_url: str) -> str | None:
		return UserUrlPolicy.strip_www(norm_url) if UserUrlPolicy.is_www_host(norm_url) else None
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__record_text_urls()`
	@staticmethod
	def strip_inline_quotes(text: str, in_g: bool, in_d: bool) -> tuple[str, bool, bool]:
		out: list[str] = []
		for ch in text:
			if '\u00ab' == ch and (not in_d):
				in_g = True
			elif '\u00bb' == ch and in_g:
				in_g = False
			elif '"' == ch and (not in_g):
				in_d = not in_d
			elif (not in_g) and (not in_d):
				out.append(ch)
		return (''.join(out), in_g, in_d)
	# @used-by :meth:`UserUrlPolicy.check_urls()`
	# @used-by :meth:`UserUrlPolicy.format_card_url()`
	# @used-by :meth:`UserUrlPolicy.non_www_alias()`
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_policy_helpers_classification_and_immutability()`
	@staticmethod
	def strip_www(url: str) -> str:
		return UserUrlPolicy.__slice_www_prefix(url) if UserUrlPolicy.is_www_host(url) else url
	# @used-by :meth:`test_user_url_policy.UserUrlPolicyTests.test_policy_helpers_classification_and_immutability()`
	@property
	def working_apex_hosts(self) -> frozenset[str]:
		return self.__working_apex_hosts
