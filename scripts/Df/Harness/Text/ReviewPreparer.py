# 2026-11-27 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.lib.research import dfh_json_data
from Df.Harness.lib.text_review import SCOPES, dfh_text_report_contract, dfh_text_review_state
from Df.Harness.lib.text_workflow import dfh_text_folder
from agent_tools.review import REVIEW_SCHEMA, ReviewClassifier, ReviewQuorumEvaluator, digest, is_nonempty_text, subject_digest
from agent_tools.storage import write_immutable_bytes
# 2026-11-27 "Move repository and grounding subsystems into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/382
class ReviewPreparer:
	# @used-by :func:`agent_tools.text_review.prepare()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	def __init__(self, root, check: str, parent_id: str, spec=None) -> None:
		self.__root = root
		self.__check = check
		self.__parent_id = parent_id
		self.__spec = spec or {}
	# @used-by :meth:`ReviewPreparer.prepare()`
	def __build_payload(self, root_p: Path, checked: dict, candidate: str, op: dict, flags: list, risk: str) -> dict:
		from agent_tools.platforms.request_binding import native_project_fields
		inputs = checked['inputs']
		base_file = dfh_text_folder(root_p) / 'operations' / op['id'] / 'base.bin'
		value = {'schema_version': REVIEW_SCHEMA, 'kind': 'client_text', 'project_root': str(root_p), **native_project_fields(root_p), 'parent_id': self.__parent_id, 'operation': op['id'], 'check': self.__check, 'scope': list(SCOPES), 'goal': op['goal'], 'requests': op['requests'], 'target': op['target'], 'response': {'file': checked['candidate'], 'sha256': digest(candidate.encode()), 'bytes': len(candidate.encode())}, 'baseline': {'file': base_file.relative_to(root_p).as_posix(), 'sha256': digest(base_file.read_bytes())}, 'diff': checked['diff'], 'manifest': checked['manifest'], 'claims': checked['claims'], 'claim_versions': checked['claim_versions'], 'kb_inputs': {p: s for p, s in inputs.items() if p.endswith('.json') and '/Evidence/' not in p}, 'evidence_inputs': {p: s for p, s in inputs.items() if not (p.endswith('.json') and '/Evidence/' not in p)}, 'source_checks': checked['source_checks'], 'risk': risk, 'risk_basis': self.__spec.get('basis', 'Computed from the actual referenced claim types and current task flags.'), 'task_flags': flags}
		value['subject_sha256'] = subject_digest(value)
		if ReviewQuorumEvaluator(root_p, dfh_text_review_state(root_p)).significant_findings(value['subject_sha256']):
			value['risk'] = 'significant'
		return value
	# @used-by :func:`agent_tools.text_review.prepare()`
	# @used-by :meth:`Df.Harness.Text.CliRunner.CliRunner.__review_source_handlers()`
	# @used-by :meth:`test_df_harness_s11_wave2c_text_flow.DfHarnessS11Wave2CTextFlowTests.test_workspace_integrity_and_review_classes()`
	def prepare(self) -> dict:
		from Df.Harness.Text.Workspace import Workspace
		root_p = Path(self.__root).resolve()
		if not is_nonempty_text(self.__parent_id):
			raise ValueError('Observed parent conversation ID is required')
		ws = Workspace(root_p)
		checked, candidate = ws.refresh_check(self.__check)
		if 'semantic' != checked['coverage']:
			raise ValueError('A mechanical diff is not a substantive review subject')
		op, _ = ws.operation(checked['operation'])
		flags = self.__spec.get('task_flags', [])
		if not isinstance(flags, list) or any((not is_nonempty_text(x) for x in flags)):
			raise ValueError('task_flags must name the current task changes')
		if self.__spec.get('risk') not in (None, 'routine', 'significant'):
			raise ValueError('Review risk must be routine or significant')
		risk = 'significant' if ReviewClassifier.has_significant_flags(checked['claims'], flags) or 'significant' == self.__spec.get('risk') else 'routine'
		value = self.__build_payload(root_p, checked, candidate, op, flags, risk)
		raw = dfh_json_data(value)
		path = write_immutable_bytes(dfh_text_folder(root_p) / 'reviews' / (digest(raw) + '-inputs.json'), raw, diff_error='Immutable text review artifact differs')
		return {**value, 'package': path.relative_to(root_p).as_posix(), 'package_sha256': digest(raw), 'required_independent_reviewers': 2 if 'significant' == value['risk'] else 1, 'report_contract': dfh_text_report_contract()}
