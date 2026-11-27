# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from datetime import timezone
from pathlib import Path
from urllib.parse import urldefrag
from Df.Harness.Research.Collector import Collector
from Df.Harness.Text.IntakeSourceEvaluator import IntakeSourceEvaluator
from Df.Harness.lib.research import dfh_inside, dfh_readable_reference
from Df.Harness.lib.text_claims import dfh_evidence_inputs, dfh_text_digest
from Df.Harness.lib.text_sources import SOURCE_MAX_AGE, dfh_source_attempt, dfh_source_datetime, dfh_source_urls
from agent_tools.storage import read_addressed_json
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SourceEvaluator:
	# @used-by :func:`agent_tools.text_sources._evaluate()`
	# @used-by :meth:`Df.Harness.Text.SourceReceiptReader.SourceReceiptReader.read()`
	# @used-by :meth:`Df.Harness.Text.SourceReceiptStore.SourceReceiptStore.save()`
	def __init__(self, root, candidate: str, spec) -> None:
		self.__root = root
		self.__candidate = candidate
		self.__spec = spec
	# @used-by :meth:`SourceEvaluator.evaluate()`
	def __check_freshness(self, meta: dict) -> None:
		dt = dfh_source_datetime()
		latest = dfh_source_attempt(self.__root, self.__candidate, self.__spec['url'], None, None, read_only=True)
		if latest and dt.fromisoformat(latest['observed_at']) > dt.fromisoformat(meta['observed_at']):
			recent = Collector.load_observation(self.__root, latest['observation'])
			if recent.get('error') or ('dom' != recent.get('kind') and (not 200 <= (recent.get('status') or 0) < 300)) or recent['body_sha256'] != meta['body_sha256'] or (recent['final_url'] != meta['final_url']):
				raise ValueError('A newer conflicting source observation exists for this candidate; resolve it instead of reusing an older success')
		expected = self.__spec.get('expected_final_url', urldefrag(self.__spec['url'])[0])
		if dfh_readable_reference(urldefrag(meta['final_url'])[0]) != dfh_readable_reference(urldefrag(expected)[0]):
			raise ValueError('Final URL differs from the intended resource; verify redirects explicitly')
		observed = dt.fromisoformat(meta['observed_at'])
		if None is observed.tzinfo or observed > dt.now(timezone.utc):
			raise ValueError('Source observation needs a nonfuture timezone-aware timestamp')
		if 'current' == self.__spec['currency'] and SOURCE_MAX_AGE < (dt.now(timezone.utc) - observed).total_seconds():
			raise ValueError('Current-source observation is older than 24 hours; collect a justified refresh')
	# @used-by :meth:`SourceEvaluator.evaluate()`
	def __validate_http_ref(self, ref) -> None:
		loc = ref.get('locator') if isinstance(ref, dict) else None
		valid = isinstance(ref, dict) and isinstance(ref.get('source'), str) and dfh_readable_reference(ref['source']) == dfh_readable_reference(self.__spec['url']) and isinstance(ref.get('quote'), str) and bool(ref['quote'].strip()) and isinstance(loc, dict) and loc.get('type') in ('text', 'anchor', 'lines', 'json_pointer') and isinstance(loc.get('value'), str) and bool(loc['value']) and type(ref.get('documentation')) is bool and bool(ref.get('observation'))
		if not valid:
			raise ValueError('Use exact URL, quote, locator, explicit documentation flag and saved HTTP/DOM observation')
		if ref['documentation'] and (not urldefrag(self.__spec['url'])[1]) and ('anchor' == ref['locator']['type']):
			raise ValueError('Put the verified documentation anchor in the cited URL itself')
	# @used-by :meth:`SourceEvaluator.evaluate()`
	def __validate_spec(self) -> None:
		if not isinstance(self.__spec, dict) or not isinstance(self.__spec.get('url'), str) or dfh_readable_reference(self.__spec['url']) not in dfh_source_urls(self.__candidate):
			raise ValueError('Source check must name an exact external URL in this candidate')
		if self.__spec.get('currency') not in ('current', 'historical') or not isinstance(self.__spec.get('currency_basis'), str) or (not self.__spec['currency_basis'].strip()):
			raise ValueError('Declare current/historical currency and its applicability basis')
		if 'historical' == self.__spec['currency'] and (not isinstance(self.__spec.get('edition'), str) or not self.__spec['edition'].strip()):
			raise ValueError('A historical source requires its explicit edition; it is not a current-source fallback')
	# @used-by :meth:`SourceEvaluator.evaluate()`
	def __verify_dom_identity(self, meta: dict, inputs: dict) -> None:
		from agent_tools.path_registry import project_paths
		identity = self.__spec.get('cdp_identity')
		if not isinstance(identity, str) or not identity.strip():
			raise ValueError('DOM fallback requires its captured CDP identity receipt')
		path = dfh_inside(project_paths(self.__root, exact_root=True).kb_dir, identity)
		raw, data = read_addressed_json(path, stem_match=True, error_msg='DOM identity does not bind this exact observation')
		prof = data.get('profile')
		if 1 != data.get('schema_version') or any((not isinstance(data.get(key), str) or not data[key] for key in ('target_id', 'browser_websocket', 'observed_at'))) or ('read-only-dom' != meta.get('collector')) or ('READ_DOM' != meta.get('method')) or (not isinstance(prof, dict)) or ('verified' != prof.get('status')):
			raise ValueError('DOM identity does not bind this exact observation')
		sid, req_scope = (data.get('session_id'), meta.get('request_scope') or '')
		ctx_sid, raw_sha = (meta.get('conditions', {}).get('reported_context', {}).get('session_id'), dfh_text_digest(raw))
		mode_tab = isinstance(sid, str) and bool(sid) and (ctx_sid == sid) and (req_scope == f"CDP-session:{sid}:tab:{data.get('target_id')}:identity:{identity}") and (meta.get('cdp_identity') in (None, identity)) and (meta.get('cdp_identity_sha256') in (None, raw_sha))
		mode_auth = isinstance(sid, str) and bool(sid) and (ctx_sid == sid) and (req_scope == f'CDP-session:{sid}' or (not req_scope.startswith('CDP-session:'))) and (data.get('target_mode') in ('hidden_session_target', 'm2a_extension_background_tab')) and (meta.get('cdp_identity') == identity) and (meta.get('cdp_identity_sha256') in (None, raw_sha))
		mode_public = None is sid and None is ctx_sid and bool(req_scope) and (not req_scope.startswith('CDP-session:')) and (data.get('target_mode') in ('ephemeral_headless_context', 'hidden_session_target')) and (meta.get('cdp_identity') == identity) and (meta.get('cdp_identity_sha256') in (None, raw_sha))
		if not (mode_tab or mode_auth or mode_public):
			raise ValueError('DOM identity does not bind this exact observation')
		inputs[path.relative_to(Path(self.__root).resolve()).as_posix()] = raw_sha
	# @used-by :func:`agent_tools.text_sources._evaluate()`
	# @used-by :meth:`Df.Harness.Text.SourceReceiptReader.SourceReceiptReader.read()`
	# @used-by :meth:`Df.Harness.Text.SourceReceiptStore.SourceReceiptStore.save()`
	def evaluate(self) -> dict:
		from agent_tools.claims import _verify_quote
		self.__validate_spec()
		ref = self.__spec.get('evidence')
		if isinstance(ref, dict) and 'intake' == ref.get('kind'):
			r = IntakeSourceEvaluator(self.__root, self.__spec).evaluate()
		else:
			self.__validate_http_ref(ref)
			meta = Collector.load_observation(self.__root, ref['observation'])
			if dfh_readable_reference(meta['url']) != dfh_readable_reference(urldefrag(self.__spec['url'])[0]):
				raise ValueError('Requested URL differs from the exact cited resource')
			self.__check_freshness(meta)
			_verify_quote(self.__root, ref, observation=ref['observation'])
			inputs = dfh_evidence_inputs(self.__root, {'facts': [{'evidence': [ref]}]})
			if 'dom' == meta.get('kind'):
				self.__verify_dom_identity(meta, inputs)
			r = {'url': dfh_readable_reference(self.__spec['url']), 'requested_url': meta['url'], 'final_url': meta['final_url'], 'method': meta['method'], 'http_status': meta['status'], 'observed_at': meta['observed_at'], 'body_sha256': meta['body_sha256'], 'currency': self.__spec['currency'], 'edition': self.__spec.get('edition'), 'inputs': inputs}
		return r
