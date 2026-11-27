# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.lib.research import dfh_inside
from Df.Harness.lib.text_review import dfh_text_review_state
from agent_tools.review import ReviewQuorumEvaluator, digest, read_package_envelope
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ReviewPackageReader:
	# @used-by :func:`agent_tools.text_review.read_package()`
	# @used-by :meth:`Df.Harness.Text.ApprovalIntegrityChecker.ApprovalIntegrityChecker.check()`
	# @used-by :meth:`Df.Harness.Text.ReviewAuthorizer.ReviewAuthorizer.__check_entry()`
	# @used-by :meth:`Df.Harness.Text.ReviewRecorder.ReviewRecorder.record()`
	def __init__(self, root, reference: str, *, require_current: bool=True, applied: bool=False) -> None:
		self.__root = root
		self.__reference = reference
		self.__require_current = require_current
		self.__applied = applied
	# @used-by :func:`agent_tools.text_review.read_package()`
	# @used-by :meth:`Df.Harness.Text.ApprovalIntegrityChecker.ApprovalIntegrityChecker.check()`
	# @used-by :meth:`Df.Harness.Text.ReviewAuthorizer.ReviewAuthorizer.__check_entry()`
	# @used-by :meth:`Df.Harness.Text.ReviewRecorder.ReviewRecorder.record()`
	def read(self) -> dict:
		from Df.Harness.Text.Workspace import Workspace
		root_p, _, value, _ = read_package_envelope(self.__root, self.__reference, expected_kind='client_text', error_msg='Invalid immutable text review package')
		if digest(dfh_inside(root_p, value['baseline']['file']).read_bytes()) != value['baseline']['sha256']:
			raise ValueError('Reviewed baseline bytes changed')
		if self.__require_current:
			from agent_tools.platforms.request_binding import native_project_fields
			if any((value.get(k) != v for k, v in native_project_fields(root_p).items())):
				raise ValueError('Text workspace identity changed')
			ws = Workspace(root_p)
			checked, _ = ws.refresh_check(value['check'], applied=self.__applied)
			op, _ = ws.operation(checked['operation'])
			if checked['inputs'] != {**value['kb_inputs'], **value['evidence_inputs']} or checked['claims'] != value['claims'] or checked['manifest'] != value['manifest'] or (checked['diff'] != value['diff']) or (op['requests'] != value['requests']):
				raise ValueError('Review no longer covers the exact request, diff, claim map or primary versions')
			if 'routine' == value['risk'] and ReviewQuorumEvaluator(root_p, dfh_text_review_state(root_p)).significant_findings(value['subject_sha256']):
				raise ValueError('Significant finding requires a new significant package and two independent reviewers')
		return value
