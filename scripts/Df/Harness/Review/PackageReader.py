# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Review.ClaimEvidenceCollector import ClaimEvidenceCollector
from Df.Harness.Review.Classifier import Classifier
from Df.Harness.Review.PackageEnvelopeReader import PackageEnvelopeReader
from Df.Harness.Review.QuorumEvaluator import QuorumEvaluator
from agent_tools.research import inside
from agent_tools.storage import read_addressed_json
import importlib
PACKAGE_HANDLERS: dict = {}
_ERR_MSG = 'Immutable answer-bound review package schema 2 is required'
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class PackageReader:
	# @used-by :func:`agent_tools.review.read_package()`
	# @used-by :meth:`Df.Harness.Review.ApprovalChecker.ApprovalChecker.check()`
	# @used-by :meth:`Df.Harness.Review.InputReceiptBuilder.InputReceiptBuilder.build()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__validate_entry()`
	# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__load_and_check()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_review_lifecycle_and_validators_extra()`
	def __init__(self, root, package: str, *, state=None, require_current: bool=True, analysis_fn=None, approved_fn=None, inside_fn=None) -> None:
		self.__root = root
		self.__package = package
		self.__state = state
		self.__require_current = require_current
		self.__analysis_fn = PackageEnvelopeReader.load_analysis if None is analysis_fn else analysis_fn
		self.__approved_fn = approved_fn
		self.__inside = inside if None is inside_fn else inside_fn
	# @used-by :meth:`PackageReader.__validate_current()`
	def __check_claims(self, cur_state: dict, data: dict, value: dict) -> None:
		index = ClaimEvidenceCollector.claim_index(value)
		is_finalized = 'complete' == cur_state.get('stages', {}).get('finalize', {}).get('status')
		if any(((c['claim_id'] not in index and (not is_finalized)) or (c['claim_id'] in index and c['claim_sha256'] != ClaimEvidenceCollector.claim_digest(index[c['claim_id']])) for c in data['claims'])):
			raise ValueError('Reviewed response claim version changed')
	# @used-by :meth:`PackageReader.read_package()`
	def __validate_current(self, root_p: Path, cur_state: dict, data: dict, cand_bytes: bytes) -> None:
		from Df.Harness.Workflow.HashCollector import HashCollector
		if data.get('kb_inputs') != HashCollector(root_p, HashCollector.kb_paths(root_p)).collect() or data.get('evidence_inputs') != HashCollector(root_p, HashCollector.evidence_paths(root_p)).collect():
			raise ValueError('Review package does not match present KB and primary evidence')
		if data.get('requests') != [{'id': item['id'], 'text': item['text']} for item in cur_state['requests']]:
			raise ValueError('Review package does not cover the exact current requests')
		value = self.__analysis_fn(root_p)
		self.__check_claims(cur_state, data, value)
		spec = {'risk': data['risk'], 'basis': data['risk_basis'], 'request_scope': data['request_scope'], 'claim_ids': [c['claim_id'] for c in data['claims']], 'claims': data['claims'], 'task_flags': data['task_flags']}
		Classifier(root_p, cur_state, value, exclude_package=self.__package, approved_fn=self.__approved_fn).classify(spec, cand_bytes.decode('utf-8'))
		if 'routine' == data['risk'] and QuorumEvaluator(root_p, cur_state).significant_findings(data['subject_sha256']):
			raise ValueError('A significant/critical finding requires a significant package and two independent A.A')
	# @used-by :func:`agent_tools.review._package_handler()`
	# @used-by :meth:`Df.Harness.Review.InputReceiptBuilder.InputReceiptBuilder.build()`
	# @used-by :meth:`PackageReader.read_package()`
	@classmethod
	def package_handler(cls, kind):
		if 'client_text' == kind and kind not in PACKAGE_HANDLERS:
			importlib.import_module('agent_tools.text_review')
		return PACKAGE_HANDLERS.get(kind)
	# @used-by :func:`agent_tools.review.register_package_handler()`
	@classmethod
	def register_handler(cls, kind, *, package_reader, contract_factory=None) -> None:
		PACKAGE_HANDLERS[kind] = {'package_reader': package_reader, 'contract_factory': contract_factory}
	# @used-by :func:`agent_tools.review.read_package()`
	# @used-by :meth:`Df.Harness.Review.ApprovalChecker.ApprovalChecker.check()`
	# @used-by :meth:`Df.Harness.Review.InputReceiptBuilder.InputReceiptBuilder.build()`
	# @used-by :meth:`Df.Harness.Review.ReviewAuthorizer.ReviewAuthorizer.__validate_entry()`
	# @used-by :meth:`Df.Harness.Review.VerdictPreparer.VerdictPreparer.__load_and_check()`
	# @used-by :meth:`Df.Harness.Review.VerdictRecorder.VerdictRecorder.record()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests.test_z_review_lifecycle_and_validators_extra()`
	def read_package(self) -> dict:
		from Df.Harness.Workflow.StateLoader import StateLoader
		_, peek = read_addressed_json(self.__inside(Path(self.__root).resolve(), self.__package), suffix='-inputs.json', error_msg=_ERR_MSG)
		handler = self.package_handler(peek.get('kind'))
		if None is not handler:
			r = handler['package_reader'](self.__root, self.__package, require_current=self.__require_current)
		else:
			root_p, _, data, cand_bytes = PackageEnvelopeReader(self.__root, self.__package, error_msg=_ERR_MSG, inside_fn=self.__inside).read_envelope()
			cur_state = self.__state or StateLoader(root_p).load()
			if data.get('job_id') != cur_state['job_id']:
				raise ValueError('Review package belongs to another project')
			if self.__require_current:
				self.__validate_current(root_p, cur_state, data, cand_bytes)
			r = data
		return r
