# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Harness.Text.SourceReceiptReader import SourceReceiptReader
from Df.Harness.lib.text_sources import dfh_source_urls
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class SourceCheckValidator:
	# @used-by :func:`agent_tools.text_sources.validate_source_checks()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__gate_applied_receipt()`
	# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.run()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
	def __init__(self, root, candidate: str, records) -> None:
		self.__root = root
		self.__candidate = candidate
		self.__records = records
	# @used-by :meth:`SourceCheckValidator.validate()`
	def __check_reference(self, reference, seen: set, inputs: dict, checks: list, issues: list) -> None:
		try:
			if not isinstance(reference, str):
				raise ValueError('An authored source-check object cannot replace a verified receipt')
			value = SourceReceiptReader(self.__root, self.__candidate, reference).read()
			if value['url'] in seen:
				raise ValueError('Duplicate source coverage')
			seen.add(value['url'])
			inputs.update(value['inputs'])
			checks.append(reference)
		except (OSError, ValueError, KeyError, TypeError) as exc:
			issues.append({'code': 'text.source_checks', 'message': str(exc), 'source_check': str(reference)})
	# @used-by :func:`agent_tools.text_sources.validate_source_checks()`
	# @used-by :meth:`Df.Harness.Text.Workspace.Workspace.__gate_applied_receipt()`
	# @used-by :meth:`Df.Harness.Text.WorkspaceCheckRunner.WorkspaceCheckRunner.run()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_claims_sources_and_cli_runner_classes()`
	def validate(self) -> dict:
		required = set(dfh_source_urls(self.__candidate))
		inputs, checks, seen, issues = ({}, [], set(), [])
		if not isinstance(self.__records, list):
			r = {'issues': [{'code': 'text.source_checks', 'message': 'source_checks must list immutable source receipt paths'}], 'inputs': {}, 'checks': []}
		else:
			for reference in self.__records:
				self.__check_reference(reference, seen, inputs, checks, issues)
			for url in sorted(required - seen):
				issues.append({'code': 'text.source_missing', 'message': 'External source needs a candidate-bound quote/anchor receipt: ' + url})
			r = {'issues': issues, 'inputs': inputs, 'checks': checks}
		return r
