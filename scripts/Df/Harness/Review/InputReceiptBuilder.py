# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from pathlib import Path
from Df.Harness.Review.AlignmentValidator import TARGET_CLAIM_RULE
from Df.Harness.Review.ClaimTargetBuilder import ClaimTargetBuilder
from Df.Harness.Review.ContractBinder import ContractBinder
from Df.Harness.Review.PackageReader import PackageReader
from Df.Harness.Review.ReportValidator import REVIEW_SCHEMA, SCOPES
from agent_tools.research import inside
import os
REPORT_CONTRACT = {'schema_version': REVIEW_SCHEMA, 'required_top_level_fields': ['schema_version', 'package', 'package_sha256', 'result', 'scope', 'summary', 'claim_reviews', 'findings'], 'falsifier_required_top_level_fields': ['schema_version', 'review_mode', 'package', 'package_sha256', 'result', 'scope', 'summary', 'disproved_claims', 'findings'], 'result_options': ['approved', 'needs_changes'], 'required_scope': list(SCOPES), 'claim_review_fields': ['claim_id', 'observed', 'inferred', 'method', 'alternatives', 'limits', 'falsification', 'raw_vs_criteria', 'test_alignment', 'outcome'], 'test_alignment_fields': ['target_claim', 'tested_claim', 'relationship', 'rationale', 'counterexample'], 'target_claim_rule': TARGET_CLAIM_RULE, 'relationship_options': ['direct', 'proxy', 'irrelevant'], 'outcome_options': ['supported', 'qualified', 'unsupported'], 'finding_fields': ['id', 'claim_ids', 'severity', 'description', 'status'], 'severity_options': ['minor', 'significant', 'critical'], 'claim_review_required': {'fields': ['claim_id', 'observed', 'inferred', 'method', 'alternatives', 'limits', 'falsification', 'raw_vs_criteria', 'test_alignment', 'outcome'], 'outcome_options': ['supported', 'qualified', 'unsupported'], 'test_alignment_required': {'fields': ['target_claim', 'tested_claim', 'relationship', 'rationale', 'counterexample'], 'target_claim_rule': TARGET_CLAIM_RULE, 'relationship_options': ['direct', 'proxy', 'irrelevant']}}, 'finding_required': {'fields': ['id', 'claim_ids', 'severity', 'description', 'status'], 'severity_options': ['minor', 'significant', 'critical'], 'status_options': ['open', 'resolved', 'rejected']}, 'falsifier_fields': ['disproved_claims'], 'disproved_claim_fields': ['claim_id', 'excerpt_from_answer', 'contradicting_tier0_source', 'verbatim_quote_from_source', 'falsification_reason']}
_OPT_KEYS = ('kind', 'goal', 'diff', 'operation', 'check', 'manifest', 'source_checks', 'auto_tier0_evidence', 'merkle_delta', 'blind_verification_predicates', 'review_mode')
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class InputReceiptBuilder:
	# @used-by :func:`agent_tools.review.input_receipt()`
	def __init__(self, root, package: str, *, package_reader=None, inside_fn=None) -> None:
		self.__root = root
		self.__package = package
		self.__package_reader = package_reader
		self.__inside = inside if None is inside_fn else inside_fn
	# @used-by :func:`agent_tools.review.input_receipt()`
	def build(self) -> dict:
		from agent_tools.runtime import platform_name
		from agent_tools.workflow import file_hash
		data = PackageReader(self.__root, self.__package, inside_fn=self.__inside).read_package() if None is self.__package_reader else self.__package_reader(self.__root, self.__package)
		reviewer = os.environ.get('CODEX_THREAD_ID') or os.environ.get('ANTIGRAVITY_CONVERSATION_ID')
		if not reviewer and 'codex' == platform_name() and os.environ.get('CODEX_HOME'):
			raise ValueError('Native Codex reviewer thread ID is unavailable')
		handler = PackageReader.package_handler(data.get('kind'))
		pkg_sha = file_hash(self.__inside(self.__root, self.__package))
		base_contract = handler['contract_factory']() if None is not handler and None is not handler.get('contract_factory') else dict(REPORT_CONTRACT)
		contract = ContractBinder(base_contract, self.__package, pkg_sha, data.get('review_mode')).bind()
		return {'upwork_review_input': 1, 'review_schema_version': REVIEW_SCHEMA, 'verified': True, 'project_root': str(Path(self.__root).resolve()), 'job_id': data['job_id'], **{k: data[k] for k in ('project_id', 'project_kind') if k in data}, 'parent_id': data['parent_id'], 'reviewer_id': reviewer, 'package': self.__package, 'package_sha256': pkg_sha, 'kb_inputs': data['kb_inputs'], 'evidence_inputs': data['evidence_inputs'], 'requests': data['requests'], 'response': data['response'], 'claims': data['claims'], 'claim_targets': ClaimTargetBuilder(data.get('claims')).build(), 'risk': data['risk'], 'report_contract': contract, **{k: data[k] for k in _OPT_KEYS if k in data}}
