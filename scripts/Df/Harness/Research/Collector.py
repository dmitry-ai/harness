# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urldefrag
from urllib.request import Request, build_opener
from Df.Harness.Research.Response import Response
from Df.Harness.Research.SafeRedirects import SafeRedirects
from Df.Harness.lib.research import HTTP_DEFAULT_ACCEPT, dfh_classify_network_error, dfh_fingerprint, dfh_inside, dfh_json_data, dfh_observed_use, dfh_request_context, dfh_request_key, dfh_research_max_bytes, dfh_research_seam
import hashlib
import json
import time
import uuid
# 2026-11-26 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class Collector:
	# @used-by :func:`agent_tools.research.collect()`
	# @used-by :meth:`Df.Harness.Research.BrowserCollector.BrowserCollector.__collect_single()`
	# @used-by :meth:`Df.Harness.Research.DomCapturer.DomCapturer.capture()`
	# @used-by :meth:`Df.Harness.Research.HttpCollector.HttpCollector.__collect_http_and_fallback()`
	# @used-by :meth:`Df.Harness.Text.SourceProber.SourceProber.probe()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_evidence_querier_and_grepper()`
	def __init__(self, root, url: str, *, headers=None, scope: str='public', max_age: float=86400, refresh_reason=None, timeout: float=15, fetcher=None, observation_kind: str='http', context=None, extra_meta=None) -> None:
		self.__root = Path(root).resolve()
		self.__url = url
		self.__headers = headers
		self.__scope = scope
		self.__max_age = max_age
		self.__refresh_reason = refresh_reason
		self.__timeout = timeout
		self.__fetcher = fetcher
		self.__kind = observation_kind
		self.__context = context
		self.__extra_meta = extra_meta
	# @used-by :meth:`Collector.__persist_fresh()`
	def __build_meta(self, key: str, url: str, headers: dict, context: dict, when: str, response: Response, error, error_kind, dns_resolved) -> dict:
		is_http = 'http' == self.__kind
		meta: dict = {'schema_version': 1, 'kind': self.__kind, 'request_key': key, 'url': url, 'final_url': response.url, 'method': 'GET' if is_http else 'READ_DOM', 'request_scope': self.__scope, 'observed_at': when, 'status': response.status if is_http else None, 'http_status_verified': is_http and 0 < response.status, 'content_type': response.content_type, 'charset': response.charset, 'redirects': list(response.redirects), 'body_sha256': hashlib.sha256(response.body).hexdigest(), 'body_bytes': len(response.body), 'refresh_reason': self.__refresh_reason, 'error': error, 'error_kind': error_kind, 'dns_resolved': dns_resolved, 'conditions': {'header_names': sorted((k.lower() for k in headers)), 'values_fingerprint': key, 'reported_context': context, 'context_fingerprint': dfh_fingerprint(context)}, 'collector': 'read-only-http' if is_http else 'read-only-dom', 'interaction_checked': False}
		if isinstance(self.__extra_meta, dict):
			for k in ('cdp_identity', 'cdp_identity_sha256'):
				if isinstance(self.__extra_meta.get(k), str) and self.__extra_meta[k]:
					meta[k] = self.__extra_meta[k]
		return meta
	# @used-by :meth:`Collector.__persist_fresh()`
	def __execute_fetch(self, url: str, headers: dict) -> tuple[Response, str | None, str | None, bool | None]:
		fetch_fn = self.__fetcher or dfh_research_seam('fetch', self.fetch)
		error, error_kind, dns_resolved = (None, None, None)
		try:
			response = fetch_fn(url, headers, self.__timeout)
			if dfh_research_max_bytes() < len(response.body):
				raise ValueError('Response exceeds 16 MiB')
			dns_resolved = True if 'http' == self.__kind and 0 < (response.status or 0) else None
		except PermissionError:
			raise
		except (OSError, ValueError, RuntimeError) as exc:
			response = Response(url, 0, 'application/octet-stream', b'')
			error = type(exc).__name__
			error_kind, dns_resolved = dfh_classify_network_error(exc)
		return (response, error, error_kind, dns_resolved)
	# @used-by :meth:`Collector.collect()`
	def __persist_fresh(self, pp, key: str, url: str, headers: dict, context: dict) -> dict:
		from agent_tools.storage import create_bytes, locked, replace_bytes
		if None is not self.__refresh_reason and (not self.__refresh_reason.strip()):
			raise ValueError('Refresh needs a reason for the new measurement')
		when = datetime.now(timezone.utc).isoformat(timespec='microseconds')
		response, error, error_kind, dns_resolved = self.__execute_fetch(url, headers)
		folder = pp.evidence_dir / 'HTTP' / key[:24] / uuid.uuid4().hex
		folder.mkdir(parents=True, exist_ok=False)
		create_bytes(folder / 'response.bin', response.body)
		meta = self.__build_meta(key, url, headers, context, when, response, error, error_kind, dns_resolved)
		create_bytes(folder / 'observation.json', dfh_json_data(meta))
		reference = (folder / 'observation.json').relative_to(pp.kb_dir).as_posix()
		with locked(pp.data_dir / 'http-index.lock'):
			idx2 = json.loads(pp.http_index_json.read_text(encoding='utf-8')) if pp.http_index_json.exists() else {}
			idx2[key] = {'observation': reference}
			replace_bytes(pp.http_index_json, dfh_json_data(idx2))
		return dfh_observed_use(pp.root, {'cached': False, 'observation': reference, **meta})
	# @used-by :meth:`Collector.collect()`
	def __prepare_headers_and_keys(self) -> tuple[dict, dict, str, str, str | None]:
		if 0 > self.__max_age or 0 >= self.__timeout or (not isinstance(self.__scope, str)) or (not self.__scope.strip()):
			raise ValueError('Nonnegative max_age, positive timeout and explicit request scope required')
		caller = dict(self.__headers or {})
		if not all((isinstance(k, str) and isinstance(v, str) for k, v in caller.items())):
			raise ValueError('Request headers must contain string keys and values')
		has_accept = any(('accept' == k.lower() for k in caller))
		headers = {'User-Agent': 'UpworkResearch/2.0', **caller}
		legacy_headers = dict(headers) if 'http' == self.__kind and (not has_accept) else None
		if 'http' == self.__kind and (not has_accept):
			headers['Accept'] = HTTP_DEFAULT_ACCEPT
		if self.__kind not in ('http', 'dom') or ('dom' == self.__kind and None is self.__fetcher):
			raise ValueError('DOM observation needs an explicit read-only browser capture')
		context = dfh_request_context(self.__context)
		url, key = dfh_request_key(self.__url, headers, self.__scope + ':' + self.__kind, context)
		legacy_key = dfh_request_key(url, legacy_headers, self.__scope + ':' + self.__kind, context)[1] if None is not legacy_headers else None
		return (headers, context, url, key, legacy_key)
	# @used-by :meth:`Collector.collect()`
	def __try_cached(self, root: Path, index: dict, key: str, legacy_key: str | None) -> dict | None:
		r: dict | None = None
		entry = index.get(key) or (index.get(legacy_key) if legacy_key else None)
		if entry and (not self.__refresh_reason) and 0 < self.__max_age:
			meta = self.load_observation(root, entry['observation'])
			needs_dom_id = 'dom' == self.__kind and isinstance(self.__extra_meta, dict) and (not meta.get('cdp_identity'))
			ttl = min(self.__max_age, 300) if meta.get('error') or (None is not meta.get('status') and 400 <= meta.get('status', 0)) else self.__max_age
			if (not needs_dom_id) and time.time() - datetime.fromisoformat(meta['observed_at']).timestamp() <= ttl:
				r = dfh_observed_use(root, {'cached': True, 'observation': entry['observation'], **meta})
		return r
	# @used-by :func:`agent_tools.research.collect()`
	# @used-by :meth:`Df.Harness.Research.BrowserCollector.BrowserCollector.__collect_single()`
	# @used-by :meth:`Df.Harness.Research.DomCapturer.DomCapturer.capture()`
	# @used-by :meth:`Df.Harness.Research.HttpCollector.HttpCollector.__collect_http_and_fallback()`
	# @used-by :meth:`Df.Harness.Text.SourceProber.SourceProber.probe()`
	# @used-by :meth:`test_df_harness_s11_wave2c_research.DfHarnessS11Wave2CResearchTests.test_evidence_querier_and_grepper()`
	def collect(self) -> dict:
		from agent_tools.path_registry import project_paths
		from agent_tools.storage import locked
		headers, context, url, key, legacy_key = self.__prepare_headers_and_keys()
		pp = project_paths(self.__root, exact_root=True)
		with locked(pp.data_dir / ('http-' + key[:24] + '.lock'), timeout=max(30, self.__timeout + 15)):
			index = json.loads(pp.http_index_json.read_text(encoding='utf-8')) if pp.http_index_json.exists() else {}
			r = self.__try_cached(pp.root, index, key, legacy_key)
			if None is r:
				r = self.__persist_fresh(pp, key, url, headers, context)
		return r
	# @used-by :func:`agent_tools.research.fetch()`
	# @used-by :meth:`Collector.__execute_fetch()`
	@staticmethod
	def fetch(url: str, headers: dict, timeout: float) -> Response:
		redirects = SafeRedirects()
		max_b = dfh_research_max_bytes()
		try:
			response = build_opener(redirects).open(Request(url, headers=headers), timeout=timeout)
		except HTTPError as error:
			response = error
		with response:
			data = response.read(max_b + 1)
			if max_b < len(data):
				raise ValueError('Response exceeds 16 MiB')
			r = Response(response.url, response.status, response.headers.get_content_type(), data, response.headers.get_content_charset() or 'utf-8', tuple(redirects.chain))
		return r
	# @used-by :func:`Df.Harness.lib.text_sources._write_attempt_if_newer()`
	# @used-by :func:`Df.Harness.lib.text_sources.dfh_source_attempt()`
	# @used-by :func:`agent_tools.research.load_observation()`
	# @used-by :meth:`Collector.__try_cached()`
	# @used-by :meth:`Df.Harness.Research.Extractor.Extractor.extract_observation()`
	# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.__check_freshness()`
	# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.evaluate()`
	@staticmethod
	def load_observation(root, reference: str) -> dict:
		from agent_tools.path_registry import project_paths
		kb_dir = project_paths(root, exact_root=True).kb_dir.resolve()
		file = dfh_inside(kb_dir, urldefrag(reference)[0])
		meta = json.loads(file.read_text(encoding='utf-8'))
		if 1 != meta.get('schema_version') or not isinstance(meta.get('body_sha256'), str):
			raise ValueError('Invalid observation metadata')
		body = (file.parent / 'response.bin').read_bytes()
		if len(body) != meta.get('body_bytes') or hashlib.sha256(body).hexdigest() != meta['body_sha256']:
			raise ValueError('Observation body differs from its saved hash/size')
		return meta
