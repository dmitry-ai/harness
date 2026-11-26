# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class SchemaHelp:
	# @used-by :func:`agent_tools.schema_help.schema_help_payload()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_schema_help_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def __init__(self, topic: str) -> None:
		self.__topic = str(topic or '').strip().lower()
	# @used-by :meth:`SchemaHelp.payload()`
	def __analysis(self) -> dict:
		from Df.Harness.Analysis.Claim.StructureAuditor import KINDS, PROPERTIES, STATUSES
		from Df.Harness.Analysis.Validator import SECTIONS
		return {
			'valid': True,
			'topic': 'analysis',
			'schema_version': 3,
			'commands': ['harness.py save-analysis <project> --candidate <file> [--merge] [--partial] [--expected-sha256 <sha>]', 'harness.py validate-analysis <project>/\ua616/KB/Analysis.json --format json --evidence', 'harness.py render-analysis <project>/\ua616/KB/Analysis.json'],
			'required_fields': {'top_level': ['schema_version', 'facts', *SECTIONS, 'notes', 'websites', 'red_flags'], 'claim': ['id', 'essence', 'assessment_basis', 'knowledge_type', 'verification_status', 'scope', 'properties', 'derived_from', 'evidence', 'missing_checks', 'materiality', 'novelty', 'category', 'impact'], 'stage_claim_extra': ['for', 'against', 'counterevidence (when against is empty)', 'probability_percent (or score_percent + criterion + applicability + validation for methods)', 'addresses (required for causes/methods)', 'alternative_explanations + discriminating_check (for causes/misconceptions)']},
			'enums': {'knowledge_type': sorted(KINDS), 'verification_status': sorted(STATUSES), 'properties': sorted(PROPERTIES), 'materiality': ['routine', 'significant'], 'novelty': ['new', 'restatement'], 'category': ['architecture', 'causal', 'descriptive', 'interaction', 'pricing']},
			'common_pitfalls': ['Never put inline source/quote inside for/against when referencing claim_id or evidence_id.', 'Unverified hypotheses with empty against cannot exceed probability_percent 75.', 'Use save-analysis --merge --partial to validate and stage sections incrementally into \ua616/data/analysis-draft.json.'],
			'minimal_example': {'schema_version': 3, 'facts': [], 'identity': [{'id': 'F-ID', 'essence': 'Verbatim intake fact.', 'assessment_basis': 'Saved intake.', 'knowledge_type': 'client_report', 'verification_status': 'verified', 'scope': {'description': 'Intake only.', 'sample': ['Evidence/intake.json'], 'limitations': ['No admin access.']}, 'properties': ['content'], 'derived_from': [], 'evidence': [{'id': 'E-1', 'kind': 'intake', 'source': 'Evidence/intake.json', 'manifest': 'Evidence/intake.json', 'source_sha256': '<64-hex>', 'quote': 'Verbatim intake fact.', 'locator': {'type': 'json_pointer', 'value': '/title'}}], 'missing_checks': [], 'materiality': 'routine', 'novelty': 'new', 'category': 'descriptive', 'impact': {'severity': 'unknown', 'basis': 'Not measured.', 'evidence_claim_ids': []}, 'probability_percent': 100, 'addresses': [], 'for': [{'argument': 'Exact quote.', 'evidence_id': 'E-1'}], 'against': [], 'counterevidence': {'status': 'not_found', 'reviewed_sources': ['Evidence/intake.json'], 'limitations': 'Intake only.'}}], 'concerns': [], 'misconceptions': [], 'causes': [], 'methods': [], 'notes': {'concerns': 'Explain empty section.'}, 'websites': [{'role': 'client', 'url': None, 'basis_id': 'F-ID'}], 'red_flags': []},
		}
	# @used-by :meth:`SchemaHelp.payload()`
	def __experiment(self) -> dict:
		from Df.Harness.Experiment.RequirementValidator import METHODS, OPERATORS, PROPERTY_METHODS, STATUSES
		return {
			'valid': True,
			'topic': 'experiment',
			'schema_version': 1,
			'commands': ['harness.py prepare-experiment <project> --spec <plan.json>', 'harness.py record-experiment <project> --spec <run.json>'],
			'required_fields': {'requirement': ['id', 'claim', 'property', 'method', 'scope.objects', 'conditions', 'expected', 'falsification', 'discriminating_test', 'completion_criterion', 'alternatives', 'assertions'], 'assertion': ['id', 'artifact_id XOR artifact_role', 'locator {type, value}', 'operator', 'expected', 'disconfirming {operator, expected}'], 'run': ['plan', 'plan_sha256', 'status', 'actual_result', 'actual_steps', 'conditions', 'artifacts']},
			'enums': {'methods': list(METHODS), 'operators': list(OPERATORS), 'statuses': list(STATUSES), 'property_methods': {k: sorted(v) for k, v in sorted(PROPERTY_METHODS.items())}},
			'common_pitfalls': ['property must be supported by the chosen method in property_methods.', 'Every assertion requires exactly one of artifact_id or artifact_role and both positive and disconfirming comparisons.', 'json_pointer locator values must be empty or start with "/".'],
			'minimal_example': {'id': 'EXP-1', 'claim': 'Target page exposes Product JSON-LD.', 'property': 'markup', 'method': 'http', 'scope': {'objects': ['https://example.com/product']}, 'conditions': {'session': {'mode': 'unknown'}}, 'expected': 'JSON-LD script contains Product type.', 'falsification': 'No Product type appears in fetched HTML.', 'discriminating_test': 'Inspect extracted JSON-LD @type.', 'completion_criterion': 'Saved HTTP observation inspected.', 'alternatives': ['Markup injected only after client JS.'], 'assertions': [{'id': 'A-1', 'artifact_id': 'page_html', 'locator': {'type': 'text', 'value': 'Product'}, 'operator': 'contains', 'expected': 'Product', 'disconfirming': {'operator': 'equals', 'expected': ''}}]},
		}
	# @used-by :meth:`SchemaHelp.payload()`
	def __review(self) -> dict:
		from Df.Harness.Review.Classifier import TASK_FLAGS
		from Df.Harness.Review.InputReceiptBuilder import REPORT_CONTRACT
		from Df.Harness.Review.ReportValidator import REVIEW_SCHEMA, SCOPES
		return {
			'valid': True,
			'topic': 'review',
			'schema_version': REVIEW_SCHEMA,
			'commands': ['harness.py prepare-review <project> --parent <uuid> --spec <spec.json> --response-file <resp.md>', 'harness.py review-input <project> --package <pkg-json>', 'harness.py native-review-proof <project> --parent <uuid> --reviewer <child-uuid> [--wait-timeout 60]', 'harness.py record-review <project> --parent <uuid> --reviewer <child-uuid> --report <report.json> --native-evidence <proof.json>'],
			'required_fields': {'falsifier_report': ['schema_version', 'review_mode', 'package', 'package_sha256', 'scope', 'result', 'disproved_claims', 'findings'], 'standard_report': ['schema_version', 'package', 'package_sha256', 'scope', 'result', 'claim_reviews', 'findings'], 'claim_review': ['claim_id', 'observed', 'inferred', 'method', 'alternatives', 'limits', 'falsification', 'raw_vs_criteria', 'outcome', 'test_alignment']},
			'enums': {'result': ['approved', 'needs_changes'], 'review_mode': ['falsifier', 'standard'], 'outcome': ['supported', 'qualified', 'unsupported'], 'relationship': ['direct', 'proxy', 'irrelevant'], 'scope': list(SCOPES), 'task_flags': sorted(TASK_FLAGS)},
			'common_pitfalls': ['Copy test_alignment.target_claim verbatim from review-input claim_targets[claim_id] without paraphrasing.', 'Return the JSON verdict once in the final native PLANNER_RESPONSE message; never duplicate full JSON via send_message.', 'Default significant /upwork-init audits to one adversarial falsifier reviewer; escalate to 2 only on findings/needs_changes.'],
			'minimal_example': {'schema_version': REVIEW_SCHEMA, 'review_mode': 'falsifier', 'package': '<package-rel-path>', 'package_sha256': '<64-hex>', 'scope': list(SCOPES), 'result': 'approved', 'disproved_claims': [], 'findings': []},
			'report_contract': dict(REPORT_CONTRACT),
		}
	# @used-by :func:`agent_tools.schema_help.schema_help_payload()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_schema_help_classes()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_z_project_sync_and_schema_paths()`
	def payload(self) -> dict:
		builders = {'analysis': self.__analysis, 'experiment': self.__experiment, 'review': self.__review}
		builder = builders.get(self.__topic)
		if None is builder:
			raise ValueError('Supported schema-help topics: ' + ', '.join(sorted(builders)))
		return builder()