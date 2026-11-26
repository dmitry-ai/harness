# 2026-10-15 Dmitrii Fediuk https://github.com/dmitrii-fediuk
# 2026-10-15
# "Eliminate redundant subagent searches with HTTP evidence caching, structured Analysis.json workflow, and in-chat resume":
# https://github.com/dmitry-ai/harness/issues/4
from typing import override
# @used-by :func:`agent_tools.analysis.analysis_issues()`
# @used-by :func:`agent_tools.analysis.require_current_contract()`
# @used-by :func:`agent_tools.claims._calculation_structure()`
# @used-by :func:`agent_tools.claims._comparison_structure()`
# @used-by :func:`agent_tools.evidence.evidence_issues()`
# @used-by :func:`agent_tools.journal_integrity.check_project_journal_problems()`
# @used-by :func:`agent_tools.knowledge.website_issues()`
# @used-by :func:`agent_tools.project_drift._kb_identity_mismatch_issues()`
# @used-by :func:`agent_tools.project_drift.analysis_card_sync_issues()`
# @used-by :func:`agent_tools.project_drift.domain_drift_issues()`
# @used-by :func:`agent_tools.red_flags.red_flag_issues()`
# @used-by :meth:`agent_tools.claims.ClaimGraphValidator._add()`
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor._analysis_card_issues()`
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor.attachment_issues()`
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor.check_project()`
# @used-by :meth:`agent_tools.workflow.ProjectHealthAuditor.kb_issues()`
def problem(code, field, message, *, claim_id=None, file=None, hint=None, severity='error'):
	# 2026-11-24
	# "Prevent context compaction with schema-help CLI and staged analysis merge":
	# https://github.com/dmitry-ai/harness/issues/217
	if None is hint:
		from .schema_help import claim_error_hint
		hint = claim_error_hint(code)
	return {k: v for k, v in dict(code=code, field=field, message=message, claim_id=claim_id, file=str(file) if file else None, hint=hint, severity=severity).items() if None is not v}
class ValidationError(ValueError):
	# 2026-11-26
	# "Apply cross-reference annotations across Harness Python and JavaScript":
	# https://github.com/dmitry-ai/harness/issues/305
	# @used-by :func:`require_valid()`
	# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_validators_emit_actionable_hints()`
	# @see :meth:`ValueError.__init__()`
	@override
	def __init__(self, issues):
		self.issues = issues
		# 2026-11-24
		# "Prevent context compaction with schema-help CLI and staged analysis merge":
		# https://github.com/dmitry-ai/harness/issues/217
		super().__init__('\n'.join((f"{x['code']} {x.get('claim_id', '')} {x['field']}: {x['message']}" + (f" [hint: {x['hint']}]" if x.get('hint') else '') for x in issues)))
# 2026-10-31
# "Reorganize AI into universal harness repository, translate rules and documentation to English, format per P.md, and enforce issue-driven Git workflow":
# https://github.com/dmitry-ai/harness/issues/26
# @used-by :func:`agent_tools.analysis.publish_analysis()`
# @used-by :func:`agent_tools.analysis.require_current_contract()`
# @used-by :func:`agent_tools.analysis.save_analysis()`
# @used-by :func:`agent_tools.analysis.validate_analysis()`
# @used-by :func:`agent_tools.analysis_merge._validate_partial()`
def require_valid(issues):
	errors = [x for x in issues if 'error' == x.get('severity', 'error')]
	if errors:
		raise ValidationError(errors)
