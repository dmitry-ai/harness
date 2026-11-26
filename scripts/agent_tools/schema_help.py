# 2026-11-24 Dmitrii Fediuk https://github.com/dmitrii-fediuk
from __future__ import annotations
# 2026-11-26 "Move analysis workflow classes into Df/Harness single-class modules": https://github.com/dmitry-ai/harness/issues/380
from Df.Harness.Analysis.AssertionValidator import AssertionValidator
from Df.Harness.Analysis.ClaimHintResolver import ClaimHintResolver
from Df.Harness.Analysis.IssueHintAnnotator import IssueHintAnnotator
from Df.Harness.Analysis.SchemaHelp import SchemaHelp
from Df.Harness.Analysis.SchemaHelpFormatter import SchemaHelpFormatter
# @used-by :func:`agent_tools.experiments.requirement_issues()`
def annotate_experiment_issues(issues: list[str]) -> list[str]:
	return IssueHintAnnotator('experiment', issues).annotate()
# @used-by :meth:`agent_tools.review.ReviewReportValidator.validate()`
def annotate_review_issues(issues: list[str]) -> list[str]:
	return IssueHintAnnotator('review', issues).annotate()
# @used-by unused
def claim_error_hint(code: str) -> str | None:
	return ClaimHintResolver(code).resolve()
# @used-by :func:`agent_tools.cli_registry._format_schema_help()`
# @used-by :meth:`test_schema_help_and_analysis_merge_m10.SchemaHelpAndAnalysisMergeM10Tests.test_schema_help_command_returns_contract_for_all_topics()`
def format_schema_help_text(res: dict) -> str:
	return SchemaHelpFormatter(res).render_text()
# @used-by :func:`agent_tools.experiments.requirement_issues()`
def requirement_assertion_issues(label: str, requirement: dict, operators: tuple[str, ...]) -> list[str]:
	return AssertionValidator(label, requirement, operators).issues()
# @used-by :func:`agent_tools.cli_registry._exec_schema_help()`
def schema_help_payload(topic: str) -> dict:
	return SchemaHelp(topic).payload()