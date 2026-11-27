# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Text.ReviewPackageReader import ReviewPackageReader
from Df.Harness.lib.research import dfh_inside
from Df.Harness.lib.text_review import dfh_text_review_issues, dfh_text_review_state
from agent_tools.review import ReviewQuorumEvaluator, digest, parse_report_object, verify_entry_native_proof
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ReviewAuthorizer:
	# @used-by :func:`agent_tools.text_review.authorize()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__gate_applied_receipt()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.apply()`
	def __init__(self, root, check: str, *, applied: bool=False) -> None:
		self.__root = root
		self.__check = check
		self.__applied = applied
	# @used-by :meth:`ReviewAuthorizer.authorize()`
	def __check_entry(self, root_p: Path, entry: dict, checked: dict, evaluator: ReviewQuorumEvaluator, groups: dict, diagnostics: list) -> None:
		try:
			package = ReviewPackageReader(root_p, entry['package'], applied=self.__applied).read()
			if package['check'] == self.__check and package['operation'] == checked['operation'] and package['response']['sha256'] == checked['candidate_sha256']:
				if not evaluator.entry_proof_current(entry) or (not entry.get('independent')):
					raise ValueError('Independent native review proof changed or is missing')
				data = parse_report_object(dfh_inside(root_p, entry['report']).read_text(encoding='utf-8'))
				if dfh_text_review_issues(data, package, dfh_inside(root_p, package['response']['file']).read_text(encoding='utf-8'), root=root_p):
					raise ValueError('Reviewer assessment is incomplete')
				verify_entry_native_proof(root_p, entry)
				if 'approved' == entry['result'] and evaluator.findings_closed(entry):
					groups.setdefault(entry['package'], (package, []))[1].append(entry)
		except (OSError, ValueError, KeyError, TypeError) as exc:
			diagnostics.append(str(exc))
	# @used-by :func:`agent_tools.text_review.authorize()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__gate_applied_receipt()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.apply()`
	def authorize(self) -> dict:
		from Df.Harness.Text.Workspace import Workspace
		root_p, state = (Path(self.__root).resolve(), dfh_text_review_state(self.__root))
		evaluator = ReviewQuorumEvaluator(root_p, state)
		checked, _ = Workspace(root_p).refresh_check(self.__check, applied=self.__applied)
		groups, diagnostics = ({}, [])
		for entry in state['reviews']:
			self.__check_entry(root_p, entry, checked, evaluator, groups, diagnostics)
		selected = evaluator.select_authorized_group(groups, allow_routine_self=False, allow_falsifier_or_cached=False)
		if None is selected:
			raise ValueError('Current independent text approval is required; significant claims need two reviewers' + (': ' + '; '.join(dict.fromkeys(diagnostics)) if diagnostics else ''))
		reference, package, eligible = selected
		return {'package': reference, 'package_sha256': digest(dfh_inside(root_p, reference).read_bytes()), 'risk': package['risk'], 'subject_sha256': package['subject_sha256'], 'review_ids': [entry['id'] for entry in eligible]}
