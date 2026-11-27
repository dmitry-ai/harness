# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.sha256 import df_sha256
from Df.Harness.Review.MerkleCacheUpdater import MerkleCacheUpdater
from Df.Harness.Review.NativeProofVerifier import NativeProofVerifier
from Df.Harness.Review.PackageEnvelopeReader import PackageEnvelopeReader
from Df.Harness.Review.PackageReader import PackageReader
from Df.Harness.Review.QuorumEvaluator import QuorumEvaluator
from Df.Harness.Review.ReportValidator import REVIEW_SCHEMA
from agent_tools.research import inside
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class ReviewAuthorizer:
	# @used-by :func:`agent_tools.review.authorize()`
	# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.__apply_answer()`
	# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.__authorize_and_select()`
	# @used-by :meth:`Df.Harness.Workflow.FinalizeStageRunner.FinalizeStageRunner.run()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__run_approval_gate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests._exercise_review_record_and_auth()`
	def __init__(self, root, state: dict, *, response=None, package_path=None, request_ids=None, analysis_fn=None, package_reader=None, update_cache_fn=None, check_project_fn=None, inside_fn=None) -> None:
		self.__root = root
		self.__state = state
		self.__response = response
		self.__package_path = package_path
		self.__request_ids = request_ids
		self.__analysis_fn = PackageEnvelopeReader.load_analysis if None is analysis_fn else analysis_fn
		self.__package_reader = package_reader
		self.__update_cache_fn = update_cache_fn
		self.__check_project_fn = check_project_fn
		self.__inside = inside if None is inside_fn else inside_fn
	# @used-by :meth:`ReviewAuthorizer.__check_prereqs()`
	def __check_post_finalize(self, questions_current) -> None:
		finalize_time = self.__state.get('stages', {}).get('finalize', {}).get('time')
		relevant: dict = {}
		for qid, q in (self.__state.get('questions') or {}).items():
			q_time = q.get('time') or q.get('created_at')
			if self.__request_ids and q.get('request_id') in self.__request_ids:
				relevant[qid] = q
			elif finalize_time and q_time and (q_time > finalize_time):
				relevant[qid] = q
		if relevant and (not questions_current(self.__root, {**self.__state, 'questions': relevant})):
			raise ValueError('Complete current research questions/gaps before publication')
	# @used-by :meth:`ReviewAuthorizer.authorize()`
	def __check_prereqs(self, value: dict) -> None:
		from Df.Harness.Workflow.HealthAuditor import HealthAuditor
		from Df.Harness.Workflow.QuestionRegistry import QuestionRegistry
		q_fn = lambda r, st: QuestionRegistry(r).current(st)
		cp_fn = (lambda r, **kw: HealthAuditor(r).check_project(**kw)) if None is self.__check_project_fn else self.__check_project_fn
		is_finalized = 'complete' == self.__state.get('stages', {}).get('finalize', {}).get('status')
		if not is_finalized:
			if not q_fn(self.__root, self.__state) or not cp_fn(self.__root, prevalidated_analysis=value)['valid']:
				raise ValueError('Complete current research questions/gaps and resolve KB/evidence diagnostics before publication')
		else:
			self.__check_post_finalize(q_fn)
	# @used-by :meth:`ReviewAuthorizer.authorize()`
	def __collect_groups(self, evaluator: QuorumEvaluator, response_shas: set[str] | None) -> tuple[dict, list[str]]:
		groups, diagnostics = ({}, [])
		for entry in self.__state['reviews']:
			if REVIEW_SCHEMA != entry.get('schema_version') or (self.__package_path and entry.get('package') != self.__package_path) or (response_shas and entry.get('response_sha256') not in response_shas):
				continue
			try:
				package = self.__validate_entry(evaluator, entry)
				groups.setdefault(entry['package'], (package, []))[1].append(entry)
			except (ValueError, OSError, KeyError, TypeError) as exc:
				diagnostics.append(str(exc))
		return (groups, diagnostics)
	# @used-by :meth:`ReviewAuthorizer.__collect_groups()`
	def __validate_entry(self, evaluator: QuorumEvaluator, entry: dict) -> dict:
		package = PackageReader(self.__root, entry['package'], state=self.__state, analysis_fn=self.__analysis_fn, inside_fn=self.__inside).read_package() if None is self.__package_reader else self.__package_reader(self.__root, entry['package'], state=self.__state)
		if not evaluator.entry_proof_current(entry):
			raise ValueError('Review proof changed')
		if 'approved' != entry['result'] or not evaluator.findings_closed(entry):
			raise ValueError('Reviewer needs changes or has open findings; parent disposition cannot replace an approval')
		if entry.get('independent'):
			NativeProofVerifier(self.__root, entry, error_msg='Authored report differs from native final response').verify()
		elif 'routine' != package['risk']:
			raise ValueError('Significant risk cannot use self-review')
		return package
	# @used-by :func:`agent_tools.review.authorize()`
	# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.__apply_answer()`
	# @used-by :meth:`Df.Harness.Workflow.AnswerRecorder.AnswerRecorder.__authorize_and_select()`
	# @used-by :meth:`Df.Harness.Workflow.FinalizeStageRunner.FinalizeStageRunner.run()`
	# @used-by :meth:`Df.Harness.Workflow.StageCompleter.StageCompleter.__run_approval_gate()`
	# @used-by :meth:`test_df_harness_s11_wave2a_review.DfHarnessS11Wave2aReviewTests._exercise_review_record_and_auth()`
	def authorize(self) -> dict:
		value = self.__analysis_fn(self.__root)
		self.__check_prereqs(value)
		evaluator = QuorumEvaluator(self.__root, self.__state, analysis_fn=self.__analysis_fn, package_reader=self.__package_reader, inside_fn=self.__inside)
		response_shas = None
		if None is not self.__response:
			from agent_tools.metadata import strip_leading_metadata_header
			response_shas = {df_sha256(self.__response.encode('utf-8')), df_sha256(strip_leading_metadata_header(self.__response).encode('utf-8'))}
		groups, diagnostics = self.__collect_groups(evaluator, response_shas)
		selected = evaluator.select_authorized_group(groups)
		if None is selected:
			detail = '; '.join(dict.fromkeys(diagnostics))
			raise ValueError('Need current answer-bound approved A.A review; significant risk defaults to one independent adversarial falsifier reviewer (or two independent reviewers in standard/escalation mode)' + (': ' + detail if detail else ''))
		path, package, eligible = selected
		if None is self.__update_cache_fn:
			MerkleCacheUpdater(self.__root, package, value, analysis_fn=self.__analysis_fn).update()
		else:
			self.__update_cache_fn(self.__root, package, value)
		return {'package': path, 'package_sha256': df_sha256(self.__inside(self.__root, path).read_bytes()), 'response_sha256': package['response']['sha256'], 'risk': package['risk'], 'review_ids': [item['id'] for item in eligible]}
