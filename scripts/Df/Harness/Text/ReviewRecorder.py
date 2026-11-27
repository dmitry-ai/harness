# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Text.ReviewPackageReader import ReviewPackageReader
from Df.Harness.lib.research import dfh_json_data
from Df.Harness.lib.text_review import dfh_source_reviews, dfh_text_review_issues, dfh_text_review_state
from Df.Harness.lib.text_workflow import dfh_text_folder
from agent_tools.review import REVIEW_SCHEMA, prepare_verdict_record, resolve_addressed_reviews
from agent_tools.storage import locked, replace_bytes
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ReviewRecorder:
	# @used-by :func:`agent_tools.text_review.record()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	def __init__(self, root, report, *, parent_id: str, reviewer_id: str, native_evidence) -> None:
		self.__root = root
		self.__report = report
		self.__parent_id = parent_id
		self.__reviewer_id = reviewer_id
		self.__native_evidence = native_evidence
	# @used-by :func:`agent_tools.text_review.record()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	def record(self) -> dict:
		from agent_tools.workflow import hashes, now
		root_r = Path(self.__root).resolve()
		prepared = prepare_verdict_record(root_r, self.__report, parent_id=self.__parent_id, reviewer_id=self.__reviewer_id, native_evidence=self.__native_evidence, allow_self=False, package_reader=lambda r, ref, **kw: ReviewPackageReader(r, ref, **kw).read(), issue_checker=lambda d, p, c: dfh_text_review_issues(d, p, c, root=root_r), reviews_dir_fn=lambda r_p, sha: dfh_text_folder(r_p) / 'reviews' / sha, artifact_prefix_fn=lambda _rev, rid: rid, diff_error='Immutable text review artifact differs')
		data, package, ident = (prepared['data'], prepared['package'], prepared['review_id'])
		proof_paths = prepared['proof_paths'] + list(dfh_source_reviews(root_r, data, package, prepared['candidate']))
		with locked(dfh_text_folder(root_r) / 'review-writer.lock'):
			state = dfh_text_review_state(root_r)
			old = {item['id']: item for item in state['reviews']}
			addressed, extra_proofs = resolve_addressed_reviews(root_r, data, package, prepared['independent'], state['reviews'])
			entry = {'schema_version': REVIEW_SCHEMA, 'id': ident, 'package': prepared['package_path'], 'package_sha256': prepared['package_sha'], 'parent_id': self.__parent_id, 'reviewer_id': self.__reviewer_id, 'role': 'AA', 'independent': prepared['independent'], 'risk': package['risk'], 'subject_sha256': package['subject_sha256'], 'result': data['result'], 'report': prepared['report_rel'], 'authored_response': prepared['authored_rel'], 'native_evidence': self.__native_evidence, 'proof': hashes(root_r, proof_paths + extra_proofs), 'dispositions': [], 'addresses_reviews': addressed, 'model_verification': prepared['native'].get('model_verification', 'unverified'), 'time': now()}
			if ident not in old:
				state['reviews'].append(entry)
				replace_bytes(dfh_text_folder(root_r) / 'reviews.json', dfh_json_data(state))
		return entry
