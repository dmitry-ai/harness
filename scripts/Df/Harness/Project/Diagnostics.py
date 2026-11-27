# 2026-11-26 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
from Df.Core.lib.array.clean.main import df_clean_null
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
class Diagnostics:
	# @used-by :func:`agent_tools.diagnostics.problem()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.CalculationContract.CalculationContract.issues()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ComparisonContract.ComparisonContract.issues()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.CounterevidenceAuditor.CounterevidenceAuditor.check()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ScopeCoverageAuditor.ScopeCoverageAuditor.check()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__add()`
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__add()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_arguments()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_claim_counter()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.issues()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagValidator.RedFlagValidator.__check_flag()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagValidator.RedFlagValidator.issues()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.__add()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.issues()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.require_current_contract()`
	# @used-by :meth:`Df.Harness.Project.CardSyncAuditor.CardSyncAuditor.__identity_mismatches()`
	# @used-by :meth:`Df.Harness.Project.CardSyncAuditor.CardSyncAuditor.audit()`
	# @used-by :meth:`Df.Harness.Project.DriftAuditor.DriftAuditor.audit()`
	# @used-by :meth:`Df.Harness.Workflow.AnalysisCardAuditor.AnalysisCardAuditor.issues()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.__check_attachment()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.__check_image()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.__check_videos()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.issues()`
	# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.__check_deliverable_links()`
	# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.__check_one_off_scripts()`
	# @used-by :meth:`Df.Harness.Workflow.KbAuditor.KbAuditor.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def __init__(self, *, clean_null=None) -> None:
		self.__clean_null = df_clean_null if None is clean_null else clean_null
	# @used-by :func:`agent_tools.diagnostics.problem()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.CalculationContract.CalculationContract.issues()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ComparisonContract.ComparisonContract.issues()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.CounterevidenceAuditor.CounterevidenceAuditor.check()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.ScopeCoverageAuditor.ScopeCoverageAuditor.check()`
	# @used-by :meth:`Df.Harness.Analysis.Claim.StructureAuditor.StructureAuditor.__add()`
	# @used-by :meth:`Df.Harness.Analysis.ClaimGraph.ClaimGraph.__add()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_arguments()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.__check_claim_counter()`
	# @used-by :meth:`Df.Harness.Analysis.EvidenceAuditor.EvidenceAuditor.issues()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagValidator.RedFlagValidator.__check_flag()`
	# @used-by :meth:`Df.Harness.Analysis.RedFlagValidator.RedFlagValidator.issues()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.__add()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.issues()`
	# @used-by :meth:`Df.Harness.Analysis.Validator.Validator.require_current_contract()`
	# @used-by :meth:`Df.Harness.Project.CardSyncAuditor.CardSyncAuditor.__identity_mismatches()`
	# @used-by :meth:`Df.Harness.Project.CardSyncAuditor.CardSyncAuditor.audit()`
	# @used-by :meth:`Df.Harness.Project.DriftAuditor.DriftAuditor.audit()`
	# @used-by :meth:`Df.Harness.Workflow.AnalysisCardAuditor.AnalysisCardAuditor.issues()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.__check_attachment()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.__check_image()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.__check_videos()`
	# @used-by :meth:`Df.Harness.Workflow.AttachmentAuditor.AttachmentAuditor.issues()`
	# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.__check_deliverable_links()`
	# @used-by :meth:`Df.Harness.Workflow.HealthAuditor.HealthAuditor.__check_one_off_scripts()`
	# @used-by :meth:`Df.Harness.Workflow.KbAuditor.KbAuditor.issues()`
	# @used-by :meth:`test_df_harness_s11_wave2a.DfHarnessS11Wave2aTests.test_diagnostics_and_label_classes()`
	def problem(self, code, field, message, *, claim_id=None, file=None, hint=None, severity='error') -> dict:
		if None is hint:
			from Df.Harness.Analysis.ClaimHintResolver import ClaimHintResolver
			hint = ClaimHintResolver(code).resolve()
		return self.__clean_null(dict(code=code, field=field, message=message, claim_id=claim_id, file=str(file) if file else None, hint=hint, severity=severity))