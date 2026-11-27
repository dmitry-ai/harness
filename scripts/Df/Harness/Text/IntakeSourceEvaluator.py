# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urldefrag, urlsplit
from Df.Harness.lib.research import dfh_inside, dfh_readable_reference
from Df.Harness.lib.text_claims import dfh_evidence_inputs
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class IntakeSourceEvaluator:
	# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.evaluate()`
	def __init__(self, root, spec: dict) -> None:
		self.__root = root
		self.__spec = spec
	# @used-by :meth:`IntakeSourceEvaluator.evaluate()`
	def __load_verified_project_state(self):
		from agent_tools.path_registry import project_paths
		from agent_tools.upwork_data import extract_upwork_job_url_id
		url_base, url_frag = urldefrag(self.__spec['url'].strip())
		if url_frag or urlsplit(url_base).query:
			raise ValueError('Intake job snapshot cannot verify URL query parameters or HTML fragments')
		cited_job_id = extract_upwork_job_url_id(self.__spec['url'])
		if not cited_job_id:
			raise ValueError('Intake source-check provenance applies only to the registered Upwork job URL of this project')
		pp = project_paths(self.__root, exact_root=True)
		state = json.loads(pp.project_json.read_text(encoding='utf-8-sig')) if pp.project_json.is_file() else {}
		if not isinstance(state, dict) or True is not state.get('initialized') or state.get('job_id') != cited_job_id:
			raise ValueError('Cited Upwork job URL does not match the registered initialized project job_id')
		return (pp, state, cited_job_id)
	# @used-by :meth:`IntakeSourceEvaluator.evaluate()`
	def __resolve_local_source(self, pp, ref: dict, manifest_doc) -> str:
		raw_src = ref.get('source')
		if isinstance(raw_src, str) and urlsplit(raw_src).scheme.lower() in ('http', 'https'):
			if dfh_readable_reference(raw_src) != dfh_readable_reference(self.__spec['url']):
				raise ValueError('Intake evidence URL differs from the exact cited resource')
			local_source = None
		elif isinstance(raw_src, str) and raw_src.strip():
			local_source = raw_src
		else:
			local_source = None
		if None is local_source:
			if isinstance(manifest_doc, dict) and isinstance(manifest_doc.get('entries'), list):
				matched = next((e for e in manifest_doc['entries'] if isinstance(e, dict) and 'identity' == e.get('transform') and 'source.json' == e.get('original_relative_provenance') and (e.get('sha256') == ref['source_sha256']) and isinstance(e.get('durable_file'), str)), None)
				if not matched:
					raise ValueError('Intake receipt has no matching source.json entry for this Upwork job snapshot')
				local_source = dfh_inside(pp.root, matched['durable_file']).relative_to(pp.kb_dir).as_posix()
			else:
				local_source = ref['manifest']
		return local_source
	# @used-by :meth:`IntakeSourceEvaluator.evaluate()`
	@staticmethod
	def __validate_intake_ref(ref: dict) -> None:
		loc = ref.get('locator')
		valid = isinstance(ref.get('manifest'), str) and bool(ref['manifest'].strip()) and isinstance(ref.get('source_sha256'), str) and bool(ref['source_sha256'].strip()) and isinstance(ref.get('quote'), str) and bool(ref['quote'].strip()) and isinstance(loc, dict) and loc.get('type') in ('json_pointer', 'text', 'lines') and isinstance(loc.get('value'), str) and bool(loc['value']) and False is ref.get('documentation', False)
		if not valid:
			raise ValueError('Intake source-check requires manifest, source_sha256, quote, non-documentation flag and json_pointer/text/lines locator')
	# @used-by :meth:`IntakeSourceEvaluator.evaluate()`
	@staticmethod
	def __verify_source_file(root_resolved: Path, state: dict, manifest_file: Path, manifest_doc, src_file: Path, ref: dict) -> None:
		if '.json' != src_file.suffix.lower():
			raise ValueError('Intake source-check for an Upwork job URL requires the JSON job snapshot, not plain-text request notes')
		snap_file = dfh_inside(root_resolved, state['snapshot']) if isinstance(state.get('snapshot'), str) and state['snapshot'].strip() else None
		if manifest_file != snap_file and isinstance(manifest_doc, dict) and isinstance(manifest_doc.get('entries'), list):
			matched = next((e for e in manifest_doc['entries'] if isinstance(e, dict) and isinstance(e.get('durable_file'), str) and (dfh_inside(root_resolved, e['durable_file']) == src_file) and (e.get('sha256') == ref['source_sha256'])), None)
			if not matched or 'source.json' != matched.get('original_relative_provenance'):
				raise ValueError('Intake source-check for an Upwork job URL requires source.json provenance')
	# @used-by :meth:`Df.Harness.Text.SourceEvaluator.SourceEvaluator.evaluate()`
	def evaluate(self) -> dict:
		from agent_tools.claims import _manifest_primary, _verify_quote
		from agent_tools.evidence import local_file
		pp, state, cited_job_id = self.__load_verified_project_state()
		ref = self.__spec['evidence']
		self.__validate_intake_ref(ref)
		manifest_file = local_file(self.__root, ref['manifest'])
		manifest_doc = json.loads(manifest_file.read_text(encoding='utf-8-sig'))
		local_source = self.__resolve_local_source(pp, ref, manifest_doc)
		src_file = local_file(self.__root, local_source)
		self.__verify_source_file(pp.root, state, manifest_file, manifest_doc, src_file, ref)
		local_ref = {**ref, 'kind': 'intake', 'source': local_source, 'documentation': False}
		_manifest_primary(self.__root, local_ref)
		_verify_quote(self.__root, local_ref)
		snap_doc = json.loads(src_file.read_text(encoding='utf-8-sig'))
		if not isinstance(snap_doc, dict) or snap_doc.get('job_id') != cited_job_id:
			raise ValueError('Intake job snapshot job_id differs from the cited Upwork job URL')
		snap_obs = snap_doc.get('captured_at') or snap_doc.get('observed_at')
		cited, base_cited = (dfh_readable_reference(self.__spec['url']), urldefrag(dfh_readable_reference(self.__spec['url']))[0])
		return {'url': cited, 'requested_url': base_cited, 'final_url': base_cited, 'method': 'INTAKE_SNAPSHOT', 'http_status': None, 'observed_at': snap_obs if isinstance(snap_obs, str) and snap_obs else None, 'body_sha256': local_ref['source_sha256'], 'currency': self.__spec['currency'], 'edition': self.__spec.get('edition'), 'inputs': dfh_evidence_inputs(self.__root, {'facts': [{'evidence': [local_ref]}]})}
