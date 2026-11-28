# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from urllib.parse import urldefrag, urlsplit
# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
from Df.Harness.Research.UserUrlPolicy import UserUrlPolicy
from Df.Harness.lib.research import MAX_BYTES
from agent_tools.evidence_loader import load_observation_bundle
import json
import re
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class EvidenceBundleIngestor:
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_response_auditor_ingestor_and_tier0_index()`
	def __init__(self, auditor) -> None:
		self.__auditor = auditor
	# @used-by :meth:`EvidenceBundleIngestor.ingest()`
	def __evidence_dirs(self) -> list[Path]:
		from agent_tools.path_registry import project_paths
		ev_dirs: list[Path] = []
		pp_ev = project_paths(self.__auditor.root, exact_root=True).evidence_dir
		if pp_ev.is_dir():
			ev_dirs.append(pp_ev.resolve())
		elif (self.__auditor.root / '_/\ua616/KB/Evidence').is_dir():
			ev_dirs.append((self.__auditor.root / '_/\ua616/KB/Evidence').resolve())
		elif (self.__auditor.root / '\ua616/KB/Evidence').is_dir():
			ev_dirs.append((self.__auditor.root / '\ua616/KB/Evidence').resolve())
		return ev_dirs
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`EvidenceBundleIngestor.ingest()`
	def __expand_non_www_aliases(self) -> None:
		working = getattr(self.__auditor, 'working_apex_hosts', set())
		failed = getattr(self.__auditor, 'failed_apex_hosts', set()) - working
		for nu in list(self.__auditor.observed_urls):
			alias = UserUrlPolicy.non_www_alias(nu)
			if not alias or UserUrlPolicy.apex_host(nu) in failed:
				continue
			self.__auditor.observed_urls.add(alias)
			if nu in self.__auditor.observed_titles:
				self.__auditor.observed_titles.setdefault(alias, self.__auditor.observed_titles[nu])
			if nu in self.__auditor.observed_anchors:
				self.__auditor.observed_anchors.setdefault(alias, set()).update(self.__auditor.observed_anchors[nu])
			if nu in self.__auditor.observed_texts:
				self.__auditor.observed_texts.setdefault(alias, []).extend(self.__auditor.observed_texts[nu])
		self.__expand_topic_aliases(failed)
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`EvidenceBundleIngestor.__expand_non_www_aliases()`
	def __expand_topic_aliases(self, failed: set[str]) -> None:
		for host, tid in list(self.__auditor.observed_topics):
			if host.startswith('www.') and '.' in host[4:]:
				apex = UserUrlPolicy.apex_host(host)
				if apex not in failed:
					atk = (apex, tid)
					self.__auditor.observed_topics.add(atk)
					if (host, tid) in self.__auditor.observed_topic_titles:
						self.__auditor.observed_topic_titles.setdefault(atk, self.__auditor.observed_topic_titles[(host, tid)])
	# @used-by :meth:`EvidenceBundleIngestor.ingest()`
	def __ingest_json_file(self, jfile: Path) -> None:
		try:
			if jfile.stat().st_size <= 4 * 1024 * 1024:
				data = json.loads(jfile.read_text(encoding='utf-8'))
				if isinstance(data, dict):
					if 'observation.json' == jfile.name:
						self.__ingest_observation_bundle(jfile, data)
					else:
						src_u = data.get('url') or data.get('html_url') or data.get('source') or ''
						host = (urlsplit(src_u).hostname or '').lower() if isinstance(src_u, str) and src_u.startswith(('http://', 'https://')) else ''
						self.__ingest_json_observations(data, host)
		except (OSError, ValueError):
			pass
	# @used-by :meth:`EvidenceBundleIngestor.__ingest_json_file()`
	# @used-by :meth:`EvidenceBundleIngestor.__ingest_observation_bundle()`
	def __ingest_json_observations(self, parsed: dict, default_host: str) -> None:
		if isinstance(parsed, dict):
			self.__record_direct_payload(parsed, default_host)
			topics: list = []
			if isinstance(parsed.get('topic_list'), dict) and isinstance(parsed['topic_list'].get('topics'), list):
				topics.extend(parsed['topic_list']['topics'])
			if isinstance(parsed.get('topics'), list):
				topics.extend(parsed['topics'])
			for topic in topics:
				self.__record_topic_entry(topic, default_host)
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`EvidenceBundleIngestor.__ingest_json_file()`
	def __ingest_observation_bundle(self, jfile: Path, data: dict) -> None:
		kind, apex = UserUrlPolicy.classify_observation(data)
		if 'working' == kind and apex and hasattr(self.__auditor, 'working_apex_hosts'):
			self.__auditor.working_apex_hosts.add(apex)
		elif 'failed' == kind and apex and hasattr(self.__auditor, 'failed_apex_hosts'):
			self.__auditor.failed_apex_hosts.add(apex)
		bundle = load_observation_bundle(jfile, data, max_bytes=MAX_BYTES)
		if None is not bundle['json_payload']:
			self.__ingest_json_observations(bundle['json_payload'], bundle['host'])
		if not bundle['valid']:
			for u in bundle['urls']:
				self.__auditor.invalid_observations.setdefault(self.norm_url(u), bundle['reason'])
		else:
			self.__record_valid_bundle(bundle)
	# @used-by :meth:`EvidenceBundleIngestor.__ingest_json_observations()`
	def __record_direct_payload(self, parsed: dict, default_host: str) -> None:
		u = parsed.get('url') or parsed.get('html_url')
		if isinstance(u, str) and u.startswith(('http://', 'https://')):
			nu = self.norm_url(u)
			self.__auditor.observed_urls.add(nu)
			if isinstance(parsed.get('title'), str) and parsed['title'].strip():
				self.__auditor.observed_titles.setdefault(nu, ' '.join(parsed['title'].split()))
			for field in ('body', 'text', 'title'):
				val = parsed.get(field)
				if isinstance(val, str) and val.strip():
					self.__auditor.observed_texts.setdefault(nu, []).append(val)
		if isinstance(parsed.get('title'), str) and parsed['title'].strip() and default_host and isinstance(parsed.get('id'), int):
			tk = (default_host.lower(), str(parsed['id']))
			self.__auditor.observed_topics.add(tk)
			self.__auditor.observed_topic_titles.setdefault(tk, ' '.join(parsed['title'].split()))
	# @used-by :meth:`EvidenceBundleIngestor.__ingest_json_observations()`
	def __record_topic_entry(self, topic, default_host: str) -> None:
		if isinstance(topic, dict) and isinstance(topic.get('id'), int) and isinstance(topic.get('title'), str):
			t, tid, host = (' '.join(topic['title'].split()), str(topic['id']), default_host)
			tu = topic.get('url')
			if isinstance(tu, str) and tu.startswith(('http://', 'https://')):
				nu = self.norm_url(tu)
				self.__auditor.observed_urls.add(nu)
				self.__auditor.observed_titles.setdefault(nu, t)
				host = host or (urlsplit(nu).hostname or '')
			if host:
				self.__record_topic_host_urls(host.lower(), tid, t, topic.get('slug'))
	# @used-by :meth:`EvidenceBundleIngestor.__record_topic_entry()`
	def __record_topic_host_urls(self, host: str, tid: str, title: str, slug: object) -> None:
		tk = (host, tid)
		self.__auditor.observed_topics.add(tk)
		self.__auditor.observed_topic_titles.setdefault(tk, title)
		urls = [f'https://{host}/t/{tid}']
		if isinstance(slug, str) and slug:
			urls.append(f'https://{host}/t/{slug}/{tid}')
		for u in urls:
			self.__auditor.observed_urls.add(u)
			self.__auditor.observed_titles.setdefault(u, title)
	# @used-by :meth:`EvidenceBundleIngestor.__ingest_observation_bundle()`
	def __record_valid_bundle(self, bundle: dict) -> None:
		for u in bundle['urls']:
			nu = self.norm_url(u)
			self.__auditor.observed_urls.add(nu)
			tk = self.discourse_topic_key(nu)
			if tk:
				self.__auditor.observed_topics.add(tk)
			for t in bundle['titles']:
				self.__auditor.observed_titles.setdefault(nu, t)
				if tk:
					self.__auditor.observed_topic_titles.setdefault(tk, t)
			if bundle['has_html_anchors']:
				self.__auditor.observed_anchors.setdefault(nu, set()).update(bundle['anchors'])
			if bundle['texts']:
				self.__auditor.observed_texts.setdefault(nu, []).extend(bundle['texts'])
	# @used-by :func:`agent_tools.response_grounding._discourse_topic_key()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_kb_membership()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_link_observations()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_link_titles()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__record_kb_url()`
	# @used-by :meth:`EvidenceBundleIngestor.__record_valid_bundle()`
	@staticmethod
	def discourse_topic_key(url: str) -> tuple[str, str] | None:
		m = re.match('^https?://([^/:?#]+)/t/(?:[^/?#]+/)?(\\d+)(?:$|[/?#])', url.strip(), re.I)
		return (m.group(1).lower(), m.group(2)) if m else None
	# 2026-11-28 "Enforce non-www user URL policy with KB alias grounding": https://github.com/dmitry-ai/harness/issues/416
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.validate()`
	# @used-by :meth:`test_df_harness_s11_wave2c_grounding.DfHarnessS11Wave2CGroundingTests.test_response_auditor_ingestor_and_tier0_index()`
	def ingest(self) -> None:
		for ev_dir in self.__evidence_dirs():
			for jfile in ev_dir.rglob('*.json'):
				if not jfile.name.startswith('extracted-'):
					self.__ingest_json_file(jfile)
		self.__expand_non_www_aliases()
	# @used-by :func:`agent_tools.response_grounding._norm_url()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_external_refs()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_kb_membership()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_link_observations()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__check_link_titles()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__expand_upwork_job_urls()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__needs_evidence_scan()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__record_client_text_urls()`
	# @used-by :meth:`Df.Harness.Grounding.ResponseAuditor.ResponseAuditor.__record_kb_url()`
	# @used-by :meth:`EvidenceBundleIngestor.__ingest_observation_bundle()`
	# @used-by :meth:`EvidenceBundleIngestor.__record_direct_payload()`
	# @used-by :meth:`EvidenceBundleIngestor.__record_topic_entry()`
	# @used-by :meth:`EvidenceBundleIngestor.__record_valid_bundle()`
	@staticmethod
	def norm_url(url: str) -> str:
		return urldefrag(url.strip())[0].rstrip('/')