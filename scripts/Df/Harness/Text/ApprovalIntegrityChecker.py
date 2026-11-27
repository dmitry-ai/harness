# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from Df.Harness.Text.ReviewPackageReader import ReviewPackageReader
from Df.Harness.lib.research import dfh_inside
from Df.Harness.lib.text_review import dfh_text_review_issues, dfh_text_review_state
from agent_tools.review import digest, parse_report_object, verify_entry_native_proof
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ApprovalIntegrityChecker:
	# @used-by :func:`agent_tools.text_review.approval_integrity()`
	# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__collect_applied_reviews()`
	def __init__(self, root, approval, *, versioned_inputs=(), require_live_proof: bool=True) -> None:
		self.__root = root
		self.__approval = approval
		self.__versioned = versioned_inputs
		self.__require_live = require_live_proof
	# @used-by :meth:`ApprovalIntegrityChecker.check()`
	def __check_entry(self, root_p: Path, entry: dict | None, package: dict, inputs: dict) -> dict:
		ap = self.__approval
		if not entry or entry.get('package') != ap['package'] or entry.get('package_sha256') != ap['package_sha256'] or entry.get('subject_sha256') != ap['subject_sha256'] or ('approved' != entry.get('result')) or (not entry.get('independent')):
			raise ValueError('Saved independent publication review changed or is missing')
		for name, expected in entry['proof'].items():
			if name not in self.__versioned:
				if digest(dfh_inside(root_p, name).read_bytes()) != expected:
					raise ValueError('Saved publication review input changed: ' + name)
				inputs[name] = expected
		data = parse_report_object(dfh_inside(root_p, entry['report']).read_text(encoding='utf-8'))
		if 'approved' != data.get('result') or data.get('package') != ap['package']:
			raise ValueError('Saved publication review no longer matches its admitted report')
		self.__check_native_proof(root_p, entry, data, package)
		return deepcopy(entry)
	# @used-by :meth:`ApprovalIntegrityChecker.__check_entry()`
	def __check_native_proof(self, root_p: Path, entry: dict, data: dict, package: dict) -> None:
		if self.__require_live:
			if dfh_text_review_issues(data, package, dfh_inside(root_p, package['response']['file']).read_text(encoding='utf-8')):
				raise ValueError('Saved publication review no longer matches its admitted report')
			verify_entry_native_proof(root_p, entry, error_msg='Saved review differs from its original native response')
		elif entry.get('native_evidence'):
			native_file = dfh_inside(root_p, entry['native_evidence'])
			if native_file.exists():
				try:
					native = json.loads(native_file.read_text(encoding='utf-8'))
					if native.get('final_response_sha256') and digest(dfh_inside(root_p, entry['authored_response']).read_bytes()) != native.get('final_response_sha256'):
						raise ValueError('Saved review differs from its recorded native response')
				except (json.JSONDecodeError, OSError):
					pass
	# @used-by :func:`agent_tools.text_review.approval_integrity()`
	# @used-by :meth:`Df.Harness.Text.IntegrityVerifier.IntegrityVerifier.__collect_applied_reviews()`
	def check(self) -> dict:
		root_p = Path(self.__root).resolve()
		if not isinstance(self.__approval, dict) or not isinstance(self.__approval.get('review_ids'), list):
			raise ValueError('Saved publication approval is missing')
		package = ReviewPackageReader(root_p, self.__approval['package'], require_current=False).read()
		package_file = dfh_inside(root_p, self.__approval['package'])
		pkg_sha = digest(package_file.read_bytes())
		if pkg_sha != self.__approval.get('package_sha256') or package['subject_sha256'] != self.__approval.get('subject_sha256') or package['risk'] != self.__approval.get('risk'):
			raise ValueError('Saved publication approval identity changed')
		inputs = {self.__approval['package']: pkg_sha, package['response']['file']: package['response']['sha256'], package['baseline']['file']: package['baseline']['sha256']}
		entries = {entry['id']: entry for entry in dfh_text_review_state(root_p)['reviews']}
		eligible, reviews = (set(), [])
		for ident in self.__approval['review_ids']:
			copied = self.__check_entry(root_p, entries.get(ident), package, inputs)
			eligible.add(copied['reviewer_id'])
			reviews.append(copied)
		if (2 if 'significant' == package['risk'] else 1) > len(eligible):
			raise ValueError('Saved publication approval lacks its required independent reviewers')
		return {'files': inputs, 'reviews': reviews}
