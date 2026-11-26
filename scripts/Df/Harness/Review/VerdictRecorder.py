# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Review.AddressedReviewResolver import AddressedReviewResolver
from Df.Harness.Review.PackageReader import PackageReader
from Df.Harness.Review.ReportValidator import REVIEW_SCHEMA, ReportValidator
from Df.Harness.Review.VerdictPreparer import VerdictPreparer
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class VerdictRecorder:
	# @used-by :func:`agent_tools.review.record()`
	def __init__(self, root, report, *, parent_id: str, reviewer_id: str, role: str='AA', native_evidence=None, risk=None, package_reader=None, inside_fn=None) -> None:
		self.__root = root
		self.__report = report
		self.__parent_id = parent_id
		self.__reviewer_id = reviewer_id
		self.__role = role
		self.__native_evidence = native_evidence
		self.__risk = risk
		self.__package_reader = package_reader
		self.__inside_fn = inside_fn
	# @used-by :meth:`VerdictRecorder.record()`
	def __build_entry(self, prepared: dict, addressed_ids: list, proof: dict, report_mode: str, timestamp: str) -> dict:
		pkg, data = (prepared['package'], prepared['data'])
		return {'schema_version': REVIEW_SCHEMA, 'id': prepared['review_id'], 'parent_id': self.__parent_id, 'reviewer_id': self.__reviewer_id, 'role': self.__role, 'risk': pkg['risk'], 'review_mode': report_mode, 'package': prepared['package_path'], 'package_sha256': prepared['package_sha'], 'result': data['result'], 'subject_sha256': pkg['subject_sha256'], 'report': prepared['report_rel'], 'authored_response': prepared['authored_rel'], 'proof': proof, 'independent': prepared['independent'], 'kb_inputs': pkg['kb_inputs'], 'evidence_inputs': pkg['evidence_inputs'], 'response_sha256': pkg['response']['sha256'], 'requests': pkg['requests'], 'native_evidence': self.__native_evidence, 'dispositions': [], 'addresses_reviews': addressed_ids, 'model_verification': prepared['native'].get('model_verification', 'unverified'), 'time': timestamp}
	# @used-by :func:`agent_tools.review.record()`
	def record(self) -> dict:
		from agent_tools.workflow import hashes, load, now, update
		if 'AA' != self.__role:
			raise ValueError('Observed A.A parent/reviewer IDs are required')
		prepared = VerdictPreparer(self.__root, self.__report, parent_id=self.__parent_id, reviewer_id=self.__reviewer_id, native_evidence=self.__native_evidence, expected_risk=self.__risk, package_reader=self.__package_reader, inside_fn=self.__inside_fn).prepare()
		root_p, data, package, review_id = (prepared['root'], prepared['data'], prepared['package'], prepared['review_id'])
		existing = load(root_p)['reviews'] if isinstance(data.get('addresses_reviews'), list) and data.get('addresses_reviews') else []
		addressed_ids, extra_proofs = AddressedReviewResolver(root_p, data, package, prepared['independent'], existing).resolve_addressed()
		proof_paths = prepared['proof_paths'] + extra_proofs
		report_mode = 'falsifier' if ReportValidator.is_falsifier_report(data) else 'standard'
		# @used-by :meth:`VerdictRecorder.record()`
		def change(state: dict) -> None:
			if None is self.__package_reader:
				PackageReader(root_p, prepared['package_path'], state=state, inside_fn=self.__inside_fn).read_package()
			else:
				self.__package_reader(root_p, prepared['package_path'], state=state)
			if not any((item.get('id') == review_id for item in state['reviews'])):
				state['reviews'].append(self.__build_entry(prepared, addressed_ids, hashes(root_p, proof_paths), report_mode, now()))
		return update(root_p, {'action': 'review', 'reviewer_id': self.__reviewer_id, 'result': data['result'], 'review_id': review_id}, change)
