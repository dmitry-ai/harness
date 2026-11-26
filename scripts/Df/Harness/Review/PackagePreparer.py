# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Review.BlindPredicateBuilder import BlindPredicateBuilder
from Df.Harness.Review.Classifier import Classifier
from Df.Harness.Review.MerkleDeltaCalculator import MerkleDeltaCalculator
from Df.Harness.Review.PackageEnvelopeReader import PackageEnvelopeReader
from Df.Harness.Review.QuorumEvaluator import QuorumEvaluator
from Df.Harness.Review.ReportValidator import REVIEW_SCHEMA, SCOPES
from Df.Harness.Review.ReviewModeResolver import ReviewModeResolver
from Df.Qa.lib.validation.check_strict import df_is_sne
from agent_tools.research import json_data
from agent_tools.storage import write_immutable_bytes
import re
_DIFF_ERR = 'Immutable review artifact differs; preserve the original and create a new attempt'
_INIT4_RE = '(?im)(?:generated\\s+at\\s+the\\s+`?finalize`?\\s+stage|\\u0444\\u043e\\u0440\\u043c\\u0438\\u0440\\u0443\\u0435\\u0442\\u0441\\u044f\\s+\\u043d\\u0430\\s+\\u044d\\u0442\\u0430\\u043f\\u0435\\s+`?finalize`?)|^\\s*#{1,6}\\s*(?:\\d+(?:\\.\\d+)*\\.?\\s*)?(?:Project\\s+Artifacts|\\u0410\\u0440\\u0442\\u0435\\u0444\\u0430\\u043a\\u0442\\u044b\\s+\\u043f\\u0440\\u043e\\u0435\\u043a\\u0442\\u0430)\\b'
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PackagePreparer:
	# @used-by :func:`agent_tools.review.prepare()`
	def __init__(self, root, parent_id: str, spec: dict, response: str, *, analysis_fn=None, approved_fn=None) -> None:
		self.__root = Path(root).resolve()
		self.__parent_id = parent_id
		self.__spec = spec
		self.__response = response
		self.__analysis_fn = PackageEnvelopeReader.load_analysis if None is analysis_fn else analysis_fn
		self.__approved_fn = approved_fn
	# @used-by :meth:`PackagePreparer.prepare()`
	def __build_data(self, state: dict, requests: list, value: dict, classified: dict, candidate: Path, resp_sha: str, payload: bytes) -> dict:
		from agent_tools.source_grounding import discover_entity_tier0_sources
		from agent_tools.workflow import evidence_paths, hashes, kb_paths
		ev_inputs = hashes(self.__root, evidence_paths(self.__root))
		extra = {'auto_tier0_evidence': discover_entity_tier0_sources(self.__root, self.__response), 'merkle_delta': MerkleDeltaCalculator(self.__root, classified['claims'], value, ev_inputs).compute(), 'blind_verification_predicates': BlindPredicateBuilder(classified['claims'], value).build()}
		data = {'schema_version': REVIEW_SCHEMA, 'project_root': str(self.__root), 'job_id': state['job_id'], 'parent_id': self.__parent_id, **classified, 'requests': requests, 'response': {'file': candidate.relative_to(self.__root).as_posix(), 'sha256': resp_sha, 'bytes': len(payload)}, 'kb_inputs': hashes(self.__root, kb_paths(self.__root)), 'evidence_inputs': ev_inputs, 'scope': list(SCOPES), 'knowledge_source': 'agent KB, primary evidence, current requests and exact response; no Context.md', **extra}
		data['subject_sha256'] = PackageEnvelopeReader.subject_digest(data)
		evaluator = QuorumEvaluator(self.__root, state)
		if (mode := ReviewModeResolver(self.__spec, data, evaluator).resolve()):
			data['review_mode'] = mode
		if 'routine' == data['risk'] and evaluator.significant_findings(data['subject_sha256']):
			raise ValueError('A significant/critical finding on this exact answer requires a significant package and two independent A.A')
		return data
	# @used-by :meth:`PackagePreparer.prepare()`
	def __validate_response(self, value: dict) -> None:
		from agent_tools.source_grounding import local_source_grounding_issues, sync_fact_ledger
		from agent_tools.workflow import doc4_sentence_issues
		if isinstance(value, dict) and [] == value.get('red_flags') and re.search('(?im)^\\s*#{1,6}\\s+Red Flags\\b', self.__response):
			raise ValueError('Do not include a Red Flags heading in the response when Analysis.json red_flags is empty (INIT-5)')
		if re.search(_INIT4_RE, self.__response):
			raise ValueError('Candidate response must not contain internal service notes or uninitialized finalize placeholders (INIT-4)')
		doc4_issues = doc4_sentence_issues(self.__response)
		if doc4_issues:
			raise ValueError('\n'.join(doc4_issues))
		sync_fact_ledger(self.__root)
		grounding_issues = local_source_grounding_issues(self.__root, self.__response)
		if grounding_issues:
			raise ValueError('\n'.join(grounding_issues))
	# @used-by :meth:`PackagePreparer.prepare()`
	def __write_candidate(self, pp) -> tuple[Path, str, bytes]:
		payload = self.__response.encode('utf-8')
		resp_sha = df_sha256(payload)
		candidate = pp.evidence_dir / 'Reviews/Candidates' / (resp_sha + '.txt')
		write_immutable_bytes(candidate, payload, diff_error=_DIFF_ERR)
		return (candidate, resp_sha, payload)
	# @used-by :func:`agent_tools.review.prepare()`
	def prepare(self) -> dict:
		from agent_tools.path_registry import project_paths
		from agent_tools.workflow import load
		if not df_is_sne(self.__parent_id) or not df_is_sne(self.__response):
			raise ValueError('Observed parent ID and the exact nonempty candidate response are required')
		state = load(self.__root)
		requests = [{'id': item['id'], 'text': item['text']} for item in state['requests']]
		if not requests:
			raise ValueError('Save/import the exact current requests before preparing review')
		value = self.__analysis_fn(self.__root)
		self.__validate_response(value)
		pp = project_paths(self.__root, exact_root=True)
		classified = Classifier(self.__root, state, value, approved_fn=self.__approved_fn).classify(self.__spec, self.__response)
		candidate, resp_sha, payload = self.__write_candidate(pp)
		data = self.__build_data(state, requests, value, classified, candidate, resp_sha, payload)
		pkg_bytes = json_data(data)
		path = pp.evidence_dir / 'Reviews' / (df_sha256(pkg_bytes) + '-inputs.json')
		write_immutable_bytes(path, pkg_bytes, diff_error=_DIFF_ERR)
		return {'package': path.relative_to(self.__root).as_posix(), 'package_sha256': df_sha256(pkg_bytes), **data}
